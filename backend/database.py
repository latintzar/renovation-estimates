"""
Lean MVP Database Client
========================

Uses Supabase REST API for reliability.
Supports the full ListingEditor schema.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Supabase REST API client
_client: Optional[httpx.AsyncClient] = None
_boq_client: Optional[httpx.AsyncClient] = None


def _get_headers() -> Dict[str, str]:
    """Get headers for Supabase API calls."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _get_base_url() -> str:
    """Get Supabase REST API base URL."""
    return f"{settings.SUPABASE_URL}/rest/v1"


async def get_client() -> httpx.AsyncClient:
    """Get or create the HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0),
            headers=_get_headers(),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
        logger.info("✅ Supabase REST client created")
    return _client


async def get_boq_client() -> httpx.AsyncClient:
    """Get or create a dedicated client for BOQ writes (avoid pool contention)."""
    global _boq_client
    if _boq_client is None:
        _boq_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=120.0),
            headers=_get_headers(),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        )
        logger.info("✅ Supabase BOQ client created")
    return _boq_client


async def reset_boq_client() -> None:
    """Force recreation of the BOQ client (useful after connect timeouts)."""
    global _boq_client
    if _boq_client:
        await _boq_client.aclose()
        _boq_client = None
        logger.warning("⚠️ Supabase BOQ client reset")


async def close_pool():
    """Close the HTTP client."""
    global _client, _boq_client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("Supabase REST client closed")
    if _boq_client:
        await _boq_client.aclose()
        _boq_client = None
        logger.info("Supabase BOQ client closed")


# =============================================================================
# PIPELINE JOB QUEUE (Supabase Postgres RPC)
# =============================================================================

async def create_pipeline_run(run_id: str, listing_id: int, config: Optional[Dict[str, Any]] = None) -> bool:
    client = await get_client()
    base_url = _get_base_url()
    payload = {
        "run_id": run_id,
        "listing_id": listing_id,
        "status": "queued",
        "config": config or {},
    }
    resp = await client.post(f"{base_url}/pipeline_runs", json=payload, headers=_get_headers())
    return resp.status_code in (200, 201)


async def delete_pipeline_run(run_id: str) -> bool:
    """
    Delete a pipeline_run and its associated pipeline_jobs.

    WHY THIS MATTERS:
    - Stale runs with 0 jobs block new enqueues and make the status endpoint report
      "enqueue failed or idempotency collision" forever.
    - The only safe fix is to remove the broken run so a fresh one can be created.
    - We delete jobs first (FK constraint), then the run.
    """
    client = await get_client()
    base_url = _get_base_url()

    # 1. Delete all jobs belonging to this run
    resp_jobs = await client.delete(
        f"{base_url}/pipeline_jobs",
        params={"run_id": f"eq.{run_id}"},
        headers=_get_headers(),
    )
    if resp_jobs.status_code not in (200, 204):
        logger.error(f"delete_pipeline_run: failed to delete jobs for {run_id}: {resp_jobs.status_code} {resp_jobs.text[:300]}")
        return False

    # 2. Delete the run itself
    resp_run = await client.delete(
        f"{base_url}/pipeline_runs",
        params={"run_id": f"eq.{run_id}"},
        headers=_get_headers(),
    )
    if resp_run.status_code not in (200, 204):
        logger.error(f"delete_pipeline_run: failed to delete run {run_id}: {resp_run.status_code} {resp_run.text[:300]}")
        return False

    logger.info(f"Deleted stale pipeline run | run_id={run_id}")
    return True


async def get_latest_pipeline_run(listing_id: int) -> Optional[Dict[str, Any]]:
    """Get the most recent queue-based pipeline run for a listing (by created_at)."""
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.get(
        f"{base_url}/pipeline_runs",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": "1",
        },
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"get_latest_pipeline_run failed: {resp.status_code} {resp.text[:300]}")
        return None
    rows = resp.json()
    return rows[0] if rows else None


async def get_pipeline_job_counts(run_id: str) -> Dict[str, int]:
    """Return job counts by status for a run_id using server-side aggregation."""
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.post(
        f"{base_url}/rpc/pipeline_job_counts",
        json={"p_run_id": run_id},
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"pipeline_job_counts failed: {resp.status_code} {resp.text[:300]}")
        return {}
    out: Dict[str, int] = {"queued": 0, "in_progress": 0, "failed": 0, "succeeded": 0}
    for row in resp.json() or []:
        status = row.get("status")
        count = row.get("count") or 0
        if status in out:
            out[status] = int(count)
        else:
            out[str(status)] = int(count)
    return out


async def refresh_pipeline_run_status(run_id: str) -> bool:
    """
    Recompute materialized run status fields from pipeline_jobs.

    WHY THIS MATTERS: pipeline_runs is now the single status source of truth
    consumed by APIs/UI. This function gives us an explicit manual refresh hook.
    """
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.post(
        f"{base_url}/rpc/refresh_pipeline_run_status",
        json={"p_run_id": run_id},
        headers=_get_headers(),
    )
    if resp.status_code not in (200, 204):
        logger.error(f"refresh_pipeline_run_status failed: {resp.status_code} {resp.text[:500]}")
        return False
    return True


async def ensure_run_materialized(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a pipeline_runs row has materialized status fields populated.
    
    If jobs_total <= 0, calls refresh_pipeline_run_status and refetches.
    Returns the (possibly updated) run dict with guaranteed integer counts.
    
    WHY THIS MATTERS: Both admin_routes and v2_routes need this bootstrap
    logic. Having it in one place avoids drift.
    """
    run_id = run.get("run_id")
    jobs_total = int(run.get("jobs_total") or 0)

    if jobs_total <= 0 and run_id:
        try:
            await refresh_pipeline_run_status(run_id)
            listing_id = int(run.get("listing_id") or 0)
            if listing_id:
                latest = await get_latest_pipeline_run(listing_id)
                if latest and str(latest.get("run_id")) == str(run_id):
                    run = latest
        except Exception:
            pass

    # Normalize integer fields
    for key in ("jobs_queued", "jobs_in_progress", "jobs_succeeded", "jobs_failed", "jobs_total"):
        run[key] = int(run.get(key) or 0)

    stages = run.get("stages")
    if not isinstance(stages, list):
        run["stages"] = []

    return run


async def backfill_pipeline_run_statuses(limit: Optional[int] = None) -> int:
    """
    Recompute run-status materialization for many runs.

    Returns number of runs refreshed (best effort; 0 on failure).
    """
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.post(
        f"{base_url}/rpc/backfill_pipeline_run_statuses",
        json={"p_limit": limit},
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"backfill_pipeline_run_statuses failed: {resp.status_code} {resp.text[:500]}")
        return 0
    try:
        return int(resp.json() or 0)
    except Exception:
        return 0


async def reap_stuck_pipeline_jobs(
    stale_seconds: int = 600,
    heartbeat_grace_seconds: int = 300,
    limit: int = 100,
) -> int:
    """
    Mark stale in_progress jobs as failed when heartbeats have expired.

    WHY THIS MATTERS: without a reaper, dead workers leave jobs in_progress forever,
    causing runs to show as "running" indefinitely.
    """
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.post(
        f"{base_url}/rpc/reap_stuck_pipeline_jobs",
        json={
            "p_stale_seconds": int(stale_seconds),
            "p_heartbeat_grace_seconds": int(heartbeat_grace_seconds),
            "p_limit": int(limit),
        },
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"reap_stuck_pipeline_jobs failed: {resp.status_code} {resp.text[:500]}")
        return 0
    try:
        return int(resp.json() or 0)
    except Exception:
        return 0


