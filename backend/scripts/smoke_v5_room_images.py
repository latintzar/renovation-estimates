#!/usr/bin/env python3
"""
Smoke: V5 Room Images — before/after renovation renderings
===========================================================

Reads existing V5 artifacts (BOQ, ELI5, delta, photo clusters) and
generates before/after images. No need to re-run the full pipeline.

Each image costs ~$0.05 (flash prompt gen + flash-image edit). Default: top 10 rooms.

Writes:
- unified_estimates: v5_generated_images_market_standard

Usage:
  python3 scripts/smoke_v5_room_images.py --listing-id 12
  python3 scripts/smoke_v5_room_images.py --listing-id 12 --force --max-rooms 3
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import call_gemini, call_gemini_image, call_gemini_json, set_gemini_tracking_context  # noqa: E402
from pricing.v5_room_images import generate_v5_room_images  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--dump-prompts", action="store_true",
                   help="Print the transformation prompts for each room (for quality review)")
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    strategy_name = "market_standard"

    # Attach DB + job context so gemini_client can persist call usage rows.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    # Check for existing (unless --force)
    img_key = f"v5_generated_images_{strategy_name}"
    if not args.force:
        existing = await db.get_unified_estimate(listing_id, img_key)
        if isinstance(existing, dict) and existing.get("generated_images"):
            ok = sum(1 for i in existing["generated_images"] if i.get("after_data"))
            logger.info("Room images already exist (%d images, use --force to regenerate)", ok)
            print(json.dumps({"stage": "v5_room_images", "listing_id": listing_id, "status": "reused", "images": ok}, indent=2))
            return 0

    # Load required artifacts
    boq_key = f"v2_{strategy_name}"
    boq_agg = await db.get_unified_estimate(listing_id, boq_key)
    if not boq_agg or not boq_agg.get("line_items"):
        logger.error("No BOQ found at key '%s' — run smoke_v5_to_v4_tail first", boq_key)
        return 1

    photo_clusters = await db.get_photo_clusters(listing_id)
    if not photo_clusters:
        logger.error("No photo_clusters for listing %s", listing_id)
        return 1

    eli5 = await db.get_unified_estimate(listing_id, f"v5_eli5_{strategy_name}")
    delta_slots = await db.get_unified_estimate(listing_id, f"v5_delta_slots_{strategy_name}")

    logger.info(
        "Starting Room Images | listing_id=%s | clusters=%d | eli5=%s | delta=%s",
        listing_id, len(photo_clusters),
        "yes" if eli5 else "no",
        "yes" if delta_slots else "no",
    )

    result = await generate_v5_room_images(
        listing_id=listing_id,
        strategy_name=strategy_name,
        photo_clusters=photo_clusters,
        boq_aggregation=boq_agg,
        eli5=eli5,
        delta_slots=delta_slots,
        db=db,
        call_gemini_image=call_gemini_image,
        call_gemini_json=call_gemini_json,
        call_gemini=call_gemini,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("ROOM IMAGES SUMMARY")
    print("=" * 60)
    for img in result.get("generated_images", []):
        status = "OK" if img.get("after_data") else f"FAIL: {img.get('error', '?')}"
        size = f"({len(img['after_data']) * 3 // 4 // 1024}KB)" if img.get("after_data") else ""
        print(f"  {img.get('room_name', '?'):25s}  [{status}] {size}")
    print(f"\n  Generated: {result.get('images_generated', 0)}")
    print(f"  Failed:    {result.get('images_failed', 0)}")
    print("=" * 60)

    # Optionally dump prompts for quality review
    if args.dump_prompts:
        print("\n" + "=" * 60)
        print("TRANSFORMATION PROMPTS (for quality review)")
        print("=" * 60)
        for img in result.get("generated_images", []):
            prompt = img.get("transformation_prompt", "")
            if not prompt:
                continue
            room = img.get("room_name", "?")
            print(f"\n{'─' * 60}")
            print(f"ROOM: {room}")
            print(f"{'─' * 60}")
            print(prompt)
        print("\n" + "=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
