"""
V5 Strategy Targets, Delta Slots, and Work-item Decomposition.

This module focuses on orchestration logic and contract enforcement.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Dict, List

from pipeline.gemini_client import call_gemini
from pricing.prompts.v5.delta_cross_room_review import build_v5_delta_cross_room_review_prompt
from pricing.prompts.v5.delta_slots import build_v5_delta_slots_prompt
from pricing.prompts.v5.decompose_work_items import (
    build_v5_decompose_work_items_prompt,
    build_v5_decompose_work_items_room_prompt,
)
from pricing.prompts.v5.strategy_targets import build_v5_strategy_targets_prompt
from pricing.schemas.gemini_schemas_v5 import V5_STRATEGY_TARGETS_SCHEMA
from pricing.schemas.gemini_schemas_v5 import V5_DELTA_CROSS_ROOM_REVIEW_SCHEMA
from pricing.v5_slots import SLOTS_V5, slot_ids_for_room_type


def _clean_json_text(text: str) -> str:
    """
    Clean typical LLM JSON wrappers (markdown fences, whitespace).
    """
    t = (text or "").strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def _safe_json_loads(text: str, *, context: str) -> Dict[str, Any]:
    """
    Parse JSON from model output with a small set of safe repairs.

    WHY THIS MATTERS:
    - Even with response_schema, the model can occasionally return invalid JSON.
    - These should fail loud with context, but after a best-effort repair.
    """
    cleaned = _clean_json_text(text)
    try:
        out = json.loads(cleaned)
        if isinstance(out, dict):
            return out
        raise JSONDecodeError("top-level JSON was not an object", cleaned, 0)
    except JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            out2 = json.loads(candidate)
            if isinstance(out2, dict):
                return out2
        raise RuntimeError(f"{context}: invalid JSON from model | head={cleaned[:220]!r}")


async def generate_v5_strategy_targets(
    *,
    listing_id: int,
    comparable_pirs: List[Dict[str, Any]],
    target_pir: Dict[str, Any],
    call_gemini_fn: Any = call_gemini,
) -> Dict[str, Any]:
    prompt = build_v5_strategy_targets_prompt(
        listing_id=listing_id,
        comparable_pirs=comparable_pirs,
        target_pir=target_pir,
        slot_ids=SLOTS_V5,
    )
    resp = await call_gemini_fn(
        prompt=prompt,
        model="flash",
        temperature=0.2,
        response_schema=V5_STRATEGY_TARGETS_SCHEMA,
        use_spanish=False,
    )
    if not resp.success:
        raise RuntimeError(f"v5 strategy_targets: gemini failed | listing_id={listing_id} err={resp.error}")
    out = json.loads(resp.text)
    return out


async def generate_v5_delta_for_room(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    room_slot_narratives: Dict[str, str],
    tier_slot_targets: Dict[str, str],
) -> Dict[str, Any]:
    slot_ids = slot_ids_for_room_type(room_type)

    def _strip_fences(text: str) -> str:
        s = (text or "").strip()
        if s.startswith("```json"):
            s = s[7:]
        elif s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        return s.strip()

    def _fallback_one_liner(sid: str) -> str:
        cur = str(room_slot_narratives.get(sid, "") or "").strip().lower()
        tgt = str(tier_slot_targets.get(sid, "") or "").strip().lower()
        # If target is empty, assume no delta (should be rare; targets are required upstream).
        if not tgt:
            return "no change"
        if cur and tgt and cur == tgt:
            return "no change"
        return "Actualizar para igualar el estándar del comparable."

    def _is_valid_one_liner(val: str) -> bool:
        s = (val or "").strip()
        if not s:
            return False
        if s.lower() == "no change":
            return True
        # Guardrails: reject obvious junk / prompt leakage / runaway verbosity.
        bad_markers = ("```", "{", "}", "schema", "valid json", "output shape", "required_slot_ids", "INVALID_OUTPUT")
        sl = s.lower()
        if any(m in sl for m in bad_markers):
            return False
        # One short sentence (rough heuristic).
        if len(s) > 220:
            return False
        return True

    # ONE CALL PER ROOM (cost control + predictable call count).
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "room_type": {"type": "string"},
            "slot_work_narratives": {
                "type": "object",
                "properties": {sid: {"type": "string"} for sid in slot_ids},
                "required": list(slot_ids),
            },
        },
        "required": ["room_id", "room_type", "slot_work_narratives"],
    }
    prompt = build_v5_delta_slots_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        room_type=room_type,
        slot_ids=slot_ids,
        # Keep per-slot context compact to reduce runaway generations.
        room_slot_narratives={
            k: str((room_slot_narratives.get(k, "") or "")).strip()[:280]
            for k in slot_ids
        },
        tier_slot_targets={
            k: str((tier_slot_targets.get(k, "") or "")).strip()[:280]
            for k in slot_ids
        },
    )
    resp = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.0,
        max_tokens=65536,
        response_schema=schema,
        no_fallback=True,
        use_spanish=True,
    )
    if not resp.success and (resp.error or "") == "No text parts in response":
        # Defensive retry: occasionally MAX_TOKENS leads to empty text parts in the SDK.
        # We re-ask with stronger brevity constraints.
        retry_prompt = (
            "CRITICAL:\n"
            "- Return ONLY valid JSON matching the schema.\n"
            "- For every slot: output exactly \"no change\" OR one <=140-char sentence.\n"
            "- If unsure, choose exactly: \"no change\".\n\n"
            + prompt
        )
        resp = await call_gemini(
            prompt=retry_prompt,
            model="pro",
            temperature=0.0,
            # Smaller cap discourages runaway outputs; expected output is tiny anyway.
            max_tokens=12000,
            response_schema=schema,
            no_fallback=True,
            use_spanish=True,
        )

    if not resp.success:
        raise RuntimeError(f"v5 delta: gemini failed | room_id={room_id} err={resp.error}")

    raw = _strip_fences(resp.text or "")
    try:
        out = json.loads(raw)
    except JSONDecodeError as e:
        raise RuntimeError(f"v5 delta: invalid JSON | room_id={room_id} err={e}") from e

    slot_work = out.get("slot_work_narratives") if isinstance(out, dict) else None
    if not isinstance(slot_work, dict):
        raise RuntimeError(f"v5 delta: invalid slot_work_narratives | room_id={room_id}")

    combined: Dict[str, str] = {}
    for sid in slot_ids:
        val = slot_work.get(sid)
        if isinstance(val, str) and _is_valid_one_liner(val):
            combined[sid] = val.strip()
        else:
            combined[sid] = _fallback_one_liner(sid)

    return {
        "room_id": str(room_id),
        "room_type": str(room_type),
        "slot_work_narratives": {sid: str(combined.get(sid, "")).strip() for sid in slot_ids},
    }


def _normalize_delta_text(s: str) -> str:
    return " ".join(str(s or "").strip().split()).lower()


def apply_v5_delta_cross_room_patches(
    *,
    delta_rooms: List[Dict[str, Any]],
    patches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Apply cross-room review patches to a delta rooms list.

    Safety rules:
    - Only apply a change if expected_old_text matches the current text (normalized).
    - Only apply to known room_id and existing slot_id keys.
    - Do not raise; return stats + updated rooms.
    """
    rooms = [r for r in (delta_rooms or []) if isinstance(r, dict)]
    by_room: Dict[str, Dict[str, Any]] = {str(r.get("room_id") or ""): r for r in rooms if str(r.get("room_id") or "")}

    applied = 0
    skipped = 0
    per_room_applied: Dict[str, int] = {}

    for rp in (patches or []):
        if not isinstance(rp, dict):
            continue
        rid = str(rp.get("room_id") or "").strip()
        if not rid:
            continue
        room = by_room.get(rid)
        if not isinstance(room, dict):
            skipped += 1
            continue

        slot_work = room.get("slot_work_narratives") or {}
        if not isinstance(slot_work, dict):
            skipped += 1
            continue

        for ch in (rp.get("slot_changes") or []):
            if not isinstance(ch, dict):
                continue
            slot_id = str(ch.get("slot_id") or "").strip()
            expected_old = str(ch.get("expected_old_text") or "").strip()
            new_text = str(ch.get("new_text") or "").strip()
            if not slot_id or not expected_old or not new_text:
                skipped += 1
                continue
            if slot_id not in slot_work:
                skipped += 1
                continue

            cur = str(slot_work.get(slot_id) or "").strip()
            if _normalize_delta_text(cur) != _normalize_delta_text(expected_old):
                skipped += 1
                continue

            # Apply.
            slot_work[slot_id] = new_text
            applied += 1
            per_room_applied[rid] = int(per_room_applied.get(rid) or 0) + 1

        room["slot_work_narratives"] = slot_work

    return {
        "rooms": rooms,
        "stats": {
            "slot_changes_applied": applied,
            "slot_changes_skipped": skipped,
            "rooms_touched": len([rid for rid, n in per_room_applied.items() if n > 0]),
            "per_room_applied": per_room_applied,
        },
    }


