"""
V2 Delta Scope Generation Module (New Call #2)
==============================================

PURPOSE:
--------
For each Strategy × Dimension × Room, generate:
1. SPECIFICATION STRATEGY - An Architect's Directive that commits to quality level
2. COST COMPONENTS - Discrete items that flow from that specification

This solves "Contextual Drift" - where the LLM sees a wood floor but doesn't 
explicitly decide if it's cheap laminate or expensive oak before pricing.

PHILOSOPHY:
-----------
- Chain-of-Thought reasoning: Force explicit quality decisions BEFORE pricing
- The Architect's Note commits to finish grade, installation style, aesthetic goal
- Cost components flow STRICTLY from the specification (no drift)

After all 6 dimensions, a SCOPE REVIEW call fills gaps for:
- Move-in readiness items (cleaning, touch-ups)
- Commonly missed baseline work
- Cross-dimension consistency

EXECUTION PATTERN:
------------------
- 3 strategies run IN PARALLEL
- Within each strategy: 6 dimensions run IN SEQUENCE
- After dimensions: 1 scope review call
- Total: 21 Gemini calls (18 dimension + 3 review)

MODEL: gemini-3-flash-preview (alias: "flash")
"""

import json
import asyncio
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

try:
    from ..pipeline.gemini_client import call_gemini
except ImportError:
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from pipeline.gemini_client import call_gemini

from .schemas.gemini_schemas_v2 import V2_DIMENSIONS
from pathlib import Path


# =============================================================================
# KNOWLEDGE BASE LOADING
# =============================================================================

