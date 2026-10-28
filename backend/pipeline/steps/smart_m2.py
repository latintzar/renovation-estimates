"""
Smart M2 Step (M1)
==================

Estimates room sizes AND dimensions by distributing total property m² across detected rooms.

Uses:
- Total property size (from listing)
- Room clusters (from P1)
- Standard architectural ratios
- Photo counts as spatial clues
- Architectural reasoning for room proportions

Outputs:
- estimated_m2: Total floor area per room
- estimated_height_m: Ceiling height
- estimated_dimensions: {length_m, width_m, aspect_ratio}
- wall_segments: IndoorGML-lite wall segments with lengths and ids
- openings: Structured opening takeoff with wall_id + size
- features: Fixtures/built-ins anchored to the room

Model: gemini-3-pro-preview via alias "pro" (architectural reasoning)

INTEGRATION:
This step runs AFTER clustering (P1) but BEFORE PIR generation.
The output is integrated into the PIR prompt so Gemini can reference
specific wall dimensions when describing room conditions.
"""

import logging
import json
import os
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..orchestrator import PipelineOrchestrator

import yaml

from ..gemini_client import call_gemini_json, fetch_images_batch

logger = logging.getLogger(__name__)

WASTE_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # lean-mvp/backend
    "pricing",
    "data",
    "waste_volume_rules.yaml",
)


