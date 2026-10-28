#!/usr/bin/env python3
"""
Semantic QC: V3 delta BCCA worklist outputs
==========================================

PURPOSE
-------
Validation ensures quantity_ref strings are selected from TAKEOFF_MENU.
This script adds "semantic QC" on top:
- Room-by-room coverage (one room_block per room, no missing/extra rooms)
- No internal inconsistencies (item.room_id matches its room_block.room_id)
- Unit-family sanity (e.g., *_M2 -> unit=m2, *_ML -> unit=ml, *_COUNT -> unit=ud, WASTE_M3 -> unit=m3)
- Duplicate quantity_refs per room (potential double-charging)
- StrategySpec alignment heuristics (targets covered by at least one item in that room/dimension)

WHY THIS MATTERS
----------------
If we generate great-looking BCCA Spanish but attach the wrong quantity refs, downstream BOQ becomes
mispriced or nonsensical. This script is a guardrail before resuming full validation runs.

USAGE
-----
./venv/bin/python scripts/qc_delta_bcca_worklist.py --listing-id 12 --strategy conservative --output-dir /tmp/worklist_smoke
"""

import argparse
import json
import logging
import re
import sys
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    from database import Database
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pricing.takeoff_menu import build_takeoff_menu
    from pipeline.gemini_client import call_gemini
except ModuleNotFoundError:
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from database import Database
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pricing.takeoff_menu import build_takeoff_menu
    from pipeline.gemini_client import call_gemini


logger = logging.getLogger("qc_delta_bcca_worklist")

IMAGE_QC_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "summary": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                    "dimension": {"type": "string"},
                    "issue_type": {"type": "string"},
                    "evidence_from_images": {"type": "string"},
                    "evidence_from_spec": {"type": "string"},
                    "worklist_item_refs": {"type": "array", "items": {"type": "string"}},
                    "suggested_fix": {"type": "string"},
                    "suggested_quantity_ref": {"type": "string"},
                },
                "required": ["severity", "dimension", "issue_type", "evidence_from_images", "evidence_from_spec", "worklist_item_refs", "suggested_fix"],
            },
        },
        "missing_work": {"type": "array", "items": {"type": "string"}},
        "unjustified_work": {"type": "array", "items": {"type": "string"}},
        "quantity_ref_suspicions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["room_id", "summary", "issues", "missing_work", "unjustified_work", "quantity_ref_suspicions"],
}


