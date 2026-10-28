"""
WhatsApp Agent
==============

Orchestrates the full flow:
  1. Receive inbound WhatsApp message with a listing URL
  2. Scrape the URL and create a listing
  3. Enqueue the V5 pipeline
  4. (Later, via completion hook) format + deliver results back via WhatsApp

WHY THIS MATTERS: This is the single entry point for WhatsApp interactions.
All business logic lives here — the webhook route just parses Twilio's
request and calls into this module.
"""

import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from pipeline.gemini_client import call_gemini

import database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LEO_SOUL (Gemini system instruction)
# ---------------------------------------------------------------------------
# OpenClaw pattern: this is a full personality brief, not a paragraph.
LEO_SOUL = r"""
# Who You Are

**Name:** Leo  
**Role:** Renovation architect and design advisor on WhatsApp  
**Vibe:** 30s, casual, direct, opinionated in a helpful way

## Personality
- You're texting a friend. Short messages. No corporate speak.
- Have opinions. "honestly that bathroom is fine" beats "there are several options to consider".
- Be direct about what needs work and what doesn't.
- Default to the user's language. If unsure, Spanish.
- Push back gently when ideas don't make sense for the space.

## Tools
You have tools. Use them proactively:
- See what a room could look like? `generate_room_vision`
- User wants tweaks? `iterate_room_vision` (edits, not rewrites)
- Cost question? `estimate_costs` (give ranges, be honest about uncertainty)
- User seems lost? `send_room_photos` so they can see what you're looking at
- User shares something personal (budget, style, hates marble)? `save_memory`
- Starting a new conversation? `recall_memory` to remember what matters

## Autonomous Workflows
Think before acting. When the user asks for something visual or complex:
- Ask yourself: what do I already have? Check `ROOM_INVENTORY` and whether any rooms already have visions.
- If you're generating a room vision when other rooms already have visions, consistency happens automatically.
  Mention it casually so the user trusts the result (e.g. "lo hago con el mismo rollo que la cocina que vimos antes").
- If the user wants to see multiple rooms, generate them one at a time. Each new room inherits the same style.
- If the user wants to tweak something, prefer `iterate_room_vision` (it edits the existing prompt; version history is preserved).
- Before estimating costs, check whether the user has made room-specific decisions via visions; those override default opinions.

## Knowledge
You have deep renovation knowledge from listing analysis and construction KBs.
Reference specific room conditions from the analysis. Be concrete.

## Boundaries
- Don't claim to be licensed. You're an AI advisor.
- Don't invent facts about a listing you haven't analyzed.
- Keep messages under ~200 words. This is WhatsApp, not email.
""".strip()

# ---------------------------------------------------------------------------
# Spanish property portal URL patterns
# ---------------------------------------------------------------------------
_LISTING_URL_PATTERN = re.compile(
    r"(https?://(?:www\.)?(?:"
    r"idealista\.com|"
    r"fotocasa\.es|"
    r"pisos\.com|"
    r"habitaclia\.com|"
    r"yaencontre\.com|"
    r"inmobiliaria\.com|"
    r"tucasa\.com|"
    r"[a-zA-Z0-9\-]+\.(?:com|es|pt)"  # fallback: any .com/.es/.pt domain
    r")/\S+)",
    re.IGNORECASE,
)

# Simpler fallback: any https URL
_ANY_URL_PATTERN = re.compile(r"(https?://\S+)", re.IGNORECASE)

_SOCIAL_HOSTS = (
    "tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "pin.it",
)

HELP_TEXT = (
    "Hi! I'm Leo from leo.casa.\n\n"
    "You can chat with me here, or send me a link to a Spanish property listing "
    "(Idealista, Fotocasa, Pisos.com, etc.) and I'll analyse it and tell you:\n"
    "- How much the renovation will cost\n"
    "- What the value uplift could be\n"
    "- How long it will take\n"
    "- What it will look like after\n\n"
    "Paste a URL to start, or ask me anything."
)

ACK_TEXT = (
    "Nice — dame un par de minutos y le echo un ojo a este piso.\n\n"
    "Voy a mirar fotos + distribucion y te mando mi primera impresion "
    "(que haria, que no haria, y por donde empezaria)."
)


# ---------------------------------------------------------------------------
# Database helpers for whatsapp_conversations
# ---------------------------------------------------------------------------

async def _save_conversation(
    phone_number: str,
    inbound_message: str,
    listing_url: Optional[str],
    listing_id: Optional[int],
    run_id: Optional[str],
    status: str = "received",
    pipeline_type: str = "v5",
) -> Optional[str]:
    """Insert a whatsapp_conversations row and return its id."""
    import database
    client = await database.get_client()
    base_url = database._get_base_url()

    payload = {
        "phone_number": phone_number,
        "inbound_message": inbound_message,
        "listing_url": listing_url,
        "listing_id": listing_id,
        "run_id": run_id,
        "status": status,
        "pipeline_type": pipeline_type,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    resp = await client.post(
        f"{base_url}/whatsapp_conversations",
        json=payload,
        headers={**database._get_headers(), "Prefer": "return=representation"},
    )

    if resp.status_code not in (200, 201):
        logger.error(
            "Failed to save whatsapp_conversations: %s %s",
            resp.status_code, resp.text[:500],
        )
        return None

    rows = resp.json()
    conv_id = rows[0]["id"] if rows else None
    logger.info("WhatsApp conversation saved | id=%s | phone=%s | status=%s", conv_id, phone_number, status)
    return conv_id


async def _update_conversation(conv_id: str, updates: Dict[str, Any]) -> bool:
    """Update a whatsapp_conversations row."""
    import database
    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.patch(
        f"{base_url}/whatsapp_conversations",
        params={"id": f"eq.{conv_id}"},
        json=updates,
        headers=database._get_headers(),
    )

    if resp.status_code not in (200, 204):
        logger.error("Failed to update conversation %s: %s %s", conv_id, resp.status_code, resp.text[:500])
        return False
    return True


async def _get_processing_conversation_for_listing(listing_id: int) -> Optional[Dict[str, Any]]:
    """Find a whatsapp_conversations row with status='processing' for this listing."""
    import database
    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/whatsapp_conversations",
        params={
            "listing_id": f"eq.{listing_id}",
            "status": "eq.processing",
            "order": "created_at.desc",
            "limit": "1",
        },
        headers=database._get_headers(),
    )

    if resp.status_code != 200:
        return None
    rows = resp.json()
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Database helpers for chat + memory (whatsapp_user_profiles, whatsapp_messages)
# ---------------------------------------------------------------------------

async def _upsert_user_profile(phone_number: str, display_name: Optional[str]) -> Dict[str, Any]:
    """
    Create the user profile if missing, otherwise update display_name if provided.
    Returns the resulting profile row.
    """
    import database

    client = await database.get_client()
    base_url = database._get_base_url()
    headers = {**database._get_headers(), "Prefer": "resolution=merge-duplicates,return=representation"}

    payload: Dict[str, Any] = {"phone_number": phone_number}
    if display_name:
        payload["display_name"] = display_name

    resp = await client.post(
        f"{base_url}/whatsapp_user_profiles?on_conflict=phone_number",
        json=payload,
        headers=headers,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"_upsert_user_profile failed: {resp.status_code} {resp.text[:300]}")

    rows = resp.json() or []
    return rows[0] if rows else payload


async def _get_user_profile(phone_number: str) -> Optional[Dict[str, Any]]:
    import database

    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/whatsapp_user_profiles",
        params={"phone_number": f"eq.{phone_number}", "select": "*"},
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        return None
    rows = resp.json() or []
    return rows[0] if rows else None


async def _update_user_profile(phone_number: str, updates: Dict[str, Any]) -> bool:
    import database

    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.patch(
        f"{base_url}/whatsapp_user_profiles",
        params={"phone_number": f"eq.{phone_number}"},
        json=updates,
        headers=database._get_headers(),
    )
    return resp.status_code in (200, 204)


