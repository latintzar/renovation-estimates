import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _normalize_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _add_ref(container: List[str], ref: str) -> None:
    if ref and ref not in container:
        container.append(ref)


def _add_entry(menu: Dict[str, List[str]], key: str, ref: str) -> None:
    if key not in menu:
        menu[key] = []
    _add_ref(menu[key], ref)


def build_takeoff_menu(smart_m2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build deterministic TAKEOFF_MENU per room from Smart M2 output.

    WHY THIS MATTERS: Downstream steps must SELECT quantity_ref strings, not compute arithmetic.
    """
    if not smart_m2 or not isinstance(smart_m2, dict):
        raise RuntimeError("takeoff_menu: smart_m2 missing or invalid")

    rooms = smart_m2.get("rooms")
    if not rooms or not isinstance(rooms, list):
        raise RuntimeError("takeoff_menu: smart_m2.rooms missing or invalid")

    menu_by_room: Dict[str, Dict[str, Any]] = {}

    for room in rooms:
        if not isinstance(room, dict):
            continue

        room_id = _normalize_id(room.get("room_id") or room.get("cluster_id"))
        if not room_id:
            raise RuntimeError(f"takeoff_menu: room missing room_id/cluster_id | room={room}")

        menu: Dict[str, List[str]] = {
            "surfaces": [],
            "details": [],
            "openings": [],
            "features": [],
            "waste": [],
        }

        # Surfaces (room-level primitives)
        if room.get("estimated_m2") is not None:
            _add_entry(menu, "surfaces", f"FLOOR_M2({room_id})")
            _add_entry(menu, "surfaces", f"CEILING_M2({room_id})")
        if room.get("perimeter_m") is not None:
            _add_entry(menu, "surfaces", f"PERIMETER_ML({room_id})")
        if room.get("wall_gross_m2") is not None:
            _add_entry(menu, "surfaces", f"WALL_GROSS_M2({room_id})")
        if room.get("openings_total_area_m2") is not None:
            _add_entry(menu, "surfaces", f"OPENINGS_TOTAL_AREA_M2({room_id})")
        if room.get("wall_net_m2") is not None:
            _add_entry(menu, "surfaces", f"WALL_NET_M2({room_id})")

        # Detail primitives (from takeoff_primitives)
        takeoff = room.get("takeoff_primitives") or {}
        if isinstance(takeoff, dict):
            if (takeoff.get("skirting_gross_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"SKIRTING_ML({room_id}, variant=gross)")
            if (takeoff.get("skirting_net_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"SKIRTING_ML({room_id}, variant=net)")
            if (takeoff.get("coving_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"COVING_ML({room_id})")
            if (takeoff.get("window_sill_total_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"WINDOW_SILL_ML({room_id})")
            if (takeoff.get("door_threshold_total_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"DOOR_THRESHOLD_ML({room_id})")
            if (takeoff.get("sealant_total_ml") or {}).get("value") is not None:
                _add_entry(menu, "details", f"SEALANT_ML({room_id})")

        # Openings (per-opening + aggregates)
        openings = room.get("openings") or []
        if isinstance(openings, list) and openings:
            _add_entry(menu, "openings", f"OPENING_COUNT({room_id})")
            _add_entry(menu, "openings", f"OPENING_AREA_TOTAL_M2({room_id})")
            _add_entry(menu, "openings", f"OPENING_PERIMETER_TOTAL_ML({room_id})")
            _add_entry(menu, "openings", f"OPENING_WIDTH_TOTAL_ML({room_id})")
            _add_entry(menu, "openings", f"OPENING_HEIGHT_TOTAL_ML({room_id})")

        for opening in openings:
            if not isinstance(opening, dict):
                continue
            opening_id = _normalize_id(opening.get("opening_id"))
            if not opening_id:
                raise RuntimeError(f"takeoff_menu: opening missing opening_id | room_id={room_id}")
            if opening.get("area_m2") is not None:
                _add_entry(menu, "openings", f"OPENING_AREA_M2({opening_id})")
            if opening.get("perimeter_ml") is not None:
                _add_entry(menu, "openings", f"OPENING_PERIMETER_ML({opening_id})")

        aggregates = room.get("opening_aggregates") or {}
        if isinstance(aggregates, dict):
            types = set()
            for key in ("counts_by_type", "area_m2_by_type", "perimeter_ml_by_type", "width_ml_by_type", "height_ml_by_type"):
                entry = aggregates.get(key) or {}
                if isinstance(entry, dict):
                    types.update([_normalize_id(t) for t in entry.keys() if _normalize_id(t)])

            for opening_type in sorted(types):
                _add_entry(menu, "openings", f"OPENING_COUNT({room_id}, opening_type={opening_type})")
                _add_entry(menu, "openings", f"OPENING_AREA_TOTAL_M2({room_id}, opening_type={opening_type})")
                _add_entry(menu, "openings", f"OPENING_PERIMETER_TOTAL_ML({room_id}, opening_type={opening_type})")
                _add_entry(menu, "openings", f"OPENING_WIDTH_TOTAL_ML({room_id}, opening_type={opening_type})")
                _add_entry(menu, "openings", f"OPENING_HEIGHT_TOTAL_ML({room_id}, opening_type={opening_type})")

        # Features (aggregates)
        feature_aggregates = room.get("feature_aggregates") or {}
        if isinstance(feature_aggregates, dict):
            counts = feature_aggregates.get("counts_by_type") or {}
            if isinstance(counts, dict):
                for feature_type in sorted([_normalize_id(t) for t in counts.keys() if _normalize_id(t)]):
                    _add_entry(menu, "features", f"FEATURE_COUNT({room_id}, feature_type={feature_type})")

            qty_sums = feature_aggregates.get("quantity_sums_by_type_and_unit") or {}
            if isinstance(qty_sums, dict):
                for feature_type, unit_map in qty_sums.items():
                    if not isinstance(unit_map, dict):
                        continue
                    feature_type_norm = _normalize_id(feature_type)
                    if not feature_type_norm:
                        continue
                    for unit in sorted([_normalize_id(u).lower() for u in unit_map.keys() if _normalize_id(u)]):
                        _add_entry(
                            menu,
                            "features",
                            f"FEATURE_QTY_SUM({room_id}, feature_type={feature_type_norm}, unit={unit})",
                        )

        # Waste menu (optional)
        waste_rules = room.get("waste_m3_by_rule") or {}
        if isinstance(waste_rules, dict) and waste_rules:
            for rule_id in sorted([_normalize_id(r) for r in waste_rules.keys() if _normalize_id(r)]):
                _add_entry(menu, "waste", f"WASTE_M3({room_id}, {rule_id})")

        all_refs: List[str] = []
        for key in ("surfaces", "details", "openings", "features", "waste"):
            for ref in menu.get(key, []):
                _add_ref(all_refs, ref)

        menu_by_room[room_id] = {
            "room_id": room_id,
            "surfaces": menu["surfaces"],
            "details": menu["details"],
            "openings": menu["openings"],
            "features": menu["features"],
            "waste": menu["waste"],
            "all_quantity_refs": all_refs,
        }

    if not menu_by_room:
        raise RuntimeError("takeoff_menu: no rooms processed")

    return {"rooms": menu_by_room}
