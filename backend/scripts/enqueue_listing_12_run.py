#!/usr/bin/env python3
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enqueue_listing")


async def main() -> None:
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
    listing_id = 12
    run_id = await enqueue_v2_run(db=db, listing_id=listing_id)
    logger.info(f"Enqueued V2 run | run_id={run_id} | listing_id={listing_id}")


if __name__ == "__main__":
    asyncio.run(main())

