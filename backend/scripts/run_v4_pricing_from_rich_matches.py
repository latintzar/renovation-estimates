#!/usr/bin/env python3
"""
Run V4 pricing using the saved "rich query packet" BCCA matches.

This performs a shadow pricing run without overwriting baseline V4 BOQ rows:
- Reads worklists: v4_worklist_{strategy}_{dim}
- Reads rich matches: v4_bcca_matches_rich_{strategy}_{dim}
- Reuses baseline quant plan when valid; otherwise regenerates and saves:
    v4_quant_plan_rich_{strategy}_{dim}
- Reuses existing signals: v4_signals_shared + v4_signals_{strategy}
- Assembles BOQ line items into boq_line_items.dimension = "v4_rich"
- Saves pricing summaries to unified_estimates:
    v4_pricing_summary_rich_{strategy}
- Writes a markdown comparison report:
    baseline v4_pricing_summary_{strategy} vs rich v4_pricing_summary_rich_{strategy}

Usage:
  .venv/bin/python -u scripts/run_v4_pricing_from_rich_matches.py --listing-id 12
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database, get_client, _get_base_url, _get_headers  # noqa: E402
from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import (  # noqa: E402
    _extract_floorplan_urls,
    _get_default_bcca_matcher,
    _plans_validate_or_raise,
    _room_photo_urls_by_id,
    forage_v4_signals_for_room,
    assemble_v4_boq,
    generate_v4_quant_plan,
)


def _json_block(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n"


def _load_signals_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Convert stored payload of shape:
      {"rooms":[{"room_id": "...", "signals":[{"signal_id": "...", ...}, ...]}, ...]}
    into:
      { room_id: { signal_id: signal_obj } }
    """
    store: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not isinstance(payload, dict):
        return store
    rooms = payload.get("rooms") or []
    if not isinstance(rooms, list):
        return store
    for rr in rooms:
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
    return store


def _signals_store_to_payload(store: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    rooms_payload: List[Dict[str, Any]] = []
    for rid in sorted(store.keys()):
        sigs_by_id = store.get(rid) or {}
        signals_list = [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]
        rooms_payload.append({"room_id": rid, "signals": signals_list})
    return {"rooms": rooms_payload}


def _collect_signal_ids(node: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    op = node.get("op")
    if op == "SIGNAL":
        sid = str(node.get("signal_id") or "").strip()
        if sid:
            out.append(sid)
        return out
    arg = node.get("arg")
    if isinstance(arg, dict):
        out.extend(_collect_signal_ids(arg))
    args = node.get("args")
    if isinstance(args, list):
        for a in args:
            if isinstance(a, dict):
                out.extend(_collect_signal_ids(a))
    return out


def _infer_unit_family_from_signal_id(signal_id: str) -> str:
    sid = signal_id.strip().lower()
    for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
        if sid.endswith(suf):
            return uf
    raise RuntimeError(f"v4_rich: signal_id missing unit suffix | signal_id={signal_id}")


async def _delete_boq_dimension(*, listing_id: int, strategy_name: str, dimension: str) -> None:
    client = await get_client()
    base = _get_base_url()
    url = f"{base}/boq_line_items"
    params = {
        "listing_id": f"eq.{listing_id}",
        "strategy_name": f"eq.{strategy_name}",
        "dimension": f"eq.{dimension}",
    }
    resp = await client.delete(url, params=params, headers=_get_headers())
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"delete boq_line_items failed | status={resp.status_code} body={resp.text[:500]}")


async def _compute_pricing_summary(*, listing_id: int, strategy_name: str, boq_dimension: str) -> Dict[str, Any]:
    client = await get_client()
    base = _get_base_url()
    url = (
        f"{base}/boq_line_items?"
        f"listing_id=eq.{listing_id}&strategy_name=eq.{strategy_name}&dimension=eq.{boq_dimension}"
        f"&select=line_total,labor_hours,provenance"
    )
    resp = await client.get(url, headers=_get_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"fetch boq_line_items failed | status={resp.status_code} body={resp.text[:500]}")
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
        "dimension": boq_dimension,
        "total_cost": total_cost,
        "total_labor_hours": total_hours,
        "by_dimension": by_dim,
        "line_items_count": len(rows),
        "match_mode": "rich_query_packet",
        "v05_schema_continuity": True,
    }


