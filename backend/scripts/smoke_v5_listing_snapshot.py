#!/usr/bin/env python3
"""
Smoke: V5 listing snapshot

Writes:
- unified_estimates: v5_listing_snapshot

Usage:
  python3 scripts/smoke_v5_listing_snapshot.py --listing-id 12 --force
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
from scripts._md_report import write_md_report  # noqa: E402
from workers.handlers import handle_v5_fetch_listing_snapshot  # noqa: E402

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

    job = {
        "id": f"smoke-{listing_id}-v5_listing_snapshot",
        "run_id": f"smoke_{listing_id}",
        "listing_id": listing_id,
        "stage": "snapshot",
        "job_type": "v5_fetch_listing_snapshot",
        "payload": {"force": force},
        "idempotency_key": f"smoke:{listing_id}:v5_fetch_listing_snapshot",
    }

    await handle_v5_fetch_listing_snapshot(job, db)
    snap = await db.get_unified_estimate(listing_id, "v5_listing_snapshot")

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_listing_snapshot_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Listing snapshot",
        meta={"listing_id": listing_id, "key_written": "v5_listing_snapshot"},
        sample=snap,
        payload={"v5_listing_snapshot": snap},
    )
    print({"stage": "v5_listing_snapshot", "listing_id": listing_id, "report_path": report_path})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

