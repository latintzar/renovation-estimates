"""V1.0 Schemas - 8-Phase Ultimate Pipeline

PHASES:
1. Scope + BOQ (Pro) - scope with BCCA codes
2. Price Lookup (Code) - deterministic pricing
3. Peer Review (Pro) - improve and adjust
4. Rendering Prompts (Pro) - AI image prompts
5. Image Generation (Gemini 2.5 Flash Image)
6. Viewing Checklist (Flash)
7. ELI5 Room Summaries (Flash)
8. Architect Report (Pro)

VALIDATION:
Critical validation functions for data integrity.
These are NOT deprecated and MUST be preserved.
"""
from typing import Dict, Any, List, Set
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA INTEGRITY EXCEPTIONS (Critical - NOT deprecated)
# =============================================================================

class SchemaContinuityError(Exception):
    """
    Data Integrity Error: Items were lost between phases.
    
    What happened: The model received N items and returned fewer. Some scope
    items from earlier phases are missing in the output.
    
    Why this matters: An estimate needs all its line items. If we started with
    42 items (demolition, electrical, finishes, etc.) and Phase 5 only returns
    38, we're missing work from the estimate. The numbers won't add up.
    
    What to do: This is usually a model error (truncation, confusion). Retry
    the phase, or check if the prompt is too long.
    """
    def __init__(self, phase_num: int, expected: int, got: int, missing_ids: Set[str]):
        self.phase_num = phase_num
        self.expected = expected
        self.got = got
        self.missing_ids = missing_ids
        super().__init__(
            f"Phase {phase_num}: {expected - got} items lost (expected {expected}, got {got}). "
            f"Missing: {sorted(list(missing_ids)[:5])}{'...' if len(missing_ids) > 5 else ''}"
        )


class PricingIncompleteError(Exception):
    """
    Data Completeness Error: Items don't have prices.
    
    What happened: After the pricing phase, some items still have null/missing
    values for unit_price or line_total.
    
    Why this matters: An estimate without prices is like a menu with "price: TBD".
    The client needs to know what things cost. We can't present "???" in a quote.
    
    What to do: Check if the BCCA/FFE indexes have coverage for these items.
    The model might have used codes that don't exist in the price database.
    """
    def __init__(self, items_missing_price: List[str]):
        self.items_missing_price = items_missing_price
        count = len(items_missing_price)
        samples = items_missing_price[:5]
        super().__init__(
            f"{count} items have no price: {samples}{'...' if count > 5 else ''}"
        )


# =============================================================================
# VALIDATION FUNCTIONS (Critical - NOT deprecated)
# =============================================================================

def validate_items_preserved(
    prev_items: List[Dict[str, Any]], 
    new_items: List[Dict[str, Any]], 
    phase_num: int
) -> None:
    """
    Verify item continuity between phases - this is a DATA INTEGRITY check.
    
    Why this matters: The multi-phase pipeline passes items through each phase.
    Each phase adds information (scheduling, pricing, adjustments) but should
    NEVER lose items. If items disappear, the estimate is fundamentally broken.
    
    This is different from room coverage (a judgment call). This is about data
    corruption - the model was given 42 items and returned 38. That's a bug.
    
    BLOCKS ON FAILURE: Yes, because the estimate would be invalid.
    
    Args:
        prev_items: Items from previous phase
        new_items: Items from current phase output
        phase_num: Current phase number
    
    Raises:
        SchemaContinuityError: If items were lost (actual data corruption)
    """
    prev_ids = {item.get("item_id") for item in prev_items if item.get("item_id")}
    new_ids = {item.get("item_id") for item in new_items if item.get("item_id")}
    
    missing = prev_ids - new_ids
    added = new_ids - prev_ids
    
    # Report what we see
    logger.info(f"  📊 Item Continuity Check (Phase {phase_num}):")
    logger.info(f"     Input items: {len(prev_items)}")
    logger.info(f"     Output items: {len(new_items)}")
    
    if added:
        logger.info(f"     + New items added: {len(added)}")
    
    if missing:
        # This is a real problem - data was lost
        logger.error(f"  ❌ DATA INTEGRITY FAILURE: {len(missing)} items LOST in Phase {phase_num}")
        logger.error(f"     This is not a judgment call - these items existed and now don't.")
        logger.error(f"     Missing item IDs: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")
        logger.error(f"     The estimate cannot proceed with missing scope items.")
        raise SchemaContinuityError(
            phase_num=phase_num,
            expected=len(prev_items),
            got=len(new_items),
            missing_ids=missing
        )
    
    logger.info(f"  ✓ Item continuity verified: all {len(prev_ids)} items preserved")


