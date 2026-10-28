#!/usr/bin/env python3
"""
Smoke: V4 tail — MATCH ONLY (from V5 work items)
===============================================

Runs ONLY the BCCA matching step of the V4 tail, starting from existing V5 work items:
- pricing.v4_quantification_pipeline._worklist_dim_from_flat_items
- pricing.v4_quantification_pipeline.match_v4_bcca

WHY THIS EXISTS:
- Debug match quality in isolation (no quant plan, no forage, no BOQ writes).
- Recompute only `v4_bcca_matches_{strategy}_{dimension}` artifacts when match policy changes.

Writes:
- unified_estimates: v4_bcca_matches_{strategy}_{dimension}
- markdown report: backend/reports/smoke_v4_tail_match_only_from_v5_{listing_id}.md

Usage:
  .venv/bin/python scripts/smoke_v4_tail_match_only_from_v5_work_items.py --listing-id 12 --force
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
from pricing.embedding_runtime import embed_texts  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import (  # noqa: E402
    _get_default_bcca_matcher,
    _worklist_dim_from_flat_items,
    match_v4_bcca,
)
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _summarize_matches(*, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    whole_dwelling_hits = [
        m
        for m in (matches or [])
        if isinstance(m, dict)
        and (
            " 1 vivienda" in str(m.get("bcca_desc_100") or "").lower()
            or "inst. eléctrica vivienda" in str(m.get("bcca_desc_100") or "").lower()
            or "vivienda hasta c.g.p" in str(m.get("bcca_desc_100") or "").lower()
            or "redes int. agua" in str(m.get("bcca_desc_100") or "").lower()
        )
    ]
    filtered_count = sum(1 for m in (matches or []) if isinstance(m, dict) and m.get("whole_dwelling_filtered") is True)
    return {
        "matches_total": len(matches or []),
        "whole_dwelling_like_matches_remaining": len(whole_dwelling_hits),
        "whole_dwelling_filtered_picks": int(filtered_count),
        "sample_whole_dwelling_like": [
            {
                "room_id": m.get("room_id"),
                "work_item_id": m.get("work_item_id"),
                "work_description": m.get("work_description"),
                "bcca_code": m.get("bcca_code"),
                "bcca_desc_100": m.get("bcca_desc_100"),
                "embedding_similarity": m.get("embedding_similarity"),
            }
            for m in whole_dwelling_hits[:10]
            if isinstance(m, dict)
        ],
    }


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="Recompute and overwrite match artifacts.")
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)
    strategy_name = "market_standard"

    work_items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    if not work_items:
        raise RuntimeError(f"missing v5_work_items_market_standard | listing_id={listing_id}")
    items = work_items.get("items") or []
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"invalid v5_work_items_market_standard.items | listing_id={listing_id}")

    matcher = _get_default_bcca_matcher()

    logger.info("v4 match-only: starting | listing_id=%s force=%s", listing_id, force)
    by_dim: Dict[str, Any] = {"listing_id": listing_id, "strategy_name": strategy_name, "dimensions": {}}

    for dim in V2_DIMENSIONS:
        pkg_matches = f"v4_bcca_matches_{strategy_name}_{dim}"
        if not force:
            existing = await db.get_unified_estimate(listing_id, pkg_matches)
            if isinstance(existing, dict) and isinstance(existing.get("matches"), list) and existing.get("matches"):
                by_dim["dimensions"][dim] = {
                    "package_type": pkg_matches,
                    "reused": True,
                    "summary": _summarize_matches(matches=existing.get("matches") or []),
                }
                continue

        worklist_dim = _worklist_dim_from_flat_items(dimension=dim, items=items)
        bcca_matches = await match_v4_bcca(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dim,
            worklist_dim=worklist_dim,
            matcher=matcher,
            embed_texts_fn=embed_texts,
        )
        await db.save_unified_estimate(listing_id, pkg_matches, {"matches": bcca_matches})
        by_dim["dimensions"][dim] = {
            "package_type": pkg_matches,
            "reused": False,
            "summary": _summarize_matches(matches=bcca_matches),
        }

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v4_tail_match_only_from_v5_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V4 tail — match only (from V5 work items)",
        meta={"listing_id": listing_id, "strategy_name": strategy_name, "source_key": "v5_work_items_market_standard"},
        sample=by_dim,
        payload=by_dim,
    )
    print(json.dumps({"stage": "v4_tail_match_only_from_v5", "listing_id": listing_id, "report_path": report_path}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

