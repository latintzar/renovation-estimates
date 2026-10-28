"""
V2 Pipeline Routes
==================

Clean V2 API with comparable-centric strategy selection.

Endpoints:
- POST /{listing_id}/v2/packages - Run full V2 pipeline
- GET  /{listing_id}/v2/packages - Get existing V2 results
- GET  /{listing_id}/v2/status   - Check pipeline status
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

import database as database_mod
from database import Database
from pricing.v2_scheduler import enqueue_v2_run

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/listings", tags=["V2 Pipeline"])

# Shared DB instance
db = Database()


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class V2StatusResponse(BaseModel):
    """Pipeline status response."""
    success: bool
    listing_id: int
    status: str  # "none", "in_progress", "complete", "error"
    checkpoints: List[str] = []
    run_id: Optional[str] = None
    queued_jobs: Optional[int] = None
    in_progress_jobs: Optional[int] = None
    failed_jobs: Optional[int] = None
    succeeded_jobs: Optional[int] = None
    # Stage-by-stage progress (V5 queue)
    current_stage: Optional[str] = None
    completed_stages: Optional[int] = None
    total_stages: Optional[int] = None
    stages: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class V2PackageStrategy(BaseModel):
    """Single strategy package."""
    strategy_name: str
    reference_comparable_id: Optional[int] = None
    reference_sold_price: Optional[int] = None
    delta_scopes: Dict[str, Any]
    boq: Dict[str, Any]
    # Post-BOQ phase outputs
    eli5_summary: Optional[Dict[str, Any]] = None
    architect_report: Optional[Dict[str, Any]] = None
    generated_images: Optional[List[Dict[str, Any]]] = None
    room_prompts: Optional[List[Dict[str, Any]]] = None
    comparables: Optional[List[Dict[str, Any]]] = None


class V2PackagesResponse(BaseModel):
    """Full V2 packages response."""
    success: bool
    listing_id: int
    run_id: Optional[str] = None
    target_pir: Optional[Dict[str, Any]] = None
    strategy_selection: Optional[Dict[str, Any]] = None
    packages: Optional[Dict[str, V2PackageStrategy]] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/{listing_id}/v2/status", response_model=V2StatusResponse)
async def get_v2_status(listing_id: int):
    """Check V2 pipeline status for a listing."""
    try:
        # Single source of truth: materialized status fields in pipeline_runs.
        latest_run = await db.get_latest_pipeline_run(listing_id)
        if latest_run:
            latest_run = await database_mod.ensure_run_materialized(latest_run)
            run_id = latest_run.get("run_id")
            jobs_queued = int(latest_run.get("jobs_queued") or 0)
            jobs_in_progress = int(latest_run.get("jobs_in_progress") or 0)
            jobs_failed = int(latest_run.get("jobs_failed") or 0)
            jobs_succeeded = int(latest_run.get("jobs_succeeded") or 0)
            jobs_total = int(latest_run.get("jobs_total") or 0)
            stages = latest_run.get("stages")
            if not isinstance(stages, list):
                stages = []
            current_stage = latest_run.get("current_stage")

            run_status = str(latest_run.get("status") or "").lower()
            if run_status == "complete":
                status = "complete"
            elif run_status == "failed":
                status = "error"
            elif run_status in {"running", "queued"}:
                status = "in_progress"
            elif jobs_queued > 0 or jobs_in_progress > 0:
                status = "in_progress"
            elif jobs_failed > 0:
                status = "error"
            elif jobs_succeeded > 0:
                status = "complete"
            else:
                status = "none"

            completed_stages = 0
            total_stages = len(stages) if stages else 0
            if stages:
                for s in stages:
                    sq = int(s.get("queued") or s.get("queued_jobs") or 0)
                    sip = int(s.get("in_progress") or s.get("in_progress_jobs") or 0)
                    ss = int(s.get("succeeded") or s.get("succeeded_jobs") or 0)
                    sf = int(s.get("failed") or s.get("failed_jobs") or 0)
                    if ss > 0 and sq == 0 and sip == 0 and sf == 0:
                        completed_stages += 1

            return V2StatusResponse(
                success=True,
                listing_id=listing_id,
                status=status,
                checkpoints=[],
                run_id=run_id,
                queued_jobs=jobs_queued,
                in_progress_jobs=jobs_in_progress,
                failed_jobs=jobs_failed,
                succeeded_jobs=jobs_succeeded,
                current_stage=current_stage,
                completed_stages=completed_stages,
                total_stages=total_stages,
                stages=stages or None,
            )

        # Check for existing checkpoints
        checkpoints = []
        
        # Check target PIR
        target_pir = await db.get_pir(listing_id, pir_type="target")
        if target_pir:
            checkpoints.append("target_pir")
        
        # Check strategy selection
        strategy = await db.get_v2_strategy_selection(listing_id)
        if strategy:
            checkpoints.append("strategy_selection")
        
        # Check BOQs
        for strat in ["conservative", "market_standard", "top_of_market"]:
            boq = await db.get_v2_boq(listing_id, strat)
            if boq:
                checkpoints.append(f"boq_{strat}")
        
        # Determine status
        if not checkpoints:
            status = "none"
        elif checkpoints:
            status = "in_progress"
        else:
            status = "none"
        
        return V2StatusResponse(
            success=True,
            listing_id=listing_id,
            status=status,
            checkpoints=checkpoints
        )
        
    except Exception as e:
        logger.error(f"Failed to get V2 status: {e}", exc_info=True)
        return V2StatusResponse(
            success=False,
            listing_id=listing_id,
            status="error",
            error=str(e)
        )


@router.get("/{listing_id}/v2/packages", response_model=V2PackagesResponse)
async def get_v2_packages(listing_id: int):
    """Get existing V2 packages for a listing."""
    try:
        def _build_comparable_triplet(
            all_comparables: List[Dict[str, Any]],
            reference_id: Optional[int],
        ) -> List[Dict[str, Any]]:
            """
            Return [below, reference, above] by price when possible.
            Falls back to top 3 closest-by-distance comparables when no reference match.
            """
            if not all_comparables:
                return []

            priced = sorted(
                [c for c in all_comparables if c.get("sale_price")],
                key=lambda c: (c["sale_price"], c.get("distance_km", 999)),
            )
            if not priced:
                return []

            ref_idx = None
            if reference_id is not None:
                ref_idx = next(
                    (
                        i for i, c in enumerate(priced)
                        if c.get("id") == reference_id
                        or c.get("casafari_property_id") == reference_id
                    ),
                    None,
                )

            if ref_idx is not None:
                neighbors: List[Dict[str, Any]] = []
                if ref_idx > 0:
                    neighbors.append({**priced[ref_idx - 1], "comp_role": "below"})
                neighbors.append({**priced[ref_idx], "comp_role": "reference"})
                if ref_idx < len(priced) - 1:
                    neighbors.append({**priced[ref_idx + 1], "comp_role": "above"})
                return neighbors

            # Fallback: closest 3 by distance (still useful in UI, even without explicit reference)
            closest = sorted(
                priced,
                key=lambda c: (
                    c.get("distance_km", 999),
                    abs((c.get("sale_price") or 0) - (priced[0].get("sale_price") or 0)),
                ),
            )[:3]
            return [{**c, "comp_role": "reference" if i == 0 else None} for i, c in enumerate(closest)]

        def _safe_float(v: Any) -> Optional[float]:
            try:
                if v is None:
                    return None
                f = float(v)
                if f <= 0:
                    return None
                return f
            except Exception:
                return None

        def _normalize(s: Any) -> str:
            return str(s or "").strip().lower()

        def _enrich_eli5_summary_with_smart_m2(eli5_summary: Any, smart_m2: Any) -> Any:
            """
            Attach Smart M² `estimated_m2` into each ELI5 room object (when possible).

            WHY: the contractor brief needs per-room m² and the ELI5 artifact currently
            only contains taglines + scope/cost fields.
            """
            if not isinstance(eli5_summary, dict):
                return eli5_summary
            if not isinstance(smart_m2, dict):
                return eli5_summary

            eli5_rooms = eli5_summary.get("rooms")
            smart_rooms = smart_m2.get("rooms")
            if not isinstance(eli5_rooms, list) or not isinstance(smart_rooms, list) or not smart_rooms:
                return eli5_summary

            id_to_m2: Dict[str, float] = {}
            name_to_m2: Dict[str, float] = {}

            for r in smart_rooms:
                if not isinstance(r, dict):
                    continue
                m2 = _safe_float(r.get("estimated_m2"))
                if m2 is None:
                    continue

                rid = _normalize(r.get("room_id") or r.get("cluster_id") or r.get("id"))
                if rid:
                    id_to_m2[rid] = m2

                rname = _normalize(r.get("cluster_name") or r.get("room_name"))
                if rname:
                    name_to_m2[rname] = m2

            # Enrich in-place (safe: dict returned from DB request, not shared state)
            for room in eli5_rooms:
                if not isinstance(room, dict):
                    continue
                if room.get("estimated_m2") is not None:
                    continue

                m2: Optional[float] = None
                rid = _normalize(room.get("room_id"))
                if rid:
                    m2 = id_to_m2.get(rid)
                if m2 is None:
                    rname = _normalize(room.get("room_name"))
                    if rname:
                        m2 = name_to_m2.get(rname)
                if m2 is None:
                    continue

                room["estimated_m2"] = m2

            return eli5_summary

        # Fetch all V2 data
        target_pir = await db.get_pir(listing_id, pir_type="target")
        strategy_selection = await db.get_v2_strategy_selection(listing_id)
        if not target_pir or not strategy_selection:
            # V5 fallback path:
            # Newer runs may not persist legacy V2 checkpoints, but they do persist
            # the final market_standard artifacts that the frontend needs.
            logger.info(
                f"get_v2_packages: legacy checkpoints missing, trying V5 fallback | listing_id={listing_id}"
            )
            v5_target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
            v5_selected_comparable = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
            v5_delta = await db.get_unified_estimate(listing_id, "v5_delta_slots_market_standard")
            v2_market_standard = await db.get_unified_estimate(listing_id, "v2_market_standard")
            v5_eli5 = await db.get_unified_estimate(listing_id, "v5_eli5_market_standard")
            v5_smart_m2 = await db.get_smart_m2(listing_id)
            # Architect report has been deprecated (kept as a nullable field for backward-compat).
            v5_architect_report = None
            v5_images = await db.get_unified_estimate(listing_id, "v5_generated_images_market_standard")

            has_v5_outputs = any(x is not None for x in [v5_delta, v2_market_standard, v5_eli5, v5_images])

            if not has_v5_outputs:
                return V2PackagesResponse(
                    success=True,
                    listing_id=listing_id,
                    error="No V2/V5 package data found. Run POST to generate.",
                )

            # Build synthetic strategy_selection + package so existing frontend keeps working.
            reference_comparable_id = None
            reference_sold_price = None
            if isinstance(v5_selected_comparable, dict):
                reference_comparable_id = (
                    v5_selected_comparable.get("id")
                    or v5_selected_comparable.get("selected_comparable_id")
                    or v5_selected_comparable.get("reference_comparable_id")
                )
                # reference_sold_price first: this is our computed value
                # (median price/m² × listing area). Fallback to raw sale_price.
                reference_sold_price = (
                    v5_selected_comparable.get("reference_sold_price")
                    or v5_selected_comparable.get("sale_price")
                )

            synthetic_strategy_selection = strategy_selection or {
                "strategies": [
                    {
                        "strategy_name": "market_standard",
                        "reference_comparable_id": reference_comparable_id,
                        "reference_sold_price": reference_sold_price,
                    }
                ]
            }

            synthetic_target_pir = target_pir or v5_target_pir
            synthetic_boq = v2_market_standard if isinstance(v2_market_standard, dict) else {}
            synthetic_delta_scopes = v5_delta if isinstance(v5_delta, dict) else {}
            synthetic_eli5_summary = _enrich_eli5_summary_with_smart_m2(
                v5_eli5 if isinstance(v5_eli5, dict) else None,
                v5_smart_m2,
            )

            packages: Dict[str, Any] = {
                "market_standard": {
                    "strategy_name": "market_standard",
                    "reference_comparable_id": reference_comparable_id,
                    "reference_sold_price": reference_sold_price,
                    "delta_scopes": synthetic_delta_scopes,
                    "boq": synthetic_boq,
                    "eli5_summary": synthetic_eli5_summary,
                    "architect_report": None,
                    "generated_images": (
                        v5_images.get("generated_images", [])
                        if isinstance(v5_images, dict)
                        else []
                    ),
                    "room_prompts": (
                        v5_images.get("room_prompts", [])
                        if isinstance(v5_images, dict)
                        else []
                    ),
                }
            }

            all_comparables = await db.get_listing_comparables(listing_id)
            if all_comparables:
                packages["market_standard"]["comparables"] = _build_comparable_triplet(
                    all_comparables=all_comparables,
                    reference_id=reference_comparable_id,
                )

            logger.info(
                f"get_v2_packages: served via V5 fallback | listing_id={listing_id} "
                f"| has_delta={bool(synthetic_delta_scopes)} has_boq={bool(synthetic_boq)} "
                f"| has_eli5={bool(v5_eli5)}"
            )

            return V2PackagesResponse(
                success=True,
                listing_id=listing_id,
                target_pir=synthetic_target_pir,
                strategy_selection=synthetic_strategy_selection,
                packages=packages,
            )
        
        # Build packages dict
        packages = {}

        # Smart M² is listing-level (not strategy-specific). If present, enrich all ELI5 outputs.
        smart_m2 = await db.get_smart_m2(listing_id)
        
        # Build strategy lookup (strategies is a list, not dict)
        strategy_list = strategy_selection.get("strategies", [])
        strategy_lookup = {s.get("strategy_name"): s for s in strategy_list}
        
        for strat in ["conservative", "market_standard", "top_of_market"]:
            delta_scopes = await db.get_v2_delta_scopes(listing_id, strat)
            boq = await db.get_v2_boq(listing_id, strat)
            
            if delta_scopes and boq:
                # Get strategy details from lookup
                strat_info = strategy_lookup.get(strat, {})
                
                # Extract eli5_summary, generated_images from BOQ
                # (legacy: stored inside the unified estimate alongside BOQ data)
                eli5_summary = boq.pop("eli5_summary", None)
                generated_images = boq.pop("generated_images", [])
                room_prompts = boq.pop("room_prompts", [])

                # V5 pipeline stores these as standalone keys — prefer them over legacy
                if not eli5_summary:
                    eli5_summary = await db.get_unified_estimate(listing_id, f"v5_eli5_{strat}")
                if not generated_images:
                    v5_images = await db.get_unified_estimate(listing_id, f"v5_generated_images_{strat}")
                    if isinstance(v5_images, dict) and v5_images.get("generated_images"):
                        generated_images = v5_images["generated_images"]

                eli5_summary = _enrich_eli5_summary_with_smart_m2(eli5_summary, smart_m2)
                
                packages[strat] = {
                    "strategy_name": strat,
                    "reference_comparable_id": strat_info.get("reference_comparable_id"),
                    "reference_sold_price": strat_info.get("reference_sold_price"),
                    "delta_scopes": delta_scopes,
                    "boq": boq,
                    # Post-BOQ phase outputs
                    "eli5_summary": eli5_summary,
                    "architect_report": None,
                    "generated_images": generated_images,
                    "room_prompts": room_prompts,
                }

        # ── Attach comparables (reference + neighbor above + neighbor below) ──
        all_comparables = await db.get_listing_comparables(listing_id)
        if all_comparables:
            for _, pkg in packages.items():
                ref_id = pkg.get("reference_comparable_id")
                pkg["comparables"] = _build_comparable_triplet(
                    all_comparables=all_comparables,
                    reference_id=ref_id,
                )
        
        return V2PackagesResponse(
            success=True,
            listing_id=listing_id,
            target_pir=target_pir,
            strategy_selection=strategy_selection,
            packages=packages,
        )
        
    except Exception as e:
        logger.error(f"Failed to get V2 packages: {e}", exc_info=True)
        return V2PackagesResponse(
            success=False,
            listing_id=listing_id,
            error=str(e)
        )


@router.post("/{listing_id}/v2/packages", response_model=V2PackagesResponse)
async def run_v2_packages(listing_id: int, force_restart: bool = False):
    """
    Run the full V2 pipeline for a listing.
    
    Pipeline:
    1. Photo filtering (all comparables)
    2. Clustering (target + all comparables)
    3. PIR generation (6-dimension analysis)
    4. Strategy selection (3 data-driven strategies)
    5. Delta scope generation (6 dimensions × 3 strategies)
    6. BOQ generation (BCCA pricing)
    7. Post-BOQ phases (peer review, ELI5, architect, checklist)
    
    Args:
        listing_id: The listing to analyze
        force_restart: If True, ignore checkpoints and restart
    """
    try:
        logger.info(f"🚀 Enqueuing V2 pipeline for listing {listing_id} (queue-based)")

        if force_restart:
            logger.warning("force_restart requested: enqueueing new run without clearing prior artifacts")

        # ── Clean up stale/broken runs before creating a new one ──
        # WHY: if a previous run has 0 jobs (enqueue failed or idempotency collision),
        # or all jobs failed, the status endpoint reports "error" forever and new runs
        # can't overwrite it. We detect and delete these stale runs so the new enqueue
        # starts fresh.
        latest_run = await db.get_latest_pipeline_run(listing_id)
        if latest_run:
            old_run_id = latest_run.get("run_id")
            counts = await db.get_pipeline_job_counts(run_id=old_run_id)
            queued = counts.get("queued", 0)
            in_progress = counts.get("in_progress", 0)
            failed = counts.get("failed", 0)
            succeeded = counts.get("succeeded", 0)
            total = queued + in_progress + failed + succeeded

            is_stale = total == 0  # 0 jobs = broken enqueue
            is_all_failed = total > 0 and failed == total  # every job failed
            is_actively_running = queued > 0 or in_progress > 0

            if is_stale or is_all_failed:
                logger.info(
                    f"Cleaning up stale run | run_id={old_run_id} | "
                    f"total={total} failed={failed} succeeded={succeeded}"
                )
                await db.delete_pipeline_run(old_run_id)
            elif is_actively_running and not force_restart:
                # Pipeline is already running — don't create a duplicate run.
                logger.info(f"Pipeline already running | run_id={old_run_id} | queued={queued} in_progress={in_progress}")
                return V2PackagesResponse(
                    success=True,
                    listing_id=listing_id,
                    run_id=old_run_id,
                    error=None,
                )

        run_id = await enqueue_v2_run(db=db, listing_id=listing_id)

        return V2PackagesResponse(
            success=True,
            listing_id=listing_id,
            run_id=run_id,
            error=None,
        )
        
    except Exception as e:
        logger.error(f"V2 pipeline failed: {e}", exc_info=True)
        return V2PackagesResponse(
            success=False,
            listing_id=listing_id,
            error=str(e)
        )


# =============================================================================
# CONDITION ASSESSMENT (Kept - Used by V2)
# =============================================================================

class ConditionV2Response(BaseModel):
    """Condition assessment response (rule verifications + Uniclass)."""
    success: bool
    hasData: bool = False
    rule_verifications: List[Dict[str, Any]] = []
    uniclass_assessments: List[Dict[str, Any]] = []
    error: Optional[str] = None


@router.get("/{listing_id}/condition-v2", response_model=ConditionV2Response)
async def get_condition_v2(listing_id: int):
    """Fetch existing condition v2 data (rule verifications + Uniclass assessments)."""
    try:
        # Get rule verifications
        rule_rows = await db.get_rule_verifications(listing_id)
        
        # Get Uniclass assessments
        uniclass_rows = await db.get_uniclass_assessments(listing_id)
        
        has_data = bool(rule_rows or uniclass_rows)
        
        return ConditionV2Response(
            success=True,
            hasData=has_data,
            rule_verifications=rule_rows or [],
            uniclass_assessments=uniclass_rows or []
        )
        
    except Exception as e:
        logger.error(f"Failed to get condition v2: {e}", exc_info=True)
        return ConditionV2Response(
            success=False,
            error=str(e)
        )


## Viewing guide (20-minute checklist) removed.