def validate_pricing_complete(items: List[Dict[str, Any]]) -> None:
    """
    Verify all items have been priced - this is a DATA COMPLETENESS check.
    
    Why this matters: After Phase 2 (Pricing), every item should have:
    - unit_price: The cost per unit from BCCA/FFE indexes
    - line_total: unit_price × quantity
    
    An item without a price is like a menu item with "price: ask waiter" - 
    it's not usable. The client needs to know what things cost.
    
    BLOCKS ON FAILURE: Yes, because an estimate with "???" prices is broken.
    
    Args:
        items: Items after Phase 2 pricing
    
    Raises:
        PricingIncompleteError: If any items lack prices
    """
    # Categorize items by pricing status
    fully_priced = []
    missing_unit_price = []
    missing_line_total = []
    zero_priced = []
    
    for item in items:
        item_id = item.get("item_id", "UNKNOWN")
        item_name = item.get("name", "Unknown item")
        unit_price = item.get("unit_price")
        line_total = item.get("line_total")
        
        if unit_price is None:
            missing_unit_price.append({"id": item_id, "name": item_name})
        elif line_total is None:
            missing_line_total.append({"id": item_id, "name": item_name})
        elif unit_price == 0 and line_total == 0:
            zero_priced.append({"id": item_id, "name": item_name})
        else:
            fully_priced.append(item_id)
    
    # Report findings
    logger.info(f"  📊 Pricing Completeness Check:")
    logger.info(f"     Fully priced: {len(fully_priced)} items")
    
    if zero_priced:
        logger.info(f"     Zero-priced (may be intentional): {len(zero_priced)} items")
        for item in zero_priced[:3]:
            logger.info(f"        • {item['id']}: {item['name'][:40]}")
    
    # Missing prices are a real problem
    missing = missing_unit_price + missing_line_total
    if missing:
        logger.error(f"  ❌ PRICING INCOMPLETE: {len(missing)} items have no price")
        logger.error(f"     An estimate needs prices. This is not optional.")
        for item in missing[:5]:
            logger.error(f"        • {item['id']}: {item['name'][:40]}")
        if len(missing) > 5:
            logger.error(f"        ... and {len(missing) - 5} more")
        raise PricingIncompleteError(
            items_missing_price=[m['id'] for m in missing]
        )
    
    # Calculate and report totals
    total = sum(item.get("line_total", 0) for item in items)
    logger.info(f"  ✓ All {len(items)} items priced (Total: €{total:,.2f})")


# =============================================================================
# ITEM SCHEMAS (Evolving through phases)
# =============================================================================

# Phase 1 output: COMPLETE BOQ ITEM
# BOQ = Bill of Quantities = scope + quantities + pricing + labor hours + schedule
# The BCCA index in context has: CODE|UNIT|PRICE|DESC_100|LABOR_HOURS|BREAKDOWN
# LLM reads PRICE and LABOR_HOURS from index, calculates line_total and total labor
BOQ_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {"type": "string", "description": "Sequential ID: ITEM_001, ITEM_002..."},
        "room_id": {"type": "string", "description": "From canonical room list or 'general'"},
        "room_name": {"type": "string", "description": "Human readable room name"},
        "name": {"type": "string", "description": "Task name in Spanish"},
        "description": {"type": "string", "description": "Detailed description in Spanish"},
        "system": {
            "type": "string", 
            "enum": ["demolition", "plumbing", "electrical", "finishes", "hvac", "carpentry", "ffe", "logistics"],
            "description": "Work system category"
        },
        "bcca_code": {"type": "string", "description": "BCCA item code from index"},
        "bcca_description": {"type": "string", "description": "Description from BCCA index"},
        "ffe_code": {"type": "string", "description": "FFE item code if applicable"},
        "ffe_install_bcca": {"type": "string", "description": "BCCA code for FFE installation"},
        "unit": {"type": "string", "description": "Unit from BCCA: m2, ud, ml, etc."},
        "quantity": {"type": "number", "description": "Estimated quantity"},
        "quantity_formula": {"type": "string", "description": "Formula showing calculation"},
        # PRICING FIELDS - LLM calculates from BCCA index
        "unit_price": {"type": "number", "description": "Price from BCCA index (the PRICE column)"},
        "ffe_price": {"type": "number", "description": "FFE item cost from FFE index if applicable"},
        "ffe_install_price": {"type": "number", "description": "Installation cost from BCCA for FFE items"},
        "line_total": {"type": "number", "description": "quantity × unit_price + FFE costs"},
        "labor_hours": {"type": "number", "description": "LABOR_HOURS from BCCA index × quantity"},
        # SCHEDULING FIELDS
        "phase_week": {"type": "integer", "description": "Week 1-10+ when this happens"},
        "depends_on": {"type": "array", "items": {"type": "string"}, "description": "Item IDs that must complete first"},
        "comparable_reference": {"type": "string", "description": "Why this item from bracket PIR"},
        "energy_impact": {"type": "string", "description": "Energy improvement if applicable"}
    },
    "required": ["item_id", "room_id", "name", "bcca_code", "unit", "quantity", "unit_price", "line_total", "labor_hours", "phase_week"]
}

# Alias for backwards compatibility
SCOPE_BOQ_ITEM_SCHEMA = BOQ_ITEM_SCHEMA
PRICED_ITEM_SCHEMA = BOQ_ITEM_SCHEMA

# Phase 3 adds: adjustment fields
ADJUSTED_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        **PRICED_ITEM_SCHEMA["properties"],
        "price_multiplier": {"type": "number", "description": "Regional adjustment multiplier"},
        "adjusted_price": {"type": "number", "description": "line_total × multiplier"},
        "adjustment_reason": {"type": "string", "description": "E.g., 'Barcelona centro +15%'"}
    },
    "required": ["item_id", "room_id", "name", "bcca_code", "unit", "quantity", "unit_price", "line_total", "adjusted_price"]
}


# =============================================================================
# PHASE 1 SCHEMA: COMPLETE BOQ
# BOQ = Bill of Quantities = scope + quantities + pricing + labor + schedule
# =============================================================================

PHASE_1_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": BOQ_ITEM_SCHEMA,
            "description": "Complete BOQ: work items with BCCA codes, prices, labor hours, and schedule"
        },
        "rooms_coverage": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "item_count": {"type": "integer"}
                },
                "required": ["room_id", "item_count"]
            },
            "description": "Item count per room for coverage check"
        },
        # PRICING TOTALS - calculated from items
        "total_pem": {"type": "number", "description": "Sum of all line_total (Presupuesto de Ejecución Material)"},
        "total_labor_hours": {"type": "number", "description": "Sum of all labor_hours"},
        # SCHEDULING
        "total_weeks": {"type": "integer", "description": "Total project duration"},
        "critical_path": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Item IDs that determine overall duration"
        },
        "energy_improvements_included": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Energy interventions in scope"
        },
        "reasoning_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Deep reasoning about scope, schedule, and pricing decisions"
        },
        "total_items": {"type": "integer"}
    },
    "required": ["items", "rooms_coverage", "total_weeks", "total_items", "total_pem", "total_labor_hours"]
}


