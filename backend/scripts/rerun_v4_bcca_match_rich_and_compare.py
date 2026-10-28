#!/usr/bin/env python3
"""
Re-run V4 BCCA matching using the "rich query packet" mode and compare vs existing matches.

What this does:
- Loads existing v4_worklist_{strategy}_{dim}
- Loads baseline matches: v4_bcca_matches_{strategy}_{dim}
- Recomputes matches with query_mode="rich"
- Saves new matches to unified_estimates as: v4_bcca_matches_rich_{strategy}_{dim}
- Writes a Markdown comparison report summarizing changes and flagging obvious nonsense codes.

NO LLM calls. Embeddings are computed via Vertex TextEmbeddingModel (same as runtime).

Usage:
  .venv/bin/python -u scripts/rerun_v4_bcca_match_rich_and_compare.py --listing-id 12
"""

from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pricing.embedding_runtime import embed_texts  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import _get_default_bcca_matcher, match_v4_bcca  # type: ignore  # noqa: E402


SUSPICIOUS_CODE_PREFIXES = [
    # office / IT / unrelated equipment (seen in bad runs)
    "08OU",  # office equipment
]

SUSPICIOUS_DESC_SUBSTRINGS = [
    "equipo pc",
    "monitor",
    "teclado",
    "ratón",
    "papelera pública",
    "pavimento gránulo caucho",
    "fibrocemento/amianto",
]


def _md_escape(s: str) -> str:
    return (s or "").replace("`", "\\`")


def _is_suspicious_match(code: str, desc_100: str) -> bool:
    c = (code or "").strip().upper()
    d = (desc_100 or "").strip().lower()
    if any(c.startswith(p) for p in SUSPICIOUS_CODE_PREFIXES):
        return True
    if any(x in d for x in SUSPICIOUS_DESC_SUBSTRINGS):
        return True
    return False


