#!/usr/bin/env python3
"""
Generate a Vinterior coffee table render inside Paloma's living room.
Uses Gemini 2.5 Flash Image to composite the furniture into the space.
"""

import asyncio
import base64
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("PIPELINE_STRICT_GEMINI_USAGE_METADATA", "false")
os.environ.setdefault("PIPELINE_STRICT_GEMINI_COST_DB_WRITE", "false")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
LEO_APP = REPO_ROOT / "lean-mvp" / "leo-copilot"
LIVING_ROOM = LEO_APP / "assets" / "images" / "rooms" / "malaga-livingroom-1.png"
PRODUCT_PHOTO = LEO_APP / "assets" / "images" / "foryou" / "auctionet-product-coffeetable.jpg"
OUTPUT_DIR = LEO_APP / "assets" / "images" / "foryou"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.


async def main() -> None:
    _load_env()

    from pipeline.gemini_client import call_gemini_image, MODELS

    logger.info("Model: %s", MODELS.get("pro-image", "NOT SET"))

    if not LIVING_ROOM.exists():
        raise FileNotFoundError(f"Living room image not found: {LIVING_ROOM}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    living_room_b64 = base64.b64encode(LIVING_ROOM.read_bytes()).decode()
    logger.info("Loaded living room image: %d bytes", len(living_room_b64))

    render_prompt = (
        "Edit this living room photo. Replace the existing small round coffee table with a "
        "Johannes Andersen rectangular rosewood coffee table from the 1960s, made by C.F. "
        "Christensen in Denmark.\n\n"
        "THE NEW TABLE LOOKS LIKE THIS:\n"
        "- Rectangular top, 160cm wide x 60cm deep, made of rich dark rosewood\n"
        "- Four elegant tapered solid rosewood legs\n"
        "- Horizontal cross-stretchers connecting the legs on each side\n"
        "- Pull-out extensions hidden at both short ends\n"
        "- Height approximately 51cm\n"
        "- The rosewood has a warm reddish-brown grain\n\n"
        "CRITICAL:\n"
        "- Place the table on the jute rug in front of the beige sofa, exactly where the "
        "current round table sits\n"
        "- Keep EVERYTHING else identical: sofa, rug, olive tree, curtains, walls, "
        "lighting, AC unit, pendant lamp, camera angle\n"
        "- Correct perspective and shadows matching the natural window light\n"
        "- Photorealistic — it must look like the table was actually photographed here\n"
        "- Output the SAME photo dimensions, just with the new table"
    )

    logger.info("Generating render: Auctionet table in living room...")
    result = await call_gemini_image(
        prompt=render_prompt,
        image_data=living_room_b64,
        image_mime_type="image/png",
        model="pro-image",
        temperature=1.0,
    )

    if not result.get("success"):
        raise RuntimeError(f"Render generation failed: {result.get('error')}")

    render_path = OUTPUT_DIR / "auctionet-render-livingroom.png"
    render_path.write_bytes(base64.b64decode(result["image_data"]))
    logger.info("Saved render to: %s (%d bytes)", render_path, render_path.stat().st_size)

    logger.info("Done! Both images generated successfully.")


if __name__ == "__main__":
    asyncio.run(main())