# =============================================================================
# PHASE 3A SCHEMA: REVIEW PLAN (Plan step - LLM generates structured plan)
# =============================================================================

# Schema for a new item to add
NEW_ITEM_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "temp_id": {"type": "string", "description": "Temporary ID like NEW_001, NEW_002"},
        "room_id": {"type": "string", "description": "Room this item belongs to"},
        "name": {"type": "string", "description": "Descriptive name in Spanish"},
        "bcca_code": {"type": "string", "description": "BCCA code from index"},
        "bcca_description": {"type": "string", "description": "Description from BCCA"},
        "unit": {"type": "string", "description": "Unit from BCCA (m2, ud, ml, etc.)"},
        "quantity": {"type": "number", "description": "Estimated quantity"},
        "unit_price": {"type": "number", "description": "Price from BCCA index"},
        "line_total": {"type": "number", "description": "quantity × unit_price"},
        "labor_hours": {"type": "number", "description": "LABOR_HOURS from BCCA × quantity"},
        "phase_week": {"type": "integer", "description": "Which week of project"},
        "reason": {"type": "string", "description": "Why this item is needed"},
    },
    "required": ["temp_id", "room_id", "name", "bcca_code", "unit", "quantity", "unit_price", "line_total", "phase_week", "reason"]
}

# Schema for modifying an existing item
ITEM_MODIFICATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {"type": "string", "description": "ID of item to modify (e.g., ITEM_001)"},
        "field": {"type": "string", "description": "Field to change: quantity, unit_price, phase_week, bcca_code, etc."},
        "old_value": {"type": "string", "description": "Current value (for audit trail)"},
        "new_value": {"type": "string", "description": "New value to set"},
        "reason": {"type": "string", "description": "Why this change is needed"},
    },
    "required": ["item_id", "field", "new_value", "reason"]
}

# Schema for sequencing changes
SEQUENCING_CHANGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {"type": "string", "description": "ID of item to reschedule"},
        "old_week": {"type": "integer", "description": "Current phase_week"},
        "new_week": {"type": "integer", "description": "New phase_week"},
        "reason": {"type": "string", "description": "Why: dependency, cure time, etc."},
    },
    "required": ["item_id", "new_week", "reason"]
}

# Main Phase 3a schema - the review plan
PHASE_3A_REVIEW_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        # Items to add (full definitions)
        "items_to_add": {
            "type": "array",
            "items": NEW_ITEM_PLAN_SCHEMA,
            "description": "New items that should be added to the scope"
        },
        # Modifications to existing items
        "items_to_modify": {
            "type": "array",
            "items": ITEM_MODIFICATION_SCHEMA,
            "description": "Changes to make to existing items"
        },
        # Schedule changes
        "sequencing_changes": {
            "type": "array",
            "items": SEQUENCING_CHANGE_SCHEMA,
            "description": "Items that need to be rescheduled"
        },
        # Regional adjustment (single multiplier for all items)
        "regional_adjustment": {
            "type": "object",
            "properties": {
                "multiplier": {"type": "number", "description": "Price multiplier (e.g., 1.15 for +15%)"},
                "factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Factors considered: location, access, building type"
                },
                "reasoning": {"type": "string", "description": "Why this adjustment"}
            },
            "required": ["multiplier", "reasoning"]
        },
        # Analysis summary
        "review_analysis": {
            "type": "object",
            "properties": {
                "gaps_found": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What was missing from Phase 1"
                },
                "errors_corrected": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Errors that were fixed"
                },
                "schedule_issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sequencing problems found"
                },
                "cost_assessment": {"type": "string", "description": "Is the cost reasonable?"},
                "energy_pathway_valid": {"type": "boolean", "description": "Does energy improvement make sense?"},
                "confidence_score": {"type": "integer", "description": "0-100 confidence in estimate"},
                "risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Concerns to flag"
                }
            },
            "required": ["gaps_found", "confidence_score"]
        }
    },
    "required": ["items_to_add", "items_to_modify", "sequencing_changes", "regional_adjustment", "review_analysis"]
}


# =============================================================================
# CONCEPT NARRATIVE SCHEMA (used in Phase 4)
# =============================================================================

# =============================================================================
# DESIGN CONCEPT SCHEMA (Used in Phase 4 and Phase 8)
# =============================================================================

