#!/usr/bin/env python3
"""
Smoke: V5 target PIR (slot-first, per-room)

Writes:
- unified_estimates: v5_pir_target

Prereqs:
- photo_clusters (V5 constrained clustering recommended; clusters are authoritative)

Usage:
  python3 scripts/smoke_v5_pir_target_slots.py --listing-id 12 --force
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import call_gemini, fetch_images_batch, set_gemini_tracking_context  # noqa: E402
from pricing.v5_pir import generate_v5_target_room_pir  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--max-photos-per-room", type=int, default=12)
    p.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max number of rooms processed concurrently (bounded). Default 5.",
    )
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)
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

    listing_data = await db.get_listing(listing_id)
    if not listing_data:
        raise RuntimeError(f"listing not found | listing_id={listing_id}")
    construction_year = listing_data.get("construction_year") or listing_data.get("year_built")

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_pir_target")
    existing_rooms: List[Dict[str, Any]] = []
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list):
        existing_rooms = [r for r in (existing.get("rooms") or []) if isinstance(r, dict)]
        if existing_rooms:
            logger.info(
                "v5_pir_target: found existing payload | listing_id=%s rooms=%s",
                listing_id,
                len(existing_rooms),
            )

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"missing photo_clusters | listing_id={listing_id}")

    room_entries: List[Dict[str, Any]] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        rid = str(c.get("cluster_id") or "").strip()
        rt = str(c.get("room_type") or "").strip() or "unknown_room"
        urls = [u for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        if not rid or not urls:
            continue
        if rt in ("floorplan", "street_view", "views_outlook"):
            continue
        room_entries.append({"room_id": rid, "room_type": rt, "photo_urls": urls})
    if not room_entries:
        raise RuntimeError(f"no usable room clusters | listing_id={listing_id}")

    rooms_out: List[Dict[str, Any]] = list(existing_rooms)
    done_room_ids = {str(r.get("room_id") or "").strip() for r in rooms_out if str(r.get("room_id") or "").strip()}

    sem = asyncio.Semaphore(concurrency)

    async def _run_one_room(entry: Dict[str, Any]) -> Dict[str, Any]:
        rid_local = str(entry["room_id"])
        async with sem:
            logger.info("v5_pir_target: start room | listing_id=%s room_id=%s", listing_id, rid_local)
            room_payload_local = await generate_v5_target_room_pir(
                room_id=rid_local,
                room_type=str(entry["room_type"]),
                photo_urls=entry["photo_urls"],
                construction_year=construction_year,
                max_photos=int(args.max_photos_per_room),
                call_gemini_fn=call_gemini,
                fetch_images_batch_fn=fetch_images_batch,
            )
            logger.info("v5_pir_target: done room | listing_id=%s room_id=%s", listing_id, rid_local)
            return room_payload_local

    entries_to_run: List[Dict[str, Any]] = []
    for e in sorted(room_entries, key=lambda x: str(x.get("room_id") or "")):
        rid = str(e["room_id"])
        if not force and rid in done_room_ids:
            logger.info("v5_pir_target: skip room already present | listing_id=%s room_id=%s", listing_id, rid)
            continue
        entries_to_run.append(e)

    logger.info(
        "v5_pir_target: plan | listing_id=%s rooms_existing=%s rooms_to_run=%s concurrency=%s",
        listing_id,
        len(rooms_out),
        len(entries_to_run),
        concurrency,
    )

    tasks_by_id: Dict[asyncio.Task[Dict[str, Any]], str] = {}
    for e in entries_to_run:
        rid = str(e["room_id"])
        t: asyncio.Task[Dict[str, Any]] = asyncio.create_task(_run_one_room(e))
        tasks_by_id[t] = rid

    try:
        for t in asyncio.as_completed(list(tasks_by_id.keys())):
            room_payload = await t
            rid = str(room_payload.get("room_id") or "").strip() or tasks_by_id.get(t, "unknown_room_id")
            rooms_out.append(room_payload)
            done_room_ids.add(rid)

            # Checkpoint after each room so interrupted runs resume without rework.
            payload_checkpoint = {
                "listing_id": listing_id,
                "rooms": sorted(rooms_out, key=lambda r: str(r.get("room_id") or "")),
                "schema_version": "v5_pir_target_v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "counts": {"rooms": len(rooms_out)},
            }
            ok = await db.save_unified_estimate(listing_id, "v5_pir_target", payload_checkpoint)
            if not ok:
                raise RuntimeError(
                    f"save_unified_estimate failed | key=v5_pir_target listing_id={listing_id} room_id={rid}"
                )
            logger.info("v5_pir_target: checkpoint saved | listing_id=%s rooms=%s", listing_id, len(rooms_out))
    except Exception:
        for pending in tasks_by_id.keys():
            if not pending.done():
                pending.cancel()
        raise

    payload_out = {
        "listing_id": listing_id,
        "rooms": sorted(rooms_out, key=lambda r: str(r.get("room_id") or "")),
        "schema_version": "v5_pir_target_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"rooms": len(rooms_out)},
    }
    ok = await db.save_unified_estimate(listing_id, "v5_pir_target", payload_out)
    if not ok:
        raise RuntimeError(f"save_unified_estimate failed | key=v5_pir_target listing_id={listing_id}")

    sample = (payload_out.get("rooms") or [])[:1]
    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_pir_target_listing_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Target PIR (per-room, slot-first)",
        meta={
            "listing_id": listing_id,
            "key_written": "v5_pir_target",
            "rooms": len(payload_out.get("rooms") or []),
        },
        sample=sample[0] if sample else None,
        payload=payload_out,
    )
    print(
        {
            "stage": "v5_pir_target",
            "listing_id": listing_id,
            "key_written": "v5_pir_target",
            "rooms": len(payload_out.get("rooms") or []),
            "report_path": report_path,
            "sample": sample,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

