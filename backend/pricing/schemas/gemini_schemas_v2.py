"""V2.0 Schemas - Comparable-Centric Strategy Selection Pipeline

V2 ARCHITECTURE:
================
1. PIR Generation (6 dimensions) - for ALL comparables + target
2. Strategy Selection - identify 3 strategies from comparable outcomes
3. Delta Scope Generation - 3 parallel × 6 sequential dimension gaps
4. BOQ Generation - pricing with BCCA codes

This file contains schemas for the NEW V2 calls (Strategy Selection + Delta Scope).
The PIR schema is in gemini_schemas_v1.py (enhanced with 6 dimensions).
"""

from typing import Dict, Any

# =============================================================================
# V2 STRATEGY SELECTION SCHEMA (New Call #1)
# =============================================================================

STRATEGY_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "market_analysis_summary": {
            "type": "string",
            "description": "Overview of what the comparable data reveals about this local market"
        },
        "finish_quality_price_correlation": {
            "type": "string",
            "description": "Analysis of how finish quality correlates with sold prices in this set"
        },
        "strategies": {
            "type": "array",
            "description": "Exactly 3 strategies: conservative, market_standard, top_of_market",
            "items": {
                "type": "object",
                "properties": {
                    "strategy_name": {
                        "type": "string",
                        "enum": ["conservative", "market_standard", "top_of_market"],
                        "description": "Strategy identifier"
                    },
                    "reference_comparable_id": {
                        "type": "integer",
                        "description": "ID of the comparable that best represents this strategy"
                    },
                    "reference_sold_price": {
                        "type": "number",
                        "description": "What the reference comparable sold for"
                    },
                    "strategy_rationale": {
                        "type": "string",
                        "description": "WHY this comparable represents this strategy approach"
                    },
                    "key_dimension_observations": {
                        "type": "object",
                        "description": "What the reference comparable shows for each dimension",
                        "properties": {
                            "shell_preparation": {"type": "string"},
                            "apertures_enclosure": {"type": "string"},
                            "systems_services": {"type": "string"},
                            "surface_finishes": {"type": "string"},
                            "fixed_joinery_equipment": {"type": "string"},
                            "details_fittings": {"type": "string"}
                        },
                        "required": [
                            "shell_preparation", "apertures_enclosure", "systems_services",
                            "surface_finishes", "fixed_joinery_equipment", "details_fittings"
                        ]
                    },
                    "transformation_philosophy": {
                        "type": "string",
                        "description": "How to think about transforming the target to match this strategy"
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Investment risk level"
                    },
                    "estimated_intervention_level": {
                        "type": "string",
                        "enum": ["minimal", "moderate", "substantial", "extensive"],
                        "description": "Overall scope of work expected"
                    }
                },
                "required": [
                    "strategy_name", "reference_comparable_id", "reference_sold_price",
                    "strategy_rationale", "key_dimension_observations", "transformation_philosophy",
                    "risk_level", "estimated_intervention_level"
                ]
            }
            # Note: minItems/maxItems not supported by Gemini SDK
        }
    },
    "required": ["market_analysis_summary", "strategies"]
}


# =============================================================================
# V2 DELTA SCOPE SCHEMA (New Call #2)
# =============================================================================

DELTA_SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "room_id": {
            "type": "string",
            "description": "Canonical room identifier"
        },
        "dimension": {
            "type": "string",
            "enum": [
                "shell_preparation", "apertures_enclosure", "systems_services",
                "surface_finishes", "fixed_joinery_equipment", "details_fittings"
            ],
            "description": "Which of the 6 dimensions this delta covers"
        },
        "comparison_summary": {
            "type": "string",
            "description": "Brief summary of Target vs Reference state for this dimension"
        },
        "elements": {
            "type": "array",
            "description": "Each element within this dimension and its gap analysis",
            "items": {
                "type": "object",
                "properties": {
                    "element_name": {
                        "type": "string",
                        "description": "e.g., 'wall_substrate', 'flooring', 'cabinetry'"
                    },
                    "target_current_state": {
                        "type": "string",
                        "description": "What the target property currently has"
                    },
                    "reference_target_state": {
                        "type": "string",
                        "description": "What the reference comparable has (our goal)"
                    },
                    "gap_exists": {
                        "type": "boolean",
                        "description": "True if intervention needed to match reference"
                    },
                    "intervention_required": {
                        "type": "string",
                        "description": "Description of work needed (or 'none' if no gap)"
                    },
                    "scope_items": {
                        "type": "array",
                        "description": "Specific work items for BOQ",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["remove", "prepare", "install", "repair", "upgrade", "none"],
                                    "description": "Type of work"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What specifically needs to be done"
                                },
                                "estimated_quantity": {
                                    "type": "string",
                                    "description": "Quantity with unit (e.g., '15m²', '3 units', '12ml')"
                                },
                                "material_spec": {
                                    "type": "string",
                                    "description": "Material specification to match reference quality"
                                }
                            },
                            "required": ["action", "description"]
                        }
                    }
                },
                "required": ["element_name", "gap_exists"]
            }
        },
        "dimension_total_scope_items": {
            "type": "integer",
            "description": "Total number of scope items generated for this dimension"
        }
    },
    "required": ["room_id", "dimension", "elements"]
}


