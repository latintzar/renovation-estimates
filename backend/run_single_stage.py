#!/usr/bin/env python3
"""
Run a single pipeline stage handler directly (no worker, no queue).

Usage:
    python run_single_stage.py <listing_id> <stage_name> [--force]

Example:
    python run_single_stage.py 17 v5_negotiation --force
    python run_single_stage.py 17 v5_translations --force
"""
import asyncio
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_single_stage")

# Load env
from dotenv import load_dotenv
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

from workers.handlers import (
    handle_v5_negotiation,
    handle_v5_translations,
)
from database import Database
from pipeline.gemini_client import set_gemini_tracking_context, clear_gemini_tracking_context

HANDLERS = {
    "v5_negotiation": handle_v5_negotiation,
    "v5_translations": handle_v5_translations,
}


async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    listing_id = int(sys.argv[1])
    stage = sys.argv[2]
    force = "--force" in sys.argv

    if stage not in HANDLERS:
        print(f"Unknown stage: {stage}. Available: {list(HANDLERS.keys())}")
        sys.exit(1)

    handler = HANDLERS[stage]
    db = Database()

    # Build a fake job dict that the handler expects
    job = {
        "id": f"manual-{stage}-{listing_id}",
        "listing_id": listing_id,
        "job_type": stage,
        "stage": stage,
        "payload": {"force": force},
        "run_id": f"manual-run-{listing_id}",
        "attempt": 1,
    }

    # Set Gemini tracking context so call logging works
    set_gemini_tracking_context(db, {
        "job_id": job["id"],
        "run_id": job["run_id"],
        "listing_id": listing_id,
        "stage": stage,
        "job_type": stage,
    })

    logger.info("Running %s for listing %d (force=%s)", stage, listing_id, force)
    try:
        await handler(job, db)
        logger.info("SUCCESS: %s completed for listing %d", stage, listing_id)
    except Exception as e:
        logger.error("FAILED: %s for listing %d: %s", stage, listing_id, e, exc_info=True)
        sys.exit(1)
    finally:
        clear_gemini_tracking_context()


if __name__ == "__main__":
    asyncio.run(main())
