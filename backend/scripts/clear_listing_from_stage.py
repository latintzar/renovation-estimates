#!/usr/bin/env python3

import asyncio
import argparse
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _resolve_stage(from_stage: str) -> str:
    aliases = {
        "comparables": "v2_comparables_filtered",
        "target_clustering": "v2_target_clustering_complete",
        "target_year": "v2_target_year_estimation_complete",
        "target_pir": "v2_target_pir_complete",
        "comparable_pirs": "v2_comparable_pirs_complete",
        "strategy_selection": "v2_strategy_selection_complete",
        "delta_scopes": "v2_delta_scopes_complete",
        "boq_conservative": "v2_boq_conservative_complete",
        "boq_market_standard": "v2_boq_market_standard_complete",
        "boq_top_of_market": "v2_boq_top_of_market_complete",
        "post_boq": "v2_post_boq_complete",
    }
    return aliases.get(from_stage, from_stage)


STAGES: List[str] = [
    "v2_comparables_filtered",
    "v2_target_clustering_complete",
    "v2_target_year_estimation_complete",
    "v2_target_pir_complete",
    "v2_comparable_pirs_complete",
    "v2_strategy_selection_complete",
    "v2_delta_scopes_complete",
    "v2_boq_conservative_complete",
    "v2_boq_market_standard_complete",
    "v2_boq_top_of_market_complete",
    "v2_post_boq_complete",
    "v2_viewing_checklist_complete",
]


def _stage_index(stage: str) -> int:
    if stage not in STAGES:
        raise ValueError(
            f"Unknown stage: {stage}. Valid stages: {', '.join(STAGES)}"
        )
    return STAGES.index(stage)


async def _delete(client, base_url: str, table: str, params: Dict[str, str], dry_run: bool):
    if dry_run:
        logger.info(f"[DRY RUN] DELETE {table} WHERE {params}")
        return
    await client.delete(f"{base_url}/{table}", params=params)
    logger.info(f"✓ Deleted from {table} where {params}")


async def main():
    parser = argparse.ArgumentParser(
        description="Clear V2 pipeline data for a listing from a given stage onward."
    )
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--from-stage", type=str, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from_stage = _resolve_stage(args.from_stage)
    stage_index = _stage_index(from_stage)
    stages_to_clear = STAGES[stage_index:]

    # Import here to avoid path issues
    try:
        from ..database import get_client, _get_base_url, Database
    except ImportError:
        import sys
        from pathlib import Path

        backend_dir = Path(__file__).resolve().parents[1]
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from database import get_client, _get_base_url, Database

    client = await get_client()
    base_url = _get_base_url()
    db = Database()

    logger.info("=" * 80)
    logger.info(f"Listing ID: {args.listing_id}")
    logger.info(f"Clear from stage: {from_stage}")
    logger.info(f"Stages cleared: {', '.join(stages_to_clear)}")
    logger.info("=" * 80)

    # Always clear checkpoints from stage onward
    await _delete(
        client,
        base_url,
        "package_generation_progress",
        {
            "listing_id": f"eq.{args.listing_id}",
            "checkpoint": f"in.({','.join(stages_to_clear)})",
        },
        args.dry_run,
    )

    # Clear pipeline cost tracking for this listing (reset cost tracking)
    await _delete(
        client,
        base_url,
        "pipeline_cost_tracking",
        {"listing_id": f"eq.{args.listing_id}"},
        args.dry_run,
    )

    # Determine comparable IDs for this listing
    comparables = await db.get_listing_comparables(args.listing_id)
    comparable_ids = [str(c["id"]) for c in comparables]
    comp_id_filter = f"in.({','.join(comparable_ids)})" if comparable_ids else None

    # Clear target clusters if clearing from target clustering or earlier
    if stage_index <= _stage_index("v2_target_clustering_complete"):
        await _delete(
            client,
            base_url,
            "photo_clusters",
            {"listing_id": f"eq.{args.listing_id}"},
            args.dry_run,
        )
        await _delete(
            client,
            base_url,
            "smart_m2",
            {"listing_id": f"eq.{args.listing_id}"},
            args.dry_run,
        )

    # Clear target PIR if clearing from target PIR or earlier
    if stage_index <= _stage_index("v2_target_pir_complete"):
        await _delete(
            client,
            base_url,
            "property_intelligence_reports",
            {"listing_id": f"eq.{args.listing_id}", "pir_type": "eq.target"},
            args.dry_run,
        )
        await _delete(
            client,
            base_url,
            "smart_m2",
            {"listing_id": f"eq.{args.listing_id}"},
            args.dry_run,
        )

    # Clear comparable clusters + PIRs if clearing from comparable PIR stage or earlier
    if stage_index <= _stage_index("v2_comparable_pirs_complete") and comp_id_filter:
        await _delete(
            client,
            base_url,
            "comparable_photo_clusters",
            {"comparable_id": comp_id_filter},
            args.dry_run,
        )
        await _delete(
            client,
            base_url,
            "property_intelligence_reports",
            {"listing_id": comp_id_filter, "pir_type": "eq.comparable"},
            args.dry_run,
        )

    # Strategy selection / delta scopes / BOQ / viewing guide stored in unified_estimates
    package_types: List[str] = []
    if stage_index <= _stage_index("v2_strategy_selection_complete"):
        package_types.append("v2_strategy_selection")
    if stage_index <= _stage_index("v2_delta_scopes_complete"):
        package_types.extend(
            ["v2_delta_conservative", "v2_delta_market_standard", "v2_delta_top_of_market"]
        )
    if stage_index <= _stage_index("v2_boq_conservative_complete"):
        package_types.extend(["v2_conservative", "v2_market_standard", "v2_top_of_market"])
        await _delete(
            client,
            base_url,
            "boq_line_items",
            {"listing_id": f"eq.{args.listing_id}"},
            args.dry_run,
        )
    if stage_index <= _stage_index("v2_viewing_checklist_complete"):
        package_types.append("v2_viewing_checklist")

    if package_types:
        await _delete(
            client,
            base_url,
            "unified_estimates",
            {
                "listing_id": f"eq.{args.listing_id}",
                "package_type": f"in.({','.join(package_types)})",
            },
            args.dry_run,
        )

    logger.info("=" * 80)
    logger.info("Clear complete.")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
