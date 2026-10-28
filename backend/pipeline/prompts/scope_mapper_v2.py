"""
=========================================================
PHASE 2: SCOPE MAPPER PROMPT
=========================================================
Maps detected conditions to remedial tasks with specifications.
Uses Gemini to generate technical specifications for BCCA lookup.

This is NOT about inventing tasks - it's about:
1. Consolidating duplicates (same defect across rooms)
2. Generating BCCA-optimized specifications
3. Creating "Essential" vs "Modern" spec variants
=========================================================
"""

from typing import Dict, Any

# The context for Gemini to understand its role
SYSTEM_CONTEXT = """You are a Spanish Construction Specification Expert.

## Your Role
You receive a list of remedial tasks derived from a property assessment. Your job is to:
1. **Consolidate** duplicate tasks (same defect type appearing in multiple rooms)
2. **Specify** each task with technical details optimized for BCCA (Base de Costos de la Construcción de Andalucía) lookup
3. **Differentiate** between ESSENTIAL (minimum legal spec) and MODERN (high-efficiency spec)

## Spanish Construction Standards Reference
- **REBT 2002**: Electrical safety - minimum standards for circuits, grounding, panels
- **CTE DB-HE**: Energy efficiency - thermal envelope, HVAC efficiency ratings
- **CTE DB-HS**: Salubrity - ventilation, waterproofing, water quality
- **CTE DB-HR**: Acoustics - sound insulation requirements
- **RITE 2013**: HVAC installations - sealed combustion, efficiency ratings

## BCCA Keyword Guidelines
BCCA uses specific Spanish construction terminology. Good keywords include:
- "instalación eléctrica vivienda" (not just "electricidad")
- "ventana PVC oscilobatiente doble acristalamiento" (specific window type)
- "bomba de calor aerotermia" (heat pump technology)
- "impermeabilización baño" (bathroom waterproofing)

## Output Quality Rules
1. **Be specific** - "m² de aislamiento SATE EPS 60mm" is better than "aislamiento"
2. **Include units** - Always specify m², ml, ud, etc. where applicable
3. **Reference regulation** - Cite the specific CTE/REBT section that mandates this
4. **Quantify when possible** - Use room counts/sqm from the property data
"""

# The prompt template for scope generation
SCOPE_GENERATION_PROMPT = """## Property Context
- **Year Built**: {year_built} ({year_source})
- **Property Size**: {sqm} m²
- **Rooms Assessed**: {room_count}

## Detected Conditions (from Phase 1 Assessment)
{conditions_summary}

## Your Task
Generate consolidated remedial scopes for both packages:

### Package 1: ESSENTIAL (Safety & Legal Compliance)
Goal: Pass ITE inspection, obtain Cédula de Habitabilidad, meet insurance requirements.
Standard: REBT 2002, CTE DB-HS, RITE 2013 minimums.
Include ONLY: SAFETY, LEGAL, HYGIENE, STRUCTURAL categories.
Specification level: **Minimum compliant** - basic materials that meet regulations.

### Package 2: MODERN (Comfort & Efficiency)  
Goal: CTE 2019+ energy standards, comfort optimization, property value increase.
Standard: CTE DB-HE full compliance, EU 2030 efficiency targets.
Include: EVERYTHING from ESSENTIAL (inherited) + ENERGY, COMFORT, ACOUSTIC categories.
Specification level: **High efficiency** - premium materials, better performance.

## Rules
1. **Consolidate duplicates** - If "replace windows" appears in 3 rooms, create ONE task with quantity "3 units"
2. **Essential items go to MODERN too** - MODERN inherits all ESSENTIAL items (may have upgraded specs)
3. **Add spec_upgrade for MODERN** - When inheriting from ESSENTIAL, specify the upgrade
4. **Include regulation reference** - Every task must cite the Spanish regulation requiring it
5. **Generate BCCA keywords** - Optimized for Spanish construction database search

## Critical Constraints
- Do NOT invent new defects - only process what was detected
- Do NOT skip any detected condition
- Do NOT provide prices - that's Phase 3
- Keep "essential_reason" concise (max 100 chars)
- Keep "modern_upgrade" concise (max 100 chars)
"""

