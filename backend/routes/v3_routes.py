"""
V3 Pipeline Routes
==================

Endpoints:
- POST /{listing_id}/v3/packages  - Enqueue V3 pipeline run
- GET  /{listing_id}/v3/packages  - Aggregate V3 artifacts
- GET  /{listing_id}/v3/status    - Pipeline status from queue
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database import Database
from pricing.v2_scheduler import enqueue_v3_run

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/listings", tags=["V3 Pipeline"])
db = Database()


class V3StatusResponse(BaseModel):
    success: bool
    listing_id: int
    status: str
    run_id: Optional[str] = None
    queued_jobs: Optional[int] = None
    in_progress_jobs: Optional[int] = None
    failed_jobs: Optional[int] = None
    succeeded_jobs: Optional[int] = None
    current_checkpoint: Optional[str] = None
    checkpoints: List[str] = []
    error: Optional[str] = None


class V3Package(BaseModel):
    strategy_name: str
    reference_comparable_id: Optional[int] = None
    reference_sold_price: Optional[int] = None
    line_items_count: int
    total_cost: float
    line_items: List[Dict[str, Any]]


class V3PackagesResponse(BaseModel):
    success: bool
    listing_id: int
    run_id: Optional[str] = None
    smart_m2: Optional[Dict[str, Any]] = None
    target_pir: Optional[Dict[str, Any]] = None
    strategy_selection: Optional[Dict[str, Any]] = None
    packages: List[V3Package] = []
    error: Optional[str] = None


class V3LogEvent(BaseModel):
    created_at: Optional[str] = None
    job_id: str
    event_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    pipeline_jobs: Optional[Dict[str, Any]] = None


class V3LogsResponse(BaseModel):
    success: bool
    listing_id: int
    run_id: Optional[str] = None
    events: List[V3LogEvent] = []
    error: Optional[str] = None


@router.get("/{listing_id}/v3/status", response_model=V3StatusResponse)
async def get_v3_status(listing_id: int):
    try:
        latest_run = await db.get_latest_pipeline_run(listing_id)
        if latest_run:
            run_id = latest_run.get("run_id")
            counts = await db.get_pipeline_job_counts(run_id=run_id)
            latest_event = await db.get_latest_pipeline_job_event(run_id=run_id)
            current_checkpoint = latest_event.get("message") if latest_event else None

            if counts:
                queued = counts.get("queued", 0)
                in_progress = counts.get("in_progress", 0)
                failed = counts.get("failed", 0)
                succeeded = counts.get("succeeded", 0)

                if failed > 0:
                    status = "error"
                elif queued > 0 or in_progress > 0:
                    status = "in_progress"
                else:
                    status = "complete"

                return V3StatusResponse(
                    success=True,
                    listing_id=listing_id,
                    status=status,
                    run_id=run_id,
                    queued_jobs=queued,
                    in_progress_jobs=in_progress,
                    failed_jobs=failed,
                    succeeded_jobs=succeeded,
                    current_checkpoint=current_checkpoint,
                    checkpoints=[],
                )

        return V3StatusResponse(success=True, listing_id=listing_id, status="none", checkpoints=[])
    except Exception as exc:
        logger.error(f"V3 status failed: {exc}", exc_info=True)
        return V3StatusResponse(success=False, listing_id=listing_id, status="error", error=str(exc))


@router.get("/{listing_id}/v3/logs", response_model=V3LogsResponse)
async def get_v3_logs(
    listing_id: int,
    limit: int = Query(default=500, ge=1, le=2000),
    event_type: Optional[str] = Query(default=None, description="Optional filter, e.g. 'log' or 'failed'"),
):
    """
    Durable pipeline logs (job events) for the latest run of this listing.

    WHY THIS MATTERS: In production you cannot rely on seeing worker stdout.
    This endpoint makes the pipeline self-observing.
    """
    try:
        latest_run = await db.get_latest_pipeline_run(listing_id)
        if not latest_run:
            return V3LogsResponse(success=True, listing_id=listing_id, events=[])
        run_id = latest_run.get("run_id")
        if not run_id:
            return V3LogsResponse(success=True, listing_id=listing_id, events=[])

        events = await db.get_pipeline_job_events_for_run(run_id=run_id, limit=limit, event_type=event_type)
        return V3LogsResponse(success=True, listing_id=listing_id, run_id=run_id, events=events)
    except Exception as exc:
        logger.error(f"V3 logs failed: {exc}", exc_info=True)
        return V3LogsResponse(success=False, listing_id=listing_id, error=str(exc))


@router.get("/{listing_id}/v3/packages", response_model=V3PackagesResponse)
async def get_v3_packages(listing_id: int):
    try:
        smart_m2 = await db.get_smart_m2(listing_id)
        target_pir = await db.get_pir(listing_id, pir_type="target")
        strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")

        packages: List[V3Package] = []
        strategy_lookup = {s.get("strategy_name"): s for s in (strategy_selection or {}).get("strategies", [])}

        for strategy_name, strategy in strategy_lookup.items():
            line_items = await db.get_boq_line_items(listing_id, strategy_name)
            if not line_items:
                continue
            total_cost = sum(float(item.get("line_total") or 0) for item in line_items)
            packages.append(
                V3Package(
                    strategy_name=strategy_name,
                    reference_comparable_id=strategy.get("reference_comparable_id"),
                    reference_sold_price=strategy.get("reference_sold_price"),
                    line_items_count=len(line_items),
                    total_cost=total_cost,
                    line_items=line_items,
                )
            )

        return V3PackagesResponse(
            success=True,
            listing_id=listing_id,
            smart_m2=smart_m2,
            target_pir=target_pir,
            strategy_selection=strategy_selection,
            packages=packages,
        )
    except Exception as exc:
        logger.error(f"V3 packages failed: {exc}", exc_info=True)
        return V3PackagesResponse(success=False, listing_id=listing_id, error=str(exc))


@router.post("/{listing_id}/v3/packages", response_model=V3PackagesResponse)
async def run_v3_packages(listing_id: int):
    try:
        logger.info(f"🚀 Enqueuing V3 pipeline for listing {listing_id} (queue-based)")
        run_id = await enqueue_v3_run(db=db, listing_id=listing_id)
        return V3PackagesResponse(success=True, listing_id=listing_id, run_id=run_id)
    except Exception as exc:
        logger.error(f"V3 pipeline failed: {exc}", exc_info=True)
        return V3PackagesResponse(success=False, listing_id=listing_id, error=str(exc))
