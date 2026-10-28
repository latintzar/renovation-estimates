#!/usr/bin/env python3
"""
Smoke: V5 decompose → work items (market_standard)

Writes:
- unified_estimates: v5_work_items_market_standard

Prereqs:
- unified_estimates: v5_delta_slots_market_standard

Usage:
  python3 scripts/smoke_v5_decompose_work_items.py --listing-id 12 --force
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
from workers.handlers import handle_v5_work_items_market_standard  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--concurrency", type=int, default=5)
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)
    concurrency = int(args.concurrency)
    if concurrency < 1:
        raise ValueError(f"--concurrency must be >= 1 (got {concurrency})")

    # Attach DB + job context so gemini_client can persist call usage rows.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    job = {
        "id": f"smoke-{listing_id}-v5_work_items",
        "run_id": f"smoke_{listing_id}",
        "listing_id": listing_id,
        "stage": "v5_decompose",
        "job_type": "v5_work_items_market_standard",
        "payload": {"force": force, "concurrency": concurrency},
        "idempotency_key": f"smoke:{listing_id}:v5_work_items_market_standard",
    }
    await handle_v5_work_items_market_standard(job, db)

    items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    sample = None
    if isinstance(items, dict):
        arr = items.get("items") or []
        sample = arr[:5] if isinstance(arr, list) else items

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_work_items_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Decompose to work items (market_standard)",
        meta={"listing_id": listing_id, "key_written": "v5_work_items_market_standard"},
        sample=sample,
        payload={"v5_work_items_market_standard": items},
    )
    print({"stage": "v5_decompose_work_items", "listing_id": listing_id, "report_path": report_path})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