# Response schema for structured output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "property_summary": {
            "type": "object",
            "description": "Brief property summary used for scope",
            "properties": {
                "year_built": {"type": "integer"},
                "age_category": {
                    "type": "string",
                    "enum": ["pre_1980", "1980_2006", "post_2006"]
                },
                "sqm": {"type": "number"},
                "total_defects_processed": {"type": "integer"}
            },
            "required": ["year_built", "age_category", "sqm", "total_defects_processed"]
        },
        "essential_package": {
            "type": "object",
            "description": "Minimum legal compliance package",
            "properties": {
                "name": {"type": "string"},
                "goal": {"type": "string"},
                "standard": {"type": "string"},
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Unique identifier for this task"
                            },
                            "title": {
                                "type": "string",
                                "description": "Human-readable task title in Spanish"
                            },
                            "system": {
                                "type": "string",
                                "enum": ["electrical", "plumbing", "envelope", "ventilation", "structure", "hvac", "finishes"]
                            },
                            "category": {
                                "type": "string",
                                "enum": ["SAFETY", "LEGAL", "HYGIENE", "STRUCTURAL", "ENERGY", "COMFORT", "ACOUSTIC"]
                            },
                            "regulation": {
                                "type": "string",
                                "description": "Spanish regulation requiring this (e.g., REBT 2002, CTE DB-HS 4)"
                            },
                            "specification": {
                                "type": "string",
                                "description": "Technical specification for minimum compliant solution"
                            },
                            "bcca_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Search keywords for BCCA database (2-3 variants)"
                            },
                            "quantity_description": {
                                "type": "string",
                                "description": "e.g., '3 unidades', 'vivienda completa', '45 m²'"
                            },
                            "rooms_affected": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of room names where this applies"
                            },
                            "source_conditions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Rule IDs from Phase 1 that triggered this task"
                            },
                            "essential_reason": {
                                "type": "string",
                                "description": "Why this is ESSENTIAL (max 100 chars)"
                            }
                        },
                        "required": ["task_id", "title", "system", "category", "regulation", "specification", "bcca_keywords", "quantity_description", "rooms_affected", "source_conditions", "essential_reason"]
                    }
                }
            },
            "required": ["name", "goal", "standard", "tasks"]
        },
        "modern_package": {
            "type": "object",
            "description": "Full efficiency and comfort package",
            "properties": {
                "name": {"type": "string"},
                "goal": {"type": "string"},
                "standard": {"type": "string"},
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string"
                            },
                            "title": {
                                "type": "string"
                            },
                            "system": {
                                "type": "string",
                                "enum": ["electrical", "plumbing", "envelope", "ventilation", "structure", "hvac", "finishes"]
                            },
                            "category": {
                                "type": "string",
                                "enum": ["SAFETY", "LEGAL", "HYGIENE", "STRUCTURAL", "ENERGY", "COMFORT", "ACOUSTIC"]
                            },
                            "regulation": {
                                "type": "string"
                            },
                            "specification": {
                                "type": "string",
                                "description": "Technical specification - upgraded for MODERN items"
                            },
                            "bcca_keywords": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "quantity_description": {
                                "type": "string"
                            },
                            "rooms_affected": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "source_conditions": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "inherited_from_essential": {
                                "type": "boolean",
                                "description": "True if this task also exists in ESSENTIAL package"
                            },
                            "modern_upgrade": {
                                "type": "string",
                                "description": "How this differs from ESSENTIAL spec (null if not inherited)"
                            }
                        },
                        "required": ["task_id", "title", "system", "category", "regulation", "specification", "bcca_keywords", "quantity_description", "rooms_affected", "source_conditions", "inherited_from_essential"]
                    }
                }
            },
            "required": ["name", "goal", "standard", "tasks"]
        },
        "consolidation_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Notes on how duplicate conditions were consolidated"
        }
    },
    "required": ["property_summary", "essential_package", "modern_package", "consolidation_notes"]
}


def build_scope_prompt(
    year_built: int,
    year_source: str,
    sqm: float,
    room_assessments: list,
) -> str:
    """Build the prompt for scope generation from Phase 1 data."""
    
    # Build conditions summary from room assessments
    conditions_by_system = {}
    room_count = len(room_assessments)
    
    for room in room_assessments:
        room_name = room.get("room_name", "Unknown")
        conditions = room.get("detected_conditions", [])
        
        for cond in conditions:
            system = cond.get("system", "unknown")
            if system not in conditions_by_system:
                conditions_by_system[system] = []
            
            conditions_by_system[system].append({
                "room": room_name,
                "rule_id": cond.get("rule_id"),
                "category": cond.get("category"),
                "trigger_type": cond.get("trigger_type"),
                "confidence": cond.get("confidence"),
                "observation": cond.get("observation", "")[:200],  # Truncate long observations
                "risk_label": cond.get("risk_label"),
                "package": cond.get("package"),
            })
    
    # Format conditions summary
    conditions_lines = []
    for system, conds in conditions_by_system.items():
        conditions_lines.append(f"\n### System: {system.upper()}")
        for c in conds:
            conditions_lines.append(
                f"- [{c['trigger_type']}] {c['rule_id']} in {c['room']}: "
                f"{c['risk_label']} ({c['category']}) - Package: {c['package']}"
            )
            if c.get("observation"):
                conditions_lines.append(f"  Observation: {c['observation']}")
    
    conditions_summary = "\n".join(conditions_lines)
    
    return SCOPE_GENERATION_PROMPT.format(
        year_built=year_built,
        year_source=year_source,
        sqm=sqm or "Unknown",
        room_count=room_count,
        conditions_summary=conditions_summary,
    )


def get_system_context() -> str:
    """Return the system context for the Gemini call."""
    return SYSTEM_CONTEXT

