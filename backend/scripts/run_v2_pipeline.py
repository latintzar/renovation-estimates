#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


async def _run(listing_id: int, force_restart: bool) -> int:
    try:
        # Local imports to avoid path issues
        try:
            from database import Database
            from pricing.v2_scheduler import enqueue_v2_run
        except ModuleNotFoundError:
            backend_dir = Path(__file__).resolve().parents[1]
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from database import Database
            from pricing.v2_scheduler import enqueue_v2_run

        db = Database()

        print("=" * 70)
        print(f"V2 PIPELINE (QUEUE) - LISTING {listing_id}")
        print("=" * 70)
        if force_restart:
            print("⚠️ force_restart requested: this script does NOT clear data; use clear-listing for explicit clears.")

        run_id = await enqueue_v2_run(db=db, listing_id=listing_id)
        print(f"Enqueued run_id: {run_id}")
        print("=" * 70)

        # Foreground monitor: print a clear run log line every 10s until done or failed.
        last = None
        last_event_id = None
        while True:
            counts = await db.get_pipeline_job_counts(run_id=run_id)
            queued = counts.get("queued", 0)
            in_progress = counts.get("in_progress", 0)
            failed = counts.get("failed", 0)
            succeeded = counts.get("succeeded", 0)
            snap = (queued, in_progress, failed, succeeded)
            if snap != last:
                print(f"run_id={run_id} | queued={queued} | in_progress={in_progress} | failed={failed} | succeeded={succeeded}")
                last = snap

            latest_event = await db.get_latest_pipeline_job_event(run_id=run_id)
            if latest_event:
                event_id = latest_event.get("id")
                if event_id and event_id != last_event_id:
                    data = latest_event.get("data") or {}
                    job_type = data.get("job_type") or "unknown"
                    stage = data.get("stage") or "unknown"
                    message = latest_event.get("message") or ""
                    event_type = latest_event.get("event_type") or "event"
                    print(f"event={event_type} | stage={stage} | job_type={job_type} | {message}")
                    last_event_id = event_id

            if failed > 0:
                print(f"❌ Run failed (failed_jobs={failed}). Check pipeline_job_events for details.")
                return 1
            if queued == 0 and in_progress == 0:
                print("✅ Run complete (no queued/in_progress jobs).")
                return 0
            await asyncio.sleep(10)
    except Exception as exc:
        print(f"\n❌ ERROR: {exc}")
        traceback.print_exc()
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run V2 pipeline in foreground.")
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--force-restart", action="store_true")
    args = parser.parse_args()

    return asyncio.run(_run(args.listing_id, args.force_restart))


if __name__ == "__main__":
    sys.exit(main())
