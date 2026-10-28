#!/usr/bin/env python3
"""
Export a single Markdown report that combines:
- Target PIR (listing)
- V2 strategy selection + V2 delta scopes (per strategy) + referenced comparable PIRs
- V3 strategy specs (per strategy)
- V4 pricing summaries (per strategy)
- BOQ analysis explaining why one strategy is higher/lower (focus: top_of_market vs others)

Usage:
  .venv/bin/python -u scripts/export_v4_postrich_analysis_md.py --listing-id 12
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402


def _json_block(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n"


def _money(x: float) -> str:
    return f"{x:,.2f}"


def _by_v4_dimension(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows or []:
        prov = (r.get("provenance") or {}) if isinstance(r, dict) else {}
        dim = str((prov or {}).get("v4_dimension") or "unknown")
        out[dim].append(r)
    return out


def _sum_by_code(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = defaultdict(float)
    for r in rows or []:
        code = str(r.get("bcca_code") or "").strip()
        if not code:
            continue
        out[code] += float(r.get("line_total") or 0.0)
    return out


def _top_code_deltas(*, a_rows: List[Dict[str, Any]], b_rows: List[Dict[str, Any]], limit: int = 15) -> List[Tuple[float, str, float, float]]:
    """
    Return deltas as (delta, code, a_cost, b_cost) where delta = a_cost - b_cost.
    """
    a = _sum_by_code(a_rows)
    b = _sum_by_code(b_rows)
    codes = set(a.keys()) | set(b.keys())
    deltas: List[Tuple[float, str, float, float]] = []
    for c in codes:
        ac = float(a.get(c, 0.0))
        bc = float(b.get(c, 0.0))
        deltas.append((ac - bc, c, ac, bc))
    deltas.sort(key=lambda t: abs(t[0]), reverse=True)
    return deltas[:limit]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--strategies", nargs="*", default=["conservative", "market_standard", "top_of_market"])
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    strategies = [str(s).strip() for s in (args.strategies or []) if str(s).strip()]
    if not strategies:
        raise RuntimeError("No strategies provided")

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(backend_root, "reports", f"v4_postrich_analysis_listing_{listing_id}.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    db = Database()

    now = datetime.now(timezone.utc).isoformat()
    md: List[str] = []
    md.append("## V4 Post-rich Analysis\n\n")
    md.append(f"- Listing ID: **{listing_id}**\n")
    md.append(f"- Exported at (UTC): **{now}**\n")
    md.append(f"- Strategies: **{', '.join(strategies)}**\n\n")

    # ---- Target PIR ----
    target_pir = await db.get_pir(listing_id, pir_type="target")
    md.append("## Target PIR (pir_type=target)\n\n")
    md.append(_json_block(target_pir))

    # ---- V2 shared artifacts ----
    v2_strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    md.append("\n## V2 Strategy Selection\n\n")
    md.append("### v2_strategy_selection\n\n")
    md.append(_json_block(v2_strategy_selection))

    # ---- Load BOQ rows once per strategy (v4) ----
    boq_rows_by_strategy: Dict[str, List[Dict[str, Any]]] = {}
    for s in strategies:
        boq_rows_by_strategy[s] = await db.get_boq_line_items(listing_id, s, dimension="v4")

    # ---- Pricing summaries ----
    pricing_by_strategy: Dict[str, Dict[str, Any]] = {}
    for s in strategies:
        pricing_by_strategy[s] = (await db.get_unified_estimate(listing_id, f"v4_pricing_summary_{s}")) or {}

    md.append("\n## V4 Pricing Summary (post-rich)\n\n")
    md.append("| strategy | total_cost | total_labor_hours | line_items |\n")
    md.append("|---|---:|---:|---:|\n")
    for s in strategies:
        ps = pricing_by_strategy.get(s) or {}
        md.append(
            f"| `{s}` | {_money(float(ps.get('total_cost') or 0))} | "
            f"{float(ps.get('total_labor_hours') or 0):.2f} | {int(ps.get('line_items_count') or 0)} |\n"
        )
    md.append("\n")

    md.append("### By-dimension totals\n\n")
    md.append("| dimension | " + " | ".join([f"{s}_cost" for s in strategies]) + " |\n")
    md.append("|---|" + "|".join(["---:"] * len(strategies)) + "|\n")
    for dim in V2_DIMENSIONS:
        row = [f"`{dim}`"]
        for s in strategies:
            ps = pricing_by_strategy.get(s) or {}
            by = (ps.get("by_dimension") or {}) if isinstance(ps.get("by_dimension"), dict) else {}
            cost = float(((by.get(dim) or {}).get("total_cost") or 0.0)) if isinstance(by.get(dim), dict) else 0.0
            row.append(_money(cost))
        md.append("| " + " | ".join(row) + " |\n")
    md.append("\n")

    # ---- Strategy specs + deltas + comparable PIRs ----
    md.append("## Strategy Specs + Deltas + Comparable PIRs\n\n")
    comparable_ids: Dict[str, int] = {}

    for s in strategies:
        md.append(f"### Strategy: `{s}`\n\n")

        spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{s}")
        md.append(f"#### v3_strategy_spec_{s}\n\n")
        md.append(_json_block(spec))

        delta = await db.get_unified_estimate(listing_id, f"v2_delta_{s}")
        md.append(f"\n#### v2_delta_{s}\n\n")
        md.append(_json_block(delta))

        cid = None
        try:
            cid = int((delta or {}).get("reference_comparable_id") or 0) or None
        except Exception:
            cid = None
        if cid:
            comparable_ids[s] = cid
            comp_pir = await db.get_pir(cid, pir_type="comparable")
            md.append(f"\n#### Comparable PIR (listing_id={cid}, pir_type=comparable)\n\n")
            md.append(_json_block(comp_pir))
        else:
            md.append("\n#### Comparable PIR\n\n")
            md.append("_No reference_comparable_id found in v2_delta._\n\n")

    # ---- BOQ analysis: why top_of_market is lower ----
    md.append("\n## Analysis: Why is `top_of_market` cheaper?\n\n")
    md.append(
        "This section compares `top_of_market` against the other strategies using **actual BOQ line items**.\n\n"
    )

    if "top_of_market" in boq_rows_by_strategy:
        top_rows = boq_rows_by_strategy["top_of_market"]
        top_by_dim = _by_v4_dimension(top_rows)

        for other in [s for s in strategies if s != "top_of_market"]:
            other_rows = boq_rows_by_strategy.get(other) or []
            other_by_dim = _by_v4_dimension(other_rows)

            md.append(f"### top_of_market vs {other}\n\n")

            top_total = float((pricing_by_strategy.get("top_of_market") or {}).get("total_cost") or 0.0)
            other_total = float((pricing_by_strategy.get(other) or {}).get("total_cost") or 0.0)
            md.append(f"- Total delta (top_of_market - {other}): **{_money(top_total - other_total)}**\n\n")

            # Identify which dimensions drive the delta (using pricing summaries).
            md.append("#### Dimension deltas (top_of_market - other)\n\n")
            md.append("| dimension | top_cost | other_cost | delta |\n")
            md.append("|---|---:|---:|---:|\n")
            top_ps = pricing_by_strategy.get("top_of_market") or {}
            oth_ps = pricing_by_strategy.get(other) or {}
            top_by = (top_ps.get("by_dimension") or {}) if isinstance(top_ps.get("by_dimension"), dict) else {}
            oth_by = (oth_ps.get("by_dimension") or {}) if isinstance(oth_ps.get("by_dimension"), dict) else {}
            deltas = []
            for dim in V2_DIMENSIONS:
                tc = float(((top_by.get(dim) or {}).get("total_cost") or 0.0)) if isinstance(top_by.get(dim), dict) else 0.0
                oc = float(((oth_by.get(dim) or {}).get("total_cost") or 0.0)) if isinstance(oth_by.get(dim), dict) else 0.0
                deltas.append((tc - oc, dim, tc, oc))
            deltas.sort(key=lambda t: abs(t[0]), reverse=True)
            for delta_cost, dim, tc, oc in deltas:
                md.append(f"| `{dim}` | {_money(tc)} | {_money(oc)} | {_money(delta_cost)} |\n")
            md.append("\n")

            # For the top 2 delta-driving dimensions, show biggest BCCA code deltas.
            md.append("#### Biggest BCCA code deltas in key dimensions\n\n")
            key_dims = [d[1] for d in deltas[:2]]
            for dim in key_dims:
                md.append(f"##### Dimension: `{dim}`\n\n")
                trows = top_by_dim.get(dim) or []
                orows = other_by_dim.get(dim) or []
                deltas_codes = _top_code_deltas(a_rows=trows, b_rows=orows, limit=20)
                md.append("| bcca_code | top_cost | other_cost | delta |\n")
                md.append("|---|---:|---:|---:|\n")
                for dc, code, tc, oc in deltas_codes:
                    md.append(f"| `{code}` | {_money(tc)} | {_money(oc)} | {_money(dc)} |\n")
                md.append("\n")

            md.append(
                "Interpretation notes:\n\n"
                "- If a dimension delta is large and is driven by **a few codes**, it usually indicates either scope differences or a small number of high-impact BCCA matches.\n"
                "- If a dimension delta is large and is spread across many codes, it suggests a broader scope/quantity difference.\n\n"
            )
    else:
        md.append("Missing `top_of_market` BOQ rows; cannot analyze.\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

