"""
WhatsApp Message Queue (OpenClaw-inspired)
=========================================

Implements three behaviors that make WhatsApp feel "real-time" and resilient:

1) Inbound debouncing (burst coalescing)
   - Users often send: "hey" -> "look at this" -> [image]
   - We coalesce rapid-fire messages into a single agent turn.

2) Per-session serialization (one run per phone)
   - Prevents overlapping Gemini calls that would race on shared chat history.

3) Mid-run steering (soft interruption)
   - If new messages arrive while the agent is thinking, we can inject them at
     safe boundaries (between Gemini rounds) to avoid sending stale replies.

WHY THIS MATTERS:
Twilio webhooks have tight response time expectations. We must return quickly,
while still giving the user a single coherent reply that includes all messages
they sent in a burst.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pipeline.gemini_client import call_gemini

logger = logging.getLogger(__name__)


def _now_s() -> float:
    return time.time()


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        return int(raw)
    except Exception:
        return default


DEBOUNCE_TEXT_MS = _env_int("WHATSAPP_INBOUND_DEBOUNCE_MS", 4000)
DEBOUNCE_FOLLOWUP_MS = _env_int("WHATSAPP_FOLLOWUP_DEBOUNCE_MS", 1000)
VOICE_AWAIT_S = float(os.getenv("WHATSAPP_VOICE_TRANSCRIPT_AWAIT_S", "4").strip() or "4")


@dataclass
class BufferedMessage:
    text: str
    media_items: List[Dict[str, Any]]
    profile_name: Optional[str]
    received_at_s: float
    voice_future: Optional[asyncio.Task[str]] = None


@dataclass
class CoalescedTurn:
    phone: str
    combined_text: str
    media_items: List[Dict[str, Any]]
    profile_name: Optional[str]
    message_count: int


def _looks_like_url(text: str) -> bool:
    t = (text or "").lower()
    return "http://" in t or "https://" in t


def _has_media_kind(media_items: List[Dict[str, Any]], kind: str) -> bool:
    k = (kind or "").strip().lower()
    for mi in media_items or []:
        if not isinstance(mi, dict):
            continue
        if str(mi.get("media_kind") or "").strip().lower() == k:
            return True
        ct = str(mi.get("content_type") or "").strip().lower()
        if k == "audio" and ct.startswith("audio/"):
            return True
        if k == "image" and ct.startswith("image/"):
            return True
        if k == "video" and ct.startswith("video/"):
            return True
    return False


def _inline_audio_part_from_media_items(media_items: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """
    Return a single inline_data-style dict for the first audio attachment,
    if base64_data is available.

    IMPORTANT: We intentionally do not fetch bytes here (no outbound HTTP) to keep
    this queue module lightweight. The webhook already downloads/uploads media and
    frequently includes base64_data for small attachments.
    """
    for mi in media_items or []:
        if not isinstance(mi, dict):
            continue
        ct = str(mi.get("content_type") or "").strip() or "application/octet-stream"
        if not ct.startswith("audio/"):
            continue
        b64 = str(mi.get("base64_data") or "").strip()
        if not b64:
            continue
        return {"mime_type": ct, "data": b64}
    return None


async def _transcribe_voice_note(media_items: List[Dict[str, Any]]) -> str:
    part = _inline_audio_part_from_media_items(media_items)
    if not part:
        return ""

    try:
        resp = await call_gemini(
            prompt=(
                "Transcribe this WhatsApp voice note.\n"
                "Return ONLY the transcript text.\n"
                "If it's not speech, say: (no speech)\n"
            ),
            model="flash-lite",
            temperature=0.0,
            max_tokens=800,
            use_spanish=False,
            strict_db_write=False,
            images=[part],
        )
        if resp.success and (resp.text or "").strip():
            txt = (resp.text or "").strip()
            if txt.lower() == "(no speech)":
                return ""
            return txt
    except Exception as exc:
        logger.debug("Queue voice transcription failed (non-fatal) | err=%s", exc)
    return ""


async def coalesce_messages(phone: str, messages: List[BufferedMessage]) -> CoalescedTurn:
    texts: List[str] = []
    media: List[Dict[str, Any]] = []
    profile: Optional[str] = None

    # Best-effort: await any voice transcripts (bounded).
    transcripts: List[str] = []
    for m in messages:
        if m.profile_name:
            profile = m.profile_name  # last-wins
        if (m.text or "").strip():
            texts.append((m.text or "").strip())
        if m.media_items:
            media.extend([x for x in m.media_items if isinstance(x, dict)])
        if m.voice_future is not None:
            try:
                t = await asyncio.wait_for(m.voice_future, timeout=VOICE_AWAIT_S)
                if (t or "").strip():
                    transcripts.append((t or "").strip())
            except asyncio.TimeoutError:
                # Let agent.py handle transcription later if needed.
                pass
            except Exception:
                pass

    combined = "\n".join([t for t in texts if t]).strip()
    if transcripts:
        # Keep this concise; long transcripts belong in the prompt, not WhatsApp UI.
        block = "\n\n".join([tr[:2000] for tr in transcripts][:2]).strip()
        if block:
            combined = (combined + "\n\n" if combined else "") + f"(voice transcript)\n{block}"

    # If user only sent media, provide a minimal placeholder so downstream logic has text.
    if not combined and media:
        combined = "(user sent media)"

    return CoalescedTurn(
        phone=phone,
        combined_text=combined,
        media_items=media,
        profile_name=profile,
        message_count=len(messages),
    )


def _coalesce_turns(turns: List[CoalescedTurn]) -> CoalescedTurn:
    if not turns:
        raise ValueError("_coalesce_turns() received empty list")
    phone = turns[-1].phone
    profile = next((t.profile_name for t in reversed(turns) if t.profile_name), None)
    media: List[Dict[str, Any]] = []
    texts: List[str] = []
    for t in turns:
        if (t.combined_text or "").strip():
            texts.append((t.combined_text or "").strip())
        if t.media_items:
            media.extend([x for x in t.media_items if isinstance(x, dict)])
    return CoalescedTurn(
        phone=phone,
        combined_text="\n".join(texts).strip(),
        media_items=media,
        profile_name=profile,
        message_count=sum(int(t.message_count or 0) for t in turns),
    )


class SessionQueue:
    """
    Per-phone serialization + pending queue.

    This queue is intentionally in-memory. It's designed to improve UX, not to be a
    durable task system. Messages are still persisted downstream by the agent.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._active: Dict[str, bool] = {}
        self._pending: Dict[str, List[CoalescedTurn]] = {}

    async def enqueue(self, turn: CoalescedTurn) -> None:
        phone = turn.phone
        async with self._lock:
            is_active = bool(self._active.get(phone))
            if is_active:
                self._pending.setdefault(phone, []).append(turn)
                logger.info("Queue: enqueued pending | phone=%s | pending=%d", phone, len(self._pending.get(phone, [])))
                return
            self._active[phone] = True

        # Run in background (in-process); webhook already returned.
        asyncio.create_task(self._run_session(phone, turn))

    def drain_pending(self, phone: str) -> List[CoalescedTurn]:
        """
        Drain pending turns for mid-run steering.
        Non-async so agent can call it cheaply.
        """
        turns = self._pending.pop(phone, [])
        return [t for t in turns if isinstance(t, CoalescedTurn)]

    async def _run_session(self, phone: str, first_turn: CoalescedTurn) -> None:
        """
        Run turns sequentially for a single phone. Uses a followup debounce to
        reduce "reply storms" when the user sends more messages during the reply.
        """
        try:
            current: Optional[CoalescedTurn] = first_turn
            while current is not None:
                await self._run_turn(current)

                # Followup debounce: wait briefly to capture any immediately-following messages.
                await asyncio.sleep(max(0.0, DEBOUNCE_FOLLOWUP_MS / 1000.0))
                pending = self.drain_pending(phone)
                if not pending:
                    current = None
                    break
                current = _coalesce_turns(pending)
        except Exception as exc:
            logger.error("Queue: session run crashed | phone=%s | err=%s", phone, exc, exc_info=True)
        finally:
            async with self._lock:
                self._active[phone] = False
                # If pending exists after marking inactive, kick a new session run.
                pending2 = self._pending.pop(phone, [])
                if pending2:
                    self._active[phone] = True
                    asyncio.create_task(self._run_session(phone, _coalesce_turns(pending2)))

    async def _run_turn(self, turn: CoalescedTurn) -> None:
        from whatsapp.agent import run_coalesced_turn

        started = _now_s()
        logger.info(
            "Queue: run turn | phone=%s | msgs=%d | text_len=%d | media=%d",
            turn.phone,
            int(turn.message_count or 0),
            len(turn.combined_text or ""),
            len(turn.media_items or []),
        )
        await run_coalesced_turn(turn=turn, session_queue=self)
        logger.info("Queue: turn complete | phone=%s | duration=%.2fs", turn.phone, _now_s() - started)


