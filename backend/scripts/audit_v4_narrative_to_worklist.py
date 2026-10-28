#!/usr/bin/env python3
"""
Audit: V3 narrative intent -> V4 worklist coverage (per strategy, dimension, room).

Deterministic (NO LLM calls).

Usage:
  .venv/bin/python -u scripts/audit_v4_narrative_to_worklist.py --listing-id 12
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS  # noqa: E402


# Regex-based token matching, to avoid false “missing” due to word forms / synonyms.
# Key: "token label" (what we report). Value: regex pattern.
TOKEN_PATTERNS_BY_DIM: Dict[str, Dict[str, str]] = {
    "shell_preparation": {
        "demolición": r"\bdemolic(?:i[oó]n|ionar|ionar\w*)\b|\bdemoler\b",
        "retirada": r"\bretirad[ao]s?\b|\bretirar\b",
        "desmontaje": r"\bdesmontaj(?:e|es)\b|\bdesmontar\b",
        "protección": r"\bprotecci[oó]n\b|\bproteger\b",
        "tapiado": r"\btapiad[ao]s?\b|\btapiar\b",
        "cegado": r"\bcegad[ao]s?\b|\bcegar\b",
        "apertura": r"\bapertur\w*\b|\babrir\b",
        "escombro": r"\bescombro(?:s)?\b",
        "vertedero": r"\bvertedero\b",
    },
    "apertures_enclosure": {
        "ventana": r"\bventana(?:s)?\b",
        "persiana": r"\bpersiana(?:s)?\b|\bcaj[oó]n\b",
        "carpintería": r"\bcarpinter[ií]a\b",
        "aluminio": r"\baluminio\b",
        "madera": r"\bmadera\b",
        "vidrio": r"\bvidrio(?:s)?\b|\bacristalamiento\b|\bacristalar\b",
        "sellado": r"\bsellad[ao]s?\b|\bsellar\b",
        "premarco": r"\bpremarco\b|\bprecerco\b",
        "rpt": r"\brpt\b",
        "puerta": r"\bpuerta(?:s)?\b",
        "balconera": r"\bbalconera(?:s)?\b",
    },
    "systems_services": {
        "cuadro": r"\bcuadro\b",
        "circuito": r"\bcircuito(?:s)?\b",
        "enchufe": r"\benchufe(?:s)?\b|\btoma(?:s)? de corriente\b",
        "interruptor": r"\binterruptor(?:es)?\b|\bmecanismo(?:s)?\b",
        "punto de luz": r"\bpunto(?:s)? de luz\b|\bluminaria(?:s)?\b",
        "toma de agua": r"\btoma(?:s)? de agua\b",
        "desagüe": r"\bdesag(?:u|ü)e\b|\bdesaguar\b",
        "radiador": r"\bradiador(?:es)?\b",
        "termostato": r"\btermostato(?:s)?\b",
        "conducto": r"\bconducto(?:s)?\b",
        "rejilla": r"\brejilla(?:s)?\b",
        "difusor": r"\bdifusor(?:es)?\b",
        "caldera": r"\bcaldera\b",
        "boiler": r"\bboiler\b",
        "aerotermia": r"\baerotermia\b",
        "climatización": r"\bclimatizaci[oó]n\b",
        "aire acondicionado": r"\baire acondicionado\b",
    },
    "surface_finishes": {
        "pintura": r"\bpintura\b|\bpintar\b",
        "rodapié": r"\brodapi[eé]\b",
        "solado": r"\bsolado\b|\bsolar\b",
        "pavimento": r"\bpavimento\b|\bpavimentar\b",
        "alicatado": r"\balicatad[ao]s?\b|\balicatar\b",
        "revestimiento": r"\brevestimient(?:o|os)\b|\brevestir\b",
        "impermeabilización": r"\bimpermeabilizaci[oó]n\b|\bimpermeabilizar\b",
        "yeso": r"\byeso\b",
        "masilla": r"\bmasilla\b|\bmasillar\b",
        "junta": r"\bjunta(?:s)?\b|\brejuntad[ao]s?\b",
        "lechada": r"\blechada\b",
        "enlucido": r"\benlucid[ao]s?\b|\benlucir\b",
    },
    "fixed_joinery_equipment": {
        "mobiliario": r"\bmobiliario\b",
        "cocina": r"\bcocina\b",
        "encimera": r"\bencimera\b",
        "armario": r"\barmario(?:s)?\b",
        "frente": r"\bfrente(?:s)?\b",
        "estantería": r"\bestanter[ií]a(?:s)?\b",
        "baldas": r"\bbalda(?:s)?\b",
        "mueble": r"\bmueble(?:s)?\b",
        "lavabo": r"\blavabo(?:s)?\b",
        "cajonera": r"\bcajonera(?:s)?\b",
        "zócalo": r"\bz[óo]calo(?:s)?\b",
    },
    "details_fittings": {
        "grifería": r"\bgrifer[ií]a\b",
        "mampara": r"\bmampara(?:s)?\b",
        "inodoro": r"\binodoro(?:s)?\b",
        "lavabo": r"\blavabo(?:s)?\b",
        "sanitario": r"\bsanitario(?:s)?\b",
        "espejo": r"\bespejo(?:s)?\b",
        "accesorio": r"\baccesorio(?:s)?\b",
        "herrajes": r"\bherraje(?:s)?\b",
        "cerradura": r"\bcerradura(?:s)?\b",
        "portero": r"\bportero\b",
        "intercom": r"\bintercom\b",
        "plato de ducha": r"\bplato de ducha\b",
    },
}

FEATURE_RE = re.compile(r"\bFEATURE\(([^)]+)\)")
OPENING_RE = re.compile(r"\bOPENING\(([^)]+)\)")

# High-specificity “design/spec detail” terms that are commonly present in narratives but are
# not reliably preserved in BCCA-oriented worklists (or may harm BCCA matching if they leak in).
DETAIL_TERM_PATTERNS: Dict[str, str] = {
    "roble": r"\broble\b",
    "teca": r"\bteca\b",
    "mármol": r"\bm[áa]rmol\b",
    "sinterizada": r"\bsinterizad\w*\b",
    "fenólico": r"\bfen[oó]lic\w*\b",
    "laca / lacado": r"\blaca\b|\blacad\w*\b",
    "mate": r"\bmate\b",
    "madera maciza": r"\bmaciz\w*\b",
    "gran formato": r"\bgran formato\b",
    "iluminación integrada": r"\biluminaci[oó]n\b.*\bintegrad\w*\b|\bintegrad\w*\b.*\biluminaci[oó]n\b",
    "tiradores integrados": r"\btirador\w*\b.*\bintegrad\w*\b|\bintegrad\w*\b.*\btirador\w*\b",
    "soportes invisibles": r"\binvisibl\w*\b",
    "empotrado": r"\bempotrad\w*\b",
    "suspendido": r"\bsuspendid\w*\b",
    "nicho": r"\bnicho\b",
    "domótica": r"\bdom[oó]tic\w*\b",
    "suelo radiante": r"\bsuelo radiante\b",
    "parquet / tarima": r"\bparquet\b|\btarima\b",
    "aerotermia": r"\baerotermia\b",
}


def _norm(s: str) -> str:
    return re.sub(r"\\s+", " ", (s or "").lower()).strip()


def _present_tokens(text: str, tokens: List[str]) -> Set[str]:
    t = _norm(text)
    out: Set[str] = set()
    for tok in tokens:
        if tok and _norm(tok) in t:
            out.add(tok)
    return out


def _present_labels_regex(text: str, patterns: Dict[str, str]) -> Set[str]:
    t = text or ""
    out: Set[str] = set()
    for label, pat in (patterns or {}).items():
        if not label or not pat:
            continue
        if re.search(pat, t, flags=re.IGNORECASE):
            out.add(label)
    return out


def _present_detail_terms(text: str) -> Set[str]:
    t = text or ""
    out: Set[str] = set()
    for label, pat in DETAIL_TERM_PATTERNS.items():
        if re.search(pat, t, flags=re.IGNORECASE | re.DOTALL):
            out.add(label)
    return out


def _md_escape(s: str) -> str:
    return (s or "").replace("`", "\\\\`")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--strategies", nargs="*", default=["conservative", "market_standard", "top_of_market"])
    parser.add_argument("--max-room-examples", type=int, default=6)
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    strategies = [str(s).strip() for s in (args.strategies or []) if str(s).strip()]
    if not strategies:
        raise RuntimeError("No strategies provided")

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(backend_root, "reports", f"v4_audit_narrative_to_worklist_listing_{listing_id}.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    db = Database()
    now = datetime.now(timezone.utc).isoformat()

    md: List[str] = []
    md.append("## V4 Audit — Narrative → Worklist Coverage\\n\\n")
    md.append(f"- Listing ID: **{listing_id}**\\n")
    md.append(f"- Exported at (UTC): **{now}**\\n")
    md.append(f"- Strategies: **{', '.join(strategies)}**\\n\\n")

    for strat in strategies:
        spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strat}") or {}
        dims = spec.get("dimensions") if isinstance(spec, dict) else {}
        dims = dims if isinstance(dims, dict) else {}

        md.append(f"### Strategy: `{_md_escape(strat)}`\\n\\n")

        for dim in V2_DIMENSIONS:
            patterns = TOKEN_PATTERNS_BY_DIM.get(dim, {})
            dim_spec = dims.get(dim) if isinstance(dim_spec := dims.get(dim), dict) else None
            room_blocks = (dim_spec.get("room_blocks") or []) if isinstance(dim_spec, dict) else []

            narrative_by_room: Dict[str, str] = {}
            tag_counts = {"FEATURE": 0, "OPENING": 0}
            for rb in room_blocks:
                if not isinstance(rb, dict):
                    continue
                rid = str(rb.get("room_id") or "").strip()
                ss = rb.get("specification_strategy") if isinstance(rb.get("specification_strategy"), dict) else {}
                trans = str((ss or {}).get("transformation") or "")
                hyg = str((ss or {}).get("hygiene_baseline") or "")
                text = (trans + "\\n" + hyg).strip()
                if rid and text:
                    narrative_by_room[rid] = text
                    tag_counts["FEATURE"] += len(FEATURE_RE.findall(text))
                    tag_counts["OPENING"] += len(OPENING_RE.findall(text))

            wl = await db.get_unified_estimate(listing_id, f"v4_worklist_{strat}_{dim}") or {}
            wl_blocks = (wl.get("room_blocks") or []) if isinstance(wl, dict) else []
            work_descs_by_room: Dict[str, List[str]] = defaultdict(list)
            for rb in wl_blocks:
                if not isinstance(rb, dict):
                    continue
                rid = str(rb.get("room_id") or "").strip()
                for pkg in (rb.get("scope_packages") or []):
                    if not isinstance(pkg, dict):
                        continue
                    wd = str(pkg.get("work_description") or "").strip()
                    if rid and wd:
                        work_descs_by_room[rid].append(wd)

            missing_rooms: List[Tuple[str, List[str], List[str]]] = []
            for rid, text in narrative_by_room.items():
                narr_present = _present_labels_regex(text, patterns)
                wl_text = " | ".join(work_descs_by_room.get(rid) or [])
                wl_present = _present_labels_regex(wl_text, patterns)
                missing = sorted(list(narr_present - wl_present))
                if missing:
                    missing_rooms.append((rid, missing, work_descs_by_room.get(rid, [])[: int(args.max_room_examples)]))

            # Strategy-detail preservation / hallucination check (dimension-wide)
            narrative_all = "\\n\\n".join(narrative_by_room.values())
            worklist_all = "\\n".join(["\\n".join(v) for v in work_descs_by_room.values()])
            narr_detail = _present_detail_terms(narrative_all)
            wl_detail = _present_detail_terms(worklist_all)
            detail_lost = sorted(list(narr_detail - wl_detail))
            detail_hallucinated = sorted(list(wl_detail - narr_detail))

            md.append(f"#### Dimension: `{_md_escape(dim)}`\\n\\n")
            md.append(f"- Rooms with narrative: **{len(narrative_by_room)}**\\n")
            md.append(f"- Rooms with missing token coverage: **{len(missing_rooms)}**\\n")
            md.append(f"- Narrative tag counts: FEATURE **{tag_counts['FEATURE']}**, OPENING **{tag_counts['OPENING']}**\\n\\n")
            md.append(f"- Detail terms mentioned in narrative: **{len(narr_detail)}**\\n")
            md.append(f"- Detail terms preserved into worklist: **{len(narr_detail & wl_detail)}**\\n")
            md.append(f"- Detail terms LOST (narrative→worklist): **{len(detail_lost)}**\\n")
            md.append(f"- Detail terms ADDED (worklist not in narrative): **{len(detail_hallucinated)}**\\n")
            if detail_lost:
                md.append(f"  - Lost: {', '.join([_md_escape(x) for x in detail_lost])}\\n")
            if detail_hallucinated:
                md.append(f"  - Added: {', '.join([_md_escape(x) for x in detail_hallucinated])}\\n")
            md.append("\\n")

            if missing_rooms:
                md.append("| room_id | missing tokens (mentioned in narrative, absent in worklist) | worklist examples |\\n")
                md.append("|---|---|---|\\n")
                for rid, missing, examples in missing_rooms[:25]:
                    ex = "; ".join([_md_escape(e)[:80] for e in examples]) if examples else "_(no worklist items)_"
                    md.append(f"| `{_md_escape(rid)}` | {', '.join([_md_escape(m) for m in missing])} | {ex} |\\n")
                md.append("\\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

