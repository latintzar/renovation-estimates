"""
V5 Work Items Builder
=====================

    Turn per-room slot deltas into a flat list of work items for catalog matching.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

from pricing.v5_strategy_delta_decompose import decompose_v5_room_all_dimensions


def slot_id_to_dimension(slot_id: str) -> str:
    s = str(slot_id or "")
    if s.startswith("shell."):
        return "shell_preparation"
    if s.startswith("enclosure."):
        return "apertures_enclosure"
    if s.startswith("mep."):
        return "systems_services"
    if s.startswith("finishes."):
        return "surface_finishes"
    if s.startswith("joinery."):
        return "fixed_joinery_equipment"
    if s.startswith("details."):
        return "details_fittings"
    return "systems_services"


async def build_v5_work_items_for_strategy(
    *,
    listing_id: int,
    strategy_name: str,
    delta_slots: Dict[str, Any],
    concurrency: int = 5,
    gemini_semaphore: Any = None,
) -> Dict[str, Any]:
    """
    Input: V5_DELTA_SLOTS_SCHEMA output (listing_id, strategy_name, rooms[].slot_work_narratives)
    Output: V5_WORK_ITEMS_SCHEMA-like dict.
    """
    if concurrency < 1:
        raise ValueError(f"concurrency must be >= 1 (got {concurrency})")

    room_jobs: List[Dict[str, Any]] = []
    for room in (delta_slots.get("rooms") or []):
        room_id = str(room.get("room_id") or "").strip()
        room_type = str(room.get("room_type") or "").strip()
        slot_work = room.get("slot_work_narratives") or {}
        if not room_id or not room_type or not isinstance(slot_work, dict):
            continue

        # One call per room: pass only the slots that require work (exclude "no change").
        slots_needing_work: Dict[str, str] = {}
        for slot_id, narrative in slot_work.items():
            if not isinstance(slot_id, str) or not slot_id.strip():
                continue
            if not isinstance(narrative, str):
                continue
            n = narrative.strip()
            if not n:
                continue
            if n.strip().lower() == "no change":
                continue
            slots_needing_work[str(slot_id)] = n

        if not slots_needing_work:
            continue

        room_jobs.append(
            {
                "room_id": room_id,
                "room_type": room_type,
                "slots_needing_work": slots_needing_work,
            }
        )

    if not room_jobs:
        return {"listing_id": int(listing_id), "strategy_name": str(strategy_name), "items": []}

    sem = asyncio.Semaphore(concurrency)

    async def _run_one(job: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        rid = str(job["room_id"])
        rt = str(job["room_type"])
        slots = job["slots_needing_work"]
        async with sem:
            out = await decompose_v5_room_all_dimensions(
                listing_id=listing_id,
                strategy_name=strategy_name,
                room_id=rid,
                room_type=rt,
                slot_narratives=slots,
                gemini_semaphore=gemini_semaphore,
            )
            return rid, rt, out or {}

    tasks = [asyncio.create_task(_run_one(j)) for j in room_jobs]
    results: List[Tuple[str, str, Dict[str, Any]]] = []
    try:
        for t in asyncio.as_completed(tasks):
            results.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    # Stable item IDs: build deterministically after all room calls finish.
    items: List[Dict[str, Any]] = []
    wid_counter = 0
    for room_id, _room_type, by_dim_by_slot_descs in sorted(results, key=lambda x: x[0]):
        if not isinstance(by_dim_by_slot_descs, dict):
            continue
        for dim in sorted(by_dim_by_slot_descs.keys()):
            by_slot = by_dim_by_slot_descs.get(dim)
            if not isinstance(by_slot, dict):
                continue
            for slot_id in sorted(by_slot.keys()):
                descs = by_slot.get(slot_id)
                if not isinstance(descs, list):
                    continue
                for d in descs:
                    if not isinstance(d, str) or not d.strip():
                        continue
                    wid_counter += 1
                    items.append(
                        {
                            "work_item_id": f"v5:{strategy_name}:{room_id}:{wid_counter}",
                            "room_id": room_id,
                            "slot_id": str(slot_id),
                            "dimension": slot_id_to_dimension(str(slot_id)),
                            "work_description": d.strip(),
                            "source_refs": [f"SLOT({slot_id})"],
                        }
                    )

    return {"listing_id": int(listing_id), "strategy_name": str(strategy_name), "items": items}

