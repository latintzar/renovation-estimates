#!/usr/bin/env python3
"""
Run V4 pricing end-to-end for all strategies available for a listing.

WHY THIS EXISTS:
- We want pricing + labor-hours (time) for ALL 6 dimensions across ALL strategies.
- We keep behavior fail-loud (no guessy quantities).
- We persist auditable outputs into unified_estimates + boq_line_items.

Usage:
  .venv/bin/python scripts/run_v4_all_strategies.py --listing-id 12
  .venv/bin/python scripts/run_v4_all_strategies.py --listing-id 12 --strategies conservative market_standard
"""

import argparse
import asyncio
import os
import sys
import json
import logging
from typing import Any, Dict, List

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database, get_client, _get_base_url, _get_headers
from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch
from pricing.embedding_runtime import embed_texts
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
from pricing.v4_quantification_pipeline import (
    assemble_v4_boq,
    forage_v4_signals_for_room,
    generate_v4_quant_plan,
    generate_v4_worklist_for_dimension,
    match_v4_bcca,
)
from pricing.v4_quantification_pipeline import _get_default_bcca_matcher  # type: ignore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_v4_all_strategies")

# Force line-buffered output so logs appear within timeout slices.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass
async def _list_strategies(listing_id: int) -> List[str]:
    client = await get_client()
    base = _get_base_url()
    url = f"{base}/unified_estimates?listing_id=eq.{listing_id}&package_type=like.v3_strategy_spec_%25&select=package_type"
    resp = await client.get(url, headers=_get_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"list_strategies failed | status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json()
    out: List[str] = []
    for r in rows:
        pt = str((r or {}).get("package_type") or "").strip()
        if not pt.startswith("v3_strategy_spec_"):
            continue
        out.append(pt.replace("v3_strategy_spec_", "", 1))
    out = sorted(set(out))
    if not out:
        raise RuntimeError(f"No strategies found for listing {listing_id} (expected v3_strategy_spec_*)")
    return out


async def _compute_v4_pricing_summary(*, listing_id: int, strategy_name: str) -> Dict[str, Any]:
    client = await get_client()
    base = _get_base_url()
    url = (
        f"{base}/boq_line_items?"
        f"listing_id=eq.{listing_id}&strategy_name=eq.{strategy_name}&dimension=eq.v4"
        f"&select=line_total,labor_hours,provenance"
    )
    resp = await client.get(url, headers=_get_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"fetch_v4_boq failed | status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json()
    by_dim: Dict[str, Dict[str, float]] = {}
    total_cost = 0.0
    total_hours = 0.0
    for r in rows:
        prov = (r or {}).get("provenance") or {}
        dim = str((prov or {}).get("v4_dimension") or "unknown")
        line_total = float((r or {}).get("line_total") or 0)
        labor_hours = (r or {}).get("labor_hours")
        labor_hours_f = float(labor_hours) if labor_hours is not None else 0.0
        by_dim.setdefault(dim, {"total_cost": 0.0, "total_labor_hours": 0.0, "line_items": 0.0})
        by_dim[dim]["total_cost"] += line_total
        by_dim[dim]["total_labor_hours"] += labor_hours_f
        by_dim[dim]["line_items"] += 1.0
        total_cost += line_total
        total_hours += labor_hours_f
    return {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "dimension": "v4",
        "total_cost": total_cost,
        "total_labor_hours": total_hours,
        "by_dimension": by_dim,
        "line_items_count": len(rows),
        "v05_schema_continuity": True,
    }


def _write_md_report(
    *,
    listing_id: int,
    strategy_name: str,
    artifacts: Dict[str, Any],
    pricing: Dict[str, Any],
    report_path: str,
) -> None:
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# V4 Pricing Report\\n\\n")
        f.write(f"- Listing ID: {listing_id}\\n")
        f.write(f"- Strategy: {strategy_name}\\n\\n")

        f.write("## Pricing Summary\\n\\n")
        f.write("```json\\n")
        f.write(json.dumps(pricing, ensure_ascii=False, indent=2))
        f.write("\\n```\\n\\n")

        for key, payload in artifacts.items():
            f.write(f"## {key}\\n\\n")
            f.write("```json\\n")
            f.write(json.dumps(payload, ensure_ascii=False, indent=2))
            f.write("\\n```\\n\\n")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--strategies", nargs="*", default=None)
    parser.add_argument("--force", action="store_true", default=False, help="Clear existing V4 BOQ rows before running each strategy.")
    parser.add_argument(
        "--stop-after",
        default=None,
        choices=["worklist", "bcca_match", "quant_plan", "forage_shared", "assemble"],
        help="Stop after completing this phase (for resumable timeout slices / debugging).",
    )
    args = parser.parse_args()

    listing_id: int = int(args.listing_id)
    strategies: List[str]
    if args.strategies:
        strategies = [str(s).strip() for s in args.strategies if str(s).strip()]
    else:
        strategies = await _list_strategies(listing_id)

    db = Database()

    logger.info(f"v4_all: listing_id={listing_id} | strategies={strategies}")

    # Load listing-level context ONCE (avoid re-fetching per strategy).
    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"v4_all: missing photo_clusters | listing_id={listing_id}")
    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        raise RuntimeError(f"v4_all: missing smart_m2 | listing_id={listing_id}")
    target_pir = await db.get_pir(listing_id, pir_type="target")
    if not target_pir:
        raise RuntimeError(f"v4_all: missing target PIR | listing_id={listing_id}")

    # Derive room photo urls + floorplan urls (same policy as pipeline).
    from pricing.v4_quantification_pipeline import _extract_floorplan_urls, _room_photo_urls_by_id  # type: ignore

    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    if not room_photos:
        raise RuntimeError(f"v4_all: no room photos found | listing_id={listing_id}")
    room_has_photos = {rid: True for rid in room_photos.keys()}

    # Canonical room ids come from Smart M2 (and must have photos).
    room_ids: List[str] = []
    for r in (smart_m2.get("rooms") or []):
        if isinstance(r, dict):
            rid = str(r.get("room_id") or r.get("cluster_id") or "").strip()
            if rid:
                if rid not in room_photos:
                    raise RuntimeError(f"v4_all: smart_m2 room has no photo cluster | room_id={rid}")
                room_ids.append(rid)
    if not room_ids:
        raise RuntimeError(f"v4_all: no canonical room_ids from smart_m2 | listing_id={listing_id}")

    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    # ----------------------------
    # PHASE 1: WORKLISTS for ALL strategies (no images)
    # ----------------------------
    logger.info("v4_all: phase=worklist | starting (bounded concurrency)")
    worklist_sem = asyncio.Semaphore(3)

    strategy_specs: Dict[str, Dict[str, Any]] = {}
    for strat in strategies:
        strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strat}")
        if not strategy_spec:
            raise RuntimeError(f"v4_all: missing strategy_spec | listing_id={listing_id} strategy={strat}")
        strategy_specs[strat] = strategy_spec

    async def _ensure_worklist(strat: str, dim: str) -> None:
        async with worklist_sem:
            pkg_worklist = f"v4_worklist_{strat}_{dim}"
            worklist_dim = await db.get_unified_estimate(listing_id, pkg_worklist)
            if isinstance(worklist_dim, dict):
                return
            worklist_dim = await generate_v4_worklist_for_dimension(
                listing_id=listing_id,
                strategy_name=strat,
                dimension=dim,
                strategy_spec=strategy_specs[strat],
                target_pir=target_pir,
                room_ids=room_ids,
                call_gemini=call_gemini,
            )
            await db.save_unified_estimate(listing_id, pkg_worklist, worklist_dim)

    await asyncio.gather(*[_ensure_worklist(strat, dim) for strat in strategies for dim in V2_DIMENSIONS])

    if args.stop_after == "worklist":
        logger.info("v4_all: stop-after=worklist (requested)")
        return 0

    # ----------------------------
    # PHASE 2: BCCA MATCHES for ALL strategies (no images)
    # ----------------------------
    for strat in strategies:
        logger.info(f"v4_all: phase=bcca_match | strategy={strat}")
        for dim in V2_DIMENSIONS:
            pkg_worklist = f"v4_worklist_{strat}_{dim}"
            worklist_dim = await db.get_unified_estimate(listing_id, pkg_worklist)
            if not isinstance(worklist_dim, dict):
                raise RuntimeError(f"Missing expected artifact | package_type={pkg_worklist}")

            pkg_matches = f"v4_bcca_matches_{strat}_{dim}"
            matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
            bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
            if isinstance(bcca_matches, list) and bcca_matches:
                continue

            bcca_matches = await match_v4_bcca(
                listing_id=listing_id,
                strategy_name=strat,
                dimension=dim,
                worklist_dim=worklist_dim,
                matcher=matcher,
                embed_texts_fn=embed_texts,
            )
            await db.save_unified_estimate(listing_id, pkg_matches, {"matches": bcca_matches})

    if args.stop_after == "bcca_match":
        logger.info("v4_all: stop-after=bcca_match (requested)")
        return 0

    # ----------------------------
    # PHASE 3: QUANT PLANS for ALL strategies (no images)
    # ----------------------------
    # NOTE: Strategy order stays serial, but dimensions are generated concurrently per strategy.
    # This is the main latency bottleneck otherwise (6 sequential Pro calls per strategy).
    from pricing.v4_quantification_pipeline import _plans_validate_or_raise  # type: ignore

    quant_plan_sem = asyncio.Semaphore(6)  # all 6 dimensions at once (per user request)

    for strat in strategies:
        logger.info(f"v4_all: phase=quant_plan | strategy={strat} (dims in parallel)")

        async def _ensure_quant_plan(dim: str) -> None:
            async with quant_plan_sem:
                pkg_plan = f"v4_quant_plan_{strat}_{dim}"
                quant_plan = await db.get_unified_estimate(listing_id, pkg_plan)
                has_cached_plan = (
                    isinstance(quant_plan, dict)
                    and isinstance(quant_plan.get("plans"), list)
                    and bool(quant_plan.get("plans"))
                )
                if has_cached_plan:
                    # Keep cached plan only if it passes current validation.
                    try:
                        pkg_matches = f"v4_bcca_matches_{strat}_{dim}"
                        matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
                        bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
                        if not isinstance(bcca_matches, list) or not bcca_matches:
                            raise RuntimeError(f"Missing expected artifact | package_type={pkg_matches}")
                        matches_by_item = {
                            m.get("work_item_id"): m
                            for m in bcca_matches
                            if isinstance(m, dict) and m.get("work_item_id")
                        }
                        _plans_validate_or_raise(
                            plan=quant_plan,
                            bcca_matches_by_item=matches_by_item,
                            bcca_meta_by_code=bcca_meta_by_code,
                        )
                        await db.save_unified_estimate(listing_id, pkg_plan, quant_plan)
                        return
                    except Exception as exc:
                        logger.warning(
                            "v4_all: cached quant plan invalid; regenerating "
                            f"| dim={dim} listing_id={listing_id} strategy={strat} err={exc}"
                        )

                pkg_worklist = f"v4_worklist_{strat}_{dim}"
                worklist_dim = await db.get_unified_estimate(listing_id, pkg_worklist)
                if not isinstance(worklist_dim, dict):
                    raise RuntimeError(f"Missing expected artifact | package_type={pkg_worklist}")

                pkg_matches = f"v4_bcca_matches_{strat}_{dim}"
                matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
                bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
                if not isinstance(bcca_matches, list) or not bcca_matches:
                    raise RuntimeError(f"Missing expected artifact | package_type={pkg_matches}")

                quant_plan2 = await generate_v4_quant_plan(
                    listing_id=listing_id,
                    strategy_name=strat,
                    dimension=dim,
                    worklist_dim=worklist_dim,
                    bcca_matches=bcca_matches,
                    floorplan_available=floorplan_available,
                    room_has_photos=room_has_photos,
                    call_gemini=call_gemini,
                    bcca_meta_by_code=bcca_meta_by_code,
                )
                await db.save_unified_estimate(listing_id, pkg_plan, quant_plan2)

        await asyncio.gather(*[_ensure_quant_plan(dim) for dim in V2_DIMENSIONS])

    if args.stop_after == "quant_plan":
        logger.info("v4_all: stop-after=quant_plan (requested)")
        return 0

    # ----------------------------
    # PHASE 4: SHARED FORAGE ONCE (images) using union of ALL strategies' required signals
    # ----------------------------
    def _infer_unit_family_from_signal_id(signal_id: str) -> str:
        sid = str(signal_id or "").strip().lower()
        for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
            if sid.endswith(suf):
                return uf
        raise RuntimeError(f"v4_all: signal_id missing unit suffix | signal_id={signal_id}")

    required_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for strat in strategies:
        for dim in V2_DIMENSIONS:
            pkg_matches = f"v4_bcca_matches_{strat}_{dim}"
            matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
            bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
            if not isinstance(bcca_matches, list) or not bcca_matches:
                raise RuntimeError(f"Missing expected artifact | package_type={pkg_matches}")
            room_by_item = {
                m.get("work_item_id"): str(m.get("room_id") or "").strip()
                for m in bcca_matches
                if isinstance(m, dict) and m.get("work_item_id")
            }
            pkg_plan = f"v4_quant_plan_{strat}_{dim}"
            quant_plan = await db.get_unified_estimate(listing_id, pkg_plan)
            plans = (quant_plan or {}).get("plans") if isinstance(quant_plan, dict) else None
            if not isinstance(plans, list) or not plans:
                raise RuntimeError(f"Missing expected artifact | package_type={pkg_plan}")
            for p in plans:
                if not isinstance(p, dict):
                    continue
                wid = str(p.get("work_item_id") or "").strip()
                rid = str(room_by_item.get(wid) or "").strip()
                if not rid:
                    raise RuntimeError(f"v4_all: missing room_id for plan item | work_item_id={wid} dim={dim} strategy={strat}")
                formula = p.get("formula_ast")
                if not isinstance(formula, dict) or str(formula.get("op") or "").strip() != "SIGNAL":
                    raise RuntimeError(f"v4_all: invalid formula_ast (expected SIGNAL) | work_item_id={wid} dim={dim} strategy={strat}")
                sid = str(formula.get("signal_id") or "").strip()
                if not sid:
                    raise RuntimeError(f"v4_all: missing signal_id | work_item_id={wid} dim={dim} strategy={strat}")
                required_by_room.setdefault(rid, {})
                required_by_room[rid][sid] = {"signal_id": sid, "unit_family": _infer_unit_family_from_signal_id(sid)}

    # Load existing shared signals for resume.
    signals_store_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    saved_shared = await db.get_unified_estimate(listing_id, "v4_signals_shared")
    if isinstance(saved_shared, dict):
        for rr in saved_shared.get("rooms") or []:
            if isinstance(rr, dict):
                rid = str(rr.get("room_id") or "").strip()
                sigs = rr.get("signals") or []
                if rid and isinstance(sigs, list):
                    signals_store_by_room.setdefault(rid, {})
                    for s in sigs:
                        if isinstance(s, dict):
                            sid = str(s.get("signal_id") or "").strip()
                            if sid:
                                signals_store_by_room[rid][sid] = s

    async def _checkpoint_shared(*, reason: str) -> None:
        rooms_payload: List[Dict[str, Any]] = []
        for rid in sorted(signals_store_by_room.keys()):
            sigs_by_id = signals_store_by_room.get(rid) or {}
            rooms_payload.append({"room_id": rid, "signals": [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]})
        payload = {"rooms": rooms_payload}
        logger.info(f"v4_all: checkpoint shared signals | reason={reason} rooms={len(rooms_payload)} listing_id={listing_id}")
        await db.save_unified_estimate(listing_id, "v4_signals_shared", payload)
        # Also store per-strategy signals (same payload) to satisfy required outputs.
        for strat in strategies:
            await db.save_unified_estimate(listing_id, f"v4_signals_{strat}", payload)

    logger.info("v4_all: phase=forage_shared | starting (this is the first time images may be fetched)")
    forage_sem = asyncio.Semaphore(3)
    checkpoint_lock = asyncio.Lock()
    room_locks: Dict[str, asyncio.Lock] = {rid: asyncio.Lock() for rid in required_by_room.keys()}

    async def _forage_room(rid: str) -> None:
        async with forage_sem:
            async with room_locks[rid]:
                signals_store_by_room.setdefault(rid, {})
                existing = set(signals_store_by_room[rid].keys())
                want = [sid for sid in required_by_room[rid].keys() if sid not in existing]
                if not want:
                    return
                want_requests = [required_by_room[rid][sid] for sid in want]
                measured = await forage_v4_signals_for_room(
                    listing_id=listing_id,
                    strategy_name="shared",
                    room_id=rid,
                    measurement_requests=want_requests,
                    floorplan_available=floorplan_available,
                    room_photo_urls=room_photos.get(rid) or [],
                    floorplan_urls=floorplan_urls,
                    smart_m2=smart_m2,
                    call_gemini_json=call_gemini_json,
                    fetch_images_batch=fetch_images_batch,
                )
                signals_store_by_room[rid].update(measured)
                # Serialize checkpoint writes (they write the full payload).
                async with checkpoint_lock:
                    await _checkpoint_shared(reason=f"room={rid} new={len(measured)}")

    await asyncio.gather(*[_forage_room(rid) for rid in sorted(required_by_room.keys())])

    await _checkpoint_shared(reason="final")

    if args.stop_after == "forage_shared":
        logger.info("v4_all: stop-after=forage_shared (requested)")
        return 0

    # ----------------------------
    # PHASE 5: ASSEMBLE BOQ + PRICING + REPORTS per strategy (uses shared signals; no more images)
    # ----------------------------
    for strat in strategies:
        logger.info(f"v4_all: phase=assemble | strategy={strat}")
        if bool(args.force):
            await db.clear_boq_line_items_by_dimension(listing_id, strategy_name=strat, dimension="v4")

        summary: Dict[str, Any] = {
            "listing_id": listing_id,
            "strategy_name": strat,
            "floorplan_available": floorplan_available,
            "room_count": len(room_ids),
            "dimensions": {},
        }
        saved_total = 0
        for dim in V2_DIMENSIONS:
            pkg_matches = f"v4_bcca_matches_{strat}_{dim}"
            matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
            bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
            if not isinstance(bcca_matches, list) or not bcca_matches:
                raise RuntimeError(f"Missing expected artifact | package_type={pkg_matches}")

            pkg_plan = f"v4_quant_plan_{strat}_{dim}"
            quant_plan = await db.get_unified_estimate(listing_id, pkg_plan)
            if not (isinstance(quant_plan, dict) and isinstance(quant_plan.get("plans"), list) and quant_plan.get("plans")):
                raise RuntimeError(f"Missing expected artifact | package_type={pkg_plan}")

            saved = await assemble_v4_boq(
                listing_id=listing_id,
                strategy_name=strat,
                dimension=dim,
                bcca_matches=bcca_matches,
                quant_plan=quant_plan,
                signals_by_room=signals_store_by_room,
                db=db,
            )
            saved_total += int(saved)
            summary["dimensions"][dim] = {"saved_boq_items": int(saved)}

        summary["saved_boq_items_total"] = int(saved_total)
        await db.save_unified_estimate(listing_id, f"v4_run_summary_{strat}", summary)

        pricing = await _compute_v4_pricing_summary(listing_id=listing_id, strategy_name=strat)
        await db.save_unified_estimate(listing_id, f"v4_pricing_summary_{strat}", pricing)

        artifacts: Dict[str, Any] = {
            "v4_run_summary": summary,
            "v4_pricing_summary": pricing,
            "v4_signals_shared": await db.get_unified_estimate(listing_id, "v4_signals_shared"),
            f"v4_signals_{strat}": await db.get_unified_estimate(listing_id, f"v4_signals_{strat}"),
        }
        for dim in V2_DIMENSIONS:
            for prefix in ("v4_worklist", "v4_bcca_matches", "v4_quant_plan"):
                pkg = f"{prefix}_{strat}_{dim}"
                payload = await db.get_unified_estimate(listing_id, pkg)
                if payload is None:
                    raise RuntimeError(f"Missing expected artifact | package_type={pkg}")
                artifacts[pkg] = payload

        report_path = os.path.join(
            BACKEND_ROOT,
            "reports",
            f"v4_pricing_listing_{listing_id}_{strat}.md",
        )
        _write_md_report(
            listing_id=listing_id,
            strategy_name=strat,
            artifacts=artifacts,
            pricing=pricing,
            report_path=report_path,
        )
        logger.info(
            f"v4_all: saved pricing summary | strategy={strat} | line_items={pricing['line_items_count']} "
            f"| total_cost={pricing['total_cost']:.2f} | labor_hours={pricing['total_labor_hours']:.2f}"
        )
        logger.info(f"v4_all: saved report | {report_path}")

    logger.info("v4_all: DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