def _load_knowledge_base(filename: str) -> str:
    """Load a knowledge base JSON file from standards folder."""
    import json
    standards_path = Path(__file__).parent.parent.parent / "standards" / filename
    if standards_path.exists():
        try:
            with open(standards_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
    return f"{filename} NOT AVAILABLE"


def _load_knowledge_graph() -> str:
    """Load the renovation knowledge graph with quantity guidance."""
    kg_path = Path(__file__).parent / "kg_context.yaml"
    if kg_path.exists():
        return kg_path.read_text(encoding='utf-8')
    return "KNOWLEDGE GRAPH NOT AVAILABLE"


def _load_all_knowledge_bases() -> Dict[str, str]:
    """Load all knowledge bases for delta scope context."""
    return {
        "energy": _load_knowledge_base("energy_knowledge.json"),
        "design": _load_knowledge_base("interior_design_knowledge.json"),
        "process": _load_knowledge_base("renovation_process_knowledge.json"),
        "knowledge_graph": _load_knowledge_graph(),
    }


# Cache knowledge bases (loaded once)
_KNOWLEDGE_CACHE = None

def _get_knowledge_context() -> str:
    """Get formatted knowledge context for prompts."""
    global _KNOWLEDGE_CACHE
    
    if _KNOWLEDGE_CACHE is None:
        logger.info("  📚 Loading knowledge bases for delta scope...")
        kbs = _load_all_knowledge_bases()
        
        _KNOWLEDGE_CACHE = f"""
═══════════════════════════════════════════════════════════════════════════════
ENERGY & BUILDING REGULATIONS KNOWLEDGE (CTE Compliance)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: Spanish building code (CTE) requires specific energy standards.
When scoping work, consider: Does this old property need insulation upgrades to meet
current standards? Does the reference comparable have features (thermal windows,
ventilation) that imply regulatory upgrades for the target?

{kbs['energy'][:15000]}

═══════════════════════════════════════════════════════════════════════════════
INTERIOR DESIGN KNOWLEDGE (Material Quality & Style)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: To understand what quality level different finishes represent.
Use this to identify the GAP between target (old finishes) and reference (modern
finishes) and scope appropriate upgrades.

{kbs['design'][:15000]}

═══════════════════════════════════════════════════════════════════════════════
RENOVATION PROCESS KNOWLEDGE (Dependencies & Sequencing)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: To understand what work items typically accompany other work.
If scoping new electrical, you likely need to scope wall chasing and replastering.
Think about the full chain of work, not isolated items.

{kbs['process'][:15000]}

═══════════════════════════════════════════════════════════════════════════════
RENOVATION KNOWLEDGE GRAPH (683 Tasks with Quantity Guidance)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: This is your MASTER REFERENCE for renovation tasks. Each task 
includes:
- QUANTITY GUIDANCE: How to measure (area_m2, count, linear_m), what factors to 
  consider, industry measurement rules, min/max constraints
- DEPENDENCIES: REQUIRES (prerequisites) and TRIGGERS (what follows)
- TRADE assignments and BCCA chapter mappings

When scoping work, CHECK THIS GRAPH to:
1. Find the standard task name and measurement approach
2. See what dependencies that task has (what else needs to be scoped)
3. Understand the quantity guidance (per_room, per_opening, per_unit)

{kbs['knowledge_graph'][:200000]}
"""
        logger.info(f"    ✓ Knowledge context: {len(_KNOWLEDGE_CACHE):,} chars")
    
    return _KNOWLEDGE_CACHE


# =============================================================================
# DIMENSION NAMES
# =============================================================================

DIMENSION_NAMES = {
    "shell_preparation": "Shell & Preparation (Masonry/Plaster)",
    "apertures_enclosure": "Apertures & Enclosure (Joinery/Glazing)",
    "systems_services": "Systems & Services (MEP)",
    "surface_finishes": "Surface Finishes (Decor)",
    "fixed_joinery_equipment": "Fixed Joinery & Equipment (Fittings)",
    "details_fittings": "Details & Fittings (Hardware)"
}


# =============================================================================
# OUTPUT SCHEMA - WITH SPECIFICATION STRATEGY
# =============================================================================

ROOM_SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "room_name": {"type": "string"},
        "specification_strategy": {
            "type": "string",
            "description": "Architect's Directive: A rich paragraph describing finish grade, installation style, aesthetic goal, material choices. Use adjectives (warm, minimalist, restored). This COMMITS to quality level BEFORE cost items."
        },
        "cost_components": {
            "type": "array",
            "description": "Discrete line items that flow STRICTLY from the Specification Strategy above",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["demolition", "preparation", "supply_install", "repair", "upgrade", "replace"]
                    },
                    "element": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Rich detail: material, grade, finish, installation method"
                    },
                    "estimated_quantity": {"type": "string"}
                },
                "required": ["action", "element", "description"]
            }
        }
    },
    "required": ["room_id", "room_name", "specification_strategy", "cost_components"]
}

DIMENSION_DELTA_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension": {"type": "string"},
        "dimension_summary": {
            "type": "string",
            "description": "Overall story for this dimension across the property"
        },
        "room_scopes": {
            "type": "array",
            "items": ROOM_SCOPE_SCHEMA
        }
    },
    "required": ["dimension", "dimension_summary", "room_scopes"]
}


# =============================================================================
# SCOPE REVIEW SCHEMA
# =============================================================================

SCOPE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "review_summary": {
            "type": "string",
            "description": "Overview of gaps found and baseline items needed"
        },
        "amendments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "dimension": {"type": "string"},
                    "amendment_type": {
                        "type": "string",
                        "enum": ["add_item", "modify_item", "baseline_refresh"]
                    },
                    "reason": {"type": "string"},
                    "specification_note": {
                        "type": "string",
                        "description": "Architect's note for this addition"
                    },
                    "cost_component": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "element": {"type": "string"},
                            "description": {"type": "string"},
                            "estimated_quantity": {"type": "string"}
                        },
                        "required": ["action", "element", "description"]
                    }
                },
                "required": ["room_id", "dimension", "amendment_type", "reason", "cost_component"]
            }
        }
    },
    "required": ["review_summary", "amendments"]
}


