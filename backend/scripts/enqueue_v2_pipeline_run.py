#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enqueue_v2_pipeline")

async def enqueue(listing_id: int) -> None:
    try:
        from database import Database
    except ModuleNotFoundError:
        backend_dir = Path(__file__).resolve().parents[1]
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from database import Database

    db = Database()
    from pricing.v2_scheduler import enqueue_v2_run

    run_id = await enqueue_v2_run(db=db, listing_id=listing_id)
    logger.info(f"Enqueued V2 pipeline run | run_id={run_id} | listing_id={listing_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enqueue full V2 pipeline run (queue-based).")
    parser.add_argument("--listing-id", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(enqueue(args.listing_id))


if __name__ == "__main__":
    main()

