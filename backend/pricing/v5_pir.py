"""
V5 PIR generation (slot-first).

Target mode: per room cluster (needs clustering + room tags), strict slot protocol per room type.
Comparable mode was removed — replaced by v5_generate_selected_comparable_room_pirs in handlers.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pipeline.gemini_client import call_gemini, fetch_images_batch
from pricing.prompts.v5.age_context import build_age_context_block
from pricing.prompts.v5.pir_target_room import build_v5_pir_target_room_prompt
from pricing.schemas.gemini_schemas_v5 import V5_PIR_TARGET_ROOM_SCHEMA
from pricing.v5_slots import slot_ids_for_room_type

logger = logging.getLogger(__name__)

def _v5_target_room_schema_for_slots(*, slot_ids: List[str]) -> Dict[str, Any]:
    """
    Build a strict per-room response schema that REQUIRES every slot_id key.

    WHY THIS MATTERS:
    - The global schema only lists optional properties for all slots.
    - For V5 correctness, each room protocol must be complete (one sentence per required slot).
    - Making requiredness part of the schema reduces missing-slot failures dramatically.
    """
    slot_ids_clean = [str(s).strip() for s in (slot_ids or []) if isinstance(s, str) and str(s).strip()]
    return {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "room_type": {"type": "string"},
            "slot_narratives": {
                "type": "object",
                "properties": {sid: {"type": "string"} for sid in slot_ids_clean},
                "required": slot_ids_clean,
            },
        },
        "required": ["room_id", "room_type", "slot_narratives"],
    }


def _ensure_one_sentence_per_slot(slot_map: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (slot_map or {}).items():
        if not isinstance(v, str):
            continue
        s = v.strip()
        if not s:
            continue
        out[str(k)] = s
    return out


async def generate_v5_target_room_pir(
    *,
    room_id: str,
    room_type: str,
    photo_urls: List[str],
    construction_year: Optional[int] = None,
    max_photos: int = 12,
    call_gemini_fn: Any = call_gemini,
    fetch_images_batch_fn: Any = fetch_images_batch,
) -> Dict[str, Any]:
    slot_ids = slot_ids_for_room_type(room_type)
    age_context_block = ""
    if isinstance(construction_year, int):
        age_context_block = build_age_context_block(
            construction_year=construction_year,
            room_type=room_type,
        )
    prompt = build_v5_pir_target_room_prompt(
        room_id=room_id,
        room_type=room_type,
        slot_ids=slot_ids,
        age_context_block=age_context_block,
    )
    response_schema = _v5_target_room_schema_for_slots(slot_ids=slot_ids)
    urls = [u for u in (photo_urls or []) if isinstance(u, str) and u.strip()]
    urls = urls[: max(1, int(max_photos))]
    images = await fetch_images_batch_fn(urls)
    images = [img for img in (images or []) if isinstance(img, dict) and img.get("data")]
    if not images:
        raise RuntimeError(f"v5 target PIR: no images fetched | room_id={room_id} photo_urls={len(photo_urls or [])}")

    logger.info(
        "stage=v5_pir_target_room listing_id=? room_id=%s room_type=%s photos=%s slots=%s",
        room_id,
        room_type,
        len(images),
        len(slot_ids),
    )

    resp = await call_gemini_fn(
        prompt=prompt,
        images=images,
        model="pro",  # room PIR is vision-heavy; keep pro for now
        temperature=0.0,
        max_tokens=65536,
        response_schema=response_schema,
        no_fallback=False,
        use_spanish=True,
    )
    if not resp.success:
        raise RuntimeError(f"v5 target PIR: gemini failed | room_id={room_id} err={resp.error}")
    raw = (resp.text or "").strip()
    # Remove markdown fences if present (defensive; schema should prevent this, but the SDK can still emit fences).
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        out = json.loads(raw)
    except JSONDecodeError:
        # Single repair attempt: ask a text-only call to convert to strict JSON per schema.
        repair_prompt = f"""
You returned INVALID JSON for a V5 Target PIR room.

TASK:
- Return ONLY valid JSON matching the provided schema.
- Include ALL required slots (one sentence each). You may say "not visible" when appropriate.

room_id={room_id}
room_type={room_type}
required_slot_ids={json.dumps(slot_ids, ensure_ascii=False)}

INVALID_OUTPUT:
{raw[:12000]}
""".strip()
        repair = await call_gemini_fn(
            prompt=repair_prompt,
            model="flash",
            temperature=0.0,
            max_tokens=65536,
            response_schema=response_schema,
            no_fallback=False,
            use_spanish=True,
        )
        if not repair.success:
            raise RuntimeError(f"v5 target PIR: repair gemini failed | room_id={room_id} err={repair.error}")
        raw2 = (repair.text or "").strip()
        if raw2.startswith("```json"):
            raw2 = raw2[7:]
        elif raw2.startswith("```"):
            raw2 = raw2[3:]
        if raw2.endswith("```"):
            raw2 = raw2[:-3]
        raw2 = raw2.strip()
        out = json.loads(raw2)

    slot_narratives = _ensure_one_sentence_per_slot(out.get("slot_narratives") or {})
    # enforce all requested slots present (even if "not visible" assumptions)
    missing = [sid for sid in slot_ids if sid not in slot_narratives]
    if missing:
        raise RuntimeError(f"v5 target PIR: missing slots | room_id={room_id} missing={missing[:8]}")
    return {"room_id": room_id, "room_type": room_type, "slot_narratives": slot_narratives}


# generate_v5_comparable_pir REMOVED — replaced by v5_generate_selected_comparable_room_pirs
# which runs per-cluster room PIR on the selected comparable only (see handlers.py).
# Schema (V5_PIR_COMPARABLE_SCHEMA) and prompt (pir_comparable_home.py) still exist
# but are unused; safe to remove in a future cleanup pass.

