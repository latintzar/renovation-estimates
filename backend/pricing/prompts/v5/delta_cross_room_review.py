from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _compact(obj: Any, *, max_str: int = 320) -> Any:
    """
    Recursively compact strings in nested structures to keep prompt size bounded.
    """
    if isinstance(obj, str):
        s = obj.strip()
        if len(s) <= max_str:
            return s
        return s[:max_str].rstrip() + "…"
    if isinstance(obj, list):
        return [_compact(x, max_str=max_str) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                continue
            out[k] = _compact(v, max_str=max_str)
        return out
    return obj


def build_v5_delta_cross_room_review_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    selected_comparable_id: int,
    delta_rooms: List[Dict[str, Any]],
    target_pir: Dict[str, Any],
    selected_comparable_room_pirs: Optional[Dict[str, Any]],
    selected_comparable_slot_standard: Optional[Dict[str, Any]],
    comparable_home_pir: Optional[Dict[str, Any]],
) -> str:
    """
    Cross-room delta review prompt (tracked-changes) for ONE listing.

    WHY THIS MATTERS:
    The per-room delta stage runs one call per room for cost control. That can
    produce small cross-room inconsistencies (finish families, hardware language,
    lighting temperature) and occasional “misses” where a change should logically
    apply across multiple rooms (e.g., coherent flooring standard) based on the
    comparable's whole-home standard.

    This reviewer call:
    - sees ALL room deltas at once
    - sees the FULL target PIR and FULL comparable context available
    - returns surgical patch instructions (tracked changes) without rewriting.
    """

    # Keep the huge JSON blocks bounded. The slot narratives are already short,
    # but PIR text can run long on older/complex listings.
    delta_rooms_c = _compact(delta_rooms, max_str=240)
    target_pir_c = _compact(target_pir, max_str=260)
    comp_rooms_c = _compact(selected_comparable_room_pirs or {}, max_str=260)
    comp_std_c = _compact(selected_comparable_slot_standard or {}, max_str=260)
    comp_home_c = _compact(comparable_home_pir or {}, max_str=380)

    return f"""
You are reviewing a renovation “delta” artifact for ONE home. The delta is a per-room, per-slot set of one-line work narratives describing the MINIMUM work needed to bring the target property up to the selected comparable standard.

WHY THIS MATTERS:
- Downstream stages (work-item decomposition, BOQ pricing, ELI5, and images) treat these deltas as truth.
- If the delta is inconsistent across rooms (e.g., different flooring families, inconsistent metal finishes) the final renovation feels like a collage.
- The upstream delta generator ran ONE call per room for cost control, so it may miss cross-room coherence.

Your job:
- Find cross-room consistency issues and “gap fills” that are strongly supported by the context.
- Return TRACKED CHANGES only: patch instructions that replace specific slot narratives in specific rooms.
- Be surgical. Change as little as possible. Do NOT rewrite whole rooms.

Hard constraints:
- Do NOT invent materials/finishes that are not supported by the comparable context.
- If evidence is weak or ambiguous, do not change it.
- Keep each replacement as a single short sentence in Spanish, or exactly "no change".
- Prefer using the comparable whole-home standard for finish “families” where appropriate.
- Never change room_id or slot_id structure.

Output JSON ONLY with this shape:
{{
  "patches": [
    {{
      "room_id": "string",
      "slot_changes": [
        {{
          "slot_id": "string",
          "expected_old_text": "string",
          "new_text": "string",
          "reason": "string"
        }}
      ]
    }}
  ]
}}

Rules for patches:
- expected_old_text MUST match exactly the current delta text you saw (copy/paste).
- Only include a slot_change when you are actually changing that slot.
- slot_id must be one of the provided slot keys.
- If you need a “global” consistency fix, apply it via multiple precise slot_changes across affected rooms.

What to look for (examples of valid interventions):
- Flooring family coherence: if the comparable standard implies one flooring family across main dry rooms, align deltas that accidentally diverged.
- Wall finish family coherence (paint vs microcement vs tiling families) where the comparable standard is consistent.
- Hardware / metal finish language consistency (e.g. all brushed nickel vs matte black) when the comparable is consistent.
- Lighting temperature / style coherence, if deltas drift.
- Windows/doors frame finish language coherence ONLY when the delta already implies replacement (do not add replacement out of nowhere).
- Consider what materials make sense in different rooms, from the materials that are mentioned in the deltas already — for example, unlikely that hardwood would make sense in a bathroom unless specifically stated.
- VALUE-FOR-MONEY challenge: for any slot that replaces a functional finish with a similar-category alternative (e.g. tile→tile, paint→paint), ask: does this fix something genuinely in bad condition, improve energy efficiency, or obviously raise resale value? If none of those apply, patch it to "no change". A smart renovation does not spend money replacing a perfectly fine finish just because the comparable happens to have something different.

listing_id: {int(listing_id)}
strategy_name: {strategy_name}
selected_comparable_id: {int(selected_comparable_id)}

CONTEXT — FULL TARGET PIR (rooms + slot narratives):
{json.dumps(target_pir_c, ensure_ascii=False)}

CONTEXT — SELECTED COMPARABLE (room PIRs payload; if present):
{json.dumps(comp_rooms_c, ensure_ascii=False)}

CONTEXT — SELECTED COMPARABLE (whole-home slot standard mapping; if present):
{json.dumps(comp_std_c, ensure_ascii=False)}

CONTEXT — SELECTED COMPARABLE (optional comparable_v5 home PIR; if present):
{json.dumps(comp_home_c, ensure_ascii=False)}

CURRENT DELTA (what you are patching):
{json.dumps(delta_rooms_c, ensure_ascii=False)}
""".strip()

