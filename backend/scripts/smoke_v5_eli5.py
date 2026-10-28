#!/usr/bin/env python3
"""
Smoke: V5 ELI5 — buyer-friendly "product configurator" summary
===============================================================

Reads the existing v2_market_standard (aggregated BOQ) and listing metadata,
then calls Gemini Pro to regroup raw BCCA line items into buyer-understandable
packages per room.

No need to re-run the full pipeline — this smoke test reuses existing BOQ.

Writes:
- unified_estimates: v5_eli5_market_standard

Usage:
  python3 scripts/smoke_v5_eli5.py --listing-id 12
  python3 scripts/smoke_v5_eli5.py --listing-id 12 --force   # re-generate even if exists
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
from pipeline.gemini_client import call_gemini_json, set_gemini_tracking_context  # noqa: E402
from pricing.v5_eli5 import generate_v5_eli5  # noqa: E402
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
    strategy_name = "market_standard"

    # Attach DB + job context so gemini_client can persist call usage rows.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    # Check for existing ELI5 (unless --force)
    eli5_key = f"v5_eli5_{strategy_name}"
    if not args.force:
        existing = await db.get_unified_estimate(listing_id, eli5_key)
        if isinstance(existing, dict) and existing.get("rooms"):
            logger.info("ELI5 already exists for listing %s (use --force to regenerate)", listing_id)
            print(json.dumps({"stage": "v5_eli5", "listing_id": listing_id, "status": "reused", "rooms": len(existing.get("rooms", []))}, indent=2))
            return 0

    # Load BOQ aggregation
    boq_key = f"v2_{strategy_name}"
    boq_agg = await db.get_unified_estimate(listing_id, boq_key)
    if not boq_agg or not boq_agg.get("line_items"):
        logger.error("No BOQ found at key '%s' for listing %s — run smoke_v5_to_v4_tail first", boq_key, listing_id)
        return 1

    # Load listing metadata
    listing = await db.get_listing(listing_id)
    if not listing:
        logger.error("Listing %s not found in database", listing_id)
        return 1

    logger.info(
        "Starting ELI5 generation | listing_id=%s | line_items=%d | total_pem=%.0f",
        listing_id, len(boq_agg.get("line_items", [])), float(boq_agg.get("total_pem", 0)),
    )

    # Load target PIR for current-condition context
    target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
    if target_pir:
        logger.info("Loaded target PIR with %d rooms for current-condition context", len(target_pir.get("rooms", [])))
    else:
        logger.info("No target PIR found — ELI5 will generate intro without current-condition context")

    eli5 = await generate_v5_eli5(
        listing_id=listing_id,
        strategy_name=strategy_name,
        boq_aggregation=boq_agg,
        listing=listing,
        db=db,
        call_gemini_json=call_gemini_json,
        target_pir=target_pir,
    )

    # ── Report ────────────────────────────────────────────────────────────────
    # Build a human-readable summary for the MD report
    rooms_summary = []
    for room in eli5.get("rooms", []):
        room_name = room.get("room_name", "?")
        cost = float(room.get("cost", 0))
        tagline = room.get("tagline", "")
        pkgs = room.get("packages", [])
        pkg_lines = [f"  - {p['name']} — EUR {float(p.get('cost', 0)):,.0f}" for p in pkgs]
        rooms_summary.append(f"**{room_name}** — EUR {cost:,.0f}\n_{tagline}_\n" + "\n".join(pkg_lines))

    timeline = eli5.get("timeline", {})
    report_body = "\n\n---\n\n".join(rooms_summary)
    report_body += f"\n\n---\n\n**Timeline:** {timeline.get('total_weeks', '?')} semanas — {timeline.get('summary', '')}"

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_eli5_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title=f"V5 ELI5 — Buyer-Friendly Summary (Listing {listing_id})",
        meta={
            "listing_id": listing_id,
            "strategy": strategy_name,
            "rooms": len(eli5.get("rooms", [])),
            "total_pem": float(boq_agg.get("total_pem", 0)),
            "grand_total": float(boq_agg.get("grand_total_with_iva", 0)),
        },
        sample=eli5,
        payload=eli5,
    )

    print(json.dumps({
        "stage": "v5_eli5",
        "listing_id": listing_id,
        "status": "generated",
        "rooms": len(eli5.get("rooms", [])),
        "report_path": report_path,
    }, indent=2))

    # Also print the human-readable summary to stdout
    print("\n" + "=" * 60)
    print("ELI5 BUYER SUMMARY")
    print("=" * 60)
    for room in eli5.get("rooms", []):
        cost = float(room.get("cost", 0))
        print(f"\n  {room.get('room_name', '?'):30s}  EUR {cost:>8,.0f}")
        print(f"  \"{room.get('tagline', '')}\"")
        for pkg in room.get("packages", []):
            pcost = float(pkg.get("cost", 0))
            print(f"    • {pkg['name']:25s}  EUR {pcost:>8,.0f}")
    print(f"\n  {'TOTAL':30s}  EUR {float(boq_agg.get('grand_total_with_iva', 0)):>8,.0f}")
    tl = eli5.get("timeline", {})
    print(f"\n  Timeline: {tl.get('total_weeks', '?')} semanas — {tl.get('summary', '')}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