CONCEPT_NARRATIVE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Architect-level design concept with technical justification",
    "properties": {
        "overall_vision": {
            "type": "string",
            "description": "2-3 sentence buyer-friendly summary of the transformed property. Paint the picture - what will it FEEL like?"
        },
        "design_style": {
            "type": "string",
            "description": "Interior design style. E.g., 'Contemporary Mediterranean', 'Scandinavian Minimalist', 'Industrial Loft', 'Modern Classic'"
        },
        "design_rationale": {
            "type": "string",
            "description": "300-500 words explaining WHY these design choices, referencing comparables explicitly. Structure: bracket positioning, common characteristics, how this renovation achieves standards, specific justified choices."
        },
        "key_features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5-8 headline features. Be specific (e.g., 'Open-plan kitchen with soft-close oak cabinetry' not 'New kitchen')"
        },
        "technical_upgrades": {
            "type": "object",
            "description": "Serious technical improvements with architect-level detail",
            "properties": {
                "energy_efficiency": {
                    "type": "object",
                    "properties": {
                        "current_rating": {"type": "string"},
                        "target_rating": {"type": "string"},
                        "interventions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "E.g., 'Double-glazed PVC windows (Uw 1.3 W/m²K)', 'Aerothermal heat pump replacing gas boiler'"
                        },
                        "expected_savings": {"type": "string"}
                    }
                },
                "acoustic": {
                    "type": "object",
                    "properties": {
                        "current_issues": {"type": "string"},
                        "interventions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "E.g., 'Acoustic underlay beneath floating floor (ΔLw 18dB)', 'Triple-seal window gaskets'"
                        }
                    }
                },
                "electrical": {
                    "type": "object",
                    "properties": {
                        "current_state": {"type": "string"},
                        "upgrade_scope": {"type": "string", "description": "E.g., 'Full rewire to REBT 2002 with differential protection per circuit'"},
                        "new_capacity": {"type": "string", "description": "E.g., '9.2kW single phase, adequate for induction hob + AC'"}
                    }
                },
                "plumbing": {
                    "type": "object",
                    "properties": {
                        "current_state": {"type": "string"},
                        "upgrade_scope": {"type": "string"},
                        "water_heating": {"type": "string"}
                    }
                }
            }
        },
        "preserved_elements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Character elements being kept and WHY (e.g., 'Original terrazzo floors — good condition, adds character, saves several thousand euros')"
        },
        "why_not": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string", "description": "Feature NOT included"},
                    "reason": {"type": "string", "description": "Why it's not included, referencing comparables or constraints"}
                },
                "required": ["feature", "reason"]
            },
            "description": "Features NOT included and why (e.g., 'No tub — 0/3 comparables have tubs, walk-in showers are bracket standard')"
        },
        "room_concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "room_name": {"type": "string"},
                    "vision": {"type": "string", "description": "1-2 sentence vision for this room - what's the experience of being in it?"},
                    "comparable_reference": {"type": "string", "description": "Which comparable feature inspired this design direction"},
                    "key_changes": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["room_id", "vision", "key_changes"]
            },
            "description": "Per-room design vision with comparable references"
        }
    },
    "required": ["overall_vision", "design_style", "design_rationale", "key_features", "technical_upgrades"]
}


# =============================================================================
# PHASE 4 SCHEMA: RENDERING PROMPTS + CONCEPT NARRATIVE
# =============================================================================

PHASE_4_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room_prompts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "room_name": {"type": "string"},
                    "photo_index": {"type": "integer"},
                    "transformation_prompt": {"type": "string"},
                    "key_changes": {"type": "array", "items": {"type": "string"}},
                    "preserve_elements": {"type": "array", "items": {"type": "string"}},
                    "style_reference": {"type": "string"}
                },
                "required": ["room_id", "room_name", "transformation_prompt", "key_changes"]
            }
        },
        "hero_room_id": {"type": "string"},
        "hero_room_reason": {"type": "string"},
        "overall_style": {"type": "string"},
        "color_palette": {"type": "array", "items": {"type": "string"}},
        "concept_narrative": CONCEPT_NARRATIVE_SCHEMA
    },
    "required": ["room_prompts", "hero_room_id", "overall_style", "concept_narrative"]
}


## Phase 6 (viewing checklist) removed.


# =============================================================================
# PHASE 7 SCHEMA: ELI5 ROOM SUMMARIES
# =============================================================================

PHASE_7_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "concept": {
            "type": "object",
            "description": "Vision statement - the 'pitch' for this renovation strategy",
            "properties": {
                "vision_statement": {
                    "type": "string",
                    "description": "2-3 sentences capturing what this renovation achieves. E.g., 'A contemporary Mediterranean refresh that preserves original character while bringing the space into 2024 with clean lines and natural materials.'"
                },
                "design_style": {
                    "type": "string",
                    "description": "Interior design style being applied. E.g., 'Contemporary Mediterranean', 'Scandinavian Minimalist', 'Industrial Loft'"
                },
                "key_upgrades": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 upgrades that make the place shine. E.g., 'Oak engineered flooring throughout', 'Quartz countertops', 'Floor-to-ceiling tiling in bathrooms'"
                },
                "value_story": {
                    "type": "string",
                    "description": "Why this makes the property worth more. E.g., 'You're getting a €400K finish for €300K investment'"
                }
            },
            "required": ["vision_statement", "design_style", "key_upgrades", "value_story"]
        },
        "property_summary": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "total_cost": {"type": "number"},
                "total_weeks": {"type": "integer"},
                "rooms_count": {"type": "integer"}
            },
            "required": ["address", "total_cost", "total_weeks"]
        },
        "rooms": {
            "type": "array",
            "description": "Short, glanceable phrases per room - modular and scannable",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "room_name": {"type": "string"},
                    "tagline": {
                        "type": "string",
                        "description": "One punchy phrase. E.g., 'Modern galley with quartz island'"
                    },
                    "key_changes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 SHORT phrases with emoji. E.g., '🪵 Oak flooring', '💡 Recessed lighting', '🚿 Walk-in rainfall shower'"
                    },
                    "cost": {"type": "number"},
                    "weeks": {"type": "string"}
                },
                "required": ["room_id", "room_name", "tagline", "key_changes", "cost"]
            }
        },
        "general_items": {
            "type": "object",
            "properties": {
                "tagline": {"type": "string", "description": "E.g., 'Full systems refresh'"},
                "key_items": {"type": "array", "items": {"type": "string"}},
                "cost": {"type": "number"}
            },
            "required": ["tagline", "key_items", "cost"]
        },
        "timeline": {
            "type": "object",
            "properties": {
                "total_weeks": {"type": "integer"},
                "summary": {"type": "string", "description": "E.g., '10-12 weeks including curing time'"}
            },
            "required": ["total_weeks", "summary"]
        }
    },
    "required": ["concept", "property_summary", "rooms", "timeline"]
}


# =============================================================================
# PHASE 8 SUB-SCHEMAS: EXPANDED ARCHITECT REPORT
# =============================================================================

