"""
Meta WhatsApp Cloud API — Webhook & Proxy Chat
================================================

Pure proxy: receives WhatsApp messages, stores in Supabase, serves them to the
Leo Copilot app.  App sends messages via /api/copilot/send, which forwards to
Meta Cloud API.  **No AI agent processing.**

Media files are saved to MEDIA_DIR on the Hetzner server and served via
GET /api/media/whatsapp/{filename}.

Endpoints:
  GET  /api/webhooks/meta-whatsapp          — Meta webhook verification
  POST /api/webhooks/meta-whatsapp          — Receive inbound WhatsApp messages
  GET  /api/copilot/conversations           — List conversations
  GET  /api/copilot/messages/{phone}        — Get messages for a phone
  POST /api/copilot/send                    — Send message (app → WhatsApp)
  POST /api/copilot/upload-voice            — Upload voice note, send via Meta
  GET  /api/media/whatsapp/{filename}       — Serve stored media files
"""

import asyncio
import logging
import os
import pathlib
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

import database

logger = logging.getLogger(__name__)

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

MEDIA_DIR = pathlib.Path(__file__).resolve().parent.parent / "media" / "whatsapp"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_MEDIA_BASE = (os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/") + '/api/media/whatsapp')

MIME_TO_EXT: Dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "audio/ogg": "ogg",
    "audio/ogg; codecs=opus": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


# ─── helpers ────────────────────────────────────────────────────────

def _get_token() -> str:
    return os.getenv("WHATSAPP_TOKEN", "") or WHATSAPP_TOKEN


def _get_phone_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "") or PHONE_NUMBER_ID