def _index_matches_by_work_item(matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for m in matches or []:
        if not isinstance(m, dict):
            continue
        wid = str(m.get("work_item_id") or "").strip()
        if not wid:
            continue
        out[wid] = m
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
    default_out = os.path.join(backend_root, "reports", f"v4_bcca_match_compare_rich_listing_{listing_id}.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    db = Database()
    matcher = _get_default_bcca_matcher()

    now = datetime.now(timezone.utc).isoformat()
    md: List[str] = []
    md.append("## V4 BCCA Matching — Baseline vs Rich Query Packet\n\n")
    md.append(f"- Listing ID: **{listing_id}**\n")
    md.append(f"- Exported at (UTC): **{now}**\n")
    md.append(f"- Strategies: **{', '.join(strategies)}**\n")
    md.append("- New artifacts saved as `v4_bcca_matches_rich_{strategy}_{dimension}`\n\n")

    global_summary_rows: List[Tuple[str, str, int, int, int, int]] = []
    # (strategy, dim, n_items, n_changed, n_suspicious_old, n_suspicious_rich)

    for strat in strategies:
        md.append(f"### Strategy: `{_md_escape(strat)}`\n\n")

        strat_changed = 0
        strat_total = 0
        strat_susp_old = 0
        strat_susp_new = 0

        for dim in V2_DIMENSIONS:
            pkg_worklist = f"v4_worklist_{strat}_{dim}"
            worklist_dim = await db.get_unified_estimate(listing_id, pkg_worklist)
            if not isinstance(worklist_dim, dict):
                md.append(f"- Missing worklist: `{_md_escape(pkg_worklist)}`\n")
                continue

            pkg_old = f"v4_bcca_matches_{strat}_{dim}"
            old_payload = await db.get_unified_estimate(listing_id, pkg_old)
            old_matches = (old_payload or {}).get("matches") if isinstance(old_payload, dict) else []
            if not isinstance(old_matches, list):
                old_matches = []

            # Recompute rich matches and save
            rich_matches = await match_v4_bcca(
                listing_id=listing_id,
                strategy_name=strat,
                dimension=dim,
                worklist_dim=worklist_dim,
                matcher=matcher,
                embed_texts_fn=embed_texts,
                query_mode="rich",
            )
            pkg_new = f"v4_bcca_matches_rich_{strat}_{dim}"
            await db.save_unified_estimate(listing_id, pkg_new, {"matches": rich_matches})

            old_by = _index_matches_by_work_item(old_matches)
            new_by = _index_matches_by_work_item(rich_matches)

            # Consider all WIDs present in either set.
            wids = sorted(set(old_by.keys()) | set(new_by.keys()))
            n_items = len(wids)
            n_changed = 0
            changed_examples: List[Tuple[str, str, str, float, str, str, float]] = []
            # (wid, room_id, old_code, old_sim, new_code, new_desc, new_sim)

            susp_old = 0
            susp_new = 0

            for wid in wids:
                o = old_by.get(wid) or {}
                n = new_by.get(wid) or {}
                old_code = str(o.get("bcca_code") or "").strip()
                new_code = str(n.get("bcca_code") or "").strip()
                old_desc = str(o.get("bcca_desc_100") or "").strip()
                new_desc = str(n.get("bcca_desc_100") or "").strip()

                if _is_suspicious_match(old_code, old_desc):
                    susp_old += 1
                if _is_suspicious_match(new_code, new_desc):
                    susp_new += 1

                if old_code and new_code and old_code != new_code:
                    n_changed += 1
                    changed_examples.append(
                        (
                            wid,
                            str(n.get("room_id") or o.get("room_id") or "").strip(),
                            old_code,
                            float(o.get("embedding_similarity") or 0.0),
                            new_code,
                            new_desc,
                            float(n.get("embedding_similarity") or 0.0),
                        )
                    )

            changed_examples.sort(key=lambda r: (r[2], r[4], r[0]))

            strat_total += n_items
            strat_changed += n_changed
            strat_susp_old += susp_old
            strat_susp_new += susp_new
            global_summary_rows.append((strat, dim, n_items, n_changed, susp_old, susp_new))

            md.append(f"#### Dimension: `{_md_escape(dim)}`\n\n")
            md.append(f"- Items compared: **{n_items}**\n")
            md.append(f"- Changed code: **{n_changed}**\n")
            md.append(f"- Suspicious matches (old → rich): **{susp_old} → {susp_new}**\n")
            md.append(f"- Artifacts: `{_md_escape(pkg_old)}` vs `{_md_escape(pkg_new)}`\n\n")

            if changed_examples:
                md.append("Top changed examples (first 15):\n\n")
                md.append("| work_item_id | room_id | old_code (sim) | new_code (sim) | new_desc_100 |\n")
                md.append("|---|---:|---:|---:|---|\n")
                for wid, room_id, old_code, old_sim, new_code, new_desc, new_sim in changed_examples[:15]:
                    md.append(
                        f"| `{_md_escape(wid)}` | `{_md_escape(room_id)}` | `{_md_escape(old_code)}` ({old_sim:.3f}) | "
                        f"`{_md_escape(new_code)}` ({new_sim:.3f}) | {_md_escape(new_desc)[:120]} |\n"
                    )
                md.append("\n")

        md.append(f"- Strategy totals: items **{strat_total}**, changed **{strat_changed}**, suspicious **{strat_susp_old} → {strat_susp_new}**\n\n")

    # Global summary table
    md.append("### Summary (all strategies × dimensions)\n\n")
    md.append("| strategy | dimension | items | changed | suspicious_old | suspicious_rich |\n")
    md.append("|---|---|---:|---:|---:|---:|\n")
    for strat, dim, n_items, n_changed, susp_old, susp_new in global_summary_rows:
        md.append(f"| `{_md_escape(strat)}` | `{_md_escape(dim)}` | {n_items} | {n_changed} | {susp_old} | {susp_new} |\n")
    md.append("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

