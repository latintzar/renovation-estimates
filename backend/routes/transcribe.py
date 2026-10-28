"""
Voice Note Transcription (Local Whisper)
=========================================

POST /api/transcribe  --  accepts audio blob, returns text transcript.
Uses faster-whisper locally — zero API cost, ~1-3s for a short voice note.

Model: "small" for speed. Upgrade to "large-v3" if quality is lacking.
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading whisper model (small, int8)...")
        _whisper_model = WhisperModel("small", compute_type="int8")
        logger.info("Whisper model loaded")
    return _whisper_model


@router.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> JSONResponse:
    content = await audio.read()
    if not content:
        return JSONResponse({"error": "empty audio"}, status_code=400)

    if len(content) > 10 * 1024 * 1024:
        return JSONResponse({"error": "audio too large (max 10MB)"}, status_code=400)

    try:
        transcript, lang, elapsed = await asyncio.to_thread(_transcribe, content, audio.content_type or "")
        logger.info("Transcribed | lang=%s | %.1fs | %d chars | %s",
                     lang, elapsed, len(transcript), transcript[:80])

        if not transcript:
            return JSONResponse({"text": "", "empty": True})
        return JSONResponse({"text": transcript, "lang": lang})

    except Exception as exc:
        logger.error("Transcription error | %s", exc, exc_info=True)
        return JSONResponse({"error": "transcription failed"}, status_code=500)


def _transcribe(audio_bytes: bytes, content_type: str) -> tuple[str, str, float]:
    t0 = time.time()

    ext = "webm"
    if "ogg" in content_type:
        ext = "ogg"
    elif "mp4" in content_type or "m4a" in content_type:
        ext = "m4a"
    elif "wav" in content_type:
        ext = "wav"

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
        f.write(audio_bytes)
        src_path = Path(f.name)

    wav_path = src_path.with_suffix(".wav")
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(src_path), "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[:300]}")

        model = _get_model()
        segments, info = model.transcribe(
            str(wav_path),
            language=None,
            beam_size=3,
            vad_filter=True,
        )

        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        lang = getattr(info, "language", "")
        elapsed = time.time() - t0
        return transcript, lang, elapsed

    finally:
        for p in [src_path, wav_path]:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