# Section 1: Target Property Summary
TARGET_PIR_SUMMARY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "address": {"type": "string"},
        "asking_price": {"type": "number"},
        "area_sqm": {"type": "number"},
        "bedrooms": {"type": "integer"},
        "bathrooms": {"type": "integer"},
        "year_built": {"type": "integer"},
        "condition_summary": {"type": "string", "description": "What needs renovation - be specific, not just 'needs work'"},
        "energy_current": {"type": "string"},
        "structural_notes": {"type": "string", "description": "Ceiling heights, load-bearing walls, floor construction"},
        "key_observations": {
            "type": "array", 
            "items": {"type": "string"},
            "description": "What stands out about this property? Quirks, character, constraints."
        }
    },
    "required": ["address", "condition_summary", "key_observations"]
}

# Section 2: Bracket/Comparables Summary
BRACKET_SUMMARY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bracket_label": {"type": "string"},
        "price_range": {"type": "string"},
        "target_buyer_profile": {"type": "string", "description": "Who buys at this bracket? First-time buyers? Investors?"},
        "common_characteristics": {
            "type": "array", 
            "items": {"type": "string"},
            "description": "What ALL successful properties at this bracket share - the non-negotiables"
        },
        "finish_standards": {"type": "string", "description": "Quality level - 'quality basics' vs 'premium but not luxury'"},
        "style_trends": {"type": "string", "description": "Common aesthetic - open plan? neutral palette? Scandi-Mediterranean?"}
    },
    "required": ["bracket_label", "common_characteristics", "finish_standards"]
}

# Section 5: Terms of Reference for Architect
INSPECTION_CHECKLIST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "structural": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Structural checks framed as questions (e.g., 'Are the load-bearing walls where expected?')"
        },
        "mep": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Mechanical/Electrical/Plumbing checks (e.g., 'Is the electrical panel adequate for planned loads?')"
        },
        "envelope": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Windows, facade, waterproofing checks"
        },
        "hidden_conditions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Asbestos likelihood, moisture indicators, party wall issues"
        }
    },
    "required": ["structural", "mep", "envelope", "hidden_conditions"]
}

DESIGN_CONSIDERATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "room": {"type": "string"},
        "comparable_features_to_match": {
            "type": "array", 
            "items": {"type": "string"},
            "description": "What features from comparables should this room achieve?"
        },
        "constraints": {"type": "string", "description": "What limits the design options?"},
        "target_opportunity": {"type": "string", "description": "What's the unique opportunity for this room?"}
    },
    "required": ["room", "comparable_features_to_match"]
}

TERMS_OF_REFERENCE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "inspection_checklist": INSPECTION_CHECKLIST_SCHEMA,
        "design_considerations": {
            "type": "array",
            "items": DESIGN_CONSIDERATION_SCHEMA,
            "description": "Per-room design guidance referencing comparables"
        },
        "design_direction": {
            "type": "string", 
            "description": "Overall guidance: match bracket quality, preserve character, don't over-invest"
        }
    },
    "required": ["inspection_checklist", "design_direction"]
}


# =============================================================================
# PHASE 8 SCHEMA: EXPANDED ARCHITECT REPORT
# =============================================================================

PHASE_8_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        # NEW: Section 1 - The Property
        "target_pir_summary": TARGET_PIR_SUMMARY_SCHEMA,
        
        # NEW: Section 2 - The Comparables
        "bracket_summary": BRACKET_SUMMARY_SCHEMA,
        
        # NEW: Section 3 - The Concept (passed from Phase 4)
        "design_concept": CONCEPT_NARRATIVE_SCHEMA,
        
        # Section 4: Scope & BOQ (existing structure)
        "document_header": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "bracket_label": {"type": "string"},
                "reference": {"type": "string"},
                "date": {"type": "string"},
                "version": {"type": "string"}
            },
            "required": ["title", "reference", "date"]
        },
        "executive_summary": {
            "type": "object",
            "properties": {
                "asking_price": {"type": "number"},
                "renovation_cost": {"type": "number"},
                "total_investment": {"type": "number"},
                "target_price": {"type": "number"},
                "potential_margin": {"type": "number"},
                "weeks_range": {
                    "type": "object",
                    "properties": {"min": {"type": "integer"}, "max": {"type": "integer"}}
                },
                "line_items_count": {"type": "integer"},
                "rooms_count": {"type": "integer"}
            },
            "required": ["renovation_cost", "total_investment", "line_items_count"]
        },
        "cost_breakdown": {
            "type": "object",
            "properties": {
                "pem": {"type": "number"},
                "overhead_13pct": {"type": "number"},
                "profit_6pct": {"type": "number"},
                "subtotal": {"type": "number"},
                "iva_21pct": {"type": "number"},
                "total_with_iva": {"type": "number"}
            },
            "required": ["pem", "total_with_iva"]
        },
        "by_trade": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trade_code": {"type": "string"},
                    "trade_name": {"type": "string"},
                    "subtotal": {"type": "number"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_id": {"type": "string"},
                                "bcca_code": {"type": "string"},
                                "description": {"type": "string"},
                                "room_id": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                                "unit_price": {"type": "number"},
                                "line_total": {"type": "number"}
                            },
                            "required": ["item_id", "bcca_code", "description", "quantity", "unit", "line_total"]
                        }
                    }
                },
                "required": ["trade_code", "trade_name", "subtotal", "items"]
            }
        },
        "by_room": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "room_name": {"type": "string"},
                    "items_count": {"type": "integer"},
                    "subtotal": {"type": "number"},
                    "percentage": {"type": "number"}
                },
                "required": ["room_id", "subtotal"]
            }
        },
        "timeline": {
            "type": "object",
            "properties": {
                "total_weeks": {
                    "type": "object",
                    "properties": {"min": {"type": "integer"}, "max": {"type": "integer"}}
                },
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "week_start": {"type": "integer"},
                            "week_end": {"type": "integer"},
                            "trades": {"type": "array", "items": {"type": "string"}},
                            "tasks": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "week_start", "week_end"]
                    }
                },
                "milestones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "week": {"type": "integer"},
                            "description": {"type": "string"}
                        },
                        "required": ["week", "description"]
                    }
                },
                "critical_path": {"type": "array", "items": {"type": "string"}}
            }
        },
        "energy_compliance": {
            "type": "object",
            "properties": {
                "current_rating": {"type": "string"},
                "target_rating": {"type": "string"},
                "improvement_letters": {"type": "integer"},
                "climate_zone": {"type": "string"},
                "meets_cte_db_he": {"type": "boolean"},
                "measures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "improvement": {"type": "string"},
                            "impact": {"type": "string"},
                            "included_in_scope": {"type": "boolean"}
                        },
                        "required": ["improvement", "included_in_scope"]
                    }
                }
            }
        },
        "compliance_notes": {
            "type": "object",
            "properties": {
                "standards": {"type": "array", "items": {"type": "string"}},
                "permits_required": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"}
            }
        },
        "risk_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "flag": {"type": "string"},
                    "severity": {"type": "string"},
                    "mitigation": {"type": "string"}
                },
                "required": ["flag", "severity"]
            }
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string"},
                    "priority": {"type": "string"}
                },
                "required": ["recommendation"]
            }
        },
        "confidence_score": {"type": "integer"},
        "sanity_check_passed": {"type": "boolean"},
        
        # NEW: Section 5 - Terms of Reference
        "terms_of_reference": TERMS_OF_REFERENCE_SCHEMA
    },
    "required": [
        "target_pir_summary",
        "bracket_summary", 
        "design_concept",
        "document_header", 
        "executive_summary", 
        "cost_breakdown", 
        "by_trade", 
        "terms_of_reference",
        "confidence_score"
    ]
}


