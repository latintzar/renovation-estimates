import logging
from typing import Any, Dict, List

from .quantity_resolver import resolve_quantity_ref
from .worklist_validator import infer_unit_family, parse_quantity_ref

logger = logging.getLogger(__name__)


def build_coverage_ledger(
    *,
    worklist_items: List[Dict[str, Any]],
    smart_m2_rooms: List[Dict[str, Any]],
    takeoff_menu: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a deterministic coverage ledger per room.

    WHY THIS MATTERS: It lets us audit coverage without introducing new arithmetic or LLM calls.
    """
    menu_rooms = (takeoff_menu or {}).get("rooms") or {}
    coverage: Dict[str, Dict[str, float]] = {}
    menu_totals: Dict[str, Dict[str, float]] = {}

    def _add(map_by_room: Dict[str, Dict[str, float]], room_id: str, family: str, qty: float) -> None:
        if room_id not in map_by_room:
            map_by_room[room_id] = {}
        map_by_room[room_id][family] = map_by_room[room_id].get(family, 0.0) + qty

    # Totals from TAKEOFF_MENU (deterministic primitives)
    for room_id, room_menu in menu_rooms.items():
        refs = room_menu.get("all_quantity_refs") or []
        for ref in refs:
            try:
                name, args = parse_quantity_ref(ref)
                family = infer_unit_family(name, args)
                if not family:
                    continue
                qty, _ = resolve_quantity_ref(ref, smart_m2_rooms)
                _add(menu_totals, room_id, family, float(qty))
            except Exception as exc:
                logger.warning(f"coverage_ledger: skip menu ref | room_id={room_id} ref={ref} err={exc}")

    # Coverage from worklist items
    for item in worklist_items:
        room_id = str(item.get("room_id") or "").strip()
        ref = item.get("quantity_ref")
        if not room_id or not ref:
            continue
        try:
            name, args = parse_quantity_ref(ref)
            family = infer_unit_family(name, args)
            if not family:
                continue
            qty, _ = resolve_quantity_ref(ref, smart_m2_rooms)
            _add(coverage, room_id, family, float(qty))
        except Exception as exc:
            logger.warning(f"coverage_ledger: skip item ref | room_id={room_id} ref={ref} err={exc}")

    residuals: Dict[str, Dict[str, float]] = {}
    for room_id, totals in menu_totals.items():
        residuals[room_id] = {}
        for family, total in totals.items():
            covered = (coverage.get(room_id) or {}).get(family, 0.0)
            residual = max(total - covered, 0.0)
            residuals[room_id][family] = residual

    return {
        "menu_totals_by_room": menu_totals,
        "covered_totals_by_room": coverage,
        "residuals_by_room": residuals,
    }
