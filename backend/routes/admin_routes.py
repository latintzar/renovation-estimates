"""
Admin Routes — Pipeline Admin Dashboard
========================================

Endpoints for the /admin dashboard:

Runs:
- GET  /api/admin/runs              — List all pipeline runs (most recent first)
- GET  /api/admin/runs/{run_id}     — Single run with job details
- GET  /api/admin/runs/{run_id}/logs — Full event log for a run

Listings:
- GET  /api/admin/listings          — All listings with latest run summary
- GET  /api/admin/listings/{id}     — Listing detail + latest run + all jobs
- POST /api/admin/listings/{id}/clear-from-stage — Clear downstream data + requeue
- POST /api/admin/listings/{id}/resume           — Requeue failed jobs
- POST /api/admin/listings/{id}/stop             — Cancel queued/in-progress jobs
- DELETE /api/admin/listings/{id}                — Delete listing + all data
- POST /api/admin/stop-all                       — Emergency stop all pipelines

Pipeline:
- GET  /api/admin/pipeline-version  — Current stage versions for staleness detection

WHY THIS EXISTS:
The admin dashboard at app.leo.casa/admin lets you monitor all listings,
view pipeline logs, clear/rerun from any stage, resume failed runs, and
delete listings. Replaces digging through Supabase or running CLI scripts.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

import database
from pipeline.v5_stages import (
    V5_STAGE_SEQUENCE,
    STAGE_NAMES_UNIQUE,
    ROOM_IMAGE_STATUS_STAGES,
    STAGE_LABELS,
    V5_JOB_TYPES,
    get_stage_versions,
    get_stages_from,
)
from pipeline.gla_stages import (
    GLA_STAGE_SEQUENCE,
    GLA_ORDERED_JOB_TYPES,
    STAGE_LABELS as GLA_STAGE_LABELS,
    get_gla_stage_versions,
)
from database import Database as Db
from pricing.v2_scheduler import enqueue_v2_run

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class RunSummary(BaseModel):
    run_id: str
    listing_id: int
    status: str
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Computed from jobs (V5 jobs ONLY for V5 pipelines)
    pipeline_type: str = "v5"  # "v5" | "gla" | "legacy"
    jobs_queued: int = 0
    jobs_in_progress: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    jobs_total: int = 0
    current_stage: Optional[str] = None
    stages: Optional[List[Dict[str, Any]]] = None
    last_event: Optional[Dict[str, Any]] = None  # {message, stage, created_at}


class RunDetail(RunSummary):
    jobs: List[Dict[str, Any]] = []


class LogEntry(BaseModel):
    id: Optional[int] = None
    job_id: Optional[str] = None
    event_type: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    # Joined from pipeline_jobs
    stage: Optional[str] = None
    job_type: Optional[str] = None


# =============================================================================
# HELPERS
# =============================================================================

async def _enrich_run_with_jobs(run: Dict[str, Any]) -> RunSummary:
    """
    Build RunSummary from materialized pipeline_runs status fields.

    WHY THIS MATTERS: status must have one source of truth. We no longer
    aggregate pipeline_jobs here; that logic lives in DB trigger function
    refresh_pipeline_run_status().
    """
    run_id = run["run_id"]
    config = run.get("config") or {}
    pipeline = str(config.get("pipeline") or "").strip().lower()
    is_v5 = pipeline == "v5"
    is_gla = pipeline == "gla"
    run = await database.ensure_run_materialized(run)
    stages = run.get("stages") if isinstance(run.get("stages"), list) else []
    jobs_queued = int(run.get("jobs_queued") or 0)
    jobs_in_progress = int(run.get("jobs_in_progress") or 0)
    jobs_succeeded = int(run.get("jobs_succeeded") or 0)
    jobs_failed = int(run.get("jobs_failed") or 0)
    jobs_total = int(run.get("jobs_total") or 0)
    current_stage = run.get("current_stage")

    # Fetch last pipeline event for this run (most recent activity)
    # NOTE: We query DESC + limit 1 directly because
    # get_pipeline_job_events_for_run orders ASC.
    last_event = None
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        evt_resp = await client.get(
            f"{base_url}/pipeline_job_events",
            params={
                "select": "*,pipeline_jobs!inner(run_id,stage,job_type)",
                "pipeline_jobs.run_id": f"eq.{run_id}",
                "order": "created_at.desc",
                "limit": "50",
            },
            headers=database._get_headers(),
        )
        if evt_resp.status_code == 200:
            rows = evt_resp.json() or []
            for evt in rows:
                job_info = evt.get("pipeline_jobs", {})
                job_type = job_info.get("job_type") if isinstance(job_info, dict) else None
                if is_v5 and job_type not in V5_JOB_TYPES:
                    continue
                if is_gla and job_type not in GLA_ORDERED_JOB_TYPES:
                    continue
                last_event = {
                    "message": evt.get("message"),
                    "stage": job_info.get("stage") if isinstance(job_info, dict) else None,
                    "event_type": evt.get("event_type"),
                    "created_at": evt.get("created_at"),
                }
                break
    except Exception as e:
        logger.debug(f"Failed to get last event for {run_id}: {e}")

    return RunSummary(
        run_id=run_id,
        listing_id=run.get("listing_id", 0),
        status=run.get("status", "unknown"),
        config=run.get("config"),
        created_at=run.get("created_at"),
        updated_at=run.get("updated_at"),
        pipeline_type="v5" if is_v5 else ("gla" if is_gla else "legacy"),
        jobs_queued=jobs_queued,
        jobs_in_progress=jobs_in_progress,
        jobs_succeeded=jobs_succeeded,
        jobs_failed=jobs_failed,
        jobs_total=jobs_total,
        current_stage=current_stage,
        stages=stages,
        last_event=last_event,
    )


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/runs")
async def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    listing_id: Optional[int] = Query(default=None),
):
    """
    List all pipeline runs, most recent first.
    Includes job counts and current stage for each run.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        params: Dict[str, str] = {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }
        if listing_id is not None:
            params["listing_id"] = f"eq.{listing_id}"

        resp = await client.get(
            f"{base_url}/pipeline_runs",
            params=params,
            headers=headers,
        )

        if resp.status_code != 200:
            logger.error(f"list_runs failed: {resp.status_code} {resp.text[:300]}")
            return {"success": False, "error": f"Database error: {resp.status_code}"}

        runs_raw = resp.json() or []

        # Enrich each run with job counts (parallel would be nice, but sequential is fine for admin)
        runs = []
        for run in runs_raw:
            try:
                enriched = await _enrich_run_with_jobs(run)
                runs.append(enriched.model_dump())
            except Exception as e:
                logger.warning(f"Failed to enrich run {run.get('run_id')}: {e}")
                runs.append({
                    **run,
                    "jobs_queued": 0, "jobs_in_progress": 0,
                    "jobs_succeeded": 0, "jobs_failed": 0, "jobs_total": 0,
                })

        return {
            "success": True,
            "runs": runs,
            "total": len(runs),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.exception(f"list_runs error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str):
    """
    Get a single run with all its jobs (stage, status, timing).
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        # Fetch the run
        resp = await client.get(
            f"{base_url}/pipeline_runs",
            params={"run_id": f"eq.{run_id}", "select": "*", "limit": "1"},
            headers=headers,
        )
        if resp.status_code != 200 or not resp.json():
            return {"success": False, "error": f"Run not found: {run_id}"}

        run = resp.json()[0]

        # Fetch all jobs
        jobs = await database.get_pipeline_jobs_for_run(run_id, limit=500)

        enriched = await _enrich_run_with_jobs(run)
        detail = enriched.model_dump()
        detail["jobs"] = jobs

        return {"success": True, "run": detail}
    except Exception as e:
        logger.exception(f"get_run_detail error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str,
    limit: int = Query(default=20000, ge=1, le=200000),
    event_type: Optional[str] = Query(default=None),
    latest: bool = Query(default=True),
):
    """
    Get pipeline_job_events for a run.

    Default behavior returns the newest events first (tail mode) and then
    reverses them to chronological order for display.

    WHY THIS MATTERS:
    - Operators care most about the newest logs during active debugging.
    - If an environment imposes a practical row cap, tail mode still includes
      the latest lines instead of only the oldest lines.
    Each event includes the stage and job_type from the parent job.
    This is the "deployment log" view — every line the pipeline produced.
    """
    try:
        # Fetch in pages because many PostgREST deployments cap each response at ~1000 rows.
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()
        events: List[Dict[str, Any]] = []
        fetched = 0
        page_size = 1000
        order_clause = "created_at.desc,id.desc" if latest else "created_at.asc,id.asc"
        while fetched < limit:
            batch_limit = min(page_size, limit - fetched)
            params: Dict[str, str] = {
                "select": "*,pipeline_jobs!inner(run_id,listing_id,stage,job_type)",
                "pipeline_jobs.run_id": f"eq.{run_id}",
                "order": order_clause,
                "limit": str(batch_limit),
                "offset": str(fetched),
            }
            if event_type:
                params["event_type"] = f"eq.{event_type}"

            resp = await client.get(
                f"{base_url}/pipeline_job_events",
                params=params,
                headers=headers,
            )
            if resp.status_code != 200:
                logger.error(f"get_run_logs failed: {resp.status_code} {resp.text[:500]}")
                return {"success": False, "error": f"Database error: {resp.status_code}"}

            batch = resp.json() or []
            if not batch:
                break
            events.extend(batch)
            fetched += len(batch)
            if len(batch) < batch_limit:
                break

        # When tail-mode is enabled we fetched newest-first for correctness;
        # convert back to chronological order for easier reading.
        if latest:
            events.reverse()

        # Flatten the joined job data for easier frontend consumption
        logs = []
        for evt in events:
            job_info = evt.get("pipeline_jobs", {})
            logs.append({
                "id": evt.get("id"),
                "job_id": evt.get("job_id"),
                "event_type": evt.get("event_type"),
                "message": evt.get("message"),
                "data": evt.get("data"),
                "created_at": evt.get("created_at"),
                "stage": job_info.get("stage") if isinstance(job_info, dict) else None,
                "job_type": job_info.get("job_type") if isinstance(job_info, dict) else None,
            })

        return {
            "success": True,
            "run_id": run_id,
            "logs": logs,
            "count": len(logs),
            "latest_mode": latest,
        }
    except Exception as e:
        logger.exception(f"get_run_logs error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/runs/{run_id}/costs")
async def get_run_costs(run_id: str):
    """
    Get cost tracking data for a pipeline run.
    Returns per-stage and per-model token counts + costs.
    This is the data behind the "Copy cost table" feature in the admin UI.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        def _to_float(v: Any) -> float:
            try:
                return float(v)
            except Exception:
                return 0.0

        async def _compute_clean_run_timing() -> Dict[str, Any]:
            """
            Compute "clean run" timing as cumulative job execution time.

            WHY THIS MATTERS:
            - Wall clock (first started -> last succeeded) includes gaps + cleared attempts.
            - clear-from-stage deletes downstream job events, so summing surviving succeeded
              `duration_s` produces a clean, rerun-safe total.
            """
            try:
                events = await database.get_pipeline_job_events_for_run(
                    run_id=run_id,
                    limit=5000,
                    event_type="succeeded",
                )
            except Exception as e:
                logger.warning(
                    "get_run_costs: timing query failed | run=%s | %s: %s",
                    run_id,
                    type(e).__name__,
                    e,
                )
                return {"clean_runtime_s": 0.0, "by_stage_s": {}, "jobs_counted": 0}

            total_s = 0.0
            jobs_counted = 0
            by_stage: Dict[str, float] = {}
            for evt in events or []:
                data = evt.get("data") if isinstance(evt, dict) else None
                dur = None
                if isinstance(data, dict):
                    dur = data.get("duration_s")
                try:
                    dur_f = float(dur) if dur is not None else None
                except Exception:
                    dur_f = None
                if dur_f is None or dur_f < 0:
                    continue
                jobs_counted += 1
                total_s += dur_f

                job_info = evt.get("pipeline_jobs") if isinstance(evt, dict) else None
                stage = job_info.get("stage") if isinstance(job_info, dict) else None
                if isinstance(stage, str) and stage:
                    by_stage[stage] = by_stage.get(stage, 0.0) + dur_f

            # Round for stable UI / copy text (we keep sub-second precision in DB).
            total_s = round(total_s, 3)
            by_stage = {k: round(v, 3) for k, v in by_stage.items()}
            return {"clean_runtime_s": total_s, "by_stage_s": by_stage, "jobs_counted": jobs_counted}

        timing = await _compute_clean_run_timing()

        # Source-of-truth: aggregated view derived from per-call gemini_call_log rows.
        # WHY THIS MATTERS: pipeline_cost_tracking can be stale or corrupted by racing writers.
        view_resp = await client.get(
            f"{base_url}/gemini_run_costs_v1",
            params={
                "run_id": f"eq.{run_id}",
                "select": "*",
                "limit": "1",
            },
            headers=headers,
        )
        if view_resp.status_code == 200:
            vrows = view_resp.json() or []
            if vrows:
                v = vrows[0]
                return {
                    "success": True,
                    "has_data": True,
                    "run_id": run_id,
                    "costs": {
                        "listing_id": v.get("listing_id"),
                        "status": "derived_from_gemini_call_log",
                        "total_calls": v.get("total_calls", 0),
                        "total_input_tokens": v.get("total_input_tokens", 0),
                        "total_output_tokens": v.get("total_output_tokens", 0),
                        "total_cost_regular": _to_float(v.get("total_cost_regular", 0)),
                        "total_cost_cached": _to_float(v.get("total_cost_cached", 0)),
                        "by_stage": v.get("by_stage", {}),
                        "by_model": v.get("by_model", {}),
                        "cleared_costs": v.get("cleared_costs", {}),
                        "first_call_at": v.get("first_call_at"),
                        "last_call_at": v.get("last_call_at"),
                        "timing": timing,
                    },
                }

        # Fallback: legacy table (kept for older runs/environments)
        resp = await client.get(
            f"{base_url}/pipeline_cost_tracking",
            params={
                "run_id": f"eq.{run_id}",
                "select": "*",
                "limit": "1",
            },
            headers=headers,
        )

        if resp.status_code != 200:
            return {"success": False, "error": f"DB error: {resp.status_code}"}

        rows = resp.json() or []
        if not rows:
            return {
                "success": True,
                "has_data": False,
                "run_id": run_id,
                "costs": None,
            }

        cost_data = rows[0]
        return {
            "success": True,
            "has_data": True,
            "run_id": run_id,
            "costs": {
                "listing_id": cost_data.get("listing_id"),
                "status": cost_data.get("status"),
                "total_calls": cost_data.get("total_calls", 0),
                "total_input_tokens": cost_data.get("total_input_tokens", 0),
                "total_output_tokens": cost_data.get("total_output_tokens", 0),
                "total_cost_regular": _to_float(cost_data.get("total_cost_regular", 0)),
                "total_cost_cached": _to_float(cost_data.get("total_cost_cached", 0)),
                "by_stage": cost_data.get("by_stage", {}),
                "by_model": cost_data.get("by_model", {}),
                "last_stage": cost_data.get("last_stage"),
                "run_started_at": cost_data.get("run_started_at"),
                "run_completed_at": cost_data.get("run_completed_at"),
                "created_at": cost_data.get("created_at"),
                "updated_at": cost_data.get("updated_at"),
                "timing": timing,
            },
        }
    except Exception as e:
        logger.exception(f"get_run_costs error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# PIPELINE VERSION (staleness detection)
# =============================================================================

@router.get("/pipeline-version")
async def get_pipeline_version():
    """
    Return current per-stage versions + stage metadata.
    The admin UI compares these against the versions stored in each run's config
    to detect stale listings that need rerunning.
    """
    return {
        "success": True,
        # Back-compat: these are V5 stage versions.
        "stage_versions": get_stage_versions(),
        "stages": [
            {"name": name, "label": STAGE_LABELS.get(name, name)}
            for name in STAGE_NAMES_UNIQUE
        ],
        # Additive: GLA stage metadata for the WhatsApp-first pipeline.
        "gla_stage_versions": get_gla_stage_versions(),
        "gla_stages": [
            {"name": stage, "label": GLA_STAGE_LABELS.get(stage, stage)}
            for stage, _job_type, _arts, _ver in GLA_STAGE_SEQUENCE
        ],
    }


# =============================================================================
# LISTINGS — List, Detail, Clear, Resume, Delete
# =============================================================================

@router.get("/listings")
async def list_listings():
    """
    List all listings with their latest run summary.
    Returns listing metadata + latest run status + job counts + staleness.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        # Fetch all listings (select all; table columns vary)
        resp = await client.get(
            f"{base_url}/listings",
            params={
                "select": "*",
                "order": "id.desc",
                "limit": "200",
            },
            headers=headers,
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"DB error fetching listings: {resp.status_code}"}

        listings_raw = resp.json() or []
        current_versions_v5 = get_stage_versions()
        current_versions_gla = get_gla_stage_versions()
        results = []

        for listing in listings_raw:
            lid = listing.get("id")
            item: Dict[str, Any] = {
                "id": lid,
                "url": listing.get("source_url") or listing.get("url"),
                "title": listing.get("title"),
                "created_at": listing.get("created_at"),
                "updated_at": listing.get("updated_at"),
                "latest_run": None,
                "stale_stages": [],
            }

            # Get latest run
            try:
                run = await database.get_latest_pipeline_run(lid)
                if run:
                    enriched = await _enrich_run_with_jobs(run)
                    run_dict = enriched.model_dump()

                    # Staleness check: compare stored versions with current
                    stored_versions = (run.get("config") or {}).get("stage_versions", {})
                    stale = []
                    if stored_versions:
                        # Use the correct stage registry for this pipeline.
                        pipeline = str(((run.get("config") or {}).get("pipeline") or "")).strip().lower()
                        if pipeline == "gla":
                            current_versions = current_versions_gla
                            labels = GLA_STAGE_LABELS
                        else:
                            current_versions = current_versions_v5
                            labels = STAGE_LABELS

                        for stage_name, current_ver in current_versions.items():
                            stored_ver = stored_versions.get(stage_name)
                            if stored_ver and stored_ver != current_ver:
                                stale.append({
                                    "stage": stage_name,
                                    "label": labels.get(stage_name, stage_name),
                                    "stored": stored_ver,
                                    "current": current_ver,
                                })

                    item["latest_run"] = run_dict
                    item["stale_stages"] = stale
            except Exception as e:
                logger.warning(f"Failed to get run for listing {lid}: {e}")

            results.append(item)

        return {"success": True, "listings": results, "total": len(results)}
    except Exception as e:
        logger.exception(f"list_listings error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/listings/{listing_id}")
async def get_listing_detail(listing_id: int):
    """
    Listing detail: metadata + latest run with all jobs + staleness info.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        # Fetch listing
        resp = await client.get(
            f"{base_url}/listings",
            params={"id": f"eq.{listing_id}", "select": "*", "limit": "1"},
            headers=headers,
        )
        if resp.status_code != 200 or not resp.json():
            return {"success": False, "error": f"Listing {listing_id} not found"}

        listing = resp.json()[0]

        # Latest run
        run = await database.get_latest_pipeline_run(listing_id)
        run_detail = None
        jobs = []
        stale_stages = []
        current_versions_v5 = get_stage_versions()
        current_versions_gla = get_gla_stage_versions()

        if run:
            enriched = await _enrich_run_with_jobs(run)
            run_detail = enriched.model_dump()
            jobs = await database.get_pipeline_jobs_for_run(run["run_id"], limit=500)
            run_detail["jobs"] = jobs

            stored_versions = (run.get("config") or {}).get("stage_versions", {})
            if stored_versions:
                pipeline = str(((run.get("config") or {}).get("pipeline") or "")).strip().lower()
                if pipeline == "gla":
                    current_versions = current_versions_gla
                    labels = GLA_STAGE_LABELS
                else:
                    current_versions = current_versions_v5
                    labels = STAGE_LABELS

                for stage_name, current_ver in current_versions.items():
                    stored_ver = stored_versions.get(stage_name)
                    if stored_ver and stored_ver != current_ver:
                        stale_stages.append({
                            "stage": stage_name,
                            "label": labels.get(stage_name, stage_name),
                            "stored": stored_ver,
                            "current": current_ver,
                        })

        return {
            "success": True,
            "listing": listing,
            "latest_run": run_detail,
            "stale_stages": stale_stages,
            # Back-compat: this key was V5-only. Keep it as V5 versions.
            "current_stage_versions": current_versions_v5,
            # Additive: allow the admin UI to render/compare GLA if desired.
            "current_stage_versions_gla": current_versions_gla,
        }
    except Exception as e:
        logger.exception(f"get_listing_detail error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/listings/{listing_id}/gla-detail")
async def get_gla_detail(listing_id: int):
    """
    GLA detail view payload for WhatsApp-first workflows.

    WHY THIS EXISTS:
    V5 admin UI is stage/comparables/cost focused. For GLA listings created via WhatsApp,
    operators need to see "behind the scenes": chat history, memory evolution, room
    opinions, generated image versions, and decisions.

    This endpoint is additive and best-effort: if some tables aren't present in an
    environment, we return empty arrays instead of failing the whole view.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        # ── Conversations (source of truth for phone_number) ─────────────────
        conversations: List[Dict[str, Any]] = []
        phone_number: Optional[str] = None
        try:
            conv_resp = await client.get(
                f"{base_url}/whatsapp_conversations",
                params={
                    "listing_id": f"eq.{listing_id}",
                    "order": "created_at.asc",
                    "limit": "200",
                },
                headers=headers,
            )
            if conv_resp.status_code == 200:
                conversations = conv_resp.json() or []
                # Prefer most recent conversation's phone number.
                if conversations:
                    phone_number = str(conversations[-1].get("phone_number") or "").strip() or None
        except Exception as e:
            logger.debug("get_gla_detail: whatsapp_conversations query failed | listing=%s | %s", listing_id, e)

        # ── User profile + chat messages (by phone) ──────────────────────────
        user_profile: Optional[Dict[str, Any]] = None
        chat_history: List[Dict[str, Any]] = []
        if phone_number:
            try:
                prof_resp = await client.get(
                    f"{base_url}/whatsapp_user_profiles",
                    params={"phone_number": f"eq.{phone_number}", "select": "*", "limit": "1"},
                    headers=headers,
                )
                if prof_resp.status_code == 200 and (prof_resp.json() or []):
                    user_profile = prof_resp.json()[0]
            except Exception as e:
                logger.debug("get_gla_detail: whatsapp_user_profiles query failed | phone=%s | %s", phone_number, e)

            # NOTE: whatsapp_messages historically did not store listing_id for all messages.
            # We therefore load by phone and let the UI filter by time / listing_id when present.
            # Once media support lands, this select list will expand; keep it resilient.
            try:
                msg_select = "id,role,message_type,message_text,created_at,listing_id,model,usage,media_urls,media_types"
                msg_resp = await client.get(
                    f"{base_url}/whatsapp_messages",
                    params={
                        "phone_number": f"eq.{phone_number}",
                        "order": "created_at.asc",
                        "limit": "500",
                        "select": msg_select,
                    },
                    headers=headers,
                )
                if msg_resp.status_code == 200:
                    chat_history = msg_resp.json() or []
                else:
                    # Fallback: older schema without media columns.
                    msg_resp2 = await client.get(
                        f"{base_url}/whatsapp_messages",
                        params={
                            "phone_number": f"eq.{phone_number}",
                            "order": "created_at.asc",
                            "limit": "500",
                            "select": "id,role,message_type,message_text,created_at,listing_id,model,usage",
                        },
                        headers=headers,
                    )
                    if msg_resp2.status_code == 200:
                        chat_history = msg_resp2.json() or []
            except Exception as e:
                logger.debug("get_gla_detail: whatsapp_messages query failed | phone=%s | %s", phone_number, e)

        # ── GLA artifacts ────────────────────────────────────────────────────
        gla_opinion: Optional[Dict[str, Any]] = None
        v5_pir_target: Optional[Dict[str, Any]] = None
        smart_m2: Optional[Dict[str, Any]] = None
        try:
            gla_opinion = await database.get_unified_estimate(listing_id, "gla_opinion")
        except Exception:
            gla_opinion = None
        try:
            v5_pir_target = await database.get_unified_estimate(listing_id, "v5_pir_target")
        except Exception:
            v5_pir_target = None
        try:
            smart_m2 = await database.get_smart_m2(listing_id)
        except Exception:
            smart_m2 = None

        # ── Generated images + decisions (best-effort; tables may not exist) ─
        image_versions: List[Dict[str, Any]] = []
        room_decisions: List[Dict[str, Any]] = []
        if phone_number:
            try:
                iv_resp = await client.get(
                    f"{base_url}/gla_image_versions",
                    params={
                        "listing_id": f"eq.{listing_id}",
                        "phone_number": f"eq.{phone_number}",
                        "order": "created_at.asc",
                        "limit": "500",
                        "select": "*",
                    },
                    headers=headers,
                )
                if iv_resp.status_code == 200:
                    image_versions = iv_resp.json() or []
            except Exception as e:
                logger.debug("get_gla_detail: gla_image_versions query failed | listing=%s | %s", listing_id, e)

            try:
                rd_resp = await client.get(
                    f"{base_url}/gla_room_decisions",
                    params={
                        "listing_id": f"eq.{listing_id}",
                        "phone_number": f"eq.{phone_number}",
                        "order": "updated_at.desc",
                        "limit": "200",
                        "select": "*",
                    },
                    headers=headers,
                )
                if rd_resp.status_code == 200:
                    room_decisions = rd_resp.json() or []
            except Exception as e:
                logger.debug("get_gla_detail: gla_room_decisions query failed | listing=%s | %s", listing_id, e)

        # ── Pipeline run status (reused from existing listing detail) ─────────
        run = await database.get_latest_pipeline_run(listing_id)
        pipeline_run: Optional[Dict[str, Any]] = None
        if run:
            enriched = await _enrich_run_with_jobs(run)
            pipeline_run = enriched.model_dump()
            try:
                jobs = await database.get_pipeline_jobs_for_run(run["run_id"], limit=500)
                pipeline_run["jobs"] = jobs
            except Exception:
                pipeline_run["jobs"] = []

        return {
            "success": True,
            "listing_id": listing_id,
            "phone_number": phone_number,
            "conversations": conversations,
            "user_profile": user_profile,
            "chat_history": chat_history,
            "gla_opinion": gla_opinion,
            "v5_pir_target": v5_pir_target,
            "smart_m2": smart_m2,
            "image_versions": image_versions,
            "room_decisions": room_decisions,
            "pipeline_run": pipeline_run,
        }
    except Exception as e:
        logger.exception("get_gla_detail error | listing=%s | %s", listing_id, e)
        return {"success": False, "error": str(e)}


class ClearFromStageRequest(BaseModel):
    from_stage: str


@router.post("/listings/{listing_id}/clear-from-stage")
async def clear_from_stage(listing_id: int, body: ClearFromStageRequest):
    """
    Clear downstream artifacts + requeue jobs from a given stage.
    This is the API version of scripts/rerun_from_stage.py.
    """
    from_stage = body.from_stage.strip()

    try:
        stages_to_clear = get_stages_from(from_stage)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        # ── Delete artifacts ──
        deleted = []
        for stage, job_type, artifacts, _ver in stages_to_clear:
            for art in artifacts:
                desc = await _delete_artifact(client, base_url, headers, listing_id, art)
                deleted.append(desc)

        # ── Find latest run ──
        run = await database.get_latest_pipeline_run(listing_id)
        created_new_v5_run = False
        created_run_id: Optional[str] = None

        # If this listing has never had a V5 run (or the latest run is legacy),
        # create a fresh V5 run so "clear-from-stage" works from the admin UI.
        #
        # WHY THIS MATTERS:
        # - The admin UI uses clear-from-stage as the primary "rerun from X" control.
        # - Some listings (older) only have legacy v3 runs, or have no run at all.
        # - Without a V5 run + jobs, there's nothing to requeue.
        needs_bootstrap = False
        if not run:
            needs_bootstrap = True
        else:
            cfg = run.get("config") if isinstance(run.get("config"), dict) else {}
            if (cfg.get("pipeline") or "").strip().lower() != "v5":
                needs_bootstrap = True

        if not needs_bootstrap and run:
            # Safety: a malformed/empty run row without jobs should be replaced.
            existing_run_id = str(run.get("run_id") or "").strip()
            if not existing_run_id:
                needs_bootstrap = True
            else:
                try:
                    jobs_probe = await database.get_pipeline_jobs_for_run(existing_run_id, limit=1)
                    if not jobs_probe:
                        needs_bootstrap = True
                except Exception:
                    # If we can't probe, don't risk creating duplicate runs.
                    pass

        if needs_bootstrap:
            logger.info(
                "clear_from_stage: bootstrapping new V5 run | listing=%s | from_stage=%s",
                listing_id,
                from_stage,
            )
            created_new_v5_run = True
            dbw = Db()
            created_run_id = await enqueue_v2_run(db=dbw, listing_id=listing_id)
            run = await database.get_latest_pipeline_run(listing_id)

        if not run:
            return {
                "success": False,
                "error": "Failed to find or create a pipeline run to requeue jobs",
                "deleted": deleted,
                "requeued": [],
            }

        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            return {
                "success": False,
                "error": "Pipeline run row missing run_id (cannot requeue jobs)",
                "deleted": deleted,
                "requeued": [],
            }

        # Build downstream stage set once (used for artifacts, logs, and requeue).
        stages_to_clear_names = {stage for stage, _job_type, _arts, _ver in stages_to_clear}

        # ── Cost tracking: mark downstream gemini_call_log rows as cleared ─────────
        # WHY THIS MATTERS:
        # clear-from-stage requeues jobs in the SAME run_id. Without this, per-call
        # usage rows would cause the rerun to double-count previous attempts.
        cleared_cost_rows = 0
        clear_seq: Optional[int] = None
        try:
            # Determine next clear sequence number for this run.
            seq_resp = await client.get(
                f"{base_url}/gemini_clear_events",
                params={
                    "run_id": f"eq.{run_id}",
                    "select": "clear_seq",
                    "order": "clear_seq.desc",
                    "limit": "1",
                },
                headers=headers,
            )
            if seq_resp.status_code == 200 and (seq_resp.json() or []):
                clear_seq = int((seq_resp.json()[0] or {}).get("clear_seq") or 0) + 1
            else:
                clear_seq = 1

            now_iso = datetime.now(timezone.utc).isoformat()
            # Record the clear event (for auditing / potential future UI).
            create_evt = await client.post(
                f"{base_url}/gemini_clear_events",
                json={
                    "listing_id": listing_id,
                    "run_id": run_id,
                    "clear_seq": clear_seq,
                    "from_stage": from_stage,
                    "stages": sorted(list(stages_to_clear_names)),
                    "created_at": now_iso,
                },
                headers={**headers, "Prefer": "return=representation"},
            )
            if create_evt.status_code not in (200, 201):
                logger.warning(
                    "clear_from_stage: failed to create gemini_clear_events row | listing=%s run=%s status=%s body=%s",
                    listing_id,
                    run_id,
                    create_evt.status_code,
                    (create_evt.text or "")[:300],
                )

            # Mark downstream call-log rows as cleared (exclude from active totals).
            # Include both V5 downstream stages AND legacy orphan stages.
            # WHY: legacy stages like "pir" aren't in the V5 set but their cost rows
            # must be cleared too, otherwise they double-count on every rerun.
            all_clear_stages = set(stages_to_clear_names)
            # Find any legacy stages that exist in gemini_call_log for this run
            legacy_stages_resp = await client.get(
                f"{base_url}/gemini_call_log",
                params={
                    "run_id": f"eq.{run_id}",
                    "cleared_seq": "is.null",
                    "select": "stage",
                },
                headers=headers,
            )
            if legacy_stages_resp.status_code == 200:
                for row in (legacy_stages_resp.json() or []):
                    s = str(row.get("stage") or "")
                    if s and s not in set(STAGE_NAMES_UNIQUE):
                        all_clear_stages.add(s)

            stage_list = ",".join(sorted(all_clear_stages))
            patch_resp = await client.patch(
                f"{base_url}/gemini_call_log",
                params={
                    "run_id": f"eq.{run_id}",
                    "cleared_seq": "is.null",
                    "stage": f"in.({stage_list})" if stage_list else "is.null",
                },
                json={
                    "cleared_seq": clear_seq,
                    "cleared_at": now_iso,
                    "cleared_from_stage": from_stage,
                },
                headers={**headers, "Prefer": "return=representation"},
            )
            if patch_resp.status_code == 200:
                rows = patch_resp.json() or []
                cleared_cost_rows = len(rows) if isinstance(rows, list) else 0
            elif patch_resp.status_code not in (204,):
                logger.warning(
                    "clear_from_stage: failed to mark gemini_call_log rows cleared | listing=%s run=%s status=%s body=%s",
                    listing_id,
                    run_id,
                    patch_resp.status_code,
                    (patch_resp.text or "")[:300],
                )
        except Exception as e:
            logger.warning(
                "clear_from_stage: gemini_call_log clear marking failed (continuing) | listing=%s run=%s | %s: %s",
                listing_id,
                run_id,
                type(e).__name__,
                e,
            )

        # ── Delete stale legacy pipeline_cost_tracking row ─────────────────────
        # WHY THIS MATTERS:
        # pipeline_cost_tracking is the LEGACY cost accumulator. The new system uses
        # per-call gemini_call_log rows + the gemini_run_costs_v1 view. But the cost
        # endpoint falls back to pipeline_cost_tracking when gemini_call_log is empty.
        # If we don't delete the legacy row on clear, the UI keeps showing the stale
        # total from the previous full run — even though all jobs were requeued.
        try:
            pct_resp = await client.delete(
                f"{base_url}/pipeline_cost_tracking",
                params={"run_id": f"eq.{run_id}"},
                headers=headers,
            )
            if pct_resp.status_code in (200, 204):
                logger.info(
                    "clear_from_stage: deleted pipeline_cost_tracking row | listing=%s run=%s",
                    listing_id,
                    run_id,
                )
            else:
                logger.warning(
                    "clear_from_stage: failed to delete pipeline_cost_tracking | listing=%s run=%s status=%s",
                    listing_id,
                    run_id,
                    pct_resp.status_code,
                )
        except Exception as e:
            logger.warning(
                "clear_from_stage: pipeline_cost_tracking cleanup failed (continuing) | listing=%s run=%s | %s: %s",
                listing_id,
                run_id,
                type(e).__name__,
                e,
            )

        # ── Clear durable comparables cache when rerunning comparables ────────
        # WHY THIS MATTERS:
        # - `fetch_comparables` treats existing `listing_comparables` rows as durable state
        #   and will NOT refetch from Casafari if rows exist.
        # - In reuse-only mode, `listing_market_stats.raw_filtered_comparables` can also
        #   rehydrate `listing_comparables`, producing the same set again.
        #
        # If the user clears from snapshot or comparables, they are explicitly asking for
        # a fresh comparable search. Clearing these tables makes the next run deterministic
        # and avoids “why are my comparables unchanged?” confusion.
        cleared_tables: List[str] = []
        try:
            if from_stage in ("snapshot", "comparables") or "comparables" in stages_to_clear_names:
                for table in ("listing_comparables", "listing_market_stats"):
                    resp = await client.delete(
                        f"{base_url}/{table}",
                        params={"listing_id": f"eq.{listing_id}"},
                        headers=headers,
                    )
                    if resp.status_code in (200, 204):
                        cleared_tables.append(table)
                    else:
                        logger.warning(
                            "clear_from_stage: failed to delete %s | listing=%s | status=%s | body=%s",
                            table,
                            listing_id,
                            resp.status_code,
                            (resp.text or "")[:300],
                        )
        except Exception as e:
            logger.warning(
                "clear_from_stage: comparables cache cleanup failed (continuing) | listing=%s | %s: %s",
                listing_id,
                type(e).__name__,
                e,
            )

        # ── Clear downstream run logs & insert summary bookmark ──
        # WHY: clear-from-stage should remove stale log history from that stage onward
        # and leave a single "cleared" event so the admin sees *when* and *why* old
        # logs disappeared, plus any failures in the previous attempt.
        cleared_log_events = 0
        downstream_jobs: List[Dict[str, Any]] = []  # populated below, used by cancel section too
        try:
            jobs: List[Dict[str, Any]] = []
            jobs_offset = 0
            jobs_page_size = 1000
            while True:
                jobs_resp = await client.get(
                    f"{base_url}/pipeline_jobs",
                    params={
                        "run_id": f"eq.{run_id}",
                        "select": "id,stage",
                        "order": "created_at.asc",
                        "limit": str(jobs_page_size),
                        "offset": str(jobs_offset),
                    },
                    headers=headers,
                )
                if jobs_resp.status_code != 200:
                    logger.warning(
                        "clear_from_stage: failed to list jobs for log cleanup | listing=%s run=%s status=%s",
                        listing_id,
                        run_id,
                        jobs_resp.status_code,
                    )
                    break
                batch = jobs_resp.json() or []
                if not batch:
                    break
                jobs.extend(batch)
                jobs_offset += len(batch)
                if len(batch) < jobs_page_size:
                    break

            # Include V5 downstream jobs AND pre-V5 jobs whose stage isn't in the V5 set.
            # WHY THIS MATTERS: older pipeline versions enqueued jobs with stages like "pir"
            # (job_type "generate_comparable_pir") that are NOT in V5_STAGE_SEQUENCE.
            # Without this, those jobs and their events survive every clear-from-stage call,
            # polluting admin logs and double-counting costs.
            all_v5_stage_names = set(STAGE_NAMES_UNIQUE)
            downstream_jobs = [
                j
                for j in (jobs or [])
                if j.get("id") and (
                    str(j.get("stage") or "") in stages_to_clear_names  # V5 downstream
                    or str(j.get("stage") or "") not in all_v5_stage_names  # pre-V5 job
                )
            ]
            downstream_job_ids = [str(j["id"]) for j in downstream_jobs]
            pre_v5_count = sum(
                1 for j in downstream_jobs
                if str(j.get("stage") or "") not in all_v5_stage_names
            )
            if pre_v5_count:
                logger.info(
                    "clear_from_stage: including %d pre-V5 jobs (stage not in V5 set) in cleanup | listing=%s run=%s",
                    pre_v5_count,
                    listing_id,
                    run_id,
                )

            # Summarise old logs per job BEFORE deleting (count events, failures, time range)
            per_job_summary: Dict[str, Dict[str, Any]] = {}
            for jid in downstream_job_ids:
                summary_resp = await client.get(
                    f"{base_url}/pipeline_job_events",
                    params={
                        "job_id": f"eq.{jid}",
                        "select": "event_type,created_at",
                        "order": "created_at.asc",
                    },
                    headers=headers,
                )
                if summary_resp.status_code == 200:
                    events = summary_resp.json() or []
                    if events:
                        fail_count = sum(1 for e in events if e.get("event_type") == "failed")
                        per_job_summary[jid] = {
                            "total_events": len(events),
                            "failures": fail_count,
                            "first_ts": events[0].get("created_at"),
                            "last_ts": events[-1].get("created_at"),
                        }

            # Delete old events
            for jid in downstream_job_ids:
                resp = await client.delete(
                    f"{base_url}/pipeline_job_events",
                    params={"job_id": f"eq.{jid}"},
                    headers=headers,
                )
                if resp.status_code in (200, 204):
                    try:
                        rows = resp.json() if resp.status_code == 200 else []
                        cleared_log_events += len(rows) if isinstance(rows, list) else 0
                    except Exception:
                        pass
                else:
                    logger.warning(
                        "clear_from_stage: failed to clear logs for job_id=%s | status=%s",
                        jid,
                        resp.status_code,
                    )

            # Insert a single "cleared" bookmark event per job
            now_iso = datetime.now(timezone.utc).isoformat()
            stage_label_map = {
                j.get("stage"): j.get("stage")
                for j in downstream_jobs
            }
            for jid in downstream_job_ids:
                job_stage = next(
                    (str(j.get("stage")) for j in downstream_jobs if str(j["id"]) == jid),
                    "unknown",
                )
                summary = per_job_summary.get(jid, {})
                total = summary.get("total_events", 0)
                fails = summary.get("failures", 0)

                if total == 0:
                    msg = f"Logs cleared — no previous logs for {job_stage}"
                else:
                    parts = [f"Cleared {total} previous log events"]
                    if fails:
                        parts.append(f"{fails} failure(s)")
                    time_range = ""
                    first = summary.get("first_ts")
                    last = summary.get("last_ts")
                    if first and last:
                        time_range = f" ({first[:19]}Z → {last[:19]}Z)"
                    msg = f"{' · '.join(parts)}{time_range} — rerunning {job_stage}"

                bookmark_event = {
                    "job_id": jid,
                    "event_type": "cleared",
                    "message": msg,
                    "data": {
                        "action": "clear_from_stage",
                        "from_stage": from_stage,
                        "previous_events": total,
                        "previous_failures": fails,
                    },
                    "created_at": now_iso,
                }
                await client.post(
                    f"{base_url}/pipeline_job_events",
                    json=bookmark_event,
                    headers=headers,
                )
        except Exception as e:
            logger.warning(
                "clear_from_stage: log cleanup failed (continuing) | listing=%s run=%s | %s: %s",
                listing_id,
                run_id,
                type(e).__name__,
                e,
            )

        # ── Reset V5 jobs (requeue) ──
        requeued = []
        for stage, job_type, artifacts, _ver in stages_to_clear:
            patch_body = {
                "status": "queued",
                "error": None,
                "error_context": None,
                "locked_by": None,
                "locked_until": None,
                "attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            h = {**headers, "Prefer": "return=representation"}
            resp = await client.patch(
                f"{base_url}/pipeline_jobs",
                json=patch_body,
                params={"run_id": f"eq.{run_id}", "job_type": f"eq.{job_type}"},
                headers=h,
            )
            rows = len(resp.json()) if resp.status_code == 200 else 0
            if rows:
                requeued.append(job_type)

        # ── Cancel pre-V5 jobs ──
        # WHY: pre-V5 jobs (e.g. old "generate_comparable_pir" with stage "pir") shouldn't
        # be requeued — they're superseded by V5 equivalents. Cancel them so they're inert.
        cancelled_legacy = 0
        pre_v5_jobs = [
            j for j in downstream_jobs
            if str(j.get("stage") or "") not in set(STAGE_NAMES_UNIQUE)
            and str(j.get("status") or "") not in ("cancelled",)
        ]
        if pre_v5_jobs:
            for pj in pre_v5_jobs:
                cancel_resp = await client.patch(
                    f"{base_url}/pipeline_jobs",
                    json={
                        "status": "cancelled",
                        "error": f"Pre-V5 job cancelled by clear-from-stage (stage '{pj.get('stage')}' not in V5 pipeline)",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    params={"id": f"eq.{str(pj['id'])}"},
                    headers={**headers, "Prefer": "return=representation"},
                )
                if cancel_resp.status_code == 200:
                    cancelled_legacy += 1
            if cancelled_legacy:
                logger.info(
                    "clear_from_stage: cancelled %d pre-V5 jobs | listing=%s run=%s",
                    cancelled_legacy,
                    listing_id,
                    run_id,
                )

        logger.info(
            f"clear_from_stage | listing={listing_id} | from={from_stage} | "
            f"deleted={len(deleted)} artifacts | requeued={len(requeued)} jobs | "
            f"log_events_cleared~={cleared_log_events} | pre_v5_cancelled={cancelled_legacy} | "
            f"legacy_cost_row_deleted=True"
        )

        return {
            "success": True,
            "listing_id": listing_id,
            "from_stage": from_stage,
            "deleted": deleted,
            "requeued": requeued,
            "logs_cleared": True,
            "cleared_log_events": cleared_log_events,
            "cleared_tables": cleared_tables,
            "costs_cleared": True,
            "cleared_cost_rows": cleared_cost_rows,
            "clear_seq": clear_seq,
            "pre_v5_jobs_cancelled": cancelled_legacy,
            "created_new_v5_run": created_new_v5_run,
            "created_run_id": created_run_id,
        }
    except Exception as e:
        logger.exception(f"clear_from_stage error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/listings/{listing_id}/stop")
async def stop_listing(listing_id: int):
    """
    Stop a listing's pipeline: cancel all queued and in_progress jobs in the latest run.
    Jobs that are already succeeded or failed are not touched.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        run = await database.get_latest_pipeline_run(listing_id)
        if not run:
            return {"success": False, "error": f"No run found for listing {listing_id}"}

        run_id = run["run_id"]

        cancelled = 0
        for status in ("queued", "in_progress"):
            patch_body = {
                "status": "cancelled",
                "error": "Stopped by admin",
                "locked_by": None,
                "locked_until": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            h = {**headers, "Prefer": "return=representation"}
            resp = await client.patch(
                f"{base_url}/pipeline_jobs",
                json=patch_body,
                params={"run_id": f"eq.{run_id}", "status": f"eq.{status}"},
                headers=h,
            )
            if resp.status_code == 200:
                cancelled += len(resp.json() or [])

        logger.info(f"stop | listing={listing_id} | run={run_id} | cancelled={cancelled}")

        return {
            "success": True,
            "listing_id": listing_id,
            "run_id": run_id,
            "cancelled": cancelled,
        }
    except Exception as e:
        logger.exception(f"stop error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/stop-all")
async def stop_all_pipelines():
    """
    Emergency stop: cancel ALL queued and in_progress jobs across ALL runs.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        cancelled = 0
        for status in ("queued", "in_progress"):
            patch_body = {
                "status": "cancelled",
                "error": "Stopped by admin (stop all)",
                "locked_by": None,
                "locked_until": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            h = {**headers, "Prefer": "return=representation"}
            resp = await client.patch(
                f"{base_url}/pipeline_jobs",
                json=patch_body,
                params={"status": f"eq.{status}"},
                headers=h,
            )
            if resp.status_code == 200:
                cancelled += len(resp.json() or [])

        logger.info(f"stop_all | cancelled={cancelled}")

        return {
            "success": True,
            "cancelled": cancelled,
        }
    except Exception as e:
        logger.exception(f"stop_all error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/resume-all")
async def resume_all_pipelines():
    """
    Resume ALL pipelines: requeue every failed or cancelled job across ALL runs.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        requeued = 0
        for status in ("failed", "cancelled"):
            patch_body = {
                "status": "queued",
                "error": None,
                "error_context": None,
                "locked_by": None,
                "locked_until": None,
                "attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            h = {**headers, "Prefer": "return=representation"}
            resp = await client.patch(
                f"{base_url}/pipeline_jobs",
                json=patch_body,
                params={"status": f"eq.{status}"},
                headers=h,
            )
            if resp.status_code == 200:
                requeued += len(resp.json() or [])

        logger.info(f"resume_all | requeued={requeued}")

        return {
            "success": True,
            "requeued": requeued,
        }
    except Exception as e:
        logger.exception(f"resume_all error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/listings/{listing_id}/resume")
async def resume_listing(listing_id: int):
    """
    Resume a listing: requeue all failed AND cancelled jobs in the latest run.
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        run = await database.get_latest_pipeline_run(listing_id)
        if not run:
            return {"success": False, "error": f"No run found for listing {listing_id}"}

        run_id = run["run_id"]
        jobs = await database.get_pipeline_jobs_for_run(run_id, limit=500)
        resumable_jobs = [j for j in jobs if j.get("status") in ("failed", "cancelled")]

        if not resumable_jobs:
            return {"success": True, "message": "No failed or cancelled jobs to resume", "requeued": 0}

        requeued = 0
        for job in resumable_jobs:
            patch_body = {
                "status": "queued",
                "error": None,
                "error_context": None,
                "locked_by": None,
                "locked_until": None,
                "attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            h = {**headers, "Prefer": "return=representation"}
            resp = await client.patch(
                f"{base_url}/pipeline_jobs",
                json=patch_body,
                params={"id": f"eq.{job['id']}"},
                headers=h,
            )
            if resp.status_code in (200, 204):
                requeued += 1

        logger.info(f"resume | listing={listing_id} | run={run_id} | requeued={requeued}/{len(resumable_jobs)}")

        return {
            "success": True,
            "listing_id": listing_id,
            "run_id": run_id,
            "requeued": requeued,
            "total_resumable": len(resumable_jobs),
        }
    except Exception as e:
        logger.exception(f"resume error: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/listings/{listing_id}")
async def delete_listing(listing_id: int):
    """
    Delete a listing and ALL associated data:
    - unified_estimates
    - photo_clusters
    - smart_m2
    - boq_line_items
    - listing_comparables
    - pipeline_job_events (via jobs)
    - pipeline_jobs
    - pipeline_cost_tracking
    - pipeline_runs
    - listings
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        headers = database._get_headers()

        tables_deleted = []

        # Order matters: delete child rows before parents
        for table, params in [
            ("unified_estimates", {"listing_id": f"eq.{listing_id}"}),
            ("photo_clusters", {"listing_id": f"eq.{listing_id}"}),
            ("smart_m2", {"listing_id": f"eq.{listing_id}"}),
            ("boq_line_items", {"listing_id": f"eq.{listing_id}"}),
            ("listing_comparables", {"listing_id": f"eq.{listing_id}"}),
            ("pipeline_cost_tracking", {"listing_id": f"eq.{listing_id}"}),
        ]:
            resp = await client.delete(
                f"{base_url}/{table}",
                params=params,
                headers=headers,
            )
            if resp.status_code in (200, 204):
                tables_deleted.append(table)
            else:
                logger.warning(f"delete {table} for listing {listing_id}: {resp.status_code}")

        # Delete pipeline_job_events for all jobs in all runs for this listing
        runs_resp = await client.get(
            f"{base_url}/pipeline_runs",
            params={"listing_id": f"eq.{listing_id}", "select": "run_id"},
            headers=headers,
        )
        if runs_resp.status_code == 200:
            for run in (runs_resp.json() or []):
                rid = run["run_id"]
                # Get job IDs
                jobs_resp = await client.get(
                    f"{base_url}/pipeline_jobs",
                    params={"run_id": f"eq.{rid}", "select": "id"},
                    headers=headers,
                )
                if jobs_resp.status_code == 200:
                    for job in (jobs_resp.json() or []):
                        await client.delete(
                            f"{base_url}/pipeline_job_events",
                            params={"job_id": f"eq.{job['id']}"},
                            headers=headers,
                        )
                # Delete jobs
                await client.delete(
                    f"{base_url}/pipeline_jobs",
                    params={"run_id": f"eq.{rid}"},
                    headers=headers,
                )
            # Delete runs
            await client.delete(
                f"{base_url}/pipeline_runs",
                params={"listing_id": f"eq.{listing_id}"},
                headers=headers,
            )
            tables_deleted.extend(["pipeline_job_events", "pipeline_jobs", "pipeline_runs"])

        # Finally delete the listing itself
        resp = await client.delete(
            f"{base_url}/listings",
            params={"id": f"eq.{listing_id}"},
            headers=headers,
        )
        if resp.status_code in (200, 204):
            tables_deleted.append("listings")

        logger.info(f"delete_listing | listing={listing_id} | tables={tables_deleted}")

        return {
            "success": True,
            "listing_id": listing_id,
            "tables_cleaned": tables_deleted,
        }
    except Exception as e:
        logger.exception(f"delete_listing error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# ARTIFACT DELETE HELPER (shared with clear-from-stage)
# =============================================================================

async def _delete_artifact(client, base_url: str, headers: dict, listing_id: int, artifact: str) -> str:
    """Delete one artifact spec. Returns description of what was deleted."""
    if artifact.startswith("ue:"):
        key = artifact[3:]
        await client.delete(
            f"{base_url}/unified_estimates",
            params={"listing_id": f"eq.{listing_id}", "package_type": f"eq.{key}"},
            headers=headers,
        )
        return f"unified_estimates[{key}]"

    elif artifact.startswith("ue_like:"):
        pattern = artifact[8:]
        await client.delete(
            f"{base_url}/unified_estimates",
            params={"listing_id": f"eq.{listing_id}", "package_type": f"like.{pattern}"},
            headers=headers,
        )
        return f"unified_estimates[like:{pattern}]"

    elif artifact == "boq_v4":
        await client.delete(
            f"{base_url}/boq_line_items",
            params={"listing_id": f"eq.{listing_id}", "dimension": "eq.v4"},
            headers=headers,
        )
        return "boq_line_items[dimension=v4]"

    elif artifact == "smart_m2":
        await client.delete(
            f"{base_url}/smart_m2",
            params={"listing_id": f"eq.{listing_id}"},
            headers=headers,
        )
        return "smart_m2"

    elif artifact == "photo_clusters":
        await client.delete(
            f"{base_url}/photo_clusters",
            params={"listing_id": f"eq.{listing_id}"},
            headers=headers,
        )
        return "photo_clusters"

    return f"unknown:{artifact}"
