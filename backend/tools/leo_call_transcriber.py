"""
Leo Call Transcriber — Local Whisper + AWS Speaker Segments
============================================================

HOW IT WORKS (the recipe that actually works — don't reinvent this):

1. Download the Twilio conference recording (MP3, authenticated).
2. Convert to WAV 16kHz mono (required by faster-whisper).
3. Run faster-whisper large-v3 locally → high quality text with timestamps.
4. Upload MP3 to S3 → kick off AWS Transcribe with ShowSpeakerLabels → speaker IDs.
5. Poll AWS Transcribe until done, download the transcript JSON.
6. STITCH: for each Whisper segment, find the AWS speaker label active at that time.
   → Result: Whisper-quality text tagged with AWS speaker labels.
7. Generate highlights + suggested next moves via Gemini flash.
8. Return a complete call_memory dict ready for the Gordon Ramsay debrief.

WHY TWO TRANSCRIPTION ENGINES:
- Whisper large-v3 gives MUCH better text (filler words, punctuation, accuracy).
- AWS Transcribe gives MUCH better speaker diarization (who said what).
- Neither does both well alone. Stitching them gives Whisper text + AWS speakers.

DEPENDENCIES:
- faster-whisper (pip install faster-whisper) — already in .venv
- boto3 (pip install boto3) — for AWS Transcribe + S3
- ffmpeg — for audio conversion (apt install ffmpeg)

Usage:
    from tools.leo_call_transcriber import process_recording
    call_memory = await process_recording(
        recording_url="https://api.twilio.com/...",
        recording_sid="RE...",
        conference_name="myproject-call-1",
        project_id="myproject",
    )
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment helpers (same pattern as leo_conference_call.py)
# ---------------------------------------------------------------------------

def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env.local"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[3] / ".env.local"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    except Exception as exc:
        logger.debug("leo_call_transcriber: .env.local load failed (non-fatal) | err=%s", exc)


def _get_twilio_auth() -> Tuple[str, str]:
    _load_env()
    sid = str(os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    token = str(os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    if not sid or not token:
        raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
    return sid, token


def _get_aws_config() -> Dict[str, str]:
    _load_env()
    return {
        "region": str(os.environ.get("AWS_REGION") or "us-east-1").strip(),
        "bucket": str(os.environ.get("AWS_S3_BUCKET") or "puedo-casa-html-archive").strip(),
        "access_key": str(os.environ.get("AWS_ACCESS_KEY_ID") or "").strip(),
        "secret_key": str(os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Step 1: Download Twilio recording
# ---------------------------------------------------------------------------

def download_recording(recording_url: str, recording_sid: str) -> Path:
    """
    Download a Twilio conference recording as MP3.

    WHY THIS MATTERS: Twilio recording URLs need Basic auth.
    The recording URL from the webhook is like:
      https://api.twilio.com/2010-04-01/Accounts/{sid}/Recordings/{RecordingSid}
    Append .mp3 to get the file.
    """
    sid, token = _get_twilio_auth()

    url = recording_url.rstrip("/")
    if not url.endswith(".mp3"):
        url += ".mp3"

    auth_str = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth_str}"})

    out_path = Path(f"/tmp/leo_recording_{recording_sid}.mp3")
    logger.info("Downloading recording | sid=%s | url=%s", recording_sid, url[:120])

    resp = urllib.request.urlopen(req, timeout=120)
    data = resp.read()
    if not data or len(data) < 1000:
        raise RuntimeError(f"Recording download too small ({len(data)} bytes) — possibly empty or auth failed")

    out_path.write_bytes(data)
    logger.info("Recording saved | path=%s | size=%d bytes", out_path, len(data))
    return out_path


# ---------------------------------------------------------------------------
# Step 2: Convert to WAV (for Whisper)
# ---------------------------------------------------------------------------

def convert_to_wav(mp3_path: Path) -> Path:
    """Convert MP3 to 16kHz mono WAV (optimal for Whisper)."""
    wav_path = mp3_path.with_suffix(".wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path),
    ]
    logger.info("Converting to WAV | src=%s", mp3_path.name)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")
    if not wav_path.exists() or wav_path.stat().st_size < 100:
        raise RuntimeError(f"WAV conversion produced empty file: {wav_path}")
    logger.info("WAV ready | path=%s | size=%d", wav_path.name, wav_path.stat().st_size)
    return wav_path


# ---------------------------------------------------------------------------
# Step 3: Run faster-whisper locally
# ---------------------------------------------------------------------------

def run_whisper(wav_path: Path) -> List[Dict[str, Any]]:
    """
    Run faster-whisper large-v3 on the audio file.

    Returns list of segments: [{start, end, text}, ...]

    WHY large-v3: It captures filler words, punctuation, and nuance that
    smaller models miss. On this server (Hetzner), int8 runs fast enough.
    """
    from faster_whisper import WhisperModel

    logger.info("Starting Whisper transcription | model=large-v3 | path=%s", wav_path.name)
    t0 = time.time()

    model = WhisperModel("large-v3", compute_type="int8")
    segments_gen, info = model.transcribe(
        str(wav_path),
        language=None,  # auto-detect
        beam_size=5,
        word_timestamps=False,
        vad_filter=True,
    )

    segments = []
    for seg in segments_gen:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })

    elapsed = time.time() - t0
    logger.info(
        "Whisper done | segments=%d | language=%s | duration=%.1fs | elapsed=%.1fs",
        len(segments),
        getattr(info, "language", "?"),
        getattr(info, "duration", 0),
        elapsed,
    )
    return segments


# ---------------------------------------------------------------------------
# Step 4: Upload to S3 + Start AWS Transcribe
# ---------------------------------------------------------------------------

def upload_to_s3(mp3_path: Path, s3_key: str) -> str:
    """Upload the MP3 to S3 and return the s3:// URI."""
    import boto3

    aws = _get_aws_config()
    s3 = boto3.client(
        "s3",
        region_name=aws["region"],
        aws_access_key_id=aws["access_key"],
        aws_secret_access_key=aws["secret_key"],
    )
    bucket = aws["bucket"]

    logger.info("Uploading to S3 | bucket=%s | key=%s", bucket, s3_key)
    s3.upload_file(str(mp3_path), bucket, s3_key, ExtraArgs={"ContentType": "audio/mpeg"})
    uri = f"s3://{bucket}/{s3_key}"
    logger.info("S3 upload complete | uri=%s", uri)
    return uri