_UNIT_BY_SUFFIX = {
    "_M2": "m2",
    "_ML": "ml",
    "_M3": "m3",
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _tokenize(text: str) -> Set[str]:
    # Spanish-ish tokenization: keep letters/numbers, split on punctuation/whitespace.
    raw = re.split(r"[^a-z0-9áéíóúñü]+", (text or "").lower(), flags=re.IGNORECASE)
    return {t for t in raw if len(t) >= 4}


def _looks_like_opaque_task_id(value: str) -> bool:
    """
    Many StrategySpec targets are opaque IDs like TASK_SUSTIT_DE_PUERTA_DE_4c2e4825.
    These are not semantically matchable against BCCA Spanish descriptions.
    """
    s = _normalize_text(value)
    if not s:
        return False
    if s.startswith("TASK_"):
        return True
    # Structural target selectors like OPENING(x), WALL(room,w1), FEATURE(room,foo)
    if re.match(r"^[A-Z_]+\([^)]*\)$", s):
        return True
    # Hex-ish suffix tokens are a strong indicator.
    if re.search(r"_[0-9a-f]{6,}$", s.lower()):
        return True
    return False


def _keyword_expected_families(bcca_description: str) -> Optional[Set[str]]:
    """
    Heuristic mapping from description keywords to expected quantity_ref 'families'.
    This is not perfect, but catches obviously wrong refs (e.g. 'silicona' with FLOOR_M2).
    """
    desc = (bcca_description or "").lower()
    if not desc:
        return None

    # High-precision rules only (avoid noisy false positives).
    # Special-cases first to avoid false positives.
    if any(k in desc for k in ("rejunt", "alicat", "azulej", "lechad")):
        return {"surfaces"}  # wall/tiles are m2-based in our takeoff menu

    # If joints/seal are explicitly about the FLOOR, they are surfaces, not sealant ML.
    if ("junta" in desc or "sellad" in desc) and any(k in desc for k in ("pavimento", "suelo", "terrazo")):
        return {"surfaces"}

    rules: List[Tuple[Sequence[str], Set[str]]] = [
        # Waste/disposal should generally be WASTE_M3(...)
        (("vertedero", "escombr", "carga y transporte", "retirada de escombros", "desescombro"), {"waste"}),
        # Sealant (silicone) is generally ml details or openings perimeter totals.
        (("silicona",), {"details", "openings"}),
        # Skirting/coving/etc are ml details.
        (("rodapi", "zócal", "zocal", "moldura", "cornisa"), {"details"}),
        # Bathroom/kitchen fixtures count/qty aggregates.
        (("fregader", "lavabo", "inodoro", "ducha", "bañera", "grif", "sumider"), {"features"}),
        # Carpentry replacement/adjustment should be tied to openings, not room wall m2.
        (("carpinter", "ventan", "puerta"), {"openings"}),
    ]

    for needles, families in rules:
        if any(n in desc for n in needles):
            return families
    return None


def _infer_unit_from_quantity_ref(quantity_ref: str) -> Optional[str]:
    """
    Infer expected unit from the deterministic TAKEOFF_MENU quantity_ref strings.
    Returns one of: m2, ml, ud, m3, or None if unknown/ambiguous.
    """
    qref = _normalize_text(quantity_ref)
    if not qref:
        return None

    if qref.startswith("WASTE_M3("):
        return "m3"

    # Counts
    if qref.startswith("OPENING_COUNT(") or qref.startswith("FEATURE_COUNT("):
        return "ud"

    # Feature quantities explicitly include a unit=... parameter.
    if qref.startswith("FEATURE_QTY_SUM("):
        m = re.search(r"unit=([a-z0-9_]+)\)?$", qref)
        if not m:
            return None
        unit = m.group(1).lower()
        # Only accept the schema-supported unit set.
        if unit in {"m2", "ml", "ud", "m3"}:
            return unit
        return None

    # Generic suffix rules for most refs: *_M2(...), *_ML(...), *_M3(...)
    for suffix, unit in _UNIT_BY_SUFFIX.items():
        if suffix in qref and qref.split("(", 1)[0].endswith(suffix):
            return unit

    return None


def _ref_family(quantity_ref: str) -> str:
    qref = _normalize_text(quantity_ref)
    prefix = qref.split("(", 1)[0]
    if prefix.startswith("WASTE_"):
        return "waste"
    if prefix.startswith("OPENING_"):
        return "openings"
    if prefix.startswith("FEATURE_"):
        return "features"
    if prefix in {"SKIRTING_ML", "COVING_ML", "WINDOW_SILL_ML", "DOOR_THRESHOLD_ML", "SEALANT_ML"}:
        return "details"
    if prefix in {
        "FLOOR_M2",
        "CEILING_M2",
        "PERIMETER_ML",
        "WALL_GROSS_M2",
        "WALL_NET_M2",
        "OPENINGS_TOTAL_AREA_M2",
    }:
        return "surfaces"
    return "other"


@dataclass(frozen=True)
class QCError:
    kind: str
    message: str


@dataclass(frozen=True)
class QCWarning:
    kind: str
    message: str


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Missing file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid JSON shape (expected object) | path={path}")
    return data


def _read_image_as_part(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise RuntimeError(f"Missing image file: {path}")
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {"mime_type": "image/jpeg", "data": data}


def _find_room_images(*, listing_id: int, room_id: str, image_root: Path, limit: int) -> List[Path]:
    """
    Prefer the original per-room images folder:
      <image_root>/listing_<id>/<room_id>/images/*.jpg
    """
    room_dir = image_root / f"listing_{listing_id}" / str(room_id) / "images"
    if not room_dir.exists():
        return []
    imgs = sorted([p for p in room_dir.glob("*.jpg") if p.is_file()])
    return imgs[: max(0, int(limit))]


def _aggregate_room_worklist(*, output_dir: Path, listing_id: int, strategy: str, room_id: str) -> Dict[str, Any]:
    """
    Build a room-centric view:
      - worklist_by_dimension[dim] = list[items] for that room
    """
    worklist_by_dimension: Dict[str, List[Dict[str, Any]]] = {}
    for dim in V2_DIMENSIONS:
        dim_path = output_dir / f"worklist_{listing_id}_{strategy}_{dim}.json"
        if not dim_path.exists():
            continue
        dim_payload = _load_json(dim_path)
        # New schema: worklist_items[].rooms[] (item-centric)
        items_for_room: List[Dict[str, Any]] = []
        for wi in (dim_payload.get("worklist_items") or []):
            if not isinstance(wi, dict):
                continue
            bcca_desc = _normalize_text(wi.get("bcca_description"))
            unit = _normalize_text(wi.get("unit"))
            for r in (wi.get("rooms") or []):
                if not isinstance(r, dict):
                    continue
                rid = _normalize_text(r.get("room_id"))
                if rid != room_id:
                    continue
                items_for_room.append(
                    {
                        "room_id": rid,
                        "bcca_description": bcca_desc,
                        "unit": unit,
                        "quantity_ref": _normalize_text(r.get("quantity_ref")),
                    }
                )
        if items_for_room:
            worklist_by_dimension[dim] = items_for_room
    return {"room_id": room_id, "worklist_by_dimension": worklist_by_dimension}


def _expand_item_centric_payload_to_room_blocks(
    *,
    payload: Dict[str, Any],
    expected_rooms: List[str],
) -> List[Dict[str, Any]]:
    """
    Convert V3 item-centric schema:
      { worklist_items: [ { bcca_description, unit, rooms: [{room_id, quantity_ref}, ...] }, ... ] }
    Into a room-centric view compatible with the existing QC logic:
      room_blocks: [ { room_id, cost_components: [ {room_id, bcca_description, unit, quantity_ref}, ... ] } ... ]
    """
    by_room: Dict[str, List[Dict[str, Any]]] = {rid: [] for rid in expected_rooms}
    for wi in (payload.get("worklist_items") or []):
        if not isinstance(wi, dict):
            continue
        bcca_desc = _normalize_text(wi.get("bcca_description"))
        unit = _normalize_text(wi.get("unit"))
        for r in (wi.get("rooms") or []):
            if not isinstance(r, dict):
                continue
            rid = _normalize_text(r.get("room_id"))
            if not rid:
                continue
            by_room.setdefault(rid, []).append(
                {
                    "room_id": rid,
                    "bcca_description": bcca_desc,
                    "unit": unit,
                    "quantity_ref": _normalize_text(r.get("quantity_ref")),
                }
            )
    return [{"room_id": rid, "cost_components": by_room.get(rid, [])} for rid in expected_rooms]


def _aggregate_room_strategy_spec(*, strategy_spec: Dict[str, Any], room_id: str) -> Dict[str, Any]:
    dims = (strategy_spec.get("dimensions") or {}) if isinstance(strategy_spec.get("dimensions"), dict) else {}
    out: Dict[str, Any] = {"room_id": room_id, "spec_by_dimension": {}}
    for dim, dim_spec in dims.items():
        if not isinstance(dim_spec, dict):
            continue
        rbs = dim_spec.get("room_blocks") or []
        if not isinstance(rbs, list):
            continue
        for rb in rbs:
            if not isinstance(rb, dict):
                continue
            rid = _normalize_text(rb.get("room_id"))
            if rid != room_id:
                continue
            out["spec_by_dimension"][str(dim)] = rb
            break
    return out


def _build_image_qc_prompt(
    *,
    listing_id: int,
    strategy: str,
    room_id: str,
    room_takeoff_menu: Dict[str, Any],
    room_strategy_spec: Dict[str, Any],
    room_worklist: Dict[str, Any],
) -> str:
    """
    Prompt tuned for "is the work plausible and are refs appropriate".
    """
    return f"""
You are a senior quantity surveyor auditing an AI-generated renovation worklist for ONE room, using photos + a deterministic takeoff menu.

WHY THIS MATTERS for this task:
- The buyer will use this to trust (or distrust) the estimate. If we claim work that isn't supported by photos/spec, we lose credibility.
- Downstream BOQ is deterministic: each item must be tied to a plausible takeoff quantity_ref for this room (m2/ml/ud/m3).

CONTEXT:
- listing_id: {listing_id}
- strategy: {strategy}
- room_id: {room_id}

WHAT YOU HAVE:
1) Room photos (attached). Treat them as the ground truth.
2) StrategySpec for this room (desired interventions; sometimes incomplete).
3) Worklist items (what we currently plan to price).
4) TAKEOFF_MENU for this room (allowed quantity_ref strings; you may propose switching to a better one if it exists here).

YOUR JOB:
For each dimension, ask yourself:
- Does the worklist include only work that is supported by the images and/or explicitly indicated by the StrategySpec?
- Is anything missing that SHOULD be included given visible conditions (e.g., obvious damp, broken tiles, outdated fixtures, damaged carpentry)?
- Are any items clearly unjustified (claims work that isn't needed)?
- For each item: is the chosen quantity_ref the RIGHT family for the work?
  - Paint/plaster/tiles → typically WALL_*_M2 or CEILING_M2
  - Floors treatment → FLOOR_M2
  - Sealant/skirting/coving → SEALANT_ML / SKIRTING_ML / similar ML refs
  - Doors/windows/carpentry replacement → OPENING_* refs (area/perimeter/count) when available
  - Fixtures (toilet/sink/boiler/radiators/intercom) → FEATURE_* refs when available
  - Disposal → WASTE_M3(...)

IMPORTANT OUTPUT GUIDANCE:
- Be concrete and skeptical. If you are not confident from the images, say so.
- Prefer a small number of high-signal issues over many vague notes.
- When suggesting a better quantity_ref, ONLY choose from TAKEOFF_MENU.all_quantity_refs for this room.

INPUTS (JSON):
TAKEOFF_MENU_ROOM:
{json.dumps(room_takeoff_menu, ensure_ascii=False, indent=2)}

STRATEGY_SPEC_ROOM:
{json.dumps(room_strategy_spec, ensure_ascii=False, indent=2)}

WORKLIST_ROOM:
{json.dumps(room_worklist, ensure_ascii=False, indent=2)}
""".strip()


def _collect_room_ids_from_takeoff_menu(takeoff_menu: Dict[str, Any]) -> List[str]:
    rooms = takeoff_menu.get("rooms") or {}
    if not isinstance(rooms, dict) or not rooms:
        raise RuntimeError("takeoff_menu.rooms missing/invalid")
    return sorted([str(rid) for rid in rooms.keys()])


def _get_allowed_refs_for_room(takeoff_menu: Dict[str, Any], room_id: str) -> Set[str]:
    rooms = takeoff_menu.get("rooms") or {}
    room_menu = rooms.get(room_id) or {}
    allowed = room_menu.get("all_quantity_refs") or []
    if not isinstance(allowed, list):
        return set()
    return {str(x) for x in allowed}


def _room_to_spec_targets(strategy_spec_dim: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Returns mapping room_id -> list[str] targets for a given dimension spec.
    """
    out: Dict[str, List[str]] = {}
    room_blocks = strategy_spec_dim.get("room_blocks") or []
    if not isinstance(room_blocks, list):
        return out
    for b in room_blocks:
        if not isinstance(b, dict):
            continue
        rid = _normalize_text(b.get("room_id"))
        if not rid:
            continue
        targets = b.get("strategy_targets") or []
        if isinstance(targets, list):
            out[rid] = [_normalize_text(t) for t in targets if _normalize_text(t)]
    return out


def _qc_dimension(
    *,
    dimension: str,
    payload: Dict[str, Any],
    takeoff_menu: Dict[str, Any],
    strategy_spec_dim: Optional[Dict[str, Any]],
) -> Tuple[List[QCError], List[QCWarning], Dict[str, Any]]:
    errors: List[QCError] = []
    warnings: List[QCWarning] = []

    expected_rooms = _collect_room_ids_from_takeoff_menu(takeoff_menu)
    expected_rooms_set = set(expected_rooms)

    # New schema is item-centric (worklist_items[].rooms[]). Expand to room_blocks for QC reporting.
    room_blocks = _expand_item_centric_payload_to_room_blocks(payload=payload, expected_rooms=expected_rooms)

    # Room coverage + duplicates
    seen_rooms: List[str] = []
    for b in room_blocks:
        if not isinstance(b, dict):
            errors.append(QCError("shape", f"room_block is not an object | dim={dimension}"))
            continue
        rid = _normalize_text(b.get("room_id"))
        if not rid:
            errors.append(QCError("shape", f"room_block missing room_id | dim={dimension}"))
            continue
        seen_rooms.append(rid)

    seen_set = set(seen_rooms)
    missing = sorted(list(expected_rooms_set - seen_set))
    extra = sorted(list(seen_set - expected_rooms_set))
    dupes = sorted([r for r in set(seen_rooms) if seen_rooms.count(r) > 1])

    if missing:
        errors.append(QCError("coverage", f"missing room_blocks | dim={dimension} missing={missing}"))
    if extra:
        errors.append(QCError("coverage", f"extra room_blocks (unknown rooms) | dim={dimension} extra={extra}"))
    if dupes:
        errors.append(QCError("coverage", f"duplicate room_blocks | dim={dimension} dupes={dupes}"))

    # Strategy target coverage heuristics
    targets_by_room: Dict[str, List[str]] = {}
    if isinstance(strategy_spec_dim, dict):
        targets_by_room = _room_to_spec_targets(strategy_spec_dim)

    per_room_summary: Dict[str, Any] = {}

    for b in room_blocks:
        if not isinstance(b, dict):
            continue
        room_id = _normalize_text(b.get("room_id"))
        if not room_id:
            continue
        allowed_refs = _get_allowed_refs_for_room(takeoff_menu, room_id)
        items = b.get("cost_components") or []
        if not isinstance(items, list):
            errors.append(QCError("shape", f"cost_components not list | dim={dimension} room_id={room_id}"))
            continue

        dup_ref_map: Dict[str, List[str]] = {}
        families: Dict[str, int] = {}

        desc_tokens_all: Set[str] = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(QCError("shape", f"cost_component not object | dim={dimension} room_id={room_id} idx={idx}"))
                continue
            item_room_id = _normalize_text(item.get("room_id"))
            if item_room_id != room_id:
                errors.append(
                    QCError(
                        "consistency",
                        f"item.room_id != room_block.room_id | dim={dimension} block={room_id} item={item_room_id} idx={idx}",
                    )
                )
            qref = _normalize_text(item.get("quantity_ref"))
            unit = _normalize_text(item.get("unit"))
            bcca_desc = _normalize_text(item.get("bcca_description"))
            desc_tokens_all |= _tokenize(bcca_desc)

            if qref and qref not in allowed_refs:
                # This should already be caught by validate_worklist, but we keep it here as a hard error.
                errors.append(QCError("quantity_ref", f"invalid quantity_ref | dim={dimension} room_id={room_id} idx={idx} qref={qref}"))

            expected_unit = _infer_unit_from_quantity_ref(qref)
            if expected_unit and unit and expected_unit != unit:
                errors.append(
                    QCError(
                        "unit_mismatch",
                        f"unit mismatch for quantity_ref family | dim={dimension} room_id={room_id} idx={idx} qref={qref} expected={expected_unit} got={unit}",
                    )
                )
            if not expected_unit:
                warnings.append(QCWarning("unit_infer", f"could not infer unit from quantity_ref | dim={dimension} room_id={room_id} idx={idx} qref={qref}"))

            if qref:
                dup_ref_map.setdefault(qref, []).append(bcca_desc or "(empty bcca_description)")

            fam = _ref_family(qref)
            families[fam] = families.get(fam, 0) + 1

            expected_fams = _keyword_expected_families(bcca_desc)
            if expected_fams is not None and fam not in expected_fams:
                warnings.append(
                    QCWarning(
                        "semantic_family_mismatch",
                        "description keywords suggest different ref family | "
                        f"dim={dimension} room_id={room_id} idx={idx} fam={fam} expected={sorted(list(expected_fams))} "
                        f"qref={qref} desc={bcca_desc}",
                    )
                )

        duplicate_refs = {q: descs for q, descs in dup_ref_map.items() if len(descs) > 1}
        if duplicate_refs:
            # Re-using the same quantity_ref is NOT inherently wrong (multiple distinct works can be
            # measured off the same geometry). Only warn if descriptions look near-duplicate,
            # suggesting accidental double-charge rather than distinct scope.
            suspicious: List[str] = []
            for qref, descs in duplicate_refs.items():
                token_sets = [_tokenize(d) for d in descs]
                if not token_sets:
                    continue
                # If any pair overlaps heavily, flag it.
                for a in range(len(token_sets)):
                    for b in range(a + 1, len(token_sets)):
                        inter = len(token_sets[a] & token_sets[b])
                        union = len(token_sets[a] | token_sets[b]) or 1
                        jacc = inter / union
                        if jacc >= 0.6:
                            suspicious.append(qref)
                            break
                    if qref in suspicious:
                        break
            if suspicious:
                warnings.append(
                    QCWarning(
                        "duplicate_quantity_ref",
                        f"potential double-charge: near-duplicate descriptions share quantity_ref | dim={dimension} room_id={room_id} refs={sorted(list(set(suspicious)))}",
                    )
                )

        # Strategy target coverage heuristic
        uncovered_targets: List[str] = []
        targets = targets_by_room.get(room_id) or []
        for t in targets:
            if _looks_like_opaque_task_id(t):
                continue
            t_tokens = _tokenize(t)
            if not t_tokens:
                continue
            if len(t_tokens & desc_tokens_all) == 0:
                uncovered_targets.append(t)
        if targets and uncovered_targets:
            warnings.append(
                QCWarning(
                    "targets_uncovered",
                    f"strategy targets not obviously covered by any bcca_description tokens | dim={dimension} room_id={room_id} uncovered={uncovered_targets}",
                )
            )

        per_room_summary[room_id] = {
            "items": len(items),
            "families": dict(sorted(families.items(), key=lambda kv: (-kv[1], kv[0]))),
            "duplicate_quantity_refs": {k: v for k, v in duplicate_refs.items()},
            "targets": targets,
            "uncovered_targets": uncovered_targets,
        }

    report = {
        "dimension": dimension,
        "rooms_expected": len(expected_rooms),
        "rooms_seen": len(seen_rooms),
        "items_total": sum((per_room_summary.get(r, {}).get("items") or 0) for r in per_room_summary.keys()),
        "per_room": per_room_summary,
    }

    return errors, warnings, report


async def main_async(args: argparse.Namespace) -> None:
    db = Database()

    listing_id = int(args.listing_id)
    strategy_name = _normalize_text(args.strategy)
    if not strategy_name:
        raise RuntimeError("strategy is required")

    output_dir = Path(args.output_dir).resolve()
    strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
    if not strategy_spec:
        raise RuntimeError(f"Missing v3_strategy_spec_{strategy_name} | listing_id={listing_id}")
    if not isinstance(strategy_spec, dict):
        raise RuntimeError(f"Invalid strategy_spec shape | listing_id={listing_id}")

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        raise RuntimeError(f"Missing smart_m2 | listing_id={listing_id}")

    takeoff_menu = build_takeoff_menu(smart_m2)

    spec_dims = (strategy_spec.get("dimensions") or {}) if isinstance(strategy_spec.get("dimensions"), dict) else {}

    all_errors: List[QCError] = []
    all_warnings: List[QCWarning] = []
    per_dim_reports: Dict[str, Any] = {}
    qref_room_owners: Dict[str, Set[str]] = {}

    # Prefer per-dimension files to avoid "combined file overwritten" pitfalls.
    # We QC only dimensions that have an output JSON present in output_dir.
    available_dims: List[str] = []
    for dim in V2_DIMENSIONS:
        dim_path = output_dir / f"worklist_{listing_id}_{strategy_name}_{dim}.json"
        if dim_path.exists():
            available_dims.append(dim)
        else:
            all_warnings.append(QCWarning("missing_dim_file", f"missing dimension output file | dim={dim} path={dim_path}"))

    if not available_dims:
        raise RuntimeError(f"No per-dimension worklist JSON files found in {output_dir}")

    for dim in available_dims:
        dim_path = output_dir / f"worklist_{listing_id}_{strategy_name}_{dim}.json"
        dim_payload = _load_json(dim_path)
        if dim_payload.get("dimension") != dim:
            all_errors.append(QCError("shape", f"dimension mismatch in file | dim={dim} file_dim={dim_payload.get('dimension')} path={dim_path}"))
            continue

        # Track whether any exact quantity_ref string appears across multiple rooms (should not happen).
        for wi in (dim_payload.get("worklist_items") or []):
            if not isinstance(wi, dict):
                continue
            for r in (wi.get("rooms") or []):
                if not isinstance(r, dict):
                    continue
                rid = _normalize_text(r.get("room_id"))
                qref = _normalize_text(r.get("quantity_ref"))
                if not qref or not rid:
                    continue
                qref_room_owners.setdefault(qref, set()).add(rid)

        dim_spec = spec_dims.get(dim) if isinstance(spec_dims, dict) else None
        errors, warnings, report = _qc_dimension(
            dimension=str(dim),
            payload=dim_payload,
            takeoff_menu=takeoff_menu,
            strategy_spec_dim=dim_spec if isinstance(dim_spec, dict) else None,
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        report["source_path"] = str(dim_path)
        per_dim_reports[str(dim)] = report

    shared_qrefs = {q: sorted(list(rids)) for q, rids in qref_room_owners.items() if len(rids) > 1}
    if shared_qrefs:
        all_warnings.append(QCWarning("cross_room_qref", f"quantity_ref appears in multiple rooms (unexpected) | count={len(shared_qrefs)}"))

    # Optional: image-based QC for rooms that have images available.
    image_qc_results: Dict[str, Any] = {}
    if bool(getattr(args, "image_qc", False)):
        image_root = Path(args.image_root).resolve()
        per_room_limit = int(args.images_per_room)
        max_rooms = int(args.max_rooms) if args.max_rooms is not None else None
        model = _normalize_text(args.image_model) or "pro"

        room_ids = _collect_room_ids_from_takeoff_menu(takeoff_menu)
        if max_rooms is not None:
            room_ids = room_ids[: max(0, max_rooms)]

        rooms_obj = takeoff_menu.get("rooms") or {}

        for room_id in room_ids:
            room_imgs = _find_room_images(listing_id=listing_id, room_id=room_id, image_root=image_root, limit=per_room_limit)
            if not room_imgs:
                image_qc_results[room_id] = {"skipped": True, "reason": "no images found"}
                continue

            room_takeoff_menu = rooms_obj.get(room_id) or {}
            room_strategy_spec = _aggregate_room_strategy_spec(strategy_spec=strategy_spec, room_id=room_id)
            room_worklist = _aggregate_room_worklist(
                output_dir=output_dir,
                listing_id=listing_id,
                strategy=strategy_name,
                room_id=room_id,
            )

            prompt = _build_image_qc_prompt(
                listing_id=listing_id,
                strategy=strategy_name,
                room_id=room_id,
                room_takeoff_menu=room_takeoff_menu,
                room_strategy_spec=room_strategy_spec,
                room_worklist=room_worklist,
            )
            images = [_read_image_as_part(p) for p in room_imgs]

            logger.info("IMAGE_QC → Gemini | room_id=%s | images=%s | model=%s", room_id, len(images), model)
            resp = await call_gemini(
                prompt=prompt,
                model=model,
                temperature=0.2,
                max_tokens=8192,
                response_schema=IMAGE_QC_SCHEMA,
                images=images,
                use_spanish=True,
            )
            if not resp.success:
                raise RuntimeError(f"image_qc failed | room_id={room_id} error={resp.error}")
            image_qc_results[room_id] = json.loads(resp.text)

    # Write machine-readable report for inspection.
    report_path = output_dir / f"qc_worklist_{listing_id}_{strategy_name}.json"
    report_path.write_text(
        json.dumps(
            {
                "listing_id": listing_id,
                "strategy": strategy_name,
                "errors": [e.__dict__ for e in all_errors],
                "warnings": [w.__dict__ for w in all_warnings],
                "shared_quantity_refs_across_rooms": shared_qrefs,
                "by_dimension": per_dim_reports,
                "image_qc": image_qc_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info("QC report written | path=%s", report_path)

    # Print a compact human summary.
    logger.info("QC SUMMARY | listing_id=%s | strategy=%s | dims=%s", listing_id, strategy_name, len(per_dim_reports))
    logger.info("  Errors: %s", len(all_errors))
    logger.info("  Warnings: %s", len(all_warnings))

    # Print top issues (bounded).
    for e in all_errors[:25]:
        logger.error("ERROR [%s] %s", e.kind, e.message)
    for w in all_warnings[:25]:
        logger.warning("WARN  [%s] %s", w.kind, w.message)

    if all_errors:
        raise RuntimeError(f"QC failed with errors={len(all_errors)} (see {report_path})")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--strategy", type=str, required=True)
    parser.add_argument("--output-dir", default="/tmp/worklist_smoke", help="Directory containing worklist_*__ALL.json")
    parser.add_argument("--image-qc", action="store_true", help="Run image-based QC per room using Gemini Pro.")
    parser.add_argument(
        "--image-root",
        default="/root/puedo_casa/lean-mvp/docs/reference/cluster_panos",
        help="Root directory containing listing_<id>/<room_id>/images/*.jpg",
    )
    parser.add_argument("--images-per-room", type=int, default=4, help="Max images to attach per room.")
    parser.add_argument("--max-rooms", type=int, default=None, help="Limit number of rooms (deterministic prefix).")
    parser.add_argument("--image-model", type=str, default="pro", help='Gemini model alias ("pro" recommended).')
    args = parser.parse_args()
    import asyncio

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

