#!/usr/bin/env python3
"""
Smoke: V5 work_items -> V4 tail (priced BOQ)

Runs ONLY the V4 tail starting from existing V5 work items:
- pricing.v4_quantification_pipeline.run_v4_tail_from_v5_work_items

WHY THIS EXISTS:
- `smoke_v5_to_v4_tail.py` runs the full V5 orchestrator and can regenerate PIR/delta when forced.
- This smoke is the "start after decomposition" path.

Prereqs:
- unified_estimates: v5_work_items_market_standard

Writes (via V4 tail):
- unified_estimates: v4_* tail artifacts (matches, quant_plans, signals, summaries)
- boq_line_items (dimension="v4")
- unified_estimates: v2_market_standard (aggregated BOQ for frontend)

Usage:
  .venv/bin/python scripts/smoke_v5_work_items_to_v4_tail.py --listing-id 12 --force
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
from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch, set_gemini_tracking_context  # noqa: E402
from pricing.embedding_runtime import embed_texts  # noqa: E402
from pricing.v4_quantification_pipeline import run_v4_tail_from_v5_work_items  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="Clear and recompute V4 tail artifacts/BOQ.")
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

    work_items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    if not work_items:
        raise RuntimeError(
            f"missing v5_work_items_market_standard | listing_id={listing_id} "
            f"(run scripts/smoke_v5_decompose_work_items.py first)"
        )

    logger.info("v5->v4_tail: starting | listing_id=%s force=%s", listing_id, force)
    summary = await run_v4_tail_from_v5_work_items(
        listing_id=listing_id,
        strategy_name="market_standard",
        v5_work_items=work_items,
        db=db,
        call_gemini=call_gemini,
        call_gemini_json=call_gemini_json,
        fetch_images_batch=fetch_images_batch,
        embed_texts_fn=embed_texts,
        clear_existing_v4=force,
    )

    # ── Post-BOQ finalization: aggregate line items -> v2_market_standard for frontend ──
    from pricing.v2_boq_generator import aggregate_boq_from_db  # noqa: E402

    boq_agg = await aggregate_boq_from_db(listing_id, "market_standard", db)
    ok = await db.save_unified_estimate(listing_id, "v2_market_standard", boq_agg)
    logger.info(
        "post-boq finalized | listing_id=%s | total_pem=%.0f | grand_total_with_iva=%.0f | lines=%d | saved=%s",
        listing_id, boq_agg.get("total_pem", 0), boq_agg.get("grand_total_with_iva", 0),
        len(boq_agg.get("line_items") or []), ok,
    )

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_work_items_to_v4_tail_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 -- work_items -> V4 tail (priced BOQ)",
        meta={
            "listing_id": listing_id,
            "strategy_name": "market_standard",
            "source_key": "v5_work_items_market_standard",
            "total_pem": boq_agg.get("total_pem"),
            "grand_total_with_iva": boq_agg.get("grand_total_with_iva"),
            "line_items_count": len(boq_agg.get("line_items") or []),
        },
        sample=summary,
        payload=summary,
    )
    print({"stage": "v5_work_items_to_v4_tail", "listing_id": listing_id, "report_path": report_path})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