def start_aws_transcribe(s3_uri: str, job_name: str) -> str:
    """
    Start an AWS Transcribe job with speaker labels enabled.

    Returns the job_name for polling.
    """
    import boto3

    aws = _get_aws_config()
    client = boto3.client(
        "transcribe",
        region_name=aws["region"],
        aws_access_key_id=aws["access_key"],
        aws_secret_access_key=aws["secret_key"],
    )

    logger.info("Starting AWS Transcribe | job=%s | uri=%s", job_name, s3_uri)

    client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp3",
        IdentifyLanguage=True,
        Settings={
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 2,
        },
        OutputBucketName=aws["bucket"],
        OutputKey=f"call-transcripts/{job_name}.json",
    )
    logger.info("AWS Transcribe job started | job=%s", job_name)
    return job_name


def poll_aws_transcribe(job_name: str, timeout_s: int = 300) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Poll AWS Transcribe until the job completes or fails.

    Returns: (transcript_json, job_metadata)
    job_metadata includes MediaDurationInSeconds so we can calculate exact cost.
    """
    import boto3

    aws = _get_aws_config()
    client = boto3.client(
        "transcribe",
        region_name=aws["region"],
        aws_access_key_id=aws["access_key"],
        aws_secret_access_key=aws["secret_key"],
    )
    s3 = boto3.client(
        "s3",
        region_name=aws["region"],
        aws_access_key_id=aws["access_key"],
        aws_secret_access_key=aws["secret_key"],
    )

    start = time.time()
    job_data = {}
    while True:
        resp = client.get_transcription_job(TranscriptionJobName=job_name)
        job_data = resp.get("TranscriptionJob", {})
        status = job_data.get("TranscriptionJobStatus", "UNKNOWN")
        logger.info("AWS Transcribe poll | job=%s | status=%s | elapsed=%.0fs", job_name, status, time.time() - start)

        if status == "COMPLETED":
            break
        elif status == "FAILED":
            reason = job_data.get("FailureReason", "unknown")
            raise RuntimeError(f"AWS Transcribe failed | job={job_name} | reason={reason}")
        elif time.time() - start > timeout_s:
            raise RuntimeError(f"AWS Transcribe timeout | job={job_name} | elapsed={time.time() - start:.0f}s")

        time.sleep(5)

    # Extract actual cost from MediaDurationInSeconds.
    # AWS Transcribe pricing: $0.024/min (standard batch, Tier 1).
    media_duration_s = float(job_data.get("MediaDurationInSeconds", 0))
    aws_cost_usd = (media_duration_s / 60.0) * 0.024
    logger.info(
        "AWS Transcribe cost | job=%s | duration=%.1fs (%.1f min) | cost=$%.4f",
        job_name, media_duration_s, media_duration_s / 60.0, aws_cost_usd,
    )

    job_metadata = {
        "media_duration_seconds": media_duration_s,
        "media_duration_minutes": round(media_duration_s / 60.0, 2),
        "aws_transcribe_cost_usd": round(aws_cost_usd, 6),
        "language_code": str(job_data.get("LanguageCode") or ""),
        "identified_language": str(
            (job_data.get("LanguageCodes") or [{}])[0].get("LanguageCode", "")
            if job_data.get("LanguageCodes") else ""
        ),
    }

    # Download transcript from S3.
    bucket = aws["bucket"]
    key = f"call-transcripts/{job_name}.json"
    logger.info("Downloading transcript | bucket=%s | key=%s", bucket, key)

    obj = s3.get_object(Bucket=bucket, Key=key)
    transcript_json = json.loads(obj["Body"].read().decode("utf-8"))
    logger.info("Transcript downloaded | items=%d", len(transcript_json.get("results", {}).get("items", [])))
    return transcript_json, job_metadata


def extract_aws_speaker_segments(transcript_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract speaker-labelled segments from AWS Transcribe output.

    Returns: [{start_time, end_time, speaker_label, content}, ...]
    """
    results = transcript_json.get("results", {})
    speaker_labels = results.get("speaker_labels", {})
    segments = speaker_labels.get("segments", [])

    out = []
    for seg in segments:
        start_t = float(seg.get("start_time", 0))
        end_t = float(seg.get("end_time", 0))
        speaker = str(seg.get("speaker_label", "unknown"))

        # Each segment has items (words) — join them for the content.
        items = seg.get("items", [])
        words = []
        for item in items:
            content = str(item.get("content", "")).strip()
            if content:
                words.append(content)
        content = " ".join(words)

        out.append({
            "start_time": start_t,
            "end_time": end_t,
            "speaker_label": speaker,
            "content": content,
        })

    logger.info("AWS speaker segments extracted | count=%d | speakers=%s",
                len(out), list(set(s["speaker_label"] for s in out)))
    return out