# =============================================================================
# PIR SCHEMAS
# =============================================================================
# ⚠️  DEPRECATION NOTICE - V2 Migration 2026-01-16
# BRACKET_PIR_SCHEMA and TARGET_BRACKET_REASONING_SCHEMA are DEPRECATED.
# V2 uses data-driven comparable analysis instead of abstract brackets.
# See: V2_IMPLEMENTATION_PLAN.md for migration guide.
# =============================================================================

# ⚠️  DEPRECATED - Use strategy_selector.py instead
BRACKET_PIR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bracket_name": {"type": "string"},
        "design_era": {"type": "string"},
        "finish_level_summary": {"type": "string"},
        "what_defines_this_bracket": {"type": "string"},
        "bracket_narrative": {"type": "string"},
        "common_materials": {
            "type": "object",
            "properties": {
                "flooring": {"type": "array", "items": {"type": "string"}},
                "walls": {"type": "array", "items": {"type": "string"}},
                "kitchen": {"type": "array", "items": {"type": "string"}},
                "bathroom": {"type": "array", "items": {"type": "string"}},
                "windows_doors": {"type": "array", "items": {"type": "string"}},
                "lighting": {"type": "array", "items": {"type": "string"}}
            }
        },
        "typical_features": {"type": "array", "items": {"type": "string"}},
        "kitchen_narrative": {"type": "string"},
        "bathroom_narrative": {"type": "string"},
        "living_spaces_narrative": {"type": "string"},
        "bedroom_narrative": {"type": "string"},
        "distinguishing_features": {"type": "string"},
        "buyer_expectations": {"type": "string"},
        "local_market_context": {"type": "string"}
    },
    "required": ["bracket_name", "design_era", "bracket_narrative"]
}

# =============================================================================
# PIR V2.0 - 6-DIMENSION ROOM ANALYSIS SCHEMA
# =============================================================================
# Each room is analyzed across 6 physical dimensions that map to renovation work.
# This provides structured data for BOQ generation while maintaining rich narratives.
# =============================================================================

# Dimension 1: Shell & Preparation (Masonry/Plaster)
SHELL_PREPARATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "wall_substrate": {
            "type": "string",
            "description": "Texture: Smooth Skim, Heavy Stucco/Gotelé, Exposed Brick, Paneling, etc."
        },
        "ceiling_substrate": {
            "type": "string", 
            "description": "Texture: Popcorn/Textured, Smooth Plaster, Suspended Grid, Exposed Beams, etc."
        },
        "condition_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Visible cracks, damp patches, peeling plaster, holes requiring demolition/prep"
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose description of wall/ceiling substrates and condition"
        }
    }
}

# Dimension 2: Apertures & Enclosure (Joinery/Glazing)
APERTURES_ENCLOSURE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "windows": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "PVC, Aluminum, Wood"},
                "opening_style": {"type": "string", "description": "Sliding, Casement, Sash"},
                "color": {"type": "string"},
                "glazing": {"type": "string", "description": "Single, Double, Triple"}
            }
        },
        "shutters": {
            "type": "object",
            "properties": {
                "present": {"type": "boolean"},
                "type": {"type": "string", "description": "External box, Integrated"},
                "operation": {"type": "string", "description": "Strap/Belt visible, Switch/Electric"}
            }
        },
        "internal_doors": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "description": "Flush, Panelled, Glass"},
                "material_finish": {"type": "string", "description": "Painted, Natural Wood, Lacquered"},
                "architrave_style": {"type": "string"}
            }
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose about windows, shutters, and doors"
        }
    }
}

