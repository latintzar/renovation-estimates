from typing import Dict, Any

from .gemini_schemas_v2 import V2_DIMENSIONS


V3_STRATEGY_SPEC_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimension": {"type": "string"},
        "dimension_intro": {
            "type": "string",
            "description": "Natural-language preface for this dimension: what work will be done and why, in a narrator tone.",
        },
        "room_blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "specification_strategy": {
                        "type": "object",
                        "properties": {
                            "transformation": {"type": "string"},
                            "hygiene_baseline": {"type": "string"},
                        },
                        "required": ["transformation", "hygiene_baseline"],
                    },
                },
                "required": ["room_id", "specification_strategy"],
            },
        },
    },
    "required": ["dimension", "dimension_intro", "room_blocks"],
}


V3_WORKLIST_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bcca_description": {"type": "string"},
        "unit": {"type": "string", "enum": ["m2", "ml", "ud", "m3"]},
        "rooms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "quantity_ref": {"type": "string"},
                },
                "required": ["room_id", "quantity_ref"],
            },
        },
    },
    "required": ["bcca_description", "unit", "rooms"],
}


V3_BCCA_WORKLIST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimension": {"type": "string"},
        "worklist_items": {"type": "array", "items": V3_WORKLIST_ITEM_SCHEMA},
    },
    "required": ["dimension", "worklist_items"],
}


V3_WORKLIST_REPAIR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "room_id": {"type": "string"},
                    "bcca_description": {"type": "string"},
                    "quantity_ref": {"type": "string"},
                    "unit": {"type": "string", "enum": ["m2", "ml", "ud", "m3"]},
                },
                "required": ["item_id", "room_id", "bcca_description", "quantity_ref", "unit"],
            },
        }
    },
    "required": ["repairs"],
}


def get_v3_schema(schema_name: str) -> Dict[str, Any]:
    schemas = {
        "strategy_spec": V3_STRATEGY_SPEC_SCHEMA,
        "bcca_worklist": V3_BCCA_WORKLIST_SCHEMA,
        "worklist_item": V3_WORKLIST_ITEM_SCHEMA,
        "worklist_repair": V3_WORKLIST_REPAIR_SCHEMA,
    }
    if schema_name not in schemas:
        raise ValueError(f"Unknown V3 schema: {schema_name}. Available: {list(schemas.keys())}")
    return schemas[schema_name]