# =============================================================================
# PROMPT BUILDER - WITH SPECIFICATION STRATEGY
# =============================================================================

def _build_dimension_prompt(
    target_rooms: List[Dict[str, Any]],
    reference_rooms: List[Dict[str, Any]],
    dimension: str,
    strategy_name: str,
    strategy_rationale: str,
    target_smart_m2: Dict[str, Any] = None,
) -> str:
    """Build a prompt that forces Chain-of-Thought via Specification Strategy."""
    
    dim_name = DIMENSION_NAMES[dimension]
    
    def format_rooms_for_dimension(rooms: List[Dict], dim: str, smart_m2: Dict = None) -> str:
        """Extract dimension data from all rooms."""
        lines = []
        for room in rooms:
            room_id = room.get("room_id", "unknown")
            room_name = room.get("room_name", room_id)
            
            # Add smart m² if available
            m2_info = ""
            if smart_m2:
                for m2_room in smart_m2.get("rooms", []):
                    if m2_room.get("room_id") == room_id or m2_room.get("room_name") == room_name:
                        m2_info = f" (~{m2_room.get('estimated_m2', '?')}m²)"
                        break
            
            lines.append(f"[{room_name}]{m2_info} (room_id: {room_id})")
            
            dim_data = room.get("dimensions", {}).get(dim, {})
            if dim_data:
                narrative = dim_data.get("narrative", "")
                if narrative:
                    lines.append(f"  {narrative}")
                for key, value in dim_data.items():
                    if key != "narrative" and value:
                        if isinstance(value, dict):
                            for k, v in value.items():
                                if v:
                                    lines.append(f"  • {k}: {v}")
                        elif isinstance(value, list) and value:
                            lines.append(f"  • {key}: {', '.join(str(v) for v in value)}")
                        elif not isinstance(value, (dict, list)):
                            lines.append(f"  • {key}: {value}")
            else:
                lines.append("  (no data)")
            lines.append("")
        
        return "\n".join(lines)
    
    target_section = format_rooms_for_dimension(target_rooms, dimension, target_smart_m2)
    reference_section = format_rooms_for_dimension(reference_rooms, dimension)
    
    # Get knowledge context (energy, design, process knowledge bases)
    knowledge_context = _get_knowledge_context()
    
    # Collect target room IDs for the output requirement
    target_room_list = ", ".join([r.get("room_id", "unknown") for r in target_rooms])
    
    return f"""
You are a senior quantity surveyor helping a buyer understand what renovation 
work is needed to transform their property.

═══════════════════════════════════════════════════════════════════════════════
THE SPECIFICATION STRATEGY APPROACH
═══════════════════════════════════════════════════════════════════════════════

WHY THIS MATTERS: We've found that when renovation scopes are created, there's 
a tendency for "contextual drift" — the AI sees a wood floor but doesn't 
explicitly decide if it's cheap laminate or expensive parquet before picking 
costs. This leads to expensive comparables resulting in cheap renovation costs.

To fix this, YOU MUST write a Specification Strategy (an "Architect's Directive") 
for EACH ROOM before listing cost items. This forces you to COMMIT to a quality 
level, finish grade, and aesthetic character before you think about individual 
line items.

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════════════════════

Analyze the gap between TARGET and REFERENCE for the dimension: {dim_name}

For EVERY room in the target property ({target_room_list}), you must produce:

1. SPECIFICATION STRATEGY (The Architect's Directive):
   Write a directive paragraph as if you are the Lead Architect instructing a 
   contractor. Describe:
   - The finish grade (budget, mid-range, premium, luxury)
   - The installation style and method
   - The aesthetic goal and character
   - Specific material choices with adjectives (e.g., "warm matte-lacquered 
     wide-plank engineered oak" not just "oak flooring")
   
   Use descriptive language: "To achieve the Scandinavian warmth of the 
   comparable, we must replace the worn linoleum with wide-plank light oak 
   engineered flooring (220mm+ planks) in a running bond pattern, finished 
   with a matte lacquer that will soften the room's hard edges."

2. COST COMPONENTS (Discrete Items):
   Based STRICTLY on your Specification Strategy above, list the specific 
   physical line items. Each flows from your specification — not invented 
   separately. If your specification says "wide-plank oak with matte lacquer," 
   your cost items are "remove existing flooring," "self-leveling compound," 
   "supply & install engineered oak flooring," "supply & install skirting."

═══════════════════════════════════════════════════════════════════════════════
HARD RULE: Every room gets a scope
═══════════════════════════════════════════════════════════════════════════════

Even if a room looks good, there is ALWAYS baseline work when people move in:
- Fresh paint to unify after other trades have been through
- Deep cleaning and prep for handover
- Touch-ups on surfaces scuffed during work
- Minor repairs that become visible when furniture moves

Include these baseline items. A property renovation always includes that final 
polish across every room. If the target already matches the reference, your 
specification might be "Maintain and refresh the existing quality with deep 
cleaning, surface touch-ups, and a fresh coat of paint to the same finish."

═══════════════════════════════════════════════════════════════════════════════
THE REFERENCE: {strategy_name.upper()}
═══════════════════════════════════════════════════════════════════════════════

{strategy_rationale}

This comparable sold successfully at a validated market price. Your scope should 
get the target to this standard — not below it, not unnecessarily above it.

═══════════════════════════════════════════════════════════════════════════════
TARGET PROPERTY — What the buyer has now
═══════════════════════════════════════════════════════════════════════════════

{target_section}

═══════════════════════════════════════════════════════════════════════════════
REFERENCE PROPERTY — The benchmark (what sold successfully)
═══════════════════════════════════════════════════════════════════════════════

{reference_section}

{knowledge_context}

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

For a room where the target has cheap linoleum and the comparable has wide-plank oak:

SPECIFICATION STRATEGY:
"To achieve the Scandinavian aesthetic of the comparable, the existing linoleum 
must be removed entirely. We specify a high-grade engineered oak floor 
(wide-plank, approximately 220mm width) with a matte lacquer finish that softens 
the light. Installation should run parallel to the main window to maximize 
natural light reflection. Standard skirting will be replaced with tall (120mm) 
square-edged white MDF skirting to frame the floor with a clean, contemporary line."

COST COMPONENTS:
- [demolition] Remove flexible floor covering: Carefully lift and dispose of 
  existing linoleum including adhesive residue
- [preparation] Floor leveling: Apply self-leveling compound to correct minor 
  undulations (average 3mm thickness)
- [supply_install] Engineered oak flooring: Premium grade wide-plank engineered 
  oak, 220mm width, matte lacquered, with acoustic underlay
- [supply_install] Skirting: White primed MDF skirting, 120mm height, square 
  profile, including adhesive fixing and corner miters

═══════════════════════════════════════════════════════════════════════════════

Generate output for ALL rooms in the target: {target_room_list}
"""


