#!/usr/bin/env python3
"""
Build BCCA whole-dwelling denylist (v1)
======================================

Goal:
- Produce a deterministic list of BCCA codes that should NOT be used in the ROOM-LEVEL pipeline.

Rationale:
- Some BCCA items are "whole dwelling" allowances/packages (e.g., "1 vivienda", "inst. eléctrica vivienda (<=100 m²)").
- If eligible during per-room matching, they get duplicated across rooms and massively overcount.

Inputs:
- pricing/construction.db (table: price_book)

Outputs:
- pricing/data/bcca_whole_dwelling_denylist_v1.json

Non-goal:
- Door/window scoping. For instance, "puerta entrada vivienda" is NOT whole-dwelling; it's an entry element.
"""

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Row:
    code: str
    unit: str
    price: float
    chapter: str
    desc_100: str


def _load_from_construction_db(path: str) -> List[Row]:
    if not os.path.exists(path):
        raise RuntimeError(f"missing construction.db | path={path}")
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT id, unit, price, chapter, desc_100 FROM price_book")
    rows: List[Row] = []
    for code, unit, price, chapter, desc_100 in cur.fetchall():
        if not code or not unit or not desc_100:
            continue
        try:
            p = float(price or 0)
        except Exception:
            p = 0.0
        rows.append(
            Row(
                code=str(code).strip(),
                unit=str(unit).strip(),
                price=p,
                chapter=str(chapter or "").strip(),
                desc_100=str(desc_100).strip(),
            )
        )
    conn.close()
    return rows


def _is_whole_dwelling(desc: str) -> Tuple[bool, str]:
    d = (desc or "").strip().lower()
    if not d:
        return False, ""

    # Strong signals (allowance / whole-home bundles)
    if " 1 vivienda" in d or " 1 viv." in d:
        return True, "contains '1 vivienda'"

    # "inst. eléctrica vivienda (<=100 m²)" style (whole-dwelling sized packages)
    if "vivienda (" in d and ("m²" in d or "m2" in d):
        return True, "contains 'vivienda (' + area sizing"

    if "inst. eléctrica vivienda" in d:
        return True, "contains 'inst. eléctrica vivienda'"

    if "instalación eléctrica vivienda" in d:
        return True, "contains 'instalación eléctrica vivienda'"

    if "vivienda hasta c.g.p" in d or "hasta c.g.p" in d and "vivienda" in d:
        return True, "contains 'vivienda hasta c.g.p'"

    # Commissioning / functional testing bundles phrased as "Vivienda."
    # Example seen: "Func. redes int. agua... Vivienda."
    if d.endswith("vivienda.") and any(k in d for k in ("func.", "funcion", "prueba", "puesta en marcha", "redes int.")):
        return True, "endswith 'Vivienda.' + commissioning/function wording"

    return False, ""


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(repo_root, "pricing", "construction.db")
    out_path = os.path.join(repo_root, "pricing", "data", "bcca_whole_dwelling_denylist_v1.json")

    rows = _load_from_construction_db(db_path)
    deny: Dict[str, Dict[str, str]] = {}

    for r in rows:
        is_whole, reason = _is_whole_dwelling(r.desc_100)
        if not is_whole:
            continue
        # Exempt obvious per-element entry door items (not a whole-dwelling allowance).
        if "puerta entrada vivienda" in r.desc_100.lower():
            continue
        deny[r.code] = {"reason": reason, "desc_100": r.desc_100[:220]}

    # Stable ordering for diffs
    payload = {
        "version": 1,
        "generated_from": "construction.db:price_book",
        "denylist_count": len(deny),
        "denylist": {k: deny[k] for k in sorted(deny.keys())},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out_path": out_path, "denylist_count": len(deny)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