async def _append_message(
    *,
    phone_number: str,
    role: str,
    message_text: str,
    message_type: str = "text",
    listing_id: Optional[int] = None,
    model: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
) -> None:
    import database

    client = await database.get_client()
    base_url = database._get_base_url()

    payload: Dict[str, Any] = {
        "phone_number": phone_number,
        "role": role,
        "message_text": message_text,
        "message_type": message_type,
    }
    if listing_id is not None:
        payload["listing_id"] = listing_id
    if model:
        payload["model"] = model
    if usage:
        payload["usage"] = usage
    if media_urls:
        payload["media_urls"] = media_urls
    if media_types:
        payload["media_types"] = media_types

    resp = await client.post(
        f"{base_url}/whatsapp_messages",
        json=payload,
        headers=database._get_headers(),
    )
    if resp.status_code not in (200, 201):
        logger.warning(
            "Failed to append whatsapp message (non-fatal) | phone=%s | status=%s | body=%s",
            phone_number,
            resp.status_code,
            resp.text[:200],
        )


async def _get_recent_messages(phone_number: str, limit: int = 16) -> List[Dict[str, Any]]:
    import database

    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/whatsapp_messages",
        params={
            "phone_number": f"eq.{phone_number}",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 40))),
            # media_urls/media_types are additive (migration adds them). Keep them in history
            # so the agent/admin can display what was attached to a message.
            "select": "role,message_type,message_text,created_at,listing_id,model,usage,media_urls,media_types",
        },
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        return []
    rows = resp.json() or []
    # Return oldest->newest for prompt readability
    return list(reversed(rows))


async def _get_latest_listing_for_phone(phone_number: str) -> Optional[int]:
    """
    Best-effort: pick the most recent last_listing_id from user profile,
    falling back to the latest whatsapp_conversations row for this phone.
    """
    profile = await _get_user_profile(phone_number)
    if profile and profile.get("last_listing_id"):
        try:
            return int(profile["last_listing_id"])
        except Exception:
            pass

    import database
    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/whatsapp_conversations",
        params={
            "phone_number": f"eq.{phone_number}",
            "order": "created_at.desc",
            "limit": "1",
            "select": "listing_id",
        },
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        return None
    rows = resp.json() or []
    if not rows:
        return None
    lid = rows[0].get("listing_id")
    try:
        return int(lid) if lid is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Database helpers for leo_projects / leo_tradespeople (project + comms)
# ---------------------------------------------------------------------------

