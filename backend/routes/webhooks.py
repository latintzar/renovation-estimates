"""
Webhook Routes
==============

External webhook endpoints for third-party integrations.

Currently:
  - POST /api/webhooks/twilio-whatsapp  — Twilio WhatsApp inbound messages
  - GET  /api/listings/{id}/generated-images/{index} — Serve generated room images
    (used by Twilio to fetch media when sending WhatsApp image messages)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import JSONResponse

import database
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# TWILIO WHATSAPP WEBHOOK
# =============================================================================

@router.post("/api/webhooks/twilio-whatsapp")
async def twilio_whatsapp_webhook(
    request: Request,
    From: str = Form(default=""),
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    ProfileName: str = Form(default=""),
    WaId: str = Form(default=""),
    MessageSid: str = Form(default=""),
) -> Response:
    """
    Receive inbound WhatsApp messages from Twilio.

    Twilio sends a POST with form-encoded data:
      - From:        Sender number (e.g. "whatsapp:+12025550101")
      - Body:        Message text
      - NumMedia:    Number of media attachments
      - ProfileName: WhatsApp profile name of sender
      - WaId:        WhatsApp ID of sender

    We reply with an empty TwiML response because we send replies
    asynchronously via the Twilio REST API (not via TwiML).
    """
    logger.info(
        "WhatsApp webhook | from=%s | profile=%s | body=%s | media=%s",
        From, ProfileName, Body[:100], NumMedia,
    )

    if not From:
        logger.warning("WhatsApp webhook: missing From")
        return _empty_twiml()

    try:
        import httpx
        from config import settings

        # Twilio media fields (MediaUrl0, MediaContentType0, ...) aren't declared as FastAPI params
        # because the count is dynamic. Pull from the raw form instead.
        form = await request.form()
        try:
            num_media = int(str(form.get("NumMedia") or NumMedia or "0"))
        except Exception:
            num_media = 0

        media_items: List[Dict[str, Any]] = []
        if num_media > 0:
            # Process only a few items inline so we don't blow webhook latency.
            # Remaining items are still forwarded to the agent as Twilio URLs.
            PROCESS_LIMIT = 3
            from datetime import datetime, timezone
            import hashlib

            from whatsapp.media import (
                download_twilio_media,
                classify_media,
                extract_video_thumbnail,
                persist_twilio_media,
                upload_to_storage,
            )

            for i in range(min(num_media, 10)):
                twilio_url = str(form.get(f"MediaUrl{i}") or "").strip()
                content_type = str(form.get(f"MediaContentType{i}") or "").strip()
                if not twilio_url or not content_type:
                    continue

                item: Dict[str, Any] = {
                    "twilio_url": twilio_url,
                    "content_type": content_type,
                    "index": i,
                }

                if len(media_items) < PROCESS_LIMIT:
                    try:
                        kind = classify_media(content_type)
                        if kind == "video":
                            video_bytes = await download_twilio_media(
                                url=twilio_url,
                                max_bytes=20 * 1024 * 1024,
                                timeout_s=30,
                            )
                            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                            sha_v = hashlib.sha256(video_bytes).hexdigest()[:12]
                            # Filename uses "unknown listing" because webhook doesn't know listing_id yet.
                            video_filename = f"listing-unknown/{From.replace(':','_')}/{ts}_{sha_v}.mp4"
                            video_url = await upload_to_storage(
                                data=video_bytes,
                                content_type=content_type,
                                filename=video_filename,
                                bucket="whatsapp-media",
                                upsert=True,
                            )

                            thumb_bytes = extract_video_thumbnail(video_bytes)
                            sha_t = hashlib.sha256(thumb_bytes).hexdigest()[:12]
                            thumb_filename = f"listing-unknown/{From.replace(':','_')}/{ts}_{sha_t}.jpg"
                            thumb_url = await upload_to_storage(
                                data=thumb_bytes,
                                content_type="image/jpeg",
                                filename=thumb_filename,
                                bucket="whatsapp-media",
                                upsert=True,
                            )

                            item.update(
                                {
                                    "media_kind": "video",
                                    "public_url": video_url,
                                    "thumbnail_url": thumb_url,
                                }
                            )
                        else:
                            public_url, _ct, _kind, b64 = await persist_twilio_media(
                                phone_number=From,
                                twilio_url=twilio_url,
                                content_type=content_type,
                                listing_id=None,
                                max_bytes=20 * 1024 * 1024,
                                max_base64_bytes=6 * 1024 * 1024,
                            )
                            item.update(
                                {
                                    "public_url": public_url,
                                    "media_kind": _kind,
                                    "base64_data": b64,
                                }
                            )
                    except Exception as exc:
                        logger.warning(
                            "WhatsApp webhook: failed to persist media | from=%s | idx=%s | %s: %s",
                            From,
                            i,
                            type(exc).__name__,
                            exc,
                        )
                        item["error"] = f"{type(exc).__name__}: {str(exc)}"
                else:
                    item["deferred"] = True

                media_items.append(item)

        # Typing indicator (Twilio WhatsApp public beta).
        # WHY THIS MATTERS: for AI responses that take a few seconds, WhatsApp users
        # expect a typing bubble; this reduces perceived latency.
        #
        # Docs: https://www.twilio.com/docs/whatsapp/api/typing-indicators-resource
        msg_sid = (str(form.get("MessageSid") or MessageSid or "").strip())
        if msg_sid and (msg_sid.startswith("SM") or msg_sid.startswith("MM")):
            try:
                # Only send typing when we expect non-trivial work (media, url, or longer text).
                # Avoid spamming typing indicators for quick one-word messages.
                should_type = bool(media_items) or ("http" in (Body or "").lower()) or (len((Body or "").strip()) >= 60)
                if should_type and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                    async with httpx.AsyncClient(timeout=5) as client:
                        await client.post(
                            "https://messaging.twilio.com/v2/Indicators/Typing.json",
                            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                            data={"messageId": msg_sid, "channel": "whatsapp"},
                        )
            except Exception as exc:
                logger.debug("Typing indicator failed (non-fatal) | sid=%s | %s", msg_sid, exc)

        # Ignore empty pings (no text, no media)
        if not (Body or "").strip() and not media_items:
            return _empty_twiml()

        # Enqueue the inbound message and return immediately.
        # WHY THIS MATTERS: Twilio webhooks have tight timeouts. We handle the actual
        # agent run (Gemini calls, scraping, etc.) asynchronously in-process.
        from whatsapp.message_queue import get_queue

        queue = get_queue()
        await queue.push(
            phone=From,
            text=Body or "",
            media_items=media_items or None,
            profile_name=(ProfileName or None),
        )

    except Exception as exc:
        logger.error("WhatsApp webhook error | from=%s | error=%s", From, exc, exc_info=True)
        # Best-effort error reply
        try:
            from whatsapp.twilio_client import send_text
            send_text(
                to=From,
                body="Sorry, something went wrong processing your request. Please try again in a few minutes.",
            )
        except Exception:
            logger.error("WhatsApp error reply also failed | from=%s", From)

    # Always return empty TwiML — we reply asynchronously via REST API
    return _empty_twiml()


def _empty_twiml() -> Response:
    """Return an empty TwiML response (tells Twilio we handled the webhook)."""
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
        status_code=200,
    )


# =============================================================================
# RESEND INBOUND EMAIL WEBHOOK
# =============================================================================

def _b64decode_secret(secret: str) -> bytes:
    # Svix signing secret format: whsec_<base64>
    s = (secret or "").strip()
    if s.startswith("whsec_"):
        s = s[len("whsec_") :]
    # Add missing padding if needed.
    pad = "=" * (-len(s) % 4)
    return base64.b64decode(s + pad)


def _parse_svix_signatures(signature_header: str) -> List[str]:
    """
    Extract all v1 signatures from the svix-signature header.

    Header looks like:
      "v1,BASE64SIG" or "v1,BASE64SIG v1,BASE64SIG2"
    """
    out: List[str] = []
    s = (signature_header or "").strip()
    if not s:
        return out
    parts = [p for p in s.split() if p.strip()]
    for p in parts:
        if "," not in p:
            continue
        ver, sig = p.split(",", 1)
        if ver.strip() == "v1" and sig.strip():
            out.append(sig.strip())
    return out


def _verify_resend_webhook(*, raw_body: bytes, headers: Dict[str, str]) -> bool:
    """
    Verify Resend webhook signature (Svix compatible).

    WHY THIS MATTERS: Resend webhooks must be authenticated to prevent attackers
    from spoofing inbound "email received" events.
    """
    secret = str(settings.RESEND_WEBHOOK_SECRET or "").strip()
    if not secret:
        logger.error("Resend webhook secret missing (RESEND_WEBHOOK_SECRET)")
        return False

    svix_id = str(headers.get("svix-id") or "").strip()
    svix_ts = str(headers.get("svix-timestamp") or "").strip()
    svix_sig = str(headers.get("svix-signature") or "").strip()
    if not svix_id or not svix_ts or not svix_sig:
        logger.warning("Resend webhook missing Svix headers | id=%s ts=%s sig=%s", bool(svix_id), bool(svix_ts), bool(svix_sig))
        return False

    try:
        ts_int = int(svix_ts)
    except Exception:
        logger.warning("Resend webhook invalid svix-timestamp: %r", svix_ts)
        return False

    tolerance_s = int(os.getenv("RESEND_WEBHOOK_TOLERANCE_SECONDS", "300"))
    now = int(time.time())
    if abs(now - ts_int) > max(30, tolerance_s):
        logger.warning("Resend webhook timestamp outside tolerance | now=%s ts=%s tol=%s", now, ts_int, tolerance_s)
        return False

    try:
        key = _b64decode_secret(secret)
    except Exception as exc:
        logger.error("Resend webhook secret decode failed | err=%s", exc)
        return False

    try:
        payload_text = raw_body.decode("utf-8")
    except Exception as exc:
        logger.warning("Resend webhook body decode failed | err=%s", exc)
        return False

    signed = f"{svix_id}.{svix_ts}.{payload_text}".encode("utf-8")
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")

    candidates = _parse_svix_signatures(svix_sig)
    return any(hmac.compare_digest(expected, cand) for cand in candidates)


def _extract_project_id_from_to(to_addrs: Any) -> str:
    # Expected: ["project-<id>@projects.leo.casa", ...]
    items: List[str] = []
    if isinstance(to_addrs, list):
        items = [str(x or "").strip() for x in to_addrs]
    elif isinstance(to_addrs, str):
        items = [to_addrs.strip()]
    for addr in items:
        a = addr.lower()
        if not a.startswith("project-") or "@" not in a:
            continue
        local = a.split("@", 1)[0]
        return local.replace("project-", "", 1).strip()
    return ""


def _extract_email_address(from_field: str) -> str:
    s = str(from_field or "").strip()
    if "<" in s and ">" in s:
        return s.split("<", 1)[1].split(">", 1)[0].strip()
    return s


@router.post("/api/webhooks/resend")
async def resend_webhook(request: Request) -> Response:
    """
    Resend inbound MX webhook endpoint.

    Expects Svix headers:
      - svix-id
      - svix-timestamp
      - svix-signature
    """
    raw = await request.body()
    hdrs = {k.lower(): v for k, v in dict(request.headers or {}).items()}

    if not _verify_resend_webhook(raw_body=raw, headers=hdrs):
        return JSONResponse({"ok": False, "error": "invalid signature"}, status_code=400)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        logger.warning("Resend webhook invalid JSON | err=%s", exc)
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    event_type = str(payload.get("type") or "").strip()
    if event_type != "email.received":
        # Acknowledge other events (delivered/bounced/etc) without side effects.
        return JSONResponse({"ok": True, "ignored": True, "type": event_type}, status_code=200)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    from_field = str(data.get("from") or "").strip()
    to_field = data.get("to")
    subject = str(data.get("subject") or "").strip()
    body_text = str(data.get("text") or "").strip()
    attachments = data.get("attachments") if isinstance(data.get("attachments"), list) else []

    project_id = _extract_project_id_from_to(to_field)
    if not project_id:
        logger.warning("Resend webhook: could not extract project_id | to=%r", to_field)
        return JSONResponse({"ok": True, "ignored": True, "reason": "no_project_id"}, status_code=200)

    # Look up project → user phone.
    client = await database.get_client()
    base_url = database._get_base_url()
    proj_resp = await client.get(
        f"{base_url}/leo_projects",
        params={"id": f"eq.{project_id}", "select": "id,phone_number,name,status"},
        headers=database._get_headers(),
    )
    if proj_resp.status_code != 200:
        logger.error("Resend webhook: leo_projects lookup failed | status=%s body=%s", proj_resp.status_code, proj_resp.text[:300])
        return JSONResponse({"ok": False, "error": "project lookup failed"}, status_code=500)
    proj_rows = proj_resp.json() or []
    project = proj_rows[0] if isinstance(proj_rows, list) and proj_rows else None
    if not isinstance(project, dict) or not project.get("phone_number"):
        return JSONResponse({"ok": True, "ignored": True, "reason": "project_not_found"}, status_code=200)

    user_phone = str(project.get("phone_number") or "").strip()

    # Update tradesperson outreach_status to replied (best-effort match by email).
    sender_email = _extract_email_address(from_field).lower()
    if sender_email:
        try:
            patch_resp = await client.patch(
                f"{base_url}/leo_tradespeople",
                params={
                    "project_id": f"eq.{project_id}",
                    "email": f"ilike.{sender_email}",
                },
                json={"outreach_status": "replied"},
                headers=database._get_headers(),
            )
            if patch_resp.status_code not in (200, 204):
                logger.warning(
                    "Resend webhook: tradespeople patch failed (non-fatal) | status=%s body=%s",
                    patch_resp.status_code,
                    patch_resp.text[:200],
                )
        except Exception as exc:
            logger.warning("Resend webhook: tradespeople patch error (non-fatal) | err=%s", exc)

    # Persist inbound comm.
    try:
        comm_payload = {
            "project_id": project_id,
            "type": "email_in",
            "from_addr": from_field,
            "to_addr": (to_field[0] if isinstance(to_field, list) and to_field else (str(to_field) if isinstance(to_field, str) else "")),
            "subject": subject,
            "body": body_text or "",
            "attachments": attachments or [],
        }
        comm_payload = {k: v for k, v in comm_payload.items() if v is not None}
        comm_resp = await client.post(
            f"{base_url}/leo_project_comms",
            json=comm_payload,
            headers=database._get_headers(),
        )
        if comm_resp.status_code not in (200, 201):
            logger.warning("Resend webhook: comm insert failed (non-fatal) | status=%s body=%s", comm_resp.status_code, comm_resp.text[:200])
    except Exception as exc:
        logger.warning("Resend webhook: comm insert error (non-fatal) | err=%s", exc)

    # Send WhatsApp summary to user.
    if str(os.getenv("RESEND_WEBHOOK_SKIP_WHATSAPP") or "").strip().lower() in {"1", "true", "yes"}:
        logger.info("Resend webhook: skipping WhatsApp send (RESEND_WEBHOOK_SKIP_WHATSAPP=true) | project_id=%s", project_id)
        return JSONResponse({"ok": True, "project_id": project_id, "whatsapp": "skipped"}, status_code=200)

    try:
        from tools.leo_webhook_handler import format_email_summary
        from whatsapp.twilio_client import send_long_text_async

        msg = format_email_summary(
            from_email=from_field,
            subject=subject,
            body=body_text or "(no text body)",
            attachments=attachments or [],
        )
        proj_name = str(project.get("name") or "").strip()
        if proj_name:
            msg = f"Proyecto: {proj_name}\n\n{msg}".strip()
        await send_long_text_async(to=user_phone, body=msg)
    except Exception as exc:
        logger.error("Resend webhook: WhatsApp send failed | project_id=%s | err=%s", project_id, exc, exc_info=True)
        return JSONResponse({"ok": False, "error": "whatsapp send failed"}, status_code=500)

    return JSONResponse({"ok": True, "project_id": project_id}, status_code=200)


# =============================================================================
# TWILIO RECORDING-COMPLETE WEBHOOK
# =============================================================================

@router.post("/api/webhooks/twilio/recording-complete")
async def twilio_recording_complete(request: Request) -> Response:
    """
    Twilio fires this when a conference recording finishes processing.

    HOW THIS FITS:
    1. User + tradesperson hang up.
    2. Twilio finishes encoding the recording → POSTs here.
    3. We kick off: download → Whisper → AWS Transcribe → stitch → highlights.
    4. Result stored as call_memory in leo_project_comms with debrief_status='pending'.
    5. Next time the user messages Leo, Leo sees the pending debrief and
       naturally asks "so how was the call?" — Gordon Ramsay style.

    Query params (embedded in TwiML by leo_conference_call.py):
      - project_id: which project this call belongs to
      - conf: conference friendly name (e.g. "myproject-call-1")

    POST body from Twilio (form-encoded):
      - RecordingSid, RecordingUrl, RecordingStatus, RecordingDuration, etc.
    """
    form = await request.form()
    query_params = dict(request.query_params)

    recording_sid = str(form.get("RecordingSid") or "").strip()
    recording_url = str(form.get("RecordingUrl") or "").strip()
    recording_status = str(form.get("RecordingStatus") or "").strip()
    recording_duration = str(form.get("RecordingDuration") or "0").strip()
    project_id = str(query_params.get("project_id") or "").strip()
    conference_name = str(query_params.get("conf") or "").strip()

    logger.info(
        "Twilio recording-complete | sid=%s | status=%s | duration=%ss | project=%s | conf=%s",
        recording_sid, recording_status, recording_duration, project_id, conference_name,
    )

    if recording_status != "completed":
        logger.info("Recording not complete (status=%s), ignoring", recording_status)
        return JSONResponse({"ok": True, "ignored": True, "status": recording_status})

    if not recording_sid or not recording_url:
        logger.warning("Recording webhook missing RecordingSid or RecordingUrl")
        return JSONResponse({"ok": False, "error": "missing recording data"}, status_code=400)

    if not project_id:
        logger.warning("Recording webhook missing project_id query param")
        return JSONResponse({"ok": False, "error": "missing project_id"}, status_code=400)

    # Update the leo_project_comms row with the recording URL (best-effort match by conference_name).
    try:
        client = await database.get_client()
        base_url = database._get_base_url()

        # Find the comm row for this conference.
        comm_resp = await client.get(
            f"{base_url}/leo_project_comms",
            params={
                "project_id": f"eq.{project_id}",
                "type": "eq.call",
                "order": "created_at.desc",
                "limit": "5",
                "select": "id,call_sids,recording_url,call_memory,debrief_status",
            },
            headers=database._get_headers(),
        )
        comm_row = None
        if comm_resp.status_code == 200:
            rows = comm_resp.json() or []
            for row in rows:
                sids = row.get("call_sids") if isinstance(row.get("call_sids"), dict) else {}
                if sids.get("conference_name") == conference_name:
                    comm_row = row
                    break
            if not comm_row and rows:
                comm_row = rows[0]

        # Persist the recording_url immediately.
        if isinstance(comm_row, dict) and comm_row.get("id"):
            await client.patch(
                f"{base_url}/leo_project_comms",
                params={"id": f"eq.{comm_row['id']}"},
                json={"recording_url": recording_url},
                headers=database._get_headers(),
            )
            logger.info("Recording URL saved to comm row | id=%s", comm_row["id"])
    except Exception as exc:
        logger.warning("Failed to update comm row with recording URL (non-fatal) | err=%s", exc)
        comm_row = None

    # Kick off the full transcription pipeline in the background.
    # WHY BACKGROUND: Whisper + AWS Transcribe take 1-3 minutes.
    # Twilio needs a quick 200 response.
    import asyncio

    async def _transcribe_and_store() -> None:
        try:
            from tools.leo_call_transcriber import process_recording

            # Build speaker map: try to figure out who is "user" vs "tradesperson".
            speaker_map = {"spk_0": "User", "spk_1": "Tradesperson"}

            call_memory = await process_recording(
                recording_url=recording_url,
                recording_sid=recording_sid,
                conference_name=conference_name,
                project_id=project_id,
                speaker_map=speaker_map,
            )

            # Persist call_memory + set debrief_status to 'pending'.
            if isinstance(comm_row, dict) and comm_row.get("id"):
                client2 = await database.get_client()
                base_url2 = database._get_base_url()
                patch_resp = await client2.patch(
                    f"{base_url2}/leo_project_comms",
                    params={"id": f"eq.{comm_row['id']}"},
                    json={
                        "call_memory": call_memory,
                        "debrief_status": "pending",
                    },
                    headers=database._get_headers(),
                )
                if patch_resp.status_code in (200, 204):
                    logger.info(
                        "Call memory saved | comm_id=%s | project=%s | segments=%d | elapsed=%.1fs",
                        comm_row["id"],
                        project_id,
                        call_memory.get("stitched_segment_count", 0),
                        call_memory.get("processing_time_s", 0),
                    )
                else:
                    logger.error(
                        "Failed to save call_memory | comm_id=%s | status=%s | body=%s",
                        comm_row["id"],
                        patch_resp.status_code,
                        (patch_resp.text or "")[:300],
                    )
            else:
                logger.warning("No comm row to attach call_memory to | project=%s | conf=%s", project_id, conference_name)

        except Exception as exc:
            logger.error(
                "Transcription pipeline failed | project=%s | rec=%s | err=%s",
                project_id, recording_sid, exc, exc_info=True,
            )

    asyncio.create_task(_transcribe_and_store())

    return JSONResponse({
        "ok": True,
        "recording_sid": recording_sid,
        "project_id": project_id,
        "transcription": "started",
    })


# =============================================================================
# GENERATED IMAGE SERVING
# =============================================================================

@router.get("/api/listings/{listing_id}/generated-images/{index}")
async def serve_generated_image(listing_id: int, index: int) -> Response:
    """
    Serve a generated room image for a listing.

    WHY THIS EXISTS: Generated images are stored as base64 in unified_estimates.
    Twilio needs a publicly accessible URL to fetch media. This endpoint
    decodes the base64 and returns the image as JPEG.

    The URL must be publicly accessible (e.g. via ngrok during testing).

    Args:
        listing_id: The listing ID
        index:      Zero-based index into the generated_images array
    """
    try:
        import database
        gen_images = await database.get_unified_estimate(
            listing_id, "v5_generated_images_market_standard"
        )
    except Exception as exc:
        logger.error("Image serve: DB error | listing_id=%s | error=%s", listing_id, exc)
        return JSONResponse({"error": "database error"}, status_code=500)

    if not gen_images or not isinstance(gen_images, dict):
        return JSONResponse({"error": "no generated images found"}, status_code=404)

    images = gen_images.get("generated_images") or []
    if index < 0 or index >= len(images):
        return JSONResponse(
            {"error": f"image index {index} out of range (0-{len(images) - 1})"},
            status_code=404,
        )

    image_entry = images[index]
    after_data = image_entry.get("after_data")

    if not after_data:
        return JSONResponse({"error": "image not generated (failed)"}, status_code=404)

    try:
        image_bytes = base64.b64decode(after_data)
    except Exception:
        return JSONResponse({"error": "invalid image data"}, status_code=500)

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 1 day
            "Content-Disposition": f'inline; filename="listing_{listing_id}_room_{index}.jpg"',
        },
    )
