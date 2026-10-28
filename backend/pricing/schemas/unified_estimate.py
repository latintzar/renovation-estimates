"""
Unified Estimate Schema (V0.4.8)
================================

THE CONTRACT between:
- Gemini (produces this structure)
- Backend (validates with Pydantic)
- Frontend (consumes via TypeScript types)

EVERY FIELD HAS A UI DESTINATION. No field exists without a consumer.

Naming Convention:
- snake_case for Python (this file)
- camelCase for TypeScript/frontend (generated)
- Field descriptions explain UI destination
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =============================================================================
# GAP ANALYSIS MODELS
# =============================================================================
# These capture the COMPARISON between target property and comparables.
# UI DESTINATION: "Transformación" section in modal

class GapComparison(BaseModel):
    """
    A single attribute-level comparison between target and comparable.
    
    UI DESTINATION: Not shown directly, but informs "Transformación" summary.
    EXAMPLE: 
        attribute="bathroom_finish", 
        target_value="1970s ceramic, yellowed", 
        comparable_value="Walk-in spa, frameless glass"
    """
    attribute: str = Field(
        description="What is being compared. Examples: 'bathroom_finish', 'kitchen_layout', 'energy_rating', 'floor_material'"
    )
    target_value: str = Field(
        description="Current state in target property (from PIR). Be specific about condition."
    )
    comparable_value: str = Field(
        description="Desired state from comparable (from PIR). This is the goal."
    )
    delta: str = Field(
        description="Human-readable gap description. Example: 'Complete bathroom renovation needed'"
    )


class IdentifiedGap(BaseModel):
    """
    A specific renovation gap that needs to be addressed.
    
    UI DESTINATION: "Qué incluye" bullet points in modal.
    Each gap becomes a user-friendly bullet like "✓ Cocina completa estilo contemporáneo"
    """
    gap_id: str = Field(
        description="Unique identifier. Format: gap_[room]_[what]. Example: gap_bathroom_full_reno"
    )
    description: str = Field(
        description="User-friendly description of what needs to change. "
                    "This exact text may be shown to customers. Write it clearly."
    )
    priority: str = Field(
        description="'high' = essential to match comparable, "
                    "'medium' = recommended, "
                    "'low' = optional enhancement. "
                    "Used to sort and filter in UI."
    )
    source_room: str = Field(
        description="Which room this gap primarily affects. "
                    "CRITICAL: Used for room attribution validation. "
                    "Valid values: bathroom, kitchen, bedroom, living, hallway, exterior, general"
    )


# =============================================================================
# SCOPE MODELS
# =============================================================================
# These capture WHAT WORK will be done, derived from KG traversal.
# UI DESTINATION: Informs the "Desglose por zona" expandable sections

class RequiredTask(BaseModel):
    """
    A task that must be done before/after another task (from KG dependencies).
    
    WHY THIS EXISTS: The KG has REQUIRES and TRIGGERS relationships.
    If you tile a bathroom, you first need to demolish old tiles (REQUIRES)
    and then seal/grout (TRIGGERS). This ensures complete scopes.
    """
    task_id: str = Field(
        description="KG task ID. Must exist in kg_context.yaml. "
                    "Example: TASK_DEMO_TILES, TASK_WATERPROOF"
    )
    reason: str = Field(
        description="Why this task is required. Shown in architect export for traceability. "
                    "Example: 'Cannot install new tiles without removing old ones'"
    )


class Intervention(BaseModel):
    """
    A high-level renovation intervention that may involve multiple tasks.
    
    RELATIONSHIP TO GAPS: Each IdentifiedGap leads to one or more Interventions.
    RELATIONSHIP TO KG: Each Intervention has a primary KG task, plus dependencies.
    
    UI DESTINATION: Not shown directly, but drives the task hierarchy.
    """
    intervention_id: str = Field(
        description="Unique identifier. Format: int_[room]_[action]. "
                    "Example: int_bathroom_retile"
    )
    kg_task_id: str = Field(
        description="Primary KG task ID for this intervention. "
                    "This is the 'root' task from which we traverse dependencies."
    )
    description: str = Field(
        description="What this intervention achieves. "
                    "Example: 'Replace bathroom wall tiles with modern large-format porcelain'"
    )
    required_tasks: List[RequiredTask] = Field(
        default_factory=list,
        description="Tasks from KG's REQUIRES relationship. "
                    "These must be done BEFORE the main task."
    )
    triggered_tasks: List[RequiredTask] = Field(
        default_factory=list,
        description="Tasks from KG's TRIGGERS relationship. "
                    "These are commonly done AFTER the main task."
    )


class RoomScope(BaseModel):
    """
    Defines the scope of work for a single room.
    
    UI DESTINATION: "Desglose por zona" accordion header.
    Each room becomes an expandable section showing its cost.
    
    WHY estimated_m2?
    Room dimensions drive quantity calculations. We estimate from photos + listing data.
    """
    room_id: str = Field(
        description="Unique room identifier. Format: room_[type]_[index]. "
                    "Example: room_bathroom_1, room_kitchen"
    )
    room_type: str = Field(
        description="Standardized room type. "
                    "Valid: bathroom, kitchen, bedroom, living, hallway, exterior, general"
    )
    estimated_m2: float = Field(
        description="Estimated room size in m². Used for quantity calculations. "
                    "Source: photo analysis + listing data + Spanish standard room sizes."
    )
    intervention_ids: List[str] = Field(
        default_factory=list,
        description="Which interventions (from Scope.interventions) apply to this room."
    )


# =============================================================================
# BILL OF QUANTITIES MODELS
# =============================================================================
# These capture EXACTLY WHAT WILL BE CHARGED and WHY.
# UI DESTINATION: Expandable line items in "Desglose por zona"

class BoQLineItem(BaseModel):
    """
    A single line in the Bill of Quantities.
    
    THIS IS THE MONEY LINE. Each BoQLineItem represents a specific charge.
    
    UI DESTINATION (Customer): Shown inside room accordion when expanded.
        Example: "• Alicatado   €4,200"
    
    UI DESTINATION (Architect): Full table with all fields.
        | Código | Descripción | Ud | Cant | PU | Total |
    
    WHY 'reasoning' FIELD?
    Explainable AI. Customers and architects can see WHY this price.
    Also enables debugging when estimates seem wrong.
    """
    line_id: str = Field(
        description="Unique line item ID. Format: boq_[room]_[task]_[index]. "
                    "Example: boq_bathroom_tiles_001"
    )
    room_id: str = Field(
        description="Which room this applies to. Links to RoomScope.room_id. "
                    "CRITICAL: <30% of items should have room_id='general'"
    )
    task_id: str = Field(
        description="KG task ID this line item prices. Must exist in KG."
    )
    task_name: str = Field(
        description="Human-readable task name from KG. "
                    "Example: 'Alicatado de paredes'"
    )
    bcca_code: str = Field(
        description="BCCA item code selected from discover_bcca candidates. "
                    "Example: '09ACE00120'. This is what architects need."
    )
    bcca_description: str = Field(
        description="BCCA item description from discover_bcca result. "
                    "Shown in architect export for verification."
    )
    quantity: float = Field(
        description="Calculated quantity. How this is calculated: "
                    "1. Get room dimensions (from RoomScope) "
                    "2. Apply formula from KG quantity_guidance "
                    "3. Example: wall_m2 = perimeter_m * height (2.5m)"
    )
    unit: str = Field(
        description="Unit of measurement from BCCA. "
                    "Common: m2 (area), ml (linear), ud (unit), m3 (volume)"
    )
    unit_price: float = Field(
        description="Price per unit from BCCA (2024 rates). "
                    "NEVER INVENT. Must come from discover_bcca candidate you selected."
    )
    total: float = Field(
        description="quantity × unit_price. Simple multiplication, no rounding."
    )
    reasoning: str = Field(
        description="EXPLAINABLE AI: Why this BCCA item? Why this quantity? "
                    "Example: 'Bathroom wall tiles: 12m² perimeter × 2.5m height = 30m² wall. "
                    "Selected 09ACE00120 (porcelain 60x30) as closest match to comparable finish. "
                    "30m² × €42.80/m² = €1,284'"
    )


class RoomTotal(BaseModel):
    """
    Aggregated cost for one room.
    
    UI DESTINATION: "Desglose por zona" accordion header shows this total.
        Example: "Baño          €14,200  ▼"
    
    WHY SEPARATE FROM LINE ITEMS?
    Pre-computed totals = instant UI rendering without client-side summing.
    """
    room_id: str = Field(description="Links to RoomScope.room_id")
    room_type: str = Field(description="Human-readable room type for UI display")
    total: float = Field(description="Sum of all BoQLineItem.total for this room")


# =============================================================================
# REASONING AND VALIDATION MODELS
# =============================================================================
# These capture HOW the estimate was built and whether it's trustworthy.
# UI DESTINATION: Architect export (reasoning), internal QA (validation)

class ReasoningStep(BaseModel):
    """
    A single step in the LLM's reasoning chain.
    
    WHY THIS EXISTS:
    1. DEBUGGING: When estimates are wrong, we can see WHERE it went wrong
    2. TRUST: Customers can verify the logic (if desired)
    3. AUDIT: Regulatory compliance may require showing work
    
    UI DESTINATION: Architect export "Annex C: Reasoning Chain"
    """
    step_number: int = Field(description="Sequential step number (1, 2, 3...)")
    action: str = Field(
        description="What was done. Valid actions: "
                    "'COMPARE' (target vs comparable), "
                    "'IDENTIFY' (gap found), "
                    "'TRAVERSE' (KG navigation), "
                    "'SEARCH' (BCCA query), "
                    "'SELECT' (chose BCCA item), "
                    "'CALCULATE' (quantity computation)"
    )
    evidence: str = Field(
        description="What was observed or found. "
                    "Example: 'Target bathroom has 1970s tiles (15x15), comparable has 60x30 porcelain'"
    )
    conclusion: str = Field(
        description="What was decided based on evidence. "
                    "Example: 'Gap identified: bathroom_tiles. Intervention: full retile with porcelain'"
    )


class ValidationMetrics(BaseModel):
    """
    Quality metrics for the estimate. Used for fail-fast validation.
    
    WHY THESE METRICS?
    These are the THREE indicators of a good estimate:
    1. room_attribution: Is work assigned to specific rooms (not dumped in 'general')?
    2. kg_grounding: Are all tasks from our Knowledge Graph (not invented)?
    3. bcca_match: Do all prices come from BCCA (not hallucinated)?
    
    THRESHOLDS (fail if not met):
    - room_attribution_pct >= 70 (less than 30% in 'general')
    - kg_grounding_pct == 100 (all tasks from KG)
    - bcca_match_pct == 100 (all prices from BCCA)
    
    UI DESTINATION: Internal QA dashboard (not shown to customer)
    """
    room_attribution_pct: float = Field(
        description="% of costs with specific room (not 'general'). Target: ≥70%"
    )
    kg_grounding_pct: float = Field(
        description="% of tasks that exist in Knowledge Graph. Target: 100%"
    )
    bcca_match_pct: float = Field(
        description="% of tasks with valid BCCA code (selected from discover_bcca). Target: 100%"
    )
    total_line_items: int = Field(description="Total number of BoQ line items")
    total_rooms: int = Field(description="Number of rooms in scope")


# =============================================================================
# YEAR CONTEXT MODELS (V0.4.8)
# =============================================================================

class InspectionRecommendation(BaseModel):
    """
    Recommendation for professional inspection based on year-implied possibilities.
    
    UI DESTINATION: "Próximos pasos" section
    """
    system: str = Field(
        description="System to inspect. Valid: 'electrical', 'plumbing', 'structure', 'hvac'"
    )
    reason: str = Field(
        description="Why inspection is recommended. "
                    "Example: 'Pre-2002 electrical possible, panel not visible'"
    )
    urgency: str = Field(
        description="When to inspect. Valid: 'before_purchase', 'before_renovation', 'during_renovation'"
    )
    professional_type: str = Field(
        description="Who should inspect. "
                    "Example: 'electricista autorizado', 'fontanero', 'arquitecto técnico'"
    )
    estimated_cost_range: str = Field(
        description="Cost of inspection (not repair). Example: '€100-200'"
    )


class YearContextSummary(BaseModel):
    """
    Summary of how construction year influenced the estimate.
    
    UI DESTINATION: "Contexto del edificio" card
    """
    target_year: int = Field(
        description="Construction year of target property"
    )
    target_year_source: str = Field(
        description="How year was determined. Valid: 'cadastre', 'listing', 'estimate'"
    )
    comparable_years: List[int] = Field(
        description="Construction years of comparable properties"
    )
    confirmed_issues: List[str] = Field(
        description="Issues confirmed by visual evidence. "
                    "Example: ['Pre-REBT electrical panel visible', 'Lead pipes visible']"
    )
    possible_issues: List[str] = Field(
        description="Issues possible but not visually confirmed. "
                    "Example: ['May have unearthed wiring (pre-1973)', 'Possible asbestos (1950-1980)']"
    )
    ruled_out: List[str] = Field(
        description="Issues ruled out by visual evidence. "
                    "Example: ['Modern circuit breakers visible - electrical likely upgraded']"
    )
    comparables_insight: str = Field(
        description="What comparable years tell us. "
                    "Example: '1970 comparables likely already upgraded electrical, plumbing'"
    )


class Disclaimer(BaseModel):
    """
    Legal/professional disclaimer for the estimate.
    
    UI DESTINATION: Footer of estimate page
    """
    scope_basis: str = Field(
        description="What the estimate is based on. "
                    "Example: 'Based on VISIBLE changes to match comparables'"
    )
    hidden_systems: str = Field(
        description="Warning about hidden systems. "
                    "Example: 'Hidden systems (electrical, plumbing) may require inspection'"
    )
    year_context_note: str = Field(
        description="Note about year-based assumptions. "
                    "Example: 'Construction year (1975) suggests pre-REBT electrical...'"
    )
    pricing_basis: str = Field(
        description="Source of prices. Example: 'Prices from BCCA 2024 Andalucía base'"
    )
    regional_note: Optional[str] = Field(
        default=None,
        description="Regional adjustment note if applicable. "
                    "Example: 'Adjusted +15% for Madrid market'"
    )
    professional_advice: str = Field(
        description="Recommendation to consult professionals. "
                    "Example: 'We recommend inspection before purchase for items marked...'"
    )


# =============================================================================
# TOP-LEVEL AGGREGATION MODELS
# =============================================================================

class GapAnalysis(BaseModel):
    """
    Container for all gap-related data.
    
    UI DESTINATION: "Transformación" summary + "Qué incluye" bullets
    """
    comparisons: List[GapComparison] = Field(
        description="All attribute-level comparisons between target and comparable"
    )
    identified_gaps: List[IdentifiedGap] = Field(
        description="All gaps that need renovation work. "
                    "Each gap → interventions → tasks → BoQ line items"
    )


class Scope(BaseModel):
    """
    Container for all scope-related data.
    
    UI DESTINATION: Drives "Desglose por zona" structure
    """
    rooms: List[RoomScope] = Field(
        description="All rooms in scope with their interventions"
    )
    interventions: List[Intervention] = Field(
        description="All interventions (high-level work items) with KG dependencies"
    )


class BillOfQuantities(BaseModel):
    """
    Container for all pricing data.
    
    UI DESTINATION: "Desglose por zona" line items + totals
    """
    line_items: List[BoQLineItem] = Field(
        description="Every priced item. This is the core of the estimate."
    )
    room_totals: List[RoomTotal] = Field(
        description="Pre-computed room subtotals for instant UI display"
    )
    grand_total: float = Field(
        description="Sum of all room_totals. "
                    "This is PEM (Presupuesto Ejecución Material) only. "
                    "UI adds: + GG (13%) + BI (6%) + IVA (10/21%)"
    )


# =============================================================================
# THE MAIN SCHEMA
# =============================================================================

class UnifiedEstimate(BaseModel):
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                        UNIFIED ESTIMATE SCHEMA                             ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  This is THE CONTRACT between:                                            ║
    ║  - Gemini (produces this structure)                                       ║
    ║  - Backend (validates with Pydantic)                                      ║
    ║  - Frontend (consumes via TypeScript types)                               ║
    ║                                                                           ║
    ║  EVERY FIELD HAS A UI DESTINATION. No field exists without a consumer.    ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    
    DATA FLOW:
    
        PIRs (target + comparables)
              │
              ▼
        ┌─────────────────────┐
        │  UNIFIED ESTIMATOR  │ ← KG + BCCA tool + System Instruction
        │  (9-Phase Pipeline) │
        └─────────────────────┘
              │
              ▼
        UnifiedEstimate (this schema)
              │
              ├──────────────────────────────────┐
              │                                  │
              ▼                                  ▼
        format_customer_view()           format_architect_view()
              │                                  │
              ▼                                  ▼
        Mobile Modal UI                  PDF/JSON Export
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # CORE CONTENT
    # ═══════════════════════════════════════════════════════════════════
    
    gap_analysis: GapAnalysis = Field(
        description="WHAT NEEDS TO CHANGE: Comparisons and identified gaps. "
                    "UI: 'Transformación' section + 'Qué incluye' bullets"
    )
    
    scope: Scope = Field(
        description="WHAT WORK WILL BE DONE: Rooms and interventions with KG dependencies. "
                    "UI: Drives 'Desglose por zona' structure"
    )
    
    bill_of_quantities: BillOfQuantities = Field(
        description="HOW MUCH IT COSTS: Every line item with BCCA pricing. "
                    "UI: Line items in room accordions + grand total"
    )
    
    reasoning_chain: List[ReasoningStep] = Field(
        description="HOW WE GOT HERE: Step-by-step reasoning for explainability. "
                    "UI: Architect export 'Annex C'"
    )
    
    validation: ValidationMetrics = Field(
        description="IS IT TRUSTWORTHY: Quality metrics for fail-fast validation. "
                    "UI: Internal QA only (not shown to customer)"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # YEAR-CONTEXT INFORMED OUTPUTS (V0.4.8)
    # ═══════════════════════════════════════════════════════════════════
    
    inspection_recommendations: List[InspectionRecommendation] = Field(
        description="Systems where professional inspection is recommended "
                    "based on year-implied possibilities. UI: 'Próximos pasos' section"
    )
    
    year_context_summary: YearContextSummary = Field(
        description="Summary of how construction year influenced the estimate. "
                    "UI: 'Contexto del edificio' card"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # PROFESSIONAL DISCLAIMER (V0.4.8)
    # ═══════════════════════════════════════════════════════════════════
    
    disclaimer: Disclaimer = Field(
        description="Legal/professional disclaimer for the estimate. "
                    "UI: Footer of estimate page"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════
    
    target_listing_id: int = Field(
        description="ID of the property being estimated"
    )
    comparable_listing_ids: List[int] = Field(
        description="IDs of comparable properties used for gap analysis"
    )
    package_type: str = Field(
        description="Type of package. Valid: 'fast_sell', 'fair_market', 'out_of_market'"
    )
    estimation_date: str = Field(
        description="When this estimate was generated (ISO format)"
    )
    model_version: str = Field(
        default="V0.4.8",
        description="Version of the estimator that produced this"
    )

