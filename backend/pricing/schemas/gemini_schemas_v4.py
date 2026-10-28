from typing import Any, Dict

from .gemini_schemas_v2 import V2_DIMENSIONS


# =============================================================================
# V4 FORMULA AST (Deterministic Quantity Expressions)
# =============================================================================
#
# WHY THIS MATTERS:
# - The Quantification Planner must output a deterministic expression we can evaluate in code.
# - No raw “quantity guesses” are allowed; quantities must be derived from signals.
# - The evaluator will validate allowed ops and fail-loud on invalid trees.
#
# AST Node Shapes:
# - CONST:  {"op":"CONST","value":1.25}
# - SIGNAL: {"op":"SIGNAL","signal_id":"room_floor_area_m2"}
# - ADD/SUB/MUL/DIV: {"op":"ADD","args":[<node>,<node>,...]}
# - MIN/MAX: {"op":"MIN","args":[<node>,<node>,...]}
# - CEIL/FLOOR: {"op":"CEIL","arg":<node>}

def _build_formula_node_schema(*, depth: int) -> Dict[str, Any]:
    """
    Build a finite-depth recursive schema for Gemini.

    WHY: Gemini rejects schema nodes where an OBJECT has an empty `properties` map.
    Also, circular/self-referential python dicts cannot be JSON-serialized.

    We allow a reasonable nesting depth for expressions and stop at a leaf node.
    """
    if depth < 0:
        depth = 0

    base_props: Dict[str, Any] = {
        "op": {
            "type": "string",
            "enum": ["CONST", "CONST_UNIT", "SIGNAL", "ADD", "SUB", "MUL", "DIV", "MIN", "MAX", "CEIL", "FLOOR"],
        },
        "value": {"type": "number"},
        "unit_family": {"type": "string", "enum": ["m2", "ml", "ud", "m3"]},
        "signal_id": {"type": "string"},
    }

    if depth == 0:
        return {
            "type": "object",
            "properties": base_props,
            "required": ["op"],
        }

    child = _build_formula_node_schema(depth=depth - 1)
    return {
        "type": "object",
        "properties": {
            **base_props,
            "args": {"type": "array", "items": child},
            "arg": child,
        },
        "required": ["op"],
    }


# Keep schema compact enough for Gemini response_schema limits while still enabling useful formulas.
# If we need deeper expressions later, we can increase carefully and validate against API constraints.
V4_FORMULA_NODE_SCHEMA: Dict[str, Any] = _build_formula_node_schema(depth=3)


# =============================================================================
# V4 WORKLIST (Room-level scope packages; no quantity_ref)
# =============================================================================

V4_SCOPE_PACKAGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "work_item_id": {"type": "string"},
        "work_description": {"type": "string"},
        "target_element": {"type": "string"},
        "source_scope_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["work_item_id", "work_description"],
}

V4_WORKLIST_ROOM_BLOCK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "scope_packages": {"type": "array", "items": V4_SCOPE_PACKAGE_SCHEMA},
    },
    "required": ["room_id", "scope_packages"],
}

V4_WORKLIST_DIMENSION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimension": {"type": "string", "enum": V2_DIMENSIONS},
        "dimension_intro": {"type": "string"},
        "room_blocks": {"type": "array", "items": V4_WORKLIST_ROOM_BLOCK_SCHEMA},
    },
    "required": ["dimension", "dimension_intro", "room_blocks"],
}

V4_WORKLIST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "strategy_name": {"type": "string"},
        "dimensions": {
            "type": "object",
            "properties": {dim: V4_WORKLIST_DIMENSION_SCHEMA for dim in V2_DIMENSIONS},
        },
    },
    "required": ["strategy_name", "dimensions"],
}


# =============================================================================
# V4 BCCA MATCH (Audit object, not necessarily a Gemini output)
# =============================================================================

V4_BCCA_MATCH_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "work_item_id": {"type": "string"},
        "room_id": {"type": "string"},
        "dimension": {"type": "string", "enum": V2_DIMENSIONS},
        "bcca_code": {"type": "string"},
        "unit": {"type": "string", "enum": ["m2", "ml", "ud", "m3"]},
        "unit_price": {"type": "number"},
        "labor_hours_per_unit": {"type": "number"},
        "bcca_desc_100": {"type": "string"},
        "bcca_full_desc": {"type": "string"},
        "embedding_similarity": {"type": "number"},
    },
    "required": ["work_item_id", "room_id", "dimension", "bcca_code", "unit", "unit_price"],
}


# =============================================================================
# V4 QUANTIFICATION PLAN (LLM output)
# =============================================================================

V4_QUANTIFICATION_PLAN_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "work_item_id": {"type": "string"},
        "formula_ast": V4_FORMULA_NODE_SCHEMA,
    },
    # Formula-only: room_id + unit_family are derived deterministically from BCCA matches/worklist.
    "required": ["work_item_id", "formula_ast"],
}

V4_QUANTIFICATION_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "strategy_name": {"type": "string"},
        "dimension": {"type": "string", "enum": V2_DIMENSIONS},
        "plans": {"type": "array", "items": V4_QUANTIFICATION_PLAN_ITEM_SCHEMA},
    },
    "required": ["strategy_name", "dimension", "plans"],
}


# =============================================================================
# V4 SMART M2 FORAGE OUTPUT (LLM output)
# =============================================================================

V4_SIGNAL_VALUE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "signal_id": {"type": "string"},
        "unit_family": {"type": "string", "enum": ["m2", "ml", "ud", "m3"]},
        "value": {"type": "number"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "defaulted": {"type": "boolean"},
        "evidence": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["floorplan", "photo", "smart_m2", "imputed", "unknown"]},
                "refs": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["source", "refs"],
        },
        "notes": {"type": "string"},
    },
    "required": ["signal_id", "unit_family", "value", "confidence", "defaulted", "evidence"],
}

V4_SMART_M2_FORAGE_ROOM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "signals": {"type": "array", "items": V4_SIGNAL_VALUE_SCHEMA},
    },
    "required": ["room_id", "signals"],
}

V4_SMART_M2_FORAGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "listing_id": {"type": "integer"},
        "strategy_name": {"type": "string"},
        "rooms": {"type": "array", "items": V4_SMART_M2_FORAGE_ROOM_SCHEMA},
    },
    "required": ["listing_id", "strategy_name", "rooms"],
}


def get_v4_schema(schema_name: str) -> Dict[str, Any]:
    schemas = {
        "formula_node": V4_FORMULA_NODE_SCHEMA,
        "worklist": V4_WORKLIST_SCHEMA,
        "bcca_match": V4_BCCA_MATCH_SCHEMA,
        "quantification_plan": V4_QUANTIFICATION_PLAN_SCHEMA,
        "smart_m2_forage": V4_SMART_M2_FORAGE_SCHEMA,
    }
    if schema_name not in schemas:
        raise ValueError(f"Unknown V4 schema: {schema_name}. Available: {list(schemas.keys())}")
    return schemas[schema_name]

