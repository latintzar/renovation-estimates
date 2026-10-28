#!/usr/bin/env python3
"""
Pipeline Step Validator
=======================

Runs each pipeline step in order for a single listing and verifies outputs.
This is meant to prove every step completes before trusting the orchestrator.

Usage:
  ./venv/bin/python scripts/validate_pipeline_listing.py --listing-id 12
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from dotenv import load_dotenv

try:
    from database import Database
    from pricing.v2_scheduler import build_run_id
    from workers import handlers
except ModuleNotFoundError:
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from database import Database
    from pricing.v2_scheduler import build_run_id
    from workers import handlers

logger = logging.getLogger("validate_pipeline_listing")

StepFn = Callable[[Dict[str, Any], Any], Awaitable[None]]
CheckFn = Callable[[Database, int], Awaitable[None]]


def _slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_") or "cluster"


def _is_exterior_cluster(cluster: Dict[str, Any]) -> bool:
    cluster_id = str(cluster.get("cluster_id") or "").strip().lower()
    room_type = str(cluster.get("room_type") or "").strip().lower()
    cluster_name = str(cluster.get("cluster_name") or "").strip().lower()
    return "exterior" in (cluster_id, room_type, cluster_name)


def _idem_key(run_id: str, listing_id: int, suffix: str) -> str:
    return f"run:{run_id}:listing:{listing_id}:{suffix}"


async def _require_comparables(db: Database, listing_id: int) -> None:
    rows = await db.get_listing_comparables(listing_id)
    if not rows:
        raise RuntimeError(f"missing comparables | listing_id={listing_id}")
    logger.info("✅ comparables present | listing_id=%s | count=%s", listing_id, len(rows))

async def _require_comparable_pirs(db: Database, listing_id: int) -> None:
    rows = await db.get_listing_comparables(listing_id)
    if not rows:
        raise RuntimeError(f"missing comparables | listing_id={listing_id}")
    missing: List[int] = []
    for comp in rows:
        comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id:
            continue
        pir = await db.get_pir(int(comp_id), pir_type="comparable")
        if not pir:
            missing.append(int(comp_id))
    if missing:
        raise RuntimeError(f"missing comparable PIRs | listing_id={listing_id} | missing={missing}")
    logger.info("✅ comparable PIRs present | listing_id=%s | count=%s", listing_id, len(rows))


async def _require_clusters(db: Database, listing_id: int) -> List[Dict[str, Any]]:
    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"missing photo clusters | listing_id={listing_id}")
    logger.info("✅ photo clusters present | listing_id=%s | count=%s", listing_id, len(clusters))
    return clusters


async def _require_smart_m2(db: Database, listing_id: int) -> Dict[str, Any]:
    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        raise RuntimeError(f"missing smart_m2 | listing_id={listing_id}")
    logger.info("✅ smart_m2 present | listing_id=%s", listing_id)
    return smart_m2


async def _require_target_pir(db: Database, listing_id: int) -> None:
    pir = await db.get_pir(listing_id, pir_type="target")
    if not pir:
        raise RuntimeError(f"missing target PIR | listing_id={listing_id}")
    logger.info("✅ target PIR present | listing_id=%s", listing_id)


async def _require_strategy_selection(db: Database, listing_id: int) -> Dict[str, Any]:
    selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not selection:
        raise RuntimeError(f"missing strategy selection | listing_id={listing_id}")
    strategies = selection.get("strategies") or []
    if not strategies:
        raise RuntimeError(f"strategy selection empty | listing_id={listing_id}")
    logger.info("✅ strategy selection present | listing_id=%s | count=%s", listing_id, len(strategies))
    return selection


async def _require_strategy_specs(db: Database, listing_id: int, strategies: List[Dict[str, Any]]) -> None:
    for strategy in strategies:
        name = strategy.get("strategy_name")
        if not name:
            continue
        spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{name}")
        if not spec:
            raise RuntimeError(f"missing strategy spec | strategy={name} | listing_id={listing_id}")
    logger.info("✅ strategy specs present | listing_id=%s", listing_id)


async def _require_bcca_worklists(db: Database, listing_id: int, strategies: List[Dict[str, Any]]) -> None:
    for strategy in strategies:
        name = strategy.get("strategy_name")
        if not name:
            continue
        worklist = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_{name}")
        if not worklist:
            raise RuntimeError(f"missing bcca worklist | strategy={name} | listing_id={listing_id}")
    logger.info("✅ bcca worklists present | listing_id=%s", listing_id)


async def _require_validated_worklists(db: Database, listing_id: int, strategies: List[Dict[str, Any]]) -> None:
    for strategy in strategies:
        name = strategy.get("strategy_name")
        if not name:
            continue
        worklist = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_validated_{name}")
        if not worklist:
            raise RuntimeError(f"missing validated worklist | strategy={name} | listing_id={listing_id}")
    logger.info("✅ validated worklists present | listing_id=%s", listing_id)


async def _require_boq(db: Database, listing_id: int, strategies: List[Dict[str, Any]]) -> None:
    for strategy in strategies:
        name = strategy.get("strategy_name")
        if not name:
            continue
        count = await db.count_boq_line_items(listing_id, name)
        if count <= 0:
            raise RuntimeError(f"missing BOQ line items | strategy={name} | listing_id={listing_id}")
    logger.info("✅ BOQ line items present | listing_id=%s", listing_id)


async def _require_coverage_ledger(db: Database, listing_id: int, strategies: List[Dict[str, Any]]) -> None:
    for strategy in strategies:
        name = strategy.get("strategy_name")
        if not name:
            continue
        ledger = await db.get_unified_estimate(listing_id, f"v3_coverage_ledger_{name}")
        if not ledger:
            raise RuntimeError(f"missing coverage ledger | strategy={name} | listing_id={listing_id}")
    logger.info("✅ coverage ledger present | listing_id=%s", listing_id)


def _build_job(
    *,
    run_id: str,
    listing_id: int,
    stage: str,
    job_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": f"manual-{listing_id}-{job_type}",
        "run_id": run_id,
        "listing_id": listing_id,
        "stage": stage,
        "job_type": job_type,
        "payload": payload or {},
        "idempotency_key": _idem_key(run_id, listing_id, job_type),
    }


async def validate_listing(
    listing_id: int,
    run_id: Optional[str],
    *,
    start_step: Optional[str],
    stop_after: Optional[str],
) -> None:
    db = Database()
    latest = await db.get_latest_pipeline_run(listing_id)
    if not run_id:
        run_id = (latest or {}).get("run_id") or build_run_id(listing_id)

    logger.info("Starting validation | listing_id=%s | run_id=%s", listing_id, run_id)

    async def _run_comparable_pirs(job: Dict[str, Any], db: Any) -> None:
        listing_id = job["listing_id"]
        rows = await db.get_listing_comparables(listing_id)
        if not rows:
            raise RuntimeError(f"generate_comparable_pirs: no comparables | listing_id={listing_id}")
        for comp in rows:
            comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
            if not comp_id:
                continue
            comp_job = _build_job(
                run_id=job["run_id"],
                listing_id=listing_id,
                stage="pir",
                job_type="generate_comparable_pir",
                payload={"comp_id": int(comp_id), "comp_data": comp},
            )
            await handlers.handle_generate_comparable_pir(comp_job, db)

    steps: List[Tuple[str, str, StepFn, CheckFn]] = [
        ("fetch_comparables", "comparables", handlers.handle_fetch_comparables, _require_comparables),
        ("generate_comparable_pirs", "pir", _run_comparable_pirs, _require_comparable_pirs),
        ("cluster_target_photos", "clustering", handlers.handle_cluster_target, _require_clusters),
        ("smart_m2_target_indoorgml", "smart_m2", handlers.handle_smart_m2_target_indoorgml, _require_smart_m2),
        ("generate_target_pir", "pir", handlers.handle_generate_target_pir, _require_target_pir),
        ("strategy_selection", "strategy", handlers.handle_strategy_selection, _require_strategy_selection),
    ]

    started = start_step is None
    # Run first steps; strategy selection is needed for downstream checks.
    for job_type, stage, handler, postcheck in steps[:6]:
        if not started:
            if job_type != start_step:
                continue
            started = True
        if not started:
            continue
        # Idempotency special-case: this validator is often run in foreground timeout slices.
        # Re-running fetch_comparables clears + reinserts rows, which changes comparable IDs and
        # can prevent the run from converging. For other steps, always run the handler and let
        # the handler decide whether to skip based on its own stronger consistency checks.
        if job_type == "fetch_comparables":
            try:
                await postcheck(db, listing_id)
                logger.info("---- STEP SKIP | %s (already satisfied) ----", job_type)
                if stop_after and job_type == stop_after:
                    logger.info("Stop-after reached | step=%s", stop_after)
                    return
                continue
            except Exception as e:
                logger.info("postcheck failed; will run step | step=%s | error=%s", job_type, e)

        logger.info("---- STEP START | %s ----", job_type)
        job = _build_job(run_id=run_id, listing_id=listing_id, stage=stage, job_type=job_type, payload=None)
        await handler(job, db)
        await postcheck(db, listing_id)
        logger.info("---- STEP OK | %s ----", job_type)
        if stop_after and job_type == stop_after:
            logger.info("Stop-after reached | step=%s", stop_after)
            return

    # Load strategies for remaining steps.
    selection = await _require_strategy_selection(db, listing_id)
    strategies = selection.get("strategies") or []

    # Run the remaining steps sequentially (in-order), starting at `start_step` if provided.
    tail_steps: List[Tuple[str, str, StepFn, CheckFn]] = [
        ("delta_strategy_spec", "delta_scopes", handlers.handle_delta_strategy_spec, lambda d, lid: _require_strategy_specs(d, lid, strategies)),
        ("delta_bcca_worklist", "delta_scopes", handlers.handle_delta_bcca_worklist, lambda d, lid: _require_bcca_worklists(d, lid, strategies)),
        ("validate_and_repair_worklist", "delta_scopes", handlers.handle_validate_and_repair_worklist, lambda d, lid: _require_validated_worklists(d, lid, strategies)),
        ("v3_boq_generate", "boq_v3", handlers.handle_v3_boq_generate, lambda d, lid: _require_boq(d, lid, strategies)),
        ("coverage_ledger_glue", "boq_v3", handlers.handle_coverage_ledger_glue, lambda d, lid: _require_coverage_ledger(d, lid, strategies)),
    ]

    tail_started = start_step is None or start_step not in {t[0] for t in tail_steps}
    for job_type, stage, handler, postcheck in tail_steps:
        if not tail_started:
            if job_type != start_step:
                continue
            tail_started = True
        if not tail_started:
            continue

        logger.info("---- STEP START | %s ----", job_type)
        job = _build_job(run_id=run_id, listing_id=listing_id, stage=stage, job_type=job_type, payload=None)
        await handler(job, db)
        await postcheck(db, listing_id)
        logger.info("---- STEP OK | %s ----", job_type)
        if stop_after and job_type == stop_after:
            logger.info("Stop-after reached | step=%s", stop_after)
            return

    logger.info("✅ ALL STEPS COMPLETE | listing_id=%s | run_id=%s", listing_id, run_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Validate pipeline steps for a listing.")
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--start-step", default=None, help="Start at a specific job_type")
    parser.add_argument("--stop-after", default=None, help="Stop after a specific job_type")
    args = parser.parse_args()

    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.

    asyncio.run(
        validate_listing(
            args.listing_id,
            args.run_id,
            start_step=args.start_step,
            stop_after=args.stop_after,
        )
    )


if __name__ == "__main__":
    main()