async def review_v5_delta_slots_cross_room(
    *,
    listing_id: int,
    strategy_name: str,
    selected_comparable_id: int,
    delta_rooms: List[Dict[str, Any]],
    target_pir: Dict[str, Any],
    selected_comparable_room_pirs: Dict[str, Any] | None = None,
    selected_comparable_slot_standard: Dict[str, Any] | None = None,
    comparable_home_pir: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Single Pro call that reviews ALL room deltas and returns tracked-change patch instructions.

    Best-effort: never raise.
    Returns:
      - success: bool
      - patches: list
      - error: optional string
    """
    try:
        prompt = build_v5_delta_cross_room_review_prompt(
            listing_id=int(listing_id),
            strategy_name=str(strategy_name),
            selected_comparable_id=int(selected_comparable_id),
            delta_rooms=delta_rooms,
            target_pir=target_pir,
            selected_comparable_room_pirs=selected_comparable_room_pirs,
            selected_comparable_slot_standard=selected_comparable_slot_standard,
            comparable_home_pir=comparable_home_pir,
        )
        resp = await call_gemini(
            prompt=prompt,
            model="pro",
            temperature=0.0,
            max_tokens=16384,
            response_schema=V5_DELTA_CROSS_ROOM_REVIEW_SCHEMA,
            # Prompt includes Spanish deltas; keep language flexible (we're outputting JSON anyway).
            use_spanish=False,
            # Never allow a fallback model here; if Pro fails, we simply skip this reviewer.
            no_fallback=True,
        )
        if not resp.success:
            return {"success": False, "patches": [], "error": str(resp.error or "unknown error")}
        out = json.loads(resp.text or "{}")
        if isinstance(out, dict) and isinstance(out.get("patches"), list):
            return {"success": True, "patches": out.get("patches") or []}
        return {"success": False, "patches": [], "error": "unexpected shape"}
    except Exception as exc:
        return {"success": False, "patches": [], "error": f"{type(exc).__name__}: {exc}"}


def _slot_id_to_dimension(slot_id: str) -> str:
    s = str(slot_id or "")
    if s.startswith("shell."):
        return "shell_preparation"
    if s.startswith("enclosure."):
        return "apertures_enclosure"
    if s.startswith("mep."):
        return "systems_services"
    if s.startswith("finishes."):
        return "surface_finishes"
    if s.startswith("joinery."):
        return "fixed_joinery_equipment"
    if s.startswith("details."):
        return "details_fittings"
    return "systems_services"


async def decompose_v5_slot_one_liner(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    slot_id: str,
    slot_one_liner: str,
) -> List[str]:
    # Back-compat helper: decompose a single slot text by wrapping it as a room×dimension request.
    dim = _slot_id_to_dimension(slot_id)
    prompt = build_v5_decompose_work_items_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        room_type=room_type,
        dimension=dim,
        slot_narratives={str(slot_id): str(slot_one_liner)},
    )
    resp = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.2,
        max_tokens=4096,
        # schema is trivial here; parse manually
        response_schema={
            "type": "object",
            "properties": {
                "by_slot": {
                    "type": "object",
                    "additionalProperties": {"type": "array", "items": {"type": "string"}},
                }
            },
            "required": ["by_slot"],
        },
        use_spanish=False,
    )
    if not resp.success:
        raise RuntimeError(f"v5 decompose: gemini failed | room_id={room_id} slot_id={slot_id} err={resp.error}")
    out = json.loads(resp.text)
    by_slot = out.get("by_slot") or {}
    arr = by_slot.get(str(slot_id)) if isinstance(by_slot, dict) else None
    descs = [d.strip() for d in (arr or []) if isinstance(d, str) and d.strip()]
    return descs


async def decompose_v5_room_dimension(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    dimension: str,
    slot_narratives: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    Decompose per ROOM × DIMENSION to keep the BCCA vocabulary menu tight.

    Returns: {slot_id: [work_description, ...]}
    """
    slot_ids = [sid for sid in (slot_narratives or {}).keys() if isinstance(sid, str) and sid.strip()]
    if not slot_ids:
        raise RuntimeError(f"v5 decompose: empty slot_narratives | room_id={room_id} dimension={dimension}")

    prompt = build_v5_decompose_work_items_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        room_type=room_type,
        dimension=str(dimension),
        slot_narratives=slot_narratives,
    )
    resp = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.2,
        max_tokens=8192,
        # NOTE: google-generativeai's response_schema proto does NOT support JSON Schema's `additionalProperties`.
        # We must enumerate keys. Here we constrain output to just the slots we provided in `slot_narratives`.
        response_schema={
            "type": "object",
            "properties": {
                "by_slot": {
                    "type": "object",
                    "properties": {sid: {"type": "array", "items": {"type": "string"}} for sid in slot_ids},
                    "required": list(slot_ids),
                }
            },
            "required": ["by_slot"],
        },
        use_spanish=False,
    )
    if not resp.success:
        raise RuntimeError(f"v5 decompose: gemini failed | room_id={room_id} dimension={dimension} err={resp.error}")
    out = json.loads(resp.text)
    by_slot = out.get("by_slot") or {}
    if not isinstance(by_slot, dict):
        raise RuntimeError(f"v5 decompose: invalid output | room_id={room_id} dimension={dimension}")
    cleaned: Dict[str, List[str]] = {}
    for sid, arr in by_slot.items():
        if not isinstance(sid, str) or not sid.strip():
            continue
        if not isinstance(arr, list):
            continue
        cleaned[sid] = [d.strip() for d in arr if isinstance(d, str) and d.strip()]
    return cleaned