# Dimension 3: Systems & Services (MEP)
SYSTEMS_SERVICES_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "lighting": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Center Pendant, Recessed Spotlights, Track, Wall Sconces"},
                "quantity_density": {"type": "string", "description": "Count or density description"}
            }
        },
        "electrical": {
            "type": "object",
            "properties": {
                "socket_switch_style": {"type": "string", "description": "Modern White, Antique, Metal"},
                "placement": {"type": "string", "description": "Surface mounted vs. Recessed"},
                "adequacy": {"type": "string", "description": "Count adequate? Modern standards?"}
            }
        },
        "climate": {
            "type": "object",
            "properties": {
                "heating": {"type": "string", "description": "Cast Iron Radiators, Aluminum Radiators, Underfloor controller, None"},
                "cooling": {"type": "string", "description": "Split Unit AC, Central Air Grilles, None"}
            }
        },
        "plumbing": {
            "type": "object",
            "properties": {
                "visible_pipework": {"type": "string", "description": "Exposed vs. Hidden"},
                "boiler_presence": {"type": "boolean"},
                "boiler_type": {"type": "string"}
            }
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose about electrical, plumbing, HVAC evidence"
        }
    }
}

# Dimension 4: Surface Finishes (Decor)
SURFACE_FINISHES_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "flooring": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "Laminate, Engineered Oak, Ceramic Tile, Marble, Carpet, Linoleum, Terrazo"},
                "format": {"type": "string", "description": "Plank width, Tile size (e.g., 60x60cm)"},
                "layout": {"type": "string", "description": "Straight, Herringbone, Diagonal"}
            }
        },
        "wall_finish": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Paint (Matte/Gloss), Wallpaper (Pattern/Texture), Tiling"},
                "tiling_height": {"type": "string", "description": "For wet areas: Full height, Half height, Splash-back only"},
                "tile_size": {"type": "string"}
            }
        },
        "junctions": {
            "type": "object",
            "properties": {
                "skirting_baseboard": {
                    "type": "object",
                    "properties": {
                        "height": {"type": "string"},
                        "material": {"type": "string"},
                        "profile": {"type": "string"}
                    }
                },
                "cornice_coving": {
                    "type": "object",
                    "properties": {
                        "present": {"type": "boolean"},
                        "style": {"type": "string"}
                    }
                }
            }
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose about flooring, wall finishes, junctions"
        }
    }
}

# Dimension 5: Fixed Joinery & Equipment (Fittings)
FIXED_JOINERY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cabinetry": {
            "type": "object",
            "properties": {
                "door_style": {"type": "string", "description": "Shaker, Slab, Glass"},
                "finish": {"type": "string", "description": "Matte, Gloss, Wood grain"},
                "handle_style": {"type": "string", "description": "Integrated, Knob, Bar"}
            }
        },
        "countertops": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "Laminate, Solid Wood, Granite, Quartz, Marble"},
                "edge_profile": {"type": "string"},
                "thickness": {"type": "string"}
            }
        },
        "sanitaryware": {
            "type": "object",
            "properties": {
                "toilet_type": {"type": "string", "description": "Wall-hung, Floor-mounted"},
                "sink_type": {"type": "string", "description": "Pedestal, Vanity-top, Wall-mounted"},
                "shower_bath": {"type": "string", "description": "Walk-in shower, Tub, Combined"},
                "enclosure": {"type": "string", "description": "Glass screen vs. Curtain"}
            }
        },
        "storage": {
            "type": "object",
            "properties": {
                "built_in_wardrobes": {"type": "string", "description": "None, Sliding, Hinged, Walk-in"}
            }
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose about cabinetry, countertops, sanitaryware, storage. State 'None' if not applicable."
        }
    }
}

# Dimension 6: Details & Fittings (Hardware)
DETAILS_HARDWARE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "door_handles": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "description": "Lever, Knob, Pull"},
                "finish": {"type": "string", "description": "Chrome, Brass, Matte Black, Satin Nickel"}
            }
        },
        "cabinet_hardware": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Knobs, Bar pulls, Handleless/Push-click"},
                "finish": {"type": "string"}
            }
        },
        "bathroom_fittings": {
            "type": "object",
            "properties": {
                "tap_style": {"type": "string", "description": "Mixer, Separate H/C, Wall-mounted"},
                "tap_finish": {"type": "string"},
                "accessories": {"type": "string", "description": "Towel rail style, mirror type, accessories"}
            }
        },
        "switch_socket_plates": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "description": "Standard white, Designer, Smart/touch"},
                "finish": {"type": "string"}
            }
        },
        "trim_details": {
            "type": "object",
            "properties": {
                "grout_color": {"type": "string"},
                "sealant_condition": {"type": "string"},
                "finishing_quality": {"type": "string", "description": "Overall execution quality"}
            }
        },
        "narrative": {
            "type": "string",
            "description": "Detailed prose about hardware, fixtures, trim - the 'jewelry' of the room"
        }
    }
}


# =============================================================================
# PIR V2.0 MAIN SCHEMA
# =============================================================================

