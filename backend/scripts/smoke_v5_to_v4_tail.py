#!/usr/bin/env python3
"""
Smoke: V5 → V4 tail (priced BOQ)

Runs:
- pricing.v5_run_market_standard.run_v5_market_standard (which calls V4 tail from V5 work items)

Writes (via orchestrator + V4 tail):
- unified_estimates: v5_selected_comparable, v5_delta_slots_market_standard, v5_work_items_market_standard
- unified_estimates: v4_* tail artifacts (matches, quant_plans, signals, summaries)
- boq_line_items (dimension="v4")

Usage:
  python3 scripts/smoke_v5_to_v4_tail.py --listing-id 12 --force
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
from pricing.v5_run_market_standard import run_v5_market_standard  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--max-comparables", type=int, default=5)
    p.add_argument("--max-photos-per-comparable", type=int, default=24)
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)

    # Attach DB + job context so gemini_client can persist call usage rows.
    # WHY THIS MATTERS: in strict mode, missing DB context aborts otherwise-successful calls.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    summary = await run_v5_market_standard(
        listing_id=listing_id,
        db=db,
        force=bool(args.force),
        max_comparables=int(args.max_comparables),
        max_photos_per_comparable=int(args.max_photos_per_comparable),
    )

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_to_v4_tail_listing_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — End-to-end to priced BOQ (via V4 tail)",
        meta={"listing_id": listing_id, "strategy_name": "market_standard"},
        sample=summary,
        payload=summary,
    )
    print({"stage": "v5_to_v4_tail", "listing_id": listing_id, "report_path": report_path})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

