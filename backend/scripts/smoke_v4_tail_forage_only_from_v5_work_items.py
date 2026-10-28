#!/usr/bin/env python3
"""
Smoke: V4 tail — FORAGE ONLY (from V5 work items + existing matches/plans)
=========================================================================

Runs ONLY the forage step (room photos + optional floorplan photos) to measure the numeric signals
requested by existing quant plans.

Inputs (must already exist):
- unified_estimates: v5_work_items_market_standard
- unified_estimates: v4_bcca_matches_market_standard_{dimension}
- unified_estimates: v4_quant_plan_market_standard_{dimension}

Writes:
- unified_estimates: v4_signals_market_standard (and v4_signals_shared)
- markdown report: backend/reports/smoke_v4_tail_forage_only_from_v5_{listing_id}.md

Why:
- Make the forage step observable and QA-able in isolation (before BOQ assembly).

Usage:
  .venv/bin/python scripts/smoke_v4_tail_forage_only_from_v5_work_items.py --listing-id 12 --concurrency 5 --force
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import call_gemini_json, fetch_images_batch  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import (  # noqa: E402
    _extract_floorplan_urls,
    _room_photo_urls_by_id,
    forage_v4_signals_for_room,
    resolve_zero_signals_for_room,
)
from scripts._md_report import write_md_report  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _require(cond: bool, msg: str) -> None:
    if cond:
        return
    raise RuntimeError(msg)


def _collect_signal_ids(formula_ast: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if not isinstance(formula_ast, dict):
        return out
    op = str(formula_ast.get("op") or "").strip()
    if op == "SIGNAL":
        sid = str(formula_ast.get("signal_id") or "").strip()
        if sid:
            out.append(sid)
        return out
    arg = formula_ast.get("arg")
    if isinstance(arg, dict):
        out.extend(_collect_signal_ids(arg))
    args = formula_ast.get("args")
    if isinstance(args, list):
        for a in args:
            if isinstance(a, dict):
                out.extend(_collect_signal_ids(a))
    return out


def _infer_unit_family_from_signal_id(signal_id: str) -> str:
    sid = str(signal_id or "").strip().lower()
    for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
        if sid.endswith(suf):
            return uf
    # We intentionally fail loud in forage if planner violates naming rules.
    raise RuntimeError(f"forage_only: signal_id missing unit suffix | signal_id={signal_id}")


def _load_signals_payload_into_store(*, payload: Any, store: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    if not isinstance(payload, dict):
        return
    for rr in payload.get("rooms") or []:
        if not isinstance(rr, dict):
            continue
        rid = str(rr.get("room_id") or "").strip()
        sigs = rr.get("signals") or []
        if not rid or not isinstance(sigs, list):
            continue
        store.setdefault(rid, {})
        for s in sigs:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("signal_id") or "").strip()
            if sid:
                store[rid][sid] = s


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--concurrency", type=int, default=5, help="Rooms in parallel (forage calls).")
    p.add_argument("--force", action="store_true", help="Ignore saved signals and re-forage missing signals from scratch.")
    args = p.parse_args()

    listing_id = int(args.listing_id)
    concurrency = int(args.concurrency)
    force = bool(args.force)
    if concurrency < 1:
        raise ValueError(f"concurrency must be >= 1 (got {concurrency})")

    strategy_name = "market_standard"
    db = Database()

    # Listing context (optional, but improves inference quality when floorplan is missing).
    try:
        listing = await db.get_listing(listing_id)
    except Exception:
        listing = None
    listing_sqm = None
    try:
        if isinstance(listing, dict) and listing.get("sqm") is not None:
            listing_sqm = float(listing.get("sqm"))
    except Exception:
        listing_sqm = None

    # Evidence
    clusters = await db.get_photo_clusters(listing_id)
    _require(bool(clusters), f"forage_only: missing photo_clusters | listing_id={listing_id}")
    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    _require(bool(room_photos), f"forage_only: no room photos found | listing_id={listing_id}")

    # NOTE: Smart M2 is removed from the V5 path. Forage + zero-rescue are authoritative.
    smart_m2 = {"rooms": []}

    # Required signals per room are derived from quant plans (which are tied to matches/work items).
    # Also collect work-item context for the zero-rescue pass.
    required_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    # signal_work_items_map: (room_id, signal_id) -> list of {work_item_id, work_description, bcca_desc_100}
    signal_work_items_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    total_plans = 0
    for dim in V2_DIMENSIONS:
        pkg_plan = f"v4_quant_plan_{strategy_name}_{dim}"
        plan = await db.get_unified_estimate(listing_id, pkg_plan)
        plans = (plan or {}).get("plans") if isinstance(plan, dict) else None
        _require(isinstance(plans, list) and plans, f"forage_only: missing quant plan | package_type={pkg_plan}")
        total_plans += len(plans)

        # Need room_id per work_item_id from bcca matches
        pkg_matches = f"v4_bcca_matches_{strategy_name}_{dim}"
        matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
        matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
        _require(isinstance(matches, list) and matches, f"forage_only: missing bcca matches | package_type={pkg_matches}")
        matches_by_item = {
            str(m.get("work_item_id")): m
            for m in matches
            if isinstance(m, dict) and str(m.get("work_item_id") or "").strip()
        }

        for pl in plans:
            if not isinstance(pl, dict):
                continue
            wid = str(pl.get("work_item_id") or "").strip()
            if not wid:
                continue
            match = matches_by_item.get(wid) or {}
            rid = str(match.get("room_id") or "").strip()
            _require(bool(rid), f"forage_only: missing room_id for plan | dim={dim} work_item_id={wid}")
            f = pl.get("formula_ast")
            _require(isinstance(f, dict), f"forage_only: missing formula_ast | work_item_id={wid}")
            for sid in sorted(set(_collect_signal_ids(f))):
                required_by_room.setdefault(rid, {})
                required_by_room[rid][sid] = {"signal_id": sid, "unit_family": _infer_unit_family_from_signal_id(sid)}
                # Track which work items use this signal (for zero-rescue context)
                key = (rid, sid)
                signal_work_items_map.setdefault(key, [])
                signal_work_items_map[key].append({
                    "work_item_id": wid,
                    "work_description": str(match.get("work_description") or "").strip(),
                    "bcca_desc_100": str(match.get("bcca_desc_100") or "").strip(),
                })

    _require(bool(required_by_room), f"forage_only: no required signals derived | listing_id={listing_id}")

    # Load saved signals to avoid re-foraging unless force=True
    signals_store_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not force:
        try:
            shared = await db.get_unified_estimate(listing_id, "v4_signals_shared")
        except Exception:
            shared = None
        _load_signals_payload_into_store(payload=shared, store=signals_store_by_room)
        try:
            strat = await db.get_unified_estimate(listing_id, f"v4_signals_{strategy_name}")
        except Exception:
            strat = None
        _load_signals_payload_into_store(payload=strat, store=signals_store_by_room)

    # Forage rooms
    forage_sem = asyncio.Semaphore(concurrency)
    checkpoint_lock = asyncio.Lock()

    async def _checkpoint(*, reason: str) -> None:
        async with checkpoint_lock:
            rooms_payload: List[Dict[str, Any]] = []
            signal_count = 0
            for rid in sorted(signals_store_by_room.keys()):
                sigs_by_id = signals_store_by_room.get(rid) or {}
                signals_list = [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]
                signal_count += len(signals_list)
                rooms_payload.append({"room_id": rid, "signals": signals_list})
            payload = {"rooms": rooms_payload}
            logger.info(
                "forage_only: checkpoint | reason=%s rooms=%s signals=%s listing_id=%s strategy=%s",
                reason,
                len(rooms_payload),
                signal_count,
                listing_id,
                strategy_name,
            )
            await db.save_unified_estimate(listing_id, f"v4_signals_{strategy_name}", payload)
            await db.save_unified_estimate(listing_id, "v4_signals_shared", payload)

    async def _forage_one_room(rid: str) -> Dict[str, Any]:
        async with forage_sem:
            reqs_by_id = required_by_room.get(rid) or {}
            _require(bool(reqs_by_id), f"forage_only: no required signals for room | room_id={rid}")
            if rid not in signals_store_by_room:
                signals_store_by_room[rid] = {}

            existing_ids = set(signals_store_by_room[rid].keys())
            want_ids = [sid for sid in reqs_by_id.keys() if sid not in existing_ids] if not force else list(reqs_by_id.keys())
            want_ids = sorted(set([sid for sid in want_ids if sid in reqs_by_id]))
            if not want_ids:
                return {"room_id": rid, "status": "skipped", "missing": 0, "measured": 0}

            room_urls = room_photos.get(rid) or []
            _require(bool(room_urls), f"forage_only: room has no photos | room_id={rid}")

            want_requests = [reqs_by_id[sid] for sid in want_ids]
            measured = await forage_v4_signals_for_room(
                listing_id=listing_id,
                strategy_name=strategy_name,
                room_id=rid,
                measurement_requests=want_requests,
                floorplan_available=floorplan_available,
                listing_sqm=listing_sqm,
                room_photo_urls=room_urls,
                floorplan_urls=floorplan_urls,
                smart_m2=smart_m2,
                call_gemini_json=call_gemini_json,
                fetch_images_batch=fetch_images_batch,
                allow_missing_smart_m2_room=True,
            )
            _require(isinstance(measured, dict) and measured, f"forage_only: empty measured signals | room_id={rid}")
            signals_store_by_room[rid].update(measured)
            await _checkpoint(reason=f"room_complete room_id={rid} new={len(measured)}")
            return {"room_id": rid, "status": "ok", "missing": len(want_ids), "measured": len(measured)}

    logger.info(
        "forage_only: start | listing_id=%s strategy=%s rooms=%s concurrency=%s floorplan_available=%s total_plans=%s",
        listing_id,
        strategy_name,
        len(required_by_room),
        concurrency,
        floorplan_available,
        total_plans,
    )

    tasks = [asyncio.create_task(_forage_one_room(rid)) for rid in sorted(required_by_room.keys())]
    results: List[Dict[str, Any]] = []
    try:
        for t in asyncio.as_completed(tasks):
            results.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    # ========================================================================
    # ZERO RESCUE PASS — Pro + photos reasoning for zero-valued signals
    # ========================================================================
    zeros_before = 0
    zeros_after = 0
    rescue_results: List[Dict[str, Any]] = []

    for rid in sorted(required_by_room.keys()):
        room_sigs = signals_store_by_room.get(rid) or {}
        zero_sids = [
            sid
            for sid, sig in room_sigs.items()
            if isinstance(sig, dict) and float(sig.get("value") or 0) == 0.0
        ]
        if not zero_sids:
            continue

        zeros_before += len(zero_sids)
        logger.info("zero_rescue: room=%s zeros=%s signals=%s", rid, len(zero_sids), zero_sids)

        # Build work-item context for each zero signal
        zero_signals_with_context: List[Dict[str, Any]] = []
        for sid in zero_sids:
            req = required_by_room.get(rid, {}).get(sid) or {}
            work_items_ctx = signal_work_items_map.get((rid, sid)) or []
            zero_signals_with_context.append({
                "signal_id": sid,
                "unit_family": req.get("unit_family") or _infer_unit_family_from_signal_id(sid),
                "work_items": work_items_ctx,
            })

        # Nonzero signals in this room (anchors)
        nonzero_signals = [
            {
                "signal_id": sig.get("signal_id"),
                "unit_family": sig.get("unit_family"),
                "value": sig.get("value"),
                "confidence": sig.get("confidence"),
            }
            for sid, sig in room_sigs.items()
            if isinstance(sig, dict) and float(sig.get("value") or 0) > 0
        ]

        room_urls = room_photos.get(rid) or []
        if not room_urls:
            logger.warning("zero_rescue: no photos for room=%s, skipping", rid)
            zeros_after += len(zero_sids)
            rescue_results.append({"room_id": rid, "status": "skipped_no_photos", "zeros_in": len(zero_sids), "resolved": 0})
            continue

        try:
            resolved = await resolve_zero_signals_for_room(
                listing_id=listing_id,
                strategy_name=strategy_name,
                room_id=rid,
                zero_signals_with_context=zero_signals_with_context,
                nonzero_signals=nonzero_signals,
                floorplan_available=floorplan_available,
                listing_sqm=listing_sqm,
                room_estimated_m2=None,
                room_photo_urls=room_urls,
                floorplan_urls=floorplan_urls,
                call_gemini_json=call_gemini_json,
                fetch_images_batch=fetch_images_batch,
            )
        except Exception as exc:
            logger.error("zero_rescue: failed for room=%s err=%s", rid, exc)
            zeros_after += len(zero_sids)
            rescue_results.append({"room_id": rid, "status": "error", "zeros_in": len(zero_sids), "resolved": 0, "error": str(exc)})
            continue

        # Merge resolved signals into store (overwrite the zeros)
        resolved_count = 0
        for sid, sig in resolved.items():
            if isinstance(sig, dict) and float(sig.get("value") or 0) > 0:
                signals_store_by_room[rid][sid] = sig
                resolved_count += 1

        remaining_zeros = len(zero_sids) - resolved_count
        zeros_after += remaining_zeros
        rescue_results.append({"room_id": rid, "status": "ok", "zeros_in": len(zero_sids), "resolved": resolved_count, "remaining_zeros": remaining_zeros})
        logger.info("zero_rescue: room=%s resolved=%s/%s", rid, resolved_count, len(zero_sids))

        await _checkpoint(reason=f"zero_rescue_complete room_id={rid} resolved={resolved_count}")

    if zeros_before > 0:
        logger.info(
            "zero_rescue: DONE | zeros_before=%s zeros_after=%s resolved=%s",
            zeros_before,
            zeros_after,
            zeros_before - zeros_after,
        )

    # Final report summary
    total_required = sum(len(reqs or {}) for reqs in required_by_room.values())
    total_have = sum(len((signals_store_by_room.get(rid) or {}).keys()) for rid in required_by_room.keys())
    # Count final zeros
    final_zeros = 0
    for rid in required_by_room.keys():
        for sid, sig in (signals_store_by_room.get(rid) or {}).items():
            if isinstance(sig, dict) and float(sig.get("value") or 0) == 0.0:
                final_zeros += 1

    payload = {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "concurrency": concurrency,
        "floorplan_available": floorplan_available,
        "rooms": results,
        "required_signals_total": total_required,
        "signals_in_store_total": total_have,
        "zero_rescue": {
            "zeros_before_rescue": zeros_before,
            "zeros_after_rescue": zeros_after,
            "resolved": zeros_before - zeros_after,
            "final_zeros_in_store": final_zeros,
            "rooms": rescue_results,
        },
        "counts": {
            "rooms_total": len(required_by_room),
            "rooms_ok": sum(1 for r in results if r.get("status") == "ok"),
            "rooms_skipped": sum(1 for r in results if r.get("status") == "skipped"),
        },
    }

    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v4_tail_forage_only_from_v5_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V4 tail — forage only (from V5 work items + existing matches/plans)",
        meta={"listing_id": listing_id, "strategy_name": strategy_name, "source_key": "v5_work_items_market_standard"},
        sample=payload,
        payload=payload,
    )
    print(json.dumps({"stage": "v4_tail_forage_only_from_v5", "listing_id": listing_id, "report_path": report_path}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

