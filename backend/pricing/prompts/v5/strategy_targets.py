from __future__ import annotations

import json
from typing import Any, Dict, List


def build_v5_strategy_targets_prompt(
    *,
    listing_id: int,
    comparable_pirs: List[Dict[str, Any]],
    target_pir: Dict[str, Any],
    slot_ids: List[str],
) -> str:
    """
    V5 strategy targets prompt: produce slot-level target narratives for the 3 tiers.
    """
    return f"""
You are defining three renovation strategies for a target property to reach comparable standards.

LISTING:
- listing_id: {listing_id}

OUTPUT:
Return targets for exactly three tiers:
- conservative
- market_standard
- top_of_market

Each tier must provide EXACTLY ONE narrative sentence per slot describing the target end-state for that slot.

RULES:
- One sentence per slot per tier.
- Keep the language decomposable into work items later (avoid marketing fluff).
- Do not mention prices.
- Return ONLY valid JSON matching the schema.

SLOTS:
{json.dumps(slot_ids, ensure_ascii=False)}

COMPARABLE_PIRS (summarized, truncated):
{json.dumps(comparable_pirs, ensure_ascii=False)[:12000]}

TARGET_PIR (summarized, truncated):
{json.dumps(target_pir, ensure_ascii=False)[:12000]}
""".strip()
