#!/usr/bin/env python3
import argparse
import asyncio
import contextvars
import json
import logging
import os
import socket
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
_log_dir = os.getenv("PIPELINE_LOG_DIR", "/root/puedo_casa/lean-mvp/logs")
try:
    Path(_log_dir).mkdir(parents=True, exist_ok=True)
    _log_path = Path(_log_dir) / "pipeline_worker.log"
    _file_handler = logging.FileHandler(_log_path)
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logging.getLogger().addHandler(_file_handler)
except Exception:
    logging.getLogger(__name__).exception("Failed to set up file logging for pipeline worker")
logger = logging.getLogger("pipeline_worker")


class BlockedByPredecessor(RuntimeError):
    """
    Signal that a job was requeued because its direct predecessor is not done.

    WHY THIS MATTERS: the queue can contain all stages upfront; this guard enforces
    strict workflow ordering at execution time so downstream jobs do not run early.
    """

# =============================================================================
# JOB-SCOPED LOG STREAMING (DB)
# =============================================================================
#
# WHY THIS MATTERS:
# - Foreground stdout is not a reliable observability mechanism for long-running workers
#   (tool timeouts, restarts, multiple processes).
# - We want every step's logs (including httpx + subprocess wrapper logs) to be visible
#   via the pipeline itself, tied to run/job IDs, without special "how to run it" incantations.
#
# Design:
# - Each job gets a bounded in-memory queue of formatted log lines.
# - A per-job async task batches/drains lines into pipeline_job_events(event_type="log").
# - A global logging.Handler routes log records into the active job’s queue via contextvars.
#
# Cost control:
# - Batches multiple log lines into one DB write.
# - Flushes on a timer and on job completion.
#
_CTX_JOB_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pipeline_job_id", default=None)
_CTX_RUN_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pipeline_run_id", default=None)
_CTX_LISTING_ID: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("pipeline_listing_id", default=None)

_JOB_LOG_QUEUES: Dict[str, "asyncio.Queue[str]"] = {}
_JOB_LOG_TASKS: Dict[str, "asyncio.Task[None]"] = {}
_JOB_LAST_ACTIVITY_TS: Dict[str, float] = {}
_JOB_STALL_REASON: Dict[str, str] = {}
_JOB_CANCEL_REASON: Dict[str, str] = {}


class _PipelineDbLogHandler(logging.Handler):
    def __init__(self, formatter: logging.Formatter) -> None:
        super().__init__(level=logging.INFO)
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            job_id = _CTX_JOB_ID.get()
            if not job_id:
                return
            q = _JOB_LOG_QUEUES.get(job_id)
            if not q:
                return
            msg = self.format(record)
            try:
                q.put_nowait(msg)
                # Any emitted log line counts as "activity" for stall detection.
                _JOB_LAST_ACTIVITY_TS[str(job_id)] = time.monotonic()
            except asyncio.QueueFull:
                # Drop rather than blocking the worker.
                return
        except Exception:
            # Never crash the worker due to logging.
            return


