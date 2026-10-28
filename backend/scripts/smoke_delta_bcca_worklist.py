#!/usr/bin/env python3
"""
Smoke test: V3 delta BCCA worklist generation (quality-focused)
==============================================================

PURPOSE
-------
Run the V3 BCCA worklist generation for a SINGLE listing/strategy and selected dimensions,
then validate the output is "takeoff safe" (quantity_ref must be selected from TAKEOFF_MENU).

WHY THIS MATTERS
----------------
- We run the full pipeline in foreground timeout slices. If quality is wrong, we want to detect
  it early with a focused run, like we did for pano smoketests.
- We must avoid the historical failure mode of "LLM invents quantities / invents refs", which
  breaks deterministic BOQ and causes rework/cost.

USAGE
-----
./venv/bin/python scripts/smoke_delta_bcca_worklist.py --listing-id 12 --strategy conservative --dimensions systems_services

By default, this script:
- reads strategy_spec + smart_m2 from Supabase
- calls Gemini (flash) only for the requested dimensions
- writes JSON outputs into /tmp/worklist_smoke/
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

try:
    from database import Database
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pricing.takeoff_menu import build_takeoff_menu
    from pricing.v3_delta_scopes import _call_bcca_worklist
except ModuleNotFoundError:
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from database import Database
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pricing.takeoff_menu import build_takeoff_menu
    from pricing.v3_delta_scopes import _call_bcca_worklist


logger = logging.getLogger("smoke_delta_bcca_worklist")


def _parse_dimensions(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return parts


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _dimension_out_path(output_dir: Path, listing_id: int, strategy_name: str, dimension: str) -> Path:
    return output_dir / f"worklist_{listing_id}_{strategy_name}_{dimension}.json"


def _validate_worklist(
    *,
    payload: Dict[str, Any],
    takeoff_menu: Dict[str, Any],
    expected_dimension: str,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return False, ["payload is not a dict"]

    dim = payload.get("dimension")
    if dim != expected_dimension:
        errors.append(f"dimension mismatch | expected={expected_dimension} got={dim}")

    rooms = (takeoff_menu.get("rooms") or {}) if isinstance(takeoff_menu, dict) else {}
    if not isinstance(rooms, dict) or not rooms:
        errors.append("takeoff_menu.rooms missing/invalid")
        return False, errors

    worklist_items = payload.get("worklist_items") or []
    if not isinstance(worklist_items, list):
        errors.append("worklist_items missing/invalid")
        return False, errors

    # Empty list is allowed (dimension may not apply), but still should be a list.
    required_item_fields = ["bcca_description", "unit", "rooms"]
    required_room_fields = ["room_id", "quantity_ref"]

    for i, item in enumerate(worklist_items):
        if not isinstance(item, dict):
            errors.append(f"worklist_item not dict | idx={i}")
            continue
        for field in required_item_fields:
            if item.get(field) in (None, "", []):
                errors.append(f"missing field | item_idx={i} field={field}")

        rooms_list = item.get("rooms") or []
        if not isinstance(rooms_list, list) or not rooms_list:
            errors.append(f"rooms invalid/empty | item_idx={i}")
            continue

        for j, r in enumerate(rooms_list):
            if not isinstance(r, dict):
                errors.append(f"rooms entry not dict | item_idx={i} room_idx={j}")
                continue
            for rf in required_room_fields:
                if r.get(rf) in (None, "", []):
                    errors.append(f"missing rooms field | item_idx={i} room_idx={j} field={rf}")
            room_id = str(r.get("room_id") or "").strip()
            if not room_id:
                continue
            room_menu = rooms.get(room_id)
            if not isinstance(room_menu, dict):
                errors.append(f"room_id not found in takeoff_menu.rooms | item_idx={i} room_id={room_id}")
                continue
            allowed_refs = room_menu.get("all_quantity_refs") or []
            if not isinstance(allowed_refs, list):
                errors.append(f"takeoff_menu.rooms[{room_id}].all_quantity_refs invalid")
                continue
            qref = r.get("quantity_ref")
            if qref and qref not in allowed_refs:
                errors.append(
                    "invalid quantity_ref (not in TAKEOFF_MENU) | "
                    f"item_idx={i} room_id={room_id} quantity_ref={qref}"
                )

    return len(errors) == 0, errors


async def _run_one_dimension(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    db: Database,
    strategy_spec: Dict[str, Any],
    takeoff_menu: Dict[str, Any],
    output_dir: Path,
    resume: bool,
) -> Dict[str, Any]:
    dims = (strategy_spec.get("dimensions") or {})
    if dimension not in dims:
        raise RuntimeError(f"strategy_spec missing dimension | strategy={strategy_name} dim={dimension}")

    out_path = _dimension_out_path(output_dir, listing_id, strategy_name, dimension)
    if resume and out_path.exists():
        logger.info("↪ Resume: using existing JSON | dim=%s | path=%s", dimension, out_path)
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        ok, errors = _validate_worklist(payload=payload, takeoff_menu=takeoff_menu, expected_dimension=dimension)
        if not ok:
            raise RuntimeError(f"resume validation failed | dim={dimension} | errors={len(errors)}")
        return payload

    logger.info("→ Calling Gemini for worklist | listing_id=%s | strategy=%s | dim=%s", listing_id, strategy_name, dimension)
    payload = await _call_bcca_worklist(
        strategy_spec=dims[dimension],
        takeoff_menu=takeoff_menu,
        strategy_name=strategy_name,
        dimension=dimension,
    )

    # Always persist raw payload so we can inspect quality even if validation fails.
    try:
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("💾 Wrote %s", out_path)
    except Exception as e:
        logger.error("Failed to write output JSON | path=%s | error=%s", out_path, e)

    ok, errors = _validate_worklist(payload=payload, takeoff_menu=takeoff_menu, expected_dimension=dimension)
    if not ok:
        logger.error("❌ Worklist validation failed | dim=%s | errors=%s", dimension, len(errors))
        for e in errors[:50]:
            logger.error("  - %s", e)
        raise RuntimeError(f"worklist validation failed | dim={dimension} | errors={len(errors)}")

    room_blocks = payload.get("room_blocks") or []
    worklist_items = payload.get("worklist_items") or []
    # Approximate expansion count (room entries) for quick sanity.
    room_entry_count = 0
    for wi in worklist_items:
        if isinstance(wi, dict):
            room_entry_count += len((wi.get("rooms") or [])) if isinstance(wi.get("rooms"), list) else 0
    logger.info(
        "✅ Worklist OK | dim=%s | worklist_items=%s | room_entries=%s",
        dimension,
        len(worklist_items) if isinstance(worklist_items, list) else 0,
        room_entry_count,
    )

    # (already written above)
    return payload


async def main_async(args: argparse.Namespace) -> None:
    db = Database()

    listing_id = int(args.listing_id)
    strategy_name = str(args.strategy).strip()
    if not strategy_name:
        raise RuntimeError("strategy is required")

    dims = _parse_dimensions(args.dimensions)
    if not dims:
        dims = list(V2_DIMENSIONS)

    bad = [d for d in dims if d not in V2_DIMENSIONS]
    if bad:
        raise RuntimeError(f"Unknown dimensions: {bad} | allowed={V2_DIMENSIONS}")

    output_dir = Path(args.output_dir).resolve()
    _ensure_dir(output_dir)
    resume = bool(args.resume)

    strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
    if not strategy_spec:
        raise RuntimeError(f"Missing v3_strategy_spec_{strategy_name} | listing_id={listing_id}")

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        raise RuntimeError(f"Missing smart_m2 | listing_id={listing_id}")

    takeoff_menu = build_takeoff_menu(smart_m2)
    logger.info("Loaded TAKEOFF_MENU | rooms=%s", len((takeoff_menu.get("rooms") or {}).keys()))

    outputs: Dict[str, Any] = {}
    for dim in dims:
        outputs[dim] = await _run_one_dimension(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dim,
            db=db,
            strategy_spec=strategy_spec,
            takeoff_menu=takeoff_menu,
            output_dir=output_dir,
            resume=resume,
        )

    combined = {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "dimensions": outputs,
        "takeoff_menu": takeoff_menu,
    }
    combined_path = output_dir / f"worklist_{listing_id}_{strategy_name}__ALL.json"
    combined_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("💾 Wrote combined %s", combined_path)
    logger.info("✅ SMOKE TEST COMPLETE | listing_id=%s | strategy=%s | dims=%s", listing_id, strategy_name, len(dims))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Smoke test for v3 delta BCCA worklist generation.")
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--strategy", required=True, help="Strategy name: conservative | market_standard | top_of_market")
    parser.add_argument(
        "--dimensions",
        default="",
        help="Comma-separated dimensions. If omitted, runs all 6 V2_DIMENSIONS.",
    )
    parser.add_argument("--output-dir", default="/tmp/worklist_smoke", help="Directory to write JSON outputs.")
    parser.add_argument("--resume", action="store_true", help="Reuse existing per-dimension JSON files if present.")
    args = parser.parse_args()

    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

