#!/usr/bin/env python3
"""
Smoke: V5 strategy targets (slot-level targets for tiers)

Writes:
- unified_estimates: v5_strategy_targets

Prereqs:
- unified_estimates: v5_pir_target
- comparable PIRs exist (pir_type="comparable") for some comparables

Usage:
  python3 scripts/smoke_v5_strategy_targets.py --listing-id 12 --force
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import call_gemini, set_gemini_tracking_context  # noqa: E402
from pricing.v5_strategy_delta_decompose import generate_v5_strategy_targets  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--max-comparables", type=int, default=5)
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

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_strategy_targets")
    if isinstance(existing, dict) and isinstance(existing.get("tiers"), list) and existing.get("tiers"):
        logger.info("v5_strategy_targets: already exists | listing_id=%s tiers=%s", listing_id, len(existing.get("tiers") or []))
        return 0

    target = await db.get_unified_estimate(listing_id, "v5_pir_target")
    if not target:
        raise RuntimeError(f"missing v5_pir_target | listing_id={listing_id}")

    comparables = await db.get_listing_comparables(listing_id)
    if not comparables:
        raise RuntimeError(f"no comparables | listing_id={listing_id}")

    comp_pirs: List[Dict[str, Any]] = []
    for comp in comparables:
        comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id:
            continue
        pir = await db.get_pir(comp_id, pir_type="comparable")
        if pir:
            comp_pirs.append(pir)
        if len(comp_pirs) >= int(args.max_comparables):
            break
    if not comp_pirs:
        raise RuntimeError(f"no comparable PIRs available | listing_id={listing_id}")

    targets = await generate_v5_strategy_targets(
        listing_id=listing_id,
        comparable_pirs=comp_pirs,
        target_pir=target,
        call_gemini_fn=call_gemini,
    )

    out = {
        **targets,
        "schema_version": "v5_strategy_targets_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"tiers": len((targets or {}).get("tiers") or [])},
    }
    ok = await db.save_unified_estimate(listing_id, "v5_strategy_targets", out)
    if not ok:
        raise RuntimeError(f"save_unified_estimate failed | key=v5_strategy_targets listing_id={listing_id}")

    tiers = out.get("tiers") or []
    sample = tiers[0] if isinstance(tiers, list) and tiers else None
    if isinstance(sample, dict):
        # shrink sample
        slot_targets = sample.get("slot_targets") or {}
        if isinstance(slot_targets, dict):
            first_keys = list(slot_targets.keys())[:5]
            sample = {**sample, "slot_targets_sample": {k: slot_targets.get(k) for k in first_keys}}
            sample.pop("slot_targets", None)
    print(
        {
            "stage": "v5_strategy_targets",
            "listing_id": listing_id,
            "key_written": "v5_strategy_targets",
            "tiers": len(out.get("tiers") or []),
            "report_path": os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_strategy_targets_listing_{listing_id}.md"),
            "sample": sample,
        }
    )
    write_md_report(
        report_path=os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_strategy_targets_listing_{listing_id}.md"),
        title="Smoke V5 — Strategy Targets (slot-level)",
        meta={
            "listing_id": listing_id,
            "key_written": "v5_strategy_targets",
            "tiers": len(out.get("tiers") or []),
        },
        sample=sample,
        payload=out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

