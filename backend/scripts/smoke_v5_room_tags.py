#!/usr/bin/env python3
"""
Smoke: V5 room tags (deterministic tags derived from canonical clusters)

Writes:
- unified_estimates: v5_room_tags

Prereqs:
- photo_clusters exists (from V5 clustering)

Usage:
  python3 scripts/smoke_v5_room_tags.py --listing-id 12 --force
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import set_gemini_tracking_context  # noqa: E402
from pricing.v5_room_tags import build_room_tags_v5  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)

    # Attach DB + job context so gemini_client can persist call usage rows.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_room_tags")
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        logger.info("v5_room_tags: skip (exists) | listing_id=%s rooms=%s", listing_id, len(existing.get("rooms") or []))
        return 0

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"v5_room_tags: missing photo_clusters | listing_id={listing_id}")

    tags = build_room_tags_v5(listing_id=listing_id, clusters=clusters)
    out = {
        **tags,
        "schema_version": "v5_room_tags_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"rooms": len(tags.get("rooms") or [])},
    }
    ok = await db.save_unified_estimate(listing_id, "v5_room_tags", out)
    if not ok:
        raise RuntimeError(f"v5_room_tags: save failed | listing_id={listing_id}")

    sample = (out.get("rooms") or [])[:2]
    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_room_tags_listing_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Room tags (deterministic)",
        meta={"listing_id": listing_id, "key_written": "v5_room_tags", "rooms": len(out.get("rooms") or [])},
        sample=sample[0] if sample else None,
        payload=out,
    )
    print({"stage": "v5_room_tags", "listing_id": listing_id, "report_path": report_path, "rooms": len(out.get("rooms") or [])})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