class MessageBuffer:
    """Per-phone debounce buffer."""

    def __init__(self, session_queue: SessionQueue) -> None:
        self._session_queue = session_queue
        self._lock = asyncio.Lock()
        self._buf: Dict[str, List[BufferedMessage]] = {}
        self._timer: Dict[str, asyncio.Task[None]] = {}

    async def push(
        self,
        *,
        phone: str,
        text: str,
        media_items: Optional[List[Dict[str, Any]]] = None,
        profile_name: Optional[str] = None,
    ) -> None:
        phone = str(phone or "").strip()
        if not phone:
            raise ValueError("MessageBuffer.push() missing phone")

        msg_media = [x for x in (media_items or []) if isinstance(x, dict)]
        msg_text = str(text or "")

        # Start transcription early (best-effort) if an audio attachment includes base64_data.
        voice_future: Optional[asyncio.Task[str]] = None
        if _has_media_kind(msg_media, "audio"):
            voice_future = asyncio.create_task(_transcribe_voice_note(msg_media))

        bm = BufferedMessage(
            text=msg_text,
            media_items=msg_media,
            profile_name=profile_name,
            received_at_s=_now_s(),
            voice_future=voice_future,
        )

        flush_now = _looks_like_url(msg_text) or _has_media_kind(msg_media, "image") or _has_media_kind(msg_media, "video")

        async with self._lock:
            self._buf.setdefault(phone, []).append(bm)

            # Cancel any existing debounce timer.
            t = self._timer.pop(phone, None)
            if t is not None:
                t.cancel()

            if flush_now:
                logger.info("Buffer: flush-now | phone=%s | reason=%s", phone, "url_or_media")
                # Flush outside of the lock to avoid blocking other phones.
                asyncio.create_task(self.flush(phone=phone, reason="url_or_media"))
                return

            # Schedule debounce flush.
            self._timer[phone] = asyncio.create_task(self._debounce_wait_and_flush(phone))

    async def _debounce_wait_and_flush(self, phone: str) -> None:
        try:
            await asyncio.sleep(max(0.0, DEBOUNCE_TEXT_MS / 1000.0))
            await self.flush(phone=phone, reason="debounce")
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("Buffer: debounce timer crashed | phone=%s | err=%s", phone, exc, exc_info=True)

    async def flush(self, *, phone: str, reason: str) -> None:
        phone = str(phone or "").strip()
        if not phone:
            return

        async with self._lock:
            t = self._timer.pop(phone, None)
            if t is not None:
                t.cancel()
            msgs = self._buf.pop(phone, [])

        if not msgs:
            return

        try:
            turn = await coalesce_messages(phone, msgs)
            logger.info(
                "Buffer: flushed | phone=%s | reason=%s | msgs=%d | text_len=%d | media=%d",
                phone,
                reason,
                len(msgs),
                len(turn.combined_text or ""),
                len(turn.media_items or []),
            )
            await self._session_queue.enqueue(turn)
        except Exception as exc:
            logger.error("Buffer: flush failed | phone=%s | err=%s", phone, exc, exc_info=True)


class WhatsAppMessageQueue:
    def __init__(self) -> None:
        self.session_queue = SessionQueue()
        self.buffer = MessageBuffer(self.session_queue)

    async def push(self, *, phone: str, text: str, media_items: Optional[List[Dict[str, Any]]], profile_name: Optional[str]) -> None:
        await self.buffer.push(phone=phone, text=text, media_items=media_items, profile_name=profile_name)


_QUEUE: Optional[WhatsAppMessageQueue] = None


def get_queue() -> WhatsAppMessageQueue:
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = WhatsAppMessageQueue()
        logger.info(
            "WhatsAppMessageQueue initialised | debounce_text_ms=%d | followup_ms=%d",
            DEBOUNCE_TEXT_MS,
            DEBOUNCE_FOLLOWUP_MS,
        )
    return _QUEUE

