#!/usr/bin/env python3
"""
Smoke: V4 tail — QUANT PLAN ONLY (from V5 work items + existing matches)
======================================================================

Runs ONLY the quantification planning step of the V4 tail, per dimension:
- Loads existing v5_work_items_market_standard
- Loads existing v4_bcca_matches_{strategy}_{dimension}
- Calls pricing.v4_quantification_pipeline.generate_v4_quant_plan

No foraging and no BOQ writes.

Writes:
- unified_estimates: v4_quant_plan_{strategy}_{dimension}
- markdown report: backend/reports/smoke_v4_tail_quant_plan_only_from_v5_{listing_id}.md

Usage:
  .venv/bin/python scripts/smoke_v4_tail_quant_plan_only_from_v5_work_items.py --listing-id 12 --force
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import call_gemini  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import (  # noqa: E402
    _get_default_bcca_matcher,
    _worklist_dim_from_flat_items,
    generate_v4_quant_plan,
)
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _require(cond: bool, msg: str) -> None:
    if cond:
        return
    raise RuntimeError(msg)


def _room_has_photos_from_clusters(clusters: List[Dict[str, Any]]) -> Dict[str, bool]:
    out: Dict[str, bool] = {}
    for c in clusters or []:
        if not isinstance(c, dict):
            continue
        room_id = str(c.get("cluster_id") or "").strip()
        if not room_id:
            continue
        urls = c.get("photo_urls") or []
        if isinstance(urls, list) and any(isinstance(u, str) and u.strip() for u in urls):
            out[room_id] = True
    return out


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="Recompute and overwrite quant plan artifacts.")
    p.add_argument(
        "--dimension",
        type=str,
        default="",
        help="Optional: run ONLY this dimension (useful to avoid timeouts).",
    )
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)
    strategy_name = "market_standard"

    work_items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    _require(bool(work_items), f"missing v5_work_items_market_standard | listing_id={listing_id}")
    items = work_items.get("items") or []
    _require(isinstance(items, list) and items, f"invalid v5_work_items_market_standard.items | listing_id={listing_id}")

    clusters = await db.get_photo_clusters(listing_id)
    _require(bool(clusters), f"missing photo_clusters | listing_id={listing_id}")
    room_has_photos = _room_has_photos_from_clusters(clusters)

    # Listing context (optional, but improves signal selection when floorplan is missing).
    try:
        listing = await db.get_listing(listing_id)
    except Exception:
        listing = None
    listing_sqm = None
    try:
        if isinstance(listing, dict) and listing.get("sqm") is not None:
            listing_sqm = float(listing.get("sqm"))
    except Exception:
        listing_sqm = None

    floorplan_available = False
    for c in clusters or []:
        if isinstance(c, dict) and str(c.get("room_type") or "").strip().lower() == "floorplan":
            urls = c.get("photo_urls") or []
            if isinstance(urls, list) and any(isinstance(u, str) and u.strip() for u in urls):
                floorplan_available = True
                break

    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    logger.info("v4 quant-plan-only: starting | listing_id=%s force=%s", listing_id, force)
    payload: Dict[str, Any] = {"listing_id": listing_id, "strategy_name": strategy_name, "dimensions": {}}

    dims = list(V2_DIMENSIONS)
    only_dim = str(args.dimension or "").strip()
    if only_dim:
        if only_dim not in dims:
            raise ValueError(f"--dimension must be one of {dims} (got {only_dim})")
        dims = [only_dim]

    for dim in dims:
        pkg_matches = f"v4_bcca_matches_{strategy_name}_{dim}"
        matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
        bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
        _require(isinstance(bcca_matches, list) and bcca_matches, f"missing bcca matches | package_type={pkg_matches}")

        pkg_plan = f"v4_quant_plan_{strategy_name}_{dim}"
        if not force:
            existing = await db.get_unified_estimate(listing_id, pkg_plan)
            if isinstance(existing, dict) and isinstance(existing.get("plans"), list) and existing.get("plans"):
                payload["dimensions"][dim] = {"package_type": pkg_plan, "reused": True, "plans": len(existing.get("plans") or [])}
                continue

        worklist_dim = _worklist_dim_from_flat_items(dimension=dim, items=items)
        quant_plan = await generate_v4_quant_plan(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dim,
            worklist_dim=worklist_dim,
            bcca_matches=bcca_matches,
            floorplan_available=floorplan_available,
            room_has_photos=room_has_photos,
            call_gemini=call_gemini,
            bcca_meta_by_code=bcca_meta_by_code,
            listing_sqm=listing_sqm,
        )
        await db.save_unified_estimate(listing_id, pkg_plan, quant_plan)
        payload["dimensions"][dim] = {"package_type": pkg_plan, "reused": False, "plans": len(quant_plan.get("plans") or [])}

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v4_tail_quant_plan_only_from_v5_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V4 tail — quant plan only (from V5 work items + existing matches)",
        meta={"listing_id": listing_id, "strategy_name": strategy_name, "source_key": "v5_work_items_market_standard"},
        sample=payload,
        payload=payload,
    )
    print(json.dumps({"stage": "v4_tail_quant_plan_only_from_v5", "listing_id": listing_id, "report_path": report_path}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