# =============================================================================
# SCOPE REVIEW PROMPT
# =============================================================================

def _build_scope_review_prompt(
    target_rooms: List[Dict[str, Any]],
    dimension_deltas: Dict[str, Dict[str, Any]],
    strategy_name: str,
    target_smart_m2: Dict[str, Any] = None,
) -> str:
    """Build prompt for scope review and gap-fill."""
    
    # Compile existing scope into readable format
    scope_summary = []
    for dim, delta in dimension_deltas.items():
        scope_summary.append(f"\n{'='*60}")
        scope_summary.append(f"DIMENSION: {DIMENSION_NAMES.get(dim, dim)}")
        scope_summary.append(f"{'='*60}")
        scope_summary.append(delta.get("dimension_summary", ""))
        
        for room_scope in delta.get("room_scopes", []):
            scope_summary.append(f"\n[{room_scope.get('room_name', room_scope.get('room_id'))}]")
            scope_summary.append(f"Specification: {room_scope.get('specification_strategy', 'N/A')}")
            scope_summary.append("Items:")
            for item in room_scope.get("cost_components", []):
                scope_summary.append(f"  • [{item.get('action')}] {item.get('element')}: {item.get('description')}")
    
    scope_text = "\n".join(scope_summary)
    
    target_room_list = ", ".join([r.get("room_id", "unknown") for r in target_rooms])
    
    # Get knowledge context for regulatory/process awareness
    knowledge_context = _get_knowledge_context()
    
    return f"""
You are a senior project manager reviewing a renovation scope before it goes 
to the Bill of Quantities team.

═══════════════════════════════════════════════════════════════════════════════
YOUR ROLE: SCOPE REVIEW & GAP-FILL
═══════════════════════════════════════════════════════════════════════════════

A scope has been generated across 6 dimensions for a property renovation 
(strategy: {strategy_name}). Your job is to review it holistically and identify:

1. GAPS — Items that were likely missed because each dimension was analyzed 
   separately. Common examples:
   - If walls are replastered, was painting included?
   - If bathrooms are retiled, were tanking/waterproofing mentioned?
   - If electrics are upgraded, were the walls made good afterwards?

2. MOVE-IN READINESS — Baseline items every renovation needs that might have 
   been overlooked because they're "obvious":
   - Deep clean throughout (professional end-of-build clean)
   - Final touch-ups after all trades have finished
   - Door adjustments if new flooring changes heights
   - Silicone sealing in wet areas
   - Protective coatings on new surfaces where appropriate
   - Window cleaning inside and out
   - Testing and commissioning of new systems

3. CROSS-DIMENSION CONSISTENCY — Make sure the quality level is consistent:
   - If kitchen is premium, are the kitchen electrics premium?
   - If flooring is high-end, is the skirting appropriate?
   - If bathroom fittings are modern, are the accessories (towel rails, 
     toilet roll holders) included?

4. SEQUENCE DEPENDENCIES — Items that must exist because of other items:
   - If ceilings are lowered for spotlights, was the plasterboard included?
   - If radiators are moved, was pipework rerouting included?
   - If layout changes, were partition walls specified?

═══════════════════════════════════════════════════════════════════════════════
THE EXISTING SCOPE
═══════════════════════════════════════════════════════════════════════════════

Rooms in property: {target_room_list}

{scope_text}

{knowledge_context}

═══════════════════════════════════════════════════════════════════════════════
WHAT TO OUTPUT
═══════════════════════════════════════════════════════════════════════════════

1. A review_summary explaining what gaps you found and what baseline items 
   were missing.

2. Amendments — specific items to ADD or MODIFY. For each:
   - Which room_id it applies to
   - Which dimension it belongs to (shell_preparation, apertures_enclosure, 
     systems_services, surface_finishes, fixed_joinery_equipment, details_fittings)
   - Why it was missed (the reason)
   - A specification_note (Architect's Directive for this item)
   - The cost_component details

Focus on items that are GENUINELY MISSING or INCOMPLETE. Don't add things 
just to add them — but DO catch the "obvious" items that people forget because 
they're taken for granted.

Remember: A buyer is moving into this property after renovation. What would 
they expect to be done that might not have been explicitly captured?
"""


