#!/usr/bin/env python3
"""
Smoke: V5 comparable (selected-only) — cluster → per-room PIRs → aggregate slot standard.

Writes:
- unified_estimates:
  - v5_selected_comparable
  - v5_selected_comparable_clusters_{comp_id}
  - v5_selected_comparable_room_pirs_{comp_id}
  - v5_selected_comparable_slot_standard_{comp_id}

Prereqs:
- listing_comparables exists

Usage:
  python3 scripts/smoke_v5_comparable_pir_v5.py --listing-id 12 --force
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import set_gemini_tracking_context  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402
from workers.handlers import (  # noqa: E402
    handle_v5_select_median_comparable,
    handle_v5_cluster_selected_comparable_photos,
    handle_v5_generate_selected_comparable_room_pirs,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--force-select",
        action="store_true",
        help="Force re-selecting the median comparable (otherwise reused if present).",
    )
    p.add_argument(
        "--force-clusters",
        action="store_true",
        help="Force re-clustering selected comparable photos (otherwise reused if present).",
    )
    p.add_argument(
        "--force-room-pirs",
        action="store_true",
        help="Force regenerating selected comparable room PIRs + slot standard (otherwise reused if present).",
    )
    p.add_argument("--max-photos-per-room", type=int, default=8)
    p.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max number of comparable rooms processed concurrently (bounded). Default 5.",
    )
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force_all = bool(args.force)
    force_select = force_all or bool(args.force_select)
    force_clusters = force_all or bool(args.force_clusters)
    force_room_pirs = force_all or bool(args.force_room_pirs)
    concurrency = int(args.concurrency)
    if concurrency < 1:
        raise ValueError(f"--concurrency must be >= 1 (got {concurrency})")

    # Attach DB + job context so gemini_client can persist call usage rows.
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    run_id = f"{script_name}_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={"run_id": run_id, "listing_id": listing_id, "stage": script_name, "job_type": "smoke", "job_id": None},
    )

    job = {
        "id": f"smoke-{listing_id}-v5_comp_selected_cluster_room_pirs",
        "run_id": f"smoke_{listing_id}",
        "listing_id": listing_id,
        "stage": "v5_select",
        "job_type": "v5_select_median_comparable",
        "payload": {"force": force_select, "price_field": "sale_price"},
        "idempotency_key": f"smoke:{listing_id}:v5_select_median_comparable",
    }
    await handle_v5_select_median_comparable(job, db)

    job2 = {
        **job,
        "id": f"smoke-{listing_id}-v5_comp_cluster",
        "stage": "v5_comparables",
        "job_type": "v5_cluster_selected_comparable_photos",
        "payload": {"force": force_clusters},
        "idempotency_key": f"smoke:{listing_id}:v5_cluster_selected_comparable_photos",
    }
    await handle_v5_cluster_selected_comparable_photos(job2, db)

    job3 = {
        **job,
        "id": f"smoke-{listing_id}-v5_comp_room_pirs",
        "stage": "v5_comparables",
        "job_type": "v5_generate_selected_comparable_room_pirs",
        "payload": {"force": force_room_pirs, "max_photos_per_room": int(args.max_photos_per_room), "concurrency": concurrency},
        "idempotency_key": f"smoke:{listing_id}:v5_generate_selected_comparable_room_pirs",
    }
    await handle_v5_generate_selected_comparable_room_pirs(job3, db)

    selected = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    selected_id = (selected or {}).get("selected_comparable_id") if isinstance(selected, dict) else None
    sample = None
    if selected_id:
        sample = await db.get_unified_estimate(listing_id, f"v5_selected_comparable_slot_standard_{int(selected_id)}")

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_comparable_pir_v5_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Comparable (selected-only) clustered room PIRs → slot standard",
        meta={"listing_id": listing_id, "selected_comparable_id": selected_id, "max_photos_per_room": int(args.max_photos_per_room)},
        sample=sample,
        payload={"v5_selected_comparable": selected, "slot_standard_key": f"v5_selected_comparable_slot_standard_{selected_id}"},
    )
    print({"stage": "v5_comparable_pir_v5", "listing_id": listing_id, "report_path": report_path})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

