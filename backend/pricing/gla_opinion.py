"""
GLA Opinion Stage
=================

Generate Leo's per-room, per-slot opinion narratives.

Inputs:
- V5 PIR target slot narratives (current state)
- room photo URLs (cluster photos)
- Smart M2 room dimensions (best-effort)
- construction year (age context via rules_engine.json + rules_engine_v2.json)

Output:
{"room_id", "room_type", "slot_opinion_narratives": {slot_id: "..."}}

WHY THIS MATTERS:
This artifact is the bridge from "what is there" (PIR) to "what should we do" (agent tools).
It is intentionally opinionated, but must remain grounded in the evidence.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pipeline.gemini_client import fetch_images_batch
from pricing.prompts.gla.opinion_room import build_gla_opinion_room_prompt
from pricing.prompts.v5.age_context import build_age_context_block

logger = logging.getLogger(__name__)


def _opinion_room_schema_for_slots(*, slot_ids: List[str]) -> Dict[str, Any]:
    slot_ids_clean = [str(s).strip() for s in (slot_ids or []) if isinstance(s, str) and str(s).strip()]
    return {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "room_type": {"type": "string"},
            "slot_opinion_narratives": {
                "type": "object",
                "properties": {sid: {"type": "string"} for sid in slot_ids_clean},
                "required": slot_ids_clean,
            },
        },
        "required": ["room_id", "room_type", "slot_opinion_narratives"],
    }


def _clean_slot_map(slot_map: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (slot_map or {}).items():
        if not isinstance(v, str):
            continue
        s = v.strip()
        if not s:
            continue
        out[str(k)] = s
    return out


async def generate_gla_opinion(
    *,
    listing_id: int,
    room_id: str,
    room_type: str,
    slot_narratives: Dict[str, str],
    photo_urls: List[str],
    smart_m2: Optional[Dict[str, Any]] = None,
    construction_year: Optional[int] = None,
    call_gemini: Any,
    max_photos: int = 8,
) -> Dict[str, Any]:
    """
    Generate a per-slot, opinionated narrative for a single room.

    Model: Flash (fast, conversational, good enough for opinion text).
    """
    if not listing_id:
        raise ValueError("generate_gla_opinion: missing listing_id")
    if not room_id:
        raise ValueError("generate_gla_opinion: missing room_id")
    if not room_type:
        raise ValueError("generate_gla_opinion: missing room_type")
    if not isinstance(slot_narratives, dict) or not slot_narratives:
        raise ValueError(f"generate_gla_opinion: missing slot_narratives | room_id={room_id}")

    slot_ids = [str(k) for k in slot_narratives.keys() if isinstance(k, str) and str(k).strip()]
    if not slot_ids:
        raise ValueError(f"generate_gla_opinion: empty slot ids | room_id={room_id}")

    age_context_block = ""
    if isinstance(construction_year, int):
        age_context_block = build_age_context_block(construction_year=construction_year, room_type=room_type)

    # best-effort per-room smart_m2 slice
    smart_m2_room: Optional[Dict[str, Any]] = None
    if isinstance(smart_m2, dict):
        rooms = smart_m2.get("rooms")
        if isinstance(rooms, list):
            for r in rooms:
                if isinstance(r, dict) and str(r.get("room_id") or "").strip() == str(room_id):
                    smart_m2_room = r
                    break

    prompt = build_gla_opinion_room_prompt(
        listing_id=int(listing_id),
        room_id=str(room_id),
        room_type=str(room_type),
        slot_narratives={str(k): str(v) for k, v in (slot_narratives or {}).items() if isinstance(v, str)},
        smart_m2_room=smart_m2_room,
        age_context_block=age_context_block,
    )

    urls = [u for u in (photo_urls or []) if isinstance(u, str) and u.strip()]
    urls = urls[: max(1, int(max_photos))]
    images = await fetch_images_batch(urls)
    images = [img for img in (images or []) if isinstance(img, dict) and img.get("data")]
    if not images:
        raise RuntimeError(f"gla_opinion: no images fetched | room_id={room_id} photo_urls={len(photo_urls or [])}")

    response_schema = _opinion_room_schema_for_slots(slot_ids=slot_ids)
    logger.info(
        "stage=gla_opinion_room listing_id=%s room_id=%s room_type=%s photos=%s slots=%s",
        listing_id,
        room_id,
        room_type,
        len(images),
        len(slot_ids),
    )

    resp = await call_gemini(
        prompt=prompt,
        images=images,
        model="flash",
        temperature=0.2,
        max_tokens=65536,
        response_schema=response_schema,
        use_spanish=True,
    )
    if not resp.success:
        raise RuntimeError(f"gla_opinion: gemini failed | room_id={room_id} err={resp.error}")

    raw = (resp.text or "").strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        out = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"gla_opinion: JSON parse failed | room_id={room_id} err={exc} raw={raw[:800]}") from exc

    slot_opinion = _clean_slot_map(out.get("slot_opinion_narratives") or {})
    missing = [sid for sid in slot_ids if sid not in slot_opinion]
    if missing:
        raise RuntimeError(f"gla_opinion: missing slots | room_id={room_id} missing={missing[:8]}")

    return {
        "room_id": str(room_id),
        "room_type": str(room_type),
        "slot_opinion_narratives": slot_opinion,
    }

