"""
V5 Room Tags
============

Derive deterministic room tags for V5 from canonical cluster labels and metadata.

V5 goal:
- clusters already have canonical `room_type` and `cluster_id` like `kitchen_1`
- tags add: environment, combined_types, traits (open_plan, studio), evidence refs
"""

from __future__ import annotations

from typing import Any, Dict, List

from pricing.v5_room_types import ROOM_TYPES_V5, combined_types_for, is_open_plan


def build_room_tags_v5(*, listing_id: int, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    rooms = []
    for c in clusters or []:
        if not isinstance(c, dict):
            continue
        room_id = str(c.get("cluster_id") or "").strip()
        room_type = str(c.get("room_type") or "").strip()
        if not room_id or not room_type:
            continue
        spec = ROOM_TYPES_V5.get(room_type)
        if not spec:
            # fallback
            spec = ROOM_TYPES_V5["unknown_room"]
            room_type = "unknown_room"

        traits: List[str] = []
        combined = combined_types_for(room_type)
        if combined:
            traits.append("open_plan")
            traits.append("combined")
        if room_type == "studio_main_space":
            traits.append("studio_main_space")

        evidence_refs: List[str] = []
        # Minimal: record photo indices as evidence refs (urls are too long/noisy).
        for idx in c.get("photo_indices") or []:
            if isinstance(idx, int):
                evidence_refs.append(f"PHOTO_IDX({idx})")

        rooms.append(
            {
                "room_id": room_id,
                "room_type": room_type,
                "environment": spec.environment,
                "traits": traits,
                "combined_types": combined,
                "confidence": float(c.get("confidence") or 0.0),
                "evidence_refs": evidence_refs,
                "notes": str(c.get("description") or ""),
            }
        )

    return {"listing_id": int(listing_id), "rooms": rooms}