# =============================================================================
# V2 CONSOLIDATED STRATEGY PACKAGE SCHEMA
# =============================================================================

STRATEGY_PACKAGE_SCHEMA = {
    "type": "object",
    "description": "Consolidated strategy package with delta scopes (Note: delta_scopes is pre-computed, this schema is for documentation only)",
    "properties": {
        "strategy_name": {"type": "string"},
        "reference_comparable_id": {"type": "integer"},
        "reference_sold_price": {"type": "number"},
        "strategy_rationale": {"type": "string"},
        "transformation_philosophy": {"type": "string"},
        "risk_level": {"type": "string"}
    },
    "required": ["strategy_name", "reference_comparable_id"]
}


# =============================================================================
# V2 BOQ PHASE SCHEMA (Updated for Delta Scope input)
# =============================================================================

V2_BOQ_LINE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "item_id": {
            "type": "string",
            "description": "Unique identifier e.g., 'R1_SHELL_001'"
        },
        "room_id": {
            "type": "string",
            "description": "Canonical room identifier"
        },
        "dimension": {
            "type": "string",
            "enum": [
                "shell_preparation", "apertures_enclosure", "systems_services",
                "surface_finishes", "fixed_joinery_equipment", "details_fittings"
            ]
        },
        "bcca_code": {
            "type": "string",
            "description": "BCCA index code for pricing"
        },
        "description": {
            "type": "string",
            "description": "Work description in Spanish"
        },
        "quantity": {
            "type": "number",
            "description": "Numerical quantity"
        },
        "unit": {
            "type": "string",
            "description": "Unit of measure (m², ml, ud, kg, etc.)"
        },
        "unit_price": {
            "type": "number",
            "description": "Price per unit from BCCA"
        },
        "line_total": {
            "type": "number",
            "description": "quantity × unit_price"
        },
        "labor_hours": {
            "type": "number",
            "description": "Estimated labor hours"
        },
        "reasoning": {
            "type": "string",
            "description": "Why this item is needed (reference to delta scope)"
        }
    },
    "required": ["item_id", "room_id", "dimension", "description", "quantity", "unit"]
}

V2_BOQ_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "strategy_name": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": V2_BOQ_LINE_ITEM_SCHEMA
        },
        "room_totals": {
            "type": "array",
            "description": "Totals per room",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "total": {"type": "number"}
                },
                "required": ["room_id", "total"]
            }
        },
        "dimension_totals": {
            "type": "array",
            "description": "Totals per dimension",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string"},
                    "total": {"type": "number"}
                },
                "required": ["dimension", "total"]
            }
        },
        "grand_total_before_iva": {"type": "number"},
        "iva_amount": {"type": "number"},
        "grand_total_with_iva": {"type": "number"},
        "total_labor_hours": {"type": "number"},
        "estimated_duration_weeks": {"type": "number"}
    },
    "required": ["strategy_name", "line_items", "grand_total_with_iva"]
}


# =============================================================================
# DIMENSION DEFINITIONS (for reference)
# =============================================================================

V2_DIMENSIONS = [
    "shell_preparation",      # Dim 1: Masonry/Plaster
    "apertures_enclosure",    # Dim 2: Joinery/Glazing
    "systems_services",       # Dim 3: MEP
    "surface_finishes",       # Dim 4: Decor
    "fixed_joinery_equipment", # Dim 5: Fittings
    "details_fittings"        # Dim 6: Hardware
]


# =============================================================================
# SCHEMA LOOKUP
# =============================================================================

V2_SCHEMAS = {
    "strategy_selection": STRATEGY_SELECTION_SCHEMA,
    "delta_scope": DELTA_SCOPE_SCHEMA,
    "strategy_package": STRATEGY_PACKAGE_SCHEMA,
    "boq_output": V2_BOQ_OUTPUT_SCHEMA,
    "boq_line_item": V2_BOQ_LINE_ITEM_SCHEMA,
}


def get_v2_schema(schema_name: str) -> Dict[str, Any]:
    """Get a V2 schema by name."""
    if schema_name not in V2_SCHEMAS:
        raise ValueError(f"Unknown V2 schema: {schema_name}. Available: {list(V2_SCHEMAS.keys())}")
    return V2_SCHEMAS[schema_name]