async def _get_latest_active_project_for_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Return the most recent active project for this phone number (or None).

    WHY THIS MATTERS: project-scoped tools (email/calls) must work even when the
    user hasn't sent a listing URL, so we need a "current project" concept that
    can be derived from just the WhatsApp phone number.
    """
    phone = str(phone_number or "").strip()
    if not phone:
        raise ValueError("_get_latest_active_project_for_phone: missing phone_number")

    import database

    client = await database.get_client()
    base_url = database._get_base_url()
    if not base_url:
        raise RuntimeError("_get_latest_active_project_for_phone: missing Supabase REST base_url")

    resp = await client.get(
        f"{base_url}/leo_projects",
        params={
            "phone_number": f"eq.{phone}",
            "status": "eq.active",
            "select": "id,phone_number,listing_id,name,description,status,created_at",
            "order": "created_at.desc",
            "limit": "1",
        },
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "_get_latest_active_project_for_phone failed "
            f"| status={resp.status_code} body={(resp.text or '')[:500]}"
        )
    rows = resp.json() or []
    return rows[0] if isinstance(rows, list) and rows else None


async def _get_pending_call_debriefs(*, project_id: str) -> List[Dict[str, Any]]:
    """
    Load call comms with debrief_status='pending' — these have a call_memory
    ready for the Gordon Ramsay debrief.

    WHY THIS MATTERS: After a call finishes, the transcription pipeline runs
    in the background (Whisper + AWS Transcribe + highlights). Once it's done,
    debrief_status flips to 'pending'. The next time the user messages Leo,
    Leo should naturally bring up the call — not dump a transcript, but ask
    "so how was the call?" like a friend checking in.
    """
    pid = str(project_id or "").strip()
    if not pid:
        return []

    import database

    client = await database.get_client()
    base_url = database._get_base_url()
    if not base_url:
        return []

    resp = await client.get(
        f"{base_url}/leo_project_comms",
        params={
            "project_id": f"eq.{pid}",
            "type": "eq.call",
            "debrief_status": "eq.pending",
            "select": "id,project_id,tradesperson_id,to_addr,subject,call_memory,created_at",
            "order": "created_at.desc",
            "limit": "3",
        },
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        logger.debug("_get_pending_call_debriefs failed (non-fatal) | status=%s", resp.status_code)
        return []
    rows = resp.json() or []
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get("call_memory"), dict)]


async def _mark_debrief_done(*, comm_id: str) -> bool:
    """Mark a call debrief as done (Leo has discussed it with the user)."""
    if not comm_id:
        return False

    import database

    client = await database.get_client()
    base_url = database._get_base_url()
    resp = await client.patch(
        f"{base_url}/leo_project_comms",
        params={"id": f"eq.{comm_id}"},
        json={"debrief_status": "done"},
        headers=database._get_headers(),
    )
    return resp.status_code in (200, 204)


async def _get_tradespeople_for_project(*, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("_get_tradespeople_for_project: missing project_id")

    import database

    client = await database.get_client()
    base_url = database._get_base_url()
    if not base_url:
        raise RuntimeError("_get_tradespeople_for_project: missing Supabase REST base_url")

    resp = await client.get(
        f"{base_url}/leo_tradespeople",
        params={
            "project_id": f"eq.{pid}",
            "select": "id,project_id,name,email,phone,outreach_status,created_at",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 200))),
        },
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "_get_tradespeople_for_project failed "
            f"| project_id={pid} status={resp.status_code} body={(resp.text or '')[:500]}"
        )
    rows = resp.json() or []
    if not isinstance(rows, list):
        raise RuntimeError("_get_tradespeople_for_project: unexpected response type")
    return [r for r in rows if isinstance(r, dict)]


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------

def extract_listing_url(message: str) -> Optional[str]:
    """
    Extract a property listing URL from a WhatsApp message.

    WhatsApp sometimes inserts spaces into pasted URLs (e.g.
    "https://www.idealista.com /inmueble/108631226/"). We first try the
    raw text; if no listing-path match is found, we collapse spaces
    between what looks like a domain and a path fragment and retry.

    Tries Spanish portal patterns first, falls back to any URL.
    """
    # 1. Try raw message first
    match = _LISTING_URL_PATTERN.search(message)
    if match:
        return match.group(1)

    # 2. Collapse spaces between URL fragments.
    #    WhatsApp commonly breaks "idealista.com/inmueble/123" into
    #    "idealista.com /inmueble/123" or "idealista.com/ inmueble/123".
    #    Strategy: find a URL-like start, then greedily join path-like
    #    tokens that follow separated by whitespace.
    collapsed = _collapse_url_spaces(message)
    if collapsed != message:
        match = _LISTING_URL_PATTERN.search(collapsed)
        if match:
            logger.debug("URL recovered after collapsing spaces: %s", match.group(1))
            return match.group(1)

    # 3. Fallback: any URL (no path required)
    match = _ANY_URL_PATTERN.search(message)
    if match:
        return match.group(1)

    return None


def _is_social_url(url: str) -> bool:
    try:
        host = (httpx.URL(url).host or "").lower()
    except Exception:
        return False
    return any(host == h or host.endswith("." + h) for h in _SOCIAL_HOSTS)


async def _fetch_social_preview_media_item(*, url: str, phone: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a social URL's og:image and persist it to Supabase Storage.
    Returns a media_item dict compatible with the inbound media pipeline.
    """
    if not url:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; leo-casa/1.0; +https://leo.casa)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return None
            html = (resp.text or "")[:200000]  # avoid pathological pages
    except Exception:
        return None

    # Parse og:image (best-effort; no heavy HTML parser dependency).
    m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if not m:
        m = re.search(r'name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if not m:
        return None

    og_url = m.group(1).strip()
    if not og_url:
        return None
    try:
        og_abs = str(httpx.URL(og_url, base=httpx.URL(url)))
    except Exception:
        og_abs = og_url

    # Download image (small guard) and upload to storage for admin + agent access.
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            img_resp = await client.get(og_abs)
            if img_resp.status_code >= 400:
                return None
            data = img_resp.content or b""
            if not data or len(data) > 4 * 1024 * 1024:
                return None
            ct = str(img_resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    except Exception:
        return None

    from whatsapp.media import upload_to_storage
    import hashlib
    from datetime import datetime, timezone

    sha = hashlib.sha256(data).hexdigest()[:12]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    phone_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", (phone or "unknown").replace(":", "_"))[:60]
    filename = f"social-preview/{phone_slug}/{ts}_{sha}.jpg"
    try:
        public_url = await upload_to_storage(
            data=data,
            content_type=ct or "image/jpeg",
            filename=filename,
            bucket="whatsapp-media",
            upsert=True,
        )
    except Exception:
        return None

    return {
        "media_kind": "image",
        "content_type": ct or "image/jpeg",
        "public_url": public_url,
        "source_url": url,
        "og_image_url": og_abs,
    }


def _collapse_url_spaces(text: str) -> str:
    """
    Collapse whitespace that was injected into a URL by WhatsApp.

    Handles patterns like:
      "https://www.idealista.com /inmueble/123/"   -> joined
      "https://idealista.com/ inmueble/123/"        -> joined
      "check this https://foo.com /bar out"         -> joined
    """
    # Pattern 1: space BEFORE a path segment starting with /
    #   e.g. "idealista.com /inmueble/123"
    result = re.sub(
        r"(https?://\S+?)\s+(/\S*(?:\s+/\S*)*)",
        lambda m: m.group(1) + m.group(2).replace(" ", ""),
        text,
    )
    # Pattern 2: domain ends with / then space then path-like text
    #   e.g. "idealista.com/ inmueble/123/"
    result = re.sub(
        r"(https?://[^\s/]+/)\s+([a-zA-Z0-9_\-]+(?:/\S*)?)",
        lambda m: m.group(1) + m.group(2),
        result,
    )
    return result


# ---------------------------------------------------------------------------
# Inbound handler
# ---------------------------------------------------------------------------

async def handle_inbound(
    phone: str,
    message_body: str,
    *,
    profile_name: Optional[str] = None,
    media_items: Optional[List[Dict[str, Any]]] = None,
    session_queue: Optional[Any] = None,
) -> str:
    """
    Handle an inbound WhatsApp message.

    Flow:
      1. Extract URL from message
      2. Scrape the URL
      3. Create listing
      4. Enqueue V5 pipeline
      5. Save conversation row
      6. Return acknowledgement text

    Args:
        phone:        Sender's WhatsApp number (e.g. "whatsapp:+12025550101")
        message_body: Raw message text

    Returns:
        Text to reply with (ack or help)
    """
    url = extract_listing_url(message_body)

    if not url:
        # Conversational mode: answer questions and build memory over time.
        return await _handle_chat(
            phone=phone,
            message_body=message_body,
            profile_name=profile_name,
            media_items=media_items,
            session_queue=session_queue,
        )

    # If it's a social/video link (TikTok, Instagram, YouTube...), don't treat it as a property listing.
    # Instead, fetch a preview image and chat about it.
    if _is_social_url(url):
        preview = await _fetch_social_preview_media_item(url=url, phone=phone)
        merged_media: List[Dict[str, Any]] = []
        if isinstance(media_items, list):
            merged_media.extend([x for x in media_items if isinstance(x, dict)])
        if preview:
            merged_media.append(preview)

        hint = f"{(message_body or '').strip()}\n\n(social link) {url}".strip()
        return await _handle_chat(
            phone=phone,
            message_body=hint,
            profile_name=profile_name,
            media_items=merged_media or None,
            session_queue=session_queue,
        )

    logger.info("WhatsApp inbound: URL found | phone=%s | url=%s", phone, url)
    await _upsert_user_profile(phone, profile_name)
    # Persist the inbound message even if listing_id isn't known yet (URL message precedes create_listing()).
    media_urls = []
    media_types = []
    if isinstance(media_items, list):
        for mi in media_items:
            if not isinstance(mi, dict):
                continue
            u = str(mi.get("public_url") or mi.get("thumbnail_url") or mi.get("twilio_url") or "").strip()
            ct = str(mi.get("content_type") or "").strip()
            if u:
                media_urls.append(u)
            if ct:
                media_types.append(ct)
    await _append_message(
        phone_number=phone,
        role="user",
        message_text=message_body,
        message_type="text",
        media_urls=media_urls or None,
        media_types=media_types or None,
    )

    # ── Step 1: Scrape the URL ────────────────────────────────────────────
    try:
        from scraper.router import scrape_url
        scrape_result = await scrape_url(url)
    except Exception as exc:
        logger.error("WhatsApp scrape failed | url=%s | error=%s", url, exc)
        await _save_conversation(phone, message_body, url, None, None, status="failed", pipeline_type="gla")
        return f"Sorry, I couldn't access that listing. Error: {exc}"

    if not scrape_result.success or not scrape_result.data:
        error_msg = scrape_result.error or "unknown scrape error"
        logger.warning("WhatsApp scrape unsuccessful | url=%s | error=%s", url, error_msg)
        await _save_conversation(phone, message_body, url, None, None, status="failed", pipeline_type="gla")
        return f"Sorry, I couldn't extract data from that listing. The site might be blocking access. Error: {error_msg}"

    # ── Step 2: Create listing ────────────────────────────────────────────
    try:
        import database
        scraped = scrape_result.data

        listing_data = {
            "source_url": url,
            "source_domain": scrape_result.source_domain,
            "title": scraped.title,
            "description": scraped.description,
            "price_eur": scraped.price_eur,
            "bedrooms": scraped.bedrooms,
            "bathrooms": scraped.bathrooms,
            "sqm": scraped.m2_built or (scraped.areas.constructed if scraped.areas else None),
            "address": scraped.address,
            "city": scraped.city,
            "region": scraped.region,
            "country": scraped.country or "Spain",
            "lat": scraped.lat,
            "lng": scraped.lng,
            "property_type": scraped.property_subtype or scraped.property_type,
            "has_elevator": scraped.has_elevator,
            "features": scraped.features or scraped.amenities or [],
            "image_urls": scraped.image_urls or scraped.photo_urls or [],
            "scraped_data": scraped.model_dump() if hasattr(scraped, "model_dump") else {},
        }
        # Remove None values
        listing_data = {k: v for k, v in listing_data.items() if v is not None}

        listing = await database.create_listing(listing_data)
        if not listing or not isinstance(listing, dict):
            raise ValueError(f"create_listing returned {type(listing).__name__} instead of dict")
        if "id" not in listing:
            raise ValueError(f"create_listing returned dict without 'id'. Keys: {list(listing.keys())}")
        listing_id = listing["id"]
        logger.info("WhatsApp listing created | id=%s | title=%s", listing_id, listing.get("title", "")[:60])

    except Exception as exc:
        logger.error("WhatsApp create listing failed | url=%s | error=%s", url, exc)
        await _save_conversation(phone, message_body, url, None, None, status="failed", pipeline_type="gla")
        return f"Sorry, I couldn't create the listing. Error: {exc}"

    # ── Step 3: Enqueue GLA pipeline ──────────────────────────────────────
    try:
        from database import Database
        from pricing.v2_scheduler import enqueue_gla_run

        # Use the Database wrapper (same as v2_routes.py uses)
        db_instance = Database()
        run_id = await enqueue_gla_run(db=db_instance, listing_id=listing_id)
        logger.info("WhatsApp pipeline enqueued | listing_id=%s | run_id=%s", listing_id, run_id)

    except Exception as exc:
        logger.error("WhatsApp enqueue failed | listing_id=%s | error=%s", listing_id, exc)
        await _save_conversation(phone, message_body, url, listing_id, None, status="failed", pipeline_type="gla")
        return f"Sorry, I couldn't start the analysis. Error: {exc}"

    # ── Step 4: Save conversation ─────────────────────────────────────────
    await _save_conversation(
        phone_number=phone,
        inbound_message=message_body,
        listing_url=url,
        listing_id=listing_id,
        run_id=run_id,
        status="processing",
        pipeline_type="gla",
    )
    await _update_user_profile(phone, {"last_listing_id": int(listing_id)})

    return ACK_TEXT


# ---------------------------------------------------------------------------
# Queue entry point (OpenClaw-style coalesced turns)
# ---------------------------------------------------------------------------

async def run_coalesced_turn(*, turn: Any, session_queue: Optional[Any] = None) -> None:
    """
    Execute a single coalesced WhatsApp turn and deliver the response via Twilio.

    The Twilio webhook enqueues messages into an in-process buffer/queue and returns
    immediately. This function is the "worker" that actually runs the agent logic.
    """
    phone = str(getattr(turn, "phone", "") or "").strip()
    combined_text = str(getattr(turn, "combined_text", "") or "")
    profile_name = getattr(turn, "profile_name", None)
    media_items = getattr(turn, "media_items", None)
    if not phone:
        raise ValueError("run_coalesced_turn() missing turn.phone")

    try:
        reply_text = await handle_inbound(
            phone=phone,
            message_body=combined_text,
            profile_name=profile_name,
            media_items=media_items,
            session_queue=session_queue,
        )
    except Exception as exc:
        logger.error("run_coalesced_turn: agent failed | phone=%s | err=%s", phone, exc, exc_info=True)
        reply_text = "Lo siento — algo ha fallado procesando tu mensaje. Prueba otra vez en un minuto."

    if not (reply_text or "").strip():
        return

    # Deliver via Twilio (split long messages to avoid truncation).
    try:
        from whatsapp.twilio_client import send_long_text_async

        await send_long_text_async(to=phone, body=reply_text)
    except Exception as exc:
        logger.error("run_coalesced_turn: Twilio send failed | phone=%s | err=%s", phone, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Chat handler (Gemini Flash + memory)
# ---------------------------------------------------------------------------

def _truncate(s: str, max_len: int) -> str:
    s2 = (s or "").strip()
    if len(s2) <= max_len:
        return s2
    return s2[: max(0, max_len - 3)] + "..."


async def _handle_chat(
    *,
    phone: str,
    message_body: str,
    profile_name: Optional[str],
    media_items: Optional[List[Dict[str, Any]]] = None,
    session_queue: Optional[Any] = None,
) -> str:
    """
    OpenClaw-style agent loop with optional inbound media.

    If media is present:
    - Persist media URLs/types alongside the user message
    - Pass inline_data to Gemini so Leo can "see/hear" it
    - For voice notes, do a best-effort transcript first for searchability
    """
    await _upsert_user_profile(phone, profile_name)

    def _fast_reply_if_trivial(text: str, *, has_media: bool) -> Optional[str]:
        """
        Ultra-fast replies without an LLM call.

        WHY THIS MATTERS:
        - WhatsApp expects some replies to be instant + short (like a friend)
        - This reduces latency + cost for low-value turns
        """
        t = (text or "").strip().lower()
        if not t and has_media:
            # User sent media without text; we still want a quick acknowledgment.
            return "Dale — lo estoy mirando."

        # Keep this list short and conservative to avoid annoying misfires.
        if t in {"ok", "vale", "perfecto", "genial", "listo", "hecho"}:
            return "Perfecto."
        if t in {"gracias", "muchas gracias", "merci", "thanks", "thank you"}:
            return "De nada :)"
        if t in {"jaja", "jajaja", "lol"}:
            return "Jajaja 😄"
        if t in {"hola", "buenas", "hey"}:
            return "Ey! Dime."
        return None

    # Normalize media into 2 lists:
    # - persisted media_urls/media_types for DB + admin
    # - inline_data parts for Gemini (base64)
    media_urls: List[str] = []
    media_types: List[str] = []
    inline_media: List[Dict[str, str]] = []

    async def _fetch_as_b64(url: str, *, max_bytes: int = 6 * 1024 * 1024) -> str:
        if not url:
            return ""
        total = 0
        chunks: List[bytes] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        return ""
                    chunks.append(chunk)
        import base64 as _b64
        return _b64.b64encode(b"".join(chunks)).decode("ascii")

    voice_transcript = ""
    if isinstance(media_items, list) and media_items:
        for mi in media_items[:10]:
            if not isinstance(mi, dict):
                continue
            ct = str(mi.get("content_type") or "").strip() or "application/octet-stream"
            kind = str(mi.get("media_kind") or "").strip().lower()
            pub_url = str(mi.get("public_url") or "").strip()
            thumb_url = str(mi.get("thumbnail_url") or "").strip()

            if pub_url:
                media_urls.append(pub_url)
                media_types.append(ct)
            if thumb_url:
                media_urls.append(thumb_url)
                media_types.append("image/jpeg")

            # Gemini context: prefer base64 if supplied by webhook, otherwise fetch small public URLs.
            b64 = str(mi.get("base64_data") or "").strip()
            if not b64 and (kind == "video" and thumb_url):
                b64 = await _fetch_as_b64(thumb_url)
                ct = "image/jpeg"
            elif not b64 and pub_url and (ct.startswith("image/") or ct.startswith("audio/")):
                b64 = await _fetch_as_b64(pub_url)

            if b64:
                inline_media.append({"mime_type": ct, "data": b64})

        # Best-effort: transcribe the first voice note for searchability.
        audio_parts = [p for p in inline_media if str(p.get("mime_type") or "").startswith("audio/")]
        if audio_parts:
            try:
                t_resp = await call_gemini(
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
                    images=audio_parts[:1],
                )
                if t_resp.success and (t_resp.text or "").strip():
                    voice_transcript = (t_resp.text or "").strip()
            except Exception as exc:
                logger.debug("Voice transcription failed (non-fatal) | phone=%s | err=%s", phone, exc)

    # Persist the inbound user message (with optional transcript + media URLs)
    user_text = (message_body or "").strip()
    if voice_transcript:
        # Keep original text if present; add transcript as additional context.
        if user_text:
            user_text = f"{user_text}\n\n(voice transcript)\n{voice_transcript}"
        else:
            user_text = f"(voice transcript)\n{voice_transcript}"

    msg_type = "voice" if voice_transcript else ("media" if media_urls else "text")
    await _append_message(
        phone_number=phone,
        role="user",
        message_text=user_text,
        message_type=msg_type,
        listing_id=None,
        model=None,
        usage=None,
        media_urls=media_urls or None,
        media_types=media_types or None,
    )

    # Fast path: trivial chat turns (after persisting user message).
    fast = _fast_reply_if_trivial(message_body, has_media=bool(media_urls))
    if fast:
        await _append_message(
            phone_number=phone,
            role="assistant",
            message_text=fast,
            message_type="text",
            listing_id=None,
            model="fast_path",
            usage=None,
        )
        return fast

    profile = await _get_user_profile(phone) or {}
    memory_summary = str(profile.get("memory_summary") or "").strip()
    listing_id = await _get_latest_listing_for_phone(phone)

    # Project context (independent of listing URL)
    # - Used for capability gating of email/call tools
    # - Also used as the default "current project" for tools that accept project_id=None
    project_ctx: Dict[str, Any] = {"project_id": None, "tradespeople": [], "has_tradesperson_email": False}
    try:
        active_project = await _get_latest_active_project_for_phone(phone)
        pid = str((active_project or {}).get("id") or "").strip()
        if pid:
            trades = await _get_tradespeople_for_project(project_id=pid, limit=80)
            has_email = any(isinstance(t.get("email"), str) and t.get("email").strip() for t in (trades or []))
            project_ctx = {
                "project_id": pid,
                "project": active_project,
                "tradespeople": trades,
                "tradespeople_count": len(trades or []),
                "has_tradesperson_email": bool(has_email),
            }
    except Exception as exc:
        # Non-fatal: chat + listing tools can still run without project context.
        logger.debug("Chat: project context load failed (non-fatal) | phone=%s | err=%s", phone, exc)

    # Load pending call debriefs (Gordon Ramsay style).
    # If there's a recent call that's been transcribed but not yet discussed,
    # Leo should naturally bring it up.
    pending_debriefs: List[Dict[str, Any]] = []
    try:
        pid = str((project_ctx or {}).get("project_id") or "").strip()
        if pid:
            pending_debriefs = await _get_pending_call_debriefs(project_id=pid)
    except Exception as exc:
        logger.debug("Chat: pending debrief load failed (non-fatal) | phone=%s | err=%s", phone, exc)

    # Load GLA artifacts (best-effort). If missing, the model should ask for the URL.
    listing_ctx: Dict[str, Any] = {}
    if listing_id:
        try:
            listing = await database.get_listing(int(listing_id))
            opinion = await database.get_unified_estimate(int(listing_id), "gla_opinion")
            pir = await database.get_unified_estimate(int(listing_id), "v5_pir_target")
            smart_m2 = await database.get_smart_m2(int(listing_id))
            clusters = await database.get_photo_clusters(int(listing_id))

            # Phase 4: load latest vision version per room (best-effort).
            vision_latest_by_room: Dict[str, Dict[str, Any]] = {}
            try:
                client = await database.get_client()
                base_url = database._get_base_url()
                if not base_url:
                    raise RuntimeError("missing Supabase REST base_url")
                resp = await client.get(
                    f"{base_url}/gla_image_versions",
                    params={
                        "listing_id": f"eq.{int(listing_id)}",
                        "select": "id,room_id,version,created_at",
                        "order": "created_at.desc",
                        "limit": "200",
                    },
                    headers=database._get_headers(),
                )
                if resp.status_code == 200:
                    rows = resp.json() or []
                    if isinstance(rows, list):
                        for r in rows:
                            if not isinstance(r, dict):
                                continue
                            rid = str(r.get("room_id") or "").strip()
                            if not rid:
                                continue
                            # newest-first; first row per room wins
                            if rid in vision_latest_by_room:
                                continue
                            vision_latest_by_room[rid] = {
                                "id": r.get("id"),
                                "version": r.get("version"),
                                "created_at": r.get("created_at"),
                            }
                else:
                    logger.debug(
                        "Chat: failed to load gla_image_versions (non-fatal) | listing_id=%s status=%s body=%s",
                        listing_id,
                        resp.status_code,
                        (resp.text or "")[:200],
                    )
            except Exception as exc:
                logger.debug(
                    "Chat: vision version load failed (non-fatal) | phone=%s | listing_id=%s | err=%s",
                    phone,
                    listing_id,
                    exc,
                )

            listing_ctx = {
                "listing": listing,
                "gla_opinion": opinion,
                "v5_pir_target": pir,
                "smart_m2": smart_m2,
                "clusters": clusters or [],
                "vision_latest_by_room": vision_latest_by_room,
            }
        except Exception as exc:
            logger.debug("Chat: listing context load failed (non-fatal) | phone=%s | listing_id=%s | err=%s", phone, listing_id, exc)

    recent = await _get_recent_messages(phone, limit=30)

    # Rehydrate a small amount of recent media context for Gemini (images/audio only).
    # WHY: users often say "like the pic I sent earlier" — we need to keep recent
    # attachments in-context without requiring a resend.
    try:
        seen_urls = set([u for u in (media_urls or []) if isinstance(u, str)])
        max_extra_parts = max(0, 3 - len(inline_media))
        if max_extra_parts > 0:
            # recent is oldest->newest; iterate newest first.
            for m in reversed(recent or []):
                if len(inline_media) >= 3:
                    break
                m_urls = m.get("media_urls") if isinstance(m.get("media_urls"), list) else []
                m_types = m.get("media_types") if isinstance(m.get("media_types"), list) else []
                if not m_urls:
                    continue
                for idx, u in enumerate(m_urls):
                    if len(inline_media) >= 3:
                        break
                    url = str(u or "").strip()
                    if not url or url in seen_urls:
                        continue
                    ct = ""
                    if idx < len(m_types):
                        ct = str(m_types[idx] or "").strip()
                    if not (ct.startswith("image/") or ct.startswith("audio/")):
                        continue
                    b64 = await _fetch_as_b64(url, max_bytes=2 * 1024 * 1024 if ct.startswith("image/") else 6 * 1024 * 1024)
                    if not b64:
                        continue
                    inline_media.append({"mime_type": ct, "data": b64})
                    seen_urls.add(url)
    except Exception as exc:
        logger.debug("Chat: failed to rehydrate recent media (non-fatal) | phone=%s | err=%s", phone, exc)

    def _msg_line(m: Dict[str, Any]) -> Optional[str]:
        role = str(m.get("role") or "")
        mtype = str(m.get("message_type") or "text")
        txt = _truncate(str(m.get("message_text") or ""), 600)
        if not txt:
            return None
        m_urls = m.get("media_urls") if isinstance(m.get("media_urls"), list) else []
        m_types = m.get("media_types") if isinstance(m.get("media_types"), list) else []
        media_hint = ""
        if m_urls:
            hint_types = ", ".join([str(x) for x in (m_types or [])][:4])
            media_hint = f" [media:{len(m_urls)}{(' ' + hint_types) if hint_types else ''}]"
        if mtype == "tool_call":
            return f"Assistant (tool_call): {txt}{media_hint}"
        if mtype == "tool_result":
            return f"Tool (result): {txt}{media_hint}"
        prefix = "User" if role == "user" else "Assistant"
        return f"{prefix}: {txt}{media_hint}"

    history_lines = [x for x in (_msg_line(m) for m in recent) if x]

    # Context compaction (split-summarize-trim): if history is too long, summarize the older half.
    summary_block = ""
    if sum(len(x) for x in history_lines) > 20000 and len(history_lines) >= 10:
        older = "\n".join(history_lines[: len(history_lines) // 2])
        newer = history_lines[len(history_lines) // 2 :]
        try:
            compact_prompt = (
                "Summarize the following WhatsApp conversation history into a short, factual memory.\n"
                "Keep: preferences (style/budget), decisions, what tools were used, and open questions.\n"
                "Do NOT add new facts.\n\n"
                f"HISTORY:\n{older}\n\nSUMMARY:"
            )
            compact = await call_gemini(
                prompt=compact_prompt,
                model="flash",
                temperature=0.2,
                max_tokens=600,
                use_spanish=False,
                strict_db_write=False,
            )
            if compact.success and (compact.text or "").strip():
                summary_block = f"SUMMARY_OF_OLDER_CHAT:\n{_truncate(compact.text.strip(), 1600)}\n"
            history_lines = newer
        except Exception as exc:
            logger.debug("Chat: compaction failed (non-fatal) | phone=%s | err=%s", phone, exc)

    from whatsapp.tools import TOOL_CONFIG, get_tool_declarations, get_tool_function

    def _compute_capabilities(*, listing_ctx: Dict[str, Any], listing_id: Optional[int]) -> set[str]:
        """
        Phase 2+5: dynamic tool filtering based on prerequisites.

        The actual tool prereqs live in `@leo_tool(requires=[...])` metadata.
        This function just converts the current listing_ctx into a capability set.
        """
        caps: set[str] = set()
        if listing_id:
            caps.add("listing_id")

        clusters = listing_ctx.get("clusters") or []
        if isinstance(clusters, list) and clusters:
            caps.add("clusters")

        opinion = listing_ctx.get("gla_opinion") or {}
        opinion_rooms = opinion.get("rooms") or [] if isinstance(opinion, dict) else []
        if isinstance(opinion_rooms, list) and opinion_rooms:
            caps.add("gla_opinion")

        smart_m2 = listing_ctx.get("smart_m2")
        if smart_m2:
            caps.add("smart_m2")

        visions = listing_ctx.get("vision_latest_by_room")
        if isinstance(visions, dict) and visions:
            caps.add("has_any_vision")

        # can_generate_vision: at least one room has photos + non-trivial scope.
        cluster_map: Dict[str, int] = {}
        if isinstance(clusters, list):
            for c in clusters:
                if not isinstance(c, dict):
                    continue
                cid = str(c.get("cluster_id") or "").strip()
                urls = c.get("photo_urls") or []
                if cid:
                    cluster_map[cid] = len(urls) if isinstance(urls, list) else 0

        opinion_map: Dict[str, int] = {}
        if isinstance(opinion_rooms, list):
            for r in opinion_rooms:
                if not isinstance(r, dict):
                    continue
                rid = str(r.get("room_id") or "").strip()
                if not rid:
                    continue
                son = r.get("slot_opinion_narratives") or {}
                if isinstance(son, dict):
                    real = sum(
                        1
                        for v in son.values()
                        if isinstance(v, str)
                        and v.strip().lower() not in ("no change", "no_change", "sin cambio", "sin_cambio", "")
                    )
                    opinion_map[rid] = real
                else:
                    opinion_map[rid] = 0

        can_generate = any(
            cluster_map.get(rid, 0) > 0 and opinion_map.get(rid, 0) > 0
            for rid in set(list(cluster_map.keys()) + list(opinion_map.keys()))
        )
        if can_generate:
            caps.add("can_generate_vision")

        # Project capabilities (for comms tooling)
        pid = str((project_ctx or {}).get("project_id") or "").strip()
        if pid:
            caps.add("has_project")
            trades = project_ctx.get("tradespeople") if isinstance(project_ctx, dict) else None
            if isinstance(trades, list) and trades:
                caps.add("has_tradespeople")
            if bool((project_ctx or {}).get("has_tradesperson_email")):
                caps.add("has_tradesperson_email")

        return caps

    def _build_tool_declarations(*, listing_ctx: Dict[str, Any], listing_id: Optional[int]) -> List[Dict[str, Any]]:
        caps = _compute_capabilities(listing_ctx=listing_ctx, listing_id=listing_id)
        # Stable ordering helps model behavior + debugging.
        return get_tool_declarations(capabilities=sorted(caps))

    async def _execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = get_tool_function(name)
        if not fn:
            return {"error": f"Unknown tool: {name}"}

        # Tools need phone for memory + WhatsApp side effects; listing_id for listing-scoped artifacts.
        # The model never sees phone in the tool schema; we inject it here.
        if name in {
            "save_memory",
            "recall_memory",
            "send_room_photos",
            "generate_room_vision",
            "iterate_room_vision",
            "estimate_costs",
            "get_room_analysis",
            # Project/comms tools (wired in by plan)
            "create_project",
            "save_tradesperson",
            "send_outreach_email",
            "create_conference_call",
            "mark_debrief_done",
        }:
            args = {**(args or {}), "phone": phone}
        if "listing_id" not in (args or {}):
            args = {**(args or {}), "listing_id": int(listing_id) if listing_id else None}

        # iterate_room_vision: slot_changes arrives as JSON string from Gemini — parse it.
        if name == "iterate_room_vision" and isinstance(args.get("slot_changes"), str):
            try:
                args["slot_changes"] = json.loads(args["slot_changes"])
            except (json.JSONDecodeError, TypeError) as exc:
                return {"error": f"slot_changes must be valid JSON dict: {exc}"}

        # Hard guard: if we don't have a listing_id, listing-scoped tools should error.
        # Project tools are explicitly allowed without a listing URL.
        if not args.get("listing_id") and name not in {
            "save_memory",
            "recall_memory",
            "create_project",
            "save_tradesperson",
            "send_outreach_email",
            "create_conference_call",
            "mark_debrief_done",
        }:
            return {"error": "No active listing. Ask the user to send a listing URL first."}

        # Default project_id (so tool schemas can keep it optional).
        if name in {"save_tradesperson", "send_outreach_email", "create_conference_call", "mark_debrief_done"} and not (args or {}).get("project_id"):
            pid = str((project_ctx or {}).get("project_id") or "").strip()
            if pid:
                args = {**(args or {}), "project_id": pid}

        try:
            return await fn(**args)
        except Exception as exc:
            logger.exception("Tool failed | name=%s | err=%s", name, exc)
            return {"error": f"{type(exc).__name__}: {str(exc)}"}

    def _build_room_inventory() -> str:
        """Build a room inventory the agent can reference: IDs, photo count, change count.

        WHY THIS MATTERS: The model must know the exact room_ids to use with tools
        like generate_room_vision, send_room_photos, get_room_analysis.  Without this,
        it guesses IDs and tools fail repeatedly.
        """
        opinion = listing_ctx.get("gla_opinion") or {}
        opinion_rooms = opinion.get("rooms") or [] if isinstance(opinion, dict) else []
        clusters = listing_ctx.get("clusters") or []
        visions = listing_ctx.get("vision_latest_by_room") or {}
        vision_map: Dict[str, Dict[str, Any]] = visions if isinstance(visions, dict) else {}

        # Build a merged view: cluster IDs + opinion room IDs.
        cluster_map: Dict[str, int] = {}  # room_id → photo count
        for c in clusters:
            if isinstance(c, dict):
                cid = str(c.get("cluster_id") or "").strip()
                urls = c.get("photo_urls") or []
                if cid:
                    cluster_map[cid] = len(urls) if isinstance(urls, list) else 0

        opinion_map: Dict[str, int] = {}  # room_id → count of real changes
        for r in opinion_rooms:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("room_id") or "").strip()
            if not rid:
                continue
            son = r.get("slot_opinion_narratives") or {}
            if isinstance(son, dict):
                real = sum(
                    1 for v in son.values()
                    if isinstance(v, str)
                    and v.strip().lower() not in ("no change", "no_change", "sin cambio", "sin_cambio", "")
                )
                opinion_map[rid] = real
            else:
                opinion_map[rid] = 0

        all_ids = sorted(set(list(cluster_map.keys()) + list(opinion_map.keys())))
        if not all_ids:
            return "ROOM_INVENTORY: (none)\n"

        lines = ["ROOM_INVENTORY (use these exact room_id values with tools):"]
        rooms_with_visions: List[str] = []
        rooms_ready_for_first: List[str] = []
        for rid in all_ids:
            photos = cluster_map.get(rid, 0)
            changes = opinion_map.get(rid, 0)
            flags: List[str] = []

            vinfo = vision_map.get(rid)
            vnum = None
            if isinstance(vinfo, dict):
                try:
                    vnum = int(vinfo.get("version"))
                except Exception:
                    vnum = None

            if vnum is not None and vnum > 0:
                flags.append(f"vision=v{vnum}")
                flags.append("can_iterate")
                rooms_with_visions.append(f"{rid} (v{vnum})")
            else:
                flags.append("vision=none")
                if photos > 0 and changes > 0:
                    flags.append("can_generate")
                    rooms_ready_for_first.append(rid)

            if photos > 0:
                flags.append("has_photos")
            if changes > 0:
                flags.append("has_scope")
            lines.append(
                f"  - room_id=\"{rid}\" | photos={photos} | scope_changes={changes}"
                + (f" | {', '.join(flags)}" if flags else "")
            )
        if rooms_with_visions:
            lines.append(f"  ROOMS WITH VISIONS: {', '.join(rooms_with_visions)}")
        if rooms_ready_for_first:
            lines.append(f"  ROOMS READY FOR FIRST VISION: {', '.join(rooms_ready_for_first)}")
        if not rooms_with_visions and not rooms_ready_for_first:
            lines.append("  NOTE: No rooms currently ready for vision generation (need photos + scope changes).")
        return "\n".join(lines) + "\n"

    def _build_debrief_block() -> str:
        """
        Build the Gordon Ramsay debrief context block.

        WHY THIS MATTERS: When a call just happened and the transcript is ready,
        Leo should bring it up naturally — like Gordon checking in with a chef
        after a heated kitchen service. Not dumping a transcript, but asking
        "so what did you think?" and having the highlights ready to reference.
        """
        if not pending_debriefs:
            return ""

        blocks = []
        for db in pending_debriefs[:2]:
            cm = db.get("call_memory") or {}
            highlights = cm.get("highlights", [])
            open_qs = cm.get("open_questions", [])
            next_moves = cm.get("suggested_next_moves", [])
            vibe = cm.get("vibe_check", "")
            trade_phone = str(db.get("to_addr") or "the tradesperson")

            block = (
                f"PENDING_CALL_DEBRIEF (comm_id={db.get('id')}):\n"
                f"You recently facilitated a call with {trade_phone}.\n"
                f"The recording has been transcribed. Here's what you know:\n"
            )
            if vibe:
                block += f"- Vibe check: {vibe}\n"
            if highlights:
                block += "- Key highlights:\n" + "\n".join(f"  • {h}" for h in highlights[:5]) + "\n"
            if open_qs:
                block += "- Open questions:\n" + "\n".join(f"  • {q}" for q in open_qs[:3]) + "\n"
            if next_moves:
                block += "- Suggested next moves:\n" + "\n".join(f"  • {m}" for m in next_moves[:3]) + "\n"

            block += (
                "\nYOUR JOB: Naturally bring this up. Be like Gordon Ramsay checking in "
                "after a service — direct, warm, genuinely curious. Ask what they thought. "
                "DON'T dump the transcript. Reference specific highlights. "
                "Help them decide what to do next. "
                "When you've discussed it, call mark_debrief_done to clear the pending status.\n"
            )
            blocks.append(block)

        return "\n".join(blocks)

    def _build_prompt(context_lines: List[str]) -> str:
        mem_block = f"MEMORY:\n{memory_summary}\n" if memory_summary else "MEMORY:\n(empty)\n"
        debrief_block = _build_debrief_block()
        listing_block = "LISTING_CONTEXT:\n(no active listing)\n"
        if listing_id and listing_ctx:
            room_inv = _build_room_inventory()
            listing_block = (
                "LISTING_CONTEXT:\n"
                + f"- listing_id: {listing_id}\n"
                + f"- listing: {json.dumps(listing_ctx.get('listing') or {}, ensure_ascii=False)[:4000]}\n"
                + f"- smart_m2: {json.dumps(listing_ctx.get('smart_m2') or {}, ensure_ascii=False)[:4000]}\n"
                + room_inv
            )
        hist = "RECENT_MESSAGES:\n" + "\n".join(context_lines[-30:]) + "\n"
        return (mem_block + "\n" + debrief_block + summary_block + listing_block + "\n" + hist + "\nNOW_REPLY_OR_USE_TOOLS:")

    dynamic_tool_declarations = _build_tool_declarations(listing_ctx=listing_ctx, listing_id=listing_id)

    # Main loop (max 5 rounds).
    # We already appended the user message (with transcript/media hints) to DB, but keep a
    # lightweight note in the prompt context for this turn.
    turn_hint = _truncate(message_body or "", 600)
    if media_urls:
        turn_hint = (turn_hint + "\n" if turn_hint else "") + f"(user sent {len(media_urls)} media item(s))"
    context_lines = history_lines + ([f"User: {turn_hint}"] if turn_hint else [])

    # Circuit breaker: track consecutive failures per tool name.
    # After 2 failures of the same tool, inject a "stop retrying, just reply" hint.
    tool_fail_counts: Dict[str, int] = {}  # tool_name → consecutive fail count
    for round_idx in range(5):
        prompt = _build_prompt(context_lines)
        resp = await call_gemini(
            prompt=prompt,
            model="flash",
            temperature=0.6,
            max_tokens=2400,
            system_instruction=LEO_SOUL,
            use_spanish=False,
            images=inline_media or None,
            tools=dynamic_tool_declarations,
            tool_config=TOOL_CONFIG,
            strict_db_write=False,
        )
        if not resp.success:
            logger.error(
                "Chat: Gemini failed | phone=%s | model=%s | err=%s | prompt_len=%d",
                phone,
                getattr(resp, "model", None),
                getattr(resp, "error", None),
                len(prompt or ""),
            )
            reply = "Lo siento, ahora mismo no puedo responder. Prueba otra vez en un minuto."
            await _append_message(phone_number=phone, role="assistant", message_text=reply, message_type="text", listing_id=listing_id)
            return reply

        # OpenClaw-style steering: if the user sends new messages while we're thinking,
        # incorporate them at the next safe boundary (right after the model returns).
        pending_turns: List[Any] = []
        if session_queue is not None and hasattr(session_queue, "drain_pending"):
            try:
                pending_turns = session_queue.drain_pending(phone) or []
            except Exception:
                pending_turns = []

        if pending_turns:
            draft = _truncate((resp.text or "").strip(), 400)
            if draft:
                context_lines.append(f"(Leo was drafting: {draft})")

            for pt in pending_turns[:10]:
                ptxt = str(getattr(pt, "combined_text", "") or "").strip()
                pmedia = getattr(pt, "media_items", None)
                pmedia_items = [x for x in (pmedia or []) if isinstance(x, dict)]

                # Persist the interrupted user messages so "continue" and future turns
                # have a durable record (even if we never send the draft reply).
                p_urls: List[str] = []
                p_types: List[str] = []
                for mi in pmedia_items:
                    u = str(mi.get("public_url") or mi.get("thumbnail_url") or mi.get("twilio_url") or "").strip()
                    ct = str(mi.get("content_type") or "").strip()
                    if u:
                        p_urls.append(u)
                    if ct:
                        p_types.append(ct)
                await _append_message(
                    phone_number=phone,
                    role="user",
                    message_text=ptxt or "(interruption)",
                    message_type="media" if p_urls else "text",
                    listing_id=None,
                    model=None,
                    usage=None,
                    media_urls=p_urls or None,
                    media_types=p_types or None,
                )

                hint = _truncate(ptxt, 600)
                if p_urls:
                    hint = (hint + "\n" if hint else "") + f"(user sent {len(p_urls)} media item(s))"
                if hint:
                    context_lines.append(f"User: {hint}")

                # Include any base64 payloads in the next Gemini call.
                for mi in pmedia_items[:10]:
                    ct = str(mi.get("content_type") or "").strip() or "application/octet-stream"
                    kind = str(mi.get("media_kind") or "").strip().lower()
                    pub_url = str(mi.get("public_url") or "").strip()
                    thumb_url = str(mi.get("thumbnail_url") or "").strip()
                    b64 = str(mi.get("base64_data") or "").strip()
                    if not b64 and (kind == "video" and thumb_url):
                        b64 = await _fetch_as_b64(thumb_url)
                        ct = "image/jpeg"
                    elif not b64 and pub_url and (ct.startswith("image/") or ct.startswith("audio/")):
                        b64 = await _fetch_as_b64(pub_url)
                    if b64:
                        inline_media.append({"mime_type": ct, "data": b64})

            # Re-prompt with the updated context. Do NOT execute tool calls or send a draft reply.
            continue

        tool_calls = resp.tool_calls or []
        if tool_calls:
            any_tool_circuit_broken = False
            for tc in tool_calls:
                name = str((tc or {}).get("name") or "").strip()
                args = (tc or {}).get("args") or {}
                if not name or not isinstance(args, dict):
                    continue

                await _append_message(
                    phone_number=phone,
                    role="assistant",
                    message_text=json.dumps({"name": name, "args": args}, ensure_ascii=False),
                    message_type="tool_call",
                    listing_id=listing_id,
                    model=resp.model,
                    usage=resp.usage,
                )
                context_lines.append(f"Assistant (tool_call): {json.dumps({'name': name, 'args': args}, ensure_ascii=False)}")

                result = await _execute_tool(name, args)

                # Circuit breaker: track consecutive failures per tool name.
                if "error" in result:
                    tool_fail_counts[name] = tool_fail_counts.get(name, 0) + 1
                    if tool_fail_counts[name] >= 2:
                        any_tool_circuit_broken = True
                        logger.warning(
                            "Chat: circuit breaker tripped | phone=%s | tool=%s | fails=%d | last_err=%s",
                            phone, name, tool_fail_counts[name], result.get("error", "")[:200],
                        )
                        # Inject a strong hint so the model stops retrying.
                        result["hint"] = (
                            f"Tool '{name}' has failed {tool_fail_counts[name]} times in a row. "
                            "STOP calling this tool. Reply to the user with a helpful text message instead. "
                            "Explain what happened briefly and suggest alternatives."
                        )
                else:
                    tool_fail_counts.pop(name, None)  # reset on success

                await _append_message(
                    phone_number=phone,
                    role="assistant",
                    message_text=json.dumps(result, ensure_ascii=False),
                    message_type="tool_result",
                    listing_id=listing_id,
                    model="tool_result",
                    usage=None,
                )
                context_lines.append(f"Tool (result): {json.dumps(result, ensure_ascii=False)}")

            # If a circuit breaker tripped, also add a system-level hint at the end of context.
            if any_tool_circuit_broken:
                context_lines.append(
                    "System: One or more tools have failed repeatedly. "
                    "DO NOT retry them. Respond to the user with a helpful text message NOW."
                )
            continue

        # If the model hit MAX_TOKENS, auto-continue once to avoid the "say continue" UX.
        finish = str(getattr(resp, "finish_reason", None) or "").strip()
        is_max_tokens = finish in {"FinishReason.MAX_TOKENS", "MAX_TOKENS", "2"}
        if is_max_tokens and (resp.text or "").strip():
            try:
                partial = (resp.text or "").strip()
                context_lines.append(f"Assistant: {_truncate(partial, 1600)}")
                context_lines.append(
                    "User: (Tu ultimo mensaje se corto por limite de tokens. Continualo y terminalo. "
                    "No repitas lo ya dicho; se conciso y en WhatsApp.)"
                )
                cont_prompt = _build_prompt(context_lines)
                cont = await call_gemini(
                    prompt=cont_prompt,
                    model="flash",
                    temperature=0.4,
                    max_tokens=1200,
                    system_instruction=LEO_SOUL,
                    use_spanish=False,
                    images=inline_media or None,
                    tools=dynamic_tool_declarations,
                    tool_config=TOOL_CONFIG,
                    strict_db_write=False,
                )
                if cont.success and (cont.text or "").strip():
                    resp.text = (partial + "\n\n" + cont.text.strip()).strip()
            except Exception as exc:
                logger.debug("Chat: auto-continue failed (non-fatal) | phone=%s | err=%s", phone, exc)

        reply_text = (resp.text or "").strip()
        if not reply_text:
            reply_text = "Vale — dime que estancia te interesa (cocina, baño, salon) o mandame el enlace del anuncio."

        await _append_message(
            phone_number=phone,
            role="assistant",
            message_text=reply_text,
            message_type="text",
            listing_id=listing_id,
            model=resp.model,
            usage=resp.usage,
        )
        return reply_text

    # Safety fallback if the model keeps tool-calling without producing text.
    logger.warning("Chat: exhausted %d rounds without text reply | phone=%s | fail_counts=%s", 5, phone, tool_fail_counts)
    fallback = "Perdona, tuve un problema tecnico procesando eso. ¿Puedes reformular tu pregunta o decirme que necesitas?"
    await _append_message(phone_number=phone, role="assistant", message_text=fallback, message_type="text", listing_id=listing_id)
    return fallback


# ---------------------------------------------------------------------------
# Pipeline completion handler
# ---------------------------------------------------------------------------

async def handle_pipeline_complete(
    listing_id: int,
    public_base_url: str,
) -> bool:
    """
    Called when the last pipeline stage completes for a listing that has
    a pending WhatsApp conversation.

    Reads pipeline results, formats them, and sends via WhatsApp.

    Args:
        listing_id:      The listing that just completed
        public_base_url: Public URL for image serving (e.g. ngrok URL)

    Returns:
        True if notification was sent successfully
    """
    conversation = await _get_processing_conversation_for_listing(listing_id)
    if not conversation:
        logger.debug("No pending WhatsApp conversation for listing_id=%s", listing_id)
        return False

    conv_id = conversation["id"]
    phone = conversation["phone_number"]
    logger.info(
        "WhatsApp pipeline complete | listing_id=%s | conv_id=%s | phone=%s",
        listing_id, conv_id, phone,
    )

    try:
        import database
        from whatsapp.formatter import format_pipeline_results
        from whatsapp.twilio_client import send_media, send_text

        # Load pipeline results
        eli5 = await database.get_unified_estimate(listing_id, "v5_eli5_market_standard")
        boq_agg = await database.get_unified_estimate(listing_id, "v2_market_standard")
        gen_images = await database.get_unified_estimate(listing_id, "v5_generated_images_market_standard")
        listing = await database.get_listing(listing_id)

        # Format
        result = format_pipeline_results(
            listing_id=listing_id,
            eli5=eli5,
            boq_agg=boq_agg,
            generated_images=gen_images,
            listing=listing,
            public_base_url=public_base_url,
        )

        # Send summary text
        send_text(phone, result.summary_text)
        await _append_message(
            phone_number=phone,
            role="assistant",
            message_text=result.summary_text,
            listing_id=listing_id,
            model="pipeline_result",
            usage=None,
        )

        # Send images (one per message for WhatsApp reliability)
        for url, caption in zip(result.image_urls, result.image_captions):
            try:
                send_media(phone, caption, [url])
            except Exception as img_exc:
                logger.warning("WhatsApp image send failed | url=%s | error=%s", url, img_exc)

        # Update conversation status
        await _update_conversation(conv_id, {
            "status": "delivered",
            "result_summary": {
                "summary_text": result.summary_text,
                "images_sent": len(result.image_urls),
            },
        })
        await _update_user_profile(phone, {"last_listing_id": int(listing_id)})

        logger.info("WhatsApp results delivered | listing_id=%s | conv_id=%s", listing_id, conv_id)
        return True

    except Exception as exc:
        logger.error(
            "WhatsApp delivery failed | listing_id=%s | conv_id=%s | error=%s",
            listing_id, conv_id, exc,
        )
        await _update_conversation(conv_id, {
            "status": "failed",
            "error_message": str(exc),
        })
        return False
