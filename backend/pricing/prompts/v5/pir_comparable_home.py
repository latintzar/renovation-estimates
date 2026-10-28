from __future__ import annotations

import json
from typing import List


def build_v5_pir_comparable_prompt(*, property_id: int, archetypes: List[str], slot_ids: List[str]) -> str:
    """
    V5 comparable PIR prompt: whole-home, archetype-based, 1 narrative sentence per slot.

We keep this intentionally compact and fuzzy (comparables are not clustered).
    """
    return f"""
You are a renovation specialist producing a Comparable Property Intelligence Report (PIR).

PROPERTY:
- property_id: {property_id}

TASK:
Create archetype summaries (e.g., typical kitchen/bathroom/bedroom/living/exterior) using ALL provided photos.
For each archetype, write EXACTLY ONE concise narrative sentence per slot describing the comparable standard (what it looks like).

RULES:
- One sentence per slot. No bullet points.
- Do not mention prices.
- Do not invent rooms/archetypes not listed.
- Return ONLY valid JSON matching the schema.

ARCHETYPES:
{json.dumps(archetypes, ensure_ascii=False, indent=2)}

SLOTS:
{json.dumps(slot_ids, ensure_ascii=False)}
""".strip()