def _sum_by_code(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = defaultdict(float)
    for r in rows or []:
        code = str(r.get("bcca_code") or "").strip()
        if not code:
            continue
        out[code] += float(r.get("line_total") or 0)
    return out


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--strategies", nargs="*", default=["conservative", "market_standard", "top_of_market"])
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    strategies = [str(s).strip() for s in (args.strategies or []) if str(s).strip()]
    if not strategies:
        raise RuntimeError("No strategies provided")

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(backend_root, "reports", f"v4_pricing_compare_rich_listing_{listing_id}.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    db = Database()

    # Context needed for quant-plan regeneration (only if needed).
    clusters = await db.get_photo_clusters(listing_id)
    smart_m2 = await db.get_smart_m2(listing_id)
    if not clusters or not smart_m2:
        raise RuntimeError(f"Missing clusters/smart_m2 | listing_id={listing_id}")
    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    room_has_photos = {rid: True for rid in room_photos.keys()}

    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    # Signals: shared + per-strategy (same shape). We'll merge: strategy overrides shared.
    shared_payload = await db.get_unified_estimate(listing_id, "v4_signals_rich_shared")
    if not isinstance(shared_payload, dict):
        shared_payload = await db.get_unified_estimate(listing_id, "v4_signals_shared")
    shared_store = _load_signals_payload(shared_payload)

    md: List[str] = []
    now = datetime.now(timezone.utc).isoformat()
    md.append("## V4 Pricing — Baseline vs Rich Matching\n\n")
    md.append(f"- Listing ID: **{listing_id}**\n")
    md.append(f"- Exported at (UTC): **{now}**\n")
    md.append(f"- Strategies: **{', '.join(strategies)}**\n")
    md.append("- Baseline BOQ table dimension: `v4`\n")
    md.append("- Rich BOQ table dimension: `v4_rich`\n\n")

    for strat in strategies:
        md.append(f"### Strategy: `{strat}`\n\n")

        # Delete any prior shadow run rows.
        await _delete_boq_dimension(listing_id=listing_id, strategy_name=strat, dimension="v4_rich")

        strat_payload = await db.get_unified_estimate(listing_id, f"v4_signals_rich_{strat}")
        if not isinstance(strat_payload, dict):
            strat_payload = await db.get_unified_estimate(listing_id, f"v4_signals_{strat}")
        strat_store = _load_signals_payload(strat_payload)
        # Merge: strategy overrides shared.
        signals_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for rid, sigs in shared_store.items():
            signals_by_room[rid] = dict(sigs)
        for rid, sigs in strat_store.items():
            signals_by_room.setdefault(rid, {})
            signals_by_room[rid].update(sigs)

        used_plans: Dict[str, Dict[str, Any]] = {}

        # Assemble BOQ for each dimension
        for dim in V2_DIMENSIONS:
            worklist = await db.get_unified_estimate(listing_id, f"v4_worklist_{strat}_{dim}")
            if not isinstance(worklist, dict):
                raise RuntimeError(f"Missing worklist | listing_id={listing_id} strategy={strat} dim={dim}")

            rich_payload = await db.get_unified_estimate(listing_id, f"v4_bcca_matches_rich_{strat}_{dim}")
            rich_matches = (rich_payload or {}).get("matches") if isinstance(rich_payload, dict) else None
            if not isinstance(rich_matches, list) or not rich_matches:
                raise RuntimeError(f"Missing rich matches | listing_id={listing_id} strategy={strat} dim={dim}")

            # Try to reuse baseline plan if valid against these matches; otherwise regen and save separately.
            plan = await db.get_unified_estimate(listing_id, f"v4_quant_plan_{strat}_{dim}")
            ok = isinstance(plan, dict) and isinstance(plan.get("plans"), list) and bool(plan.get("plans"))
            if ok:
                try:
                    matches_by_item = {
                        m.get("work_item_id"): m for m in rich_matches if isinstance(m, dict) and m.get("work_item_id")
                    }
                    _plans_validate_or_raise(plan=plan, bcca_matches_by_item=matches_by_item, bcca_meta_by_code=bcca_meta_by_code)
                except Exception:
                    ok = False

            if not ok:
                plan = await generate_v4_quant_plan(
                    listing_id=listing_id,
                    strategy_name=strat,
                    dimension=dim,
                    worklist_dim=worklist,
                    bcca_matches=rich_matches,
                    floorplan_available=floorplan_available,
                    room_has_photos=room_has_photos,
                    call_gemini=call_gemini,
                    bcca_meta_by_code=bcca_meta_by_code,
                )

            # Save the plan we used (even if reused) under a rich package name for auditability.
            used_plans[dim] = plan  # type: ignore[assignment]
            await db.save_unified_estimate(listing_id, f"v4_quant_plan_rich_{strat}_{dim}", plan)

            # Ensure required signals exist (forage only missing).
            required_by_room: Dict[str, List[str]] = defaultdict(list)
            matches_by_item = {
                m.get("work_item_id"): m for m in rich_matches if isinstance(m, dict) and m.get("work_item_id")
            }
            for p in (plan.get("plans") or []):
                if not isinstance(p, dict):
                    continue
                wid = str(p.get("work_item_id") or "").strip()
                match = matches_by_item.get(wid) or {}
                rid = str(match.get("room_id") or "").strip()
                if not rid:
                    continue
                formula_ast = p.get("formula_ast")
                if not isinstance(formula_ast, dict):
                    continue
                required_by_room[rid].extend(_collect_signal_ids(formula_ast))
            for rid in list(required_by_room.keys()):
                required_by_room[rid] = sorted(set([s for s in required_by_room[rid] if s]))

            for rid, required_sids in required_by_room.items():
                have = set((signals_by_room.get(rid) or {}).keys())
                missing = [sid for sid in required_sids if sid not in have]
                if not missing:
                    continue
                reqs = [{"signal_id": sid, "unit_family": _infer_unit_family_from_signal_id(sid)} for sid in missing]
                found = await forage_v4_signals_for_room(
                    listing_id=listing_id,
                    strategy_name=strat,
                    room_id=rid,
                    measurement_requests=reqs,
                    floorplan_available=floorplan_available,
                    room_photo_urls=room_photos.get(rid) or [],
                    floorplan_urls=floorplan_urls,
                    smart_m2=smart_m2,
                    call_gemini_json=call_gemini_json,
                    fetch_images_batch=fetch_images_batch,
                )
                signals_by_room.setdefault(rid, {})
                signals_by_room[rid].update(found)
                await db.save_unified_estimate(listing_id, f"v4_signals_rich_{strat}", _signals_store_to_payload(signals_by_room))
                await db.save_unified_estimate(listing_id, "v4_signals_rich_shared", _signals_store_to_payload(signals_by_room))

            await assemble_v4_boq(
                listing_id=listing_id,
                strategy_name=strat,
                dimension=dim,
                bcca_matches=rich_matches,
                quant_plan=plan,  # type: ignore[arg-type]
                signals_by_room=signals_by_room,
                db=db,
                boq_table_dimension="v4_rich",
                match_mode="rich_query_packet",
            )

        # Pricing summaries
        baseline_summary = await db.get_unified_estimate(listing_id, f"v4_pricing_summary_{strat}")
        rich_summary = await _compute_pricing_summary(listing_id=listing_id, strategy_name=strat, boq_dimension="v4_rich")
        await db.save_unified_estimate(listing_id, f"v4_pricing_summary_rich_{strat}", rich_summary)

        md.append("#### Pricing totals\n\n")
        md.append("| run | total_cost | total_labor_hours | line_items |\n")
        md.append("|---|---:|---:|---:|\n")
        md.append(
            f"| baseline (`v4`) | {float((baseline_summary or {}).get('total_cost') or 0):.2f} | "
            f"{float((baseline_summary or {}).get('total_labor_hours') or 0):.2f} | "
            f"{int((baseline_summary or {}).get('line_items_count') or 0)} |\n"
        )
        md.append(
            f"| rich (`v4_rich`) | {float(rich_summary.get('total_cost') or 0):.2f} | "
            f"{float(rich_summary.get('total_labor_hours') or 0):.2f} | {int(rich_summary.get('line_items_count') or 0)} |\n"
        )
        md.append("\n")

        # By-dimension delta table
        md.append("#### By-dimension deltas (rich - baseline)\n\n")
        md.append("| dimension | baseline_cost | rich_cost | delta |\n")
        md.append("|---|---:|---:|---:|\n")
        b_by = (baseline_summary or {}).get("by_dimension") or {}
        r_by = rich_summary.get("by_dimension") or {}
        for dim in V2_DIMENSIONS:
            bc = float(((b_by.get(dim) or {}).get("total_cost") or 0)) if isinstance(b_by, dict) else 0.0
            rc = float(((r_by.get(dim) or {}).get("total_cost") or 0)) if isinstance(r_by, dict) else 0.0
            md.append(f"| `{dim}` | {bc:.2f} | {rc:.2f} | {(rc - bc):.2f} |\n")
        md.append("\n")

        # Top code deltas using boq_line_items (baseline vs rich)
        base_rows = await db.get_boq_line_items(listing_id, strat, dimension="v4")
        rich_rows = await db.get_boq_line_items(listing_id, strat, dimension="v4_rich")
        base_sum = _sum_by_code(base_rows)
        rich_sum = _sum_by_code(rich_rows)
        all_codes = set(base_sum.keys()) | set(rich_sum.keys())
        deltas = []
        for c in all_codes:
            deltas.append((rich_sum.get(c, 0.0) - base_sum.get(c, 0.0), c, base_sum.get(c, 0.0), rich_sum.get(c, 0.0)))
        deltas.sort(key=lambda t: abs(t[0]), reverse=True)
        md.append("#### Biggest BCCA code cost deltas (absolute)\n\n")
        md.append("| bcca_code | baseline_cost | rich_cost | delta |\n")
        md.append("|---|---:|---:|---:|\n")
        for delta, code, bc, rc in deltas[:20]:
            md.append(f"| `{code}` | {bc:.2f} | {rc:.2f} | {delta:.2f} |\n")
        md.append("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

