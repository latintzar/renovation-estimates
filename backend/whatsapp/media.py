"""
WhatsApp Inbound Media Helpers
=============================

Handles inbound Twilio media URLs (images, voice notes, videos):
- Download media from Twilio (requires auth)
- Enforce size limits (avoid runaway storage/cost)
- Upload to Supabase Storage (public bucket: whatsapp-media)
- For videos: extract a single thumbnail frame via ffmpeg

WHY THIS MATTERS:
Users message WhatsApp like they message a friend — screenshots, voice notes,
and videos. Persisting these attachments lets:
- the agent "see" them in later turns
- the admin UI inspect what happened behind the scenes
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)


MAX_MEDIA_BYTES_DEFAULT = 20 * 1024 * 1024  # 20MB


def classify_media(content_type: str) -> str:
    ct = (content_type or "").strip().lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("audio/"):
        return "audio"
    if ct.startswith("video/"):
        return "video"
    return "unknown"


def _safe_slug(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return "unknown"
    s = s.replace("+", "plus")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:80] or "unknown"


def _guess_extension(content_type: str) -> str:
    ct = (content_type or "").strip().lower()
    if ct == "image/jpeg" or ct == "image/jpg":
        return "jpg"
    if ct == "image/png":
        return "png"
    if ct == "image/webp":
        return "webp"
    if ct in ("audio/ogg", "audio/opus", "audio/ogg; codecs=opus"):
        return "ogg"
    if ct in ("audio/mpeg", "audio/mp3"):
        return "mp3"
    if ct == "audio/wav":
        return "wav"
    if ct == "video/mp4":
        return "mp4"
    if ct in ("video/quicktime", "video/mov"):
        return "mov"
    # Fallback: best-effort
    return "bin"


async def download_twilio_media(
    *,
    url: str,
    max_bytes: int = MAX_MEDIA_BYTES_DEFAULT,
    timeout_s: int = 60,
) -> bytes:
    """
    Download a media item from Twilio's MediaUrl.

    Twilio's MediaUrl endpoints require HTTP Basic Auth:
      username = TWILIO_ACCOUNT_SID
      password = TWILIO_AUTH_TOKEN
    """
    if not url or not isinstance(url, str):
        raise ValueError("download_twilio_media: url is required")
    if max_bytes <= 0:
        raise ValueError(f"download_twilio_media: invalid max_bytes={max_bytes}")
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials missing (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)")

    logger.info("Downloading Twilio media | url=%s... | max_bytes=%d", url[:60], max_bytes)

    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    total = 0
    chunks: list[bytes] = []
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        async with client.stream("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Twilio media exceeds max size ({total} > {max_bytes} bytes)")
                chunks.append(chunk)
    data = b"".join(chunks)
    logger.info("Downloaded Twilio media | bytes=%d", len(data))
    return data


async def upload_to_storage(
    *,
    data: bytes,
    content_type: str,
    filename: str,
    bucket: str = "whatsapp-media",
    upsert: bool = True,
    timeout_s: int = 120,
) -> str:
    """
    Upload to Supabase Storage and return a public URL.
    """
    if not data:
        raise ValueError("upload_to_storage: data is empty")
    if not content_type:
        raise ValueError("upload_to_storage: content_type is required")
    if not filename:
        raise ValueError("upload_to_storage: filename is required")
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    if not key:
        raise RuntimeError("Supabase key missing (SUPABASE_SERVICE_ROLE_KEY or NEXT_PUBLIC_SUPABASE_ANON_KEY)")

    storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{filename}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type,
        "x-upsert": "true" if upsert else "false",
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(storage_url, content=data, headers=headers)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed: {resp.status_code} {(resp.text or '')[:300]}")

    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}"


async def persist_twilio_media(
    *,
    phone_number: str,
    twilio_url: str,
    content_type: str,
    listing_id: Optional[int] = None,
    max_bytes: int = MAX_MEDIA_BYTES_DEFAULT,
    max_base64_bytes: int = 6 * 1024 * 1024,  # 6MB
) -> Tuple[str, str, str, str]:
    """
    Download from Twilio and upload to Supabase storage.

    Returns:
      (public_url, content_type, media_kind, base64_data)

    NOTE: We return base64 for immediate Gemini inline_data usage when the payload
    is reasonably sized. For large media we return an empty string; the caller can
    fetch from storage later if needed.
    """
    data = await download_twilio_media(url=twilio_url, max_bytes=max_bytes)
    media_kind = classify_media(content_type)
    ext = _guess_extension(content_type)

    sha = hashlib.sha256(data).hexdigest()[:12]
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    phone_slug = _safe_slug(phone_number)
    listing_part = f"listing-{int(listing_id)}" if listing_id is not None else "listing-unknown"

    filename = f"{listing_part}/{phone_slug}/{now}_{sha}.{ext}"
    public_url = await upload_to_storage(
        data=data,
        content_type=content_type,
        filename=filename,
        bucket="whatsapp-media",
        upsert=True,
    )
    b64 = ""
    if len(data) <= max(0, int(max_base64_bytes)):
        b64 = base64.b64encode(data).decode("ascii")
    return public_url, content_type, media_kind, b64


def extract_video_thumbnail(video_bytes: bytes) -> bytes:
    """
    Extract a single thumbnail frame as JPEG using ffmpeg.

    WHY THIS MATTERS: we don't want to feed full video into Gemini by default;
    a single frame is cheap and still provides context.
    """
    if not video_bytes:
        raise ValueError("extract_video_thumbnail: video_bytes is empty")

    ffmpeg = os.getenv("FFMPEG_BIN", "ffmpeg")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as f:
        f.write(video_bytes)
        f.flush()

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            f.name,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"ffmpeg thumbnail extraction failed (code={proc.returncode}): {err}")
        if not proc.stdout:
            raise RuntimeError("ffmpeg returned empty thumbnail data")
        return proc.stdout

