import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Quantity refs include digits in the function name (e.g., FLOOR_M2, WALL_NET_M2).
# The validator must accept these, otherwise it will incorrectly flag valid refs and trigger expensive repairs.
_REF_PATTERN = re.compile(r"^(?P<name>[A-Z0-9_]+)\((?P<args>.*)\)$")


def _normalize_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_quantity_ref(quantity_ref: str) -> Tuple[str, List[str]]:
    if not quantity_ref or not isinstance(quantity_ref, str):
        raise RuntimeError(f"worklist_validator: empty quantity_ref | value={quantity_ref!r}")
    match = _REF_PATTERN.match(quantity_ref.strip())
    if not match:
        raise RuntimeError(f"worklist_validator: invalid quantity_ref format | value={quantity_ref}")
    name = match.group("name")
    args_raw = match.group("args")
    args = [part.strip() for part in (args_raw or "").split(",") if part.strip()]
    return name, args


def infer_unit_family(name: str, args: List[str]) -> Optional[str]:
    if name in ("FLOOR_M2", "CEILING_M2", "WALL_GROSS_M2", "WALL_NET_M2", "OPENINGS_TOTAL_AREA_M2", "OPENING_AREA_M2", "OPENING_AREA_TOTAL_M2"):
        return "m2"
    if name in (
        "PERIMETER_ML",
        "OPENING_PERIMETER_ML",
        "OPENING_PERIMETER_TOTAL_ML",
        "OPENING_WIDTH_TOTAL_ML",
        "OPENING_HEIGHT_TOTAL_ML",
        "SKIRTING_ML",
        "COVING_ML",
        "WINDOW_SILL_ML",
        "DOOR_THRESHOLD_ML",
        "SEALANT_ML",
    ):
        return "ml"
    if name in ("OPENING_COUNT", "FEATURE_COUNT"):
        return "ud"
    if name == "FEATURE_QTY_SUM":
        for arg in args:
            if arg.startswith("unit="):
                return _normalize_id(arg.split("=", 1)[1]).lower()
        return None
    if name == "WASTE_M3":
        return "m3"
    return None


def _index_rooms(rooms: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for room in rooms or []:
        if not isinstance(room, dict):
            continue
        rid = _normalize_id(room.get("room_id") or room.get("cluster_id"))
        if not rid:
            raise RuntimeError(f"worklist_validator: room missing room_id/cluster_id | room={room}")
        if rid in by_id:
            raise RuntimeError(f"worklist_validator: duplicate room_id | room_id={rid}")
        by_id[rid] = room
    return by_id


def _index_openings(rooms_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    by_opening: Dict[str, str] = {}
    for room_id, room in rooms_by_id.items():
        for opening in room.get("openings") or []:
            if not isinstance(opening, dict):
                continue
            oid = _normalize_id(opening.get("opening_id"))
            if not oid:
                raise RuntimeError(f"worklist_validator: opening missing opening_id | room_id={room_id}")
            if oid in by_opening:
                raise RuntimeError(f"worklist_validator: duplicate opening_id | opening_id={oid}")
            by_opening[oid] = room_id
    return by_opening


def validate_worklist_items(
    *,
    items: List[Dict[str, Any]],
    smart_m2_rooms: List[Dict[str, Any]],
    takeoff_menu: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rooms_by_id = _index_rooms(smart_m2_rooms)
    openings_by_id = _index_openings(rooms_by_id)
    menu_rooms = (takeoff_menu or {}).get("rooms") or {}

    failures: List[Dict[str, Any]] = []

    for item in items:
        item_id = item.get("_item_id")
        try:
            room_id = _normalize_id(item.get("room_id"))
            if not room_id or room_id not in rooms_by_id:
                raise RuntimeError(f"unknown room_id | room_id={room_id}")

            quantity_ref = item.get("quantity_ref")
            name, args = parse_quantity_ref(quantity_ref)

            unit = _normalize_id(item.get("unit")).lower()
            expected_unit = infer_unit_family(name, args)
            if not expected_unit:
                raise RuntimeError(f"unsupported quantity_ref family | quantity_ref={quantity_ref}")
            if unit != expected_unit:
                raise RuntimeError(f"unit mismatch | expected={expected_unit} got={unit}")

            if name.startswith("OPENING_") and args:
                opening_arg = _normalize_id(args[0])
                if opening_arg and opening_arg in openings_by_id and openings_by_id[opening_arg] != room_id:
                    raise RuntimeError(f"opening_id mismatch in quantity_ref | opening_id={opening_arg} room_id={room_id}")

            room_menu = menu_rooms.get(room_id) or {}
            menu_refs = room_menu.get("all_quantity_refs") or []
            if quantity_ref not in menu_refs:
                raise RuntimeError(f"quantity_ref not in TAKEOFF_MENU | quantity_ref={quantity_ref} room_id={room_id}")

        except Exception as exc:
            failures.append(
                {
                    "item_id": item_id,
                    "error": str(exc),
                    "item": item,
                }
            )

    return failures