async def _download_meta_media(media_id: str) -> Optional[Dict[str, str]]:
    """
    Download a media file from Meta Cloud API, save it to MEDIA_DIR,
    and return {"url": public_url, "mime": mime_type, "filename": fname}.
    Returns None on any failure.
    """
    token = _get_token()
    if not token or not media_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            meta_resp = await client.get(
                f"{META_API_BASE}/{media_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if meta_resp.status_code != 200:
                logger.warning("Meta media lookup failed | id=%s | status=%s", media_id, meta_resp.status_code)
                return None

            info = meta_resp.json()
            download_url = info.get("url")
            mime_type = info.get("mime_type", "application/octet-stream")
            if not download_url:
                return None

            bin_resp = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if bin_resp.status_code != 200:
                logger.warning("Meta media download failed | id=%s | status=%s", media_id, bin_resp.status_code)
                return None

            ext = MIME_TO_EXT.get(mime_type.split(";")[0].strip(), "bin")
            fname = f"{uuid.uuid4().hex[:12]}.{ext}"
            fpath = MEDIA_DIR / fname
            fpath.write_bytes(bin_resp.content)

            public_url = f"{PUBLIC_MEDIA_BASE}/{fname}"
            logger.info(
                "Saved media | id=%s | mime=%s | size=%d bytes | file=%s",
                media_id, mime_type, len(bin_resp.content), fname,
            )
            return {"url": public_url, "mime": mime_type, "filename": fname}

    except Exception as exc:
        logger.error("Media download exception | id=%s | err=%s", media_id, exc)
        return None


async def _store_message(
    phone_number: str,
    role: str,
    text: str,
    message_type: str = "text",
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
    wa_message_id: Optional[str] = None,
    reply_to_wa_id: Optional[str] = None,
    reply_to_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a message into whatsapp_messages via Supabase REST."""
    client = await database.get_client()
    base_url = database._get_base_url()
    row: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "phone_number": phone_number,
        "role": role,
        "message_text": text,
        "message_type": message_type,
        "media_urls": media_urls or [],
        "media_types": media_types or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if wa_message_id:
        row["wa_message_id"] = wa_message_id
    if reply_to_wa_id:
        row["reply_to_wa_id"] = reply_to_wa_id
    if reply_to_text:
        row["reply_to_text"] = reply_to_text
    resp = await client.post(
        f"{base_url}/whatsapp_messages",
        json=row,
        headers={**database._get_headers(), "Prefer": "return=representation"},
    )
    if resp.status_code not in (200, 201):
        logger.error("Failed to store message | status=%s body=%s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"Supabase insert failed: {resp.status_code}")
    stored = resp.json()
    return stored[0] if isinstance(stored, list) and stored else stored


# ─── Auto-reply via CS agent ───────────────────────────────────────

async def _lookup_lead(phone: str) -> Optional[Dict[str, Any]]:
    """Look up a user in cs_leads by their WhatsApp number."""
    try:
        sb_client = await database.get_client()
        sb_base = database._get_base_url()
        clean = phone.lstrip("+").replace(" ", "").replace("-", "")
        resp = await sb_client.get(
            f"{sb_base}/cs_leads",
            params={
                "select": "name,whatsapp,location,chat_summary",
                "or": f"(whatsapp.eq.{phone},whatsapp.eq.+{clean},whatsapp.eq.{clean})",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=database._get_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                logger.info("WA lead found | phone=%s | name=%s", phone, rows[0].get("name"))
                return rows[0]
    except Exception as exc:
        logger.debug("Lead lookup failed (non-fatal) | %s", exc)
    return None


async def _auto_reply_wa(phone: str, contact_name: str, user_text: str) -> None:
    """
    Fetch full conversation history, call the CS agent, and send the
    reply back via WhatsApp. Runs as a background task so the webhook
    responds quickly to Meta.
    """
    try:
        from routes.cs_chat import _call_bedrock, _to_bedrock_msgs

        sb_client = await database.get_client()
        sb_base = database._get_base_url()

        lead = await _lookup_lead(phone)

        # Build lead context string for the system prompt (NOT as a fake user message)
        lead_context = ""
        if lead:
            context_parts = []
            if lead.get("name"):
                context_parts.append(f"name: {lead['name']}")
            if lead.get("location"):
                context_parts.append(f"location: {lead['location']}")
            if lead.get("chat_summary"):
                context_parts.append(f"prior context: {lead['chat_summary']}")
            if context_parts:
                lead_context = (
                    f"You already know this person: {'; '.join(context_parts)}. "
                    f"Don't re-ask for info you already have."
                )

        # Fetch ALL messages for this conversation (no limit)
        hist_resp = await sb_client.get(
            f"{sb_base}/whatsapp_messages",
            params={
                "phone_number": f"eq.{phone}",
                "select": "role,message_text",
                "order": "created_at.asc",
            },
            headers=database._get_headers(),
        )
        raw_msgs = []

        if hist_resp.status_code == 200:
            for row in hist_resp.json():
                role = row.get("role", "user")
                txt = row.get("message_text", "").strip()
                if txt:
                    raw_msgs.append({"role": role, "text": txt})

        # Safety net: if the user's latest message isn't at the end of
        # history (race condition or DB lag), append it explicitly
        if raw_msgs:
            last_user_msgs = [m for m in raw_msgs if m["role"] == "user"]
            if not last_user_msgs or last_user_msgs[-1]["text"] != user_text:
                raw_msgs.append({"role": "user", "text": user_text})
        else:
            raw_msgs = [{"role": "user", "text": user_text}]

        # Ensure conversation starts with user role (Bedrock requirement)
        while raw_msgs and raw_msgs[0]["role"] != "user":
            raw_msgs.pop(0)
        if not raw_msgs:
            raw_msgs = [{"role": "user", "text": user_text}]

        logger.info("WA auto-reply | phone=%s | msgs=%d | first_role=%s | last_role=%s | user_text=%s",
                     phone, len(raw_msgs), raw_msgs[0]["role"] if raw_msgs else "?",
                     raw_msgs[-1]["role"] if raw_msgs else "?", user_text[:80])

        bedrock_msgs = _to_bedrock_msgs(raw_msgs)
        if not bedrock_msgs:
            logger.warning("WA auto-reply | no valid bedrock msgs for %s | raw_count=%d", phone, len(raw_msgs))
            return

        reply = await _call_bedrock(bedrock_msgs, mode="whatsapp", raw_history=raw_msgs, lead_context=lead_context)
        if not reply:
            logger.warning("WA auto-reply | empty reply for %s", phone)
            return

        reply_clean = reply.strip()
        if len(reply_clean) > 4000:
            reply_clean = reply_clean[:4000]

        token = _get_token()
        phone_id = _get_phone_id()
        wa_to = phone.lstrip("+")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "text",
                    "text": {"body": reply_clean},
                },
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.error("WA auto-reply send failed | to=%s | status=%s | body=%s", phone, resp.status_code, result)
                return

            sent_wa_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("WA auto-reply sent | to=%s | wamid=%s | text=%s", phone, sent_wa_id, reply_clean[:80])

        await _store_message(
            phone_number=phone,
            role="assistant",
            text=reply_clean,
            wa_message_id=sent_wa_id,
        )

    except Exception as exc:
        logger.error("WA auto-reply failed | phone=%s | err=%s", phone, exc, exc_info=True)


# ─── Webhook verification (GET) ────────────────────────────────────

@router.get("/api/webhooks/meta-whatsapp")
async def meta_whatsapp_verify(
    request: Request,
) -> PlainTextResponse:
    """
    Meta sends a GET with hub.mode, hub.verify_token, hub.challenge.
    We echo back hub.challenge if the token matches.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Meta webhook verified")
        return PlainTextResponse(challenge, status_code=200)

    logger.warning("Meta webhook verification failed | mode=%s token_match=%s", mode, token == VERIFY_TOKEN)
    return PlainTextResponse("Forbidden", status_code=403)


# ─── Webhook receiver (POST) ───────────────────────────────────────

@router.post("/api/webhooks/meta-whatsapp")
async def meta_whatsapp_webhook(request: Request) -> JSONResponse:
    """
    Receive inbound WhatsApp messages from Meta Cloud API.
    Store in Supabase.  No AI processing — pure proxy.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    entry_list = payload.get("entry", [])
    for entry in entry_list:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Log status updates for debugging delivery issues
            statuses = value.get("statuses", [])
            if statuses:
                for st in statuses:
                    sid = st.get("id", "?")
                    status_val = st.get("status", "?")
                    recip = st.get("recipient_id", "?")
                    errors = st.get("errors", [])
                    err_str = f" | errors={errors}" if errors else ""
                    logger.info(
                        "Meta status update | wamid=%s | status=%s | recipient=%s%s",
                        sid, status_val, recip, err_str,
                    )

            if "messages" not in value:
                continue

            contacts = value.get("contacts", [])
            contact_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"
            messages = value.get("messages", [])

            for msg in messages:
                from_number = msg.get("from", "")
                msg_type = msg.get("type", "text")
                wa_msg_id = msg.get("id", "")

                if not from_number:
                    continue

                phone = f"+{from_number}" if not from_number.startswith("+") else from_number

                # Extract reply context if this message is replying to another
                context = msg.get("context", {})
                reply_to_wa_id = context.get("id") if context else None

                text = ""
                media_urls: List[str] = []
                media_types: List[str] = []

                # --- Extract media_id and text for each type ---
                media_id: Optional[str] = None

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")

                elif msg_type == "image":
                    media_id = msg.get("image", {}).get("id")
                    text = msg.get("image", {}).get("caption", "") or ""

                elif msg_type == "sticker":
                    media_id = msg.get("sticker", {}).get("id")

                elif msg_type == "video":
                    media_id = msg.get("video", {}).get("id")
                    text = msg.get("video", {}).get("caption", "") or ""

                elif msg_type == "audio":
                    media_id = msg.get("audio", {}).get("id")

                elif msg_type == "document":
                    media_id = msg.get("document", {}).get("id")
                    text = msg.get("document", {}).get("filename", "") or ""

                elif msg_type == "reaction":
                    text = msg.get("reaction", {}).get("emoji", "")

                elif msg_type == "button":
                    text = msg.get("button", {}).get("text", "")

                elif msg_type == "location":
                    loc = msg.get("location", {})
                    text = f"📍 {loc.get('name', 'Location')} ({loc.get('latitude', '')}, {loc.get('longitude', '')})"

                elif msg_type == "contacts":
                    c_list = msg.get("contacts", [])
                    names = [c.get("name", {}).get("formatted_name", "?") for c in c_list]
                    text = f"👤 {', '.join(names)}"

                else:
                    text = f"[{msg_type}]"

                # --- Download media if present ---
                if media_id:
                    result = await _download_meta_media(media_id)
                    if result:
                        media_urls.append(result["url"])
                        media_types.append(result["mime"])
                    if not text:
                        friendly = {"image": "📷 Photo", "sticker": "🎨 Sticker", "video": "🎥 Video",
                                    "audio": "🎤 Voice note", "document": "📎 Document"}
                        text = friendly.get(msg_type, f"[{msg_type}]")

                logger.info(
                    "Meta WhatsApp inbound | from=%s | name=%s | type=%s | media=%d | text=%s",
                    phone, contact_name, msg_type, len(media_urls), text[:80],
                )

                # Look up the text of the message being replied to
                reply_to_text_val = None
                if reply_to_wa_id:
                    try:
                        sb_client = await database.get_client()
                        sb_base = database._get_base_url()
                        rp_resp = await sb_client.get(
                            f"{sb_base}/whatsapp_messages",
                            params={
                                "wa_message_id": f"eq.{reply_to_wa_id}",
                                "select": "message_text",
                                "limit": "1",
                            },
                            headers=database._get_headers(),
                        )
                        if rp_resp.status_code == 200:
                            rp_rows = rp_resp.json()
                            if rp_rows:
                                reply_to_text_val = rp_rows[0].get("message_text", "")
                    except Exception as rp_exc:
                        logger.debug("Reply-to lookup failed (non-fatal) | %s", rp_exc)

                try:
                    await _store_message(
                        phone_number=phone,
                        role="user",
                        text=text,
                        message_type=msg_type,
                        media_urls=media_urls,
                        media_types=media_types,
                        wa_message_id=wa_msg_id,
                        reply_to_wa_id=reply_to_wa_id,
                        reply_to_text=reply_to_text_val,
                    )

                    if contact_name and contact_name != "Unknown":
                        try:
                            client = await database.get_client()
                            base_url = database._get_base_url()
                            await client.post(
                                f"{base_url}/whatsapp_user_profiles",
                                json={
                                    "phone_number": phone,
                                    "display_name": contact_name,
                                },
                                headers={
                                    **database._get_headers(),
                                    "Prefer": "resolution=merge-duplicates",
                                },
                            )
                        except Exception as exc:
                            logger.debug("Profile upsert failed (non-fatal) | %s", exc)

                    asyncio.create_task(_auto_reply_wa(phone, contact_name, text))

                except Exception as exc:
                    logger.error("Failed to store inbound message | from=%s | err=%s", phone, exc)

    return JSONResponse({"status": "ok"}, status_code=200)


# ─── Read conversations ────────────────────────────────────────────

@router.get("/api/copilot/conversations")
async def list_conversations() -> JSONResponse:
    """
    List distinct phone numbers with their most recent message + display name.
    """
    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/rpc/copilot_conversations",
        headers=database._get_headers(),
    )

    if resp.status_code != 200:
        # Fallback: raw distinct query
        resp2 = await client.get(
            f"{base_url}/whatsapp_messages",
            params={
                "select": "phone_number,message_text,role,created_at",
                "order": "created_at.desc",
                "limit": "100",
            },
            headers=database._get_headers(),
        )
        if resp2.status_code != 200:
            return JSONResponse({"error": "failed to fetch"}, status_code=500)

        rows = resp2.json() or []
        seen = {}
        for r in rows:
            pn = r.get("phone_number", "")
            if pn not in seen:
                seen[pn] = {
                    "phone_number": pn,
                    "last_message": r.get("message_text", ""),
                    "last_role": r.get("role", ""),
                    "last_at": r.get("created_at", ""),
                    "display_name": None,
                }
        return JSONResponse(list(seen.values()))

    return JSONResponse(resp.json())


# ─── Read messages for a phone ─────────────────────────────────────

@router.get("/api/copilot/messages/{phone}")
async def get_messages(
    phone: str,
    limit: int = Query(default=50, le=200),
    after: Optional[str] = Query(default=None),
) -> JSONResponse:
    """
    Get messages for a specific phone number, ordered by time.
    Pass `after` (ISO timestamp) for polling new messages.
    """
    clean_phone = phone if phone.startswith("+") else f"+{phone}"
    client = await database.get_client()
    base_url = database._get_base_url()

    params: Dict[str, str] = {
        "phone_number": f"eq.{clean_phone}",
        "select": "id,phone_number,role,message_text,message_type,media_urls,media_types,created_at,wa_message_id,reply_to_wa_id,reply_to_text",
        "order": "created_at.asc",
        "limit": str(limit),
    }
    if after:
        params["created_at"] = f"gt.{after}"

    resp = await client.get(
        f"{base_url}/whatsapp_messages",
        params=params,
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        return JSONResponse({"error": "failed to fetch"}, status_code=500)

    return JSONResponse(resp.json())


# ─── Send message from app ─────────────────────────────────────────

@router.post("/api/copilot/send")
async def send_message(request: Request) -> JSONResponse:
    """
    Send a WhatsApp message from the Leo Copilot app.

    Body: { "to": "+12025550102", "text": "Hello from Leo!" }

    Stores in Supabase as role='assistant' then sends via Meta Cloud API.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    to = str(body.get("to", "")).strip()
    text = str(body.get("text", "")).strip()
    reply_to = str(body.get("reply_to", "")).strip() or None

    if not to or not text:
        return JSONResponse({"error": "to and text required"}, status_code=400)

    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    # Send via Meta Cloud API first so we get the wa_message_id
    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        logger.error("Meta Cloud API credentials missing | token=%s phone_id=%s", bool(token), bool(phone_id))
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    meta_payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": wa_to,
        "type": "text",
        "text": {"body": text},
    }
    if reply_to:
        meta_payload["context"] = {"message_id": reply_to}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=meta_payload,
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.error("Meta send failed | status=%s body=%s", resp.status_code, result)
                return JSONResponse({
                    "error": "Meta API error",
                    "detail": result,
                }, status_code=502)

            sent_wa_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("Meta WhatsApp sent | to=%s | text=%s | wamid=%s",
                        clean_to, text[:50], sent_wa_id)

    except Exception as exc:
        logger.error("Meta send exception | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    # Look up the text of the message being replied to for display
    reply_to_text_val = None
    if reply_to:
        try:
            sb_client = await database.get_client()
            sb_base = database._get_base_url()
            rp_resp = await sb_client.get(
                f"{sb_base}/whatsapp_messages",
                params={
                    "wa_message_id": f"eq.{reply_to}",
                    "select": "message_text",
                    "limit": "1",
                },
                headers=database._get_headers(),
            )
            if rp_resp.status_code == 200:
                rp_rows = rp_resp.json()
                if rp_rows:
                    reply_to_text_val = rp_rows[0].get("message_text", "")
        except Exception:
            pass

    # Store in Supabase with wa_message_id and reply context
    try:
        stored = await _store_message(
            phone_number=clean_to,
            role="assistant",
            text=text,
            wa_message_id=sent_wa_id,
            reply_to_wa_id=reply_to,
            reply_to_text=reply_to_text_val,
        )
    except Exception as exc:
        logger.error("Failed to store outbound message | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"ok": True, "stored": False, "wa_message_id": sent_wa_id})

    return JSONResponse({
        "ok": True,
        "message_id": stored.get("id") if isinstance(stored, dict) else None,
        "wa_message_id": sent_wa_id,
    })


# ─── Send template message ─────────────────────────────────────────

@router.post("/api/copilot/send-template")
async def send_template(request: Request) -> JSONResponse:
    """
    Send a WhatsApp template message to initiate a conversation.

    Body: { "to": "+12025550102", "template": "hello_world" }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    to = str(body.get("to", "")).strip()
    template_name = str(body.get("template", "hello_world")).strip()
    language = str(body.get("language", "en_US")).strip()

    if not to:
        return JSONResponse({"error": "to required"}, status_code=400)

    wa_to = to.lstrip("+")
    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": language},
                    },
                },
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.error("Template send failed | status=%s body=%s", resp.status_code, result)
                return JSONResponse({"error": "Meta API error", "detail": result}, status_code=502)

    except Exception as exc:
        logger.error("Template send exception | to=%s | err=%s", to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    # Store the template send as an outbound message
    try:
        await _store_message(
            phone_number=to if to.startswith("+") else f"+{to}",
            role="assistant",
            text=f"[Template: {template_name}]",
            message_type="template",
        )
    except Exception as exc:
        logger.warning("Failed to store template message (non-fatal) | %s", exc)

    return JSONResponse({
        "ok": True,
        "wa_message_id": result.get("messages", [{}])[0].get("id", ""),
    })


# ─── Serve media files from disk ──────────────────────────────────

@router.get("/api/media/whatsapp/{filename}")
async def serve_media(filename: str):
    """Serve a media file that was downloaded from Meta."""
    safe_name = pathlib.Path(filename).name
    fpath = MEDIA_DIR / safe_name
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(fpath, headers={"Cache-Control": "public, max-age=31536000"})


# ─── Upload & send voice note from app ────────────────────────────

@router.post("/api/copilot/upload-voice")
async def upload_voice(
    to: str = Form(...),
    audio: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a voice note from the Leo Copilot app, save to disk, convert
    to OGG Opus (WhatsApp requirement), send via Meta Cloud API, and
    store in Supabase.
    """
    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        return JSONResponse({"error": "empty audio"}, status_code=400)

    uid = uuid.uuid4().hex[:12]
    raw_fname = f"voice_raw_{uid}.webm"
    raw_path = MEDIA_DIR / raw_fname
    raw_path.write_bytes(audio_bytes)

    # Convert WebM -> OGG Opus (mono 48kHz, speech-optimized for WhatsApp PTT)
    ogg_fname = f"voice_{uid}.ogg"
    ogg_path = MEDIA_DIR / ogg_fname
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(raw_path),
            "-ar", "48000", "-ac", "1",
            "-c:a", "libopus", "-b:a", "128k",
            "-application", "voip",
            "-f", "ogg", str(ogg_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            logger.error("ffmpeg convert failed | rc=%s | stderr=%s", proc.returncode, stderr_data.decode()[:300])
            return JSONResponse({"error": "Audio conversion failed"}, status_code=500)
    except asyncio.TimeoutError:
        logger.error("ffmpeg conversion timed out")
        return JSONResponse({"error": "Audio conversion timed out"}, status_code=500)

    ogg_bytes = ogg_path.read_bytes()
    public_url = f"{PUBLIC_MEDIA_BASE}/{ogg_fname}"

    logger.info(
        "Voice upload | to=%s | raw=%d bytes | ogg=%d bytes | file=%s",
        clean_to, len(audio_bytes), len(ogg_bytes), ogg_fname,
    )

    token = _get_token()
    phone_id = _get_phone_id()
    sent_wa_id = ""

    if not token or not phone_id:
        logger.error("Meta Cloud API credentials missing for voice upload")
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            upload_resp = await client.post(
                f"{META_API_BASE}/{phone_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (ogg_fname, ogg_bytes, "audio/ogg; codecs=opus")},
                data={"messaging_product": "whatsapp", "type": "audio/ogg; codecs=opus"},
            )
            if upload_resp.status_code not in (200, 201):
                logger.error("Meta voice upload failed | status=%s body=%s", upload_resp.status_code, upload_resp.text[:300])
                return JSONResponse({"error": "Meta voice upload failed", "detail": upload_resp.json()}, status_code=502)

            wa_media_id = upload_resp.json().get("id")
            if not wa_media_id:
                return JSONResponse({"error": "No media ID from Meta"}, status_code=502)

            send_resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "audio",
                    "audio": {"id": wa_media_id},
                },
            )
            result = send_resp.json()
            if send_resp.status_code not in (200, 201):
                logger.error("Meta voice send failed | status=%s body=%s", send_resp.status_code, result)
                return JSONResponse({"error": "Meta voice send failed", "detail": result}, status_code=502)

            sent_wa_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("Meta voice sent | to=%s | wamid=%s", clean_to, sent_wa_id)

    except Exception as exc:
        logger.error("Voice send exception | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    try:
        await _store_message(
            phone_number=clean_to,
            role="assistant",
            text="🎤 Voice note",
            message_type="audio",
            media_urls=[public_url],
            media_types=["audio/ogg"],
            wa_message_id=sent_wa_id,
        )
    except Exception as exc:
        logger.error("Failed to store voice message | to=%s | err=%s", clean_to, exc)

    return JSONResponse({"ok": True, "url": public_url, "wa_message_id": sent_wa_id})


# ─── Upload & send media (image/document) from app ────────────────

UPLOAD_MIME_TO_WA_TYPE = {
    "image/jpeg": "image", "image/png": "image", "image/webp": "image",
    "image/gif": "image", "video/mp4": "video", "video/3gpp": "video",
    "audio/ogg": "audio", "audio/mpeg": "audio", "audio/mp4": "audio",
    "application/pdf": "document", "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
}


@router.post("/api/copilot/upload-media")
async def upload_media(
    to: str = Form(...),
    media: UploadFile = File(...),
    caption: Optional[str] = Form(default=None),
) -> JSONResponse:
    """
    Upload any media from the Leo Copilot app, save to disk, send via
    Meta Cloud API, and store in Supabase.
    """
    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    media_bytes = await media.read()
    if len(media_bytes) == 0:
        return JSONResponse({"error": "empty file"}, status_code=400)

    content_type = media.content_type or "application/octet-stream"
    wa_type = UPLOAD_MIME_TO_WA_TYPE.get(content_type, "document")
    ext = MIME_TO_EXT.get(content_type.split(";")[0].strip(), "bin")
    fname = f"upload_{uuid.uuid4().hex[:12]}.{ext}"
    fpath = MEDIA_DIR / fname
    fpath.write_bytes(media_bytes)
    public_url = f"{PUBLIC_MEDIA_BASE}/{fname}"

    logger.info(
        "Media upload | to=%s | type=%s | mime=%s | size=%d bytes | file=%s",
        clean_to, wa_type, content_type, len(media_bytes), fname,
    )

    token = _get_token()
    phone_id = _get_phone_id()
    sent_wa_id = ""

    if token and phone_id:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                upload_resp = await client.post(
                    f"{META_API_BASE}/{phone_id}/media",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": (media.filename or fname, media_bytes, content_type)},
                    data={"messaging_product": "whatsapp", "type": content_type},
                )
                if upload_resp.status_code not in (200, 201):
                    logger.error("Meta media upload failed | status=%s body=%s",
                                 upload_resp.status_code, upload_resp.text[:300])
                    return JSONResponse({"error": "Meta upload failed"}, status_code=502)

                wa_media_id = upload_resp.json().get("id")
                if not wa_media_id:
                    return JSONResponse({"error": "No media ID from Meta"}, status_code=502)

                msg_payload: Dict[str, Any] = {
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": wa_type,
                    wa_type: {"id": wa_media_id},
                }
                if caption and wa_type in ("image", "video", "document"):
                    msg_payload[wa_type]["caption"] = caption
                if wa_type == "document" and media.filename:
                    msg_payload[wa_type]["filename"] = media.filename

                send_resp = await client.post(
                    f"{META_API_BASE}/{phone_id}/messages",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=msg_payload,
                )
                result = send_resp.json()
                if send_resp.status_code not in (200, 201):
                    logger.error("Meta media send failed | status=%s body=%s",
                                 send_resp.status_code, result)
                    return JSONResponse({"error": "Meta send failed", "detail": result}, status_code=502)

                sent_wa_id = result.get("messages", [{}])[0].get("id", "")

        except Exception as exc:
            logger.error("Media send exception | to=%s | err=%s", clean_to, exc)
            return JSONResponse({"error": str(exc)}, status_code=502)

    friendly = {"image": "📷 Photo", "video": "🎥 Video", "document": "📎 Document", "audio": "🎤 Audio"}
    display_text = caption or friendly.get(wa_type, f"[{wa_type}]")

    try:
        await _store_message(
            phone_number=clean_to,
            role="assistant",
            text=display_text,
            message_type=wa_type,
            media_urls=[public_url],
            media_types=[content_type],
            wa_message_id=sent_wa_id,
        )
    except Exception as exc:
        logger.error("Failed to store media message | to=%s | err=%s", clean_to, exc)

    return JSONResponse({"ok": True, "url": public_url, "wa_message_id": sent_wa_id})