async def _emit_progress_event(
    *,
    db: Any,
    job_id: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort "progress" events that show up alongside logs in pipeline_job_events.

    WHY THIS MATTERS:
    - Logs can be noisy; progress events are intentional and easier to scan.
    - We can distinguish "alive" (heartbeat) from "making progress" (progress markers).
    """
    try:
        await db.add_pipeline_job_event(job_id=str(job_id), event_type="progress", message=message, data=data or {})
    except Exception:
        # Best-effort only; progress events should never crash the worker.
        return


async def _stall_watchdog(
    *,
    db: Any,
    job_id: str,
    worker_id: str,
    run_id: Optional[str],
    listing_id: Optional[int],
    stage: Optional[str],
    job_type: Optional[str],
    stall_seconds: float,
    check_every_seconds: float,
    job_task: "asyncio.Task[None]",
) -> None:
    """
    Fail a job if it stops producing activity (logs/progress) for too long.

    IMPORTANT:
    - This is INTERNAL hang detection (not forbidden external polling).
    - The worker stays in the foreground; this just prevents silent hangs.
    """
    if stall_seconds <= 0:
        return
    try:
        while True:
            await asyncio.sleep(check_every_seconds)
            last = _JOB_LAST_ACTIVITY_TS.get(str(job_id), time.monotonic())
            idle_s = time.monotonic() - last
            if idle_s <= stall_seconds:
                continue

            reason = (
                f"STALL DETECTED: no activity for {idle_s:.1f}s (limit={stall_seconds:.1f}s) "
                f"| stage={stage} | job_type={job_type}"
            )
            _JOB_STALL_REASON[str(job_id)] = reason
            await _emit_progress_event(
                db=db,
                job_id=str(job_id),
                message=reason,
                data={
                    "run_id": run_id,
                    "listing_id": listing_id,
                    "stage": stage,
                    "job_type": job_type,
                    "worker_id": worker_id,
                    "stall_seconds": stall_seconds,
                    "idle_seconds": round(idle_s, 3),
                },
            )
            job_task.cancel()
            return
    except asyncio.CancelledError:
        return


async def _cancel_watchdog(
    *,
    db: Any,
    job_id: str,
    worker_id: str,
    run_id: Optional[str],
    listing_id: Optional[int],
    stage: Optional[str],
    job_type: Optional[str],
    check_every_seconds: float,
    job_task: "asyncio.Task[None]",
) -> None:
    """
    Cancel a running job if an admin marks it as cancelled.

    WHY THIS MATTERS:
    - Admin stop sets pipeline_jobs.status='cancelled' in the DB.
    - Without honoring that mid-flight, the worker will keep running and may overwrite
      the cancelled status by acking the job as succeeded.
    """
    try:
        while True:
            await asyncio.sleep(check_every_seconds)
            try:
                row = await db.get_pipeline_job(str(job_id))
            except Exception as exc:
                logger.warning(
                    "CancelWatchdog: exception reading job status | job_id=%s | %s: %s",
                    job_id,
                    type(exc).__name__,
                    exc,
                )
                continue
            status = str((row or {}).get("status") or "")
            if status != "cancelled":
                continue

            reason = f"STOP REQUESTED: job marked cancelled in DB | stage={stage} | job_type={job_type}"
            _JOB_CANCEL_REASON[str(job_id)] = reason
            await _emit_progress_event(
                db=db,
                job_id=str(job_id),
                message=reason,
                data={
                    "run_id": run_id,
                    "listing_id": listing_id,
                    "stage": stage,
                    "job_type": job_type,
                    "worker_id": worker_id,
                },
            )
            job_task.cancel()
            return
    except asyncio.CancelledError:
        return


async def _flush_job_logs_to_db(*, db: Any, job_id: str, max_lines: int = 80) -> int:
    q = _JOB_LOG_QUEUES.get(job_id)
    if not q:
        return 0

    lines: List[str] = []
    for _ in range(max_lines):
        if q.empty():
            break
        try:
            lines.append(q.get_nowait())
        except Exception:
            break

    if not lines:
        return 0

    run_id = _CTX_RUN_ID.get()
    listing_id = _CTX_LISTING_ID.get()
    message = "\n".join(lines)
    try:
        await db.add_pipeline_job_event(
            job_id=str(job_id),
            event_type="log",
            message=message,
            data={"run_id": run_id, "listing_id": listing_id, "source": "python-logger"},
        )
    except Exception:
        # Best-effort: logs should never take the pipeline down.
        logger.exception(f"Failed to flush job logs to DB | job_id={job_id}")
        return 0

    return len(lines)


async def _job_log_streamer(*, db: Any, job_id: str, flush_every_s: float = 1.25) -> None:
    try:
        while True:
            await asyncio.sleep(flush_every_s)
            await _flush_job_logs_to_db(db=db, job_id=job_id)
    except asyncio.CancelledError:
        return


# Attach DB log handler to the root logger so it captures logs from any module (httpx included).
_db_log_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logging.getLogger().addHandler(_PipelineDbLogHandler(_db_log_formatter))


JobHandler = Callable[[Dict[str, Any], Any], Awaitable[None]]


def _worker_id() -> str:
    host = socket.gethostname()
    pid = os.getpid()
    return f"{host}:{pid}"


async def _handle_noop(job: Dict[str, Any], db: Any) -> None:
    raise RuntimeError(f"No handler implemented for job_type={job.get('job_type')}")


async def _dispatch(job: Dict[str, Any], db: Any, handlers: Dict[str, JobHandler]) -> None:
    job_type = job.get("job_type")
    handler = handlers.get(job_type) or _handle_noop
    await handler(job, db)


async def _heartbeat_loop(db: Any, job_id: str, worker_id: str, every_seconds: float = 15.0, lock_seconds: int = 60) -> None:
    """
    Periodically renew the lock for long-running jobs and emit a heartbeat event.

    WHY THIS MATTERS: Without a heartbeat, a dead worker looks like a "hung job" until lock expiry,
    which is exactly the muddy behavior you’re seeing. This makes "still running" explicit and
    reduces time-to-reclaim if a worker dies.
    """
    try:
        while True:
            await asyncio.sleep(every_seconds)
            try:
                ok = await db.extend_pipeline_job_lock(job_id=job_id, worker_id=worker_id, lock_seconds=lock_seconds)
            except Exception as exc:
                logger.warning(f"Heartbeat: exception renewing lock | job_id={job_id} | {type(exc).__name__}: {exc}")
                continue
            if not ok:
                # Don't stop heartbeating on a transient failure; keep trying so long jobs
                # don't look dead and get reclaimed mid-flight.
                logger.warning(f"Heartbeat: failed to renew lock | job_id={job_id} | will_retry=true")
                continue
    except asyncio.CancelledError:
        # Expected during normal job completion/cleanup.
        return


async def _run_loop(
    db: Any,
    handlers: Dict[str, JobHandler],
    poll_seconds: float,
    limit: int,
    lock_seconds: int,
    max_inflight: int,
) -> int:
    from pipeline.v5_stages import V5_JOB_PREDECESSOR
    from pipeline.gla_stages import GLA_JOB_PREDECESSOR

    # Unified predecessor graph for strict linear execution within each pipeline.
    # Keys are distinct ("v5_*" vs "gla_*"), so merge is safe.
    JOB_PREDECESSOR: Dict[str, str] = {**V5_JOB_PREDECESSOR, **GLA_JOB_PREDECESSOR}
    # Optional debug escape hatch: exit worker after completing a specific job.
    # WHY THIS MATTERS: makes it easy to "run snapshot only" deterministically without
    # manual intervention or accidentally processing downstream jobs.
    exit_after_job_type = (os.getenv("PIPELINE_EXIT_AFTER_JOB_TYPE") or "").strip()
    exit_after_stage = (os.getenv("PIPELINE_EXIT_AFTER_STAGE") or "").strip()
    exit_event: "asyncio.Event" = asyncio.Event()

    def _iso_utc_after(seconds: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(seconds=max(0, int(seconds)))).isoformat()

    async def _block_if_predecessor_not_ready(job: Dict[str, Any]) -> None:
        """
        Requeue a job when its direct predecessor has not succeeded yet.

        This keeps execution order deterministic even when many jobs are pre-enqueued.
        """
        job_type = str(job.get("job_type") or "")
        predecessor = JOB_PREDECESSOR.get(job_type)
        if not predecessor:
            return

        run_id = str(job.get("run_id") or "")
        job_id = str(job.get("id") or "")
        if not run_id or not job_id:
            return

        jobs_for_run = await db.get_pipeline_jobs_for_run(run_id=run_id, limit=500)
        predecessor_status: Optional[str] = None
        for row in jobs_for_run:
            if str(row.get("job_type") or "") != predecessor:
                continue
            status = str(row.get("status") or "")
            if status == "succeeded":
                predecessor_status = "succeeded"
                break
            if predecessor_status is None:
                predecessor_status = status or None

        if predecessor_status == "succeeded":
            return

        # ── Predecessor FAILED or CANCELLED → fail this job immediately ──
        # WHY: if comparables fails (e.g. Casafari 402), there's no point
        # endlessly retrying clustering→PIR→delta→...→room_images every 20s.
        # That loop floods the DB with hundreds of useless events per minute.
        if predecessor_status in {"failed", "cancelled"}:
            reason = (
                f"{job_type}: predecessor {predecessor} has {predecessor_status} — "
                f"cannot proceed (clear & rerun to retry)"
            )
            raise RuntimeError(reason)

        # ── Predecessor still running or queued → reschedule with backoff ──
        delay_seconds = 20 if predecessor_status in {None, "", "queued", "in_progress"} else 120
        reason = (
            f"{job_type}: waiting for predecessor {predecessor} "
            f"(status={predecessor_status or 'missing'})"
        )
        ok = await db.requeue_pipeline_job(
            job_id=job_id,
            available_at=_iso_utc_after(delay_seconds),
            reason=reason,
        )
        if not ok:
            raise RuntimeError(
                f"failed to requeue blocked job | job_id={job_id} predecessor={predecessor} status={predecessor_status or 'missing'}"
            )
        raise BlockedByPredecessor(reason)

    wid = _worker_id()
    logger.info(f"Worker starting | worker_id={wid}")
    inflight = asyncio.Semaphore(max_inflight)
    stop_on_failure = os.getenv("PIPELINE_STOP_ON_FAILURE", "true").lower() == "true"
    # Hard watchdogs (fail loud vs "runs forever")
    # Default is intentionally conservative: we should never let panos run "all night" unnoticed.
    cluster_panos_timeout_s = float(os.getenv("PIPELINE_CLUSTER_PANOS_TIMEOUT_S", "3600"))  # 1h default
    default_job_timeout_s = float(os.getenv("PIPELINE_JOB_TIMEOUT_S", "0") or 0)
    # Stall watchdogs (fail if no activity/progress for too long)
    default_stall_s = float(os.getenv("PIPELINE_JOB_STALL_S", "300"))  # 5m
    cluster_panos_stall_s = float(os.getenv("PIPELINE_CLUSTER_PANOS_STALL_S", "600"))  # 10m
    stall_check_every_s = float(os.getenv("PIPELINE_STALL_CHECK_EVERY_S", "5"))  # low overhead

    async def _process_one(job: Dict[str, Any]) -> None:
        async with inflight:
            job_id = job.get("id")
            run_id = job.get("run_id")
            listing_id = job.get("listing_id")
            stage = job.get("stage")
            job_type = job.get("job_type")
            started_at = datetime.utcnow()
            logger.info(f"Job claimed | id={job_id} | run_id={run_id} | listing_id={listing_id} | stage={stage} | type={job_type}")

            # Set per-job logging context (used by DB log handler).
            _t_job = _CTX_JOB_ID.set(str(job_id) if job_id is not None else None)
            _t_run = _CTX_RUN_ID.set(run_id)
            _t_listing = _CTX_LISTING_ID.set(listing_id)

            # Start job log streamer (batches into pipeline_job_events).
            if job_id is not None:
                _JOB_LOG_QUEUES[str(job_id)] = asyncio.Queue(maxsize=int(os.getenv("PIPELINE_JOB_LOG_QUEUE_SIZE", "1500")))
                _JOB_LOG_TASKS[str(job_id)] = asyncio.create_task(_job_log_streamer(db=db, job_id=str(job_id)))
                _JOB_LAST_ACTIVITY_TS[str(job_id)] = time.monotonic()

            # Attach DB + job context so gemini_client persists usage events automatically.
            try:
                from pipeline.gemini_client import set_gemini_tracking_context

                set_gemini_tracking_context(
                    db=db,
                    job_ctx={
                        "job_id": str(job_id) if job_id is not None else None,
                        "run_id": run_id,
                        "listing_id": listing_id,
                        "stage": stage,
                        "job_type": job_type,
                        "worker_id": wid,
                    },
                )
            except Exception:
                # Best-effort only; pipeline must keep running if context cannot be set.
                pass

            # Emit explicit "started" event for Notion-style run logs.
            try:
                ok = await db.add_pipeline_job_event(
                    job_id=str(job_id),
                    event_type="started",
                    message="job started",
                    data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid},
                )
                if not ok:
                    logger.error(f"Failed to write started event (returned false) | job_id={job_id}")
            except Exception:
                logger.exception(f"Failed to write started event (exception) | job_id={job_id}")

            heartbeat_task: Optional[asyncio.Task] = None
            if job_id:
                heartbeat_task = asyncio.create_task(_heartbeat_loop(db, job_id=str(job_id), worker_id=wid))

            watchdog_task: Optional[asyncio.Task] = None
            cancel_task: Optional[asyncio.Task] = None
            try:
                # Enforce a hard max runtime per job so we never "run all night" without realizing.
                timeout_s = default_job_timeout_s
                stall_s = default_stall_s

                # Strict predecessor gate for V5: do not execute this job until
                # its direct predecessor in the V5 chain has succeeded.
                await _block_if_predecessor_not_ready(job)

                job_task = asyncio.create_task(_dispatch(job, db, handlers))
                watchdog_task = asyncio.create_task(
                    _stall_watchdog(
                        db=db,
                        job_id=str(job_id),
                        worker_id=wid,
                        run_id=run_id,
                        listing_id=listing_id,
                        stage=stage,
                        job_type=job_type,
                        stall_seconds=stall_s,
                        check_every_seconds=stall_check_every_s,
                        job_task=job_task,
                    )
                )
                cancel_task = asyncio.create_task(
                    _cancel_watchdog(
                        db=db,
                        job_id=str(job_id),
                        worker_id=wid,
                        run_id=run_id,
                        listing_id=listing_id,
                        stage=stage,
                        job_type=job_type,
                        check_every_seconds=3.0,
                        job_task=job_task,
                    )
                )

                if timeout_s and timeout_s > 0:
                    await asyncio.wait_for(job_task, timeout=timeout_s)
                else:
                    await job_task

                # If an admin cancelled mid-flight, do NOT ack as succeeded.
                try:
                    latest = await db.get_pipeline_job(str(job_id))
                    if str((latest or {}).get("status") or "") == "cancelled":
                        reason = _JOB_CANCEL_REASON.get(str(job_id)) or "job cancelled by admin"
                        logger.info("Job cancelled (post-run) | id=%s | reason=%s", job_id, reason)
                        try:
                            await db.add_pipeline_job_event(
                                job_id=str(job_id),
                                event_type="cancelled",
                                message="job cancelled",
                                data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid},
                            )
                        except Exception:
                            logger.exception(f"Failed to write cancelled event | job_id={job_id}")
                        return
                except Exception:
                    # Best-effort only; never crash due to cancellation check.
                    pass

                ok = await db.ack_pipeline_job(job_id)
                if not ok:
                    # If ack didn't match (e.g., admin cancelled just before ack),
                    # treat this as a cancellation rather than a failure.
                    try:
                        latest = await db.get_pipeline_job(str(job_id))
                        if str((latest or {}).get("status") or "") == "cancelled":
                            reason = _JOB_CANCEL_REASON.get(str(job_id)) or "job cancelled by admin"
                            logger.info("Job cancelled (ack blocked) | id=%s | reason=%s", job_id, reason)
                            try:
                                await db.add_pipeline_job_event(
                                    job_id=str(job_id),
                                    event_type="cancelled",
                                    message="job cancelled",
                                    data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid},
                                )
                            except Exception:
                                logger.exception(f"Failed to write cancelled event | job_id={job_id}")
                            return
                    except Exception:
                        pass
                    raise RuntimeError(f"ack failed for job_id={job_id}")

                duration_s = (datetime.utcnow() - started_at).total_seconds()
                try:
                    await db.add_pipeline_job_event(
                        job_id=str(job_id),
                        event_type="succeeded",
                        message="job succeeded",
                        data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid, "duration_s": round(duration_s, 3)},
                    )
                except Exception:
                    logger.exception(f"Failed to write succeeded event | job_id={job_id}")

            except asyncio.CancelledError:
                # Cancellation can mean either:
                # 1) Stall watchdog (internal) -> treat as failure
                # 2) Admin stop (external) -> treat as cancelled without failing
                cancel_reason = _JOB_CANCEL_REASON.get(str(job_id))
                if cancel_reason:
                    logger.info("Job cancelled by admin | id=%s | %s", job_id, cancel_reason)
                    try:
                        await db.add_pipeline_job_event(
                            job_id=str(job_id),
                            event_type="cancelled",
                            message="job cancelled",
                            data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid},
                        )
                    except Exception:
                        logger.exception(f"Failed to write cancelled event | job_id={job_id}")
                    return

                reason = _JOB_STALL_REASON.get(str(job_id)) or "job cancelled"
                raise RuntimeError(reason)
            except Exception as exc:
                if exc.__class__.__name__ in {"RescheduleRequested", "BlockedByPredecessor"}:
                    msg = str(exc) or f"{job_type}: rescheduled"
                    # Only log locally — do NOT persist "rescheduled" events to DB.
                    # WHY: when a predecessor is still queued, every downstream job gets
                    # rescheduled every ~20s. Writing events for each creates hundreds
                    # of useless DB rows per minute and floods the admin log viewer.
                    logger.info("Job rescheduled | id=%s | stage=%s | reason=%s", job_id, stage, msg)
                    return

                err = f"{type(exc).__name__}: {exc}"
                ctx = {
                    "traceback": traceback.format_exc()[-8000:],
                    "job_type": job_type,
                    "stage": stage,
                }
                # Default: retry quickly a couple times, then let DB mark failed via max_attempts
                try:
                    await db.fail_pipeline_job(job_id, err, ctx, retry_in_seconds=15)
                except httpx.ConnectTimeout:
                    logger.error(
                        f"Job failed but could not record failure (ConnectTimeout) | id={job_id} | err={err}"
                    )
                logger.error(f"Job failed | id={job_id} | err={err}")

                duration_s = (datetime.utcnow() - started_at).total_seconds()
                try:
                    await db.add_pipeline_job_event(
                        job_id=str(job_id),
                        event_type="failed",
                        message=err,
                        data={"run_id": run_id, "listing_id": listing_id, "stage": stage, "job_type": job_type, "worker_id": wid, "duration_s": round(duration_s, 3), "error": err},
                    )
                except Exception:
                    logger.exception(f"Failed to write failed event | job_id={job_id}")
                if stop_on_failure:
                    logger.error(
                        f"Stopping worker due to job failure (hard rule) | id={job_id} | stage={stage} | type={job_type}"
                    )
                    raise
            finally:
                if watchdog_task:
                    watchdog_task.cancel()
                    try:
                        await watchdog_task
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        pass

                if cancel_task:
                    cancel_task.cancel()
                    try:
                        await cancel_task
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        pass

                if heartbeat_task:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    except BaseException:
                        # Heartbeat failures should never crash the worker.
                        pass

                # Flush remaining logs before tearing down context/tasks.
                if job_id is not None:
                    try:
                        await _flush_job_logs_to_db(db=db, job_id=str(job_id), max_lines=2000)
                    except Exception:
                        pass
                    t = _JOB_LOG_TASKS.pop(str(job_id), None)
                    if t:
                        t.cancel()
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass
                        except BaseException:
                            pass
                    _JOB_LOG_QUEUES.pop(str(job_id), None)
                    _JOB_LAST_ACTIVITY_TS.pop(str(job_id), None)
                    _JOB_STALL_REASON.pop(str(job_id), None)
                    _JOB_CANCEL_REASON.pop(str(job_id), None)

                duration_s = (datetime.utcnow() - started_at).total_seconds()
                logger.info(f"Job finished | id={job_id} | stage={stage} | type={job_type} | duration={duration_s:.1f}s")

                # If configured, request a clean worker exit after this job completes.
                try:
                    if exit_after_job_type and str(job_type or "") == exit_after_job_type:
                        logger.info("Exit-after-job triggered | job_type=%s", exit_after_job_type)
                        exit_event.set()
                    if exit_after_stage and str(stage or "") == exit_after_stage:
                        logger.info("Exit-after-stage triggered | stage=%s", exit_after_stage)
                        exit_event.set()
                except Exception:
                    # Never crash due to debug-only exit checks.
                    pass

                try:
                    from pipeline.gemini_client import clear_gemini_tracking_context

                    clear_gemini_tracking_context()
                except Exception:
                    pass

                # Clear contextvars
                try:
                    _CTX_JOB_ID.reset(_t_job)
                    _CTX_RUN_ID.reset(_t_run)
                    _CTX_LISTING_ID.reset(_t_listing)
                except Exception:
                    pass

    while True:
        try:
            reaped = await db.reap_stuck_pipeline_jobs(stale_seconds=600, heartbeat_grace_seconds=300, limit=50)
            if reaped > 0:
                logger.warning("Reaped stuck pipeline jobs | count=%d", reaped)
        except Exception:
            logger.exception("Failed to reap stuck pipeline jobs")

        jobs = await db.claim_pipeline_jobs(worker_id=wid, limit=limit, lock_seconds=lock_seconds)
        if not jobs:
            await asyncio.sleep(poll_seconds)
            continue

        try:
            await asyncio.gather(*[_process_one(job) for job in jobs])
        except Exception:
            logger.exception("Worker stopping after job failure")
            return 1

        # Clean exit for debug runs.
        if exit_event.is_set():
            logger.info(
                "Worker exiting due to exit_after flag | exit_after_job_type=%s exit_after_stage=%s",
                exit_after_job_type or None,
                exit_after_stage or None,
            )
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline queue worker (fixed throughput).")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    # WHY THIS MATTERS: operators should not have to remember flags. A single env var controls concurrency.
    # - PIPELINE_WORKER_CONCURRENCY: sets BOTH claim limit + max inflight (default 30)
    default_concurrency = int(os.getenv("PIPELINE_WORKER_CONCURRENCY", "30"))
    parser.add_argument(
        "--claim-limit",
        type=int,
        default=int(os.getenv("PIPELINE_WORKER_CLAIM_LIMIT", str(default_concurrency))),
        help="How many jobs to claim per polling cycle (defaults to PIPELINE_WORKER_CONCURRENCY).",
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=int(os.getenv("PIPELINE_MAX_INFLIGHT", str(default_concurrency))),
        help="Max concurrent jobs processed per worker process.",
    )
    parser.add_argument("--lock-seconds", type=int, default=300)
    args = parser.parse_args()

    # Local imports to avoid path issues
    try:
        from database import Database
    except ModuleNotFoundError:
        backend_dir = Path(__file__).resolve().parents[1]
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from database import Database

    db = Database()

    from workers.handlers import (
        handle_fetch_comparables,
        handle_cluster_target,
        handle_v5_cluster_target_photos,
        handle_v5_fetch_listing_snapshot,
        handle_v5_fetch_comparables_snapshot,
        handle_smart_m2_target_indoorgml,
        handle_generate_target_pir,
        handle_v5_generate_target_pir_slots,
        handle_v5_room_tags,
        handle_v5_cluster_selected_comparable_photos,
        handle_v5_generate_selected_comparable_room_pirs,
        handle_v5_select_median_comparable,
        handle_v5_select_comparable,
        handle_v5_delta_slots_market_standard,
        handle_v5_work_items_market_standard,
        handle_v5_run_market_standard,
        # V5 sub-stages (split from monolithic v5_run)
        handle_v5_smart_m2,
        handle_gla_opinion,
        handle_v5_bcca_match,
        handle_v5_quant_plan,
        handle_v5_forage,
        handle_v5_boq_assembly,
        handle_v5_eli5,
        handle_v5_negotiation,
        handle_v5_architect_report,
        handle_v5_room_images,
        handle_v5_translations,
        handle_v5_finalize,
        handle_generate_cluster_panos,
        handle_cache_comparable_images,
        handle_cluster_comparable,
        handle_strategy_selection,
        handle_delta_scopes,
        handle_delta_strategy_spec,
        handle_delta_bcca_worklist,
        handle_validate_and_repair_worklist,
        handle_v3_boq_generate,
        handle_coverage_ledger_glue,
        handle_v4_run_strategy,
        handle_boq_enqueue_jobs,
        handle_boq_llm_scope_item,
        handle_boq_write_items,
        handle_boq_finalize_strategy,
        handle_boq_finalize_all,
        handle_post_boq_enqueue_all,
        handle_post_boq,
    )

    handlers: Dict[str, JobHandler] = {
        "fetch_comparables": handle_fetch_comparables,
        "cluster_target_photos": handle_cluster_target,
        "v5_cluster_target_photos": handle_v5_cluster_target_photos,
        "v5_fetch_listing_snapshot": handle_v5_fetch_listing_snapshot,
        "v5_fetch_comparables_snapshot": handle_v5_fetch_comparables_snapshot,
        "smart_m2_target_indoorgml": handle_smart_m2_target_indoorgml,
        "generate_target_pir": handle_generate_target_pir,
        "v5_generate_target_pir_slots": handle_v5_generate_target_pir_slots,
        "v5_room_tags": handle_v5_room_tags,
        # GLA (General Listing Analysis) reuses V5 handlers for shared stages.
        "gla_fetch_listing_snapshot": handle_v5_fetch_listing_snapshot,
        "gla_cluster_target_photos": handle_v5_cluster_target_photos,
        "gla_room_tags": handle_v5_room_tags,
        "gla_generate_target_pir_slots": handle_v5_generate_target_pir_slots,
        "gla_smart_m2": handle_v5_smart_m2,
        "gla_opinion": handle_gla_opinion,
        "v5_cluster_selected_comparable_photos": handle_v5_cluster_selected_comparable_photos,
        "v5_generate_selected_comparable_room_pirs": handle_v5_generate_selected_comparable_room_pirs,
        "v5_select_median_comparable": handle_v5_select_median_comparable,
        "v5_select_comparable": handle_v5_select_comparable,
        "v5_delta_slots_market_standard": handle_v5_delta_slots_market_standard,
        "v5_work_items_market_standard": handle_v5_work_items_market_standard,
        "v5_run_market_standard": handle_v5_run_market_standard,
        # V5 sub-stages (split from monolithic v5_run)
        "v5_smart_m2": handle_v5_smart_m2,
        "v5_bcca_match": handle_v5_bcca_match,
        "v5_quant_plan": handle_v5_quant_plan,
        "v5_forage": handle_v5_forage,
        "v5_boq_assembly": handle_v5_boq_assembly,
        "v5_eli5": handle_v5_eli5,
        "v5_negotiation": handle_v5_negotiation,
        "v5_architect_report": handle_v5_architect_report,
        "v5_room_images": handle_v5_room_images,
        "v5_translations": handle_v5_translations,
        "v5_finalize": handle_v5_finalize,
        # Backwards-compat only (no longer enqueued): panos removed from pipeline.
        "generate_cluster_panos": handle_generate_cluster_panos,
        "cache_comparable_images": handle_cache_comparable_images,
        "cluster_comparable_photos": handle_cluster_comparable,
        "strategy_selection": handle_strategy_selection,
        "delta_scopes": handle_delta_scopes,
        "delta_strategy_spec": handle_delta_strategy_spec,
        "delta_bcca_worklist": handle_delta_bcca_worklist,
        "validate_and_repair_worklist": handle_validate_and_repair_worklist,
        "v3_boq_generate": handle_v3_boq_generate,
        "coverage_ledger_glue": handle_coverage_ledger_glue,
        "v4_run_strategy": handle_v4_run_strategy,
        "boq_enqueue_scope_jobs": handle_boq_enqueue_jobs,
        "boq_llm_scope_item": handle_boq_llm_scope_item,
        "boq_write_items": handle_boq_write_items,
        "boq_finalize_strategy": handle_boq_finalize_strategy,
        "boq_finalize_all": handle_boq_finalize_all,
        "post_boq_enqueue_all": handle_post_boq_enqueue_all,
        "post_boq_strategy": handle_post_boq,
    }

    return asyncio.run(_run_loop(db, handlers, args.poll_seconds, args.claim_limit, args.lock_seconds, args.max_inflight))


if __name__ == "__main__":
    raise SystemExit(main())

