#!/usr/bin/env python3
"""
Generate image assets for scope.html landing page via Gemini image generation.

Uses the pro-image model (gemini-2.5-flash-image) for pure text-to-image generation.
No input image — just a text prompt with responseModalities: ['IMAGE'].

Output: lean-mvp/frontend/public/images/scope/
Cost:   ~5 images x ~$0.04 = ~$0.20
"""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

pass  # Recipient runtime supplies its explicit private environment.

os.environ["PIPELINE_STRICT_GEMINI_USAGE_METADATA"] = "false"
os.environ["PIPELINE_STRICT_GEMINI_COST_DB_WRITE"] = "false"
os.environ["PIPELINE_STRICT_GEMINI_PRICING"] = "false"

from pipeline.gemini_client import get_api_key, MODELS, _compress_to_jpeg

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "frontend/public/images/scope"

IMAGES = [
    {
        "name": "boiler-photo",
        "prompt": (
            "Generate a photorealistic photo taken with a smartphone by a plumber "
            "during a site visit. The photo shows an old domestic hot water cylinder "
            "(copper, slightly corroded fittings) inside an airing cupboard in a "
            "Spanish Mediterranean apartment. The lighting is slightly dim with warm "
            "tones from an overhead bulb. The angle is slightly off-center and tilted, "
            "like someone quickly snapped it with one hand. There are pipes running "
            "along the wall, and the cupboard shelves have some towels on them. "
            "The photo should feel completely authentic — like a real tradesperson's "
            "WhatsApp photo, not a stock image. 4:3 aspect ratio."
        ),
    },
    {
        "name": "scope-cylinder",
        "prompt": (
            "Generate a photorealistic close-up photo of a domestic hot water "
            "cylinder (Megaflo or similar unvented type, white/cream enamel body) "
            "with aged copper fittings and valves visible at the top. Taken in a "
            "Spanish apartment utility cupboard. Clean, well-lit service-photo style "
            "as if documenting the unit for a work report. Natural overhead lighting. "
            "Sharp focus on the cylinder and fittings. Square 1:1 aspect ratio. "
            "Photorealistic, not illustrated."
        ),
    },
    {
        "name": "scope-pipework",
        "prompt": (
            "Generate a photorealistic close-up photo of copper pipework and brass "
            "valve connections behind a domestic hot water cylinder. The pipes show "
            "some patina and age but are functional. A couple of isolation valves are "
            "visible. The background is a plastered wall in a Spanish apartment utility "
            "space. Well-lit, clear, practical service documentation photo style. "
            "Square 1:1 aspect ratio. Photorealistic."
        ),
    },
    {
        "name": "scope-cupboard",
        "prompt": (
            "Generate a photorealistic full-view photo of an airing cupboard in a "
            "Spanish apartment, door open, showing a hot water tank with lagging "
            "insulation. Some copper pipes are visible running along the walls. There "
            "is a small shelf above with towels. The cupboard is in a hallway with "
            "tiled floor visible at the bottom. Natural lighting from the hallway. "
            "Taken straight-on for documentation purposes. Square 1:1 aspect ratio. "
            "Photorealistic."
        ),
    },
    {
        "name": "hero-og",
        "prompt": (
            "Generate a modern, minimal editorial illustration for a tech product "
            "landing page. Split composition on a warm cream background (#FAF8F4): "
            "on the left side, a smartphone showing a WhatsApp-style chat with a "
            "voice note waveform in green (#25D366). On the right side, a clean "
            "professional document/scope of work with neat line items and a teal "
            "accent color (#115E59). Between them, a subtle arrow or flow indicator "
            "suggesting transformation. The overall feel is warm, premium, and "
            "trustworthy — like a fintech or proptech brand. Light drop shadows. "
            "16:9 aspect ratio. Modern flat design with subtle depth."
        ),
    },
]


async def generate_text_to_image(prompt: str, output_name: str) -> bool:
    """Generate an image from a text-only prompt (no input image)."""
    logger.info("Generating: %s", output_name)
    logger.info("  Prompt: %s...", prompt[:100])

    model_name = MODELS.get("pro-image", "gemini-2.5-flash-image")
    api_key = get_api_key()

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 1.0,
            "topP": 0.95,
            "maxOutputTokens": 8192,
            "responseModalities": ["IMAGE"],
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
        ],
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    logger.info("  Calling %s ...", model_name)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url, json=body, headers={"Content-Type": "application/json"}
            )

            if not response.is_success:
                logger.error("  HTTP %d: %s", response.status_code, response.text[:300])
                return False

            data = response.json()
            if not isinstance(data, dict):
                data = data[0] if isinstance(data, list) and data else {}

            candidates = data.get("candidates", [])
            for candidate in candidates:
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        image_b64 = part["inlineData"]["data"]
                        compressed_b64, mime = _compress_to_jpeg(image_b64, quality=85)

                        out_path = OUTPUT_DIR / f"{output_name}.jpg"
                        out_path.write_bytes(base64.b64decode(compressed_b64))
                        size_kb = out_path.stat().st_size // 1024
                        logger.info("  Saved: %s (%d KB)", out_path, size_kb)
                        return True

            text_parts = []
            for candidate in candidates:
                for part in candidate.get("content", {}).get("parts", []):
                    if "text" in part:
                        text_parts.append(part["text"])
            if text_parts:
                logger.warning("  Got text instead of image: %s", " ".join(text_parts)[:200])

            logger.error("  No image in response for %s", output_name)
            return False

    except Exception as exc:
        logger.exception("  Exception generating %s: %s", output_name, exc)
        return False


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output dir: %s", OUTPUT_DIR)
    logger.info("Model: %s", MODELS.get("pro-image", "NOT SET"))
    logger.info("Generating %d images...", len(IMAGES))

    succeeded = 0
    failed = 0
    for img in IMAGES:
        ok = await generate_text_to_image(img["prompt"], img["name"])
        if ok:
            succeeded += 1
        else:
            failed += 1

    logger.info("Done: %d succeeded, %d failed", succeeded, failed)
    if failed:
        logger.error("Some images failed. Re-run to retry.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