def _load_waste_rules() -> Dict[str, Any]:
    """Load waste volume derivation rules for provenance-safe m3 menus."""
    if not os.path.exists(WASTE_RULES_PATH):
        raise FileNotFoundError(f"waste rules missing: {WASTE_RULES_PATH}")
    with open(WASTE_RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "defaults" not in data or "rules" not in data:
        raise ValueError(f"invalid waste rules schema in {WASTE_RULES_PATH}")
    return data


def _compute_room_waste_m3_menu(room: Dict[str, Any], waste_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a per-room menu of potential waste volumes (m3) by rule id.

    IMPORTANT:
    - This is pure quantities: derived deterministically from room geometry primitives.
    - Delta scopes later selects which rule applies by referencing WASTE_M3(room_id, rule_id).
    """
    estimated_m2 = float(room.get("estimated_m2") or 0)
    height_m = float(room.get("estimated_height_m") or 0)
    perimeter_m = float(room.get("perimeter_m") or 0)

    # If wall_area_m2 isn't present, derive it from perimeter×height (approx, ignoring openings)
    wall_area_m2 = room.get("wall_area_m2")
    if wall_area_m2 is None:
        if perimeter_m > 0 and height_m > 0:
            wall_area_m2 = perimeter_m * height_m
        else:
            wall_area_m2 = 0
    wall_area_m2 = float(wall_area_m2 or 0)

    thickness = (waste_rules.get("defaults") or {}).get("thickness_m") or {}
    bulking = (waste_rules.get("defaults") or {}).get("bulking_factor") or {}

    def rule_value(base_m2: float, thickness_key: str, bulking_key: str) -> Dict[str, Any]:
        t = float(thickness.get(thickness_key))
        b = float(bulking.get(bulking_key))
        waste_m3 = base_m2 * t * b
        return {
            "base_m2": round(base_m2, 3),
            "thickness_key": thickness_key,
            "thickness_m": t,
            "bulking_key": bulking_key,
            "bulking_factor": b,
            "waste_m3": round(waste_m3, 3),
            "formula": f"{base_m2:.3f} * {t} * {b} = {waste_m3:.3f}",
        }

    menu: Dict[str, Any] = {}
    for rule in waste_rules.get("rules") or []:
        rule_id = rule.get("id")
        if not rule_id:
            continue

        # Determine base by input primitive
        inputs = rule.get("inputs") or []
        base_kind = inputs[0] if inputs else ""
        if base_kind.startswith("FLOOR_M2"):
            base_m2 = estimated_m2
        elif base_kind.startswith("WALL_M2"):
            base_m2 = wall_area_m2
        else:
            # Unknown base; skip (fail-loud not needed here, it's optional menu)
            continue

        # Read keys from the rule's output formula string (we use the agreed defaults keys)
        output = rule.get("output") or {}
        waste_type = output.get("waste_type") or "mixed_rubble"

        if rule_id in ("floor_tile_rubble", "wall_tile_rubble"):
            thickness_key = "floor_finish_tile" if rule_id == "floor_tile_rubble" else "wall_tile"
            bulking_key = "ceramics_masonry"
        elif rule_id in ("floor_screed_rubble", "wall_plaster_rubble"):
            thickness_key = "floor_screed" if rule_id == "floor_screed_rubble" else "wall_plaster"
            bulking_key = "mixed_rubble"
        else:
            # Conservative fallback
            thickness_key = "floor_finish_tile"
            bulking_key = "mixed_rubble"

        menu[rule_id] = {
            "waste_type": waste_type,
            **rule_value(base_m2=base_m2, thickness_key=thickness_key, bulking_key=bulking_key),
        }

    return menu


def _compute_opening_derived_fields(opening: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add deterministic derived fields for an opening: area_m2, perimeter_ml.

    Smart M2 (LLM) provides width_m/height_m as estimates; we compute the geometry.
    """
    width_m = opening.get("width_m")
    height_m = opening.get("height_m")
    if width_m is None or height_m is None:
        return opening
    try:
        w = float(width_m)
        h = float(height_m)
    except Exception:
        return opening
    if w <= 0 or h <= 0:
        return opening

    opening["area_m2"] = round(w * h, 3)
    opening["perimeter_ml"] = round(2 * (w + h), 3)
    return opening


def _compute_wall_segment_derived_fields(room: Dict[str, Any]) -> None:
    wall_segments = room.get("wall_segments")
    if not isinstance(wall_segments, list) or not wall_segments:
        raise RuntimeError(
            f"smart_m2: missing wall_segments | room={room.get('cluster_name') or room.get('room_id')}"
        )

    openings = room.get("openings") or []
    if not isinstance(openings, list):
        openings = []

    openings_by_wall: Dict[str, List[Dict[str, Any]]] = {}
    for opening in openings:
        wall_id = opening.get("wall_id")
        if not wall_id:
            raise RuntimeError(
                f"smart_m2: opening missing wall_id | room={room.get('cluster_name') or room.get('room_id')} | opening={opening}"
            )
        openings_by_wall.setdefault(str(wall_id), []).append(opening)

    seen_wall_ids = set()
    for segment in wall_segments:
        wall_id = segment.get("wall_id")
        if not wall_id:
            raise RuntimeError(
                f"smart_m2: wall_segment missing wall_id | room={room.get('cluster_name') or room.get('room_id')} | segment={segment}"
            )
        wall_id = str(wall_id)
        if wall_id in seen_wall_ids:
            raise RuntimeError(
                f"smart_m2: duplicate wall_id in room | room={room.get('cluster_name') or room.get('room_id')} | wall_id={wall_id}"
            )
        seen_wall_ids.add(wall_id)

        length_m = segment.get("length_m")
        height_m = segment.get("height_m") or room.get("estimated_height_m")
        try:
            length = float(length_m)
            height = float(height_m)
        except Exception as exc:
            raise RuntimeError(
                f"smart_m2: invalid wall_segment dimensions | wall_id={wall_id} | length_m={length_m} | height_m={height_m}"
            ) from exc
        if length <= 0 or height <= 0:
            raise RuntimeError(
                f"smart_m2: non-positive wall_segment dims | wall_id={wall_id} | length_m={length} | height_m={height}"
            )

        wall_m2 = round(length * height, 3)
        openings_area = 0.0
        for opening in openings_by_wall.get(wall_id, []):
            area = opening.get("area_m2")
            if area is None:
                _compute_opening_derived_fields(opening)
                area = opening.get("area_m2") or 0
            openings_area += float(area or 0)

        segment["wall_segment_m2"] = wall_m2
        segment["wall_segment_net_m2"] = round(max(wall_m2 - openings_area, 0), 3)


def _compute_room_level_primitives(room: Dict[str, Any]) -> None:
    """
    Deterministic, room-level primitives used by the resolver.

    IMPORTANT:
    - These DO NOT depend on opening positions.
    - These are the authoritative quantities for downstream costing.
    """
    openings = room.get("openings") or []
    if not isinstance(openings, list):
        openings = []

    # Fail loud: if openings exist, they must be measurable (we need net wall m2 to be trustworthy).
    for op in openings:
        if not isinstance(op, dict):
            continue
        w = op.get("width_m")
        h = op.get("height_m")
        if w is None or h is None:
            raise RuntimeError(
                f"smart_m2: opening missing width_m/height_m | room={room.get('cluster_name') or room.get('room_id')} | opening={op}"
            )
        try:
            wf = float(w)
            hf = float(h)
        except Exception as exc:
            raise RuntimeError(
                f"smart_m2: opening width_m/height_m not numeric | room={room.get('cluster_name') or room.get('room_id')} | width_m={w} | height_m={h} | opening={op}"
            ) from exc
        if wf <= 0 or hf <= 0:
            raise RuntimeError(
                f"smart_m2: opening width_m/height_m non-positive | room={room.get('cluster_name') or room.get('room_id')} | width_m={wf} | height_m={hf} | opening={op}"
            )

    openings_total_area_m2 = 0.0
    for op in openings:
        if not isinstance(op, dict):
            continue
        area = op.get("area_m2")
        if area is None:
            _compute_opening_derived_fields(op)
            area = op.get("area_m2")
        openings_total_area_m2 += float(area or 0)

    # Prefer gross wall area from perimeter×height (position-free), fallback to wall_area_m2, last resort sum segments.
    wall_gross_m2: float | None = None
    try:
        perimeter_m = float(room.get("perimeter_m") or 0)
        height_m = float(room.get("estimated_height_m") or 0)
        if perimeter_m > 0 and height_m > 0:
            wall_gross_m2 = perimeter_m * height_m
    except Exception:
        wall_gross_m2 = None

    if wall_gross_m2 is None:
        try:
            wall_area_m2 = float(room.get("wall_area_m2") or 0)
            if wall_area_m2 > 0:
                wall_gross_m2 = wall_area_m2
        except Exception:
            wall_gross_m2 = None

    if wall_gross_m2 is None:
        wall_segments = room.get("wall_segments") or []
        if not isinstance(wall_segments, list) or not wall_segments:
            raise RuntimeError(
                f"smart_m2: cannot derive wall_gross_m2 (missing perimeter/height/wall_area_m2 and missing wall_segments) | room={room.get('cluster_name') or room.get('room_id')}"
            )
        # Ensure derived fields exist before summing.
        _compute_wall_segment_derived_fields(room)
        wall_gross_m2 = 0.0
        for seg in wall_segments:
            if not isinstance(seg, dict):
                continue
            wall_gross_m2 += float(seg.get("wall_segment_m2") or 0)

    room["wall_gross_m2"] = round(float(wall_gross_m2), 3)
    room["openings_total_area_m2"] = round(openings_total_area_m2, 3)
    room["wall_net_m2"] = round(max(float(wall_gross_m2) - openings_total_area_m2, 0.0), 3)

    # Make the contract explicit for downstream steps.
    room["calc_authority"] = {
        "authoritative": [
            "estimated_m2",
            "estimated_height_m",
            "perimeter_m",
            "wall_gross_m2",
            "openings_total_area_m2",
            "wall_net_m2",
            "openings[].width_m",
            "openings[].height_m",
            "openings[].area_m2",
        ],
        "non_authoritative": [
            "openings[].offset",
            "wall_segments[].features (semantic labels only)",
            "3d_visualization_geometry",
        ],
    }


def _compute_opening_aggregates(room: Dict[str, Any]) -> None:
    """
    Deterministically precompute opening aggregates so downstream can "choose from a menu"
    without re-doing arithmetic in prompts.

    We intentionally keep these position-free and provenance-safe:
    - counts, area totals, perimeter totals, width totals, height totals
    - grouped by opening_type
    """
    openings = room.get("openings") or []
    if not isinstance(openings, list):
        openings = []

    counts_by_type: Dict[str, int] = {}
    area_m2_by_type: Dict[str, float] = {}
    perimeter_ml_by_type: Dict[str, float] = {}
    width_ml_by_type: Dict[str, float] = {}
    height_ml_by_type: Dict[str, float] = {}
    opening_ids_by_type: Dict[str, List[str]] = {}

    for op in openings:
        if not isinstance(op, dict):
            continue
        opening_type = str(op.get("opening_type") or "unknown")
        counts_by_type[opening_type] = counts_by_type.get(opening_type, 0) + 1
        oid = str(op.get("opening_id") or "").strip()
        if oid:
            opening_ids_by_type.setdefault(opening_type, []).append(oid)

        # Ensure derived fields exist
        _compute_opening_derived_fields(op)

        try:
            w = float(op.get("width_m") or 0)
            h = float(op.get("height_m") or 0)
            area = float(op.get("area_m2") or 0)
            perim = float(op.get("perimeter_ml") or 0)
        except Exception as exc:
            raise RuntimeError(
                f"smart_m2: opening has non-numeric dims/derived fields | room={room.get('cluster_name') or room.get('room_id')} | opening={op}"
            ) from exc

        area_m2_by_type[opening_type] = area_m2_by_type.get(opening_type, 0.0) + area
        perimeter_ml_by_type[opening_type] = perimeter_ml_by_type.get(opening_type, 0.0) + perim
        width_ml_by_type[opening_type] = width_ml_by_type.get(opening_type, 0.0) + w
        height_ml_by_type[opening_type] = height_ml_by_type.get(opening_type, 0.0) + h

    room["opening_aggregates"] = {
        "counts_by_type": counts_by_type,
        "area_m2_by_type": {k: round(v, 3) for k, v in area_m2_by_type.items()},
        "perimeter_ml_by_type": {k: round(v, 3) for k, v in perimeter_ml_by_type.items()},
        "width_ml_by_type": {k: round(v, 3) for k, v in width_ml_by_type.items()},
        "height_ml_by_type": {k: round(v, 3) for k, v in height_ml_by_type.items()},
        "opening_ids_by_type": opening_ids_by_type,
    }


def _compute_feature_aggregates(room: Dict[str, Any]) -> None:
    """
    Deterministically precompute feature aggregates from Smart M2 `features[]`.

    WHY:
    - MEP + equipment items (e.g., radiators, boiler, electrical panel, countertop runs) should be selectable
      without the LLM doing arithmetic.

    We aggregate:
    - counts_by_type
    - quantity_sums_by_type_and_unit (e.g., countertop_run ml total)
    """
    features = room.get("features") or []
    if not isinstance(features, list):
        features = []

    counts_by_type: Dict[str, int] = {}
    quantity_sums: Dict[str, Dict[str, float]] = {}
    feature_ids_by_type: Dict[str, List[str]] = {}
    feature_ids_with_quantity_by_type_and_unit: Dict[str, Dict[str, List[str]]] = {}

    for feat in features:
        if not isinstance(feat, dict):
            continue
        ftype = str(feat.get("feature_type") or "unknown")
        counts_by_type[ftype] = counts_by_type.get(ftype, 0) + 1
        fid = str(feat.get("feature_id") or "").strip()
        if fid:
            feature_ids_by_type.setdefault(ftype, []).append(fid)

        qty = feat.get("quantity")
        if not isinstance(qty, dict):
            continue
        unit = str(qty.get("unit") or "").strip().lower()
        val = qty.get("value")
        if not unit or val is None:
            continue
        try:
            vf = float(val)
        except Exception as exc:
            raise RuntimeError(
                f"smart_m2: feature quantity value not numeric | room={room.get('cluster_name') or room.get('room_id')} | feature={feat}"
            ) from exc

        by_unit = quantity_sums.setdefault(ftype, {})
        by_unit[unit] = by_unit.get(unit, 0.0) + vf
        if fid:
            feature_ids_with_quantity_by_type_and_unit.setdefault(ftype, {}).setdefault(unit, []).append(fid)

    room["feature_aggregates"] = {
        "counts_by_type": counts_by_type,
        "quantity_sums_by_type_and_unit": {
            ftype: {unit: round(v, 3) for unit, v in by_unit.items()}
            for ftype, by_unit in quantity_sums.items()
        },
        "feature_ids_by_type": feature_ids_by_type,
        "feature_ids_with_quantity_by_type_and_unit": feature_ids_with_quantity_by_type_and_unit,
    }


def _compute_takeoff_primitives(room: Dict[str, Any]) -> None:
    """
    A deterministic, provenance-friendly "menu" of common quantities used across the 6 dimensions.

    RULE:
    - Only include quantities we can compute from Smart M2 primitives (m2/ml/count/m3).
    - No geometry-position dependence.
    - Every entry includes the upstream keys + contributing IDs (openings/features) where applicable.
    """
    perimeter_m = float(room.get("perimeter_m") or 0.0)
    floor_m2 = float(room.get("estimated_m2") or 0.0)
    ceiling_m2 = floor_m2
    wall_gross_m2 = float(room.get("wall_gross_m2") or 0.0)
    openings_total_area_m2 = float(room.get("openings_total_area_m2") or 0.0)
    wall_net_m2 = float(room.get("wall_net_m2") or 0.0)

    opening_aggs = room.get("opening_aggregates") or {}
    width_by_type = opening_aggs.get("width_ml_by_type") or {}
    perim_by_type = opening_aggs.get("perimeter_ml_by_type") or {}
    ids_by_type = opening_aggs.get("opening_ids_by_type") or {}

    floor_opening_types = {"door", "balcony_door"}
    floor_opening_width_total_ml = 0.0
    floor_opening_ids: List[str] = []
    for ot in floor_opening_types:
        floor_opening_width_total_ml += float(width_by_type.get(ot, 0.0) or 0.0)
        floor_opening_ids.extend(ids_by_type.get(ot) or [])

    skirting_gross_ml = perimeter_m
    skirting_net_ml = max(perimeter_m - floor_opening_width_total_ml, 0.0)

    window_sill_total_ml = float(width_by_type.get("window", 0.0) or 0.0)
    window_ids = ids_by_type.get("window") or []

    door_threshold_total_ml = float(width_by_type.get("door", 0.0) or 0.0) + float(width_by_type.get("balcony_door", 0.0) or 0.0)

    # Perimeter-based "detail runs" (useful across dims: joinery, hygiene baseline, weatherproofing)
    openings_perimeter_windows_ml = float(perim_by_type.get("window", 0.0) or 0.0)
    openings_perimeter_doors_ml = float(perim_by_type.get("door", 0.0) or 0.0) + float(perim_by_type.get("balcony_door", 0.0) or 0.0)
    sealant_total_ml = openings_perimeter_windows_ml + openings_perimeter_doors_ml

    room["takeoff_primitives"] = {
        "floor_finish_m2": {
            "value": round(floor_m2, 3),
            "unit": "m2",
            "computed_from": ["estimated_m2"],
        },
        "ceiling_finish_m2": {
            "value": round(ceiling_m2, 3),
            "unit": "m2",
            "computed_from": ["estimated_m2"],
        },
        "wall_paint_m2": {
            "value": round(wall_net_m2, 3),
            "unit": "m2",
            "computed_from": ["wall_net_m2"],
        },
        "wall_gross_m2": {
            "value": round(wall_gross_m2, 3),
            "unit": "m2",
            "computed_from": ["wall_gross_m2"],
        },
        "openings_total_area_m2": {
            "value": round(openings_total_area_m2, 3),
            "unit": "m2",
            "computed_from": ["openings_total_area_m2"],
            "opening_ids_by_type": ids_by_type,
        },
        "room_perimeter_ml": {
            "value": round(perimeter_m, 3),
            "unit": "ml",
            "computed_from": ["perimeter_m"],
        },
        "skirting_gross_ml": {
            "value": round(skirting_gross_ml, 3),
            "unit": "ml",
            "computed_from": ["perimeter_m"],
        },
        "skirting_net_ml": {
            "value": round(skirting_net_ml, 3),
            "unit": "ml",
            "computed_from": ["perimeter_m", "opening_aggregates.width_ml_by_type(door/balcony_door)"],
            "opening_ids": floor_opening_ids,
        },
        "coving_ml": {
            "value": round(perimeter_m, 3),
            "unit": "ml",
            "computed_from": ["perimeter_m"],
        },
        "window_sill_total_ml": {
            "value": round(window_sill_total_ml, 3),
            "unit": "ml",
            "computed_from": ["opening_aggregates.width_ml_by_type(window)"],
            "opening_ids": window_ids,
        },
        "door_threshold_total_ml": {
            "value": round(door_threshold_total_ml, 3),
            "unit": "ml",
            "computed_from": ["opening_aggregates.width_ml_by_type(door/balcony_door)"],
            "opening_ids": floor_opening_ids,
        },
        "openings_perimeter_windows_ml": {
            "value": round(openings_perimeter_windows_ml, 3),
            "unit": "ml",
            "computed_from": ["opening_aggregates.perimeter_ml_by_type(window)"],
            "opening_ids": window_ids,
        },
        "openings_perimeter_doors_ml": {
            "value": round(openings_perimeter_doors_ml, 3),
            "unit": "ml",
            "computed_from": ["opening_aggregates.perimeter_ml_by_type(door/balcony_door)"],
            "opening_ids": floor_opening_ids,
        },
        "sealant_total_ml": {
            "value": round(sealant_total_ml, 3),
            "unit": "ml",
            "computed_from": ["openings_perimeter_windows_ml", "openings_perimeter_doors_ml"],
            "opening_ids": list(dict.fromkeys([*window_ids, *floor_opening_ids])),
        },
    }


# =============================================================================
# PROMPT
# =============================================================================

def get_smart_m2_prompt(total_m2: float, clusters: list, listing_context: str) -> str:
    """Build prompt for Smart M2 estimation with IndoorGML-lite output."""
    # Build cluster summaries
    cluster_summaries = []
    for c in clusters:
        cluster_summaries.append({
            "cluster_id": c.get("cluster_id") or c.get("id") or "Unknown",
            "name": c.get("cluster_name") or c.get("room_name") or c.get("cluster_id", "Unknown"),
            "room_type": c.get("room_type", "room"),
            "photo_count": len(c.get("photo_urls", [])),
        })
    
    return f"""You are an expert architect estimating room sizes AND dimensions from a floor plan mental model.

{listing_context}

INPUTS:
- Total Property Size: {total_m2} m²
- Detected Rooms (Clusters): {json.dumps(cluster_summaries, indent=2)}

PHOTOS PROVIDED:
The user message includes ALL cluster photos (in the exact order shown in PHOTO INDEX MAP).
Use the photos to ground:
- finish_hints (floor/wall/ceiling finish types)
- measurable_features (kitchen islands, countertop runs, shower screens, wardrobes, etc.)
- (optional) a conservative depth-class choice for demolition waste assumptions (tile vs screed vs plaster)

TASK:

IMPORTANT FILTERING:
- Ignore any cluster with room_type "exterior" or "common_area" (building facade, lobby, pool, etc.). These are not part of the unit.
- Do NOT ignore balcony/terrace/patio/garden clusters that belong to the property.

CRITICAL - EXACT CLUSTER_IDs:
You MUST use these EXACT cluster_id values (no modifications, no normalizations, no removing slashes):
{", ".join([f'"{c.get("cluster_id") or c.get("id")}"' for c in clusters if c.get("room_type") not in ("exterior", "common_area")])}

1. DISTRIBUTE THE TOTAL M² across detected rooms:
   - Use standard architectural ratios:
     * Living room/Salon: typically largest (20-35% of total)
     * Kitchen: 8-15% of total
     * Master bedroom: 12-18% of total
     * Secondary bedrooms: 8-14% each
     * Bathrooms: 4-8% each
     * Terrace/Balcony: varies
   - Use photo counts as spatial clues (more photos often = larger space)
   - Account for walls/circulation (~10-15% of total)

2. ESTIMATE ROOM DIMENSIONS (length × width):
   Think about realistic room proportions. Most rooms are not perfect squares.
   - Bedrooms: often 3:4 or 2:3 aspect ratio
   - Living rooms: can be longer (2:3 to 1:2)
   - Kitchens: varies widely, often galley (long/narrow) or square
   - Bathrooms: typically compact, often 2:3 or more narrow
   
   The length × width should multiply to approximately the estimated_m2.
   ROUND to nearest 0.5m (e.g., 4.0m × 3.5m = 14m², not 4.2m × 3.8m).

3. NAME THE WALLS with ANCHOR POINTS (LABELS ONLY):
   For each room, identify walls by their ORIENTATION and FEATURES:
   - "window_wall" / "pared del ventanal" — the wall with windows/balcony access
   - "entrance_wall" / "pared de entrada" — where you enter from the hallway
   - "long_wall" / "pared larga" — the longest continuous wall
   - "back_wall" / "pared del fondo" — opposite the entrance
   
   For each wall, add VISUAL ANCHORS in the 'features' list:
   - Apertures: "window", "balcony_access", "door", "sliding_door"
   - Built-ins: "closet_space", "shelving", "radiator", "air_conditioning"
   - Fixtures: "sink", "countertop", "appliances", "mirror"
   - Orientation hints: "street_facing", "courtyard_facing", "interior"
   
   WHY THIS MATTERS:
   - These wall_ids are stable references so PIR / Delta Scopes can say “opening_id X is on wall_id w1”.
   - The exact wall geometry and opening POSITION are NOT authoritative. We only rely on totals for quantities.
   
   FLOOR PLAN NOTE: If a floor plan image was provided, it can help you avoid missing openings.
   
   ROUNDING: Round ALL dimensions to the nearest 0.5 meter (half-meter precision).
   Examples: 3.7m → 3.5m, 4.2m → 4.0m, 5.8m → 6.0m
   This reflects the estimation nature of the task.

4. ESTIMATE CEILING HEIGHT (meters):
   - Standard modern: 2.5m
   - Older buildings with high ceilings: 2.8-3.2m
   - False ceilings (Kitchen/Bath): 2.3-2.4m

5. FINISH + TAKEOFF HINTS (for downstream quantities, keep it conservative):
   For each room, add:
   - finish_hints:
     * floor_finish: one of ["tile", "wood", "laminate", "stone", "concrete", "unknown"]
     * wall_finish: one of ["paint", "tile", "mixed", "unknown"]
     * ceiling_finish: one of ["paint", "false_ceiling", "unknown"]
     * reasoning: 1 sentence, based on room_type and typical Spanish apartment conventions
  - features (REQUIRED, may be empty): a short list of any fixtures/built-ins that could help later takeoff.
    Only include if likely and useful (do not list furniture/decor).
    Examples:
      * countertop_run (unit=ml)
      * island_footprint (unit=m2)
      * shower_screen (unit=ml)
      * wardrobe_run (unit=ml)
    Each feature should include:
      * feature_id (unique in room, e.g., "feature_1")
      * feature_type (string)
      * room_id (same as cluster_id)
      * wall_id (nullable)
      * opening_id (nullable)
      * quantity: {{ "unit": "ml"|"m2"|"ud", "value": number }} or null
      * photo_indices
      * confidence: low|medium|high|unknown

6. STRUCTURED OPENINGS TAKEOFF (REQUIRED):
   For each room, list the significant openings you can see or strongly infer from the cluster photos:
   - doors and windows (including balcony sliding doors)
   - for each opening include:
     * opening_id (unique in room, e.g., "cocina_1_window_1")
     * opening_type: one of ["window","door","sliding_door","balcony_door","unknown"]
     * wall_id: which wall segment this opening belongs to (e.g., "w1")
     * width_m and height_m (estimate; round to nearest 0.1m; use conservative defaults if needed)
     * sill_height_m (0 for doors; window sill height for windows)
     * confidence: low|medium|high|unknown
     * photo_indices: list of integers referencing PHOTO INDEX MAP items that show this opening
     * defaulted: true/false (true if you used a default size rather than a visual estimate)
     * notes: short phrase (e.g., "appears to be standard interior door")
   IMPORTANT: This is the canonical openings takeoff used for BOQ quantities (m² openings).

7. INDOORGML-LITE WALL SEGMENTS (REQUIRED):
   For each room, output wall segments as a simple ordered list of wall ids:
   - wall_id: "w1", "w2", ... (unique within room)
   - length_m (rounded to nearest 0.5m)
   - height_m (use estimated_height_m unless you have a reason to vary)
   - features[] (short tags like "window", "door", "radiator", "street_facing")
   - photo_indices[] (if any)

OUTPUT JSON:
{{
  "rooms": [
    {{
      "room_id": "salon_comedor",  // MUST match cluster_id exactly
      "cluster_name": "Salón",
      "cluster_id": "salon_comedor",  // MUST match cluster_id exactly
      "estimated_m2": 24,
      "estimated_dimensions": {{
        "length_m": 6.0,
        "width_m": 4.0,
        "aspect_ratio": "elongated",
        "dimension_confidence": "medium"
      }},
      "wall_segments": [
        {{"wall_id": "w1", "length_m": 6.0, "height_m": 2.5, "features": ["window", "balcony_access", "street_facing"], "photo_indices": [2,3]}},
        {{"wall_id": "w2", "length_m": 4.0, "height_m": 2.5, "features": ["door"], "photo_indices": [1]}},
        {{"wall_id": "w3", "length_m": 6.0, "height_m": 2.5, "features": ["radiator"], "photo_indices": []}},
        {{"wall_id": "w4", "length_m": 4.0, "height_m": 2.5, "features": [], "photo_indices": []}}
      ],
      "estimated_height_m": 2.5,
      "perimeter_m": 20,
      "wall_area_m2": 50,
      "openings": [
        {{"opening_id": "salon_1_window_1", "opening_type": "window", "wall_id": "w1", "width_m": 1.5, "height_m": 1.2, "sill_height_m": 0.9, "confidence": "low", "photo_indices": [1], "defaulted": true, "notes": "standard window assumption"}}
      ],
      "finish_hints": {{
        "floor_finish": "tile",
        "wall_finish": "paint",
        "ceiling_finish": "paint",
        "reasoning": "Kitchen/bathrooms in this housing type commonly have tiled floors and painted walls."
      }},
      "features": [
        {{"feature_id": "feature_1", "feature_type": "countertop_run", "room_id": "salon_1", "wall_id": null, "opening_id": null, "quantity": {{"unit": "ml", "value": 3.0}}, "photo_indices": [4], "confidence": "low"}}
      ],
      "confidence": "high",
      "reasoning": "Central living space, largest photo coverage, likely elongated layout"
    }},
    {{
      "cluster_name": "Cocina",
      "cluster_id": "cocina_1",
      "estimated_m2": 12,
      "estimated_dimensions": {{
        "length_m": 4.0,
        "width_m": 3.0,
        "aspect_ratio": "rectangular",
        "dimension_confidence": "medium"
      }},
      "wall_segments": [
        {{"wall_id": "w1", "length_m": 4.0, "height_m": 2.5, "features": ["countertop", "sink", "window"], "photo_indices": []}},
        {{"wall_id": "w2", "length_m": 3.0, "height_m": 2.5, "features": ["appliances"], "photo_indices": []}},
        {{"wall_id": "w3", "length_m": 3.0, "height_m": 2.5, "features": ["door"], "photo_indices": []}}
      ],
      "estimated_height_m": 2.5,
      "perimeter_m": 14,
      "wall_area_m2": 35,
      "openings": [
        {{"opening_id": "cocina_1_window_1", "opening_type": "window", "wall_id": "w1", "width_m": 1.2, "height_m": 1.0, "sill_height_m": 1.0, "confidence": "low", "photo_indices": [1], "defaulted": true, "notes": "small kitchen window assumption"}}
      ],
      "finish_hints": {{
        "floor_finish": "tile",
        "wall_finish": "mixed",
        "ceiling_finish": "paint",
        "reasoning": "Kitchens often have tiled splashback areas with the remainder painted."
      }},
      "features": [],
      "confidence": "medium",
      "reasoning": "Standard kitchen proportions for apartment of this size"
    }}
  ],
  "circulation_and_walls_m2": 12,
  "total_check": {total_m2},
  "dimension_methodology": "Estimated from total m² using standard architectural proportions and half-meter rounding"
}}

CRITICAL VALIDATION:
- The sum of all room m² plus circulation_and_walls_m2 MUST equal exactly {total_m2}
- Each room's length_m × width_m should approximately equal its estimated_m2
- perimeter_m = 2 × (length_m + width_m)
- wall_area_m2 = perimeter_m × estimated_height_m (approximate, ignoring openings)
- Every room must include an "openings" list (can be empty if none observed)
- Every room must include "wall_segments" with unique wall_id values
- Every opening must reference a valid wall_id from wall_segments
- Every room must include "features" (can be empty)
- room_id and cluster_id MUST match the input cluster_id exactly (no invented ids)

Return ONLY valid JSON."""


def get_smart_m2_single_room_prompt(*, cluster: Dict[str, Any], listing_context: str) -> str:
    """
    Single-room Smart M2 prompt.

    WHY:
    - Isolating one cluster reduces cognitive load and improves openings recall.
    - Missing an opening is worse than adding a low-confidence opening with clear notes.
    """
    cluster_id = cluster.get("cluster_id") or cluster.get("id") or "unknown"
    cluster_name = cluster.get("cluster_name") or cluster.get("room_name") or cluster_id
    room_type = cluster.get("room_type", "room")
    photo_count = len(cluster.get("photo_urls", []) or [])

    return f"""You are a senior architect doing a structured room takeoff from photos.

WHY THIS MATTERS:
We need a room-local, auditable reference graph (IndoorGML-lite) and an openings list (doors/windows) that is as complete as possible.
Missing an opening is worse than adding a low-confidence one with clear provenance notes.

{listing_context}

ROOM CLUSTER:
- cluster_id: {cluster_id}
- cluster_name: {cluster_name}
- room_type: {room_type}
- photo_count: {photo_count}

PHOTO INDEX MAP (same order as images):
1..N correspond to the photos provided for THIS room cluster only.

TASK:
Build ONE room object for this cluster. Be exhaustive about openings:
- For each photo, ask yourself: "Do I see a door? a balcony door? a window? a glass partition?"
- If you suspect an opening exists but you cannot size it, include it with confidence="low" and defaulted=true, and explain in notes.
- If you are uncertain whether two photos show the same opening, be explicit and either merge (with a note) or keep separate with low confidence.

Return ONLY valid JSON (no prose, no markdown, no code fences):
{{
  "room": {{
    "room_id": "{cluster_id}",
    "cluster_id": "{cluster_id}",
    "cluster_name": "{cluster_name}",
    "room_type": "{room_type}",

    "estimated_m2": 0,
    "estimated_dimensions": {{
      "length_m": 0,
      "width_m": 0,
      "aspect_ratio": "rectangular|L_shaped|open_plan|irregular|unknown",
      "dimension_confidence": "low|medium|high"
    }},
    "estimated_height_m": 0,
    "perimeter_m": 0,
    "wall_area_m2": 0,

    "wall_segments": [
      {{
        "wall_id": "w1",
        "length_m": 0,
        "height_m": 0,
        "features": [],
        "photo_indices": []
      }}
    ],

    "openings": [
      {{
        "opening_id": "unique_id_string",
        "opening_type": "door|window|balcony_door|sliding_door|archway|unknown",
        "wall_id": "w1",
        "width_m": 0,
        "height_m": 0,
        "sill_height_m": 0,
        "confidence": "low|medium|high",
        "photo_indices": [],
        "defaulted": false,
        "notes": "brief evidence + what you’re unsure about, if anything"
      }}
    ],

    "finish_hints": {{
      "floor_finish": "tile|wood|laminate|concrete|stone|unknown",
      "wall_finish": "paint|tile|wood|mixed|unknown",
      "ceiling_finish": "paint|tile|wood|mixed|unknown",
      "reasoning": "short"
    }},

    "features": [
      {{
        "feature_id": "unique_id_string",
        "feature_type": "radiator|boiler|electrical_panel|countertop_run|sink|sanitary_ware|unknown",
        "room_id": "{cluster_id}",
        "wall_id": "w1",
        "opening_id": null,
        "quantity": {{"unit": "ud|ml|m2", "value": 0}},
        "photo_indices": [],
        "confidence": "low|medium|high"
      }}
    ],

    "confidence": "low|medium|high",
    "reasoning": "short"
  }}
}}"""


# =============================================================================
# STEP HANDLER
# =============================================================================

async def run_m1_smart_m2(
    orchestrator: "PipelineOrchestrator",
    listing_id: int,
    *,
    persist_to_db: bool = True,
    focus_cluster_ids: list[str] | None = None,
) -> Dict[str, Any]:
    """
    M1: Estimate room sizes from total property m².
    
    Reads: listings, photo_clusters
    Writes: smart_m2 (only when persist_to_db=True)
    """
    logger.info(f"📐 M1: Smart M2 estimation for listing {listing_id}")
    
    # Get listing data
    listing = await orchestrator.db.get_listing(listing_id)
    if not listing:
        raise ValueError(f"Listing {listing_id} not found")
    
    # Get total m²
    total_m2 = listing.get("sqm") or listing.get("m2_built") or listing.get("m2_useful")
    
    if not total_m2:
        # Try scraped_data
        scraped = listing.get("scraped_data", {})
        areas = scraped.get("areas", {})
        total_m2 = areas.get("constructed") or areas.get("useful") or scraped.get("sqm")
    
    if not total_m2:
        raise ValueError("No total m² found for listing")
    
    total_m2 = float(total_m2)
    logger.info(f"📐 Total property size: {total_m2} m²")
    
    # Get clusters (Gate 0 + v3: Smart M2 is only for UNIT-PRIVATE spaces; exclude shared building infrastructure)
    clusters = await orchestrator.db.get_photo_clusters(listing_id)
    
    if not clusters:
        raise ValueError("No room clusters found - run P1 first")
    
    # Keywords that indicate shared building infrastructure (NOT part of the unit)
    SHARED_BUILDING_KEYWORDS = {
        "lobby", "portal", "vestibulo", "vestíbulo",
        "lift", "elevator", "ascensor",
        "stairwell", "escalera", "stairs",
        "pool", "piscina",
        "gym", "gimnasio",
        "parking", "garaje", "garage",
        "building", "edificio", "fachada", "facade",
        "condominium", "comunidad",
        "common_area", "zonas_comunes", "zonas comunes",
    }
    
    def _is_shared_building_cluster(cluster: Dict[str, Any]) -> bool:
        """
        Exclude clusters that are SHARED BUILDING INFRASTRUCTURE, not part of the unit.
        
        INCLUDE (part of the unit → goes into Smart M2):
        - All interior rooms (bedrooms, bathrooms, kitchen, hallway, etc.)
        - Private outdoor spaces (balcony, terrace, patio, garden)
        - Utility areas (galería/lavadero)
        
        EXCLUDE (shared building infrastructure → NOT part of unit):
        - Street/building facade shots (room_type == "exterior")
        - Building common areas (room_type == "common_area")
        - Any cluster whose name/id contains shared building keywords
        """
        room_type = str(cluster.get("room_type") or "").strip().lower()
        cluster_id = str(cluster.get("cluster_id") or cluster.get("id") or "").strip().lower()
        cluster_name = str(cluster.get("cluster_name") or cluster.get("room_name") or "").strip().lower()
        
        # Explicit room_type exclusions
        if room_type in ("exterior", "common_area", "floorplan"):
            return True
        
        # Keyword-based exclusions (safety net for mislabeled clusters)
        combined_text = f"{cluster_id} {cluster_name}".lower()
        for keyword in SHARED_BUILDING_KEYWORDS:
            if keyword in combined_text:
                return True
        
        return False

    original_cluster_count = len(clusters)
    excluded_clusters = [c for c in clusters if _is_shared_building_cluster(c)]
    clusters = [c for c in clusters if not _is_shared_building_cluster(c)]
    if excluded_clusters:
        excluded_ids = [c.get("cluster_id") or c.get("id") for c in excluded_clusters]
        logger.info(
            f"📐 Smart M2: Excluding shared building clusters | excluded={excluded_ids} | before={original_cluster_count} after={len(clusters)}"
        )
    
    if focus_cluster_ids:
        focus_set = {str(cid).strip() for cid in focus_cluster_ids if str(cid).strip()}
        clusters = [c for c in clusters if str(c.get("cluster_id") or c.get("id") or "").strip() in focus_set]
        if not clusters:
            raise RuntimeError(
                f"smart_m2: focus_cluster_ids filtered out all clusters | listing_id={listing_id} focus_cluster_ids={focus_cluster_ids}"
            )
        logger.info(f"📐 Smart M2: Focused clusters | count={len(clusters)} ids={sorted(focus_set)}")

    logger.info(f"📐 Found {len(clusters)} room clusters")
    
    # Build listing context
    listing_context = f"""PROPERTY CONTEXT:
- Title: {listing.get('title', 'N/A')}
- Bedrooms: {listing.get('bedrooms', 'N/A')}
- Bathrooms: {listing.get('bathrooms', 'N/A')}
- City: {listing.get('city', 'N/A')}"""
    
    # Build prompt
    prompt = get_smart_m2_prompt(total_m2, clusters, listing_context)

    # Fetch ALL cluster photos (user-requested). Keep a cluster→image index map in prompt.
    all_urls: list[str] = []
    all_meta: list[Dict[str, str]] = []

    for c in clusters:
        cluster_name = c.get("cluster_name") or c.get("room_name") or c.get("cluster_id", "unknown")
        for url in (c.get("photo_urls", []) or []):
            all_urls.append(url)
            all_meta.append({"cluster_name": cluster_name, "url": url})

    images = []
    if all_urls:
        logger.info(f"📐 Smart M2: Fetching ALL cluster photos for grounding | count={len(all_urls)}")
        fetched = await fetch_images_batch(all_urls)
        for img in fetched:
            if img is None:
                continue
            images.append(img)
        logger.info(f"📐 Smart M2: Fetched {len(images)}/{len(all_urls)} photos")

        mapping_lines = []
        for idx, meta in enumerate(all_meta, start=1):
            mapping_lines.append(f"{idx}. [{meta['cluster_name']}] {meta['url']}")
        prompt += (
            "\n\nPHOTO INDEX MAP (same order as images):\n"
            + "\n".join(mapping_lines)
            + "\n"
        )
    
    # Call Gemini
    result = await call_gemini_json(prompt, model="pro", temperature=0.1, images=images or None)
    
    if not result:
        raise RuntimeError("M1 Gemini call failed")
    
    # Extract data
    rooms = result.get("rooms", [])
    circulation = result.get("circulation_and_walls_m2", 0)
    total_check = result.get("total_check", 0)
    methodology = result.get("dimension_methodology", "")
    
    if not isinstance(rooms, list) or not rooms:
        raise RuntimeError(f"smart_m2: missing rooms list | listing_id={listing_id}")

    # Build canonical cluster_id lookup (input clusters are the source of truth)
    canonical_cluster_ids = {
        str(c.get("cluster_id") or c.get("id") or "").strip(): c
        for c in clusters
    }
    # Also index by cluster_name for fuzzy matching
    canonical_by_name = {
        str(c.get("cluster_name") or c.get("room_name") or "").strip().lower(): str(c.get("cluster_id") or c.get("id") or "").strip()
        for c in clusters
    }

    # Drop shared building rooms if the model emitted them anyway
    def _is_shared_room(room: Dict[str, Any]) -> bool:
        rid = str(room.get("cluster_id") or room.get("room_id") or "").strip().lower()
        rname = str(room.get("cluster_name") or "").strip().lower()
        if rid in ("exterior", "zonas_comunes", "common_area"):
            return True
        combined = f"{rid} {rname}".lower()
        for kw in SHARED_BUILDING_KEYWORDS:
            if kw in combined:
                return True
        return False

    rooms = [r for r in rooms if not _is_shared_room(r)]
    
    if focus_cluster_ids:
        focus_set = {str(cid).strip() for cid in focus_cluster_ids if str(cid).strip()}
        rooms = [r for r in rooms if str(r.get("cluster_id") or r.get("room_id") or "").strip() in focus_set]

    # CRITICAL: Force room_id and cluster_id to match INPUT cluster_ids exactly.
    # The model may normalize (e.g., "galeria_/_lavadero" → "galeria_lavadero").
    # We must overwrite with the canonical cluster_id to ensure downstream joins work.
    for room in rooms:
        model_room_id = str(room.get("room_id") or "").strip()
        model_cluster_id = str(room.get("cluster_id") or "").strip()
        model_cluster_name = str(room.get("cluster_name") or "").strip()
        
        # Try to find canonical cluster_id
        canonical_id = None
        
        # 1. Exact match on cluster_id
        if model_cluster_id in canonical_cluster_ids:
            canonical_id = model_cluster_id
        # 2. Exact match on room_id
        elif model_room_id in canonical_cluster_ids:
            canonical_id = model_room_id
        # 3. Fuzzy match: normalize both and compare
        else:
            # Normalize: lowercase, replace slashes/spaces with underscores, strip
            def _normalize(s: str) -> str:
                return s.lower().replace("/", "_").replace(" ", "_").replace("__", "_").strip("_")
            
            norm_model = _normalize(model_cluster_id or model_room_id)
            for cid in canonical_cluster_ids:
                if _normalize(cid) == norm_model:
                    canonical_id = cid
                    break
            
            # 4. Match by cluster_name
            if not canonical_id and model_cluster_name:
                name_lower = model_cluster_name.lower()
                if name_lower in canonical_by_name:
                    canonical_id = canonical_by_name[name_lower]
        
        if not canonical_id:
            raise RuntimeError(
                f"smart_m2: room has no matching input cluster | "
                f"model_room_id={model_room_id} model_cluster_id={model_cluster_id} model_cluster_name={model_cluster_name} | "
                f"canonical_ids={list(canonical_cluster_ids.keys())}"
            )
        
        # Overwrite with canonical ID
        if room.get("room_id") != canonical_id:
            logger.info(f"  📐 Normalizing room_id: {room.get('room_id')} → {canonical_id}")
        room["room_id"] = canonical_id
        room["cluster_id"] = canonical_id
    
    # Validate required fields
    for room in rooms:
        room_id = room.get("room_id")
        cluster_id = room.get("cluster_id")
        if not room_id:
            raise RuntimeError(f"smart_m2: missing room_id | room={room}")
        if not cluster_id:
            raise RuntimeError(f"smart_m2: missing cluster_id | room_id={room_id}")
        if "features" not in room:
            raise RuntimeError(f"smart_m2: missing features[] | room_id={room_id}")
    
    # Validate total m²
    calculated_total = sum(r.get("estimated_m2", 0) for r in rooms) + circulation
    if abs(calculated_total - total_m2) > 1:
        logger.warning(f"M2 distribution mismatch: {calculated_total} vs {total_m2}")
    
    # Validate dimensions match m² for each room
    for room in rooms:
        dims = room.get("estimated_dimensions", {})
        if dims:
            length = dims.get("length_m", 0)
            width = dims.get("width_m", 0)
            calculated_m2 = length * width
            estimated_m2 = room.get("estimated_m2", 0)
            if abs(calculated_m2 - estimated_m2) > 2:  # Allow 2m² tolerance
                logger.warning(
                    f"  ⚠ {room.get('cluster_name')}: dimensions {length}×{width}={calculated_m2:.1f}m² "
                    f"vs estimated {estimated_m2}m²"
                )
    
    # Log dimension details
    for room in rooms:
        dims = room.get("estimated_dimensions", {})
        wall_segments = room.get("wall_segments") or []
        if dims:
            logger.info(
                f"  📐 {room.get('cluster_name')}: {room.get('estimated_m2')}m² "
                f"({dims.get('length_m')}m × {dims.get('width_m')}m), "
                f"{len(wall_segments)} wall segments"
            )

    # Compute provenance-safe m3 menu per room (pure quantities augmentation)
    waste_rules = _load_waste_rules()
    for room in rooms:
        try:
            room["waste_m3_by_rule"] = _compute_room_waste_m3_menu(room, waste_rules)
        except Exception as e:
            raise RuntimeError(
                f"smart_m2: failed to compute waste_m3_by_rule | room={room.get('cluster_name')} | err={e}"
            ) from e

        # Compute derived geometry fields for structured openings (area/perimeter)
        openings = room.get("openings") or []
        if not isinstance(openings, list):
            openings = []
        for opening in openings:
            if isinstance(opening, dict):
                _compute_opening_derived_fields(opening)
        room["openings"] = openings

        # Compute derived fields for wall segments (gross + net m2)
        _compute_wall_segment_derived_fields(room)

        # Compute deterministic, position-free room-level primitives for downstream resolver
        _compute_room_level_primitives(room)

        # Compute deterministic aggregates (menu) for downstream selection (no extra math in prompts)
        _compute_opening_aggregates(room)
        _compute_feature_aggregates(room)
        _compute_takeoff_primitives(room)
    
    if persist_to_db:
        # Save to database
        await orchestrator.db.save_smart_m2(
            listing_id=listing_id,
            rooms=rooms,
            circulation_and_walls_m2=circulation,
            total_check=total_check,
            model_used="pro",
        )
    
    logger.info(f"✅ M1: Distributed {total_m2} m² across {len(rooms)} rooms with dimensions")
    
    return {
        "summary": f"Distributed {total_m2} m² across {len(rooms)} rooms with wall dimensions",
        "total_m2": total_m2,
        "rooms_count": len(rooms),
        "circulation_m2": circulation,
        "rooms": rooms,  # Include full room data for downstream use
        "methodology": methodology,
    }


async def run_m1_smart_m2_single_room(
    orchestrator: "PipelineOrchestrator",
    listing_id: int,
    *,
    focus_cluster_id: str,
    model: str = "pro",
) -> Dict[str, Any]:
    """
    Gate 0 helper: run Smart M2 for a single cluster to test openings recall/completeness.
    Does NOT write to DB.
    """
    if not focus_cluster_id or not str(focus_cluster_id).strip():
        raise ValueError("smart_m2_single_room: focus_cluster_id is required")
    focus_cluster_id = str(focus_cluster_id).strip()

    listing = await orchestrator.db.get_listing(listing_id)
    if not listing:
        raise ValueError(f"Listing {listing_id} not found")

    listing_context = f"""PROPERTY CONTEXT:
- Title: {listing.get('title', 'N/A')}
- Bedrooms: {listing.get('bedrooms', 'N/A')}
- Bathrooms: {listing.get('bathrooms', 'N/A')}
- City: {listing.get('city', 'N/A')}"""

    clusters = await orchestrator.db.get_photo_clusters(listing_id)
    if not clusters:
        raise ValueError("No room clusters found - run P1 first")

    cluster = None
    for c in clusters:
        cid = str(c.get("cluster_id") or c.get("id") or "").strip()
        if cid == focus_cluster_id:
            cluster = c
            break
    if not cluster:
        raise RuntimeError(
            f"smart_m2_single_room: cluster not found | listing_id={listing_id} cluster_id={focus_cluster_id}"
        )

    urls = cluster.get("photo_urls", []) or []
    if not urls:
        raise RuntimeError(f"smart_m2_single_room: cluster has no photos | cluster_id={focus_cluster_id}")

    logger.info(
        f"📐 Smart M2 (single-room): Fetching cluster photos | cluster_id={focus_cluster_id} count={len(urls)}"
    )
    images = [img for img in (await fetch_images_batch(urls)) if img is not None]
    logger.info(f"📐 Smart M2 (single-room): Fetched {len(images)}/{len(urls)} photos")

    prompt = get_smart_m2_single_room_prompt(cluster=cluster, listing_context=listing_context)

    mapping_lines = []
    cluster_name = cluster.get("cluster_name") or cluster.get("room_name") or focus_cluster_id
    for idx, url in enumerate(urls, start=1):
        mapping_lines.append(f"{idx}. [{cluster_name}] {url}")
    prompt += "\n\nPHOTO INDEX MAP:\n" + "\n".join(mapping_lines) + "\n"

    result = await call_gemini_json(prompt, model=model, temperature=0.1, images=images or None)
    if not result or not isinstance(result, dict) or "room" not in result:
        raise RuntimeError(
            f"smart_m2_single_room: invalid model response | cluster_id={focus_cluster_id} keys={list((result or {}).keys())}"
        )

    room = result.get("room") or {}
    if not isinstance(room, dict):
        raise RuntimeError(f"smart_m2_single_room: room is not an object | cluster_id={focus_cluster_id}")

    room["cluster_id"] = focus_cluster_id
    room["room_id"] = focus_cluster_id

    # Normalize wall_ids to w1..wN for viewer compatibility (model may emit semantic wall ids).
    wall_segments = room.get("wall_segments") or []
    if not isinstance(wall_segments, list) or not wall_segments:
        raise RuntimeError(f"smart_m2_single_room: missing wall_segments | cluster_id={focus_cluster_id}")
    wall_id_map: Dict[str, str] = {}
    for idx, segment in enumerate(wall_segments, start=1):
        if not isinstance(segment, dict):
            continue
        old_id = str(segment.get("wall_id") or f"w{idx}")
        new_id = f"w{idx}"
        wall_id_map[old_id] = new_id
        segment["wall_id"] = new_id
    room["wall_segments"] = wall_segments

    def _remap_wall_id(item: Dict[str, Any]) -> None:
        wall_id = item.get("wall_id")
        if wall_id and wall_id in wall_id_map:
            item["wall_id"] = wall_id_map[wall_id]

    openings = room.get("openings") or []
    if not isinstance(openings, list):
        openings = []
    for opening in openings:
        if isinstance(opening, dict):
            _remap_wall_id(opening)
            _compute_opening_derived_fields(opening)
    room["openings"] = openings

    features = room.get("features") or []
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, dict):
                _remap_wall_id(feature)
        room["features"] = features
    _compute_wall_segment_derived_fields(room)
    _compute_room_level_primitives(room)
    _compute_opening_aggregates(room)
    _compute_feature_aggregates(room)
    _compute_takeoff_primitives(room)

    waste_rules = _load_waste_rules()
    room["waste_m3_by_rule"] = _compute_room_waste_m3_menu(room, waste_rules)

    return {"room": room}