PIR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "building_profile": {
            "type": "object",
            "properties": {
                "year_built": {"type": "integer"},
                "construction_era": {"type": "string"},
                "building_type": {"type": "string"},
                "floor": {"type": "integer"},
                "total_floors": {"type": "integer"},
                "energy_rating": {"type": "string"},
                "building_narrative": {"type": "string"}
            }
        },
        "rooms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    # CORE IDENTIFIERS
                    "room_id": {"type": "string"},
                    "room_type": {"type": "string"},
                    
                    # LEGACY FIELDS (maintained for compatibility)
                    "visual_narrative": {
                        "type": "string",
                        "description": "RICH prose narrative walking through the room. This is the main descriptive text."
                    },
                    "condition_summary": {"type": "string"},
                    "condition_rating": {"type": "string", "description": "poor/fair/good/excellent"},
                    "key_issues": {"type": "array", "items": {"type": "string"}},
                    "elements_observed": {"type": "array", "items": {"type": "string"}},
                    "estimated_dimensions": {"type": "string"},
                    "natural_light": {"type": "string"},
                    "layout_notes": {"type": "string"},
                    
                    # V2.0: 6-DIMENSION STRUCTURED ANALYSIS
                    "dimensions": {
                        "type": "object",
                        "properties": {
                            "shell_preparation": SHELL_PREPARATION_SCHEMA,
                            "apertures_enclosure": APERTURES_ENCLOSURE_SCHEMA,
                            "systems_services": SYSTEMS_SERVICES_SCHEMA,
                            "surface_finishes": SURFACE_FINISHES_SCHEMA,
                            "fixed_joinery": FIXED_JOINERY_SCHEMA,
                            "details_hardware": DETAILS_HARDWARE_SCHEMA
                        },
                        "description": "Structured analysis across 6 physical dimensions for BOQ generation"
                    }
                },
                "required": ["room_id", "room_type", "visual_narrative", "dimensions"]
            }
        },
        "design_profile": {
            "type": "object",
            "properties": {
                "dominant_style": {"type": "string"},
                "finish_quality_overall": {"type": "string"},
                "color_palette": {"type": "array", "items": {"type": "string"}},
                "design_narrative": {"type": "string"}
            }
        },
        "triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "trigger": {"type": "string"},
                    "urgency": {"type": "string"},
                    "evidence": {"type": "string"},
                    "detailed_reasoning": {"type": "string"},
                    "affected_rooms": {"type": "array", "items": {"type": "string"}},
                    "estimated_scope": {"type": "string"}
                },
                "required": ["category", "trigger", "urgency"]
            }
        },
        # V2.1: REGULATORY FLAGS - based on rules_engine_v2.json
        # PIR must confirm or debunk visual triggers from the rules engine
        "regulatory_flags": {
            "type": "array",
            "description": "For EACH rule_id that COULD apply based on property year, indicate if visual triggers were CONFIRMED or DEBUNKED",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "Rule ID from rules_engine (e.g., ELEC_REBT_001, PLUMB_LEAD_001)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["confirmed", "debunked", "inconclusive"],
                        "description": "confirmed: visual triggers DEFINITELY seen. debunked: looked carefully and DEFINITELY not present. inconclusive: cannot determine from photos."
                    },
                    "evidence": {
                        "type": "string",
                        "description": "What was seen (or NOT seen) that led to this determination"
                    },
                    "affected_rooms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which rooms showed this evidence"
                    }
                },
                "required": ["rule_id", "status", "evidence"]
            }
        },
        "property_narrative": {"type": "string"},
        "renovation_context": {"type": "string"}
    },
    "required": ["building_profile", "rooms", "property_narrative"]
}


# ⚠️  DEPRECATED - Use delta_scope_generator.py instead
TARGET_BRACKET_REASONING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "strategic_summary": {
            "type": "string",
            "description": "800-1200 words of strategic narrative synthesizing renovation philosophy"
        },
        "structural_realities": {
            "type": "string",
            "description": "Exhaustive description of permanent constraints that cannot change"
        },
        "inherent_advantages": {
            "type": "string",
            "description": "What this property has that is special, rare, or valuable"
        },
        "bracket_alignment_analysis": {
            "type": "string",
            "description": "Detailed analysis comparing target property to bracket expectations"
        },
        "impossibilities": {
            "type": "string",
            "description": "Bracket expectations this property cannot deliver"
        },
        "opportunity_zones": {
            "type": "string",
            "description": "Where this property could exceed bracket expectations"
        },
        "individuality_assessment": {
            "type": "string",
            "description": "500-800 words about this property's character and soul"
        },
        "strategic_direction": {
            "type": "string",
            "description": "Core strategy thesis guiding all scope decisions"
        },
        "confidence_notes": {
            "type": "string",
            "description": "Honest assessment of confidence levels and uncertainties"
        },
        "scoper_guidance": {
            "type": "string",
            "description": "600-1000 words of detailed room-by-room guidance"
        }
    },
    "required": [
        "strategic_summary",
        "structural_realities",
        "inherent_advantages",
        "bracket_alignment_analysis",
        "impossibilities",
        "opportunity_zones",
        "individuality_assessment",
        "strategic_direction",
        "confidence_notes",
        "scoper_guidance"
    ]
}


# =============================================================================
# REGISTRIES
# =============================================================================

GEMINI_SCHEMAS_V1 = {
    1: PHASE_1_SCHEMA,
    3: PHASE_3A_REVIEW_PLAN_SCHEMA,  # Plan step (code applies it)
    4: PHASE_4_SCHEMA,
    7: PHASE_7_SCHEMA,
    8: PHASE_8_SCHEMA,
    "pir": PIR_SCHEMA,
    "bracket_pir": BRACKET_PIR_SCHEMA,
    "target_bracket_reasoning": TARGET_BRACKET_REASONING_SCHEMA,
}

ITEM_SCHEMAS_V1 = {
    1: SCOPE_BOQ_ITEM_SCHEMA,
    3: BOQ_ITEM_SCHEMA,  # Phase 3 code adds adjustment fields to BOQ items
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_schema_for_phase_v1(phase_num: int) -> Dict[str, Any]:
    """Get the Gemini-native schema for a phase."""
    if phase_num not in GEMINI_SCHEMAS_V1:
        raise ValueError(f"No schema defined for phase {phase_num}")
    return GEMINI_SCHEMAS_V1[phase_num]


def get_item_schema_for_phase_v1(phase_num: int) -> Dict[str, Any]:
    """Get the item schema appropriate for a phase."""
    if phase_num not in ITEM_SCHEMAS_V1:
        raise ValueError(f"No item schema defined for phase {phase_num}")
    return ITEM_SCHEMAS_V1[phase_num]
