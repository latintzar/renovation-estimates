#!/usr/bin/env python3
"""
Smoke script for Gemini image generation (manual).

WHY THIS EXISTS:
- Useful for debugging image generation locally.
- Must NOT be collected by pytest (so `python -m pytest` stays non-interactive).
"""

import asyncio
import base64
import sys
from pathlib import Path


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    repo_root = Path(__file__).resolve().parents[3]  # /root/puedo_casa
    lean_root = repo_root / "lean-mvp"
    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.


async def main() -> None:
    _load_env()

    from pipeline.gemini_client import call_gemini_image, fetch_image_as_base64, MODELS

    print("=" * 60, flush=True)
    print("TESTING GEMINI IMAGE GENERATION", flush=True)
    print("=" * 60, flush=True)
    print(f"\nModel configured: {MODELS.get('pro-image', 'NOT SET')}", flush=True)

    test_image_url = "https://img4.idealista.com/blur/WEB_DETAIL/0/id.pro.es.image.master/03/2e/01/1395809227.jpg"
    print(f"\nFetching test image: {test_image_url}", flush=True)
    image_data = await fetch_image_as_base64(test_image_url)
    if not image_data:
        raise RuntimeError("Failed to fetch test image")

    prompt = (
        "Transform this room photo to show a modern renovation.\n\n"
        "CHANGES TO APPLY:\n"
        "- Fresh white paint on all walls\n"
        "- Modern laminate flooring\n"
        "- Updated lighting fixtures\n"
        "- Clean, minimal style\n\n"
        "Keep the EXACT same camera angle and room geometry.\n"
        "Output a photorealistic result."
    )

    print("\nCalling image generation...", flush=True)
    result = await call_gemini_image(
        prompt=prompt,
        image_data=image_data["data"],
        image_mime_type=image_data["mime_type"],
        model="pro-image",
        temperature=1.0,
    )

    print("\nResult:", flush=True)
    print(f"  success={result.get('success')}", flush=True)
    if not result.get("success"):
        raise RuntimeError(f"Image generation failed: {result.get('error')}")

    out_path = Path("/tmp/test_after_image.png")
    out_path.write_bytes(base64.b64decode(result["image_data"]))
    print(f"Saved image to: {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

