#!/usr/bin/env python3
"""
Rerun From Stage — clear downstream data & requeue jobs from a given stage.
===========================================================================

Use when you've changed pipeline logic at a specific stage and want to rerun
from there without redoing unaffected upstream steps.

Examples:
  # Rerun from v5_forage onward for listing 13:
  python3 scripts/rerun_from_stage.py --listing-id 13 --from-stage v5_forage

  # Rerun just the presentation stages (ELI5 + report + images):
  python3 scripts/rerun_from_stage.py --listing-id 13 --from-stage v5_eli5

  # Dry run (show what would be deleted/requeued without doing it):
  python3 scripts/rerun_from_stage.py --listing-id 13 --from-stage v5_bcca_match --dry-run

  # Show all stages:
  python3 scripts/rerun_from_stage.py --list-stages

WHY THIS MATTERS:
- Pipeline stages produce artifacts keyed by listing_id in unified_estimates,
  boq_line_items, smart_m2, and photo_clusters.
- If you change logic at stage X, everything from X onward must be regenerated.
- This script deletes exactly the artifacts produced by stages X..end, then
  requeues those jobs so the worker picks them up automatically.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Import the shared stage registry (single source of truth)
from pipeline.v5_stages import V5_STAGE_SEQUENCE as _FULL_SEQUENCE, STAGE_NAMES_UNIQUE

# Strip the version field for backward compat — this script only needs (stage, job_type, artifacts)
V5_STAGE_SEQUENCE: List[Tuple[str, str, List[str]]] = [
    (stage, jt, arts) for stage, jt, arts, _ver in _FULL_SEQUENCE
]


async def _delete_artifact(
    listing_id: int,
    artifact: str,
    dry_run: bool,
) -> str:
    """Delete one artifact spec via Supabase REST. Returns a description."""
    from database import get_client, _get_base_url, _get_headers

    client = await get_client()
    base = _get_base_url()
    headers = _get_headers()

    if artifact.startswith("ue:"):
        key = artifact[3:]
        desc = f"unified_estimates[{key}]"
        if not dry_run:
            resp = await client.delete(
                f"{base}/unified_estimates",
                params={"listing_id": f"eq.{listing_id}", "package_type": f"eq.{key}"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact.startswith("ue_like:"):
        pattern = artifact[8:]
        desc = f"unified_estimates[like:{pattern}]"
        if not dry_run:
            resp = await client.delete(
                f"{base}/unified_estimates",
                params={"listing_id": f"eq.{listing_id}", "package_type": f"like.{pattern}"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact == "boq_v4":
        desc = "boq_line_items[dimension=v4]"
        if not dry_run:
            resp = await client.delete(
                f"{base}/boq_line_items",
                params={"listing_id": f"eq.{listing_id}", "dimension": "eq.v4"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact == "smart_m2":
        desc = "smart_m2"
        if not dry_run:
            resp = await client.delete(
                f"{base}/smart_m2",
                params={"listing_id": f"eq.{listing_id}"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact == "photo_clusters":
        desc = "photo_clusters"
        if not dry_run:
            resp = await client.delete(
                f"{base}/photo_clusters",
                params={"listing_id": f"eq.{listing_id}"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact == "listing_comparables":
        desc = "listing_comparables"
        if not dry_run:
            resp = await client.delete(
                f"{base}/listing_comparables",
                params={"listing_id": f"eq.{listing_id}"},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: delete {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    elif artifact == "market_stats_cache":
        desc = "listing_market_stats[raw_filtered_comparables→NULL]"
        if not dry_run:
            resp = await client.patch(
                f"{base}/listing_market_stats",
                params={"listing_id": f"eq.{listing_id}"},
                headers=headers,
                json={"raw_filtered_comparables": None},
            )
            if resp.status_code not in (200, 204):
                logger.warning(f"  WARN: clear {desc} -> {resp.status_code}: {resp.text[:200]}")
        return desc

    else:
        logger.error(f"Unknown artifact spec: {artifact}")
        return f"UNKNOWN:{artifact}"


async def _reset_jobs(
    run_id: str,
    job_types: List[str],
    dry_run: bool,
) -> None:
    """Reset pipeline_jobs rows to queued for the given run + job_types."""
    from database import get_client, _get_base_url, _get_headers

    client = await get_client()
    base = _get_base_url()
    headers = _get_headers()

    for jt in job_types:
        if dry_run:
            print(f"  WOULD RESET  {jt}")
            continue

        patch_body = {
            "status": "queued",
            "error": None,
            "error_context": None,
            "locked_by": None,
            "locked_until": None,
            "attempts": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        # Prefer header return for row count
        h = {**headers, "Prefer": "return=representation"}
        resp = await client.patch(
            f"{base}/pipeline_jobs",
            json=patch_body,
            params={"run_id": f"eq.{run_id}", "job_type": f"eq.{jt}"},
            headers=h,
        )
        if resp.status_code not in (200, 204):
            logger.warning(f"  WARN: reset {jt} -> {resp.status_code}: {resp.text[:200]}")
            continue

        rows = len(resp.json()) if resp.status_code == 200 else 0
        if rows:
            print(f"  RESET        {jt:45s} ({rows} row(s))")
        else:
            print(f"  NOT FOUND    {jt:45s} (no job in run)")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear downstream artifacts and requeue pipeline jobs from a given stage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/rerun_from_stage.py --listing-id 13 --from-stage v5_forage
  python3 scripts/rerun_from_stage.py --listing-id 13 --from-stage v5_eli5 --dry-run
  python3 scripts/rerun_from_stage.py --list-stages
        """,
    )
    parser.add_argument("--listing-id", type=int, help="Listing ID to rerun")
    parser.add_argument("--from-stage", type=str, help="Stage name to rerun from (inclusive)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without doing it")
    parser.add_argument("--list-stages", action="store_true", help="Print all stages in order and exit")
    args = parser.parse_args()

    # ── --list-stages ──
    if args.list_stages:
        print("\nV5 Pipeline Stages (in execution order):\n")
        for i, (stage, job_type, artifacts) in enumerate(V5_STAGE_SEQUENCE):
            art_str = ", ".join(artifacts) if artifacts else "(no artifacts)"
            print(f"  {i+1:2d}. {stage:22s}  job={job_type:45s}  clears: {art_str}")
        print(f"\nTotal: {len(V5_STAGE_SEQUENCE)} jobs across {len(STAGE_NAMES_UNIQUE)} stages")
        print(f"\nValid --from-stage values: {', '.join(STAGE_NAMES_UNIQUE)}")
        return 0

    # ── Validate required args ──
    if not args.listing_id or not args.from_stage:
        parser.error("--listing-id and --from-stage are required (use --list-stages to see options)")

    listing_id = args.listing_id
    from_stage = args.from_stage.strip()
    dry_run = args.dry_run

    # Find the index of from_stage in the sequence
    from_idx: Optional[int] = None
    for i, (stage, _, _) in enumerate(V5_STAGE_SEQUENCE):
        if stage == from_stage:
            from_idx = i
            break
    if from_idx is None:
        print(f"\nERROR: Unknown stage '{from_stage}'.")
        print(f"Valid stages: {', '.join(STAGE_NAMES_UNIQUE)}")
        return 1

    stages_to_rerun = V5_STAGE_SEQUENCE[from_idx:]
    stages_to_keep = V5_STAGE_SEQUENCE[:from_idx]

    # ── Summary ──
    tag = "DRY RUN — " if dry_run else ""
    print(f"\n{tag}Rerun from stage '{from_stage}' for listing {listing_id}")
    print(f"  Keeping  (upstream):  {len(stages_to_keep):2d} jobs — stages won't be touched")
    print(f"  Clearing (from here): {len(stages_to_rerun):2d} jobs — artifacts deleted + jobs requeued")
    print()
    print("  Stages being cleared:")
    for s, jt, arts in stages_to_rerun:
        art_str = ", ".join(arts) if arts else "(no data artifacts)"
        print(f"    • {s:22s} → {art_str}")

    # ── Step 1: Delete artifacts ──
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Deleting artifacts...")
    deleted_count = 0
    for stage, job_type, artifacts in stages_to_rerun:
        for art in artifacts:
            desc = await _delete_artifact(listing_id, art, dry_run)
            deleted_count += 1
            label = "WOULD DELETE" if dry_run else "DELETED"
            print(f"  {label:14s} {desc}")

    if deleted_count == 0:
        print("  (no artifacts to delete for selected stages)")

    # ── Step 2: Find latest run ──
    from database import get_latest_pipeline_run
    latest_run = await get_latest_pipeline_run(listing_id)
    if not latest_run:
        print(f"\nERROR: No pipeline run found for listing {listing_id}. Nothing to requeue.")
        return 1

    run_id = latest_run["run_id"]
    run_status = latest_run.get("status", "unknown")
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Latest run: {run_id} (status: {run_status})")

    # ── Step 3: Reset jobs ──
    job_types_to_reset = [jt for _, jt, _ in stages_to_rerun]
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Resetting {len(job_types_to_reset)} jobs to queued...\n")
    await _reset_jobs(run_id, job_types_to_reset, dry_run)

    # ── Done ──
    if dry_run:
        print(f"\nDry run complete. No changes were made.")
    else:
        print(f"\nDone! {len(job_types_to_reset)} jobs requeued for listing {listing_id} (run {run_id}).")
        print(f"The worker will pick them up automatically.")
        print(f"\nMonitor progress:")
        print(f"  journalctl -u leo-pipeline-worker.service -f")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
