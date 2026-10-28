import logging
import re
from typing import Any, Dict, Iterable, Tuple

logger = logging.getLogger(__name__)

# Quantity refs include digits in function names (e.g., FLOOR_M2, WALL_NET_M2, OPENING_AREA_TOTAL_M2).
# Parser must accept digits to avoid incorrectly rejecting valid TAKEOFF_MENU refs.
_REF_PATTERN = re.compile(r"^(?P<name>[A-Z0-9_]+)\((?P<args>.*)\)$")


def _normalize_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_args(raw: str) -> list[str]:
    if raw is None:
        return []
    # Split on commas but keep simple; we don't support quoted commas.
    return [part.strip() for part in raw.split(",") if part.strip()]


def _index_rooms_by_id(rooms: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for room in rooms:
        if not isinstance(room, dict):
            continue
        rid = _normalize_id(room.get("room_id") or room.get("cluster_id"))
        if not rid:
            raise RuntimeError(f"quantity_resolver: room missing room_id/cluster_id | room={room}")
        if rid in by_id:
            raise RuntimeError(f"quantity_resolver: duplicate room_id | room_id={rid}")
        by_id[rid] = room
    return by_id


def _index_openings(rooms_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    by_opening: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for room_id, room in rooms_by_id.items():
        openings = room.get("openings") or []
        if not isinstance(openings, list):
            continue
        for opening in openings:
            if not isinstance(opening, dict):
                continue
            oid = _normalize_id(opening.get("opening_id"))
            if not oid:
                raise RuntimeError(
                    f"quantity_resolver: opening missing opening_id | room_id={room_id} | opening={opening}"
                )
            if oid in by_opening:
                raise RuntimeError(f"quantity_resolver: duplicate opening_id | opening_id={oid}")
            by_opening[oid] = (room_id, opening)
    return by_opening


def resolve_quantity_ref(
    quantity_ref: str,
    smart_m2_rooms: Iterable[Dict[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    """
    Resolve a quantity_ref string to a numeric quantity + provenance.

    Supported refs:
    - FLOOR_M2(room_id)
    - CEILING_M2(room_id)
    - PERIMETER_ML(room_id)
    - WALL_GROSS_M2(room_id)
    - OPENINGS_TOTAL_AREA_M2(room_id)
    - WALL_NET_M2(room_id)
    - OPENING_AREA_M2(opening_id)
    - OPENING_PERIMETER_ML(opening_id)
    - OPENING_COUNT(room_id, opening_type=door|window|balcony_door)
    - OPENING_AREA_TOTAL_M2(room_id, opening_type=door|window|balcony_door)
    - OPENING_PERIMETER_TOTAL_ML(room_id, opening_type=door|window|balcony_door)
    - OPENING_WIDTH_TOTAL_ML(room_id, opening_type=...)
    - OPENING_HEIGHT_TOTAL_ML(room_id, opening_type=...)
    - SKIRTING_ML(room_id, variant=gross|net)
    - COVING_ML(room_id)
    - WINDOW_SILL_ML(room_id)
    - DOOR_THRESHOLD_ML(room_id)
    - SEALANT_ML(room_id)
    - FEATURE_COUNT(room_id, feature_type=...)
    - FEATURE_QTY_SUM(room_id, feature_type=..., unit=ml|m2|ud|m3)
    - WASTE_M3(room_id, rule_id)
    """
    if not quantity_ref or not isinstance(quantity_ref, str):
        raise RuntimeError(f"quantity_resolver: empty quantity_ref | value={quantity_ref!r}")

    match = _REF_PATTERN.match(quantity_ref.strip())
    if not match:
        raise RuntimeError(f"quantity_resolver: invalid quantity_ref format | value={quantity_ref}")

    name = match.group("name")
    args = _parse_args(match.group("args"))

    rooms_by_id = _index_rooms_by_id(smart_m2_rooms)
    openings_by_id = _index_openings(rooms_by_id)

    def _room(room_id: str) -> Dict[str, Any]:
        rid = _normalize_id(room_id)
        if not rid or rid not in rooms_by_id:
            raise RuntimeError(f"quantity_resolver: unknown room_id | room_id={room_id}")
        return rooms_by_id[rid]

    if name in ("FLOOR_M2", "CEILING_M2", "PERIMETER_ML", "WALL_GROSS_M2", "OPENINGS_TOTAL_AREA_M2", "WALL_NET_M2"):
        if len(args) != 1:
            raise RuntimeError(f"quantity_resolver: {name} requires 1 arg | ref={quantity_ref}")
        room = _room(args[0])
        key_map = {
            "FLOOR_M2": "estimated_m2",
            "CEILING_M2": "estimated_m2",
            "PERIMETER_ML": "perimeter_m",
            "WALL_GROSS_M2": "wall_gross_m2",
            "OPENINGS_TOTAL_AREA_M2": "openings_total_area_m2",
            "WALL_NET_M2": "wall_net_m2",
        }
        key = key_map[name]
        value = room.get(key)
        if value is None:
            raise RuntimeError(f"quantity_resolver: missing {key} | room_id={args[0]} | ref={quantity_ref}")
        qty = float(value)
        return qty, {"ref": quantity_ref, "room_id": args[0], "source_key": key}

    if name in ("OPENING_AREA_M2", "OPENING_PERIMETER_ML"):
        if len(args) != 1:
            raise RuntimeError(f"quantity_resolver: {name} requires 1 arg | ref={quantity_ref}")
        oid = _normalize_id(args[0])
        if oid not in openings_by_id:
            raise RuntimeError(f"quantity_resolver: unknown opening_id | opening_id={oid}")
        room_id, opening = openings_by_id[oid]
        key = "area_m2" if name == "OPENING_AREA_M2" else "perimeter_ml"
        value = opening.get(key)
        if value is None:
            raise RuntimeError(f"quantity_resolver: missing {key} | opening_id={oid}")
        qty = float(value)
        return qty, {"ref": quantity_ref, "room_id": room_id, "opening_id": oid, "source_key": key}

    if name in (
        "OPENING_COUNT",
        "OPENING_AREA_TOTAL_M2",
        "OPENING_PERIMETER_TOTAL_ML",
        "OPENING_WIDTH_TOTAL_ML",
        "OPENING_HEIGHT_TOTAL_ML",
    ):
        if len(args) < 1:
            raise RuntimeError(f"quantity_resolver: {name} requires room_id | ref={quantity_ref}")
        room = _room(args[0])
        opening_type = None
        for arg in args[1:]:
            if arg.startswith("opening_type="):
                opening_type = arg.split("=", 1)[1].strip()

        aggregates = room.get("opening_aggregates") or {}
        counts_by_type = aggregates.get("counts_by_type") or {}
        area_by_type = aggregates.get("area_m2_by_type") or {}
        perim_by_type = aggregates.get("perimeter_ml_by_type") or {}
        width_by_type = aggregates.get("width_ml_by_type") or {}
        height_by_type = aggregates.get("height_ml_by_type") or {}

        # Deterministic fallback for older Smart M2 rows without aggregates
        if not aggregates:
            openings = room.get("openings") or []
            if not isinstance(openings, list):
                openings = []
            for o in openings:
                if not isinstance(o, dict):
                    continue
                ot = str(o.get("opening_type") or "unknown")
                counts_by_type[ot] = int(counts_by_type.get(ot, 0)) + 1
                width_by_type[ot] = float(width_by_type.get(ot, 0.0)) + float(o.get("width_m") or 0.0)
                height_by_type[ot] = float(height_by_type.get(ot, 0.0)) + float(o.get("height_m") or 0.0)
                area_by_type[ot] = float(area_by_type.get(ot, 0.0)) + float(o.get("area_m2") or 0.0)
                perim_by_type[ot] = float(perim_by_type.get(ot, 0.0)) + float(o.get("perimeter_ml") or 0.0)

        if name == "OPENING_COUNT":
            if opening_type:
                count = float(counts_by_type.get(opening_type, 0))
            else:
                count = float(sum(counts_by_type.values()))
            return count, {"ref": quantity_ref, "room_id": args[0], "opening_type": opening_type}

        if name == "OPENING_AREA_TOTAL_M2":
            if opening_type:
                total_area = float(area_by_type.get(opening_type, 0.0))
            else:
                total_area = float(sum(area_by_type.values()))
            return total_area, {"ref": quantity_ref, "room_id": args[0], "opening_type": opening_type}

        if name == "OPENING_PERIMETER_TOTAL_ML":
            if opening_type:
                total_perim = float(perim_by_type.get(opening_type, 0.0))
            else:
                total_perim = float(sum(perim_by_type.values()))
            return total_perim, {"ref": quantity_ref, "room_id": args[0], "opening_type": opening_type}

        if name == "OPENING_WIDTH_TOTAL_ML":
            if opening_type:
                total_w = float(width_by_type.get(opening_type, 0.0))
            else:
                total_w = float(sum(width_by_type.values()))
            return total_w, {"ref": quantity_ref, "room_id": args[0], "opening_type": opening_type}

        if name == "OPENING_HEIGHT_TOTAL_ML":
            if opening_type:
                total_h = float(height_by_type.get(opening_type, 0.0))
            else:
                total_h = float(sum(height_by_type.values()))
            return total_h, {"ref": quantity_ref, "room_id": args[0], "opening_type": opening_type}

    if name == "WASTE_M3":
        if len(args) != 2:
            raise RuntimeError(f"quantity_resolver: WASTE_M3 requires room_id, rule_id | ref={quantity_ref}")
        room = _room(args[0])
        rule_id = _normalize_id(args[1])
        waste_menu = room.get("waste_m3_by_rule") or {}
        if rule_id not in waste_menu:
            raise RuntimeError(f"quantity_resolver: unknown waste rule_id | room_id={args[0]} rule_id={rule_id}")
        value = (waste_menu.get(rule_id) or {}).get("waste_m3")
        if value is None:
            raise RuntimeError(f"quantity_resolver: missing waste_m3 | room_id={args[0]} rule_id={rule_id}")
        return float(value), {
            "ref": quantity_ref,
            "room_id": args[0],
            "rule_id": rule_id,
        }

    if name in ("SKIRTING_ML", "COVING_ML", "WINDOW_SILL_ML", "DOOR_THRESHOLD_ML", "SEALANT_ML"):
        if len(args) < 1:
            raise RuntimeError(f"quantity_resolver: {name} requires room_id | ref={quantity_ref}")
        room = _room(args[0])
        takeoff = room.get("takeoff_primitives") or {}
        if not isinstance(takeoff, dict):
            raise RuntimeError(f"quantity_resolver: takeoff_primitives missing/invalid | room_id={args[0]}")

        key = None
        extra: Dict[str, Any] = {}
        if name == "SKIRTING_ML":
            variant = "gross"
            for arg in args[1:]:
                if arg.startswith("variant="):
                    variant = arg.split("=", 1)[1].strip()
            if variant not in ("gross", "net"):
                raise RuntimeError(f"quantity_resolver: invalid skirting variant | variant={variant} ref={quantity_ref}")
            key = "skirting_gross_ml" if variant == "gross" else "skirting_net_ml"
            extra["variant"] = variant
        elif name == "COVING_ML":
            key = "coving_ml"
        elif name == "WINDOW_SILL_ML":
            key = "window_sill_total_ml"
        elif name == "DOOR_THRESHOLD_ML":
            key = "door_threshold_total_ml"
        elif name == "SEALANT_ML":
            key = "sealant_total_ml"

        entry = takeoff.get(key) if key else None
        if not isinstance(entry, dict) or entry.get("value") is None:
            raise RuntimeError(f"quantity_resolver: missing takeoff primitive | room_id={args[0]} key={key}")
        qty = float(entry["value"])
        prov = {"ref": quantity_ref, "room_id": args[0], "takeoff_key": key, **extra}
        if "opening_ids" in entry:
            prov["opening_ids"] = entry.get("opening_ids")
        return qty, prov

    if name in ("FEATURE_COUNT", "FEATURE_QTY_SUM"):
        if len(args) < 1:
            raise RuntimeError(f"quantity_resolver: {name} requires room_id | ref={quantity_ref}")
        room = _room(args[0])
        feature_type = None
        unit = None
        for arg in args[1:]:
            if arg.startswith("feature_type="):
                feature_type = arg.split("=", 1)[1].strip()
            if arg.startswith("unit="):
                unit = arg.split("=", 1)[1].strip().lower()
        if not feature_type:
            raise RuntimeError(f"quantity_resolver: {name} requires feature_type=... | ref={quantity_ref}")

        aggs = room.get("feature_aggregates") or {}
        if not isinstance(aggs, dict):
            raise RuntimeError(f"quantity_resolver: feature_aggregates missing/invalid | room_id={args[0]}")

        if name == "FEATURE_COUNT":
            counts = aggs.get("counts_by_type") or {}
            qty = float(counts.get(feature_type, 0))
            prov = {"ref": quantity_ref, "room_id": args[0], "feature_type": feature_type}
            ids = (aggs.get("feature_ids_by_type") or {}).get(feature_type)
            if ids:
                prov["feature_ids"] = ids
            return qty, prov

        # FEATURE_QTY_SUM
        if not unit:
            raise RuntimeError(f"quantity_resolver: FEATURE_QTY_SUM requires unit=... | ref={quantity_ref}")
        sums = (aggs.get("quantity_sums_by_type_and_unit") or {}).get(feature_type) or {}
        if unit not in sums:
            raise RuntimeError(
                f"quantity_resolver: missing FEATURE_QTY_SUM | room_id={args[0]} feature_type={feature_type} unit={unit}"
            )
        qty = float(sums[unit])
        prov = {"ref": quantity_ref, "room_id": args[0], "feature_type": feature_type, "unit": unit}
        ids = ((aggs.get("feature_ids_with_quantity_by_type_and_unit") or {}).get(feature_type) or {}).get(unit)
        if ids:
            prov["feature_ids"] = ids
        return qty, prov

    raise RuntimeError(f"quantity_resolver: unsupported quantity_ref | ref={quantity_ref}")
