#!/usr/bin/env python3
"""
Build BCCA dimension artifacts (V1)
==================================

Purpose
- Precompute deterministic, auditable artifacts so runtime pipeline can:
  1) Restrict embedding matching to a dimension-scoped subset (COMPLETE via overlap)
  2) Provide a dimension-scoped vocabulary menu to the V5 decompose prompt

Important constraints
- NO re-embedding. We slice/mask using existing:
    - backend/pricing/data/bcca_embeddings_full_metadata.json
- Completeness is preserved:
    - Every BCCA code is assigned to >=1 dimension
    - If a code is unassigned by rules, it is included in ALL dimensions

Outputs (written to backend/pricing/data/bcca_by_dimension_v1/)
- bcca_codes_by_dimension_v1.json
- bcca_vocab_by_dimension_v1.json
- AUDIT_REPORT.md
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

DIMS: List[str] = [
    "shell_preparation",
    "apertures_enclosure",
    "systems_services",
    "surface_finishes",
    "fixed_joinery_equipment",
    "details_fittings",
]


def _text_blob(m: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("desc_100", "full_desc", "description"):
        v = m.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return "\n".join(parts).lower()


def _assign_dims(*, meta: Dict[str, Any]) -> Set[str]:
    """
    High-recall deterministic rules.
    Overlap is intentional. Unassigned -> ALL dims (completeness w/o runtime fallback).
    """
    chapter = str(meta.get("chapter") or "").strip()
    t = _text_blob(meta)

    dims: Set[str] = set()

    # shell_preparation: demo / removal / waste / protection (often chapter 01 + 13)
    if chapter in ("01", "13") or any(
        s in t
        for s in (
            "demolic",
            "retirada",
            "desmont",
            "levantad",
            "carga",
            "transporte",
            "vertedero",
            "contenedor",
            "protecci",
            "tapiad",
            "cegad",
            "apertura de hueco",
        )
    ):
        dims.add("shell_preparation")

    # apertures_enclosure: windows/doors/glazing/insulation (often 05/07/09)
    if chapter in ("05", "07", "09") or any(
        s in t
        for s in (
            "ventana",
            "puerta",
            "carpinter",
            "aluminio",
            "madera",
            "pvc",
            "persiana",
            "cajón",
            "acrist",
            "vidrio",
            "sellad",
            "premarco",
            "precerco",
            "junta",
            "aislam",
        )
    ):
        # Avoid obviously cabinetry/wardrobe joinery skew (but overlap can still add via joinery rules)
        if not any(s in t for s in ("mueble", "armario")):
            dims.add("apertures_enclosure")

    # systems_services: MEP installations (often 08)
    if chapter == "08" or any(
        s in t
        for s in (
            "electric",
            "cuadro",
            "circuito",
            "mecanismo",
            "interruptor",
            "enchufe",
            "toma de corriente",
            "punto de luz",
            "fontaner",
            "tuber",
            "desag",
            "válvula",
            "grifer",
            "caldera",
            "radiador",
            "termostato",
            "conducto",
            "rejilla",
            "difusor",
            "ventil",
            "climat",
        )
    ):
        dims.add("systems_services")

    # surface_finishes: finishes (tiles/paint/plaster/etc) – largely chapter 01 in this dataset
    if chapter == "01" or any(
        s in t
        for s in (
            "alicat",
            "solad",
            "paviment",
            "revest",
            "rodapi",
            "pintur",
            "enluc",
            "yeso",
            "lechad",
            "impermeab",
        )
    ):
        # Avoid sanitary fixture replacements being misread as finishes
        if not any(s in t for s in ("inodoro", "lavabo", "plato de ducha", "mampara")):
            dims.add("surface_finishes")

    # fixed_joinery_equipment: cabinetry/joinery/built-ins (often 06)
    if chapter == "06" or any(
        s in t
        for s in (
            "mobiliario",
            "mueble",
            "encimera",
            "zócalo",
            "armario",
            "frente",
            "estanter",
            "baldas",
            "puerta interior",
            "herrajes",
        )
    ):
        dims.add("fixed_joinery_equipment")

    # details_fittings: fixtures/fittings (sanitary + accessories), chapter varies
    if any(
        s in t
        for s in (
            "sanitario",
            "inodoro",
            "lavabo",
            "bidé",
            "bañera",
            "ducha",
            "plato de ducha",
            "mampara",
            "grifer",
            "espejo",
            "accesorio",
            "toallero",
            "barra asidero",
        )
    ):
        dims.add("details_fittings")

    if not dims:
        # Completeness, no runtime fallback: treat as shared and include everywhere.
        return set(DIMS)
    return dims


def _extract_vocab_candidates(vocab_yaml: Path) -> Tuple[List[str], List[str]]:
    """
    Candidate pool from precomputed n-gram vocab file.
    We'll score these candidates against each dimension's assigned BCCA text.
    """
    data = yaml.safe_load(vocab_yaml.read_text(encoding="utf-8"))

    verbs: List[str] = []
    nouns: List[str] = []

    actions = (data or {}).get("actions") or {}
    if isinstance(actions, dict):
        for v in actions.values():
            if isinstance(v, list):
                verbs.extend([str(x).strip().lower() for x in v if isinstance(x, str) and x.strip()])

    def walk(node: Any) -> None:
        nonlocal nouns
        if isinstance(node, list):
            nouns.extend([str(x).strip().lower() for x in node if isinstance(x, str) and x.strip()])
        elif isinstance(node, dict):
            for vv in node.values():
                walk(vv)

    elements = (data or {}).get("elements") or {}
    walk(elements)

    def dedupe(xs: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return dedupe(verbs), dedupe(nouns)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "backend" / "pricing" / "data"

    meta_path = data_dir / "bcca_embeddings_full_metadata.json"
    vocab_yaml = data_dir / "bcca_vocabulary.yaml"
    out_dir = data_dir / "bcca_by_dimension_v1"
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, list) or not meta:
        raise SystemExit("full metadata missing/empty")

    # Assign codes to dimensions.
    codes_by_dim: Dict[str, Set[str]] = {d: set() for d in DIMS}
    dims_by_code: Dict[str, List[str]] = {}

    # also build per-dim concatenated text for vocab scoring
    dim_text_parts: Dict[str, List[str]] = {d: [] for d in DIMS}

    for m in meta:
        if not isinstance(m, dict):
            continue
        code = str(m.get("code") or "").strip()
        if not code:
            continue
        dims = sorted(list(_assign_dims(meta=m)))
        dims_by_code[code] = dims
        blob = _text_blob(m)
        for d in dims:
            codes_by_dim[d].add(code)
            if blob:
                dim_text_parts[d].append(blob)

    # Completeness audits
    all_codes = {str(m.get("code") or "").strip() for m in meta if isinstance(m, dict) and str(m.get("code") or "").strip()}
    union_codes: Set[str] = set()
    for d in DIMS:
        union_codes |= codes_by_dim[d]
    missing = sorted(all_codes - union_codes)
    if missing:
        raise SystemExit(f"INCOMPLETE: codes not in union | count={len(missing)} sample={missing[:30]}")

    # Write codes_by_dim
    codes_by_dim_json: Dict[str, List[str]] = {d: sorted(list(codes_by_dim[d])) for d in DIMS}
    (out_dir / "bcca_codes_by_dimension_v1.json").write_text(
        json.dumps(codes_by_dim_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "bcca_code_to_dimensions_v1.json").write_text(
        json.dumps(dims_by_code, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Build vocab by dimension by scoring candidates on assigned text
    verbs, nouns = _extract_vocab_candidates(vocab_yaml)
    vocab_by_dim: Dict[str, Dict[str, List[str]]] = {}

    for d in DIMS:
        dim_text = "\n".join(dim_text_parts[d]).lower()

        def score_terms(terms: List[str], top_k: int) -> List[str]:
            scored: List[Tuple[int, str]] = []
            for term in terms:
                c = dim_text.count(term)
                if c > 0:
                    scored.append((c, term))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [t for _, t in scored[:top_k]]

        vocab_by_dim[d] = {
            "verbs": score_terms(verbs, top_k=80),
            "nouns": score_terms(nouns, top_k=260),
        }

    (out_dir / "bcca_vocab_by_dimension_v1.json").write_text(
        json.dumps(vocab_by_dim, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Audit report
    overlap_counts = defaultdict(int)
    for dims in dims_by_code.values():
        overlap_counts[len(dims)] += 1

    lines: List[str] = []
    lines.append("# BCCA dimension artifacts (V1)\n")
    lines.append(f"- Total codes (full metadata): **{len(all_codes)}**")
    lines.append(f"- Union across dimensions: **{len(union_codes)}**")
    lines.append("")
    for d in DIMS:
        lines.append(f"- {d}: **{len(codes_by_dim[d])}** codes")
    lines.append("")
    lines.append("## Overlap distribution (codes assigned to N dimensions)")
    for n in sorted(overlap_counts.keys()):
        lines.append(f"- N={n}: {overlap_counts[n]}")
    lines.append("")
    (out_dir / "AUDIT_REPORT.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    logger.info("✅ wrote bcca_by_dimension_v1 artifacts | dir=%s", out_dir)


if __name__ == "__main__":
    main()