# =============================================================================
# DIMENSION PROCESSOR
# =============================================================================

async def _generate_dimension_delta(
    target_rooms: List[Dict[str, Any]],
    reference_rooms: List[Dict[str, Any]],
    dimension: str,
    strategy_name: str,
    strategy_rationale: str,
    target_smart_m2: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Generate delta scope for one dimension with Specification Strategy."""
    
    prompt = _build_dimension_prompt(
        target_rooms=target_rooms,
        reference_rooms=reference_rooms,
        dimension=dimension,
        strategy_name=strategy_name,
        strategy_rationale=strategy_rationale,
        target_smart_m2=target_smart_m2,
    )
    
    response = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.4,
        response_schema=DIMENSION_DELTA_SCHEMA,
        use_spanish=False,
    )
    
    if not response.success:
        raise RuntimeError(f"Delta scope failed for {dimension}: {response.error}")
    
    result = json.loads(response.text)
    result["dimension"] = dimension
    return result


async def _review_and_fill_gaps(
    target_rooms: List[Dict[str, Any]],
    dimension_deltas: Dict[str, Dict[str, Any]],
    strategy_name: str,
    target_smart_m2: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Review scope holistically and fill gaps."""
    
    prompt = _build_scope_review_prompt(
        target_rooms=target_rooms,
        dimension_deltas=dimension_deltas,
        strategy_name=strategy_name,
        target_smart_m2=target_smart_m2,
    )
    
    response = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.3,
        response_schema=SCOPE_REVIEW_SCHEMA,
        use_spanish=False,
    )
    
    if not response.success:
        raise RuntimeError(f"Scope review failed for {strategy_name}: {response.error}")
    
    return json.loads(response.text)


