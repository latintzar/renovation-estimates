from __future__ import annotations

from typing import Any, Dict, List

from pricing.v5_room_types import ROOM_TYPES_V5
from pricing.v5_slots import SLOTS_V5


# =============================================================================
# V5 ROOM TAGS (persisted artifact, not necessarily Gemini output)
# =============================================================================

V5_ROOM_TAG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "room_type": {"type": "string", "enum": sorted(list(ROOM_TYPES_V5.keys()))},
        "environment": {"type": "string", "enum": ["wet", "dry", "exterior"]},
        "traits": {"type": "array", "items": {"type": "string"}},
        "combined_types": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["room_id", "room_type", "environment", "traits", "confidence", "evidence_refs"],
}

V5_ROOM_TAGS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "rooms": {"type": "array", "items": V5_ROOM_TAG_SCHEMA},
    },
    "required": ["listing_id", "rooms"],
}


# =============================================================================
# V5 PIR (one narrative per slot)
# =============================================================================

# Target PIR: one object per room cluster, with a slot->string mapping.
V5_PIR_TARGET_ROOM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "room_type": {"type": "string", "enum": sorted(list(ROOM_TYPES_V5.keys()))},
        "slot_narratives": {
            "type": "object",
            # NOTE: Gemini schema objects require concrete properties to be fully strict.
            # We provide optional properties for each slot and enforce requiredness in code based on protocol.
            "properties": {sid: {"type": "string"} for sid in SLOTS_V5},
        },
    },
    "required": ["room_id", "room_type", "slot_narratives"],
}

V5_PIR_TARGET_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "rooms": {"type": "array", "items": V5_PIR_TARGET_ROOM_SCHEMA},
    },
    "required": ["listing_id", "rooms"],
}


# Comparable PIR: whole-home summary + archetype slot narratives (typical kitchen/bath/etc).
V5_PIR_COMPARABLE_ARCHETYPE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "archetype": {"type": "string"},  # e.g., "typical_kitchen", "typical_bathroom"
        "slot_narratives": {
            "type": "object",
            "properties": {sid: {"type": "string"} for sid in SLOTS_V5},
        },
    },
    "required": ["archetype", "slot_narratives"],
}

V5_PIR_COMPARABLE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "property_id": {"type": "integer"},
        "home_summary": {"type": "string"},
        "archetypes": {"type": "array", "items": V5_PIR_COMPARABLE_ARCHETYPE_SCHEMA},
    },
    "required": ["property_id", "home_summary", "archetypes"],
}


# =============================================================================
# V5 STRATEGY TARGETS (per tier, slot narratives)
# =============================================================================

V5_STRATEGY_TIER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "strategy_name": {"type": "string", "enum": ["conservative", "market_standard", "top_of_market"]},
        "slot_targets": {
            "type": "object",
            "properties": {sid: {"type": "string"} for sid in SLOTS_V5},
        },
    },
    "required": ["strategy_name", "slot_targets"],
}

V5_STRATEGY_TARGETS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "tiers": {"type": "array", "items": V5_STRATEGY_TIER_SCHEMA},
    },
    "required": ["listing_id", "tiers"],
}

# =============================================================================
# V5 DELTA SLOTS (per room × slot narratives)
# =============================================================================

V5_DELTA_ROOM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "room_type": {"type": "string", "enum": sorted(list(ROOM_TYPES_V5.keys()))},
        "slot_work_narratives": {
            "type": "object",
            "properties": {sid: {"type": "string"} for sid in SLOTS_V5},
        },
    },
    "required": ["room_id", "room_type", "slot_work_narratives"],
}

V5_DELTA_SLOTS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "strategy_name": {"type": "string"},
        "rooms": {"type": "array", "items": V5_DELTA_ROOM_SCHEMA},
    },
    "required": ["listing_id", "strategy_name", "rooms"],
}


# =============================================================================
# V5 DELTA CROSS-ROOM REVIEW (tracked changes / patch instructions)
# =============================================================================

V5_DELTA_CROSS_ROOM_REVIEW_PATCH_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "slot_id": {"type": "string"},
        "expected_old_text": {"type": "string"},
        "new_text": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["slot_id", "expected_old_text", "new_text", "reason"],
}

V5_DELTA_CROSS_ROOM_REVIEW_ROOM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "slot_changes": {"type": "array", "items": V5_DELTA_CROSS_ROOM_REVIEW_PATCH_SCHEMA},
    },
    "required": ["room_id", "slot_changes"],
}

V5_DELTA_CROSS_ROOM_REVIEW_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "patches": {"type": "array", "items": V5_DELTA_CROSS_ROOM_REVIEW_ROOM_SCHEMA},
    },
    "required": ["patches"],
}


# =============================================================================
# V5 DECOMPOSED WORK ITEMS (slot one-liners -> BCCA-matchable items)
# =============================================================================

V5_WORK_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "work_item_id": {"type": "string"},
        "room_id": {"type": "string"},
        "slot_id": {"type": "string"},
        "dimension": {"type": "string"},  # dimension derived later; keep flexible here
        "work_description": {"type": "string"},
        "source_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["work_item_id", "room_id", "slot_id", "work_description"],
}

V5_WORK_ITEMS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "strategy_name": {"type": "string"},
        "items": {"type": "array", "items": V5_WORK_ITEM_SCHEMA},
    },
    "required": ["listing_id", "strategy_name", "items"],
}


def get_v5_schema(schema_name: str) -> Dict[str, Any]:
    schemas = {
        "room_tags": V5_ROOM_TAGS_SCHEMA,
        "pir_target": V5_PIR_TARGET_SCHEMA,
        "pir_comparable": V5_PIR_COMPARABLE_SCHEMA,
        "strategy_targets": V5_STRATEGY_TARGETS_SCHEMA,
        "delta_slots": V5_DELTA_SLOTS_SCHEMA,
        "work_items": V5_WORK_ITEMS_SCHEMA,
    }
    if schema_name not in schemas:
        raise ValueError(f"Unknown V5 schema: {schema_name}. Available: {list(schemas.keys())}")
    return schemas[schema_name]

