"""
Twilio WhatsApp Client
======================

Thin wrapper around the Twilio REST API for sending WhatsApp messages.
Supports plain text and media (images) messages.

WHY THIS MATTERS: This is the only module that talks to Twilio. Everything
else in the WhatsApp agent uses this client, so swapping providers later
(e.g. Meta Cloud API) means changing only this file.
"""

import logging
from typing import List, Optional

from twilio.rest import Client as TwilioClient

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton — only created when first message is sent
# ---------------------------------------------------------------------------
_client: Optional[TwilioClient] = None


def _get_client() -> TwilioClient:
    """Return a cached Twilio client, creating it on first call."""
    global _client
    if _client is None:
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise RuntimeError(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env.local"
            )
        _client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialised | sid=%s...", settings.TWILIO_ACCOUNT_SID[:8])
    return _client


def _get_from_number() -> str:
    """Return the configured WhatsApp sender number."""
    if not settings.TWILIO_WHATSAPP_FROM:
        raise RuntimeError(
            "TWILIO_WHATSAPP_FROM not configured. "
            "Set it to the Twilio sandbox number, e.g. whatsapp:+12025550100"
        )
    return settings.TWILIO_WHATSAPP_FROM


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_text(to: str, body: str) -> str:
    """
    Send a plain-text WhatsApp message.

    Args:
        to:   Recipient in Twilio format, e.g. "whatsapp:+12025550101"
        body: Message text (Twilio WhatsApp enforces ~1600 chars)

    Returns:
        Twilio message SID
    """
    client = _get_client()
    from_number = _get_from_number()

    logger.info("WhatsApp send_text | to=%s | len=%d", to, len(body))

    message = client.messages.create(
        from_=from_number,
        to=to,
        body=body,
    )

    logger.info("WhatsApp sent | sid=%s | status=%s", message.sid, message.status)
    return message.sid


def send_media(to: str, body: str, media_urls: List[str]) -> str:
    """
    Send a WhatsApp message with media attachments (images).

    Args:
        to:         Recipient in Twilio format
        body:       Caption text
        media_urls: List of publicly-accessible image URLs (max 10 per message)

    Returns:
        Twilio message SID
    """
    client = _get_client()
    from_number = _get_from_number()

    logger.info(
        "WhatsApp send_media | to=%s | media_count=%d | len=%d",
        to, len(media_urls), len(body),
    )

    message = client.messages.create(
        from_=from_number,
        to=to,
        body=body,
        media_url=media_urls,
    )

    logger.info("WhatsApp media sent | sid=%s | status=%s", message.sid, message.status)
    return message.sid


def _split_for_whatsapp(text: str, *, max_chars: int = 1500) -> List[str]:
    """
    Split a long text into WhatsApp-sized chunks.

    WHY THIS MATTERS:
    - Twilio WhatsApp has a practical body limit (~1600 chars).
    - Splitting at natural boundaries avoids mid-sentence cut-offs.
    """
    s = (text or "").strip()
    if not s:
        return [""]
    if len(s) <= max_chars:
        return [s]

    # Prefer paragraph boundaries.
    chunks: List[str] = []
    current = ""
    for para in s.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if not current:
            current = p
            continue
        if len(current) + 2 + len(p) <= max_chars:
            current = current + "\n\n" + p
            continue
        chunks.append(current.strip())
        current = p
    if current.strip():
        chunks.append(current.strip())

    # Safety fallback: if a single paragraph is too long, hard-slice.
    final: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
            continue
        start = 0
        while start < len(c):
            final.append(c[start : start + max_chars].strip())
            start += max_chars
    return [x for x in final if x] or [s[:max_chars]]


def send_long_text(to: str, body: str, *, max_chars: int = 1500) -> List[str]:
    """
    Send a long WhatsApp message by splitting into multiple texts.

    Returns a list of Twilio message SIDs.
    """
    parts = _split_for_whatsapp(body, max_chars=max_chars)
    sids: List[str] = []
    for p in parts:
        sid = send_text(to=to, body=p)
        sids.append(sid)
    return sids


async def send_text_async(to: str, body: str) -> str:
    """Async wrapper for send_text() (runs in a thread)."""
    import asyncio

    return await asyncio.to_thread(send_text, to, body)


async def send_long_text_async(to: str, body: str, *, max_chars: int = 1500, delay_s: float = 0.3) -> List[str]:
    """
    Async wrapper for send_long_text(), sending chunks in order.

    delay_s is a small pacing delay to reduce out-of-order delivery in WhatsApp clients.
    """
    import asyncio

    parts = _split_for_whatsapp(body, max_chars=max_chars)
    sids: List[str] = []
    for idx, p in enumerate(parts):
        sid = await asyncio.to_thread(send_text, to, p)
        sids.append(sid)
        if idx < len(parts) - 1 and delay_s > 0:
            await asyncio.sleep(delay_s)
    return sids