def _apply_amendments(
    dimension_deltas: Dict[str, Dict[str, Any]],
    amendments: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Apply amendments to dimension deltas."""
    
    for amendment in amendments:
        dim = amendment.get("dimension")
        room_id = amendment.get("room_id")
        
        if dim not in dimension_deltas:
            continue
        
        # Find or create room scope
        room_scopes = dimension_deltas[dim].get("room_scopes", [])
        room_scope = None
        for rs in room_scopes:
            if rs.get("room_id") == room_id:
                room_scope = rs
                break
        
        if not room_scope:
            room_scope = {
                "room_id": room_id,
                "room_name": room_id,
                "specification_strategy": amendment.get("specification_note", ""),
                "cost_components": []
            }
            room_scopes.append(room_scope)
        
        # Add or modify
        if amendment.get("amendment_type") == "add_item":
            component = amendment.get("cost_component", {})
            room_scope["cost_components"].append(component)
            
            # Update specification if provided
            if amendment.get("specification_note"):
                existing = room_scope.get("specification_strategy", "")
                room_scope["specification_strategy"] = f"{existing} [ADDED: {amendment.get('specification_note')}]"
    
    return dimension_deltas


# =============================================================================
# STRATEGY WORKER
# =============================================================================

async def _generate_delta_scopes_for_strategy(
    target_pir: Dict[str, Any],
    reference_pir: Dict[str, Any],
    strategy: Dict[str, Any],
    target_smart_m2: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Generate all delta scopes for ONE strategy (6 dimensions + review)."""
    
    strategy_name = strategy.get("strategy_name", "unknown")
    strategy_rationale = strategy.get("rationale", "")
    
    logger.info(f"      [{strategy_name}] Starting...")
    
    target_rooms = target_pir.get("rooms", [])
    reference_rooms = reference_pir.get("rooms", [])
    
    if not target_rooms:
        raise ValueError("Target PIR has no rooms")
    
    logger.info(f"      [{strategy_name}] Target: {len(target_rooms)} rooms, Reference: {len(reference_rooms)} rooms")
    
    dimension_deltas = {}
    total_items = 0
    
    # Phase 1: Generate dimension deltas (6 calls, PARALLEL)
    logger.info(f"        [{strategy_name}] All 6 dimensions in parallel...")
        
    async def generate_dim(dimension: str) -> tuple:
        delta = await _generate_dimension_delta(
            target_rooms=target_rooms,
            reference_rooms=reference_rooms,
            dimension=dimension,
            strategy_name=strategy_name,
            strategy_rationale=strategy_rationale,
            target_smart_m2=target_smart_m2,
        )
        items = sum(len(rs.get("cost_components", [])) for rs in delta.get("room_scopes", []))
        return dimension, delta, items
    
    dim_results = await asyncio.gather(*[generate_dim(dim) for dim in V2_DIMENSIONS])
        
    for dimension, delta, items in dim_results:
        dimension_deltas[dimension] = delta
        total_items += items
        logger.info(f"          [{strategy_name}] {DIMENSION_NAMES[dimension]}: {items} items")
    
    # Phase 2: Review and fill gaps (1 call)
    logger.info(f"        [{strategy_name}] Scope Review & Gap-Fill...")
    
    review = await _review_and_fill_gaps(
        target_rooms=target_rooms,
        dimension_deltas=dimension_deltas,
        strategy_name=strategy_name,
        target_smart_m2=target_smart_m2,
    )
    
    amendments = review.get("amendments", [])
    logger.info(f"          → {len(amendments)} amendments identified")
    
    # Apply amendments
    if amendments:
        dimension_deltas = _apply_amendments(dimension_deltas, amendments)
        amendment_items = len(amendments)
        total_items += amendment_items
        logger.info(f"          → Applied {amendment_items} amendments")
    
    logger.info(f"      [{strategy_name}] Complete: {total_items} total scope items (including amendments)")
    
    return {
        "strategy_name": strategy_name,
        "reference_comparable_id": strategy.get("reference_comparable_id"),
        "rationale": strategy_rationale,
        "dimension_deltas": dimension_deltas,
        "scope_review": review,
        "total_scope_items": total_items,
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def generate_delta_scopes(
    target_pir: Dict[str, Any],
    comparable_pirs: Dict[int, Dict[str, Any]],
    strategies: List[Dict[str, Any]],
    target_smart_m2: Dict[str, Any] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate delta scopes for all strategies IN PARALLEL.
    
    Each strategy:
    - 6 dimension calls (sequential) with Specification Strategy
    - 1 scope review call to fill gaps
    
    Args:
        target_pir: Target property's PIR
        comparable_pirs: Dict mapping comparable_id -> PIR
        strategies: List of strategy dicts with reference_comparable_id
        target_smart_m2: Optional smart m² data for quantity estimation
    
    Returns:
        Dict mapping strategy_name -> delta_scope_package
    """
    logger.info("=" * 70)
    logger.info("  V2 DELTA SCOPE GENERATION (with Specification Strategy)")
    logger.info("=" * 70)
    logger.info(f"  Target: {len(target_pir.get('rooms', []))} rooms")
    logger.info(f"  Strategies: {[s.get('strategy_name') for s in strategies]}")
    logger.info(f"  Smart m²: {'yes' if target_smart_m2 else 'no'}")
    logger.info("")
    logger.info("  Pattern: 3 strategies parallel × (6 dimensions + 1 review) = 21 calls")
    logger.info("")
    
    async def process_strategy(strategy: Dict[str, Any]) -> tuple:
        strategy_name = strategy.get("strategy_name", "unknown")
        ref_id = strategy.get("reference_comparable_id")
        
        reference_pir = comparable_pirs.get(ref_id)
        if not reference_pir:
            raise ValueError(f"No PIR for reference comparable {ref_id}")
        
        result = await _generate_delta_scopes_for_strategy(
            target_pir=target_pir,
            reference_pir=reference_pir,
            strategy=strategy,
            target_smart_m2=target_smart_m2,
        )
        return strategy_name, result
    
    logger.info("  Starting parallel processing...")
    
    tasks = [process_strategy(s) for s in strategies]
    results = await asyncio.gather(*tasks)
    
    delta_scopes = {name: result for name, result in results}
    
    logger.info("")
    logger.info("  COMPLETE")
    for name, result in delta_scopes.items():
        logger.info(f"    {name}: {result.get('total_scope_items', 0)} scope items")
    logger.info("=" * 70)
    
    return delta_scopes
