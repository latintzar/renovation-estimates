"""
V5 Comparable Standard Aggregation
=================================

We often need a *whole-property* reference standard derived from per-room comparable PIRs.

WHY:
- Whole-home comparable PIRs can be very large and can hit output truncation.
- Per-room PIRs are smaller, slot-protocol based, and more reliable.

This module aggregates comparable room PIRs into a single slot->sentence mapping that
represents the comparable "market standard" baseline.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pricing.v5_slots import SLOTS_V5


def build_v5_comparable_slot_standard(*, room_pirs: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build a whole-property slot standard mapping from comparable room PIRs.

    Strategy:
    - For each slot, choose the first available narrative from the most relevant room types.
    - If no preferred room type has that slot, fall back to any room that does.
    """
    rooms = [r for r in (room_pirs or []) if isinstance(r, dict)]
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for r in rooms:
        rt = str(r.get("room_type") or "").strip() or "unknown_room"
        by_type.setdefault(rt, []).append(r)

    def _slot_map(room: Dict[str, Any]) -> Dict[str, str]:
        m = room.get("slot_narratives") or {}
        if not isinstance(m, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in m.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                out[k.strip()] = v.strip()
        return out

    def _pick(slot_id: str, preferred_types: List[str]) -> str:
        # Preferred room types first
        for rt in preferred_types:
            for room in by_type.get(rt, []):
                val = _slot_map(room).get(slot_id)
                if val:
                    return val
        # Any room that has it
        for room in rooms:
            val = _slot_map(room).get(slot_id)
            if val:
                return val
        return ""

    # Room-type preference heuristics by slot family
    KITCHEN = ["kitchen", "open_plan_kitchen_living", "open_plan_kitchen_dining", "open_plan_kitchen_living_dining", "gallery_laundry"]
    BATH = ["bathroom_full", "bathroom_en_suite", "shower_room", "toilet_room", "powder_room"]
    LAUNDRY = ["laundry_room", "gallery_laundry", "utility_room"]
    ENTRY = ["entry_hall", "hallway", "landing"]
    DRY_MAIN = ["living_room", "dining_room", "open_plan_living_dining", "open_plan_kitchen_living", "open_plan_kitchen_living_dining", "bedroom_primary", "bedroom_secondary", "bedroom_single", "office"]
    EXTERIOR = ["balcony", "terrace", "terrace_covered", "terrace_rooftop", "patio", "garden", "service_terrace", "balcony_laundry"]

    # Specific slot overrides (strong preferences)
    pref_overrides: Dict[str, List[str]] = {
        # kitchen joinery/equipment
        "joinery.kitchen_cabinetry": KITCHEN,
        "joinery.kitchen_worktops_splashback": KITCHEN,
        "joinery.kitchen_appliance_integration": KITCHEN,
        # bathroom fixtures
        "details.sanitary_fixtures": BATH,
        "details.bathing_units": BATH,
        "details.taps_mixers": BATH,
        "finishes.wall_tiling": BATH + KITCHEN,
        "finishes.joints_grout": BATH + KITCHEN,
        "finishes.waterproofing": BATH + KITCHEN,
        # laundry
        "joinery.laundry_storage": LAUNDRY,
        # entrance/security
        "enclosure.entrance_door": ENTRY,
        "details.intercom_entry": ENTRY,
        # balcony/terrace
        "enclosure.balcony_doors": EXTERIOR + DRY_MAIN,
    }

    out: Dict[str, str] = {}
    for slot_id in SLOTS_V5:
        slot = str(slot_id)
        pref = pref_overrides.get(slot)
        if not pref:
            if slot.startswith("joinery.kitchen_"):
                pref = KITCHEN
            elif slot.startswith("mep.plumbing_") or slot in ("mep.hot_water_generator", "mep.gas_supply"):
                pref = (KITCHEN + BATH + LAUNDRY + ENTRY)
            elif slot.startswith("finishes.wall_") or slot.startswith("finishes.joints_") or slot.startswith("finishes.water"):
                pref = (BATH + KITCHEN + DRY_MAIN)
            elif slot.startswith("mep.electrical_") or slot in ("mep.sockets_switches", "mep.lighting_points", "details.electrical_trim"):
                pref = (ENTRY + DRY_MAIN + KITCHEN + BATH)
            elif slot.startswith("shell.") or slot.startswith("enclosure."):
                pref = (DRY_MAIN + ENTRY + KITCHEN + BATH + EXTERIOR)
            else:
                pref = (DRY_MAIN + ENTRY + KITCHEN + BATH + EXTERIOR + LAUNDRY)

        val = _pick(slot, pref)
        if val:
            out[slot] = val
        else:
            # Keep keys stable: if no signal, provide a conservative placeholder.
            out[slot] = "No se aprecia claramente en las fotos ni hay evidencia suficiente en los PIRs; confirmar en visita."

    return out