async def decompose_v5_room_all_dimensions(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    slot_narratives: Dict[str, str],
    gemini_semaphore: Any = None,
) -> Dict[str, Dict[str, List[str]]]:
    """
    ONE CALL PER ROOM.

    Input: {slot_id: one-liner} for slots that require work (no "no change" slots).
    Output: {dimension: {slot_id: [work_desc, ...]}}
    """
    if not isinstance(slot_narratives, dict) or not slot_narratives:
        raise RuntimeError(f"v5 decompose(room): empty slot_narratives | room_id={room_id}")

    # Group slot narratives by dimension so we can provide the correct vocab per dimension in one prompt.
    by_dim_in: Dict[str, Dict[str, str]] = {}
    for sid, text in slot_narratives.items():
        if not isinstance(sid, str) or not sid.strip():
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        if text.strip().lower() == "no change":
            continue
        dim = _slot_id_to_dimension(sid)
        by_dim_in.setdefault(dim, {})[sid] = text.strip()

    if not by_dim_in:
        return {}

    dims = sorted(by_dim_in.keys())
    # Build schema with enumerated dimension keys and slot keys (no additionalProperties).
    dim_props: Dict[str, Any] = {}
    for dim in dims:
        slots = sorted(by_dim_in[dim].keys())
        dim_props[dim] = {
            "type": "object",
            "properties": {sid: {"type": "array", "items": {"type": "string"}} for sid in slots},
            "required": list(slots),
        }

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "by_dim": {
                "type": "object",
                "properties": dim_props,
                "required": list(dims),
            }
        },
        "required": ["by_dim"],
    }

    prompt = build_v5_decompose_work_items_room_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        room_type=room_type,
        slot_narratives_by_dim=by_dim_in,
    )

    # max_tokens=65536: rooms with many active slots produce large structured JSON.
    # 16384 was causing MAX_TOKENS truncation → invalid JSON → hard failure.
    if gemini_semaphore is not None:
        async with gemini_semaphore:
            resp = await call_gemini(
                prompt=prompt,
                model="flash",
                temperature=0.2,
                max_tokens=65536,
                response_schema=schema,
                use_spanish=False,
            )
    else:
        resp = await call_gemini(
            prompt=prompt,
            model="flash",
            temperature=0.2,
            max_tokens=65536,
            response_schema=schema,
            use_spanish=False,
        )
    if not resp.success:
        raise RuntimeError(f"v5 decompose(room): gemini failed | room_id={room_id} err={resp.error}")

    out = json.loads((resp.text or "").strip())
    by_dim = out.get("by_dim") or {}
    if not isinstance(by_dim, dict):
        raise RuntimeError(f"v5 decompose(room): invalid output | room_id={room_id}")

    cleaned: Dict[str, Dict[str, List[str]]] = {}
    for dim, by_slot in by_dim.items():
        if not isinstance(dim, str) or not isinstance(by_slot, dict):
            continue
        cleaned[dim] = {}
        for sid, arr in by_slot.items():
            if not isinstance(sid, str) or not isinstance(arr, list):
                continue
            cleaned[dim][sid] = [d.strip() for d in arr if isinstance(d, str) and d.strip()]
    return cleaned