async def get_pipeline_jobs_for_run(run_id: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch pipeline_jobs for a run_id (ordered by created_at).

    WHY THIS MATTERS:
    - The frontend needs stage-by-stage progress (not just total counts).
    - We keep this query cheap by selecting only the fields needed for progress UI.
    """
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.get(
        f"{base_url}/pipeline_jobs",
        params={
            "run_id": f"eq.{run_id}",
            "select": "id,stage,job_type,status,attempts,created_at,updated_at,available_at,locked_by,locked_until",
            "order": "created_at.asc",
            "limit": str(limit),
        },
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"get_pipeline_jobs_for_run failed: {resp.status_code} {resp.text[:300]}")
        return []
    return resp.json() or []


async def get_pipeline_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single pipeline_jobs row by id.

    WHY THIS MATTERS:
    - Admin "stop" marks jobs as cancelled.
    - Workers must honor cancellation for in-progress jobs (otherwise they will keep running
      and then overwrite cancelled -> succeeded).
    """
    if not job_id:
        return None
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.get(
        f"{base_url}/pipeline_jobs",
        params={
            "id": f"eq.{job_id}",
            "select": "id,run_id,listing_id,stage,job_type,status,updated_at,locked_by,locked_until",
            "limit": "1",
        },
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"get_pipeline_job failed: {resp.status_code} {resp.text[:300]}")
        return None
    rows = resp.json() or []
    return rows[0] if rows else None


async def enqueue_pipeline_job(
    run_id: str,
    listing_id: int,
    stage: str,
    job_type: str,
    payload: Dict[str, Any],
    idempotency_key: str,
    available_at: Optional[str] = None,
    max_attempts: int = 5,
) -> Optional[str]:
    """
    Enqueue a pipeline job via direct REST INSERT.

    WHY THIS MATTERS: The original RPC approach breaks with PostgREST 300
    (ambiguous overload — two function signatures differ only in integer vs bigint).
    Direct INSERT with ON CONFLICT on idempotency_key replicates the same
    idempotency guarantee without relying on the broken RPC.
    """
    import uuid as _uuid

    client = await get_client()
    base_url = _get_base_url()
    job_id = str(_uuid.uuid4())

    row: Dict[str, Any] = {
        "id": job_id,
        "run_id": run_id,
        "listing_id": listing_id,
        "stage": stage,
        "job_type": job_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "status": "queued",
        "max_attempts": max_attempts,
        "attempts": 0,
    }
    if available_at is not None:
        row["available_at"] = available_at

    headers = {**_get_headers(), "Prefer": "return=representation,resolution=ignore-duplicates"}
    resp = await client.post(
        f"{base_url}/pipeline_jobs",
        json=row,
        headers=headers,
        params={"on_conflict": "idempotency_key"},
    )
    if resp.status_code in (200, 201):
        rows = resp.json()
        if rows and isinstance(rows, list) and len(rows) > 0:
            return rows[0].get("id", job_id)
        # 200 with empty body means idempotency_key already exists (ignored)
        logger.info(f"enqueue_pipeline_job: idempotency_key already exists | key={idempotency_key}")
        return None
    logger.error(f"enqueue_pipeline_job failed: {resp.status_code} {resp.text[:800]}")
    return None


async def claim_pipeline_jobs(worker_id: str, limit: int = 10, lock_seconds: int = 300) -> List[Dict[str, Any]]:
    client = await get_client()
    base_url = _get_base_url()
    body = {"p_worker_id": worker_id, "p_limit": limit, "p_lock_seconds": lock_seconds}
    resp = await client.post(f"{base_url}/rpc/claim_pipeline_jobs", json=body, headers=_get_headers())
    if resp.status_code == 200:
        return resp.json()
    logger.error(f"claim_pipeline_jobs failed: {resp.status_code} {resp.text[:300]}")
    return []


async def add_pipeline_job_event(job_id: str, event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """Append an event to pipeline_job_events for observability (Notion-style run logs)."""
    client = await get_client()
    base_url = _get_base_url()
    payload: Dict[str, Any] = {
        "job_id": job_id,
        "event_type": event_type,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    resp = await client.post(f"{base_url}/pipeline_job_events", json=payload, headers=_get_headers())
    if resp.status_code in (200, 201):
        return True
    logger.error(f"add_pipeline_job_event failed: {resp.status_code} {resp.text[:500]}")
    return False


async def add_gemini_call_log_row(
    *,
    listing_id: int,
    run_id: str,
    stage: str,
    model: str,
    prompt_tokens: int,
    output_tokens: int,
    thinking_tokens: int,
    total_tokens: int,
    cost_regular: float,
    cost_cached: float,
    job_id: Optional[str] = None,
    job_type: Optional[str] = None,
    has_images: bool = False,
    pricing_tier: str = "standard",
    pricing_mode: str = "regular",
    usage_metadata: Optional[Dict[str, Any]] = None,
    request_meta: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Persist ONE Gemini call usage row (source-of-truth for cost tracking).

    WHY THIS MATTERS:
    - Pipeline cost reporting must never depend on parsing stdout logs.
    - In-memory token trackers can be reset or raced across jobs/listings.
    - We store per-call usage_metadata so we can always recompute totals.
    """
    client = await get_client()
    base_url = _get_base_url()

    def _jsonable(value: Any) -> Any:
        """
        Best-effort conversion to JSON-serializable primitives.
        This MUST be defensive: SDK objects (e.g. google.generativeai UsageMetadata)
        are not JSON serializable and should never be allowed to crash the pipeline.
        """
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for k, v in value.items():
                # PostgREST JSON keys must be strings
                out[str(k)] = _jsonable(v)
            return out
        if isinstance(value, (list, tuple, set)):
            return [_jsonable(v) for v in value]

        # Common SDK pattern: "to_dict()" yields a JSON-safe payload.
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            try:
                return _jsonable(to_dict())
            except Exception:
                pass

        # Fallback: attempt attribute dict.
        try:
            d = getattr(value, "__dict__", None)
            if isinstance(d, dict) and d:
                return _jsonable(d)
        except Exception:
            pass

        # Last resort: store as a string so we can still persist the row.
        try:
            return str(value)
        except Exception:
            return repr(value)

    row: Dict[str, Any] = {
        "listing_id": int(listing_id),
        "run_id": str(run_id),
        "job_id": str(job_id) if job_id else None,
        "stage": str(stage),
        "job_type": str(job_type) if job_type else None,
        "model": str(model),
        "has_images": bool(has_images),
        "pricing_tier": str(pricing_tier),
        "pricing_mode": str(pricing_mode),
        "prompt_tokens": int(prompt_tokens),
        "output_tokens": int(output_tokens),
        "thinking_tokens": int(thinking_tokens or 0),
        "total_tokens": int(total_tokens),
        "cost_regular": float(cost_regular),
        "cost_cached": float(cost_cached),
        "usage_metadata": _jsonable(usage_metadata) if usage_metadata is not None else None,
        "request_meta": _jsonable(request_meta) if request_meta is not None else None,
    }

    # Validate JSON serialization before sending to httpx.
    # WHY THIS MATTERS: httpx will raise TypeError during request building, which would
    # incorrectly surface as a "Gemini call failed" even if the model call succeeded.
    try:
        import json as _json  # local import to avoid global cost

        _json.dumps(row)
    except TypeError as exc:
        logger.error(
            "add_gemini_call_log_row: row not JSON-serializable; dropping metadata | err=%s | types=%s",
            str(exc),
            {
                "usage_metadata": type(row.get("usage_metadata")).__name__,
                "request_meta": type(row.get("request_meta")).__name__,
            },
        )
        row["usage_metadata"] = None
        row["request_meta"] = None

    headers = {**_get_headers(), "Prefer": "return=representation"}
    resp = await client.post(f"{base_url}/gemini_call_log", json=row, headers=headers)
    if resp.status_code in (200, 201):
        rows = resp.json()
        if isinstance(rows, list) and rows:
            return rows[0]
        if isinstance(rows, dict):
            return rows
        # Some PostgREST configs return empty body even with Prefer=return=representation.
        return {"success": True}

    logger.error(
        "add_gemini_call_log_row failed: %s %s | listing_id=%s run_id=%s stage=%s model=%s",
        resp.status_code,
        resp.text[:800],
        listing_id,
        run_id,
        stage,
        model,
    )
    return None


async def get_latest_pipeline_job_event(run_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent pipeline_job_event for a run."""
    client = await get_client()
    base_url = _get_base_url()
    resp = await client.get(
        f"{base_url}/pipeline_job_events",
        params={
            "select": "*,pipeline_jobs!inner(run_id)",
            "pipeline_jobs.run_id": f"eq.{run_id}",
            "order": "created_at.desc",
            "limit": "1",
        },
        headers=_get_headers(),
    )
    if resp.status_code != 200:
        logger.error(f"get_latest_pipeline_job_event failed: {resp.status_code} {resp.text[:300]}")
        return None
    rows = resp.json()
    return rows[0] if rows else None


async def get_pipeline_job_events_for_run(
    run_id: str,
    *,
    limit: int = 500,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch pipeline_job_events joined with pipeline_jobs for a given run.

    WHY THIS MATTERS: This is the durable, pipeline-native log transport.
    It powers "show me everything the pipeline did" without depending on stdout visibility.
    """
    client = await get_client()
    base_url = _get_base_url()
    params: Dict[str, str] = {
        "select": "*,pipeline_jobs!inner(run_id,listing_id,stage,job_type)",
        "pipeline_jobs.run_id": f"eq.{run_id}",
        "order": "created_at.asc",
        "limit": str(limit),
    }
    if event_type:
        params["event_type"] = f"eq.{event_type}"

    resp = await client.get(f"{base_url}/pipeline_job_events", params=params, headers=_get_headers())
    if resp.status_code != 200:
        logger.error(f"get_pipeline_job_events_for_run failed: {resp.status_code} {resp.text[:500]}")
        return []
    return resp.json() or []


async def extend_pipeline_job_lock(job_id: str, worker_id: str, lock_seconds: int = 60) -> bool:
    """
    Renew lock for a long-running job via direct REST PATCH.

    WHY THIS MATTERS: The original RPC has a text-vs-uuid overload that causes
    PostgREST 300. Direct PATCH avoids this entirely.
    """
    from datetime import datetime, timezone, timedelta

    client = await get_client()
    base_url = _get_base_url()
    new_until = (datetime.now(timezone.utc) + timedelta(seconds=lock_seconds)).isoformat()
    patch_body = {
        "locked_by": worker_id,
        "locked_until": new_until,
        "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Only extend locks for actively running jobs. If an admin cancels a job mid-flight,
    # we must NOT keep renewing the lock.
    headers = {**_get_headers(), "Prefer": "return=representation"}
    resp = await client.patch(
        f"{base_url}/pipeline_jobs",
        json=patch_body,
        params={"id": f"eq.{job_id}", "status": "eq.in_progress"},
        headers=headers,
    )
    if resp.status_code not in (200, 204):
        logger.warning(f"extend_pipeline_job_lock failed: {resp.status_code} {resp.text[:300]}")
        return False
    # With Prefer:return=representation, a successful update returns the updated row(s).
    # If the filter matched zero rows (e.g., job already cancelled), treat as not-ok.
    if resp.status_code == 200:
        try:
            rows = resp.json() or []
            return bool(rows)
        except Exception:
            return False
    return True


async def ack_pipeline_job(job_id: str) -> bool:
    """
    Mark a pipeline job as succeeded via direct REST PATCH.

    WHY THIS MATTERS: The original RPC has a text-vs-uuid overload that causes
    PostgREST 300. Direct PATCH avoids this entirely.
    """
    from datetime import datetime, timezone

    client = await get_client()
    base_url = _get_base_url()
    now_iso = datetime.now(timezone.utc).isoformat()
    patch_body = {
        "status": "succeeded",
        "finished_at": now_iso,
        "updated_at": now_iso,
    }
    # Only ack jobs that are still in_progress. If an admin cancels a job mid-flight,
    # this prevents overwriting cancelled -> succeeded.
    headers = {**_get_headers(), "Prefer": "return=representation"}
    resp = await client.patch(
        f"{base_url}/pipeline_jobs",
        json=patch_body,
        params={"id": f"eq.{job_id}", "status": "eq.in_progress"},
        headers=headers,
    )
    if resp.status_code not in (200, 204):
        logger.error(f"ack_pipeline_job failed: {resp.status_code} {resp.text[:300]}")
        return False
    if resp.status_code == 200:
        try:
            rows = resp.json() or []
            return bool(rows)
        except Exception:
            return False
    return True


async def requeue_pipeline_job(
    job_id: str,
    payload: Optional[Dict[str, Any]] = None,
    available_at: Optional[str] = None,
    reason: Optional[str] = None,
) -> bool:
    """
    Return an in-flight pipeline job to queued state.

    WHY THIS MATTERS: waiting for prerequisites should not mark the current job
    as succeeded or failed. We requeue the same row so stage status remains
    truthful and idempotency keys stay stable.
    """
    from datetime import datetime, timezone

    client = await get_client()
    base_url = _get_base_url()
    now_iso = datetime.now(timezone.utc).isoformat()
    patch_body: Dict[str, Any] = {
        "status": "queued",
        "updated_at": now_iso,
        "finished_at": None,
        "locked_by": None,
        "locked_until": None,
        "error_context": None,
    }
    if payload is not None:
        patch_body["payload"] = payload
    if available_at is not None:
        patch_body["available_at"] = available_at
    if reason is not None:
        patch_body["error"] = reason

    resp = await client.patch(
        f"{base_url}/pipeline_jobs",
        json=patch_body,
        params={"id": f"eq.{job_id}"},
        headers=_get_headers(),
    )
    if resp.status_code not in (200, 204):
        logger.error(f"requeue_pipeline_job failed: {resp.status_code} {resp.text[:500]}")
        return False
    return True


async def fail_pipeline_job(job_id: str, error: str, error_context: Optional[Dict[str, Any]] = None, retry_in_seconds: Optional[int] = None) -> bool:
    """
    Mark a pipeline job as failed via direct REST PATCH.

    WHY THIS MATTERS: The original RPC has a text-vs-uuid overload that causes
    PostgREST 300. Failing a job must be durable; otherwise the worker will
    continuously re-claim the same job and spam the queue.
    """
    from datetime import datetime, timezone

    client = await get_client()
    base_url = _get_base_url()
    now_iso = datetime.now(timezone.utc).isoformat()
    patch_body: Dict[str, Any] = {
        "status": "failed",
        "error": error,
        "finished_at": now_iso,
        "updated_at": now_iso,
    }
    if error_context is not None:
        patch_body["error_context"] = error_context
    resp = await client.patch(
        f"{base_url}/pipeline_jobs",
        json=patch_body,
        params={"id": f"eq.{job_id}"},
        headers=_get_headers(),
    )
    if resp.status_code not in (200, 204):
        logger.error(f"fail_pipeline_job failed: {resp.status_code} {resp.text[:300]}")
        return False
    return True


# =============================================================================
# LISTINGS CRUD (Full Schema)
# =============================================================================

async def create_listing(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new listing with full schema support.
    Handles all ListingEditor fields.
    """
    client = await get_boq_client()
    base_url = _get_base_url()
    
    # Extract areas if present
    areas = data.get("areas", {})
    m2_built = areas.get("constructed") or data.get("m2_built") or data.get("sqm")
    m2_useful = areas.get("useful") or data.get("m2_useful")
    
    # Prepare listing data with full schema (exclude image_urls - stored separately)
    # Note: listing_type, floor_level stored in scraped_data JSONB
    listing_data = {
        # Core Info
        "source_url": data.get("source_url"),
        "source_domain": data.get("source_domain"),
        "title": data.get("title"),
        "description": data.get("description"),
        
        # Numbers
        "price_eur": data.get("price_eur"),
        "bedrooms": data.get("bedrooms"),
        "bathrooms": data.get("bathrooms"),
        
        # Areas
        "sqm": m2_built,  # Primary field for area
        
        # Location
        "address": data.get("address"),
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country", "Spain"),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        
        # Property Classification
        "property_type": data.get("property_subtype") or data.get("property_type"),
        
        # Boolean Amenities
        "has_elevator": data.get("has_elevator"),
        
        # Features
        "features": data.get("features") or data.get("amenities") or [],
        
        # Full scraped data for reference (includes listing_type, floor_level, etc.)
        "scraped_data": data.get("scraped_data") or _build_scraped_data(data),
        
        # Status
        "pipeline_status": "scraped",
    }
    
    # Remove None values
    listing_data = {k: v for k, v in listing_data.items() if v is not None}
    
    # Insert listing
    response = await client.post(
        f"{base_url}/listings",
        json=listing_data,
    )
    
    if response.status_code not in (200, 201):
        logger.error(f"❌ Create listing failed: {response.status_code} {response.text}")
        raise Exception(f"Failed to create listing: {response.text}")
    
    listings = response.json()
    logger.debug(f"create_listing response type={type(listings).__name__} | status={response.status_code}")
    
    if listings is None:
        raise ValueError(
            f"create_listing got null response body (status {response.status_code}). "
            f"Possible cause: missing 'Prefer: return=representation' header or PostgREST misconfiguration."
        )
    
    if isinstance(listings, list):
        if not listings:
            raise ValueError(
                f"create_listing got empty array response (status {response.status_code}). "
                f"Possible cause: RLS policy blocking read-back of inserted row."
            )
        listing = listings[0]
    elif isinstance(listings, dict):
        listing = listings
    else:
        raise ValueError(
            f"create_listing got unexpected response type {type(listings).__name__}: {str(listings)[:200]}"
        )
    
    if "id" not in listing:
        raise ValueError(
            f"create_listing response missing 'id' field. Keys: {list(listing.keys())}"
        )
    
    # Insert photos if provided
    image_urls = data.get("image_urls") or data.get("photo_urls") or []
    if image_urls:
        photos_data = [
            {
                "listing_id": listing["id"],
                "url": url,
                "display_order": i,
                "is_primary": i == 0,
            }
            for i, url in enumerate(image_urls)
            if url  # Filter out None/empty URLs
        ]
        
        if photos_data:
            await client.post(
                f"{base_url}/listing_photos",
                json=photos_data,
            )
            logger.info(f"📸 Stored {len(photos_data)} photos for listing {listing['id']}")
    
    logger.info(f"✅ Created listing {listing['id']}: {listing.get('title', 'Untitled')}")
    return listing


def _build_scraped_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build scraped_data from individual fields for storage."""
    # Get photos from various sources
    photos = data.get("image_urls") or data.get("photo_urls") or []
    
    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "price_eur": data.get("price_eur"),
        "bedrooms": data.get("bedrooms"),
        "bathrooms": data.get("bathrooms"),
        "m2_built": data.get("m2_built") or data.get("areas", {}).get("constructed"),
        "m2_useful": data.get("m2_useful") or data.get("areas", {}).get("useful"),
        "listing_type": data.get("listing_type"),
        "price_period": data.get("price_period"),
        "address": data.get("address"),
        "city": data.get("city"),
        "neighborhood": data.get("neighborhood"),
        "region": data.get("region"),
        "country": data.get("country"),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "property_subtype": data.get("property_subtype"),
        "housing_situation": data.get("housing_situation"),
        "ad_origin": data.get("ad_origin"),
        "condition": data.get("condition"),
        "floor_level": data.get("floor_level"),
        "floor_number": data.get("floor_number"),
        "has_elevator": data.get("has_elevator"),
        "is_exterior": data.get("is_exterior"),
        "has_terrace": data.get("has_terrace"),
        "has_balcony": data.get("has_balcony"),
        "has_pool": data.get("has_pool"),
        "has_garage": data.get("has_garage"),
        "has_garden": data.get("has_garden"),
        "has_storage": data.get("has_storage"),
        "has_air_conditioning": data.get("has_air_conditioning"),
        "has_wardrobes": data.get("has_wardrobes"),
        "is_accessible": data.get("is_accessible"),
        "amenities": data.get("amenities") or data.get("features") or [],
        "additionalFeatures": data.get("additionalFeatures") or [],
        "reference": data.get("reference"),
        "agency": data.get("agency"),
        # Include photos in scraped_data for reference
        "image_urls": photos,
        "photo_urls": photos,
    }


async def get_listing(listing_id: int) -> Optional[Dict[str, Any]]:
    """Get a listing by ID."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/listings",
        params={"id": f"eq.{listing_id}", "select": "*"},
    )
    
    if response.status_code != 200:
        return None
    
    listings = response.json()
    return listings[0] if listings else None


async def get_listing_with_photos(listing_id: int) -> Optional[Dict[str, Any]]:
    """Get a listing with its photos, merging scraped_data for full field access."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Get listing
    listing = await get_listing(listing_id)
    if not listing:
        return None
    
    # CRITICAL: Merge scraped_data back into the listing for full field access
    # scraped_data contains floor_level, floor_number, condition, amenities, etc.
    scraped_data = listing.get("scraped_data") or {}
    if isinstance(scraped_data, dict):
        for key, value in scraped_data.items():
            # Only fill in if the column value is None/missing
            if listing.get(key) is None and value is not None:
                listing[key] = value
    
    # Get photos
    response = await client.get(
        f"{base_url}/listing_photos",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "url",
            "order": "display_order",
        },
    )
    
    photos = response.json() if response.status_code == 200 else []
    listing["photos"] = [p["url"] for p in photos]
    
    return listing


async def get_listings(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all listings with photos."""
    client = await get_client()
    base_url = _get_base_url()
    
    params = {
        "select": "*",
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    
    response = await client.get(f"{base_url}/listings", params=params)
    
    if response.status_code != 200:
        logger.error(f"❌ Get listings failed: {response.status_code}")
        return []
    
    listings = response.json()
    
    # Get photos for each listing and merge scraped_data
    for listing in listings:
        # Merge scraped_data back into the listing for full field access
        scraped_data = listing.get("scraped_data") or {}
        if isinstance(scraped_data, dict):
            for key, value in scraped_data.items():
                if listing.get(key) is None and value is not None:
                    listing[key] = value
        
        # Get photos
        photos_response = await client.get(
            f"{base_url}/listing_photos",
            params={
                "listing_id": f"eq.{listing['id']}",
                "select": "url",
                "order": "display_order",
            },
        )
        photos = photos_response.json() if photos_response.status_code == 200 else []
        listing["photos"] = [p["url"] for p in photos]
    
    return listings


async def update_listing(listing_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a listing."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Remove None values and internal fields
    update_data = {k: v for k, v in data.items() if v is not None and k not in ("id", "created_at")}
    
    if not update_data:
        return await get_listing(listing_id)
    
    response = await client.patch(
        f"{base_url}/listings",
        params={"id": f"eq.{listing_id}"},
        json=update_data,
    )
    
    if response.status_code != 200:
        logger.error(f"❌ Update listing failed: {response.status_code}")
        return None
    
    listings = response.json()
    return listings[0] if listings else None


async def delete_listing(listing_id: int) -> bool:
    """Delete a listing and its photos."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Delete photos first (foreign key constraint)
    await client.delete(
        f"{base_url}/listing_photos",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    # Delete listing
    response = await client.delete(
        f"{base_url}/listings",
        params={"id": f"eq.{listing_id}"},
    )
    
    return response.status_code in (200, 204)


async def get_listing_photos(listing_id: int) -> List[str]:
    """Get photo URLs for a listing."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/listing_photos",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "url",
            "order": "display_order",
        },
    )
    
    if response.status_code != 200:
        return []
    
    photos = response.json()
    return [p["url"] for p in photos if p.get("url")]


async def count_listings(user_id: Optional[str] = None) -> int:
    """Count total listings."""
    client = await get_client()
    base_url = _get_base_url()
    
    params = {"select": "id", "limit": "0"}
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    
    # Use HEAD request with Prefer: count=exact
    response = await client.head(
        f"{base_url}/listings",
        params=params,
        headers={**_get_headers(), "Prefer": "count=exact"},
    )
    
    # Get count from Content-Range header
    content_range = response.headers.get("content-range", "*/0")
    try:
        total = int(content_range.split("/")[1])
        return total
    except (IndexError, ValueError):
        return 0


# =============================================================================
# HEALTH CHECK
# =============================================================================

async def check_health() -> bool:
    """Check database connectivity."""
    try:
        client = await get_client()
        base_url = _get_base_url()
        
        response = await client.get(
            f"{base_url}/listings",
            params={"select": "id", "limit": "1"},
        )
        
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


# =============================================================================
# COMPARABLES & MARKET STATS
# =============================================================================

async def get_listing_comparables(listing_id: int) -> List[Dict[str, Any]]:
    """Get comparables for a listing."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/listing_comparables",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "*",
            "order": "distance_km"
        },
    )
    
    if response.status_code != 200:
        return []
    
    return response.json()


async def get_listing_market_stats(listing_id: int) -> Optional[Dict[str, Any]]:
    """Get listing_market_stats row for a listing (may include raw Casafari payloads)."""
    client = await get_client()
    base_url = _get_base_url()

    resp = await client.get(
        f"{base_url}/listing_market_stats",
        params={"listing_id": f"eq.{listing_id}", "select": "*", "limit": "1"},
    )
    if resp.status_code != 200:
        logger.error(f"get_listing_market_stats failed: {resp.status_code} {resp.text[:300]}")
        return None
    rows = resp.json() or []
    return rows[0] if rows else None


async def save_listing_market_stats(
    listing_id: int,
    stats: Dict[str, Any],
    search_params: Optional[Dict[str, Any]] = None,
    raw_casafari_response: Optional[Dict[str, Any]] = None,
    raw_filtered_comparables: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Upsert listing market stats (Casafari summary)."""
    client = await get_client()
    base_url = _get_base_url()
    numeric_fields = {
        "average_price",
        "average_price_per_sqm",
        "average_days_on_market",
        "sold_last_6_months",
        "casafari_fast_sell",
        "casafari_fair_market",
        "casafari_premium",
        "filtered_fast_sell",
        "filtered_fair_market",
        "filtered_premium",
        "filtered_comparables_count",
        "casafari_comparables_count",
        "asking_price",
    }

    def _as_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    payload: Dict[str, Any] = {
        "listing_id": listing_id,
        **(stats or {}),
        "search_params": search_params or {},
        "raw_casafari_response": raw_casafari_response,
        "raw_filtered_comparables": raw_filtered_comparables,
    }
    for key in list(payload.keys()):
        if key in numeric_fields:
            coerced = _as_int(payload.get(key))
            if coerced is None:
                payload.pop(key, None)
            else:
                payload[key] = coerced
    headers = _get_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        response = await client.post(
        f"{base_url}/listing_market_stats",
        params={"on_conflict": "listing_id"},
        json=payload,
            headers=headers,
        )
        if response.status_code in (200, 201, 204):
            return True

        if response.status_code == 400:
            try:
                message = response.json().get("message", "")
            except Exception:
                message = response.text
            import re

            match = re.search(r"Could not find the '([^']+)' column", message)
            if match:
                missing_column = match.group(1)
                if missing_column in payload:
                    logger.warning(
                        f"save_listing_market_stats: dropping missing column | column={missing_column} | listing_id={listing_id}"
                    )
                    payload.pop(missing_column, None)
                    continue

        logger.error(f"save_listing_market_stats failed: {response.status_code} {response.text[:300]}")
        if attempt < max_attempts:
            await asyncio.sleep(0.5 * attempt)
            continue
        return False
    logger.error(f"save_listing_market_stats failed: exceeded retries | listing_id={listing_id}")
    return False


async def replace_listing_comparables(listing_id: int, rows: List[Dict[str, Any]]) -> bool:
    """Replace listing comparables for a listing with a new set."""
    client = await get_client()
    base_url = _get_base_url()

    # Clear existing comparables
    await client.delete(
        f"{base_url}/listing_comparables",
        params={"listing_id": f"eq.{listing_id}"},
    )

    if not rows:
        return True

    def _as_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def _as_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # Only allow columns that exist in listing_comparables (avoid schema drift failures).
    allowed_keys = {
        "listing_id",
        "casafari_property_id",
        "price_bucket",
        "sale_price",
        "price_per_sqm",
        "total_area",
        "living_area",
        "plot_area",
        "bedrooms",
        "bathrooms",
        "condition",
        "construction_year",
        "distance_km",
        "address",
        "zip_code",
        "property_url",
        "photo_urls",
        "coordinates",
        "features",
        "energy_rating",
        "days_on_market",
        "is_filtered",
        "similarity_score",
        "analysis_status",
        "analysis_error",
        "full_analysis_status",
        "clusters_count",
        "rooms_analyzed",
        "overall_condition_score",
        "overall_condition_label",
        "full_analysis_started_at",
        "full_analysis_completed_at",
    }

    for row in rows:
        casafari_property_id = _as_int(row.get("casafari_property_id") or row.get("property_id"))
        if casafari_property_id is None:
            raise RuntimeError(f"replace_listing_comparables: missing casafari_property_id | listing_id={listing_id}")

        payload_raw: Dict[str, Any] = {"listing_id": listing_id, **(row or {})}
        payload_raw["casafari_property_id"] = casafari_property_id
        payload_raw["sale_price"] = _as_int(row.get("sale_price"))
        payload_raw["price_per_sqm"] = _as_int(row.get("price_per_sqm"))
        payload_raw["total_area"] = _as_int(row.get("total_area"))
        payload_raw["living_area"] = _as_int(row.get("living_area"))
        payload_raw["plot_area"] = _as_int(row.get("plot_area"))
        payload_raw["bedrooms"] = _as_int(row.get("bedrooms"))
        payload_raw["bathrooms"] = _as_int(row.get("bathrooms"))
        payload_raw["construction_year"] = _as_int(row.get("construction_year"))
        payload_raw["days_on_market"] = _as_int(row.get("days_on_market"))
        payload_raw["distance_km"] = _as_float(row.get("distance_km"))

        payload = {k: v for k, v in payload_raw.items() if k in allowed_keys}
        response = await client.post(
            f"{base_url}/listing_comparables",
            json=payload,
        )
        if response.status_code not in (200, 201):
            logger.error(f"replace_listing_comparables failed: {response.status_code} {response.text[:300]}")
            return False

    return True




async def save_photo_clusters(
    listing_id: int,
    clusters: List[Dict[str, Any]],
    excluded_content: List[Dict[str, Any]] = None,
    ai_image_summary: Dict[str, Any] = None
) -> bool:
    """Save photo clusters for a listing (V0.4.8)."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Delete existing clusters for this listing
    await client.delete(
        f"{base_url}/photo_clusters",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    # Insert new clusters
    for cluster in clusters:
        data = {
            "listing_id": listing_id,
            "cluster_id": cluster.get("cluster_id", ""),
            "cluster_name": cluster.get("cluster_name", ""),
            "room_type": cluster.get("room_type", ""),
            "photo_urls": cluster.get("photo_urls", []),
            "photo_count": len(cluster.get("photo_urls", [])),
            "is_real": cluster.get("is_real", True),
            "confidence": cluster.get("confidence", 0.9),
        }
        
        response = await client.post(
            f"{base_url}/photo_clusters",
            json=data,
        )
        
        if response.status_code not in (200, 201):
            logger.error(f"Failed to save cluster: {response.text}")
            return False
    
    return True


async def get_photo_clusters(listing_id: int) -> List[Dict[str, Any]]:
    """Get photo clusters for a listing (V0.4.8)."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/photo_clusters",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "*",
        },
    )
    
    if response.status_code != 200:
        return []
    
    return response.json()


async def get_comparable_clusters(comparable_id: int) -> List[Dict[str, Any]]:
    """Get photo clusters for a comparable property from comparable_photo_clusters table."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/comparable_photo_clusters",
        params={
            "comparable_id": f"eq.{comparable_id}",
            "select": "*",
        },
    )
    
    if response.status_code != 200:
        return []
    
    return response.json()


async def save_comparable_clusters(
    comparable_id: int,
    clusters: List[Dict[str, Any]]
) -> bool:
    """Save photo clusters for a comparable property."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Delete existing clusters for this comparable
    await client.delete(
        f"{base_url}/comparable_photo_clusters",
        params={"comparable_id": f"eq.{comparable_id}"},
    )
    
    # Insert new clusters
    for cluster in clusters:
        cluster_name = cluster.get("cluster_name", "") or cluster.get("room_name", "")
        data = {
            "comparable_id": comparable_id,
            "cluster_id": cluster.get("cluster_id", "unknown"),
            "cluster_name": cluster_name,
            "room_name": cluster_name,  # Table has both columns
            "room_type": cluster.get("room_type", "unknown"),
            "photo_urls": cluster.get("photo_urls", []),
            "photo_count": len(cluster.get("photo_urls", [])),
            "is_real": cluster.get("is_real", True),
            "confidence": cluster.get("confidence", 0.9),
        }
        
        response = await client.post(
            f"{base_url}/comparable_photo_clusters",
            json=data,
        )
        
        if response.status_code not in (200, 201):
            logger.error(f"Failed to save comparable cluster: {response.text}")
            return False
    
    return True


async def update_listing_year(
    listing_id: int,
    year_built: int,
    year_source: str
) -> bool:
    """Update listing with construction year."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.patch(
        f"{base_url}/listings",
        params={"id": f"eq.{listing_id}"},
        json={
            "year_built": year_built,
            "year_source": year_source,
        },
    )
    
    return response.status_code in (200, 204)


async def save_pir(listing_id: int, pir: Dict[str, Any]) -> bool:
    """
    Save Property Intelligence Report (V0.4.8).
    
    Handles both old format (year_context) and new format (building_profile).
    Extracts key metadata for indexed columns.
    """
    client = await get_client()
    base_url = _get_base_url()
    
    pir_type = pir.get("type", "target")
    
    # Extract room_count (either from explicit field or rooms array)
    room_count = pir.get("room_count", 0)
    if room_count == 0 and "rooms" in pir:
        room_count = len(pir.get("rooms", []))
    
    # Extract year_built (check both old and new formats)
    year_built = None
    year_source = None
    
    # New format: building_profile.year_built
    if "building_profile" in pir:
        bp = pir["building_profile"]
        year_built = bp.get("year_built")
        year_source = bp.get("year_source")
    
    # Old format fallback: year_context.year_built
    if year_built is None and "year_context" in pir:
        yc = pir["year_context"]
        year_built = yc.get("year_built")
        year_source = yc.get("year_source")
    
    # Determine model version from metadata
    metadata = pir.get("_metadata", {})
    model_version = metadata.get("version", "V0.4.8")
    if "v0.5" in model_version.lower():
        model_version = "V0.5"
    
    # Upsert (delete existing + insert)
    data = {
        "listing_id": listing_id,
        "pir_type": pir_type,
        "pir_data": pir,
        "room_count": room_count,
        "year_built": year_built,
        "year_source": year_source,
        "model_version": model_version,
    }
    
    # Delete existing
    await client.delete(
        f"{base_url}/property_intelligence_reports",
        params={
            "listing_id": f"eq.{listing_id}",
            "pir_type": f"eq.{pir_type}",
        },
    )
    
    # Insert new
    response = await client.post(
        f"{base_url}/property_intelligence_reports",
        json=data,
    )
    
    success = response.status_code in (200, 201)
    if success:
        logger.info(f"  ✓ Saved {model_version} PIR for listing {listing_id} (type: {pir_type})")
    else:
        logger.error(f"  ✗ Failed to save PIR for listing {listing_id}: {response.status_code}")
    
    return success


async def get_pir(listing_id: int, pir_type: str = "target") -> Optional[Dict[str, Any]]:
    """Get Property Intelligence Report (V0.4.8)."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/property_intelligence_reports",
        params={
            "listing_id": f"eq.{listing_id}",
            "pir_type": f"eq.{pir_type}",
            "select": "pir_data",
        },
    )
    
    if response.status_code != 200:
        return None
    
    rows = response.json()
    if rows:
        return rows[0].get("pir_data")
    
    return None


async def get_pir_row(listing_id: int, pir_type: str = "target") -> Optional[Dict[str, Any]]:
    """
    Get Property Intelligence Report row (pir_data + metadata columns).

    WHY THIS MATTERS: v3 is panorama-first and we need to detect stale legacy PIRs
    (e.g. model_version=V0.4.8) and regenerate them once prerequisites are present.
    """
    client = await get_client()
    base_url = _get_base_url()

    response = await client.get(
        f"{base_url}/property_intelligence_reports",
        params={
            "listing_id": f"eq.{listing_id}",
            "pir_type": f"eq.{pir_type}",
            "select": "pir_data,model_version,generated_at",
        },
    )
    if response.status_code != 200:
        return None

    rows = response.json()
    if not rows:
        return None

    row = rows[0] or {}
    return {
        "pir_data": row.get("pir_data"),
        "model_version": row.get("model_version"),
        "generated_at": row.get("generated_at"),
    }


# =============================================================================
# V0.5: BRACKET PIR PERSISTENCE
# =============================================================================

async def save_bracket_pir(
    listing_id: int,
    bracket_name: str,
    bracket_pir: Dict[str, Any]
) -> bool:
    """
    Save bracket PIR to database (V0.5).
    
    Bracket PIRs are synthesized from comparable PIRs and represent what
    properties in a specific price bracket "look and feel like."
    """
    client = await get_client()
    base_url = _get_base_url()
    
    # Upsert into bracket_pirs_v05 table
    # Using property_intelligence_reports table with pir_type="bracket_{bracket_name}"
    pir_type = f"bracket_{bracket_name}"
    
    # Delete existing
    await client.delete(
        f"{base_url}/property_intelligence_reports",
        params={
            "listing_id": f"eq.{listing_id}",
            "pir_type": f"eq.{pir_type}",
        },
    )
    
    # Insert new with V0.5 model version
    data = {
        "listing_id": listing_id,
        "pir_type": pir_type,
        "pir_data": bracket_pir,
        "model_version": "V0.5",  # Bracket PIRs are always V0.5
    }
    
    response = await client.post(
        f"{base_url}/property_intelligence_reports",
        json=data,
    )
    
    success = response.status_code in (200, 201)
    if success:
        logger.info(f"  💾 Saved V0.5 bracket PIR: {bracket_name} for listing {listing_id}")
    else:
        logger.error(f"  ✗ Failed to save bracket PIR: {response.status_code} {response.text}")
    
    return success


async def get_bracket_pir(
    listing_id: int,
    bracket_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get bracket PIR from database (V0.5).
    """
    client = await get_client()
    base_url = _get_base_url()
    
    pir_type = f"bracket_{bracket_name}"
    
    response = await client.get(
        f"{base_url}/property_intelligence_reports",
        params={
            "listing_id": f"eq.{listing_id}",
            "pir_type": f"eq.{pir_type}",
            "select": "pir_data",
        },
    )
    
    if response.status_code != 200:
        return None
    
    rows = response.json()
    if rows:
        return rows[0].get("pir_data")
    
    return None


async def save_unified_estimate(
    listing_id: int,
    package_type: str,
    estimate: Dict[str, Any]
) -> bool:
    """
    Save unified estimate (V0.5 Schema Continuity).
    
    V0.5 changes:
    - Uses estimate.get("total_cost") directly (not nested in bill_of_quantities)
    - Adds v05_schema_continuity flag
    - Adds item_counts for validation tracking
    """
    client = await get_client()
    base_url = _get_base_url()
    
    # V0.5: Extract fields directly from unified estimate
    # (No longer nested in bill_of_quantities)
    is_v05 = estimate.get("v05_schema_continuity", False)
    
    if is_v05:
        # V0.5 Schema Continuity format
        total_cost = estimate.get("total_cost", 0)
        room_count = len(estimate.get("cost_by_room", {}))
        line_item_count = estimate.get("line_items_count", 0)
        item_counts = estimate.get("item_counts", {})
    else:
        # V0.4.8 legacy format (for backward compatibility during transition)
        boq = estimate.get("bill_of_quantities", {})
        validation = estimate.get("validation", {})
        total_cost = boq.get("grand_total", 0)
        room_count = validation.get("total_rooms", 0)
        line_item_count = validation.get("total_line_items", 0)
        item_counts = {}
    
    data = {
        "listing_id": listing_id,
        "package_type": package_type,
        "estimate_data": estimate,
        "total_cost": total_cost,
        "room_count": room_count,
        "line_item_count": line_item_count,
        # V0.5 fields
        "v05_schema_continuity": is_v05,
        "item_counts": item_counts if item_counts else None,
    }

    # Use direct table upsert via PostgREST to avoid function overload ambiguity
    # PostgREST upsert: POST with ?on_conflict=unique_constraint
    upsert_payload = {
        "listing_id": listing_id,
        "package_type": package_type,
        "estimate_data": data["estimate_data"],
        "total_cost": total_cost,
        "room_count": room_count,
        "line_item_count": line_item_count,
        "v05_schema_continuity": is_v05,
        "item_counts": item_counts if item_counts else None,
    }
    
    response = await client.post(
        f"{base_url}/unified_estimates?on_conflict=listing_id,package_type",
        json=upsert_payload,
        headers={**_get_headers(), "Prefer": "resolution=merge-duplicates"},
    )

    if response.status_code in (200, 201, 204):
        if package_type.startswith("v2_"):
            logger.info(f"  💾 Saved V2 data: {package_type} for listing {listing_id}")
        else:
            version = "V0.5" if is_v05 else "V0.4.8"
            logger.info(f"  💾 Saved {version} estimate: {package_type} for listing {listing_id}")
        return True

    logger.error(f"Failed to save {package_type}: {response.status_code} {response.text[:500]}")
    return False


async def get_unified_estimate(
    listing_id: int,
    package_type: str
) -> Optional[Dict[str, Any]]:
    """Get unified estimate (V0.5 compatible - handles both V0.4.8 and V0.5 formats)."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/unified_estimates",
        params={
            "listing_id": f"eq.{listing_id}",
            "package_type": f"eq.{package_type}",
            "select": "estimate_data",
        },
    )
    
    if response.status_code != 200:
        return None
    
    rows = response.json()
    if rows:
        return rows[0].get("estimate_data")
    
    return None


async def save_package_checkpoint(
    listing_id: int,
    checkpoint: str,
    status: str = "completed",
    error_message: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> bool:
    """
    Save package generation checkpoint (robust upsert).
    
    Status lifecycle:
    - in_progress: started_at is set
    - completed: completed_at is set
    - failed: completed_at is set + error_message
    """
    client = await get_client()
    base_url = _get_base_url()
    
    now = datetime.utcnow().isoformat()
    if status == "in_progress" and not started_at:
        started_at = now
    if status in ("completed", "failed") and not completed_at:
        completed_at = now
    
    data = {
        "listing_id": listing_id,
        "checkpoint": checkpoint,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "error_message": error_message,
    }
    
    response = await client.post(
        f"{base_url}/package_generation_progress",
        params={"on_conflict": "listing_id,checkpoint"},
        json=data,
        headers={"Prefer": "resolution=merge-duplicates"},
    )
    
    success = response.status_code in (200, 201)
    if not success:
        logger.warning(
            f"Failed to save checkpoint {checkpoint} ({status}): {response.status_code} {response.text[:200]}"
        )
    return success


async def start_package_checkpoint(listing_id: int, checkpoint: str) -> bool:
    """Mark checkpoint as in-progress with started_at timestamp."""
    return await save_package_checkpoint(
        listing_id=listing_id,
        checkpoint=checkpoint,
        status="in_progress",
    )


async def fail_package_checkpoint(listing_id: int, checkpoint: str, error_message: str) -> bool:
    """Mark checkpoint as failed with error message."""
    return await save_package_checkpoint(
        listing_id=listing_id,
        checkpoint=checkpoint,
        status="failed",
        error_message=error_message,
    )


async def get_package_checkpoints(listing_id: int) -> List[str]:
    """Get completed checkpoints for a listing."""
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/package_generation_progress",
        params={
            "listing_id": f"eq.{listing_id}",
            "status": "eq.completed",
            "select": "checkpoint",
            "order": "completed_at",
        },
    )
    
    if response.status_code != 200:
        return []
    
    rows = response.json()
    return [r["checkpoint"] for r in rows]


async def clear_pipeline_data(listing_id: int) -> bool:
    """Clear all V0.4.8 data for a listing (for clean re-runs)."""
    client = await get_client()
    base_url = _get_base_url()
    
    # Clear checkpoints
    await client.delete(
        f"{base_url}/package_generation_progress",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    # Clear estimates
    await client.delete(
        f"{base_url}/unified_estimates",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    # Clear PIRs
    await client.delete(
        f"{base_url}/property_intelligence_reports",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    # Clear clusters
    await client.delete(
        f"{base_url}/photo_clusters",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    logger.info(f"Cleared V0.4.8 data for listing {listing_id}")
    return True


## Viewing guide (20-minute checklist) removed.


# =============================================================================
# SMART M² FUNCTIONS
# =============================================================================

async def save_smart_m2(
    listing_id: int,
    rooms: List[Dict[str, Any]],
    circulation_and_walls_m2: float = 0,
    total_check: float = 0,
    model_used: str = "gemini-2.5-pro",
) -> bool:
    """
    Save Smart M² room dimension estimates.
    
    Args:
        listing_id: The listing ID
        rooms: List of room dicts with estimated_m2, dimensions, wall_descriptions
        circulation_and_walls_m2: Area allocated to circulation/walls
        total_check: Validation check of total m²
        model_used: Model used for estimation
    
    Returns:
        True if saved successfully
    """
    client = await get_client()
    base_url = _get_base_url()
    
    data = {
        "listing_id": listing_id,
        "rooms": rooms,
        "circulation_and_walls_m2": circulation_and_walls_m2,
        "total_check": total_check,
        "model_used": model_used,
        "updated_at": "now()",
    }
    
    # Upsert: delete existing and insert new
    await client.delete(
        f"{base_url}/smart_m2",
        params={"listing_id": f"eq.{listing_id}"},
    )
    
    response = await client.post(
        f"{base_url}/smart_m2",
        json=data,
    )
    
    success = response.status_code in (200, 201)
    if success:
        logger.info(f"  ✓ Saved Smart M² for listing {listing_id} ({len(rooms)} rooms)")
    else:
        logger.error(f"  ✗ Failed to save Smart M² for listing {listing_id}: {response.status_code}")
    
    return success


async def get_smart_m2(listing_id: int) -> Optional[Dict[str, Any]]:
    """
    Get Smart M² data for a listing.
    
    Returns dict with:
        - rooms: List of room dimension estimates
        - circulation_and_walls_m2: Area for circulation
        - total_check: Total m² validation
    """
    client = await get_client()
    base_url = _get_base_url()
    
    response = await client.get(
        f"{base_url}/smart_m2",
        params={
            "listing_id": f"eq.{listing_id}",
            "select": "rooms,circulation_and_walls_m2,total_check,model_used",
        },
    )
    
    if response.status_code != 200:
        return None
    
    rows = response.json()
    if rows:
        return rows[0]
    
    return None


# =============================================================================
# V2 METHODS: Strategy Selection + Delta Scopes
# =============================================================================

async def save_v2_strategy_selection(
    listing_id: int,
    selection: Dict[str, Any]
) -> bool:
    """Save V2 strategy selection using unified_estimates table."""
    return await save_unified_estimate(listing_id, "v2_strategy_selection", selection)


async def get_v2_strategy_selection(listing_id: int) -> Optional[Dict[str, Any]]:
    """Get V2 strategy selection result."""
    return await get_unified_estimate(listing_id, "v2_strategy_selection")


async def save_v2_delta_scopes(
    listing_id: int,
    strategy_name: str,
    delta_scopes: Dict[str, Any]
) -> bool:
    """Save V2 delta scopes for a strategy using unified_estimates table."""
    return await save_unified_estimate(listing_id, f"v2_delta_{strategy_name}", delta_scopes)


async def get_v2_delta_scopes(
    listing_id: int,
    strategy_name: str
) -> Optional[Dict[str, Any]]:
    """Get V2 delta scopes for a strategy."""
    return await get_unified_estimate(listing_id, f"v2_delta_{strategy_name}")


async def save_v2_boq(
    listing_id: int,
    strategy_name: str,
    boq: Dict[str, Any]
) -> bool:
    """
    Save V2 BOQ for a strategy.
    
    Uses unified_estimates_v1 table with package_type prefixed by 'v2_'.
    """
    return await save_unified_estimate(listing_id, f"v2_{strategy_name}", boq)


async def get_v2_boq(
    listing_id: int,
    strategy_name: str
) -> Optional[Dict[str, Any]]:
    """Get V2 BOQ for a strategy."""
    return await get_unified_estimate(listing_id, f"v2_{strategy_name}")


# =============================================================================
# BOQ LINE ITEMS (Per-Scope-Item Incremental Saves)
# =============================================================================

async def save_boq_line_item(
    listing_id: int,
    strategy_name: str,
    dimension: str,
    room_name: str,
    item_data: Dict[str, Any]
) -> bool:
    """
    Save a single BOQ line item to the boq_line_items table.
    Uses upsert to handle duplicates gracefully.
    """
    client = await get_client()
    base_url = _get_base_url()
    
    row = {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "dimension": dimension,
        "room_name": room_name,
        "scope_item_element": item_data.get("scope_item_element") or item_data.get("scope_item"),
        "bcca_code": item_data.get("bcca_code"),
        "description": item_data.get("description"),
        "quantity": item_data.get("quantity") or item_data.get("qty"),
        "unit": item_data.get("unit"),
        "unit_price": item_data.get("unit_price"),
        "line_total": item_data.get("line_total"),
        "labor_hours": item_data.get("labor_hours"),
        "quantity_reasoning": item_data.get("quantity_reasoning") or item_data.get("qty_reasoning"),
        "room_id": item_data.get("room_id"),
        "wall_id": item_data.get("wall_id"),
        "opening_id": item_data.get("opening_id"),
        "quantity_ref": item_data.get("quantity_ref"),
        "quantity_rule_id": item_data.get("quantity_rule_id"),
        "item_kind": item_data.get("item_kind"),
        "embedding_similarity": item_data.get("embedding_similarity"),
        "embedding_top_k": item_data.get("embedding_top_k"),
        "provenance": item_data.get("provenance"),
    }
    
    try:
        # Use upsert with on_conflict
        response = await client.post(
            f"{base_url}/boq_line_items",
            json=row,
            headers={
                **_get_headers(),
                "Prefer": "resolution=merge-duplicates,return=minimal"
            }
        )
        
        if response.status_code in (200, 201, 204):
            return True
        else:
            logger.warning(f"Failed to save BOQ line item: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving BOQ line item: {e}")
        return False


async def save_boq_line_items_batch(
    listing_id: int,
    strategy_name: str,
    dimension: str,
    room_name: str,
    items: List[Dict[str, Any]]
) -> int:
    """
    Save multiple BOQ line items in a single batch.
    Returns count of successfully saved items.
    """
    if not items:
        return 0
    
    client = await get_client()
    base_url = _get_base_url()
    
    # De-dupe within the batch on the table's UNIQUE constraint to avoid 409s
    # UNIQUE (listing_id, strategy_name, dimension, room_name, bcca_code, description)
    merged: dict[tuple, dict] = {}
    for item_data in items:
        row = {
            "listing_id": listing_id,
            "strategy_name": strategy_name,
            "dimension": dimension,
            "room_name": room_name,
            "scope_item_element": item_data.get("scope_item_element") or item_data.get("scope_item"),
            "bcca_code": item_data.get("bcca_code"),
            "description": item_data.get("description"),
            "quantity": item_data.get("quantity") or item_data.get("qty"),
            "unit": item_data.get("unit"),
            "unit_price": item_data.get("unit_price"),
            "line_total": item_data.get("line_total"),
            "labor_hours": item_data.get("labor_hours"),
            "quantity_reasoning": item_data.get("quantity_reasoning") or item_data.get("qty_reasoning"),
            "room_id": item_data.get("room_id"),
            "wall_id": item_data.get("wall_id"),
            "opening_id": item_data.get("opening_id"),
            "quantity_ref": item_data.get("quantity_ref"),
            "quantity_rule_id": item_data.get("quantity_rule_id"),
            "item_kind": item_data.get("item_kind"),
            "embedding_similarity": item_data.get("embedding_similarity"),
            "embedding_top_k": item_data.get("embedding_top_k"),
            "provenance": item_data.get("provenance"),
        }

        key = (
            row["listing_id"],
            row["strategy_name"],
            row["dimension"],
            row["room_name"],
            row.get("bcca_code"),
            row.get("description"),
        )

        existing = merged.get(key)
        if not existing:
            merged[key] = row
            continue

        # Merge duplicates by summing quantities/totals/hours.
        # WHY: duplicates can be produced by the LLM across multiple scope items, and we want idempotent writes.
        try:
            existing_qty = float(existing.get("quantity") or 0)
            row_qty = float(row.get("quantity") or 0)
            existing_total = float(existing.get("line_total") or 0)
            row_total = float(row.get("line_total") or 0)
            existing_hours = float(existing.get("labor_hours") or 0)
            row_hours = float(row.get("labor_hours") or 0)
        except Exception:
            existing_qty = existing.get("quantity") or 0
            row_qty = row.get("quantity") or 0
            existing_total = existing.get("line_total") or 0
            row_total = row.get("line_total") or 0
            existing_hours = existing.get("labor_hours") or 0
            row_hours = row.get("labor_hours") or 0

        existing["quantity"] = existing_qty + row_qty
        existing["line_total"] = existing_total + row_total
        existing["labor_hours"] = existing_hours + row_hours

        # Keep a representative unit/unit_price (prefer existing). If they conflict, log once.
        if existing.get("unit") and row.get("unit") and existing.get("unit") != row.get("unit"):
            logger.warning(
                f"BOQ batch merge has mismatched unit | listing_id={listing_id} | strategy={strategy_name} | dim={dimension} | room={room_name} | code={row.get('bcca_code')} | unit_existing={existing.get('unit')} unit_new={row.get('unit')}"
            )
        if existing.get("unit_price") is None and row.get("unit_price") is not None:
            existing["unit_price"] = row.get("unit_price")

        # Append reasoning for traceability
        r1 = (existing.get("quantity_reasoning") or "").strip()
        r2 = (row.get("quantity_reasoning") or "").strip()
        if r2 and r2 not in r1:
            existing["quantity_reasoning"] = (r1 + ("\n\n" if r1 else "") + r2)[:4000]

    rows = list(merged.values())
    
    try:
        response = await client.post(
            f"{base_url}/rpc/boq_line_items_upsert",
            json={"rows": rows},
            headers=_get_headers(),
        )

        if response.status_code == 200:
            try:
                return int(response.json())
            except Exception:
                return len(rows)
        error_msg = f"Batch save failed: {response.status_code} - {response.text[:500]}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
            
    except Exception as e:
        logger.exception(f"Error batch saving BOQ line items: {e}")
        raise


async def get_boq_line_items(
    listing_id: int,
    strategy_name: str,
    dimension: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all BOQ line items for a listing/strategy.
    Optionally filter by dimension.
    """
    client = await get_client()
    base_url = _get_base_url()
    
    url = f"{base_url}/boq_line_items?listing_id=eq.{listing_id}&strategy_name=eq.{strategy_name}"
    if dimension:
        url += f"&dimension=eq.{dimension}"
    url += "&order=dimension,room_name,id"
    
    try:
        response = await client.get(url, headers=_get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get BOQ line items: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting BOQ line items: {e}")
        return []


async def clear_boq_line_items(
    listing_id: int,
    strategy_name: Optional[str] = None
) -> bool:
    """
    Clear BOQ line items for a listing.
    If strategy_name is provided, only clear that strategy.
    """
    client = await get_client()
    base_url = _get_base_url()
    
    url = f"{base_url}/boq_line_items?listing_id=eq.{listing_id}"
    if strategy_name:
        url += f"&strategy_name=eq.{strategy_name}"
    
    try:
        response = await client.delete(url, headers=_get_headers())
        
        if response.status_code in (200, 204):
            logger.info(f"Cleared BOQ line items for listing {listing_id}" + 
                       (f" strategy {strategy_name}" if strategy_name else ""))
            return True
        else:
            logger.warning(f"Failed to clear BOQ line items: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error clearing BOQ line items: {e}")
        return False


async def clear_boq_line_items_by_dimension(
    listing_id: int,
    *,
    strategy_name: Optional[str] = None,
    dimension: Optional[str] = None,
) -> bool:
    """
    Clear BOQ line items for a listing, optionally filtered by strategy and/or dimension.

    WHY THIS MATTERS: V4 writes BOQ line items with dimension="v4". We need to clear V4 without
    deleting V3 outputs (dimension="v3").
    """
    client = await get_client()
    base_url = _get_base_url()

    url = f"{base_url}/boq_line_items?listing_id=eq.{listing_id}"
    if strategy_name:
        url += f"&strategy_name=eq.{strategy_name}"
    if dimension:
        url += f"&dimension=eq.{dimension}"

    try:
        response = await client.delete(url, headers=_get_headers())
        if response.status_code in (200, 204):
            logger.info(
                "Cleared BOQ line items | listing_id=%s%s%s",
                listing_id,
                f" | strategy={strategy_name}" if strategy_name else "",
                f" | dimension={dimension}" if dimension else "",
            )
            return True
        logger.warning(f"Failed to clear BOQ line items: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Error clearing BOQ line items: {e}")
        return False


async def count_boq_line_items(
    listing_id: int,
    strategy_name: str
) -> int:
    """Count BOQ line items for a listing/strategy."""
    client = await get_client()
    base_url = _get_base_url()
    
    url = f"{base_url}/boq_line_items?listing_id=eq.{listing_id}&strategy_name=eq.{strategy_name}&select=id"
    
    try:
        response = await client.get(
            url,
            headers={
                **_get_headers(),
                "Prefer": "count=exact"
            }
        )
        
        if response.status_code == 200:
            # Count is in Content-Range header
            content_range = response.headers.get("Content-Range", "")
            if "/" in content_range:
                return int(content_range.split("/")[1])
            return len(response.json())
        return 0
        
    except Exception as e:
        logger.error(f"Error counting BOQ line items: {e}")
        return 0


async def count_boq_line_items_by_dimension(
    listing_id: int,
    strategy_name: str,
    *,
    dimension: Optional[str] = None,
) -> int:
    """Count BOQ line items for a listing/strategy, optionally filtered by dimension."""
    client = await get_client()
    base_url = _get_base_url()

    url = f"{base_url}/boq_line_items?listing_id=eq.{listing_id}&strategy_name=eq.{strategy_name}&select=id"
    if dimension:
        url += f"&dimension=eq.{dimension}"

    try:
        response = await client.get(
            url,
            headers={
                **_get_headers(),
                "Prefer": "count=exact",
            },
        )
        if response.status_code == 200:
            content_range = response.headers.get("Content-Range", "")
            if "/" in content_range:
                return int(content_range.split("/")[1])
            return len(response.json())
        return 0
    except Exception as e:
        logger.error(f"Error counting BOQ line items: {e}")
        return 0


# =============================================================================
# PIPELINE COST TRACKING
# =============================================================================

async def create_cost_tracking_run(
    listing_id: int,
    run_id: str,
) -> bool:
    """Create a new cost tracking run record."""
    client = await get_client()
    base_url = _get_base_url()
    
    row = {
        "listing_id": listing_id,
        "run_id": run_id,
        "run_started_at": "now()",
        "status": "running",
        "total_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost_regular": 0,
        "total_cost_cached": 0,
        "by_stage": {},
        "by_model": {},
    }
    
    try:
        response = await client.post(
            f"{base_url}/pipeline_cost_tracking",
            json=row,
            headers=_get_headers()
        )
        
        if response.status_code in (200, 201):
            logger.info(f"Created cost tracking run: {run_id}")
            return True
        else:
            logger.warning(f"Failed to create cost tracking run: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating cost tracking run: {e}")
        return False


async def update_cost_tracking(
    listing_id: int,
    run_id: str,
    stage: str,
    stage_data: Dict[str, Any],
    model_data: Dict[str, Any],
    totals: Dict[str, Any],
) -> bool:
    """
    Update cost tracking with incremental data after a stage completes.
    
    Args:
        listing_id: Listing ID
        run_id: Unique run identifier
        stage: Current stage name
        stage_data: Cost data for this stage {input, output, calls, cost_regular, cost_cached}
        model_data: Updated model breakdown
        totals: Updated totals {calls, input_tokens, output_tokens, cost_regular, cost_cached}
    """
    client = await get_client()
    base_url = _get_base_url()
    
    # First, get current by_stage to merge with new data
    try:
        get_response = await client.get(
            f"{base_url}/pipeline_cost_tracking?listing_id=eq.{listing_id}&run_id=eq.{run_id}&select=by_stage",
            headers=_get_headers()
        )
        
        current_by_stage = {}
        if get_response.status_code == 200:
            rows = get_response.json()
            if rows:
                current_by_stage = rows[0].get("by_stage", {}) or {}
        
        # Merge stage data
        current_by_stage[stage] = stage_data
        
        # Update the record
        update_data = {
            "total_calls": totals.get("calls", 0),
            "total_input_tokens": totals.get("input_tokens", 0),
            "total_output_tokens": totals.get("output_tokens", 0),
            "total_cost_regular": round(totals.get("cost_regular", 0), 4),
            "total_cost_cached": round(totals.get("cost_cached", 0), 4),
            "by_stage": current_by_stage,
            "by_model": model_data,
            "last_stage": stage,
            "updated_at": "now()",
        }
        
        response = await client.patch(
            f"{base_url}/pipeline_cost_tracking?listing_id=eq.{listing_id}&run_id=eq.{run_id}",
            json=update_data,
            headers=_get_headers()
        )
        
        if response.status_code in (200, 204):
            return True
        else:
            logger.warning(f"Failed to update cost tracking: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating cost tracking: {e}")
        return False


async def complete_cost_tracking(
    listing_id: int,
    run_id: str,
    success: bool = True,
) -> bool:
    """Mark a cost tracking run as completed."""
    client = await get_client()
    base_url = _get_base_url()
    
    update_data = {
        "status": "completed" if success else "failed",
        "run_completed_at": "now()",
        "updated_at": "now()",
    }
    
    try:
        response = await client.patch(
            f"{base_url}/pipeline_cost_tracking?listing_id=eq.{listing_id}&run_id=eq.{run_id}",
            json=update_data,
            headers=_get_headers()
        )
        
        if response.status_code in (200, 204):
            logger.info(f"Completed cost tracking run: {run_id} (success={success})")
            return True
        else:
            logger.warning(f"Failed to complete cost tracking: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error completing cost tracking: {e}")
        return False


async def get_cost_tracking_runs(
    listing_id: int,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get recent cost tracking runs for a listing."""
    client = await get_client()
    base_url = _get_base_url()
    
    url = f"{base_url}/pipeline_cost_tracking?listing_id=eq.{listing_id}&order=created_at.desc&limit={limit}"
    
    try:
        response = await client.get(url, headers=_get_headers())
        
        if response.status_code == 200:
            return response.json()
        return []
        
    except Exception as e:
        logger.error(f"Error getting cost tracking runs: {e}")
        return []


# =============================================================================
# DATABASE CLASS WRAPPER (for V0.4.8)
# =============================================================================

class Database:
    """
    Database wrapper class for use in V0.4.8+ pipeline.
    
    Wraps the module-level functions for cleaner dependency injection.
    """
    
    @property
    def base_url(self) -> str:
        """Get base URL for REST API calls."""
        return _get_base_url()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for REST API calls."""
        return _get_headers()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for REST API calls."""
        return await get_client()

    async def reset_boq_client(self) -> None:
        """Reset the dedicated BOQ client after transient network issues."""
        await reset_boq_client()

    # Pipeline queue wrappers
    async def create_pipeline_run(self, run_id: str, listing_id: int, config: Optional[Dict[str, Any]] = None) -> bool:
        return await create_pipeline_run(run_id, listing_id, config)

    async def delete_pipeline_run(self, run_id: str) -> bool:
        return await delete_pipeline_run(run_id)

    async def get_latest_pipeline_run(self, listing_id: int) -> Optional[Dict[str, Any]]:
        return await get_latest_pipeline_run(listing_id)

    async def get_pipeline_job_counts(self, run_id: str) -> Dict[str, int]:
        return await get_pipeline_job_counts(run_id)

    async def refresh_pipeline_run_status(self, run_id: str) -> bool:
        return await refresh_pipeline_run_status(run_id)

    async def backfill_pipeline_run_statuses(self, limit: Optional[int] = None) -> int:
        return await backfill_pipeline_run_statuses(limit=limit)

    async def reap_stuck_pipeline_jobs(
        self,
        stale_seconds: int = 600,
        heartbeat_grace_seconds: int = 300,
        limit: int = 100,
    ) -> int:
        return await reap_stuck_pipeline_jobs(
            stale_seconds=stale_seconds,
            heartbeat_grace_seconds=heartbeat_grace_seconds,
            limit=limit,
        )

    async def get_pipeline_jobs_for_run(self, run_id: str, *, limit: int = 500) -> List[Dict[str, Any]]:
        return await get_pipeline_jobs_for_run(run_id, limit=limit)

    async def get_pipeline_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return await get_pipeline_job(job_id)

    async def enqueue_pipeline_job(
        self,
        run_id: str,
        listing_id: int,
        stage: str,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        available_at: Optional[str] = None,
        max_attempts: int = 5,
    ) -> Optional[str]:
        return await enqueue_pipeline_job(run_id, listing_id, stage, job_type, payload, idempotency_key, available_at, max_attempts)

    async def claim_pipeline_jobs(self, worker_id: str, limit: int = 10, lock_seconds: int = 300) -> List[Dict[str, Any]]:
        return await claim_pipeline_jobs(worker_id, limit, lock_seconds)

    async def ack_pipeline_job(self, job_id: str) -> bool:
        return await ack_pipeline_job(job_id)

    async def fail_pipeline_job(
        self,
        job_id: str,
        error: str,
        error_context: Optional[Dict[str, Any]] = None,
        retry_in_seconds: Optional[int] = None,
    ) -> bool:
        return await fail_pipeline_job(job_id, error, error_context, retry_in_seconds)

    async def requeue_pipeline_job(
        self,
        job_id: str,
        payload: Optional[Dict[str, Any]] = None,
        available_at: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        return await requeue_pipeline_job(job_id, payload=payload, available_at=available_at, reason=reason)

    async def add_pipeline_job_event(
        self,
        job_id: str,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return await add_pipeline_job_event(job_id, event_type, message, data)

    async def add_gemini_call_log_row(
        self,
        *,
        listing_id: int,
        run_id: str,
        stage: str,
        model: str,
        prompt_tokens: int,
        output_tokens: int,
        thinking_tokens: int,
        total_tokens: int,
        cost_regular: float,
        cost_cached: float,
        job_id: Optional[str] = None,
        job_type: Optional[str] = None,
        has_images: bool = False,
        pricing_tier: str = "standard",
        pricing_mode: str = "regular",
        usage_metadata: Optional[Dict[str, Any]] = None,
        request_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        return await add_gemini_call_log_row(
            listing_id=listing_id,
            run_id=run_id,
            stage=stage,
            model=model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            total_tokens=total_tokens,
            cost_regular=cost_regular,
            cost_cached=cost_cached,
            job_id=job_id,
            job_type=job_type,
            has_images=has_images,
            pricing_tier=pricing_tier,
            pricing_mode=pricing_mode,
            usage_metadata=usage_metadata,
            request_meta=request_meta,
        )

    async def get_latest_pipeline_job_event(self, run_id: str) -> Optional[Dict[str, Any]]:
        return await get_latest_pipeline_job_event(run_id)

    async def get_pipeline_job_events_for_run(
        self,
        run_id: str,
        *,
        limit: int = 500,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await get_pipeline_job_events_for_run(run_id, limit=limit, event_type=event_type)

    async def extend_pipeline_job_lock(self, job_id: str, worker_id: str, lock_seconds: int = 60) -> bool:
        return await extend_pipeline_job_lock(job_id, worker_id, lock_seconds)
    
    async def get_listing(self, listing_id: int) -> Optional[Dict[str, Any]]:
        return await get_listing(listing_id)
    
    async def get_listing_photos(self, listing_id: int) -> List[str]:
        return await get_listing_photos(listing_id)
    
    async def get_listing_comparables(self, listing_id: int) -> List[Dict[str, Any]]:
        return await get_listing_comparables(listing_id)

    async def get_listing_market_stats(self, listing_id: int) -> Optional[Dict[str, Any]]:
        return await get_listing_market_stats(listing_id)

    async def get_pir_row(self, listing_id: int, pir_type: str = "target") -> Optional[Dict[str, Any]]:
        return await get_pir_row(listing_id, pir_type=pir_type)

    async def save_listing_market_stats(
        self,
        listing_id: int,
        stats: Dict[str, Any],
        search_params: Optional[Dict[str, Any]] = None,
        raw_casafari_response: Optional[Dict[str, Any]] = None,
        raw_filtered_comparables: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        return await save_listing_market_stats(
            listing_id,
            stats,
            search_params,
            raw_casafari_response,
            raw_filtered_comparables,
        )

    async def replace_listing_comparables(self, listing_id: int, rows: List[Dict[str, Any]]) -> bool:
        return await replace_listing_comparables(listing_id, rows)
    
    async def save_photo_clusters(self, listing_id: int, clusters: List[Dict], **kwargs) -> bool:
        return await save_photo_clusters(listing_id, clusters, **kwargs)
    
    async def get_photo_clusters(self, listing_id: int) -> List[Dict[str, Any]]:
        return await get_photo_clusters(listing_id)
    
    async def get_comparable_clusters(self, comparable_id: int) -> List[Dict[str, Any]]:
        return await get_comparable_clusters(comparable_id)
    
    async def save_comparable_clusters(self, comparable_id: int, clusters: List[Dict]) -> bool:
        return await save_comparable_clusters(comparable_id, clusters)
    
    async def update_listing_year(self, listing_id: int, year: int, source: str) -> bool:
        return await update_listing_year(listing_id, year, source)
    
    async def save_pir(self, listing_id: int, pir: Dict[str, Any]) -> bool:
        return await save_pir(listing_id, pir)
    
    async def get_pir(self, listing_id: int, pir_type: str = "target") -> Optional[Dict[str, Any]]:
        return await get_pir(listing_id, pir_type)
    
    # V0.5: Bracket PIR methods
    async def save_bracket_pir(self, listing_id: int, bracket_name: str, bracket_pir: Dict) -> bool:
        return await save_bracket_pir(listing_id, bracket_name, bracket_pir)
    
    async def get_bracket_pir(self, listing_id: int, bracket_name: str) -> Optional[Dict]:
        return await get_bracket_pir(listing_id, bracket_name)
    
    async def save_unified_estimate(self, listing_id: int, package_type: str, estimate: Dict) -> bool:
        return await save_unified_estimate(listing_id, package_type, estimate)
    
    async def get_unified_estimate(self, listing_id: int, package_type: str) -> Optional[Dict]:
        return await get_unified_estimate(listing_id, package_type)
    
    async def save_package_checkpoint(self, listing_id: int, checkpoint: str, timestamp: str) -> bool:
        return await save_package_checkpoint(listing_id, checkpoint, status="completed", completed_at=timestamp)

    async def start_package_checkpoint(self, listing_id: int, checkpoint: str) -> bool:
        return await start_package_checkpoint(listing_id, checkpoint)

    async def fail_package_checkpoint(self, listing_id: int, checkpoint: str, error_message: str) -> bool:
        return await fail_package_checkpoint(listing_id, checkpoint, error_message)
    
    async def get_package_checkpoints(self, listing_id: int) -> List[str]:
        return await get_package_checkpoints(listing_id)
    
    # Smart M² methods
    async def save_smart_m2(
        self,
        listing_id: int,
        rooms: List[Dict],
        circulation_and_walls_m2: float = 0,
        total_check: float = 0,
        model_used: str = "gemini-2.5-pro",
    ) -> bool:
        return await save_smart_m2(listing_id, rooms, circulation_and_walls_m2, total_check, model_used)
    
    async def get_smart_m2(self, listing_id: int) -> Optional[Dict[str, Any]]:
        return await get_smart_m2(listing_id)
    
    async def clear_pipeline_data(self, listing_id: int) -> bool:
        return await clear_pipeline_data(listing_id)
    
    async def upload_rendered_image(
        self,
        listing_id: int,
        package_type: str,
        room_name: str,
        image_data: bytes,
        file_extension: str = "png"
    ) -> Optional[str]:
        """
        Upload AI-rendered image to Supabase storage.
        
        Args:
            listing_id: The listing ID
            package_type: fast_sell, fair_market, out_of_market
            room_name: Room identifier (e.g., "kitchen", "hero")
            image_data: Raw image bytes
            file_extension: File extension (png, jpg)
        
        Returns:
            Public URL of uploaded image, or None on failure
        """
        bucket = "rendered-images"
        filename = f"listing-{listing_id}/{package_type}/{room_name}.{file_extension}"
        
        # Supabase storage URL
        storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{filename}"
        
        # Content type based on extension
        content_type = "image/png" if file_extension == "png" else "image/jpeg"
        
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": content_type,
            "x-upsert": "true",  # Overwrite if exists
        }
        
        try:
            async with httpx.AsyncClient(timeout=300) as client:  # 5 minutes
                response = await client.post(
                    storage_url,
                    content=image_data,
                    headers=headers,
                )
                
                if response.status_code in (200, 201):
                    # Return public URL
                    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}"
                    logger.info(f"✓ Uploaded rendered image: {public_url}")
                    return public_url
                else:
                    logger.error(f"Failed to upload rendered image: {response.status_code} {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error uploading rendered image: {e}")
            return None
    
    # Viewing guide removed.
    
    # =========================================================================
    # V2 METHODS: Strategy Selection + Delta Scopes
    # =========================================================================
    
    async def save_v2_strategy_selection(
        self, 
        listing_id: int, 
        selection: Dict[str, Any]
    ) -> bool:
        """Save V2 strategy selection result."""
        return await save_v2_strategy_selection(listing_id, selection)
    
    async def get_v2_strategy_selection(
        self, 
        listing_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get V2 strategy selection result."""
        return await get_v2_strategy_selection(listing_id)
    
    async def save_v2_delta_scopes(
        self,
        listing_id: int,
        strategy_name: str,
        delta_scopes: Dict[str, Any]
    ) -> bool:
        """Save V2 delta scopes for a strategy."""
        return await save_v2_delta_scopes(listing_id, strategy_name, delta_scopes)
    
    async def get_v2_delta_scopes(
        self,
        listing_id: int,
        strategy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get V2 delta scopes for a strategy."""
        return await get_v2_delta_scopes(listing_id, strategy_name)
    
    async def save_v2_boq(
        self,
        listing_id: int,
        strategy_name: str,
        boq: Dict[str, Any]
    ) -> bool:
        """Save V2 BOQ for a strategy."""
        return await save_v2_boq(listing_id, strategy_name, boq)
    
    async def get_v2_boq(
        self,
        listing_id: int,
        strategy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get V2 BOQ for a strategy."""
        return await get_v2_boq(listing_id, strategy_name)
    
    # BOQ Line Items (per-scope-item)
    
    async def save_boq_line_item(
        self,
        listing_id: int,
        strategy_name: str,
        dimension: str,
        room_name: str,
        item_data: Dict[str, Any]
    ) -> bool:
        """Save a single BOQ line item."""
        return await save_boq_line_item(listing_id, strategy_name, dimension, room_name, item_data)
    
    async def save_boq_line_items_batch(
        self,
        listing_id: int,
        strategy_name: str,
        dimension: str,
        room_name: str,
        items: List[Dict[str, Any]]
    ) -> int:
        """Save multiple BOQ line items in a batch."""
        return await save_boq_line_items_batch(listing_id, strategy_name, dimension, room_name, items)
    
    async def get_boq_line_items(
        self,
        listing_id: int,
        strategy_name: str,
        dimension: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get BOQ line items for a listing/strategy."""
        return await get_boq_line_items(listing_id, strategy_name, dimension)
    
    async def clear_boq_line_items(
        self,
        listing_id: int,
        strategy_name: Optional[str] = None
    ) -> bool:
        """Clear BOQ line items."""
        return await clear_boq_line_items(listing_id, strategy_name)

    async def clear_boq_line_items_by_dimension(
        self,
        listing_id: int,
        *,
        strategy_name: Optional[str] = None,
        dimension: Optional[str] = None,
    ) -> bool:
        """Clear BOQ line items, optionally filtered by strategy and/or dimension."""
        return await clear_boq_line_items_by_dimension(
            listing_id,
            strategy_name=strategy_name,
            dimension=dimension,
        )
    
    async def count_boq_line_items(
        self,
        listing_id: int,
        strategy_name: str
    ) -> int:
        """Count BOQ line items."""
        return await count_boq_line_items(listing_id, strategy_name)

    async def count_boq_line_items_by_dimension(
        self,
        listing_id: int,
        strategy_name: str,
        *,
        dimension: Optional[str] = None,
    ) -> int:
        """Count BOQ line items, optionally filtered by dimension."""
        return await count_boq_line_items_by_dimension(
            listing_id,
            strategy_name,
            dimension=dimension,
        )
    
    # Cost Tracking
    
    async def create_cost_tracking_run(
        self,
        listing_id: int,
        run_id: str,
    ) -> bool:
        """Create a new cost tracking run."""
        return await create_cost_tracking_run(listing_id, run_id)
    
    async def update_cost_tracking(
        self,
        listing_id: int,
        run_id: str,
        stage: str,
        stage_data: Dict[str, Any],
        model_data: Dict[str, Any],
        totals: Dict[str, Any],
    ) -> bool:
        """Update cost tracking with stage data."""
        return await update_cost_tracking(listing_id, run_id, stage, stage_data, model_data, totals)
    
    async def complete_cost_tracking(
        self,
        listing_id: int,
        run_id: str,
        success: bool = True,
    ) -> bool:
        """Mark cost tracking run as complete."""
        return await complete_cost_tracking(listing_id, run_id, success)
    
    async def get_cost_tracking_runs(
        self,
        listing_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent cost tracking runs."""
        return await get_cost_tracking_runs(listing_id, limit)