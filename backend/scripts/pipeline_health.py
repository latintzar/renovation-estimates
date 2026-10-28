#!/usr/bin/env python3
"""
Pipeline Health Check - proactive visibility for stuck pipelines.

This script answers:
1) Are any jobs stuck? (in_progress with expired locks, or running too long)
2) Are runs stale? (started long ago with pending jobs)
3) What is throughput in the last hour?

EXIT CODES:
  0 = healthy
  1 = WARNING (needs attention)
  2 = CRITICAL (pipeline likely stuck)
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_supabase_key, get_supabase_url

# Thresholds
MAX_JOB_DURATION_HOURS = 2  # Any single job > 2h is suspicious
MAX_RUN_AGE_HOURS = 6       # A run > 6h old with incomplete jobs is stuck
ZOMBIE_LOCK_MINUTES = 30    # Lock expired > 30 min ago but still in_progress
MAX_RUNS_TO_CHECK = 50      # Prevent a full-table fanout in large queues

logger = logging.getLogger("pipeline_health")


def _get_headers() -> Dict[str, str]:
    key = get_supabase_key()
    if not key:
        raise RuntimeError("SUPABASE key missing (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY)")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "count=exact",
    }


def _get_base_url() -> str:
    url = get_supabase_url()
    if not url:
        raise RuntimeError("SUPABASE_URL missing")
    return f"{url}/rest/v1"


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    expected: Tuple[int, ...] = (200,),
) -> Any:
    url = f"{_get_base_url()}/{path.lstrip('/')}"
    response = client.request(method, url, params=params, json=json_body, headers=_get_headers())
    if response.status_code not in expected:
        raise RuntimeError(
            f"Supabase request failed | {method} {url} | status={response.status_code} | body={response.text[:500]}"
        )
    if response.text.strip() == "":
        return []
    return response.json()


def _request_count(client: httpx.Client, path: str, params: Dict[str, str]) -> int:
    url = f"{_get_base_url()}/{path.lstrip('/')}"
    response = client.get(url, params=params, headers=_get_headers())
    if response.status_code not in (200, 206):
        raise RuntimeError(f"Count request failed | {url} | status={response.status_code} | body={response.text[:300]}")
    content_range = response.headers.get("content-range") or response.headers.get("Content-Range", "*/0")
    try:
        return int(content_range.split("/")[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"Invalid Content-Range header: {content_range}") from exc


def _get_run_job_counts(client: httpx.Client, run_id: str) -> Dict[str, int]:
    rows = _request_json(
        client,
        "POST",
        "rpc/pipeline_job_counts",
        json_body={"p_run_id": run_id},
        expected=(200,),
    )
    out = {"queued": 0, "in_progress": 0, "failed": 0, "succeeded": 0, "completed": 0}
    for row in rows or []:
        status = str(row.get("status"))
        count = int(row.get("count") or 0)
        out[status] = count
    return out


def check_health() -> int:
    now = datetime.now(timezone.utc)
    issues: List[str] = []
    warnings: List[str] = []

    logger.info("============================================================")
    logger.info("PIPELINE HEALTH CHECK | %s", now.isoformat())
    logger.info("============================================================")

    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        # 1) Zombie jobs: in_progress + lock expired
        zombies = _request_json(
            client,
            "GET",
            "pipeline_jobs",
            params={
                "select": "id,stage,job_type,run_id,locked_until,attempts",
                "status": "eq.in_progress",
                "locked_until": f"lt.{now.isoformat()}",
            },
        )
        for job in zombies or []:
            lock_expired = _parse_iso(job.get("locked_until"))
            if not lock_expired:
                continue
            minutes_expired = (now - lock_expired).total_seconds() / 60
            if minutes_expired > ZOMBIE_LOCK_MINUTES:
                issues.append(
                    f"🧟 ZOMBIE JOB: {job.get('stage')}/{job.get('job_type')} "
                    f"(id={str(job.get('id'))[:8]}...) "
                    f"lock expired {minutes_expired:.0f} min ago, attempts={job.get('attempts')}"
                )

        # 2) Long-running jobs: in_progress + created_at old
        in_progress = _request_json(
            client,
            "GET",
            "pipeline_jobs",
            params={
                "select": "id,stage,job_type,run_id,created_at,attempts",
                "status": "eq.in_progress",
            },
        )
        for job in in_progress or []:
            created_at = _parse_iso(job.get("created_at"))
            if not created_at:
                continue
            age_hours = (now - created_at).total_seconds() / 3600
            if age_hours > MAX_JOB_DURATION_HOURS:
                issues.append(
                    f"⏰ LONG-RUNNING: {job.get('stage')}/{job.get('job_type')} "
                    f"(id={str(job.get('id'))[:8]}...) "
                    f"running {age_hours:.1f}h, attempts={job.get('attempts')}"
                )

        # 3) Stale runs: runs with pending jobs, run age too old
        pending_jobs = _request_json(
            client,
            "GET",
            "pipeline_jobs",
            params={
                "select": "run_id",
                "status": "in.(queued,in_progress)",
                "limit": str(MAX_RUNS_TO_CHECK),
            },
        )
        run_ids = sorted({r.get("run_id") for r in pending_jobs or [] if r.get("run_id")})
        if len(run_ids) >= MAX_RUNS_TO_CHECK:
            warnings.append(f"⚠️ Large queue: checking first {MAX_RUNS_TO_CHECK} runs only")

        for run_id in run_ids:
            runs = _request_json(
                client,
                "GET",
                "pipeline_runs",
                params={"select": "run_id,listing_id,created_at", "run_id": f"eq.{run_id}"},
            )
            if not runs:
                continue
            run = runs[0]
            run_created = _parse_iso(run.get("created_at"))
            if not run_created:
                continue
            age_hours = (now - run_created).total_seconds() / 3600
            counts = _get_run_job_counts(client, run_id)
            pending = counts.get("queued", 0) + counts.get("in_progress", 0)
            completed = counts.get("completed", 0) + counts.get("succeeded", 0)
            failed = counts.get("failed", 0)
            if age_hours > MAX_RUN_AGE_HOURS:
                issues.append(
                    f"🐌 STALE RUN: listing={run.get('listing_id')} started {age_hours:.1f}h ago "
                    f"pending={pending} completed={completed} failed={failed}"
                )
            elif age_hours > 1:
                warnings.append(
                    f"⚠️ SLOW RUN: listing={run.get('listing_id')} started {age_hours:.1f}h ago "
                    f"pending={pending} completed={completed} failed={failed}"
                )

        # 4) Throughput (last hour)
        one_hour_ago = datetime.fromtimestamp(now.timestamp() - 3600, timezone.utc).isoformat()
        throughput_count = _request_count(
            client,
            "pipeline_jobs",
            {
                "select": "id",
                "status": "eq.completed",
                "updated_at": f"gte.{one_hour_ago}",
                "limit": "0",
            },
        )
        logger.info("📊 THROUGHPUT: %s jobs completed in last hour", throughput_count)

        # 5) Queue depth
        queued_count = _request_count(
            client,
            "pipeline_jobs",
            {"select": "id", "status": "eq.queued", "limit": "0"},
        )
        in_progress_count = _request_count(
            client,
            "pipeline_jobs",
            {"select": "id", "status": "eq.in_progress", "limit": "0"},
        )
        logger.info("📋 QUEUE: %s queued, %s in_progress", queued_count, in_progress_count)

    logger.info("------------------------------------------------------------")
    if issues:
        logger.error("CRITICAL ISSUES:")
        for issue in issues:
            logger.error("  %s", issue)
    if warnings:
        logger.warning("WARNINGS:")
        for warn in warnings:
            logger.warning("  %s", warn)
    if not issues and not warnings:
        logger.info("✅ ALL HEALTHY - no stuck jobs or stale runs detected")
    logger.info("============================================================")

    if issues:
        return 2
    if warnings:
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.
    sys.exit(check_health())
