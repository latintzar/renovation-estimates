"""
V5 Comparable Selector
=====================

Pick ONE comparable to serve as the market_standard reference.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from pipeline.gemini_client import call_gemini
from pricing.prompts.v5.comparable_selector import build_v5_comparable_selector_prompt


V5_COMPARABLE_SELECTOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "selected_comparable_id": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["listing_id", "selected_comparable_id", "reason"],
}

def select_v5_median_price_comparable(
    *,
    listing_id: int,
    comparables: List[Dict[str, Any]],
    price_field: str = "sale_price",
) -> Dict[str, Any]:
    """
    Deterministically pick a single comparable using the median of a price field.

    WHY THIS EXISTS:
    - This is a simpler, no-LLM alternative to the V5 comparable selector.
    - It reduces cost/time by generating PIR for only ONE comparable.

    Selection rules:
    - Prefer comparables with a numeric `price_field` (default: sale_price).
    - Sort ascending by (price, distance_km, casafari_property_id) and pick the median element.
    - If none have the requested field, fallback to price_per_sqm; if still none, pick closest-by-distance.
    """
    comps = [c for c in (comparables or []) if isinstance(c, dict)]

    def _comp_id(c: Dict[str, Any]) -> int:
        raw = c.get("casafari_property_id") or c.get("id") or c.get("comparable_id") or c.get("listing_id")
        try:
            return int(raw)
        except Exception:
            return 0

    def _as_float(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return float("nan")

    def _dist(c: Dict[str, Any]) -> float:
        d = _as_float(c.get("distance_km"))
        return d if d == d else 1e9  # NaN-safe

    def _choose_by_field(field: str) -> Optional[Dict[str, Any]]:
        rows = []
        for c in comps:
            val = _as_float(c.get(field))
            if val != val:  # NaN
                continue
            cid = _comp_id(c)
            if cid <= 0:
                continue
            rows.append((val, _dist(c), cid, c))
        if not rows:
            return None
        rows.sort(key=lambda t: (t[0], t[1], t[2]))
        median_idx = len(rows) // 2
        return {
            "field": field,
            "median_value": rows[median_idx][0],
            "selected": rows[median_idx][3],
            "count": len(rows),
        }

    chosen = _choose_by_field(str(price_field or "").strip() or "sale_price")
    if not chosen:
        chosen = _choose_by_field("price_per_sqm")

    if chosen:
        selected = chosen["selected"]
        cid = _comp_id(selected)
        return {
            "listing_id": int(listing_id),
            "selected_comparable_id": int(cid),
            "reason": (
                f"Selected median comparable by {chosen['field']} (n={chosen['count']}, median={chosen['median_value']}). "
                f"Tie-breakers: distance_km then casafari_property_id."
            ),
            "selection_method": "median_price",
            "price_field": str(chosen["field"]),
            "median_value": float(chosen["median_value"]),
        }

    # Fallback: pick closest-by-distance among valid IDs
    dist_rows = []
    for c in comps:
        cid = _comp_id(c)
        if cid <= 0:
            continue
        dist_rows.append((_dist(c), cid, c))
    if not dist_rows:
        raise RuntimeError(f"v5 median comparable: no valid comparable IDs | listing_id={listing_id}")
    dist_rows.sort(key=lambda t: (t[0], t[1]))
    cid = dist_rows[0][1]
    return {
        "listing_id": int(listing_id),
        "selected_comparable_id": int(cid),
        "reason": "Selected closest-by-distance comparable (median selection had no usable prices).",
        "selection_method": "closest_distance_fallback",
        "price_field": None,
        "median_value": None,
    }


async def select_v5_market_standard_comparable(
    *,
    listing_id: int,
    target_pir: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    comparable_pirs: List[Dict[str, Any]],
    call_gemini_fn: Any = call_gemini,
) -> Dict[str, Any]:
    prompt = build_v5_comparable_selector_prompt(
        listing_id=int(listing_id),
        target_pir=target_pir,
        comparables=comparables,
        comparable_pirs=comparable_pirs,
    )
    resp = await call_gemini_fn(
        prompt=prompt,
        model="flash",
        temperature=0.2,
        response_schema=V5_COMPARABLE_SELECTOR_SCHEMA,
        use_spanish=False,
    )
    if not resp.success:
        raise RuntimeError(f"v5 comparable selector: gemini failed | listing_id={listing_id} err={resp.error}")
    return json.loads(resp.text)

