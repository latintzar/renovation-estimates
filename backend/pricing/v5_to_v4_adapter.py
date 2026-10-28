"""
Adapters between V5 artifacts and existing V4 tail.

Key idea: We can keep V4 quant/forage/BOQ unchanged by writing `v4_worklist_{strategy}_{dim}`
from V5 decomposed work items (room-scoped).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS


def v5_work_items_to_v4_worklists_by_dim(*, work_items: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Input: V5 work_items payload (listing_id, strategy_name, items[])
    Output: dict keyed by dimension -> V4_WORKLIST_DIMENSION-like payload.
    """
    items = work_items.get("items") or []
    by_dim_room: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        if not isinstance(it, dict):
            continue
        dim = str(it.get("dimension") or "").strip()
        if dim not in V2_DIMENSIONS:
            continue
        room_id = str(it.get("room_id") or "").strip()
        if not room_id:
            continue
        by_dim_room[dim][room_id].append(it)

    out: Dict[str, Dict[str, Any]] = {}
    for dim in V2_DIMENSIONS:
        room_blocks = []
        for room_id in sorted(by_dim_room.get(dim, {}).keys()):
            pkgs = []
            for it in by_dim_room[dim][room_id]:
                pkgs.append(
                    {
                        "work_item_id": str(it.get("work_item_id") or ""),
                        "work_description": str(it.get("work_description") or ""),
                        "target_element": str(it.get("slot_id") or ""),
                        "source_scope_refs": list(it.get("source_refs") or []),
                    }
                )
            room_blocks.append({"room_id": room_id, "scope_packages": pkgs})
        out[dim] = {"dimension": dim, "dimension_intro": f"V5-derived worklist for {dim}", "room_blocks": room_blocks}
    return out