# ---------------------------------------------------------------------------
# Step 5: Stitch Whisper text + AWS speakers
# ---------------------------------------------------------------------------

def stitch_transcripts(
    whisper_segments: List[Dict[str, Any]],
    aws_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Combine Whisper text quality with AWS speaker diarization.

    HOW IT WORKS:
    For each Whisper segment (which has great text), find the AWS speaker
    segment that overlaps the most in time. Tag the Whisper text with that
    speaker label. This gives us the best of both worlds.

    WHY THIS WORKS:
    - Whisper captures filler words, punctuation, accents perfectly.
    - AWS Transcribe nails speaker identification but its text is mediocre.
    - Time alignment bridges them: same audio, same timestamps, different strengths.
    """
    if not aws_segments:
        # Fallback: no speaker info, just return Whisper segments as single speaker.
        return [
            {"start": s["start"], "end": s["end"], "speaker": "speaker_0", "text": s["text"]}
            for s in whisper_segments
        ]

    stitched = []
    for ws in whisper_segments:
        ws_start = ws["start"]
        ws_end = ws["end"]
        ws_mid = (ws_start + ws_end) / 2.0

        # Find the AWS segment whose time range contains the midpoint of this Whisper segment.
        best_speaker = "unknown"
        best_overlap = 0.0

        for aws_seg in aws_segments:
            overlap_start = max(ws_start, aws_seg["start_time"])
            overlap_end = min(ws_end, aws_seg["end_time"])
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = aws_seg["speaker_label"]

        # Fallback: if no overlap found, check which AWS segment contains the midpoint.
        if best_speaker == "unknown":
            for aws_seg in aws_segments:
                if aws_seg["start_time"] <= ws_mid <= aws_seg["end_time"]:
                    best_speaker = aws_seg["speaker_label"]
                    break

        stitched.append({
            "start": ws_start,
            "end": ws_end,
            "speaker": best_speaker,
            "text": ws["text"],
        })

    logger.info("Stitched %d segments | speakers=%s", len(stitched), list(set(s["speaker"] for s in stitched)))
    return stitched


def format_transcript_clean(stitched: List[Dict[str, Any]], speaker_map: Optional[Dict[str, str]] = None) -> str:
    """
    Format stitched segments into a clean, readable transcript.

    speaker_map: optional mapping like {"spk_0": "User", "spk_1": "Tradesperson"}
    """
    if not speaker_map:
        speaker_map = {}

    lines = []
    prev_speaker = None
    for seg in stitched:
        spk = speaker_map.get(seg["speaker"], seg["speaker"])
        text = seg["text"].strip()
        if not text:
            continue

        if spk != prev_speaker:
            lines.append(f"\n[{spk}]")
            prev_speaker = spk
        lines.append(text)

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Step 6: Generate highlights via Gemini
# ---------------------------------------------------------------------------

async def generate_highlights(
    transcript_clean: str,
    project_context: str = "",
) -> Dict[str, Any]:
    """
    Ask Gemini flash to extract highlights and suggested next moves.

    WHY THIS MATTERS: The debrief isn't about reading the transcript.
    It's about "what did you both agree on? what's still open? what should
    the user decide next?" — like a Gordon Ramsay check-in after service.
    """
    from pipeline.gemini_client import call_gemini

    prompt = f"""You're Leo, a renovation concierge who just facilitated a call between a homeowner and a tradesperson.

Below is the call transcript. Your job is to extract:

1. **highlights**: The 3-5 most important things discussed (agreements, prices mentioned, concerns raised, timelines, anything the user should remember).

2. **open_questions**: Things that weren't resolved or need follow-up.

3. **suggested_next_moves**: 2-3 concrete actions the user could take next (e.g., "ask for a written quote", "schedule the site visit for Thursday", "compare with another tradesperson").

4. **vibe_check**: In one sentence, how did the call go? (e.g., "The tradesperson sounded knowledgeable and keen — good vibe." or "Felt a bit evasive about timelines.")

Be concise. This will be used in a WhatsApp conversation, not a report.

{f"PROJECT CONTEXT: {project_context}" if project_context else ""}

TRANSCRIPT:
{transcript_clean[:12000]}

Return strict JSON:
{{
  "highlights": ["string", ...],
  "open_questions": ["string", ...],
  "suggested_next_moves": ["string", ...],
  "vibe_check": "string"
}}"""

    resp = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.3,
        max_tokens=2000,
        use_spanish=False,
        strict_db_write=False,
    )

    if not resp.success or not (resp.text or "").strip():
        logger.warning("Highlights generation failed | err=%s", getattr(resp, "error", ""))
        return {
            "highlights": ["Transcript available but auto-highlights failed."],
            "open_questions": [],
            "suggested_next_moves": ["Review the transcript and decide next steps."],
            "vibe_check": "Could not auto-assess — read the transcript.",
        }

    try:
        # Strip markdown fences if present.
        text = (resp.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception as exc:
        logger.warning("Highlights JSON parse failed | err=%s | raw=%s", exc, (resp.text or "")[:300])
        return {
            "highlights": ["Transcript available but auto-highlights failed."],
            "open_questions": [],
            "suggested_next_moves": ["Review the transcript and decide next steps."],
            "vibe_check": "Could not auto-assess — read the transcript.",
        }


# ---------------------------------------------------------------------------
# Main orchestrator: process_recording
# ---------------------------------------------------------------------------

async def process_recording(
    *,
    recording_url: str,
    recording_sid: str,
    conference_name: str,
    project_id: str,
    speaker_map: Optional[Dict[str, str]] = None,
    project_context: str = "",
) -> Dict[str, Any]:
    """
    Full pipeline: download → Whisper → AWS Transcribe → stitch → highlights.

    Returns a call_memory dict ready to store in leo_project_comms.call_memory.

    THIS IS THE FUNCTION THAT "GOT IT TO WORK". Don't reinvent this pipeline.
    If something breaks, debug here — the recipe is sound.
    """
    t_start = time.time()
    logger.info(
        "=== CALL TRANSCRIPTION PIPELINE START | project=%s | conf=%s | rec=%s ===",
        project_id, conference_name, recording_sid,
    )

    # Step 1: Download from Twilio
    mp3_path = await asyncio.to_thread(download_recording, recording_url, recording_sid)

    # Step 2: Convert to WAV for Whisper
    wav_path = await asyncio.to_thread(convert_to_wav, mp3_path)

    # Step 3: Run Whisper (CPU, takes ~30-60s for a 5-10 min call)
    whisper_segments = await asyncio.to_thread(run_whisper, wav_path)

    # Step 4: Upload to S3 + start AWS Transcribe (runs in parallel while we have Whisper text)
    s3_key = f"call-recordings/{project_id}/{recording_sid}.mp3"
    job_name = f"leo-{recording_sid}"[:200]

    s3_uri = await asyncio.to_thread(upload_to_s3, mp3_path, s3_key)
    await asyncio.to_thread(start_aws_transcribe, s3_uri, job_name)

    # Step 5: Poll AWS Transcribe (typically 30-90s)
    transcript_json, aws_job_meta = await asyncio.to_thread(poll_aws_transcribe, job_name, 300)
    aws_segments = extract_aws_speaker_segments(transcript_json)

    # Step 6: Stitch
    stitched = stitch_transcripts(whisper_segments, aws_segments)

    # Step 7: Format clean transcript
    transcript_clean = format_transcript_clean(stitched, speaker_map=speaker_map)

    # Step 8: Generate highlights
    highlights = await generate_highlights(transcript_clean, project_context=project_context)

    # Assemble call_memory with ACTUAL costs (not estimates).
    elapsed = time.time() - t_start

    # Cost breakdown — every cent tracked.
    # AWS Transcribe: from MediaDurationInSeconds (exact, from the API response).
    # Twilio voice: we don't have the exact Twilio cost here (it depends on call
    # duration which comes from Twilio's call-status webhook, not the recording webhook).
    # Gemini highlights: ~$0.002 per call (flash model, small prompt).
    # Whisper: $0.00 (local).
    aws_transcribe_cost = aws_job_meta.get("aws_transcribe_cost_usd", 0)
    gemini_highlights_cost_est = 0.002  # flash call, ~1K tokens
    total_pipeline_cost = round(aws_transcribe_cost + gemini_highlights_cost_est, 6)

    call_memory = {
        "transcript_clean": transcript_clean,
        "speaker_segments": stitched,
        "highlights": highlights.get("highlights", []),
        "open_questions": highlights.get("open_questions", []),
        "suggested_next_moves": highlights.get("suggested_next_moves", []),
        "vibe_check": highlights.get("vibe_check", ""),
        "whisper_model": "large-v3",
        "aws_job_name": job_name,
        "recording_sid": recording_sid,
        "conference_name": conference_name,
        "s3_uri": s3_uri,
        "processing_time_s": round(elapsed, 1),
        "whisper_segment_count": len(whisper_segments),
        "aws_segment_count": len(aws_segments),
        "stitched_segment_count": len(stitched),
        "cost_breakdown": {
            "aws_transcribe_usd": aws_transcribe_cost,
            "aws_media_duration_s": aws_job_meta.get("media_duration_seconds", 0),
            "aws_media_duration_min": aws_job_meta.get("media_duration_minutes", 0),
            "whisper_local_usd": 0.0,
            "gemini_highlights_est_usd": gemini_highlights_cost_est,
            "total_pipeline_usd": total_pipeline_cost,
            "note": "Twilio voice cost tracked separately via call-status webhook",
        },
    }

    logger.info(
        "=== CALL TRANSCRIPTION PIPELINE DONE | project=%s | elapsed=%.1fs | whisper=%d aws=%d stitched=%d ===",
        project_id, elapsed, len(whisper_segments), len(aws_segments), len(stitched),
    )

    # Clean up temp files (best-effort).
    for p in [mp3_path, wav_path]:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass

    return call_memory


# ---------------------------------------------------------------------------
# CLI for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Leo Call Transcriber — manual test")
    parser.add_argument("--recording-url", required=True, help="Twilio recording URL")
    parser.add_argument("--recording-sid", required=True, help="Twilio RecordingSid")
    parser.add_argument("--project-id", default="test-project", help="Project ID")
    parser.add_argument("--conference-name", default="test-call-1", help="Conference name")
    args = parser.parse_args()

    async def _main() -> None:
        result = await process_recording(
            recording_url=args.recording_url,
            recording_sid=args.recording_sid,
            conference_name=args.conference_name,
            project_id=args.project_id,
        )
        print("\n=== CALL MEMORY ===")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:8000])

    asyncio.run(_main())
