from __future__ import annotations

import json
from typing import Any, Dict, List


def build_v5_comparable_selector_prompt(
    *,
    listing_id: int,
    target_pir: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    comparable_pirs: List[Dict[str, Any]],
) -> str:
    """
    Select ONE comparable to represent the market_standard reference.

    Output is enforced by response_schema at the call site; the prompt should explain WHY.
    """
    return f"""
You are selecting a single comparable property to serve as the market_standard reference for a renovation estimate.

WHY THIS MATTERS:
- Every downstream step (market targets → delta → work items → BOQ) depends on this choice.
- A bad reference creates wrong scope and choppy BOQs. We want the comparable that best represents the standard we should renovate towards.

TARGET LISTING:
- listing_id: {listing_id}

CONTEXT PROVIDED:
1) TARGET PIR (slot-first, per-room). Use it to understand the current state.
2) Comparable candidates + their Comparable PIRs (slot-first, whole-home archetypes). Use them to judge the standard we should aim for.

SELECTION GUIDANCE:
- Prefer the comparable most similar in property type and overall finish level to what a buyer expects as market standard.
- Avoid outliers (luxury/high-spec or very dated/low-spec) unless all candidates are outliers.
- If multiple are close, prefer the one with clearer, higher-quality PIR evidence (less ambiguity).
- Do not optimize for price alone.

Return ONLY valid JSON.

TARGET_PIR (truncated):
{json.dumps(target_pir, ensure_ascii=False)[:10000]}

COMPARABLES (raw listing fields, truncated):
{json.dumps(comparables, ensure_ascii=False)[:8000]}

COMPARABLE_PIRS (truncated):
{json.dumps(comparable_pirs, ensure_ascii=False)[:16000]}
""".strip()

