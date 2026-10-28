#!/usr/bin/env python3
"""
Deterministic audit for V4 worklist ↔ BCCA match coherence.

What this does (NO LLM calls):
- Loads V4 worklists + V4 BCCA matches for a listing from unified_estimates
- Builds a small keyword vocabulary (from the per-dimension BCCA lexicon in v4_quantification_pipeline)
- Derives "never-together" keyword pairs deterministically from the BCCA corpus:
    For keywords that each occur >= MIN_COUNT times in BCCA desc_100, if they never co-occur in the same
    BCCA line, we treat them as mutually exclusive.
- Flags matches where work_description contains keyword A while matched bcca_desc_100 contains keyword B,
  and (A,B) is mutually exclusive (and B is not also present in the work text).

Usage:
  .venv/bin/python -u scripts/audit_v4_matching_deterministic.py --listing-id 12
  .venv/bin/python -u scripts/audit_v4_matching_deterministic.py --listing-id 12 --out backend/reports/v4_audit_12.md
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402
from pricing.v4_quantification_pipeline import _get_default_bcca_matcher  # type: ignore  # noqa: E402


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _work_item_ids_from_worklist(worklist_dim: Dict[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    for rb in (worklist_dim.get("room_blocks") or []):
        if not isinstance(rb, dict):
            continue
        for pkg in (rb.get("scope_packages") or []):
            if not isinstance(pkg, dict):
                continue
            wid = str(pkg.get("work_item_id") or "").strip()
            if wid:
                ids.add(wid)
    return ids


def _desc_by_id_from_worklist(worklist_dim: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for rb in (worklist_dim.get("room_blocks") or []):
        if not isinstance(rb, dict):
            continue
        for pkg in (rb.get("scope_packages") or []):
            if not isinstance(pkg, dict):
                continue
            wid = str(pkg.get("work_item_id") or "").strip()
            if not wid:
                continue
            out[wid] = str(pkg.get("work_description") or "").strip()
    return out


def _keyword_pattern(kw: str) -> re.Pattern[str]:
    # Match whole word-ish tokens, but allow accents and slashes inside the kw itself.
    # e.g., "rodapié" or "galeria_/_lavadero" won't be used here; this is for short keywords.
    return re.compile(rf"(?<![a-z0-9_]){re.escape(kw)}(?![a-z0-9_])", re.IGNORECASE)


def _keywords_present(text: str, keywords: Sequence[str]) -> Set[str]:
    t = _norm(text)
    out: Set[str] = set()
    for kw in keywords:
        if not kw:
            continue
        if _keyword_pattern(kw).search(t):
            out.add(kw)
    return out


def _lexicon_keywords_from_pipeline() -> List[str]:
    """
    Keep this deterministic and small:
    - Start from the worklist lexicon we already added (v4_quantification_pipeline.py)
    - Add a few high-signal head nouns that help catch obvious collisions.
    """
    from pricing.v4_quantification_pipeline import build_v4_worklist_prompt  # noqa: F401
    # Hardcode to avoid brittle parsing of prompt strings: mirror the dict in v4_quantification_pipeline.
    bcca_lexicon_by_dim: Dict[str, Dict[str, List[str]]] = {
        "shell_preparation": {
            "nouns": ["demolición", "retirada", "desmontaje", "carga", "transporte", "vertedero", "protección", "tapiado", "cegado", "apertura de hueco"],
        },
        "apertures_enclosure": {
            "nouns": ["ventana", "balconera", "corredera", "abatible", "carpintería", "aluminio", "madera", "persiana", "cajón", "vidrio", "doble acristalamiento", "rpt", "sellado", "premarco"],
        },
        "systems_services": {
            "nouns": ["punto de luz", "mecanismo", "interruptor", "toma de corriente", "enchufe", "cuadro", "circuito", "toma de agua", "desagüe", "radiador", "rejilla", "difusor", "conducto", "termostato"],
        },
        "surface_finishes": {
            "nouns": ["alicatado", "solado", "pavimento", "revestimiento", "rodapié", "pintura", "enlucido", "yeso", "junta", "lechada", "impermeabilización"],
        },
        "fixed_joinery_equipment": {
            "nouns": ["mobiliario", "cocina", "mueble", "lavabo", "encimera", "zócalo", "armario", "frente", "estantería", "baldas", "columna"],
        },
        "details_fittings": {
            "nouns": ["sanitario", "lavabo", "inodoro", "plato", "ducha", "mampara", "grifería", "espejo", "accesorio", "barra", "asidero", "toallero", "herrajes"],
        },
    }

    # IMPORTANT:
    # "Never together" only makes sense for head-nouns (not generic verbs/process words like "desmontaje"/"vertedero").
    # Keep a focused, high-signal noun list.
    hard_nouns: Set[str] = {
        # apertures/enclosure
        "puerta",
        "ventana",
        "balconera",
        "persiana",
        # services
        "radiador",
        "rejilla",
        "difusor",
        "termostato",
        "interruptor",
        "enchufe",
        # finishes
        "alicatado",
        "solado",
        "rodapié",
        "pintura",
        # fittings / equipment
        "lavabo",
        "lavadero",
        "fregadero",
        "inodoro",
        "mampara",
        "ducha",
        "encimera",
        "armario",
        "estantería",
        "mueble",
    }

    # Also include any lexicon nouns that are themselves head-nouns and appear in the dict above (no expansion).
    out = sorted({n for n in hard_nouns if n})
    return out


@dataclass(frozen=True)
class Conflict:
    work_kw: str
    bcca_kw: str


def _derive_mutual_exclusions_from_bcca(
    *,
    bcca_descs: Sequence[str],
    keywords: Sequence[str],
    min_count: int,
) -> Set[Tuple[str, str]]:
    """
    Returns ordered pairs (a,b) such that:
      - a and b each occur in >= min_count BCCA lines
      - a and b never co-occur in the same BCCA line
    """
    kws = list(keywords)
    pats = {kw: _keyword_pattern(kw) for kw in kws}
    counts: Dict[str, int] = {kw: 0 for kw in kws}
    cooc: Dict[Tuple[str, str], int] = {}

    for raw in bcca_descs:
        present = [kw for kw, pat in pats.items() if pat.search(raw or "")]
        for kw in present:
            counts[kw] += 1
        # mark co-occurrences within the line
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = present[i], present[j]
                key = (a, b) if a < b else (b, a)
                cooc[key] = cooc.get(key, 0) + 1

    frequent = [kw for kw, c in counts.items() if c >= min_count]
    frequent_set = set(frequent)

    exclusions: Set[Tuple[str, str]] = set()
    # Only consider among frequent keywords.
    for i, a in enumerate(frequent):
        for b in frequent[i + 1 :]:
            key = (a, b) if a < b else (b, a)
            if cooc.get(key, 0) == 0:
                exclusions.add((a, b))
                exclusions.add((b, a))
    return exclusions


def _find_conflicts(
    *,
    work_desc: str,
    bcca_desc: str,
    keywords: Sequence[str],
    exclusions: Set[Tuple[str, str]],
) -> List[Conflict]:
    work_present = _keywords_present(work_desc, keywords)
    bcca_present = _keywords_present(bcca_desc, keywords)
    conflicts: List[Conflict] = []
    for a in work_present:
        for b in bcca_present:
            if a == b:
                continue
            if (a, b) in exclusions and b not in work_present:
                conflicts.append(Conflict(work_kw=a, bcca_kw=b))
    # stable order
    conflicts.sort(key=lambda c: (c.work_kw, c.bcca_kw))
    return conflicts


def _md_escape(s: str) -> str:
    return s.replace("`", "\\`")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--strategies", nargs="*", default=["conservative", "market_standard", "top_of_market"])
    parser.add_argument("--min-count", type=int, default=60, help="Min BCCA occurrence for a keyword to be considered in exclusions.")
    parser.add_argument("--max-examples", type=int, default=20, help="Max examples to print per strategy/dimension.")
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    strategies = [str(s).strip() for s in (args.strategies or []) if str(s).strip()]
    if not strategies:
        raise RuntimeError("No strategies provided")

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(backend_root, "reports", f"v4_audit_matching_listing_{listing_id}.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Build exclusion rules from the BCCA corpus (deterministic).
    matcher = _get_default_bcca_matcher()
    meta_by_code = matcher.get_metadata_by_code_map()
    bcca_descs = [str(m.get("desc_100") or m.get("description") or "") for m in meta_by_code.values() if isinstance(m, dict)]
    keywords = _lexicon_keywords_from_pipeline()
    exclusions = _derive_mutual_exclusions_from_bcca(bcca_descs=bcca_descs, keywords=keywords, min_count=int(args.min_count))

    db = Database()
    md: List[str] = []
    md.append("## V4 Deterministic Audit — Worklist ↔ BCCA Match\n\n")
    md.append(f"- Listing ID: **{listing_id}**\n")
    md.append(f"- Strategies: **{', '.join(strategies)}**\n")
    md.append(f"- Keyword universe size: **{len(keywords)}**\n")
    md.append(f"- Mutual-exclusion rules (directed pairs): **{len(exclusions)}** (min_count={int(args.min_count)})\n\n")

    total_flagged = 0
    for strat in strategies:
        md.append(f"### Strategy: `{_md_escape(strat)}`\n\n")
        for dim in V2_DIMENSIONS:
            wl = await db.get_unified_estimate(listing_id, f"v4_worklist_{strat}_{dim}")
            mp = await db.get_unified_estimate(listing_id, f"v4_bcca_matches_{strat}_{dim}")
            if not isinstance(wl, dict) or not isinstance(mp, dict):
                md.append(f"- `{dim}`: missing artifacts\n")
                continue
            work_ids = _work_item_ids_from_worklist(wl)
            desc_by_id = _desc_by_id_from_worklist(wl)
            matches = mp.get("matches") or []
            if not isinstance(matches, list) or not matches:
                md.append(f"- `{dim}`: empty matches\n")
                continue

            flagged_rows: List[Tuple[float, str, str, str, List[Conflict]]] = []
            for m in matches:
                if not isinstance(m, dict):
                    continue
                wid = str(m.get("work_item_id") or "").strip()
                if not wid or wid not in work_ids:
                    continue
                work_desc = desc_by_id.get(wid) or ""
                bcca_desc = str(m.get("bcca_desc_100") or m.get("desc_100") or m.get("bcca_full_desc") or "").strip()
                sim = float(m.get("embedding_similarity") or 0.0)
                conflicts = _find_conflicts(work_desc=work_desc, bcca_desc=bcca_desc, keywords=keywords, exclusions=exclusions)
                if conflicts:
                    flagged_rows.append((sim, wid, str(m.get("room_id") or ""), bcca_desc, conflicts))

            flagged_rows.sort(key=lambda r: r[0], reverse=True)
            total_flagged += len(flagged_rows)
            md.append(f"#### Dimension: `{dim}`\n\n")
            md.append(f"- Work items in worklist: **{len(work_ids)}**\n")
            md.append(f"- Matches: **{len(matches)}**\n")
            md.append(f"- Flagged by mutual-exclusion collisions: **{len(flagged_rows)}**\n\n")
            if not flagged_rows:
                continue

            md.append("Top flagged examples (highest similarity first):\n\n")
            for sim, wid, rid, bcca_desc, conflicts in flagged_rows[: int(args.max_examples)]:
                work_desc = desc_by_id.get(wid) or ""
                md.append(f"- **sim={sim:.3f}** `work_item_id={_md_escape(wid)}` `room_id={_md_escape(rid)}`\n")
                md.append(f"  - conflicts: `{', '.join([c.work_kw + '↔' + c.bcca_kw for c in conflicts[:6]])}`\n")
                md.append(f"  - work: {_md_escape(work_desc)}\n")
                md.append(f"  - bcca: {_md_escape(bcca_desc)}\n")
            md.append("\n")

    md.insert(0, f"# V4 Deterministic Matching Audit\n\nTotal flagged matches: **{total_flagged}**\n\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

