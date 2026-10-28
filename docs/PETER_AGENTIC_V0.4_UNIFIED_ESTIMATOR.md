Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.4.8: 9-Phase Orchestrator with Cached Context

> **Date**: January 11, 2026  
> **Status**: 📋 IMPLEMENTATION GUIDE - Ready for development  
> **Philosophy**: 9 deliberate phases, same cached context, no Pareto-ing  
> **Model Strategy**: Pro for generation (5 phases), Flash for verification (4 phases)

### Key Changes in V0.4.8 (9-Phase Orchestrator)

| What | Why |
|------|-----|
| **9 PHASES** | Each phase has ONE job, verified by next phase. Can't skip anything. |
| **CACHED CONTEXT** | Same ~700K tokens reused 9 times. 60% cheaper than naive approach. |
| **PRO + FLASH MIX** | Pro for creative work, Flash for verification. Optimal cost/quality. |
| **NO PARETO-ING** | Check phases ADD items but never remove. Completeness guaranteed. |
| **FULL REASONING** | Every phase output preserved. See exactly how estimate was built. |

### The 9 Phases (Quick Reference)

| # | Phase | Model | Purpose |
|---|-------|-------|---------|
| 1 | Scope Definition | Pro | What needs to change? Room-by-room. |
| 2 | Scope Check | Flash | What's missing? ADD items. |
| 3 | Work Phases | Pro | Fan out: labor, logistics, timeline |
| 4 | BOQ Check | Flash | Sequencing OK? ADD items. |
| 5 | Pricing Strategy | Pro | Match to BCCA/FFE with EXPLAINED adaptation |
| 6 | Adjustments | Pro | Regional, access, market factors |
| 7 | Timeline Check | Flash | Physical constraints respected? |
| 8 | Energy Check | Flash | Will we hit target CEE? |
| 9 | Final Sanity | Pro | Does this make sense? Package output. |

### Cost per Estimate (with caching)
```
Pro (5 calls):  $1.40 + 4×$0.14 = $1.96 input
Flash (4 calls): 4×$0.035 = $0.14 input  
Output: ~$2.00
───────────────────────────────────
TOTAL: ~$4.10 per complete estimate
```

---

## Table of Contents

0. [**Part 0: 9-Phase Orchestrator (V0.4.8)**](#part-0-9-phase-orchestrator-with-cached-context) ⭐ **NEW - THE ARCHITECTURE**
1. [The Core Insight](#the-core-insight)
2. [Architecture Overview](#architecture-overview)
3. [Part 1: System Instruction Template](#part-1-system-instruction-template)
4. [Part 2: get_bcca_price Tool (Price Lookup)](#part-2-get_bcca_price-tool-implementation)
5. [Part 2B: discover_ffe Tool (FF&E)](#part-2b-discover_ffe-tool-implementation-ffe-pricing)
6. [Part 2C: BCCA Index Generation](#part-2c-bcca-index-generation-v047---new)
7. [Part 3: Response Schema (UnifiedEstimate)](#part-3-response-schema-unifiedestimate)
8. [Part 4: Unified Estimator Implementation](#part-4-unified-estimator-implementation)
9. [Part 5: View Formatters](#part-5-view-formatters)
10. [Part 6: Token Budget](#part-6-token-budget)
11. [Part 7: Implementation Checklist](#part-7-implementation-checklist)
12. [Part 8: PIR Schema Reference](#part-8-propertyintelligencereport-pir-schema)
13. [Part 9: Energy Task Enrichment](#part-9-energy-task-enrichment-from-v031)
14. [Part 10: Preserved Decisions](#part-10-preserved-decisions-from-audit)
15. [Part 11: Structured Error Response](#part-11-structured-error-response)
16. [Part 12: UI Specification (Mobile-First)](#part-12-ui-specification-mobile-first)
17. [Part 13: Complete System Summary](#part-13-complete-system-summary)

---

## Part 0: 9-Phase Orchestrator with Cached Context

> **V0.4.8 BREAKTHROUGH**: Instead of one massive call that might "Pareto" (do 80%, skip 20%), 
> we use **9 deliberate phases** with the **same cached context**. Each phase builds on the previous.
> Check phases use **Flash** (cheap), generation phases use **Pro** (smart).
> Context caching makes this **80% cheaper** than 9 separate calls.

### Why 9 Phases Instead of 1?

**The Pareto Problem with Single Calls:**
```
One massive call risks:
├── Missing rooms (properties have multiple instances of same room type)
├── Skipping dependencies (demos tile but forgets waterproofing)
├── Fatigue toward end (detailed early, sloppy late)
├── No verification (who checks the checker?)
└── Black box (can't see intermediate reasoning)
```

**The 9-Phase Solution:**
```
Each phase has ONE job → verified by next phase → nothing gets missed
├── GENERATION phases: Creative work (Pro)
├── CHECK phases: Verification (Flash, cheap)
├── Same context: 700K tokens cached, reused 9 times
└── Full transparency: See every decision at every step
```

### The 9 Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CACHED CONTEXT (~700K tokens)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Knowledge Graph (214K)     • BCCA INDEX (444K)                    │   │
│  │ • FFE INDEX (12K)            • Energy/Process/Interior (24K)        │   │
│  │ • Target PIR + Photos        • Comparable PIRs + Photos             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓ CACHED ↓                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  PHASE 1: SCOPE DEFINITION                        [Gemini 3 Pro]      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  "What needs to happen to transform target → comparable standard?"    ║ │
│  ║                                                                       ║ │
│  ║  Tasks:                                                               ║ │
│  ║  • Room-by-room breakdown (bathroom_1, bathroom_2, kitchen...)       ║ │
│  ║  • CONSISTENT items across rooms (same paint, same electrical std)   ║ │
│  ║  • UNIQUE items per room (bath waterproofing, kitchen extraction)    ║ │
│  ║  • Compare target photos to comparable photos                        ║ │
│  ║                                                                       ║ │
│  ║  Output: DRAFT_SCOPE                                                  ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                      ↓                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  PHASE 2: SCOPE COMPLETENESS CHECK              [Gemini 3 Flash] ✓   │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  "Review DRAFT_SCOPE. What's missing? ADD but don't remove."         │ │
│  │                                                                       │ │
│  │  Checks:                                                              │ │
│  │  • Every room from listing covered?                                  │ │
│  │  • Every system per room addressed? (demo, plumb, elec, finish)      │ │
│  │  • Dependencies satisfied? (demo tile → waterproof → new tile)       │ │
│  │  • Consistent items actually applied to ALL relevant rooms?          │ │
│  │  • Minimum items per room type met? (bathroom≥15, kitchen≥20)        │ │
│  │                                                                       │ │
│  │  Output: VERIFIED_SCOPE (DRAFT_SCOPE + additions)                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  PHASE 3: WORK PHASES EXPANSION                   [Gemini 3 Pro]      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  "Fan out VERIFIED_SCOPE into complete BOQ with labor + logistics"   ║ │
│  ║                                                                       ║ │
│  ║  Adds:                                                                ║ │
│  ║  • LABOR breakdown (not just materials - installation hours)         ║ │
│  ║  • TIME per phase (week 1: demo, week 2: rough-in, week 3: finish)  ║ │
│  ║  • SITE MANAGEMENT (scaffolding, skip hire, floor protection)        ║ │
│  ║  • CLEANUP phases (debris removal, mid-project clean, final clean)   ║ │
│  ║  • PERMITS required (structural changes, electrical, plumbing)       ║ │
│  ║  • INSPECTIONS needed (pre-cover, final)                            ║ │
│  ║                                                                       ║ │
│  ║  Output: FULL_BOQ_DRAFT                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                      ↓                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  PHASE 4: BOQ COMPLETENESS CHECK                [Gemini 3 Flash] ✓   │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  "Review FULL_BOQ_DRAFT. What's missing? ADD but don't remove."      │ │
│  │                                                                       │ │
│  │  Checks:                                                              │ │
│  │  • Every scope item has BOTH labor AND materials?                    │ │
│  │  • Site logistics accounted for? (access, storage, waste)            │ │
│  │  • Sequencing makes sense? (can't tile before waterproof cures)      │ │
│  │  • Contingency items included? (discovery allowance, unforeseen)     │ │
│  │  • FF&E items separated from construction?                           │ │
│  │                                                                       │ │
│  │  Output: VERIFIED_BOQ                                                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  PHASE 5: PRICING STRATEGY + DB ADAPTATION        [Gemini 3 Pro]      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  "For each BOQ item, decide HOW to price with EXPLAINED ADAPTATION"  ║ │
│  ║                                                                       ║ │
│  ║  For each item:                                                       ║ │
│  ║  • Find matching BCCA/FFE code from INDEX                            ║ │
│  ║  • ADAPTATION REASONING when not exact match:                        ║ │
│  ║    "Scope: 'large format porcelain 60x60'                            ║ │
│  ║     BCCA: 09ACE00140 'gres porcelánico 45x45' = €45/m²              ║ │
│  ║     ADAPTING: +15% for larger format = €51.75/m²                     ║ │
│  ║     REASONING: Larger tiles = more material waste + harder install"  ║ │
│  ║  • Quantity calculation with FORMULA shown                           ║ │
│  ║  • get_bcca_price() calls for exact prices                          ║ │
│  ║                                                                       ║ │
│  ║  Output: PRICED_BOQ_DRAFT                                            ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                      ↓                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  PHASE 6: PRICING ADJUSTMENTS + REGIONAL FACTORS  [Gemini 3 Pro]      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  "Apply regional, access, and market adjustments with REASONING"     ║ │
│  ║                                                                       ║ │
│  ║  Adjustments (all with explicit reasoning):                          ║ │
│  ║  • REGIONAL MULTIPLIER:                                              ║ │
│  ║    "BCCA base is Andalucía. Property in Madrid → +12% labor"         ║ │
│  ║  • ACCESS FACTORS:                                                    ║ │
│  ║    "No lift, 3rd floor → +8% material handling"                      ║ │
│  ║    "Narrow street, limited parking → +5% delivery logistics"         ║ │
│  ║  • BUILDING TYPE:                                                     ║ │
│  ║    "Heritage listed building → +15% careful demolition"              ║ │
│  ║  • MARKET CONDITIONS:                                                 ║ │
│  ║    "High demand area, Q1 2026 → contractor rates +5%"                ║ │
│  ║                                                                       ║ │
│  ║  Output: ADJUSTED_BOQ                                                ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                      ↓                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  PHASE 7: TIMELINE VALIDATION                   [Gemini 3 Flash] ✓   │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  "Does the timeline make physical sense?"                            │ │
│  │                                                                       │ │
│  │  Checks:                                                              │ │
│  │  • Can't tile before waterproofing cures (48h minimum)               │ │
│  │  • Can't paint before plaster dries (2 weeks for new plaster)        │ │
│  │  • Kitchen appliances arrive AFTER cabinets installed                │ │
│  │  • Electrical rough-in BEFORE drywall close                          │ │
│  │  • Total duration realistic for scope + team size?                   │ │
│  │  • Critical path identified?                                         │ │
│  │                                                                       │ │
│  │  Output: TIMELINE_VERIFIED_BOQ (with schedule adjustments)           │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  PHASE 8: ENERGY COMPLIANCE CHECK               [Gemini 3 Flash] ✓   │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  "Will post-renovation meet energy targets?"                         │ │
│  │                                                                       │ │
│  │  Checks:                                                              │ │
│  │  • Current CEE rating: [from target PIR]                             │ │
│  │  • Target CEE rating: [from comparable PIR]                          │ │
│  │  • Insulation scope sufficient? (walls, roof, floor)                 │ │
│  │  • Window upgrades included? (U-value improvement)                   │ │
│  │  • HVAC efficiency adequate? (heat pump vs old boiler)               │ │
│  │  • Predicted post-renovation CEE: [calculate from interventions]     │ │
│  │  • Gap to target? → Add items if needed                              │ │
│  │                                                                       │ │
│  │  Output: ENERGY_VERIFIED_BOQ                                         │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  PHASE 9: FINAL SANITY CHECK + OUTPUT             [Gemini 3 Pro]      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  "Does this make sense overall? Final packaging."                    ║ │
│  ║                                                                       ║ │
│  ║  Sanity checks:                                                       ║ │
│  ║  • Total cost reasonable for property value? (renovation < 30%?)     ║ │
│  ║  • Cost per m² within market norms? (€800-2000/m² typical)          ║ │
│  ║  • Labor:materials ratio sensible? (typically 40:60 to 50:50)        ║ │
│  ║  • Any obvious gaps or duplications?                                 ║ │
│  ║  • Would YOU renovate this way?                                      ║ │
│  ║                                                                       ║ │
│  ║  Final packaging:                                                     ║ │
│  ║  • Compile UnifiedEstimate schema                                    ║ │
│  ║  • Generate executive summary                                        ║ │
│  ║  • Create room-by-room breakdown                                     ║ │
│  ║  • Produce timeline visualization data                               ║ │
│  ║                                                                       ║ │
│  ║  Output: FINAL_UNIFIED_ESTIMATE                                      ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Model Selection Strategy

| Phase | Type | Model | Why |
|-------|------|-------|-----|
| 1 | Generation | **Gemini 3 Pro** | Creative scope definition needs best reasoning |
| 2 | Check | **Gemini 3 Flash** | Verification is formulaic, Flash is 4x cheaper |
| 3 | Generation | **Gemini 3 Pro** | Work phase expansion needs domain expertise |
| 4 | Check | **Gemini 3 Flash** | BOQ verification is checklist-based |
| 5 | Generation | **Gemini 3 Pro** | Pricing adaptation needs nuanced reasoning |
| 6 | Generation | **Gemini 3 Pro** | Regional adjustments need market knowledge |
| 7 | Check | **Gemini 3 Flash** | Timeline math is formulaic |
| 8 | Check | **Gemini 3 Flash** | Energy calculations are formula-based |
| 9 | Generation | **Gemini 3 Pro** | Final sanity + packaging needs holistic view |

**Summary**: 5× Pro calls, 4× Flash calls

### Cost Analysis with Context Caching

```
CONTEXT SIZE: ~700K tokens = 0.7M tokens

═══════════════════════════════════════════════════════════════════════════════
WITHOUT CACHING (Naive approach - DON'T DO THIS):
═══════════════════════════════════════════════════════════════════════════════

Pro calls (5×):
  Input: 5 × $2/M × 0.7M = $7.00
  Output: 5 × $12/M × 0.03M = $1.80
  
Flash calls (4×):
  Input: 4 × $0.5/M × 0.7M = $1.40
  Output: 4 × $3/M × 0.02M = $0.24

TOTAL WITHOUT CACHING: $10.44 per estimate ❌

═══════════════════════════════════════════════════════════════════════════════
WITH CONTEXT CACHING (THE RIGHT WAY):
═══════════════════════════════════════════════════════════════════════════════

Pro calls:
  First call (cache miss): $2/M × 0.7M = $1.40
  Subsequent 4 calls (cache hit): 4 × $0.2/M × 0.7M = $0.56
  Output: 5 × $12/M × 0.03M = $1.80
  Pro subtotal: $3.76

Flash calls (all cache hits after Pro cached):
  4 calls: 4 × $0.05/M × 0.7M = $0.14
  Output: 4 × $3/M × 0.02M = $0.24
  Flash subtotal: $0.38

TOTAL WITH CACHING: $4.14 per estimate ✓

═══════════════════════════════════════════════════════════════════════════════
SAVINGS: 60% cheaper AND more thorough!
═══════════════════════════════════════════════════════════════════════════════
```

### Phase Output Schemas

```python
# =============================================================================
# pricing/schemas/phase_outputs.py
# =============================================================================

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from enum import Enum

# -----------------------------------------------------------------------------
# PHASE 1 & 2: Scope
# -----------------------------------------------------------------------------

class ScopeItem(BaseModel):
    """Single item in the scope."""
    room_id: str                    # "bathroom_1", "kitchen"
    system: str                     # "demolition", "plumbing", "finishes"
    task: str                       # "demo_wall_tiles", "install_shower"
    kg_task_id: Optional[str]       # Reference to Knowledge Graph
    is_consistent: bool = False     # Same across multiple rooms?
    comparable_reference: str       # What in comparable drives this?

class DraftScope(BaseModel):
    """Output of Phase 1: Scope Definition."""
    rooms_identified: List[str]
    consistent_items: List[ScopeItem]   # Applied to multiple rooms
    unique_items: Dict[str, List[ScopeItem]]  # Per room
    total_items: int
    
class VerifiedScope(BaseModel):
    """Output of Phase 2: Scope Check."""
    original_scope: DraftScope
    items_added: List[ScopeItem]        # What was missing
    verification_notes: List[str]       # "Added waterproofing to bathroom_2"
    rooms_verified: Dict[str, bool]     # Each room checked
    final_item_count: int

# -----------------------------------------------------------------------------
# PHASE 3 & 4: BOQ
# -----------------------------------------------------------------------------

class BOQLineItem(BaseModel):
    """Single line in Bill of Quantities."""
    line_id: str
    room_id: str
    system: str
    task: str
    description: str
    
    # Quantities
    quantity: float
    unit: str
    quantity_formula: str           # "7m perimeter × 2.4m height = 16.8m²"
    
    # Timing
    phase: str                      # "demolition", "rough-in", "finish"
    week: int
    duration_hours: float
    
    # Dependencies
    requires: List[str]             # Line IDs that must complete first
    
    # Classification
    is_labor: bool
    is_material: bool
    is_site_logistics: bool
    
class FullBOQDraft(BaseModel):
    """Output of Phase 3: Work Phases Expansion."""
    line_items: List[BOQLineItem]
    site_setup_items: List[BOQLineItem]     # Scaffolding, protection, etc.
    cleanup_items: List[BOQLineItem]
    permits_required: List[str]
    inspections_required: List[str]
    total_weeks: int
    
class VerifiedBOQ(BaseModel):
    """Output of Phase 4: BOQ Check."""
    original_boq: FullBOQDraft
    items_added: List[BOQLineItem]
    sequencing_fixes: List[str]     # "Moved waterproof before tiles"
    contingency_added: bool
    ff_e_items_separated: List[BOQLineItem]

# -----------------------------------------------------------------------------
# PHASE 5 & 6: Pricing
# -----------------------------------------------------------------------------

class PricingAdaptation(BaseModel):
    """How we adapted scope item to our database."""
    scope_description: str          # What the scope says
    bcca_code: Optional[str]        # What we matched to
    ffe_code: Optional[str]         # Or FF&E code
    exact_match: bool
    adaptation_reasoning: str       # Why this adaptation
    base_price: float
    adaptation_multiplier: float    # 1.0 if exact, 1.15 if +15%, etc.
    final_unit_price: float

class PricedLineItem(BOQLineItem):
    """BOQ line item with pricing."""
    pricing: PricingAdaptation
    line_total: float               # quantity × final_unit_price

class PricedBOQDraft(BaseModel):
    """Output of Phase 5: Pricing Strategy."""
    priced_items: List[PricedLineItem]
    total_before_adjustments: float
    adaptation_summary: str         # "78% exact matches, 22% adapted"

class RegionalAdjustment(BaseModel):
    """Single adjustment applied."""
    adjustment_type: str            # "regional", "access", "market", "building"
    description: str
    multiplier: float
    reasoning: str

class AdjustedBOQ(BaseModel):
    """Output of Phase 6: Pricing Adjustments."""
    priced_items: List[PricedLineItem]
    adjustments_applied: List[RegionalAdjustment]
    total_adjustments_multiplier: float
    total_after_adjustments: float
    adjustment_breakdown: str       # Human-readable summary

# -----------------------------------------------------------------------------
# PHASE 7 & 8: Validation
# -----------------------------------------------------------------------------

class TimelineVerification(BaseModel):
    """Output of Phase 7: Timeline Check."""
    schedule_valid: bool
    issues_found: List[str]
    fixes_applied: List[str]
    critical_path: List[str]        # Line IDs on critical path
    total_duration_weeks: int
    
class EnergyVerification(BaseModel):
    """Output of Phase 8: Energy Check."""
    current_cee: str                # "G"
    target_cee: str                 # "C"
    predicted_cee: str              # "D" (what we'll achieve)
    gap_to_target: bool
    items_added_for_energy: List[BOQLineItem]
    energy_interventions: List[str] # "Added wall insulation", etc.

# -----------------------------------------------------------------------------
# PHASE 9: Final Output
# -----------------------------------------------------------------------------

class SanityCheckResult(BaseModel):
    """Final sanity checks."""
    cost_per_m2: float
    cost_per_m2_reasonable: bool    # Within €800-2000?
    cost_to_value_ratio: float      # Renovation / property value
    ratio_reasonable: bool          # Under 30%?
    labor_material_ratio: str       # "45:55"
    obvious_gaps: List[str]
    duplications_found: List[str]
    overall_confidence: Literal["HIGH", "MEDIUM", "LOW"]

class FinalUnifiedEstimate(BaseModel):
    """Output of Phase 9: The final deliverable."""
    
    # Metadata
    target_property_id: str
    comparable_ids: List[str]
    generated_at: str
    model_versions: Dict[str, str]  # Which models used per phase
    
    # The estimate
    total_cost: float
    cost_breakdown_by_room: Dict[str, float]
    cost_breakdown_by_system: Dict[str, float]
    
    # Full BOQ
    boq_items: List[PricedLineItem]
    ff_e_items: List[PricedLineItem]
    
    # Timeline
    total_weeks: int
    schedule_by_week: Dict[int, List[str]]  # Week → task descriptions
    
    # Adjustments applied
    regional_adjustments: List[RegionalAdjustment]
    
    # Reasoning chain
    scope_reasoning: str
    pricing_adaptations_summary: str
    adjustment_reasoning: str
    
    # Quality metrics
    sanity_check: SanityCheckResult
    energy_verification: EnergyVerification
    
    # Phase outputs (for debugging/transparency)
    phase_outputs: Dict[str, str]   # Phase name → JSON of output
```

### Orchestrator Implementation

```python
# =============================================================================
# pricing/multi_phase_estimator.py
# =============================================================================
"""
9-Phase Estimation Orchestrator with Cached Context

ARCHITECTURE:
- Same ~700K context cached across all 9 phases
- Pro for generation (5 phases), Flash for checks (4 phases)
- Each phase builds on previous phase output
- Check phases can ADD but never REMOVE items
- Full transparency: every phase output is preserved
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .schemas.phase_outputs import *
from .schemas.unified_estimate import UnifiedEstimate
from ..pipeline.gemini_client import get_api_key

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# PHASE DEFINITIONS
# =============================================================================

PHASES = {
    1: {
        "name": "scope_definition",
        "model": "gemini-3-pro-preview",
        "task": "Define complete transformation scope room-by-room",
        "output_schema": DraftScope,
    },
    2: {
        "name": "scope_check",
        "model": "gemini-3-flash-preview",
        "task": "Verify scope completeness, ADD missing items",
        "output_schema": VerifiedScope,
    },
    3: {
        "name": "work_phases",
        "model": "gemini-3-pro-preview",
        "task": "Expand into full BOQ with labor, logistics, timeline",
        "output_schema": FullBOQDraft,
    },
    4: {
        "name": "boq_check",
        "model": "gemini-3-flash-preview",
        "task": "Verify BOQ completeness, ADD missing items",
        "output_schema": VerifiedBOQ,
    },
    5: {
        "name": "pricing_strategy",
        "model": "gemini-3-pro-preview",
        "task": "Price each item with EXPLAINED adaptation to BCCA/FFE",
        "output_schema": PricedBOQDraft,
    },
    6: {
        "name": "pricing_adjustments",
        "model": "gemini-3-pro-preview",
        "task": "Apply regional, access, market adjustments with REASONING",
        "output_schema": AdjustedBOQ,
    },
    7: {
        "name": "timeline_validation",
        "model": "gemini-3-flash-preview",
        "task": "Validate timeline makes physical sense",
        "output_schema": TimelineVerification,
    },
    8: {
        "name": "energy_check",
        "model": "gemini-3-flash-preview",
        "task": "Verify energy improvements meet target",
        "output_schema": EnergyVerification,
    },
    9: {
        "name": "final_sanity",
        "model": "gemini-3-pro-preview",
        "task": "Final sanity check and output packaging",
        "output_schema": FinalUnifiedEstimate,
    },
}


# =============================================================================
# ORCHESTRATOR CLASS
# =============================================================================

class MultiPhaseEstimator:
    """
    Orchestrates 9-phase estimation with cached context.
    
    Usage:
        estimator = MultiPhaseEstimator()
        result = await estimator.estimate(target_pir, comparable_pirs, photos)
    """
    
    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize with cache settings.
        
        Args:
            cache_ttl_seconds: How long to cache context (default 1 hour)
        """
        self.cache_ttl = cache_ttl_seconds
        self.phase_outputs: Dict[int, Any] = {}
        self.cached_context: Optional[str] = None
        self.cache_id: Optional[str] = None
        
        # Configure Gemini
        genai.configure(api_key=get_api_key())
        
    async def estimate(
        self,
        target_pir: Dict,
        comparable_pirs: List[Dict],
        target_photos: List[bytes],
        comparable_photos: List[List[bytes]],
        listing_data: Dict
    ) -> FinalUnifiedEstimate:
        """
        Run full 9-phase estimation.
        
        Args:
            target_pir: PropertyIntelligenceReport for target
            comparable_pirs: List of PIRs for comparables
            target_photos: Photos of target property
            comparable_photos: Photos of each comparable
            listing_data: Basic listing info (price, m2, rooms, location)
        
        Returns:
            FinalUnifiedEstimate with full reasoning chain
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("STARTING 9-PHASE ESTIMATION")
        logger.info("=" * 60)
        
        # Step 1: Build cached context
        logger.info("Building cached context (~700K tokens)...")
        self.cached_context = await self._build_context(
            target_pir, comparable_pirs, 
            target_photos, comparable_photos,
            listing_data
        )
        
        # Step 2: Run all 9 phases
        for phase_num in range(1, 10):
            phase_config = PHASES[phase_num]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"PHASE {phase_num}: {phase_config['name'].upper()}")
            logger.info(f"Model: {phase_config['model']}")
            logger.info(f"{'='*60}")
            
            # Get previous phase output as input
            prev_output = self.phase_outputs.get(phase_num - 1)
            
            # Run the phase
            self.phase_outputs[phase_num] = await self._run_phase(
                phase_num=phase_num,
                model=phase_config["model"],
                task=phase_config["task"],
                output_schema=phase_config["output_schema"],
                previous_output=prev_output
            )
            
            logger.info(f"Phase {phase_num} complete ✓")
        
        # Step 3: Return final output
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n{'='*60}")
        logger.info(f"ESTIMATION COMPLETE in {duration:.1f}s")
        logger.info(f"{'='*60}")
        
        return self.phase_outputs[9]
    
    async def _build_context(
        self,
        target_pir: Dict,
        comparable_pirs: List[Dict],
        target_photos: List[bytes],
        comparable_photos: List[List[bytes]],
        listing_data: Dict
    ) -> str:
        """
        Build the ~700K token context that gets cached.
        
        This includes:
        - Knowledge Graph (214K)
        - BCCA INDEX (444K)
        - FFE INDEX (12K)
        - Supporting knowledge (24K)
        - Target and comparable data (variable)
        """
        # Load static knowledge (these are pre-built files)
        kg = self._load_file("pricing/data/knowledge_graph.json")
        bcca_index = self._load_file("pricing/data/bcca_index.txt")
        ffe_index = self._load_file("pricing/data/ffe_index.txt")
        energy_knowledge = self._load_file("pricing/data/energy_knowledge.json")
        process_knowledge = self._load_file("pricing/data/process_knowledge.json")
        interior_knowledge = self._load_file("pricing/data/interior_knowledge.json")
        
        # Build system instruction
        context = f"""
{PHASE_SYSTEM_INSTRUCTION}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH - 683 RENOVATION TASKS
═══════════════════════════════════════════════════════════════════════════════
{kg}

═══════════════════════════════════════════════════════════════════════════════
BCCA INDEX - 12,565 CONSTRUCTION ITEMS (code|unit|description)
═══════════════════════════════════════════════════════════════════════════════
{bcca_index}

═══════════════════════════════════════════════════════════════════════════════
FFE INDEX - 202 FURNITURE/FIXTURE ITEMS (with tier pricing)
═══════════════════════════════════════════════════════════════════════════════
{ffe_index}

═══════════════════════════════════════════════════════════════════════════════
ENERGY KNOWLEDGE
═══════════════════════════════════════════════════════════════════════════════
{energy_knowledge}

═══════════════════════════════════════════════════════════════════════════════
PROCESS KNOWLEDGE
═══════════════════════════════════════════════════════════════════════════════
{process_knowledge}

═══════════════════════════════════════════════════════════════════════════════
INTERIOR DESIGN KNOWLEDGE
═══════════════════════════════════════════════════════════════════════════════
{interior_knowledge}

═══════════════════════════════════════════════════════════════════════════════
TARGET PROPERTY
═══════════════════════════════════════════════════════════════════════════════
Listing: {json.dumps(listing_data, indent=2)}

PIR: {json.dumps(target_pir, indent=2)}

═══════════════════════════════════════════════════════════════════════════════
COMPARABLE PROPERTIES ({len(comparable_pirs)} comparables)
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(comparable_pirs, indent=2)}
"""
        return context
    
    async def _run_phase(
        self,
        phase_num: int,
        model: str,
        task: str,
        output_schema: type,
        previous_output: Optional[Any]
    ) -> Any:
        """
        Run a single phase with cached context.
        
        Args:
            phase_num: Which phase (1-9)
            model: Model to use (pro or flash)
            task: Task description
            output_schema: Pydantic schema for output
            previous_output: Output from previous phase (if any)
        
        Returns:
            Parsed output matching output_schema
        """
        # Build phase-specific prompt
        prompt = self._build_phase_prompt(phase_num, task, previous_output)
        
        # Create model instance
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2 if "check" in PHASES[phase_num]["name"] else 0.7,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # Call with cached context
        # Note: Context caching is automatic when same content is sent
        # Gemini's server-side caching handles this
        response = await gemini_model.generate_content_async([
            {"role": "user", "parts": [self.cached_context]},
            {"role": "user", "parts": [prompt]}
        ])
        
        # Parse response
        try:
            result = json.loads(response.text)
            # Validate against schema
            validated = output_schema(**result)
            return validated
        except Exception as e:
            logger.error(f"Phase {phase_num} output parsing failed: {e}")
            logger.error(f"Raw response: {response.text[:1000]}...")
            raise
    
    def _build_phase_prompt(
        self,
        phase_num: int,
        task: str,
        previous_output: Optional[Any]
    ) -> str:
        """Build the phase-specific prompt."""
        
        phase_prompts = {
            1: """
PHASE 1: SCOPE DEFINITION

Your task: {task}

Analyze the target property and comparables. Define what needs to change.

OUTPUT REQUIREMENTS:
1. List EVERY room from the target property
2. For each room, identify what systems need work
3. Flag items that are CONSISTENT across rooms (same paint, same outlets)
4. Flag items that are UNIQUE to specific rooms
5. Reference the comparable that drives each decision

Return JSON matching DraftScope schema.
""",
            2: """
PHASE 2: SCOPE COMPLETENESS CHECK

Your task: {task}

Previous phase output:
{previous_output}

CRITICAL RULES:
- You may ADD items, you may NOT remove items
- Check every room is covered
- Check minimum items per room: bathroom≥15, kitchen≥20, bedroom≥8
- Check all dependencies are satisfied
- If you find nothing missing, still return the verified scope

Return JSON matching VerifiedScope schema.
""",
            3: """
PHASE 3: WORK PHASES EXPANSION

Your task: {task}

Previous phase output (verified scope):
{previous_output}

Expand each scope item into:
- Materials line item
- Labor line item  
- Add site logistics (scaffolding, skip, protection)
- Add cleanup phases
- Identify permits needed
- Assign to weeks based on sequencing

Return JSON matching FullBOQDraft schema.
""",
            4: """
PHASE 4: BOQ COMPLETENESS CHECK

Your task: {task}

Previous phase output:
{previous_output}

CRITICAL RULES:
- You may ADD items, you may NOT remove items
- Every material must have corresponding labor
- Site logistics must be included
- Sequencing must be physically possible
- Contingency allowance must be included

Return JSON matching VerifiedBOQ schema.
""",
            5: """
PHASE 5: PRICING STRATEGY + DB ADAPTATION

Your task: {task}

Previous phase output (verified BOQ):
{previous_output}

For EACH line item:
1. Find the best matching BCCA code from the INDEX above
2. If not exact match, EXPLAIN your adaptation:
   - What the scope says
   - What BCCA code you're using
   - Why this adaptation makes sense
   - What multiplier you're applying (1.0 if exact)
3. Calculate quantity using formulas
4. Apply pricing

Return JSON matching PricedBOQDraft schema.
""",
            6: """
PHASE 6: PRICING ADJUSTMENTS

Your task: {task}

Previous phase output (priced BOQ):
{previous_output}

Apply adjustments with EXPLICIT REASONING:
- REGIONAL: BCCA is Andalucía base. Adjust for actual location.
- ACCESS: No lift? High floor? Narrow access?
- BUILDING TYPE: Heritage? New construction?
- MARKET: Current demand conditions?

Each adjustment needs:
- Type
- Multiplier
- Full reasoning

Return JSON matching AdjustedBOQ schema.
""",
            7: """
PHASE 7: TIMELINE VALIDATION

Your task: {task}

Previous phase output (adjusted BOQ with schedule):
{previous_output}

Check physical constraints:
- Waterproofing must cure 48h before tiling
- Plaster must dry 2 weeks before painting
- Electrical rough-in before closing walls
- Kitchen appliances after cabinets
- Critical path makes sense?

Fix any sequencing issues.

Return JSON matching TimelineVerification schema.
""",
            8: """
PHASE 8: ENERGY COMPLIANCE CHECK

Your task: {task}

Previous phase output:
{previous_output}

Check energy improvements:
- What's the current CEE rating?
- What's the target comparable's CEE?
- Does our scope include sufficient:
  - Insulation (walls, roof, floor)?
  - Window upgrades?
  - HVAC improvements?
- What CEE will we achieve?
- If gap exists, ADD items to close it

Return JSON matching EnergyVerification schema.
""",
            9: """
PHASE 9: FINAL SANITY CHECK + OUTPUT

Your task: {task}

All previous phase outputs available in context.

Final checks:
- Cost per m² reasonable? (€800-2000 typical)
- Renovation cost < 30% of property value?
- Labor:materials ratio sensible? (40:60 to 50:50)
- Any obvious gaps?
- Any duplications?
- Would YOU renovate this property this way?

Package the final output with:
- Executive summary
- Room-by-room breakdown
- Timeline visualization data
- Full reasoning chain

Return JSON matching FinalUnifiedEstimate schema.
"""
        }
        
        prompt = phase_prompts[phase_num].format(
            task=task,
            previous_output=json.dumps(previous_output, indent=2, default=str) if previous_output else "N/A"
        )
        
        return prompt
    
    def _load_file(self, path: str) -> str:
        """Load a file from the pricing data directory."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {path}")
            return f"[FILE NOT FOUND: {path}]"


# =============================================================================
# PHASE SYSTEM INSTRUCTION
# =============================================================================

PHASE_SYSTEM_INSTRUCTION = """
You are a senior Spanish renovation cost estimator working through a 9-phase 
estimation process. Each phase builds on the previous.

CRITICAL RULES:
1. In CHECK phases (2, 4, 7, 8): You may ADD items, you may NOT remove items
2. Always reference the Knowledge Graph for task dependencies
3. Always use BCCA INDEX for construction pricing
4. Always use FFE INDEX for furniture/fixtures pricing
5. When adapting prices, EXPLAIN your reasoning
6. Regional adjustments must have explicit reasoning
7. Timeline must respect physical constraints (cure times, sequencing)

YEAR-CONTEXT INTERPRETATION (CRITICAL):
The PIR contains `year_context` with construction year and implied possibilities.
Use this information as CONTEXT, not as REQUIREMENTS:

FOR TARGET PROPERTY:
- `implied_possibilities` = What MIGHT be behind the walls based on construction era
- `visual_evidence` = What PIR SAW that confirms/contradicts the implication
- `confidence: "confirmed"` = Visual evidence supports year-implied issue
- `confidence: "possible"` = No visual evidence either way - note for inspection
- `confidence: "unlikely"` = Visual evidence contradicts year-implied issue

FOR COMPARABLES:
- `likely_prior_upgrades` = What we THINK was upgraded to achieve "very good" status
- This is INFORMATIONAL - tells you what work similar buildings needed
- Do NOT assume target needs identical upgrades - compare VISIBLE outcomes

FRAMING FOR PACKAGES:
- Packages are based on MATCHING VISIBLE OUTCOMES of comparables
- NOT on blindly applying year-based rules
- Year context informs WHAT TO INSPECT, not WHAT TO MANDATE
- Include inspection recommendations for "possible" confidence items

PROFESSIONAL DISCLAIMER:
All estimates include the standard disclaimer that hidden systems may require
professional inspection. Year-implied possibilities inform this disclaimer.

COMPLETENESS IS EVERYTHING:
- A bathroom renovation has ≥15 line items
- A kitchen renovation has ≥20 line items
- Every demolition has a corresponding installation
- Every wet area has waterproofing
- Every room in the listing is addressed

OUTPUT FORMAT:
- Always return valid JSON matching the specified schema
- Include reasoning in designated fields
- Be explicit about adaptations and multipliers
"""
```

### Implementation Checklist Updates

Add to Part 7:

```markdown
### Phase 0: Multi-Phase Orchestrator (V0.4.8)

- [ ] Create `pricing/multi_phase_estimator.py` - Main orchestrator class
- [ ] Create `pricing/schemas/phase_outputs.py` - All phase output schemas
- [ ] Create `pricing/phase_prompts/` - Phase-specific prompt templates
- [ ] Create `pricing/data/bcca_index.txt` - BCCA with 100-char descriptions (from paraphrasing)
- [ ] Create `pricing/data/ffe_index.txt` - FFE formatted for context
- [ ] Test context caching behavior with Gemini API
- [ ] Benchmark: 9-phase vs single-call quality comparison
- [ ] Benchmark: Cost per estimate with caching
```

---

## The Core Insight

**V0.3 was wrong** by splitting into 4 stages:

**V0.3 was wrong** by splitting into 4 stages:
```
WRONG (V0.3):
PIR → Gap Analysis → Scope Expansion → EstimatorV3 → Format
     (stage 2)        (stage 3)         (stage 4)     (stage 5)
     
Each handoff = information loss, context switching, complexity
```

**V0.4 is right** by unifying:
```
RIGHT (V0.4):
PIR → UNIFIED ESTIMATOR (Gap + Scope + Pricing in one Gemini call) → Format Views
      (one massive call with tools)                                   (optional)
```

---

## Architecture Overview

> **V0.4.7 KEY CHANGE**: Full BCCA + FFE indexes IN CONTEXT. Gemini sees ALL available items and matches semantically. SQL only for final price lookup.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PETER AGENTIC V0.4.7 - FULL CONTEXT ARCHITECTURE               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  WHY FULL CONTEXT?                                                          │
│  ─────────────────                                                          │
│  OLD: Gemini guesses SQL query → hopes to find good matches                 │
│  NEW: Gemini READS all 12K BCCA + 202 FFE items → picks best semantically   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              SYSTEM INSTRUCTION (~700K tokens total)                │    │
│  │                                                                     │    │
│  │  1. ROLE & GROUNDING RULES (~3K)                                   │    │
│  │     "You are a senior Spanish renovation cost estimator..."        │    │
│  │     "Read the BCCA INDEX and FFE INDEX below to find items..."     │    │
│  │     "Call get_bcca_price(code) only to fetch final price..."       │    │
│  │                                                                     │    │
│  │  2. KNOWLEDGE GRAPH - FULL (~214K)                                 │    │
│  │     683 tasks with dependencies, quantity guidance, energy impact  │    │
│  │                                                                     │    │
│  │  ════════════════════════════════════════════════════════════════  │    │
│  │  3. BCCA INDEX - FULL (~444K tokens) ⭐ NEW IN V0.4.7              │    │
│  │  ════════════════════════════════════════════════════════════════  │    │
│  │     ALL 12,565 construction items:                                 │    │
│  │     - Code + Unit + AI-paraphrased 100-char description            │    │
│  │     - Created by Gemini 2.5 Flash Lite (intelligent compression)   │    │
│  │     - Gemini READS and MATCHES semantically                        │    │
│  │     - No query guessing - sees everything available!               │    │
│  │                                                                     │    │
│  │     Format:                                                        │    │
│  │     09ACE00130|m2|Alicatado azulejo 30x30 gres porcel. C1 s/UNE    │    │
│  │     08PCM00100|ud|Puerta corredera madera maciza 80x210 lacada     │    │
│  │                                                                     │    │
│  │  ════════════════════════════════════════════════════════════════  │    │
│  │  4. FFE INDEX - FULL (~12K tokens) ⭐ NEW IN V0.4.7                │    │
│  │  ════════════════════════════════════════════════════════════════  │    │
│  │     ALL 202 furniture/fixture items:                               │    │
│  │     - Full tier pricing (budget/mid/high/luxury)                   │    │
│  │     - Brand references per tier (IKEA → Kave → Marset → Poliform)  │    │
│  │     - Style tags for adaptation matching                           │    │
│  │     - NO tool call needed - all info in context!                   │    │
│  │                                                                     │    │
│  │  5. SUPPORTING KNOWLEDGE (~24K)                                    │    │
│  │     - Energy knowledge (~6K)                                       │    │
│  │     - Process knowledge (~4K)                                      │    │
│  │     - Interior design knowledge (~8K)                              │    │
│  │     - Quantity formulas (~2K)                                      │    │
│  │     - FFE style matching guide (~4K)                               │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │            TOOLS (Simplified - Price Lookup Only)                   │    │
│  │                                                                     │    │
│  │  get_bcca_price(code: str)                                         │    │
│  │  ─────────────────────────────────────────────────────────────────  │    │
│  │  - Simple lookup AFTER Gemini finds code in BCCA INDEX             │    │
│  │  - Returns: {code, price, unit, full_desc}                         │    │
│  │  - Gemini already knows what it wants from reading the index       │    │
│  │                                                                     │    │
│  │  (FFE: NO TOOL - full pricing already in context!)                 │    │
│  │                                                                     │    │
│  │  EXAMPLE WORKFLOW:                                                 │    │
│  │  ─────────────────────────────────────────────────────────────────  │    │
│  │  1. Photo shows "terrazzo-style floor tiles in bathroom"           │    │
│  │  2. Gemini reads BCCA INDEX, sees multiple options:                │    │
│  │     - 09ACE00xxx: Alicatado terrazzo discrete tiles                │    │
│  │     - 09STC00xxx: Suelo continuo terrazo (poured)                  │    │
│  │  3. Gemini reasons: "Photo shows discrete tiles, not poured"       │    │
│  │  4. Gemini calls: get_bcca_price("09ACE00xxx")                     │    │
│  │  5. Returns: €28.45/m² with full installation specs                │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     USER PROMPT (Per Request ~30K)                  │    │
│  │                                                                     │    │
│  │  TARGET PROPERTY:                                                  │    │
│  │  - PropertyIntelligenceReport (full)                               │    │
│  │  - Photos (as image parts)                                         │    │
│  │  - Listing data (price, m2, rooms, energy rating)                  │    │
│  │                                                                     │    │
│  │  COMPARABLE PROPERTIES (1-3):                                      │    │
│  │  - PropertyIntelligenceReport (full) for each                      │    │
│  │  - Key attributes: finish_quality, design_style, systems           │    │
│  │                                                                     │    │
│  │  TASK:                                                             │    │
│  │  "Compare target to comparables. Identify what needs to change.    │    │
│  │   For each change, find the right BCCA item from the INDEX.        │    │
│  │   Call get_bcca_price() to get the price.                          │    │
│  │   For FFE, read pricing directly from the FFE INDEX.               │    │
│  │   Output the complete renovation estimate."                        │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     GEMINI REASONING (ReAct Loop)                   │    │
│  │                                                                     │    │
│  │  Step 1: COMPARE                                                   │    │
│  │  "Target has dated bathroom tiles vs comparable's modern finish"   │    │
│  │  "Target energy rating E vs comparable's C - need insulation"      │    │
│  │                                                                     │    │
│  │  Step 2: IDENTIFY INTERVENTIONS                                    │    │
│  │  "bathroom_tile_replacement, wall_insulation, window_replacement"  │    │
│  │                                                                     │    │
│  │  Step 3: TRAVERSE KG                                               │    │
│  │  "bathroom_tile_replacement REQUIRES: demolition_tiles,            │    │
│  │   wall_preparation, waterproofing, tile_installation"              │    │
│  │  "Each has quantity_guidance in KG"                                │    │
│  │                                                                     │    │
│  │  Step 4: CALL discover_bcca (tool call)                            │    │
│  │  [Gemini gets candidate pools for each chapter/unit combo]         │    │
│  │                                                                     │    │
│  │  Step 5: READ CANDIDATES & SELECT WITH REASONING                   │    │
│  │  "Saw 25 tile options (€21-52/m²). Selected 09ACE00130 (30x30)    │    │
│  │   because comparable has modern large-format. Not 10x10 (dated)."  │    │
│  │                                                                     │    │
│  │  Step 6: PACKAGE RESULT                                            │    │
│  │  [Output structured JSON per response_schema]                      │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     RESPONSE SCHEMA (65K output limit)              │    │
│  │                                                                     │    │
│  │  UnifiedEstimate:                                                  │    │
│  │    gap_analysis:                                                   │    │
│  │      comparisons: [{attribute, target_value, comparable_value}]    │    │
│  │      identified_gaps: [{gap_id, description, priority}]            │    │
│  │                                                                     │    │
│  │    scope:                                                          │    │
│  │      rooms: [{room_id, room_type, interventions}]                  │    │
│  │      interventions: [{                                             │    │
│  │        intervention_id, kg_task_id,                                │    │
│  │        required_tasks: [{task_id, reason}],                        │    │
│  │        triggered_tasks: [{task_id, reason}]                        │    │
│  │      }]                                                            │    │
│  │                                                                     │    │
│  │    bill_of_quantities:                                             │    │
│  │      line_items: [{                                                │    │
│  │        room_id, task_id, task_name,                                │    │
│  │        bcca_code, bcca_description,                                │    │
│  │        quantity, unit, unit_price, total,                          │    │
│  │        reasoning: "Why this BCCA item, why this quantity"          │    │
│  │      }]                                                            │    │
│  │      room_totals: [{room_id, total}]                               │    │
│  │      grand_total: number                                           │    │
│  │                                                                     │    │
│  │    reasoning_chain:                                                │    │
│  │      steps: [{step_number, action, evidence, conclusion}]          │    │
│  │                                                                     │    │
│  │    validation:                                                     │    │
│  │      room_attribution_pct: number  (target: <30% "General")        │    │
│  │      kg_grounding_pct: number      (target: 100%)                  │    │
│  │      bcca_match_pct: number        (target: 100%)                  │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: System Instruction Template

```text
# ROLE

You are a senior Spanish renovation cost estimator with expertise in:
- Spanish construction standards (CTE, REBT)
- BCCA (Base de Costes de la Construcción de Andalucía) pricing
- Property renovation scoping and dependency management

# GROUNDING RULES

1. TASK GROUNDING: Every task you include MUST come from the Knowledge Graph below. 
   Do not invent tasks. If a task isn't in the KG, it cannot be included.

2. PRICE GROUNDING: Every price MUST come from calling discover_bcca(). 
   Never invent prices. READ the returned candidates and SELECT the best match.

3. QUANTITY GROUNDING: Use the quantity_guidance in each KG task.
   Estimate room dimensions from photos. Show your calculation.

4. DEPENDENCY TRAVERSAL: When you identify an intervention:
   - Check its REQUIRES list - add all prerequisite tasks
   - Check its TRIGGERS list - add commonly triggered follow-on tasks
   - This ensures complete scopes (no missing prep work)

5. ROOM ATTRIBUTION: Every task must be assigned to a specific room.
   Only use "General" for truly whole-property work (e.g., electrical panel upgrade).
   Target: <30% of costs attributed to "General"

6. REASONING CHAINS: For each line item, explain:
   - Why this task is needed (gap → intervention → task)
   - Why this BCCA code (what candidates you saw → which you selected → WHY)
   - Why this quantity (room dimensions → formula → result)

# BCCA DISCOVERY GUIDE

Use discover_bcca(chapter, unit?, keywords?, price_range?, limit?) to get candidates:
- chapter: REQUIRED - BCCA chapter code (see index)
- unit: Filter by m2, ml, ud, m3 (based on task type)
- keywords: Spanish terms to narrow results
- price_range: (min, max) when you know quality tier

CRITICAL: discover_bcca returns CANDIDATES. You must READ descriptions and SELECT.
DO NOT just take the first item. READ and REASON about which matches best.

## BCCA Chapter Index
- 01: Demolitions, earthworks (demolicion, desmontaje, excavacion)
- 02: Concrete, structures (hormigon, estructura, forjado)
- 03: Masonry (fabrica, ladrillo, tabique)
- 05: Roofing (cubierta, tejado, impermeabilizacion)
- 06: Plumbing, drainage (fontaneria, saneamiento, tuberia)
- 07: Insulation (aislamiento, lana, poliestireno)
- 08: Electrical (electricidad, punto luz, mecanismo)
- 09: Finishes (revestimiento, alicatado, solado, pintura)
- 10: Carpentry (carpinteria, puerta, ventana)
- 11: Glass, enclosures (vidrio, acristalamiento)
- 13: HVAC (climatizacion, calefaccion, aire acondicionado)

## Keyword Construction Patterns
- [action] OR [material] OR [specification] - keywords are OR-combined in SQL
- Examples:
  - ["solado", "gres", "porcelanico"] for floor tiles
  - ["alicatado", "azulejo"] for wall tiles
  - ["demolicion", "tabiqueria"] for wall demolition
  - ["punto", "luz", "electrico"] for electrical points
  - ["aislamiento", "lana", "mineral"] for insulation

## Discovery Strategy
1. Start with chapter + unit + 1-2 keywords: discover_bcca(chapter="09", unit="m2", keywords=["solado"])
2. If too many results, add more keywords: keywords=["solado", "porcelanico"]
3. If too few results, remove keywords or broaden unit filter
4. READ the candidates - understand what you're choosing from
5. SELECT based on description match to intent, not just lowest price

## Selection Reasoning (REQUIRED)
When you select a BCCA item, EXPLAIN:
- What candidates you saw (summarize the range)
- Why you chose this one (quality match, specification match)
- Why you rejected others (too basic, too high-end, wrong spec)

# QUANTITY FORMULAS

- floor_m2 = length_m × width_m
- wall_m2 = perimeter_m × height_m (typically 2.5m)
- perimeter_ml = 2 × (length_m + width_m)
- unit = count (doors, windows, fixtures)

Estimate dimensions using (in priority order):
1. Listing data (total m2, room count) - most reliable
2. Photo perspective analysis - visual estimation
3. Spanish standard room sizes - when above unavailable

Note: This is quantity estimation guidance, not an error fallback.
If listing has m2 data, use it. Don't silently guess.

# KNOWLEDGE GRAPH

[KG_CONTEXT_YAML_INSERTED_HERE]

# ENERGY KNOWLEDGE

Use this to understand energy ratings and intervention impacts:

## Rating Scale (Spanish CEE)
- A: Ultra-efficient (new passive house standard)
- B: Very efficient (new construction with excellent insulation)
- C: Efficient (modern renovation standard - typical TARGET)
- D: Average (2007-2013 construction or partial upgrades)
- E: Below average (1980-2006 construction, minimal insulation)
- F: Poor (1960-1979, single-pane windows, no insulation)
- G: Very poor (pre-1960, historic buildings without upgrades)

## Age → Typical Rating Correlation
- Pre-1940: G (no insulation, single glazing, inefficient systems)
- 1940-1959: G-F (minimal construction standards)
- 1960-1979: F-E (first building codes, but weak thermal requirements)
- 1980-2006: E-D (NBE-CT-79 thermal code, some insulation)
- 2007-2013: D-C (CTE 2006, improved requirements)
- 2014-present: C-B (CTE 2013/2019, near-zero energy buildings)

## Intervention Impacts
- Wall insulation (SATE/ETICS): +1-2 letters (E→C or D→B)
- Window replacement (double/triple glazing): +1 letter
- Roof insulation: +1 letter (high impact in top floors)
- HVAC upgrade (heat pump): +1 letter + operational savings
- Solar thermal: +0.5 letter (hot water contribution)
- LED lighting + efficient appliances: +0.5 letter

## Climate Zones (Spain CTE DB-HE)
- Zone A: Canary Islands, mild coastal (U-wall ≤ 0.94)
- Zone B: Mediterranean coast (U-wall ≤ 0.82)
- Zone C: Southern interior, Madrid basin (U-wall ≤ 0.73)
- Zone D: Northern interior, Castilla (U-wall ≤ 0.66)
- Zone E: Mountain areas, Pyrenees (U-wall ≤ 0.57)

[Full energy_knowledge.json also available for detailed reference]

# PROCESS KNOWLEDGE

Use this to understand renovation triggers and regulatory context:

## Renovation Triggers
- REGULATORY: ITE inspection (buildings >50 years), cédula de habitabilidad renewal
- ECONOMIC: Property sale/purchase, rental optimization, subsidy availability
- COMFORT: Energy bills too high, thermal discomfort, noise issues
- BUILDING_PROBLEMS: Humidity, cracks, outdated systems, accessibility needs

## When Professional Is Required
- Structural work: Always (architect/engineer certification)
- Electrical panel upgrade: Licensed electrician + boletín
- Gas installation: Licensed installer + certificado
- Facade changes: Municipal license + community approval
- >50m² interior: Often requires project (varies by municipality)

## Community Approval (Horizontal Property)
- Common elements (facade, structure, roof): 3/5 majority
- Accessibility improvements: Simple majority
- Individual unit interior: Generally no approval needed
- New openings in facade: Unanimous or 3/5 depending on statutes

[Full renovation_process_knowledge.json also available for detailed reference]

# INTERIOR DESIGN KNOWLEDGE

Use this to assess finish quality and design style:

## Finish Quality Tiers
- BUILDER_GRADE: Basic functionality, visible hinges, laminate counters, aluminum door frames
- MID_RANGE: Soft-close hinges, composite stone counters, lacquered MDF doors, decent tile
- HIGH_END: Concealed hinges, natural stone/Dekton counters, solid wood or premium veneer
- LUXURY: Custom millwork, book-matched marble, integrated appliances, designer fixtures

## Style Indicators
- DATED (pre-2000): Gotelé walls, dark wood trim, brass fixtures, small tiles
- TRANSITIONAL: Neutral walls, mixed traditional/modern, chrome fixtures
- CONTEMPORARY: Clean lines, large format tiles, matte black/brushed nickel, minimal trim
- WARM_MINIMALISM: Natural materials, curved forms, earth tones, textured surfaces

## Spanish Construction Eras
- Pre-1940: Hydraulic tiles, lime plaster, solid wood doors, high ceilings
- 1960-1980: Terrazzo floors, aluminum windows, built-in wardrobes, small bathrooms
- 1980-2000: Gres tiles, PVC windows, gotelé walls, white sanitaryware
- 2000-2015: Porcelain tiles, aluminum/PVC windows, smooth walls, integrated kitchens
- 2015-present: Large format porcelain, thermal-break aluminum, open concepts

[Full interior_design_knowledge.json also available for detailed reference]
```

---

## Part 2: get_bcca_price Tool Implementation

> **V0.4.7 CHANGE**: With full BCCA INDEX in context, Gemini finds items by READING the index.
> The tool is now a simple **price lookup** - Gemini already knows which code it wants.

### Evolution of BCCA Discovery

| Version | Approach | Problem |
|---------|----------|---------|
| V0.4.0 | Embeddings | Black box scores, wrong matches |
| V0.4.4 | SQL Discovery | Better, but still query guessing |
| **V0.4.7** | **Full Index in Context** | **Gemini SEES everything, picks best** |

### Why Full Context is Better Than Discovery Tools

**V0.4.4 SQL Discovery approach:**
```
LLM guesses SQL query → SQL returns candidates → LLM reads candidates → LLM picks

Problem: LLM might guess wrong keywords, miss items that would have been perfect matches.
"alicatado azulejo" might miss "revestimiento cerámico pared" even though same thing.
```

**V0.4.7 Full Context approach:**
```
LLM sees ALL 12,565 items in BCCA INDEX → Reads semantically → Picks best → Looks up price

LLM has COMPLETE knowledge. Can't miss anything because it sees EVERYTHING.
```

### Comparison: Discovery vs Full Context

| Aspect | SQL Discovery (V0.4.4) | Full Context (V0.4.7) |
|--------|------------------------|----------------------|
| **LLM sees** | Only query results | ALL 12,565 items |
| **Can miss items?** | ✅ Yes, if query wrong | ❌ No, sees everything |
| **Query guessing** | ⚠️ Required | ✅ Not needed |
| **Semantic matching** | On candidates only | On FULL corpus |
| **Tool calls** | Many (one per task) | Few (only price lookups) |
| **Tokens used** | ~10K tool responses | ~444K in context |
| **Total tokens** | ~307K | ~760K |
| **Accuracy** | Good | **Best possible** |

### The Tool: get_bcca_price

Simple price lookup. Gemini already found the code by reading the BCCA INDEX in context.

```python
# =============================================================================
# pricing/bcca_price_lookup.py  (V0.4.7 - Simplified from discovery tool)
# =============================================================================
# PURPOSE: Simple price lookup AFTER Gemini finds the code in BCCA INDEX.
#          Gemini has ALL 12,565 items in context. It reads, reasons, selects.
#          This tool just fetches the final price and full description.
#
# WHY FULL CONTEXT INSTEAD OF DISCOVERY?
# - Gemini can't miss items if it SEES all of them
# - No query guessing, no keyword matching issues
# - Perfect semantic matching across entire corpus
# - "revestimiento cerámico" matches "alicatado azulejo" because Gemini reads both
#
# THE TOOL IS NOW TRIVIAL:
# 1. Gemini reads BCCA INDEX (12,565 items with 100-char descriptions)
# 2. Gemini selects the best code based on semantic understanding
# 3. Gemini calls get_bcca_price(code) to get exact price and full description
# =============================================================================

import sqlite3
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BCCAPriceLookup:
    """
    Simple price lookup for BCCA items.
    
    V0.4.7 ARCHITECTURE:
    1. Full BCCA INDEX (12,565 items) is in Gemini's context
    2. Gemini READS the index and finds the best matching code
    3. Gemini calls get_bcca_price(code) to fetch the price
    
    WHY THIS IS SIMPLE NOW:
    - Gemini has complete knowledge (sees ALL items)
    - No query guessing - semantic matching on full corpus
    - This tool just does the final price lookup
    """
    
    def __init__(self, db_path: str = "Lean MVP/backend/pricing/data/bcca.db"):
        self.db_path = db_path
        
    def get_price(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Look up price for a BCCA code.
        
        Args:
            code: The BCCA code (e.g., "09ACE00130") found in BCCA INDEX
        
        Returns:
            Dict with code, price, unit, full_desc if found, None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, price, unit, full_desc
            FROM price_book
            WHERE code = ?
        """, (code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "code": row[0],
                "price": float(row[1]) if row[1] else 0.0,
                "unit": row[2],
                "full_desc": row[3]  # Full description for detailed reasoning
            }
        return None


# =============================================================================
# TOOL FUNCTION FOR GEMINI
# =============================================================================
# Simple price lookup. Gemini already found the code by reading the BCCA INDEX.

def get_bcca_price(code: str) -> Dict[str, Any]:
    """
    Look up the price for a BCCA code you found in the BCCA INDEX.
    
    WORKFLOW (V0.4.7):
    1. You READ the BCCA INDEX (12,565 items in your context)
    2. You FIND the best matching code semantically
    3. You CALL get_bcca_price(code) to get the exact price
    4. You USE the price in your BoQ
    
    Args:
        code: The BCCA code you selected from reading the BCCA INDEX
              Example: "09ACE00130" for 30x30 ceramic tiles
    
    Returns:
        Dictionary with:
            - code: The BCCA code
            - price: Unit price in EUR (2024 BCCA rates)
            - unit: Unit of measurement (m2, ml, ud, m3)
            - full_desc: Full Spanish description
            - found: Boolean indicating if code exists
    
    EXAMPLE:
    
    You read BCCA INDEX and find:
        09ACE00130|m2|Alicatado azulejo 30x30 gres porcel. C1 UNE
    
    You call:
        get_bcca_price("09ACE00130")
    
    You receive:
        {
            "code": "09ACE00130",
            "price": 32.00,
            "unit": "m2",
            "full_desc": "Alicatado con azulejo cerámico 30x30 cm tipo gres 
                          porcelánico esmaltado, colocado con adhesivo C1 
                          según UNE-EN 12004, sobre soporte de mortero...",
            "found": true
        }
    
    NOTE: The BCCA INDEX has 100-char AI-paraphrased descriptions for quick
    scanning. Use this tool when you need the FULL description for detailed
    reasoning or specification.
    """
    tool = BCCAPriceLookup()
    result = tool.get_price(code)
    
    if result:
        result["found"] = True
        logger.info(f"BCCA Price Lookup: {code} = €{result['price']}/{result['unit']}")
        return result
    else:
        logger.warning(f"BCCA Price Lookup: {code} NOT FOUND")
        return {
            "code": code,
            "found": False,
            "error": f"Code {code} not found in BCCA database"
        }
```

---

## Part 2B: discover_ffe Tool Implementation (FF&E Pricing)

> **Design Philosophy**: Same SQL + LLM Selection pattern as BCCA, but for FF&E (Furniture, Fixtures & Equipment).
> Construction costs come from BCCA. Non-construction costs (furniture, appliances, decor) come from FF&E database.

### Why a Separate FF&E Database?

**BCCA covers construction** (materials + labor):
- Tiling, painting, plumbing, electrical
- Demo, insulation, windows
- Everything installed by contractors

**FF&E covers furnishing** (products purchased):
- Furniture (sofas, beds, tables)
- Appliances (fridge, washing machine)
- Textiles (curtains, rugs)
- Lighting (lamps, not recessed fixtures)
- Decor (art, plants, accessories)

### Data Source: interior_design_knowledge.json

The existing knowledge base has `indicative_ranges_eur` embedded:

```json
// Example from bedroom furniture
"indicative_ranges_eur": {
  "budget": "200-500",
  "mid": "600-1,500",
  "high": "1,800-4,000",
  "luxury": "5,000+"
}

// Example from kitchen appliances
"indicative_ranges_eur": {
  "budget": "2,000-3,500",
  "mid": "4,000-7,000",
  "high": "8,000-15,000",
  "luxury": "20,000+"
}
```

### FFE Database Schema

We need to extract this into a structured SQLite database:

```sql
-- ffe_items.db

CREATE TABLE ffe_categories (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,              -- 'living_room', 'bedroom', 'kitchen_appliances'
    name_es TEXT,                  -- 'Salón', 'Dormitorio', 'Electrodomésticos'
    name_en TEXT
);

CREATE TABLE ffe_items (
    id INTEGER PRIMARY KEY,
    category_code TEXT,            -- FK to ffe_categories.code
    item_code TEXT UNIQUE,         -- 'FFE_SOFA_001', 'FFE_BED_001'
    name_es TEXT,                  -- 'Sofá 3 plazas'
    name_en TEXT,                  -- '3-seater sofa'
    description_es TEXT,           -- What to look for, quality indicators
    
    -- Price ranges by tier (EUR)
    budget_min REAL,
    budget_max REAL,
    mid_min REAL,
    mid_max REAL,
    high_min REAL,
    high_max REAL,
    luxury_min REAL,
    luxury_max REAL,
    
    -- Metadata
    unit TEXT DEFAULT 'ud',        -- 'ud' (unit), 'pack', 'set'
    typical_quantity_per_room REAL,-- e.g., 1 sofa, 4-6 dining chairs
    investment_priority TEXT,      -- 'alta', 'media', 'baja'
    lifespan_years INTEGER,        -- Expected durability
    
    -- Source tracing
    source_brands_budget TEXT,     -- JSON array: ["IKEA", "Conforama"]
    source_brands_mid TEXT,        -- JSON array: ["Kave Home", "Kenay"]
    source_brands_high TEXT,       -- JSON array: ["Treku", "Sancal"]
    source_brands_luxury TEXT,     -- JSON array: ["Poliform", "Minotti"]
    
    -- Documentation
    basis_notes TEXT,              -- How this price was derived
    last_updated DATE
);

-- Example data
INSERT INTO ffe_items (
    category_code, item_code, name_es, description_es,
    budget_min, budget_max, mid_min, mid_max, high_min, high_max, luxury_min, luxury_max,
    unit, typical_quantity_per_room, investment_priority, lifespan_years,
    source_brands_budget, source_brands_mid, source_brands_high, source_brands_luxury,
    basis_notes, last_updated
) VALUES 
-- Living Room Furniture
('living_room', 'FFE_SOFA_3P', 'Sofá 3 plazas', 
 'Pieza central del salón. Budget: tela sintética, Mid: algodón/lino, High: cuero/bouclé, Luxury: diseño de autor',
 400, 800, 1200, 2500, 3000, 6000, 8000, NULL,
 'ud', 1, 'alta', 12,
 '["IKEA", "Conforama"]', '["Kave Home", "Kenay Home"]', '["Sancal", "Expormim"]', '["Poliform", "Minotti"]',
 'Based on 2024 Spanish market survey. IKEA KIVIK/EKTORP as budget baseline. 
  Luxury open-ended as custom/designer pieces vary widely.',
 '2026-01-10'),

('living_room', 'FFE_COFFEE_TABLE', 'Mesa de centro',
 'Mesa baja para salón. Budget: aglomerado, Mid: madera maciza/mármol sintético, High: mármol/nogal, Luxury: diseño firmado',
 80, 200, 300, 800, 1000, 2500, 3000, NULL,
 'ud', 1, 'media', 15,
 '["IKEA", "Maisons du Monde"]', '["Kave Home", "Kenay"]', '["Treku", "Punt"]', '["Poliform", "B&B Italia"]',
 'Wide range reflects material variance. Budget = MDF/particle board, Luxury = solid stone/designer.',
 '2026-01-10'),

-- Bedroom
('bedroom', 'FFE_BED_FRAME', 'Estructura cama + cabecero (matrimonio)',
 'Base y cabecero para cama de matrimonio (150-180cm). Budget: melamina, Mid: lacado/roble, High: nogal/tapizado, Luxury: diseño',
 200, 500, 600, 1500, 1800, 4000, 5000, NULL,
 'ud', 1, 'media', 20,
 '["IKEA", "Muebles Lufe"]', '["Kenay", "Kave", "Tediber"]', '["Treku", "Novamobili"]', '["Poliform", "Schramm"]',
 'Cabecero drives price at higher tiers. Budget = MALM style, Luxury = upholstered designer.',
 '2026-01-10'),

('bedroom', 'FFE_MATTRESS', 'Colchón matrimonio (150-180cm)',
 'Colchón de espuma/muelles. Budget: espuma básica, Mid: muelles ensacados, High: látex/memoria, Luxury: artesanal',
 200, 400, 500, 1200, 1500, 3000, 4000, NULL,
 'ud', 1, 'alta', 10,
 '["IKEA", "Carrefour"]', '["Tediber", "Emma", "Flex"]', '["Tempur", "Hästens"]', '["Hästens", "Vispring"]',
 'Critical comfort item. Tediber/Emma disrupted mid-range. Hästens €10K+ for ultra-luxury.',
 '2026-01-10'),

-- Kitchen Appliances
('kitchen_appliances', 'FFE_APPLIANCE_PACK', 'Pack electrodomésticos principales',
 'Nevera + Horno + Placa + Lavavajillas + Campana. Budget: marcas blancas, Mid: Balay/Bosch, High: Siemens/Neff, Luxury: Gaggenau',
 2000, 3500, 4000, 7000, 8000, 15000, 20000, NULL,
 'pack', 1, 'alta', 12,
 '["Beko", "Indesit", "Teka"]', '["Balay", "Bosch", "Samsung"]', '["Siemens", "Neff", "Miele"]', '["Gaggenau", "Sub-Zero", "Wolf"]',
 'Pack pricing from MediaMarkt/El Corte Inglés promotions. Luxury prices for integrated paneled units.',
 '2026-01-10'),

-- Bathroom Fixtures (not sanitaryware - that's BCCA)
('bathroom', 'FFE_BATHROOM_ACCESSORIES', 'Accesorios baño (toallero, espejo, accesorios)',
 'Conjunto de accesorios: espejo, toalleros, portarrollos, dispensador. Budget: IKEA/Leroy, Mid: Roca/Tres, High: Inbani, Luxury: diseño',
 100, 250, 300, 800, 1000, 2500, 3000, NULL,
 'set', 1, 'baja', 15,
 '["IKEA", "Leroy Merlin"]', '["Roca", "Tres Grifería"]', '["Inbani", "Cosmic"]', '["Agape", "Boffi"]',
 'Espejo drives cost. Budget = basic mirror, Luxury = backlit designer mirror.',
 '2026-01-10'),

-- Lighting
('lighting', 'FFE_CEILING_PENDANT', 'Lámpara colgante principal',
 'Lámpara decorativa para comedor/salón. Budget: básica, Mid: diseño español, High: Marset/Vibia, Luxury: firmada',
 50, 150, 200, 600, 800, 2000, 2500, NULL,
 'ud', 2, 'media', 20,
 '["IKEA", "Leroy Merlin"]', '["Faro Barcelona", "Schuller"]', '["Marset", "Vibia", "Santa & Cole"]', '["Foscarini", "Flos", "Moooi"]',
 'Spanish lighting brands (Marset, Vibia) are world-class. High tier = good value for quality.',
 '2026-01-10'),

-- Textiles
('textiles', 'FFE_CURTAINS_LIVING', 'Cortinas salón (por ventana)',
 'Cortinas confeccionadas. Budget: poliéster, Mid: lino sintético, High: lino natural, Luxury: a medida con blackout',
 80, 200, 250, 600, 800, 1500, 2000, NULL,
 'ud', 2, 'media', 8,
 '["IKEA", "Zara Home"]', '["El Corte Inglés", "Textura"]', '["Gancedo", "Gastón y Daniela"]', '["Confección a medida", "Diseñador"]',
 'Price per window opening. Living rooms typically have 2-3 windows.',
 '2026-01-10'),

('textiles', 'FFE_RUG_LIVING', 'Alfombra salón (200x300 aprox)',
 'Alfombra decorativa grande. Budget: sintética, Mid: lana/algodón, High: lana premium/sisal, Luxury: vintage/diseño',
 100, 300, 400, 1200, 1500, 4000, 5000, NULL,
 'ud', 1, 'media', 10,
 '["IKEA", "Sklum"]', '["Kave", "La Redoute"]', '["Nanimarquina", "GAN"]', '["Diurne", "Edición limitada"]',
 'GAN and Nanimarquina are Spanish high-end rug brands with global reputation.',
 '2026-01-10');

-- Indices for discovery
CREATE INDEX idx_ffe_category ON ffe_items(category_code);
CREATE INDEX idx_ffe_priority ON ffe_items(investment_priority);
```

### discover_ffe Tool Implementation

```python
# =============================================================================
# pricing/ffe_discovery.py
# =============================================================================
# PURPOSE: Provide Gemini with a tool to discover FF&E (Furniture, Fixtures,
#          Equipment) pricing for non-construction items.
#
# RELATIONSHIP TO BCCA:
# - BCCA = Construction costs (materials + labor, installed by contractors)
# - FFE = Furnishing costs (products purchased, delivered/assembled)
#
# DATA SOURCE:
# Prices extracted from interior_design_knowledge.json + market research.
# Each item has basis_notes explaining how the price was derived.
#
# DESIGN PRINCIPLE: Same SQL + LLM Selection pattern as discover_bcca.
# LLM reads candidates, understands quality tiers, selects appropriate tier.
# =============================================================================

import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FFECandidate:
    """
    An FF&E item candidate for LLM selection.
    
    Unlike BCCA (single price per code), FFE has TIER-based pricing.
    The LLM must select the appropriate tier based on comparable finish quality.
    """
    item_code: str          # e.g., "FFE_SOFA_3P"
    category: str           # e.g., "living_room"
    name_es: str            # e.g., "Sofá 3 plazas"
    description_es: str     # Quality indicators, what to look for
    
    # Price ranges by tier (EUR)
    budget_range: str       # e.g., "400-800"
    mid_range: str          # e.g., "1,200-2,500"
    high_range: str         # e.g., "3,000-6,000"
    luxury_range: str       # e.g., "8,000+"
    
    # For calculation
    unit: str               # 'ud', 'pack', 'set'
    typical_qty: float      # per room
    
    # Brands by tier (helps LLM understand positioning)
    brands_budget: List[str]
    brands_mid: List[str]
    brands_high: List[str]
    brands_luxury: List[str]
    
    # Documentation
    basis_notes: str        # How this was priced


class FFEDiscoveryTool:
    """
    SQL-based discovery of FF&E items for LLM selection.
    
    WORKFLOW:
    1. LLM reasons: "Need living room furniture, comparable is mid-range"
    2. LLM calls: discover_ffe(category="living_room")
    3. Tool returns: All FFE items in that category with tier pricing
    4. LLM READS: Understands each item and its tier pricing
    5. LLM SELECTS: Picks appropriate tier based on comparable quality
    6. LLM EXPLAINS: "Selected mid-range sofa (€1,200-2,500) to match 
       comparable's Kave Home style finish"
    """
    
    def __init__(self, db_path: str = "Lean MVP/backend/pricing/data/ffe.db"):
        self.db_path = db_path
        
    def discover(
        self,
        category: Optional[str] = None,
        item_code: Optional[str] = None,
        investment_priority: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> List[FFECandidate]:
        """
        Discover FF&E items using structured SQL filtering.
        
        Args:
            category: FFE category code. Options:
                - living_room: Sofás, mesas, estanterías
                - bedroom: Camas, colchones, mesitas
                - dining: Mesa comedor, sillas
                - kitchen_appliances: Electrodomésticos
                - bathroom: Accesorios (no sanitarios - eso es BCCA)
                - lighting: Lámparas decorativas
                - textiles: Cortinas, alfombras
                - outdoor: Mobiliario exterior
            
            item_code: Specific FFE item code (if known)
            
            investment_priority: Filter by priority
                - alta: Items worth investing in (long lifespan, daily use)
                - media: Balance of cost/impact
                - baja: Can be budget without much sacrifice
            
            keywords: Spanish keywords to filter names/descriptions
            
        Returns:
            List of FFE candidates with full tier pricing.
            LLM should select appropriate tier based on comparable finish quality.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build SQL query
        sql = """
            SELECT 
                item_code, category_code, name_es, description_es,
                budget_min, budget_max, mid_min, mid_max, 
                high_min, high_max, luxury_min, luxury_max,
                unit, typical_quantity_per_room,
                source_brands_budget, source_brands_mid, 
                source_brands_high, source_brands_luxury,
                basis_notes
            FROM ffe_items
            WHERE 1=1
        """
        params: List[Any] = []
        
        if category:
            sql += " AND category_code = ?"
            params.append(category)
            
        if item_code:
            sql += " AND item_code = ?"
            params.append(item_code)
            
        if investment_priority:
            sql += " AND investment_priority = ?"
            params.append(investment_priority)
            
        if keywords:
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append(
                    "(LOWER(name_es) LIKE LOWER(?) OR LOWER(description_es) LIKE LOWER(?))"
                )
                params.extend([f"%{kw}%", f"%{kw}%"])
            sql += f" AND ({' OR '.join(keyword_conditions)})"
        
        sql += " ORDER BY category_code, name_es"
        
        logger.debug(f"FFE Discovery SQL: {sql}")
        cursor.execute(sql, params)
        
        candidates = []
        for row in cursor.fetchall():
            # Format price ranges
            def format_range(min_val, max_val):
                if max_val is None:
                    return f"€{int(min_val):,}+"
                return f"€{int(min_val):,}-{int(max_val):,}"
            
            # Parse JSON brand arrays
            import json
            def parse_brands(brands_json):
                try:
                    return json.loads(brands_json) if brands_json else []
                except:
                    return []
            
            candidates.append(FFECandidate(
                item_code=row[0],
                category=row[1],
                name_es=row[2],
                description_es=row[3],
                budget_range=format_range(row[4], row[5]),
                mid_range=format_range(row[6], row[7]),
                high_range=format_range(row[8], row[9]),
                luxury_range=format_range(row[10], row[11]),
                unit=row[12],
                typical_qty=row[13],
                brands_budget=parse_brands(row[14]),
                brands_mid=parse_brands(row[15]),
                brands_high=parse_brands(row[16]),
                brands_luxury=parse_brands(row[17]),
                basis_notes=row[18]
            ))
        
        conn.close()
        
        logger.info(f"FFE Discovery: category={category}, found {len(candidates)} items")
        return candidates


# =============================================================================
# TOOL FUNCTION FOR GEMINI
# =============================================================================

def discover_ffe(
    category: Optional[str] = None,
    item_code: Optional[str] = None,
    investment_priority: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Discover FF&E (Furniture, Fixtures, Equipment) pricing.
    
    USE FOR NON-CONSTRUCTION COSTS:
    - Furniture (sofas, beds, tables, chairs)
    - Appliances (fridge, oven, washing machine)
    - Textiles (curtains, rugs, bedding)
    - Lighting (decorative lamps, not recessed fixtures)
    - Decor and accessories
    
    USE discover_bcca FOR CONSTRUCTION COSTS:
    - Materials and labor installed by contractors
    - Tiling, painting, plumbing, electrical
    - Sanitaryware (toilets, sinks - installed)
    
    WORKFLOW:
    1. Identify what FF&E the comparable has (from PIR)
    2. Call discover_ffe(category=...) to get items and tier pricing
    3. READ the items - understand what each one is
    4. SELECT the appropriate TIER based on comparable's finish quality
    5. EXPLAIN: "Selected mid-range because comparable has Kave Home style"
    
    TIER SELECTION GUIDE:
    - budget: IKEA, basic functionality, shorter lifespan
    - mid: Kave Home, Kenay - Spanish mid-market, good value
    - high: Treku, Sancal - Spanish design brands, long lifespan
    - luxury: Poliform, Minotti - designer, investment pieces
    
    Args:
        category: FFE category. Options:
            - living_room, bedroom, dining, kitchen_appliances
            - bathroom, lighting, textiles, outdoor
        
        item_code: Specific item code if known
        
        investment_priority: 'alta', 'media', 'baja'
            Use 'alta' for items worth quality investment (sofa, mattress)
        
        keywords: Spanish keywords to filter
    
    Returns:
        Dictionary with:
            - candidates: List of items with tier pricing
            - metadata: Search parameters
    
    EXAMPLE:
    
    Intent: "Price living room furniture for mid-range comparable"
    
    Step 1 - CALL:
        discover_ffe(category="living_room")
    
    Step 2 - READ returned items:
        FFE_SOFA_3P - Sofá 3 plazas
          Budget: €400-800 (IKEA, Conforama)
          Mid: €1,200-2,500 (Kave Home, Kenay)
          High: €3,000-6,000 (Sancal, Expormim)
          Luxury: €8,000+ (Poliform, Minotti)
          
        FFE_COFFEE_TABLE - Mesa de centro
          Budget: €80-200
          Mid: €300-800
          ...
    
    Step 3 - SELECT tier with reasoning:
        "Comparable has mid-range finish (Kave Home style furniture visible
         in photos). Selecting MID tier for all living room items:
         - Sofá 3 plazas: €1,850 (mid of €1,200-2,500)
         - Mesa de centro: €550 (mid of €300-800)"
    
    Step 4 - USE in estimate with basis:
        {
            ffe_code: "FFE_SOFA_3P",
            name_es: "Sofá 3 plazas",
            tier_selected: "mid",
            unit_price: 1850.00,
            quantity: 1,
            total: 1850.00,
            reasoning: "Mid-range tier to match comparable's Kave Home style. 
                       Price at midpoint of €1,200-2,500 range."
        }
    """
    tool = FFEDiscoveryTool()
    
    candidates = tool.discover(
        category=category,
        item_code=item_code,
        investment_priority=investment_priority,
        keywords=keywords
    )
    
    return {
        "candidates": [asdict(c) for c in candidates],
        "metadata": {
            "category": category,
            "item_code": item_code,
            "investment_priority": investment_priority,
            "keywords": keywords,
            "count": len(candidates)
        },
        "tier_guide": {
            "budget": "IKEA level - functional, basic materials, 5-8 year lifespan",
            "mid": "Kave/Kenay level - good design, quality materials, 10-12 year",
            "high": "Treku/Sancal level - Spanish design brands, premium, 15-20 year",
            "luxury": "Poliform/Minotti - investment pieces, heirloom quality"
        }
    }
```

### Price Derivation Documentation

**CRITICAL**: Every FFE item MUST have `basis_notes` explaining:
1. **Source**: Where the price range came from
2. **Brands**: Reference brands used to anchor each tier
3. **Year**: When the research was done
4. **Caveats**: Any assumptions or limitations

Example basis_notes:

```
"Based on 2024 Spanish market survey. 
Budget: IKEA KIVIK (€599) and EKTORP (€399) as anchors.
Mid: Kave Home sofas (€1,200-1,800) and Kenay (€1,400-2,200).
High: Sancal mainline (€3,500-5,500), Expormim (€2,800-4,500).
Luxury: Poliform Bristol (€8,000+), Minotti Hamilton (€12,000+).
Prices include IVA. Delivery extra (typically €50-150).
Note: Sales periods (Jan/July) can discount 20-40%."
```

### The New Agentic Flow (Updated with FF&E)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SINGLE GEMINI CALL with AGENTIC TOOL CALLING                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: CONSTRUCTION DISCOVERY (BCCA)                               │   │
│  │ LLM: "I need to price 15 construction tasks."                       │   │
│  │                                                                      │   │
│  │ Tool call: discover_bcca(chapter="09", unit="m2", keywords=[...])   │   │
│  │ Tool call: discover_bcca(chapter="01", unit="m2", keywords=[...])   │   │
│  │ Tool call: discover_bcca(chapter="08", unit="ud", keywords=[...])   │   │
│  │                                                                      │   │
│  │ → Returns BCCA candidate pools for construction tasks               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1B: FF&E DISCOVERY (Non-construction)                         │   │
│  │ LLM: "I also need to price furniture and appliances."               │   │
│  │                                                                      │   │
│  │ Tool call: discover_ffe(category="living_room")                     │   │
│  │ Tool call: discover_ffe(category="kitchen_appliances")              │   │
│  │ Tool call: discover_ffe(category="bedroom")                         │   │
│  │                                                                      │   │
│  │ → Returns FF&E items with tier pricing (budget/mid/high/luxury)     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: SELECTION (LLM READS, not scores)                          │   │
│  │ LLM reads all candidates, selects best match for each task          │   │
│  │                                                                      │   │
│  │ "For bathroom tiles: 09ACE00130 (30x30 matches comparable's modern  │   │
│  │  large-format style. Not 10x10 dated, not porcelain exceeds budget)"│   │
│  │ "For demolition: 01DTB00080 (tabiquería ladrillo matches existing)" │   │
│  │ "For outlets: 08EME00120 (Legrand matches mid-range specification)" │   │
│  │                                                                      │   │
│  │ Growing context: LLM now knows selected items and prices            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: QUANTITY CALCULATION                                        │   │
│  │ LLM applies quantity formulas from KG quantity_guidance              │   │
│  │                                                                      │   │
│  │ "Bathroom wall area: 7m perimeter × 2.4m = 16.8m² − 1.6m² door"    │   │
│  │ "Kitchen cabinets: 6.5 ml measured from comparable photos"          │   │
│  │                                                                      │   │
│  │ Growing context: LLM now has quantities for each selected item      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 4: FINAL PACKAGING                                             │   │
│  │ LLM assembles UnifiedEstimate with full reasoning chains            │   │
│  │                                                                      │   │
│  │ - BoQ line items with reasoning (why this item, why this qty)       │   │
│  │ - Room totals                                                        │   │
│  │ - Validation metrics (room attribution, etc.)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2C: BCCA Index Generation (V0.4.7 - NEW)

> **Purpose**: Generate AI-paraphrased 100-character descriptions for ALL 12,565 BCCA items so they can be included in Gemini's context window for semantic matching.

### Why 100-Character Descriptions?

**The Problem**:
- Full BCCA descriptions average ~80 words each
- 12,565 items × 80 words × 1.3 tokens/word = **~1.3M tokens** (exceeds 1M limit!)
- Can't fit full descriptions in context

**The Solution**:
- Use Gemini 2.5 Flash Lite to intelligently compress each description to 100 characters
- Preserves key specs: material, size, finish, quality level
- 12,565 items × 100 chars × 0.3 tokens/char = **~444K tokens** ✓
- Fits comfortably in context with room for KG + FFE + property data

### BCCA Index Format

```
# BCCA INDEX - 12,565 CONSTRUCTION ITEMS
# Format: CODE|UNIT|DESCRIPTION (100 char max)
# Use get_bcca_price(CODE) to fetch final price

09ACE00130|m2|Alicatado azulejo 30x30 gres porcelán C1 UNE-EN paramento
09ACE00140|m2|Alicatado azulejo 40x40 gres esmaltado C2 mortero cola
08PCM00100|ud|Puerta corredera madera maciza 80x210 lacada lisa canto
01DTB00080|m2|Demol tabique ladrillo hueco 7cm manual sin recuperar
...
```

### Generation Script

**File**: `backend/scripts/paraphrase_bcca_descriptions.py`

```python
# Key features:
# - Model: gemini-2.5-flash-lite (fast, cheap)
# - Batch size: 50 items per API call
# - Rate limiting: 30s wait on 429 errors
# - Resume capability: tracks progress in DB
# - Output: desc_100 column in price_book table

PROMPT = """
Summarize the following BCCA construction item description into a concise phrase 
of maximum 100 characters. Focus on key specifications, materials, and purpose. 
Maintain Spanish context. If the description is already short, return it as is.

Description: {description}
Summary (max 100 chars):
"""
```

### Status (2026-01-11)

- **Total items**: 12,565
- **Processing**: ~45 minutes (batch of 50, rate limited)
- **Script**: Running in background
- **Output**: `desc_100` column added to `price_book` table

### Export to Index File

After paraphrasing completes:

```bash
# Export BCCA index for system instruction
sqlite3 /root/puedo_casa/Lean\ MVP/backend/pricing/data/bcca.db \
  "SELECT code || '|' || unit || '|' || desc_100 
   FROM price_book 
   WHERE desc_100 IS NOT NULL
   ORDER BY code" > pricing/data/bcca_index.txt
```

---

## Part 3: Response Schema (UnifiedEstimate)

> **Design Philosophy**: This schema is the CONTRACT between backend and frontend.
> Every field has a specific UI destination. No field exists without a consumer.

```python
# =============================================================================
# pricing/schemas/unified_estimate.py
# =============================================================================
# PURPOSE: Define the EXACT structure of what comes out of the Unified Estimator.
#          This schema serves THREE purposes:
#          1. GEMINI OUTPUT: Constrains what Gemini can return (response_schema)
#          2. BACKEND VALIDATION: Pydantic validates all fields
#          3. FRONTEND CONTRACT: TypeScript types are generated from this
#
# NAMING CONVENTION:
# - snake_case for Python (this file)
# - camelCase for TypeScript/frontend (generated)
# - Field descriptions explain UI destination
# =============================================================================

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
        description="Tasks from KG's REQUIRES relationship. "
                    "These must be done BEFORE the main task."
    )
    triggered_tasks: List[RequiredTask] = Field(
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
        │  (Single Gemini call)│
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
    # InspectionRecommendation:
    #   system: str                    # "electrical" | "plumbing" | "structure"
    #   reason: str                    # "Pre-2002 electrical possible, panel not visible"
    #   urgency: str                   # "before_purchase" | "before_renovation" | "during_renovation"
    #   professional_type: str         # "electricista autorizado" | "fontanero" | "arquitecto técnico"
    #   estimated_cost_range: str      # "€100-200" (inspection cost, not repair)
    
    year_context_summary: YearContextSummary = Field(
        description="Summary of how construction year influenced the estimate. "
                    "UI: 'Contexto del edificio' card"
    )
    # YearContextSummary:
    #   target_year: int
    #   target_year_source: str        # "cadastre" | "estimate"
    #   comparable_years: List[int]
    #   confirmed_issues: List[str]    # Issues confirmed by visual evidence
    #   possible_issues: List[str]     # Issues possible but not confirmed
    #   ruled_out: List[str]           # Issues ruled out by visual evidence
    #   comparables_insight: str       # "1970 comparables likely already upgraded X, Y"
    
    # ═══════════════════════════════════════════════════════════════════
    # PROFESSIONAL DISCLAIMER (V0.4.8)
    # ═══════════════════════════════════════════════════════════════════
    
    disclaimer: Disclaimer = Field(
        description="Legal/professional disclaimer for the estimate. "
                    "UI: Footer of estimate page"
    )
    # Disclaimer:
    #   scope_basis: str               # "Based on VISIBLE changes to match comparables"
    #   hidden_systems: str            # "Hidden systems (electrical, plumbing) may require inspection"
    #   year_context_note: str         # "Construction year (1975) suggests pre-REBT electrical..."
    #   pricing_basis: str             # "Prices from BCCA 2024 Andalucía base"
    #   regional_note: Optional[str]   # "Adjusted +15% for Madrid market"
    #   professional_advice: str       # "We recommend inspection before purchase for items marked..."
    
    # ═══════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════
    
    target_listing_id: int = Field(
        description="ID of the property being estimated"
    )
    comparable_listing_ids: List[int] = Field(
        description="IDs of comparable properties used for gap analysis"
    )
    estimation_date: str = Field(
        description="When this estimate was generated (ISO format)"
    )
    model_version: str = Field(
        default="V0.4.8",
        description="Version of the estimator that produced this"
    )
```

---

## Part 4: Unified Estimator Implementation

> **Design Philosophy**: One massive Gemini call that does everything.
> This class is the HEART of V0.4. It orchestrates the entire estimation pipeline.

```python
# =============================================================================
# pricing/unified_estimator.py
# =============================================================================
# PURPOSE: Orchestrate the entire renovation estimation in ONE Gemini call.
#
# WHY ONE CALL INSTEAD OF MULTIPLE?
# V0.3 split the pipeline into 4 stages (PIR → Gap → Scope → Pricing).
# This caused:
# - Information loss at each handoff
# - Context switching overhead
# - Complex orchestration code
# - Inconsistent reasoning
#
# V0.4 puts EVERYTHING in one Gemini call:
# - Full KG (~214K tokens) in system instruction
# - All knowledge bases (~18K tokens) in system instruction
# - BCCA-speak guide in system instruction
# - discover_bcca as a tool Gemini can call (SQL discovery, LLM selection)
# - All PIRs and photos in user prompt
#
# Gemini then reasons through the entire estimation in one coherent flow.
# =============================================================================

import json
import yaml
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from google import genai
from google.genai import types

from .bcca_discovery import discover_bcca
from .ffe_discovery import discover_ffe
from .schemas.unified_estimate import UnifiedEstimate
from .schemas.estimation_error import EstimationError

# Set up logging for debugging
logger = logging.getLogger(__name__)


class UnifiedEstimator:
    """
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                        V0.4 UNIFIED ESTIMATOR                              ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║  Single massive Gemini call with full context + tools.                    ║
    ║  Combines: gap analysis + scope expansion + pricing                        ║
    ║                                                                           ║
    ║  INPUT:  PIRs (target + comparables) + photos + listing data              ║
    ║  OUTPUT: UnifiedEstimate (gap, scope, BoQ, reasoning, validation)         ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    
    LIFECYCLE:
    1. __init__: Load all knowledge, build system instruction, register tools
    2. estimate(): Build prompt → Call Gemini → Handle tool calls → Parse result
    3. _validate(): Check quality metrics → Fail fast if bad
    """
    
    def __init__(self):
        """
        Initialize the estimator.
        
        WHAT HAPPENS HERE:
        1. Create Gemini client (uses GOOGLE_APPLICATION_CREDENTIALS)
        2. Build massive system instruction (~250K tokens):
           - Role and grounding rules
           - Full Knowledge Graph (683 tasks with dependencies)
           - Energy knowledge (ratings, interventions, climate)
           - Process knowledge (triggers, regulations)
           - Interior design knowledge (styles, finishes)
           - BCCA-speak guide (how to search)
        3. Register discover_bcca as a tool (SQL discovery, LLM reads and selects)
        
        WHY DO THIS AT INIT?
        Building the system instruction is expensive (file I/O, string ops).
        We do it ONCE at init so estimate() is fast for each request.
        """
        # Gemini client - uses Application Default Credentials
        self.client = genai.Client()
        
        # Model selection:
        # - gemini-3-pro-preview: Best reasoning, higher cost, ~1M context
        # - gemini-3-flash-preview: Faster, cheaper, good for testing
        self.model = "gemini-3-pro-preview"
        
        # Build the massive system instruction (runs once)
        logger.info("Building system instruction (~250K tokens)...")
        self.system_instruction = self._build_system_instruction()
        logger.info(f"System instruction built: {len(self.system_instruction):,} chars")
        
        # Register tools (just discover_bcca for now)
        self.tools = self._register_tools()
        
    def _build_system_instruction(self) -> str:
        """
        Build the complete system instruction with ALL knowledge.
        
        WHY SO MUCH IN SYSTEM INSTRUCTION?
        Gemini's system instruction is "cached" - it doesn't count against
        per-request token costs the same way. By putting the KG and KBs here,
        we pay the token cost once, not per-request.
        
        WHAT GETS LOADED:
        1. Template (roles, rules, BCCA-speak guide, quantity formulas)
        2. KG context (~214K tokens) - 683 tasks with full dependencies
        3. Energy knowledge (~6K tokens) - ratings, interventions
        4. Process knowledge (~4K tokens) - triggers, regulations
        5. Interior design knowledge (~8K tokens) - styles, finishes
        
        TOTAL: ~235K tokens
        """
        base_path = Path(__file__).parent.parent.parent
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 1: Load the template
        # ─────────────────────────────────────────────────────────────────
        # This contains: ROLE, GROUNDING RULES, BCCA-SPEAK GUIDE, QUANTITY FORMULAS
        # and placeholder tokens like [KG_CONTEXT_YAML_INSERTED_HERE]
        template_path = Path(__file__).parent / "system_instruction_template.txt"
        instruction = template_path.read_text()
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 2: Insert Knowledge Graph
        # ─────────────────────────────────────────────────────────────────
        # WHY YAML? More token-efficient than JSON, human-readable
        # Contains: 683 tasks with requires[], triggers[], quantity_guidance
        kg_path = base_path / "backend/pricing/kg_context.yaml"
        kg_content = kg_path.read_text()
        instruction = instruction.replace("[KG_CONTEXT_YAML_INSERTED_HERE]", kg_content)
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 3: Insert Energy Knowledge
        # ─────────────────────────────────────────────────────────────────
        # Contains: Rating scale (A-G), age→rating correlation, 
        # intervention impacts, climate zones
        energy_path = base_path / "standards/energy_knowledge.json"
        energy_data = json.loads(energy_path.read_text())
        energy_flat = self._flatten_knowledge(energy_data, "energy")
        instruction = instruction.replace("[ENERGY_KNOWLEDGE_FLATTENED_HERE]", energy_flat)
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 4: Insert Process Knowledge
        # ─────────────────────────────────────────────────────────────────
        # Contains: Renovation triggers, when professional required,
        # community approval rules, regulatory context
        process_path = base_path / "standards/renovation_process_knowledge.json"
        process_data = json.loads(process_path.read_text())
        process_flat = self._flatten_knowledge(process_data, "process")
        instruction = instruction.replace("[PROCESS_KNOWLEDGE_FLATTENED_HERE]", process_flat)
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 5: Insert Interior Design Knowledge
        # ─────────────────────────────────────────────────────────────────
        # Contains: Finish quality tiers, style indicators, 
        # Spanish construction eras, material vocabulary
        design_path = base_path / "standards/interior_design_knowledge.json"
        design_data = json.loads(design_path.read_text())
        design_flat = self._flatten_knowledge(design_data, "design")
        instruction = instruction.replace("[INTERIOR_DESIGN_KNOWLEDGE_FLATTENED_HERE]", design_flat)
        
        return instruction
    
    def _flatten_knowledge(self, data: Dict, kb_type: str) -> str:
        """
        Convert JSON knowledge base to token-efficient YAML.
        
        WHY YAML OVER JSON?
        - No quotes around strings = fewer tokens
        - Indentation-based = fewer braces
        - More human-readable = better for LLM comprehension
        
        Example token savings:
        - JSON: {"key": "value"} = 5 tokens
        - YAML: key: value = 3 tokens
        - 40% reduction adds up over 20K+ tokens
        """
        return yaml.dump(
            data, 
            allow_unicode=True,      # Spanish characters like ñ, á
            default_flow_style=False # Multi-line for readability
        )
    
    def _register_tools(self) -> List[types.Tool]:
        """
        Register both discover_bcca (construction) and discover_ffe (furnishing) tools.
        
        TWO TOOLS FOR TWO COST TYPES:
        - discover_bcca: Construction costs (BCCA database - materials + labor)
        - discover_ffe: Furnishing costs (FFE database - products to purchase)
        
        SAME SQL + LLM SELECTION PATTERN FOR BOTH:
        1. Gemini reasons about what it needs
        2. Gemini calls appropriate discovery tool
        3. Tool returns candidates with descriptions/tiers
        4. Gemini READS and SELECTS with reasoning
        
        WHY SQL DISCOVERY INSTEAD OF EMBEDDINGS?
        1. Data is STRUCTURED: chapters, categories, units, tiers
        2. LLM READS SPANISH: Better than any embedding model
        3. TRANSPARENCY: See candidates, see selection reasoning
        4. SPEED: SQL ~10ms vs embedding ~100ms
        """
        return [
            types.Tool(
                function_declarations=[
                    # ─────────────────────────────────────────────────────────
                    # TOOL 1: discover_bcca (Construction costs)
                    # ─────────────────────────────────────────────────────────
                    types.FunctionDeclaration(
                        name="discover_bcca",
                        description=(
                            "Discover BCCA construction items (materials + labor). "
                            "USE FOR: tiling, painting, plumbing, electrical, demolition, "
                            "sanitaryware (toilets, sinks), windows, doors - anything INSTALLED. "
                            "Returns candidate pool for you to READ and SELECT from."
                        ),
                        parameters={
                            "type": "object",
                            "properties": {
                                "chapter": {
                                    "type": "string",
                                    "description": (
                                        "REQUIRED. BCCA chapter code. "
                                        "01=demolition, 06=plumbing, 08=electrical, "
                                        "09=finishes, 10=carpentry, 13=HVAC, etc."
                                    )
                                },
                                "unit": {
                                    "type": "string",
                                    "description": (
                                        "Optional. Filter by unit: m2, ml, ud, m3."
                                    )
                                },
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": (
                                        "Optional. Spanish keywords to filter descriptions."
                                    )
                                },
                                "price_range": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Optional. [min, max] price range in EUR."
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Optional. Max items to return (default 30)."
                                }
                            },
                            "required": ["chapter"]
                        }
                    ),
                    
                    # ─────────────────────────────────────────────────────────
                    # TOOL 2: discover_ffe (Furnishing costs)
                    # ─────────────────────────────────────────────────────────
                    types.FunctionDeclaration(
                        name="discover_ffe",
                        description=(
                            "Discover FF&E items (Furniture, Fixtures, Equipment). "
                            "USE FOR: sofas, beds, appliances, curtains, rugs, lamps, "
                            "accessories - anything PURCHASED and DELIVERED (not installed). "
                            "Returns items with TIER PRICING (budget/mid/high/luxury). "
                            "Select appropriate tier based on comparable's finish quality."
                        ),
                        parameters={
                                        "type": "object",
                                        "properties": {
                                "category": {
                                                "type": "string",
                                                "description": (
                                        "FFE category. Options: living_room, bedroom, dining, "
                                        "kitchen_appliances, bathroom, lighting, textiles, outdoor."
                                                )
                                            },
                                "item_code": {
                                                "type": "string",
                                    "description": "Optional. Specific FFE item code if known."
                                },
                                "investment_priority": {
                                                "type": "string",
                                                "description": (
                                        "Optional. 'alta' (worth investing), 'media', 'baja' "
                                        "(can be budget without sacrifice)."
                                                )
                                        },
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional. Spanish keywords to filter."
                                    }
                                }
                        }
                    )
                ]
            )
        ]
    
    def _handle_tool_call(self, function_call: types.FunctionCall) -> Dict[str, Any]:
        """
        Execute a tool call from Gemini and return results.
        
        HANDLES TWO TOOLS:
        - discover_bcca: Construction costs (BCCA database)
        - discover_ffe: Furnishing costs (FFE database)
        
        Both follow the same SQL + LLM Selection pattern:
        1. Gemini REASONS about what it needs
        2. Gemini ACTS by calling appropriate tool
        3. We execute SQL: return candidate pool
        4. Gemini READS: examines descriptions/tiers
        5. Gemini SELECTS: picks best match with reasoning
        """
        # ─────────────────────────────────────────────────────────────────
        # TOOL: discover_bcca (Construction)
        # ─────────────────────────────────────────────────────────────────
        if function_call.name == "discover_bcca":
            chapter = function_call.args.get("chapter", "")
            unit = function_call.args.get("unit")
            keywords = function_call.args.get("keywords")
            price_range = function_call.args.get("price_range")
            limit = function_call.args.get("limit", 30)
            
            logger.info(f"Tool call: discover_bcca chapter={chapter}, unit={unit}, "
                       f"keywords={keywords}, limit={limit}")
            
            results = discover_bcca(
                chapter=chapter,
                unit=unit,
                keywords=keywords,
                price_range=tuple(price_range) if price_range else None,
                limit=limit
            )
            
            logger.info(f"BCCA discovery returned {results['metadata']['count']} candidates")
            return results
        
        # ─────────────────────────────────────────────────────────────────
        # TOOL: discover_ffe (Furnishing)
        # ─────────────────────────────────────────────────────────────────
        elif function_call.name == "discover_ffe":
            category = function_call.args.get("category")
            item_code = function_call.args.get("item_code")
            investment_priority = function_call.args.get("investment_priority")
            keywords = function_call.args.get("keywords")
            
            logger.info(f"Tool call: discover_ffe category={category}, "
                       f"item_code={item_code}, priority={investment_priority}")
            
            results = discover_ffe(
                category=category,
                item_code=item_code,
                investment_priority=investment_priority,
                keywords=keywords
            )
            
            logger.info(f"FFE discovery returned {results['metadata']['count']} items")
            return results
        
        else:
            # Unknown tool - shouldn't happen if tools are registered correctly
            logger.error(f"Unknown tool requested: {function_call.name}")
            return {"error": f"Unknown tool: {function_call.name}"}
    
    # ═══════════════════════════════════════════════════════════════════
    # MAIN ESTIMATION METHOD
    # ═══════════════════════════════════════════════════════════════════
    
    def estimate(
        self,
        target_pir: Dict[str, Any],
        target_photos: List[bytes],
        target_listing: Dict[str, Any],
        comparable_pirs: List[Dict[str, Any]]
    ) -> UnifiedEstimate:
        """
        Run the unified estimation pipeline.
        
        THIS IS THE MAIN ENTRY POINT. It orchestrates:
        1. Building the prompt
        2. Calling Gemini with tools enabled
        3. Handling the ReAct loop (tool calls → results → continue)
        4. Parsing and validating the result
        
        Args:
            target_pir: PropertyIntelligenceReport for target property.
                        Generated by the PIR step (V0.3.2).
                        Contains: building profile, room analyses, regulatory, design.
            
            target_photos: Raw photo bytes for target property.
                           Used by Gemini to understand current condition.
                           Limited to 10 photos to stay within token budget.
            
            target_listing: Listing data from Idealista/source.
                            Contains: id, price, size_m2, rooms, energy_rating, year_built.
                            Used for "El Cálculo" in UI.
            
            comparable_pirs: List of PIRs for comparable properties.
                             Typically 1-3 properties from same bracket.
                             Gemini compares these to target to find gaps.
        
        Returns:
            UnifiedEstimate: Complete estimation with:
                - gap_analysis: What needs to change
                - scope: What work will be done (KG-based)
                - bill_of_quantities: How much it costs (BCCA-priced)
                - reasoning_chain: How we got here (explainability)
                - validation: Quality metrics
        
        Raises:
            ValueError: If validation fails (room attribution, KG grounding, etc.)
            json.JSONDecodeError: If Gemini returns invalid JSON
            Exception: For API errors, network issues, etc.
        """
        
        logger.info(f"Starting estimation for listing {target_listing.get('id')}")
        logger.info(f"  - {len(target_photos)} photos")
        logger.info(f"  - {len(comparable_pirs)} comparables")
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 1: Build the user prompt
        # ─────────────────────────────────────────────────────────────────
        # This contains the PIRs and listing data, plus task instructions.
        # System instruction already has KG, KBs, BCCA-speak guide.
        user_prompt = self._build_user_prompt(
            target_pir, target_listing, comparable_pirs
        )
        logger.info(f"User prompt built: {len(user_prompt):,} chars")
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 2: Build content parts (text + images)
        # ─────────────────────────────────────────────────────────────────
        # Gemini accepts multimodal input: text prompts + images
        # Photos help Gemini understand actual condition vs PIR description
        content_parts = [types.Part.from_text(user_prompt)]
        
        # Add photos (limit to 10 to stay within token budget)
        # WHY 10? Each photo is ~1K tokens. 10 photos = ~10K tokens.
        for photo in target_photos[:10]:
            content_parts.append(
                types.Part.from_bytes(data=photo, mime_type="image/jpeg")
            )
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 3: Configure generation
        # ─────────────────────────────────────────────────────────────────
        config = types.GenerateContentConfig(
            # System instruction is the massive context (~250K tokens)
            system_instruction=self.system_instruction,
            
            # Enable discover_bcca tool (SQL discovery, LLM selection)
            tools=self.tools,
            
            # CRITICAL: Request JSON output matching our schema
            # This constrains Gemini to produce valid UnifiedEstimate
            response_mime_type="application/json",
            response_schema=UnifiedEstimate,
            
            # Low temperature = consistent, reproducible results
            # Higher = more creative but less predictable
            temperature=0.2,
            
            # Max output tokens (65K is Gemini's limit for most models)
            # Our schema typically uses 20-30K tokens
            max_output_tokens=65000
        )
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 4: ReAct loop with tool calling
        # ─────────────────────────────────────────────────────────────────
        # ReAct = Reasoning + Acting
        # 
        # Gemini might need to call discover_bcca() multiple times:
        # - First call: discover candidates for finishes (chapter 09)
        # - Second call: discover candidates for demolition (chapter 01)
        # - etc.
        #
        # Each call returns candidates; Gemini READS and SELECTS.
        # We loop until Gemini returns final JSON (no more tool calls).
        
        messages = [types.Content(role="user", parts=content_parts)]
        
        # Max iterations prevents infinite loops (shouldn't happen, but safety)
        max_iterations = 10
        iteration = 0
        
        for iteration in range(max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}")
            
            # Call Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config
            )
            
            # Check if Gemini wants to call a tool
            tool_call_found = False
            
            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_call_found = True
                        
                        # Execute the tool
                        tool_result = self._handle_tool_call(part.function_call)
                        
                        # Add assistant's message (contains the tool call)
                        messages.append(response.candidates[0].content)
                        
                        # Add tool result as "user" message (Gemini convention)
                        messages.append(types.Content(
                            role="user",
                            parts=[types.Part.from_function_response(
                                name=part.function_call.name,
                                response=tool_result
                            )]
                        ))
                        
                        # Only process one tool call per iteration
                        break
            
            if not tool_call_found:
                # No tool call = Gemini has produced final response
                logger.info(f"Final response after {iteration + 1} iterations")
                break
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 5: Parse final response
        # ─────────────────────────────────────────────────────────────────
        # Gemini should have returned JSON matching UnifiedEstimate schema
        result_text = response.text
        logger.info(f"Response received: {len(result_text):,} chars")
        
        try:
            result_dict = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {result_text[:1000]}...")
            raise
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 6: Validate and return
        # ─────────────────────────────────────────────────────────────────
        # Pydantic validates schema; _validate checks quality metrics
        estimate = UnifiedEstimate(
            **result_dict,
            target_listing_id=target_listing.get('id', 0),
            comparable_listing_ids=[p.get('listing_id', 0) for p in comparable_pirs],
            estimation_date=datetime.now().isoformat()
        )
        
        # Fail-fast validation
        self._validate(estimate)
        
        logger.info(f"Estimation complete: {estimate.bill_of_quantities.grand_total:.2f}€")
        return estimate
    
    # ═══════════════════════════════════════════════════════════════════
    # PROMPT BUILDING
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_user_prompt(
        self,
        target_pir: Dict,
        target_listing: Dict,
        comparable_pirs: List[Dict]
    ) -> str:
        """
        Build the user prompt with all property data.
        
        WHY MARKDOWN FORMAT?
        - Gemini understands Markdown well
        - Clear section headers help organize long prompts
        - Easy to read in logs for debugging
        
        STRUCTURE:
        1. Target Property (listing data + PIR)
        2. Comparable Properties (PIRs)
        3. Task Instructions (what to do)
        """
        
        # ─────────────────────────────────────────────────────────────────
        # SECTION 1: Target Property
        # ─────────────────────────────────────────────────────────────────
        prompt = f"""
# TARGET PROPERTY

This is the property we're estimating renovation costs for.

## Listing Data
These are facts from the original listing. Use for validation and "El Cálculo".

- ID: {target_listing.get('id')}
- Asking Price: €{target_listing.get('price', 'unknown'):,}
- Size: {target_listing.get('size_m2', 'unknown')} m²
- Rooms: {target_listing.get('rooms', 'unknown')}
- Energy Rating: {target_listing.get('energy_rating', 'unknown')}
- Year Built: {target_listing.get('year_built', 'unknown')}

## Property Intelligence Report (PIR)
This is our comprehensive analysis of the target property.
Use this to understand current condition, finishes, systems, etc.

{yaml.dump(target_pir, allow_unicode=True, default_flow_style=False)}

# COMPARABLE PROPERTIES

These properties represent the TARGET STATE - what the target property should
become after renovation. Compare each attribute to find gaps.

"""
        
        # ─────────────────────────────────────────────────────────────────
        # SECTION 2: Comparable Properties
        # ─────────────────────────────────────────────────────────────────
        for i, comp in enumerate(comparable_pirs, 1):
            prompt += f"""
## Comparable {i}

{yaml.dump(comp, allow_unicode=True, default_flow_style=False)}

"""
        
        # ─────────────────────────────────────────────────────────────────
        # SECTION 3: Task Instructions
        # ─────────────────────────────────────────────────────────────────
        prompt += """
# YOUR TASK

Complete the following steps to produce a UnifiedEstimate:

## Step 1: COMPARE (Gap Analysis)
Compare the target property to the comparables attribute by attribute:
- Finish quality (countertops, cabinets, flooring, fixtures)
- Systems (electrical, plumbing, HVAC)
- Design style (dated vs contemporary)
- Energy rating (G→C is 4 letters)
- Layout (closed kitchen vs open plan)

For each difference, create a GapComparison entry.
Group into IdentifiedGap entries by room.

## Step 2: IDENTIFY INTERVENTIONS (Scope)
For each gap, identify what KG tasks address it:
- Look up the primary task in the KNOWLEDGE GRAPH (system instruction)
- Check REQUIRES relationships - add prerequisite tasks
- Check TRIGGERS relationships - add follow-on tasks
- Create Intervention entries with full dependency chains

CRITICAL: Every task MUST exist in the KG. Do not invent tasks.

## Step 3: PRICE EACH TASK (BoQ)
For each task in your scope:
1. Reason about what BCCA chapter and unit using BCCA-SPEAK GUIDE
2. Call discover_bcca(chapter=..., unit=..., keywords=[...]) to get candidates
3. READ all candidate descriptions carefully - understand what each item is
4. SELECT the best match and EXPLAIN why (not just lowest price!)
5. Calculate quantity using QUANTITY FORMULAS (system instruction)
6. Create BoQLineItem with:
   - BCCA code and description (from your selection)
   - Quantity and unit (from your calculation)
   - Unit price (from your selection)
   - Total = quantity × unit_price
   - Reasoning (WHY this BCCA item over others, WHY this quantity)

CRITICAL: Every price MUST come from discover_bcca. Do not invent prices.
CRITICAL: READ the candidates. SELECT based on understanding, not position.

## Step 4: PACKAGE RESULT
Output the complete UnifiedEstimate JSON:
- gap_analysis: Your comparisons and identified gaps
- scope: Rooms and interventions with dependencies
- bill_of_quantities: All line items with room_totals and grand_total
- reasoning_chain: Step-by-step record of your analysis
- validation: Calculate the metrics (room_attribution_pct, etc.)

## Quality Requirements
- Room attribution: ≥70% of costs should have specific room (not "General")
- KG grounding: 100% of tasks must exist in Knowledge Graph
- BCCA matching: 100% of prices must come from discover_bcca selections
- Reasoning: Every line item must have reasoning explaining WHY

Good luck! The customer and architect are counting on you.
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════════
    # VALIDATION (FAIL-FAST)
    # ═══════════════════════════════════════════════════════════════════
    
    def _validate(self, estimate: UnifiedEstimate) -> None:
        """
        Run validation gates. Raises ValueError if critical failure.
        
        WHY FAIL-FAST?
        V1 had fallbacks that produced garbage silently. Users saw €53 bathrooms.
        V0.4 has NO FALLBACKS and NO RETRIES. If validation fails, we raise immediately.
        
        When error is raised:
        - Error propagates to API layer
        - API returns structured error to frontend
        - User sees clear error message
        - Developer can debug from logs
        
        NO AUTOMATIC RETRIES. If it fails, investigate why.
        
        VALIDATION GATES:
        These check PROCESS quality, not output reasonableness.
        We don't check "is €15K reasonable for a bathroom" because that's
        subjective and creates bias. We check "did we follow the process".
        """
        
        errors = []
        
        # ─────────────────────────────────────────────────────────────────
        # GATE 1: Room Attribution
        # ─────────────────────────────────────────────────────────────────
        # WHY? If 75% of costs are in "General", the customer can't see
        # what they're paying for per room. This was a V1 problem.
        # TARGET: ≥70% of costs in specific rooms (not "General")
        if estimate.validation.room_attribution_pct < 70:
            errors.append(
                f"ROOM_ATTRIBUTION_LOW: {estimate.validation.room_attribution_pct:.1f}% "
                f"(target: ≥70%). More than 30% of costs in 'General'. "
                f"Review line items and assign to specific rooms."
            )
        
        # ─────────────────────────────────────────────────────────────────
        # GATE 2: KG Grounding
        # ─────────────────────────────────────────────────────────────────
        # WHY? Every task must come from our Knowledge Graph.
        # Invented tasks mean invented dependencies and quantities.
        # TARGET: 100%
        if estimate.validation.kg_grounding_pct < 100:
            errors.append(
                f"KG_GROUNDING_INCOMPLETE: {estimate.validation.kg_grounding_pct:.1f}% "
                f"(target: 100%). Some tasks not found in Knowledge Graph. "
                f"Only KG tasks are allowed."
            )
        
        # ─────────────────────────────────────────────────────────────────
        # GATE 3: BCCA Matching
        # ─────────────────────────────────────────────────────────────────
        # WHY? Every price must come from discover_bcca selections.
        # Invented prices mean hallucinated costs.
        # TARGET: 100% (relaxed to 90% to allow some flexibility)
        if estimate.validation.bcca_match_pct < 90:
            errors.append(
                f"BCCA_MATCH_LOW: {estimate.validation.bcca_match_pct:.1f}% "
                f"(target: ≥90%). Some tasks missing valid BCCA codes. "
                f"Review discovery calls and selection reasoning."
            )
        
        # ─────────────────────────────────────────────────────────────────
        # GATE 4: Non-Empty
        # ─────────────────────────────────────────────────────────────────
        # WHY? An empty estimate is useless.
        if estimate.validation.total_line_items == 0:
            errors.append(
                "EMPTY_ESTIMATE: No line items generated. "
                "Check if PIRs have enough detail to identify gaps."
            )
        
        # ─────────────────────────────────────────────────────────────────
        # GATE 5: Reasonable Total (sanity check, not hard rule)
        # ─────────────────────────────────────────────────────────────────
        # WHY? Catch obvious errors like €53 bathrooms or €5M studios.
        # This is a SOFT check - we log but don't fail.
        if estimate.bill_of_quantities.grand_total < 1000:
            logger.warning(
                f"SANITY_CHECK: Grand total (€{estimate.bill_of_quantities.grand_total:,.2f}) "
                f"seems very low. Verify this is correct."
            )
        
        if estimate.bill_of_quantities.grand_total > 500000:
            logger.warning(
                f"SANITY_CHECK: Grand total (€{estimate.bill_of_quantities.grand_total:,.2f}) "
                f"seems very high. Verify this is correct."
            )
        
        # ─────────────────────────────────────────────────────────────────
        # RAISE IF ANY ERRORS
        # ─────────────────────────────────────────────────────────────────
        if errors:
            error_msg = "Validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Validation passed ✓")
```

---

## Part 5: View Formatting (Customer & Architect)

> **Design Philosophy**: The UnifiedEstimate is the raw data.
> These formatters transform it into views optimized for each audience.

```python
# =============================================================================
# pricing/format_views.py
# =============================================================================
# PURPOSE: Transform UnifiedEstimate into audience-specific views.
#
# WHY TWO VIEWS?
# - CUSTOMER: Wants simple, understandable breakdown in layman terms
#   "How much per room?" "What do I get?" - NOT BCCA codes
# - ARCHITECT: Wants full technical detail for planning and execution
#   BCCA codes, quantities, units, reasoning chains - NO SIMPLIFICATION
#
# WHEN TO USE:
# - After UnifiedEstimator.estimate() returns successfully
# - These are OPTIONAL - frontend can also consume UnifiedEstimate directly
# - Useful to reduce payload size for mobile
# =============================================================================

from typing import Dict, Any, List
from .schemas.unified_estimate import UnifiedEstimate


# =============================================================================
# COST CALCULATION HELPERS
# =============================================================================
# WHY SEPARATE CALCULATION?
# UnifiedEstimate.grand_total is PEM (Presupuesto Ejecución Material) only.
# We need to add contractor overhead and taxes for final price.

def calculate_full_cost(pem: float, iva_rate: float = 0.10) -> Dict[str, float]:
    """
    Calculate full cost from PEM (Material Execution Budget).
    
    SPANISH CONSTRUCTION COST BREAKDOWN:
    - PEM: Raw material + labor costs from BCCA
    - GG (Gastos Generales): 13% of PEM - contractor overhead
    - BI (Beneficio Industrial): 6% of PEM - contractor profit
    - PEC = PEM + GG + BI (Presupuesto Ejecución Contrata)
    - IVA: 10% for residential renovation, 21% otherwise
    - TOTAL = PEC + IVA
    
    WHY THESE PERCENTAGES?
    These are standard Spanish public works percentages.
    Private contractors may vary, but these are reasonable estimates.
    """
    gastos_generales = pem * 0.13    # 13% overhead
    beneficio_industrial = pem * 0.06  # 6% profit
    
    pec = pem + gastos_generales + beneficio_industrial
    
    iva = pec * iva_rate  # 10% for residential, 21% for commercial
    
    total = pec + iva
    
    return {
        "pem": round(pem, 2),
        "gastos_generales": round(gastos_generales, 2),
        "beneficio_industrial": round(beneficio_industrial, 2),
        "pec": round(pec, 2),
        "iva": round(iva, 2),
        "iva_rate": iva_rate,
        "total": round(total, 2)
    }


# =============================================================================
# CUSTOMER VIEW
# =============================================================================

def format_customer_view(
    estimate: UnifiedEstimate,
    asking_price: float,
    target_price: float
) -> Dict[str, Any]:
    """
    Format estimate for customer display in mobile modal.
    
    DESIGN PRINCIPLE: Simplicity and trust.
    - Show WHAT they're getting (not technical details)
    - Show HOW MUCH per room (not BCCA codes)
    - Show THE MATH (investment vs value)
    - Show TRANSFORMATION (energy, style)
    
    UI DESTINATION: BracketAnalysisModal.tsx
    
    Args:
        estimate: The raw UnifiedEstimate from estimator
        asking_price: Listing price (€280,000)
        target_price: Comparable bracket average (€410,000)
    
    Returns:
        Dict optimized for mobile modal rendering
    """
    
    # Calculate full cost with GG, BI, IVA
    cost = calculate_full_cost(estimate.bill_of_quantities.grand_total)
    
    # ─────────────────────────────────────────────────────────────────
    # THE MATH SECTION
    # ─────────────────────────────────────────────────────────────────
    # UI: "El Cálculo" card at top of modal
    the_math = {
        "asking_price": asking_price,                           # "Precio Pedido"
        "renovation_cost": cost["total"],                       # "+ Reforma"
        "total_investment": asking_price + cost["total"],       # "= Tu Inversión"
        "target_price": target_price,                           # "Valor Objetivo"
        "margin": target_price - (asking_price + cost["total"]), # "= Margen Potencial"
        "margin_positive": target_price > (asking_price + cost["total"])
    }
    
    # ─────────────────────────────────────────────────────────────────
    # TRANSFORMATION SECTION
    # ─────────────────────────────────────────────────────────────────
    # UI: "Transformación" card showing before→after
    # Extract energy gap from comparisons
    energy_comparison = next(
        (c for c in estimate.gap_analysis.comparisons 
         if "energy" in c.attribute.lower()),
        None
    )
    
    transformation = {
        "energy": {
            "from": energy_comparison.target_value if energy_comparison else "?",
            "to": energy_comparison.comparable_value if energy_comparison else "?",
            "letters_improved": 4  # Placeholder - should calculate from actual values
        } if energy_comparison else None,
        "style": {
            "from": "Tradicional 1970s",  # Should extract from PIR
            "to": "Contemporáneo"
        },
        "scope_level": _determine_scope_level(estimate)
    }
    
    # ─────────────────────────────────────────────────────────────────
    # QUÉ INCLUYE (What's included)
    # ─────────────────────────────────────────────────────────────────
    # UI: Bullet list of high-priority items
    # Take gap descriptions and make them customer-friendly
    included_items = [
        gap.description
        for gap in estimate.gap_analysis.identified_gaps
        if gap.priority in ["high", "medium"]
    ]
    
    # ─────────────────────────────────────────────────────────────────
    # DESGLOSE POR ZONA (Breakdown by room)
    # ─────────────────────────────────────────────────────────────────
    # UI: Expandable accordions per room
    room_breakdown = []
    for rt in estimate.bill_of_quantities.room_totals:
        # Get line items for this room (for expanded view)
        room_items = [
            {
                "name": li.task_name,  # Customer-friendly name
                "total": li.total
            }
            for li in estimate.bill_of_quantities.line_items
            if li.room_id == rt.room_id
        ]
        
        # Map room_type to Spanish display name
        room_name_map = {
            "bathroom": "Baño",
            "kitchen": "Cocina",
            "bedroom": "Dormitorio",
            "living": "Salón",
            "hallway": "Pasillo",
            "exterior": "Exterior",
            "general": "Instalaciones"
        }
        
        room_breakdown.append({
            "room_id": rt.room_id,
            "room_name": room_name_map.get(rt.room_type, rt.room_type.title()),
            "total": rt.total,
            "item_count": len(room_items),
            "items": room_items  # For expanded view
        })
    
    # ─────────────────────────────────────────────────────────────────
    # COST SUMMARY (PEM + overhead)
    # ─────────────────────────────────────────────────────────────────
    # UI: Breakdown at bottom of cost section
    cost_summary = {
        "pem": cost["pem"],
        "gastos_generales": cost["gastos_generales"],
        "beneficio_industrial": cost["beneficio_industrial"],
        "iva": cost["iva"],
        "iva_rate_display": f"{int(cost['iva_rate'] * 100)}%",
        "total": cost["total"]
    }
    
    # ─────────────────────────────────────────────────────────────────
    # TIMELINE
    # ─────────────────────────────────────────────────────────────────
    # UI: Visual timeline with phase bars
    timeline = _estimate_timeline(estimate)
    
    # ─────────────────────────────────────────────────────────────────
    # VIEWING CHECKLIST
    # ─────────────────────────────────────────────────────────────────
    # UI: Checkboxes for property viewing
    checklist = _generate_viewing_checklist(estimate)
    
    return {
        "the_math": the_math,
        "transformation": transformation,
        "included_items": included_items,
        "room_breakdown": room_breakdown,
        "cost_summary": cost_summary,
        "timeline": timeline,
        "viewing_checklist": checklist,
        
        # Metadata
        "estimation_date": estimate.estimation_date,
        "model_version": estimate.model_version
    }


def _determine_scope_level(estimate: UnifiedEstimate) -> str:
    """
    Determine renovation scope level for display.
    
    WHY? Customers want a simple label like "Reforma integral"
    instead of counting interventions.
    """
    total = estimate.bill_of_quantities.grand_total
    room_count = len(estimate.scope.rooms)
    
    if total > 80000 or room_count >= 4:
        return "Reforma integral"
    elif total > 40000 or room_count >= 2:
        return "Reforma parcial"
    else:
        return "Actualización puntual"


def _estimate_timeline(estimate: UnifiedEstimate) -> List[Dict[str, Any]]:
    """
    Estimate renovation timeline based on scope.
    
    WHY ESTIMATE?
    Real timelines depend on contractor availability, permits, etc.
    This is a rough guide based on typical renovation phases.
    """
    # Simplified timeline based on total cost
    total = estimate.bill_of_quantities.grand_total
    
    if total > 80000:
        return [
            {"phase": "Demolición", "weeks": "S1-2", "duration": 2},
            {"phase": "Instalaciones", "weeks": "S3-5", "duration": 3},
            {"phase": "Albañilería", "weeks": "S6-8", "duration": 3},
            {"phase": "Acabados", "weeks": "S9-12", "duration": 4},
            {"phase": "Repasos", "weeks": "S13-14", "duration": 2}
        ]
    elif total > 40000:
        return [
            {"phase": "Demolición", "weeks": "S1", "duration": 1},
            {"phase": "Instalaciones", "weeks": "S2-3", "duration": 2},
            {"phase": "Acabados", "weeks": "S4-7", "duration": 4},
            {"phase": "Repasos", "weeks": "S8", "duration": 1}
        ]
    else:
        return [
            {"phase": "Preparación", "weeks": "S1", "duration": 1},
            {"phase": "Ejecución", "weeks": "S2-3", "duration": 2},
            {"phase": "Repasos", "weeks": "S4", "duration": 1}
        ]


def _generate_viewing_checklist(estimate: UnifiedEstimate) -> List[str]:
    """
    Generate viewing checklist based on identified gaps.
    
    WHY? Help customers know what to look for when visiting the property.
    """
    checklist = []
    
    # Always include basics
    checklist.append("Verificar estado general de paredes y techos")
    
    # Add based on gaps
    for gap in estimate.gap_analysis.identified_gaps:
        desc_lower = gap.description.lower()
        
        if "ventana" in desc_lower or "window" in desc_lower:
            checklist.append("Verificar estado de ventanas y cierres")
        if "eléctric" in desc_lower or "electric" in desc_lower:
            checklist.append("Localizar cuadro eléctrico y verificar estado")
        if "baño" in desc_lower or "bathroom" in desc_lower:
            checklist.append("Revisar humedades y ventilación en baño")
        if "cocina" in desc_lower or "kitchen" in desc_lower:
            checklist.append("Comprobar instalaciones de agua y gas en cocina")
        if "suelo" in desc_lower or "floor" in desc_lower:
            checklist.append("Revisar estado del suelo en todas las estancias")
    
    # Deduplicate and limit
    checklist = list(dict.fromkeys(checklist))[:6]
    
    return checklist


# =============================================================================
# ARCHITECT VIEW
# =============================================================================

def format_architect_view(estimate: UnifiedEstimate) -> Dict[str, Any]:
    """
    Format estimate for architect/contractor export.
    
    DESIGN PRINCIPLE: Full technical detail, nothing hidden.
    - Every BCCA code for proper budgeting
    - Every quantity with unit for measurement verification
    - Every reasoning chain for audit trail
    - Dependencies for scheduling
    
    UI DESTINATION: PDF/JSON export via "Exportar para Arquitecto" button
    
    OUTPUT FORMAT: Matches typical Spanish BoQ (Presupuesto) structure
    """
    
    return {
        # ─────────────────────────────────────────────────────────────
        # PROJECT SCOPE (For project planning)
        # ─────────────────────────────────────────────────────────────
        "project_scope": {
            "total_interventions": len(estimate.scope.interventions),
            "total_rooms": len(estimate.scope.rooms),
            
            "interventions": [
                {
                    "id": i.intervention_id,
                    "kg_task": i.kg_task_id,           # KG reference for traceability
                    "description": i.description,
                    "dependencies": {
                        "requires": [             # Must do these BEFORE
                            {"task_id": r.task_id, "reason": r.reason}
                            for r in i.required_tasks
                        ],
                        "triggers": [             # Typically do these AFTER
                            {"task_id": t.task_id, "reason": t.reason}
                            for t in i.triggered_tasks
                        ]
                    }
                }
                for i in estimate.scope.interventions
            ],
            
            "rooms": [
                {
                    "room_id": r.room_id,
                    "room_type": r.room_type,
                    "estimated_m2": r.estimated_m2,
                    "intervention_ids": r.intervention_ids
                }
                for r in estimate.scope.rooms
            ]
        },
        
        # ─────────────────────────────────────────────────────────────
        # BILL OF QUANTITIES (For budgeting and execution)
        # ─────────────────────────────────────────────────────────────
        # This is the core of what architects need
        "bill_of_quantities": {
            "line_items": [
                {
                    # Room attribution
                    "room": li.room_id,
                    
                    # Task identification
                    "task_id": li.task_id,    # KG reference
                    "task_name": li.task_name,
                    
                    # BCCA pricing (CRITICAL for contractors)
                    "bcca_code": li.bcca_code,
                    "bcca_description": li.bcca_description,
                    
                    # Quantities (CRITICAL for measurement)
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_price": li.unit_price,
                    "total": li.total,
                    
                    # Reasoning (for audit and verification)
                    "reasoning": li.reasoning
                }
                for li in estimate.bill_of_quantities.line_items
            ],
            
            # Subtotals by room
            "room_subtotals": {
                rt.room_type: {
                    "room_id": rt.room_id,
                    "total": rt.total
                }
                for rt in estimate.bill_of_quantities.room_totals
            },
            
            # Summary
            "pem": estimate.bill_of_quantities.grand_total,
            "full_cost": calculate_full_cost(estimate.bill_of_quantities.grand_total)
        },
        
        # ─────────────────────────────────────────────────────────────
        # REASONING AUDIT (For verification and debugging)
        # ─────────────────────────────────────────────────────────────
        "reasoning_audit": [
            {
                "step": step.step_number,
                "action": step.action,
                "evidence": step.evidence,
                "conclusion": step.conclusion
            }
            for step in estimate.reasoning_chain
        ],
        
        # ─────────────────────────────────────────────────────────────
        # VALIDATION METRICS (For QA)
        # ─────────────────────────────────────────────────────────────
        "validation_metrics": {
            "room_attribution_pct": estimate.validation.room_attribution_pct,
            "kg_grounding_pct": estimate.validation.kg_grounding_pct,
            "bcca_match_pct": estimate.validation.bcca_match_pct,
            "total_line_items": estimate.validation.total_line_items,
            "total_rooms": estimate.validation.total_rooms
        },
        
        # ─────────────────────────────────────────────────────────────
        # METADATA
        # ─────────────────────────────────────────────────────────────
        "metadata": {
            "target_listing_id": estimate.target_listing_id,
            "comparable_listing_ids": estimate.comparable_listing_ids,
            "estimation_date": estimate.estimation_date,
            "model_version": estimate.model_version,
            "pricing_source": "BCCA 2024",
            "disclaimer": (
                "Este presupuesto es orientativo y está basado en precios estándar "
                "de la Base de Costes de la Construcción de Andalucía (BCCA). "
                "Los precios finales pueden variar según el contratista, la ubicación, "
                "y las condiciones específicas del inmueble."
            )
        }
    }
```

---

## Part 6: Token Budget

> **V0.4.7 UPDATE**: Full BCCA + FFE indexes in context. Higher token usage but MUCH better semantic matching.

```
SYSTEM INSTRUCTION (V0.4.7 - Full Context Architecture):
├── Role + Grounding Rules:        ~3,000 tokens
├── Knowledge Graph (full):      ~214,000 tokens
├── ═══════════════════════════════════════════════
├── BCCA INDEX (12,565 items)    ~444,000 tokens  ⭐ NEW
│   └── AI-paraphrased 100-char descriptions
│   └── Created by Gemini 2.5 Flash Lite
├── ═══════════════════════════════════════════════
├── FFE INDEX (202 items)         ~12,000 tokens  ⭐ NEW
│   └── Full tier pricing + brands
│   └── Style matching tags
├── ═══════════════════════════════════════════════
├── Supporting Knowledge:
│   ├── Energy Knowledge:          ~6,000 tokens
│   ├── Process Knowledge:         ~4,000 tokens
│   ├── Interior Design:           ~8,000 tokens
│   ├── Quantity Formulas:         ~2,000 tokens
│   └── FFE Style Matching:        ~4,000 tokens
├── ═══════════════════════════════════════════════
└── TOTAL SYSTEM INSTRUCTION:    ~697,000 tokens

USER PROMPT:
├── Target PIR + listing:          ~5,000 tokens
├── Photos (10 images):           ~10,000 tokens
├── Comparable PIRs (3):          ~15,000 tokens
└── TOTAL USER PROMPT:            ~30,000 tokens

TOOL RESPONSES (Simplified - Price Lookup Only):
├── ~30 get_bcca_price calls:      ~3,000 tokens (just prices, not candidates)
└── TOTAL TOOL:                    ~3,000 tokens

OUTPUT:
├── UnifiedEstimate JSON:         ~30,000 tokens (target)
└── MAX OUTPUT:                    65,000 tokens (if needed)

═══════════════════════════════════════════════════════════════════════
GRAND TOTAL: ~730K input + 30K output = ~760K tokens
GEMINI 2.5 PRO LIMIT: 1M input + 65K output
HEADROOM: ~240K tokens (24% buffer) ✓
═══════════════════════════════════════════════════════════════════════

WHY THIS IS WORTH THE TOKENS:
─────────────────────────────
• Gemini SEES all 12,565 BCCA items → semantic matching, not query guessing
• Gemini SEES all 202 FFE items with pricing → no tool calls needed
• Better matches = more accurate estimates = happier customers
• Fewer tool calls = faster execution = lower latency
```

---

## Part 7: Implementation Checklist (V0.4.8 - 9-Phase Architecture)

> **Updated**: 2026-01-11 for 9-Phase Orchestrator with Cached Context
> **DEFINITION OF COMPLETE**: Press "Make Packages" → Full pipeline runs → 3 packages with images displayed

---

## 🎯 AUTONOMOUS IMPLEMENTATION EXECUTION PLAN

**TEST LISTING**: `listing_id = 12`

**CRITICAL**: This implementation will be done autonomously with NO user input required.
The user will only be contacted when the implementation is COMPLETE and TESTED.

### What Will Happen:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AUTONOMOUS IMPLEMENTATION SEQUENCE                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. IMPLEMENT (Phases 0-14B)                                                 │
│     → Create all files as per the plan                                       │
│     → No user input needed                                                   │
│                                                                              │
│  2. CLEAR TEST DATA                                                          │
│     → Clear V0.4.8 tables for listing 12                                    │
│     → KEEP listing_comparables (save Casafari API calls)                    │
│     → Command: DELETE FROM photo_clusters_v048 WHERE listing_id=12;         │
│                DELETE FROM property_intelligence_reports_v048 WHERE ...;     │
│                DELETE FROM unified_estimates_v048 WHERE listing_id=12;       │
│                DELETE FROM package_generation_progress WHERE listing_id=12;  │
│                                                                              │
│  3. RUN TERMINAL TEST                                                        │
│     → python scripts/test_v048_pipeline.py --listing-id 12 --verbose        │
│     → Watch foreground logs                                                  │
│     → Logs show each step, checkpoints, timing                              │
│                                                                              │
│  4. IF TEST FAILS                                                            │
│     → Read error from logs                                                   │
│     → Fix the code                                                           │
│     → Resume from checkpoint: --from-checkpoint <last_good_checkpoint>      │
│     → Repeat until SUCCESS                                                   │
│                                                                              │
│  5. WHEN TEST PASSES                                                         │
│     → Verify output:                                                         │
│       ✓ 3 packages generated (fast_sell, fair_market, out_of_market)        │
│       ✓ Each package has: price, margin, timeline, before/after images      │
│       ✓ All checkpoints saved to DB                                         │
│       ✓ All images uploaded to Supabase storage                             │
│                                                                              │
│  6. TELL USER: "READY FOR FRONTEND TEST"                                     │
│     → User opens /listing/12                                               │
│     → User clicks "Make Packages"                                           │
│     → User sees 3 packages with all details                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Test Success Criteria:

```
============================================================
✅ V0.4.8 PIPELINE TEST - LISTING 12 - SUCCESS
============================================================

Checkpoints completed: 8/8
  ✓ clustering_complete
  ✓ year_estimation_complete
  ✓ pir_target_complete
  ✓ pir_comparables_complete
  ✓ estimate_fast_sell_complete
  ✓ estimate_fair_market_complete
  ✓ estimate_out_of_market_complete
  ✓ visuals_complete

Packages generated: 3
  - fast_sell:       €XX,XXX (margin: €XX,XXX)
  - fair_market:     €XX,XXX (margin: €XX,XXX)
  - out_of_market:   €XX,XXX (margin: €XX,XXX)

Images uploaded: 6 (3 before + 3 after)

Total execution time: X minutes

============================================================
🚀 READY FOR FRONTEND TEST
   Open: http://localhost:3000/listing/12
   Click: "Make Packages" button
============================================================
```

### What User Will See After Implementation:

1. **Message from me**: "V0.4.8 implementation complete. Terminal test passed for listing 12. Ready for frontend test."

2. **Instructions**:
   - Open http://localhost:3000/listing/12
   - Comparables should already be there
   - Click "Make Packages"
   - Watch progress bar
   - See 3 package cards appear
   - Click each card to see full modal
   - Verify "Contexto del Edificio" card on listing tab

---

---

### 🎯 END-TO-END FLOW: "MAKE PACKAGES" BUTTON → UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPLETE V0.4.8 PIPELINE                                 │
│                                                                              │
│  USER ACTION: Clicks "Make Packages" button (after "Get Comparables")       │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 0: PREREQUISITES (already done by this point)                          │
│  ──────────────────────────────────────────────────                          │
│  ✓ Listing scraped (Idealista/Universal parser)                             │
│  ✓ Photos stored in Supabase                                                │
│  ✓ "Get Comparables" button pressed → 9 comparables from Casafari           │
│  ✓ Comparable photos fetched (2-call strategy, up to 20 each)               │
│                                                                              │
│  STEP 1: CLUSTERING (Zero-Shot)                                              │
│  ──────────────────────────────────                                          │
│  → Cluster TARGET photos into rooms                                         │
│  → Cluster EACH COMPARABLE's photos into rooms                              │
│  → Detect AI renders / virtual staging                                       │
│  → Output: PhotoClusters for target + 9 comparables                         │
│                                                                              │
│  STEP 2: SMART YEAR ESTIMATION (Cadastre)                                    │
│  ─────────────────────────────────────────                                   │
│  → Call smart_year_estimation() for TARGET:                                 │
│    Priority: listing.construction_year → cadastre(coords) → cadastre(addr)  │
│           → street_sampling → neighborhood_sampling → visual_estimate        │
│  → For COMPARABLES: Use construction_year from Casafari (already have it)   │
│  → Output: year_built + year_source for each property                       │
│                                                                              │
│  Code Location: backend/pipeline/steps/analyze_room.py → smart_year_estimation()
│                                                                              │
│  STEP 3: PIR GENERATION (Property Intelligence Reports)                      │
│  ──────────────────────────────────────────────────────                      │
│  → Generate PIR for TARGET (with year_context, all rooms)                   │
│  → Generate PIR for EACH COMPARABLE (same approach)                         │
│  → Output: 1 target_pir + 9 comparable_pirs                                 │
│                                                                              │
│  STEP 4: BUCKET COMPARABLES                                                  │
│  ─────────────────────────────                                               │
│  → Group comparable_pirs by price_bucket:                                   │
│    • fast_sell_pirs (3 comparables)                                         │
│    • fair_market_pirs (3 comparables)                                       │
│    • out_of_market_pirs (3 comparables)                                     │
│                                                                              │
│  STEP 5: 9-PHASE ESTIMATOR (×3 packages)                                     │
│  ────────────────────────────────────────                                    │
│  → FOR EACH BUCKET:                                                          │
│    → Run 9-phase estimator with:                                            │
│      • target_pir                                                           │
│      • comparable_pirs from that bucket                                     │
│      • cached context (BCCA, FFE, KG, knowledge bases)                      │
│    → Output: UnifiedEstimate per bucket                                     │
│  → Total: 3 UnifiedEstimates (fast_sell, fair_market, out_of_market)        │
│                                                                              │
│  STEP 6: VISUALS (V1-V4 Image Generation)                                    │
│  ─────────────────────────────────────────                                   │
│  → FOR EACH PACKAGE:                                                         │
│    V1: Defurnish target photos (if needed)                                  │
│    V2: Select best "before" photo (kitchen focus)                           │
│    V3: Generate rendering prompt from estimate scope                        │
│    V4: Render "after" image using Imagen/Gemini                             │
│  → Output: Before/After images per package                                  │
│                                                                              │
│  STEP 7: FORMAT FOR UI                                                       │
│  ─────────────────────────                                                   │
│  → Format each UnifiedEstimate for Customer View                            │
│  → Attach before/after images                                               │
│  → Calculate margins, durations                                             │
│  → Output: 3 formatted packages ready for display                           │
│                                                                              │
│  STEP 8: STORE & RESPOND                                                     │
│  ───────────────────────                                                     │
│  → Store estimates in database                                              │
│  → Store images in Supabase storage                                         │
│  → Return to frontend                                                        │
│                                                                              │
│  UI RESULT:                                                                  │
│  ──────────                                                                  │
│  → 3 Package Cards displayed (Fast Sell, Fair Market, Out of Market)        │
│  → Each card shows: price, margin, duration, before/after thumbnail        │
│  → Click card → Full modal with all details                                 │
│  → "Export for Architect" button → PDF/JSON                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 📂 COMPLETE FILE INVENTORY (What Gets Created/Modified)

```
Lean MVP/backend/
├── pipeline/
│   ├── package_orchestrator.py         🆕 NEW - Main entry point
│   ├── multi_phase_estimator.py        🆕 NEW - 9-phase engine
│   ├── context_builder.py              🆕 NEW - Build cached context
│   ├── cadastre_client.py              📝 UPDATE - Add smart_year_estimation from analyze_room.py
│   ├── gemini_client.py                ✅ EXISTS - Update for caching
│   │
│   ├── steps/
│   │   ├── property_intelligence.py    📝 UPDATE - Add year_context
│   │   ├── cluster_photos.py           🆕 NEW - Extract P1 from photo_analysis.py
│   │   ├── cluster_all_properties.py   🆕 NEW - Cluster target+comparables
│   │   ├── generate_all_pirs.py        🆕 NEW - PIR for all properties
│   │   ├── generate_package_visuals.py 🆕 NEW - Before/after per package
│   │   ├── visuals.py                  ✅ EXISTS - V1-V4 (no changes)
│   │   │
│   │   ├── comparable_workflow.py      ❌ DELETE
│   │   ├── analyze_comparables.py      📝 UPDATE - Keep Casafari, delete analysis
│   │   ├── photo_analysis.py           📝 EXTRACT P1 → cluster_photos.py, DELETE rest
│   │   ├── assess_uniclass.py          ❌ DELETE
│   │   ├── verify_rules.py             ❌ DELETE
│   │   ├── map_to_scope.py             ❌ DELETE
│   │   ├── scope_search.py             ❌ DELETE
│   │   ├── scope.py                    ❌ DELETE
│   │   ├── estimate_timeline.py        ❌ DELETE
│   │   ├── architect.py                ❌ DELETE
│   │   ├── analyze_room.py             📝 EXTRACT smart_year_estimation → cadastre_client.py, DELETE rest
│   │   ├── comparative_gap_analysis.py ❌ DELETE
│   │   ├── architect_condition.py      ❌ DELETE (old A1/A2/A3)
│   │   ├── architect_difficulty.py     ❌ DELETE (old A1/A2/A3)
│   │   ├── smart_m2.py                 📝 REVIEW (merge into PIR or keep?)
│   │   ├── context_research.py         ✅ KEEP (Research Tab - out of scope)
│   │   └── text_analysis.py            ✅ KEEP (Viewing Tab checklist - review later)
│   │
│   ├── schemas/
│   │   ├── property_intelligence.py    📝 UPDATE - V0.4.8 schema
│   │   ├── phase_outputs.py            🆕 NEW - 9-phase schemas
│   │   ├── unified_estimate.py         🆕 NEW - Final output schema
│   │   └── estimation_error.py         🆕 NEW - Error schema
│   │
│   └── phase_prompts/                  🆕 NEW FOLDER
│       ├── phase_1_scope_definition.txt
│       ├── phase_2_scope_check.txt
│       ├── phase_3_work_phases.txt
│       ├── phase_4_boq_check.txt
│       ├── phase_5_pricing_strategy.txt
│       ├── phase_6_pricing_adjustments.txt
│       ├── phase_7_timeline_validation.txt
│       ├── phase_8_energy_check.txt
│       └── phase_9_final_sanity.txt
│
├── pricing/
│   ├── bcca_price_lookup.py            🆕 NEW - Simple code→price lookup
│   │
│   ├── data/
│   │   ├── bcca_index.txt              🆕 NEW - 12,565 items formatted
│   │   ├── ffe_index.txt               🆕 NEW - 202 items formatted
│   │   ├── bcca.db                     ✅ EXISTS - Has desc_100
│   │   └── ffe.db                      ✅ EXISTS - 202 items
│   │
│   ├── system_instruction_base.txt     🆕 NEW - Role + rules
│   │
│   ├── renovation_resolver.py          ❌ DELETE
│   ├── kg_estimator.py                 ❌ DELETE
│   ├── room_inference.py               ❌ DELETE
│   ├── bcca_embeddings.npy             ❌ DELETE
│   └── system_instruction.txt          ❌ DELETE
│
├── clients/
│   └── casafari_client.py              ✅ EXISTS - No changes
│
├── scraper/
│   ├── parsers/idealista.py            ✅ EXISTS - Updated for energy_rating
│   ├── parsers/gemini_universal.py     ✅ EXISTS - Updated for energy_rating
│   ├── normalizer.py                   ✅ EXISTS - Updated
│   └── rules.py                        ✅ EXISTS - Updated
│
├── scripts/
│   ├── export_bcca_index.py            🆕 NEW - Generate bcca_index.txt
│   ├── export_ffe_index.py             🆕 NEW - Generate ffe_index.txt
│   ├── paraphrase_bcca_descriptions.py ✅ EXISTS - DONE
│   ├── build_ffe_database.py           ✅ EXISTS - DONE
│   └── parse_ffe_research.py           ✅ EXISTS - DONE
│
├── api/routes/
│   └── renovation.py                   📝 UPDATE - Add /make-packages
│
└── schema.py                           ✅ EXISTS - Updated for energy_rating

supabase/migrations/
├── 009_v048_pir_tables.sql             🆕 NEW - Enhanced PIRs
└── 010_v048_estimates.sql              🆕 NEW - Package estimates

Lean MVP/frontend/src/
├── components/
│   ├── PackageGenerator.tsx            📝 UPDATE - Wire Make Packages
│   ├── PackageCard.tsx                 📝 UPDATE - Display 3 packages
│   ├── PackageModal.tsx                📝 UPDATE - Inspection recs, disclaimer
│   └── BuildingContextCard.tsx         🆕 NEW - Contexto del Edificio
│
└── app/listing/[id]/
    └── page.tsx                        📝 UPDATE - Add BuildingContextCard

```

**Legend:**
- 🆕 NEW = Create this file
- 📝 UPDATE = Modify existing file
- ✅ EXISTS = Already done/working, no changes
- ❌ DELETE = Move to `/deprecated/` folder

**File Counts:**
- New files to create: **25** (including cluster_photos.py extraction)
- Files to update/extract: **13** (photo_analysis→cluster, analyze_room→cadastre, etc.)
- Files to delete: **17** (after extraction)
- Files to keep unchanged: **8** (Casafari, visuals, context_research, text_analysis, etc.)

**CRITICAL EXTRACTIONS:**
1. `photo_analysis.py` → Extract P1 clustering → `cluster_photos.py`
2. `analyze_room.py` → Extract smart_year_estimation → `cadastre_client.py`
3. `comparable_workflow.py` → Extract cluster_photos_direct → `cluster_photos.py`

---

### ✅ COMPLETED PREREQUISITES

#### BCCA Index Generation
- [x] Create `scripts/paraphrase_bcca_descriptions.py` - AI-compress BCCA to 100 chars
- [x] Run paraphrasing job - **12,565/12,565 items COMPLETE** (2026-01-11)
- [ ] Export `pricing/data/bcca_index.txt` - Pipe-delimited format for context

#### FFE Database
- [x] Create `pricing/data/ffe.db` - **202 items** from Gemini 3 Pro research
- [x] Create `scripts/parse_ffe_research.py` - Parser for Gemini research → SQLite
- [x] Create `scripts/research_ffe_expansion.py` - Gemini 3 Pro research generator
- [x] Create `scripts/build_ffe_database.py` - Initial database builder
- [ ] Export `pricing/data/ffe_index.txt` - Formatted for context inclusion

---

### 📋 IMPLEMENTATION PHASE 0: Code Extraction (Day 0, ~1 hour)

**BEFORE DELETING ANY FILES, EXTRACT THESE FUNCTIONS:**

- [ ] From `photo_analysis.py` → `cluster_photos.py`:
  - [ ] `get_p1_clustering_prompt()`
  - [ ] `run_p1_clustering()` → rename to `cluster_photos()`
  - [ ] `cluster_photos_direct()` (imported from comparable_workflow.py)

- [ ] From `analyze_room.py` → `cadastre_client.py`:
  - [ ] `smart_year_estimation()` - Critical function for year_built
  - [ ] `lookup_year_from_cadastre()` - May already be in cadastre_client.py
  - [ ] Any helper functions for cadastre lookup

- [ ] From `comparable_workflow.py` → Keep `cluster_photos_direct()`:
  - [ ] This function is used for clustering comparable photos
  - [ ] Move to new `cluster_photos.py` alongside target clustering

**VERIFICATION:**
After extraction, run these tests to ensure nothing is broken:
```bash
# Test clustering still works
python -c "from pipeline.steps.cluster_photos import cluster_photos; print('✅ Clustering OK')"

# Test year estimation still works  
python -c "from pipeline.cadastre_client import smart_year_estimation; print('✅ Year estimation OK')"
```

---

### 📋 IMPLEMENTATION PHASE 1: Data Exports (Day 1, ~2 hours)

```bash
# Export BCCA INDEX (444K tokens)
# Format: ID|UNIT|DESC_100
```

- [ ] Create `scripts/export_bcca_index.py`:
  ```python
  # Reads construction.db, outputs bcca_index.txt
  # Format: 09ACE00130|m2|Alicatado azulejo 30x30 gres porcel. C1 UNE
  # Excludes Chapter 18 (test items)
  # Orders by chapter, then code
  ```

- [ ] Create `scripts/export_ffe_index.py`:
  ```python
  # Reads ffe.db, outputs ffe_index.txt
  # Format includes: code, name, all tier prices, brands, style tags
  # Formatted for easy LLM reading
  ```

- [ ] Verify token counts:
  - BCCA INDEX: ~444K tokens (12,565 × ~35 tokens/line)
  - FFE INDEX: ~12K tokens (202 × ~60 tokens/item)

---

### 📋 IMPLEMENTATION PHASE 2: Schemas (Day 1, ~3 hours)

- [ ] Create `pricing/schemas/phase_outputs.py`:

  ```python
  """
  Pydantic schemas for 9-phase estimator outputs.
  Each phase returns a specific schema that feeds into the next phase.
  """
  from pydantic import BaseModel, Field
  from typing import List, Optional, Literal
  from enum import Enum
  
  # =============================================================================
  # PHASE 1: SCOPE DEFINITION
  # =============================================================================
  
  class ScopeItem(BaseModel):
      """Single item in the renovation scope."""
      room_id: str  # "bathroom_1", "kitchen", "living_room"
      room_name: str  # "Baño Principal", "Cocina"
      category: Literal["demolition", "construction", "mep", "finishes", "furniture"]
      description_es: str  # "Demolición de alicatado existente"
      quantity: float
      unit: str  # "m2", "ud", "ml"
      notes: Optional[str] = None
  
  class DraftScope(BaseModel):
      """Phase 1 output: Initial scope definition."""
      rooms: List[str]  # All rooms identified
      systems: List[str]  # ["electrical", "plumbing", "hvac"]
      items: List[ScopeItem]
      cross_room_items: List[ScopeItem]  # Same paint, same flooring across rooms
      reasoning: str  # Why these items were chosen
  
  # =============================================================================
  # PHASE 2: SCOPE CHECK
  # =============================================================================
  
  class VerifiedScope(BaseModel):
      """Phase 2 output: Scope with completeness verified."""
      original_items: List[ScopeItem]
      items_added: List[ScopeItem]  # What was missing and got added
      rooms_checked: dict  # {"bathroom": {"required": 15, "actual": 18, "pass": True}}
      all_checks_passed: bool
      verification_notes: str
  
  # =============================================================================
  # PHASE 3: WORK PHASES / BOQ
  # =============================================================================
  
  class BOQLineItem(BaseModel):
      """Single line item in Bill of Quantities."""
      line_id: str  # Unique ID
      room_id: str
      scope_item_ref: str  # Links back to scope item
      work_phase: Literal["pre_construction", "demolition", "rough", "installation", "finishing", "furnishing"]
      description_es: str
      quantity: float
      unit: str
      waste_factor: float = 1.0  # 1.1 = 10% waste
      labor_hours: Optional[float] = None
  
  class FullBOQDraft(BaseModel):
      """Phase 3 output: Full Bill of Quantities."""
      line_items: List[BOQLineItem]
      total_m2_demo: float
      total_m2_install: float
      waste_containers_needed: int
      includes_site_management: bool
      includes_final_cleaning: bool
      reasoning: str
  
  # =============================================================================
  # PHASE 4: BOQ CHECK
  # =============================================================================
  
  class DependencyCheck(BaseModel):
      """Check for a single dependency pair."""
      dependency_type: str  # "demo_install", "prep_install", etc.
      found_demo: bool
      found_install: bool
      passed: bool
      missing_item: Optional[str] = None
  
  class VerifiedBOQ(BaseModel):
      """Phase 4 output: BOQ with dependencies verified."""
      original_items: List[BOQLineItem]
      items_added: List[BOQLineItem]
      dependency_checks: List[DependencyCheck]
      all_checks_passed: bool
      verification_notes: str
  
  # =============================================================================
  # PHASE 5: PRICING STRATEGY
  # =============================================================================
  
  class PricingAdaptation(BaseModel):
      """How a line item was matched to BCCA/FFE."""
      bcca_code: Optional[str]  # "01RST00010" or None
      ffe_code: Optional[str]  # "FFE-LIV-001" or None
      match_type: Literal["exact", "adapted", "estimated"]
      base_price: float
      adaptation_reasoning: Optional[str]  # Why we adjusted
      adapted_price: float
  
  class PricedLineItem(BaseModel):
      """BOQ line item with pricing."""
      line_item: BOQLineItem
      pricing: PricingAdaptation
      unit_price: float
      total_price: float  # unit_price * quantity * waste_factor
  
  class PricedBOQDraft(BaseModel):
      """Phase 5 output: BOQ with prices."""
      priced_items: List[PricedLineItem]
      subtotal_materials: float
      subtotal_labor: float
      subtotal_ffe: float
      pre_adjustment_total: float
      bcca_coverage_pct: float  # % with valid BCCA codes
  
  # =============================================================================
  # PHASE 6: REGIONAL ADJUSTMENTS
  # =============================================================================
  
  class RegionalAdjustment(BaseModel):
      """A single adjustment applied."""
      type: Literal["regional", "access", "building", "coordination"]
      name: str  # "Madrid pricing", "No elevator floor 4"
      percentage: float  # 0.15 = 15%
      amount: float
      reasoning: str
  
  class AdjustedBOQ(BaseModel):
      """Phase 6 output: BOQ with adjustments."""
      base_total: float
      adjustments: List[RegionalAdjustment]
      adjusted_total: float
      tax_rate: float  # 0.21 for Spain IVA
      total_with_tax: float
  
  # =============================================================================
  # PHASE 7: TIMELINE
  # =============================================================================
  
  class TimelinePhase(BaseModel):
      """A phase in the timeline."""
      phase_name: str
      duration_days: int
      start_week: int
      end_week: int
      key_activities: List[str]
      dependencies: List[str]  # Phase names that must complete first
  
  class TimelineVerification(BaseModel):
      """Phase 7 output: Timeline."""
      phases: List[TimelinePhase]
      total_weeks: int
      critical_path: List[str]
      milestones: List[dict]  # {"name": "Demo complete", "week": 2}
      buffer_days: int
      notes: str
  
  # =============================================================================
  # PHASE 8: ENERGY
  # =============================================================================
  
  class EnergyVerification(BaseModel):
      """Phase 8 output: Energy compliance."""
      current_rating: Optional[str]  # "E"
      improvements_included: List[str]  # ["windows", "insulation"]
      estimated_new_rating: Optional[str]  # "C"
      letters_improved: int
      not_improved_reason: Optional[str]
      future_recommendations: List[str]
  
  # =============================================================================
  # PHASE 9: FINAL SANITY
  # =============================================================================
  
  class SanityCheck(BaseModel):
      """A single sanity check."""
      check_name: str
      passed: bool
      expected: str
      actual: str
      severity: Literal["error", "warning", "info"]
      suggestion: Optional[str] = None
  
  class InspectionRecommendation(BaseModel):
      """Recommended inspection before purchase."""
      system: str  # "electrical", "plumbing"
      reason: str  # "Pre-2002 installation possible"
      estimated_cost: str  # "€100-150"
      professional_type: str  # "Electricista colegiado"
  
  class SanityCheckResult(BaseModel):
      """Phase 9 output: Final checks."""
      all_checks: List[SanityCheck]
      critical_failures: int
      warnings: int
      ready_for_output: bool
      inspection_recommendations: List[InspectionRecommendation]
  
  # =============================================================================
  # FINAL OUTPUT
  # =============================================================================
  
  class FinalUnifiedEstimate(BaseModel):
      """Complete output from 9-phase estimator."""
      # Identity
      listing_id: int
      package_type: Literal["fast_sell", "fair_market", "out_of_market"]
      comparable_ids: List[int]
      
      # Pricing
      total_price: int
      breakdown: dict  # By room, by category
      margin: int  # comparable_avg - listing_price - reno_cost
      
      # Scope
      rooms: List[dict]  # Room-by-room detail
      all_line_items: List[PricedLineItem]
      scope_summary: str  # "Reforma integral de 3 dormitorios..."
      
      # Timeline
      timeline: TimelineVerification
      
      # Energy
      energy: EnergyVerification
      
      # Quality
      sanity: SanityCheckResult
      inspection_recommendations: List[InspectionRecommendation]
      
      # Year context
      year_context_summary: dict
      
      # Disclaimer
      disclaimer: dict  # {customer_version: str, architect_version: str}
      
      # Metadata
      model_version: str = "v0.4.8"
      bcca_coverage_pct: float
      generation_time_seconds: int
  ```

- [ ] Create `pricing/schemas/unified_estimate.py` (frontend-friendly version):

  ```python
  """
  Simplified schema for frontend consumption.
  FinalUnifiedEstimate is converted to this before sending to API.
  """
  from pydantic import BaseModel
  from typing import List, Optional
  
  class PackageCard(BaseModel):
      """What the frontend needs to render a package card."""
      package_type: str
      display_name: str  # "Venta Rápida"
      total_price: int
      margin: int
      duration_weeks: int
      before_photo_url: str
      after_photo_url: str
      rooms_count: int
      line_items_count: int
  
  class PackageDetail(BaseModel):
      """Full detail for modal."""
      card: PackageCard
      
      # El Cálculo
      price_breakdown: dict
      
      # Transformación
      scope_summary: str
      
      # Qué incluye
      line_items: List[dict]
      
      # Desglose por zona
      rooms: List[dict]
      
      # Cronograma
      timeline: dict
      
      # Próximos pasos
      inspection_recommendations: List[dict]
      
      # Year context (for Building Context card)
      year_context: dict
      
      # Disclaimer
      disclaimer_text: str
  
  class MakePackagesResponse(BaseModel):
      """Response from /make-packages endpoint."""
      success: bool
      packages: List[PackageCard]
      building_context: dict  # For listing tab card
      generation_time_seconds: int
  ```

- [ ] Create `pricing/schemas/estimation_error.py`:

  ```python
  """
  Structured error responses.
  
  PHILOSOPHY: FAIL LOUD AND FAST
  - No retries
  - No fallbacks
  - No partial results that might be wrong
  - Clear error messages that explain what went wrong
  """
  from pydantic import BaseModel
  from typing import Optional
  
  class EstimationError(BaseModel):
      """Error during estimation - always fatal, always clear."""
      error_code: str        # "PHASE_5_FAILED", "OUTPUT_TRUNCATED", "VALIDATION_FAILED"
      phase: Optional[int]   # Which phase failed (1-9)
      phase_name: Optional[str]  # "Pricing Strategy"
      message: str           # Human-readable explanation
      technical_detail: str  # Full error for debugging
      
      # NO retry_after_seconds - we don't retry
      # NO partial_result - we don't return potentially wrong data
  ```

---

### 📋 IMPLEMENTATION PHASE 3: 9-Phase Orchestrator (Day 1-2, ~6 hours)

- [ ] Create `pricing/multi_phase_estimator.py`:
  - [ ] `PHASES` configuration dict (9 phases, model per phase)
  - [ ] `MultiPhaseEstimator` class
  - [ ] `_build_context()` - Assemble cached context (~700K tokens)
  - [ ] `_run_phase()` - Execute single phase with caching
  - [ ] `_build_phase_prompt()` - Phase-specific prompts
  - [ ] `estimate()` - Main entry point running all 9 phases
  
  **CRITICAL: Gemini Configuration**
  ```python
  # For ALL estimation calls (9 phases)
  ESTIMATION_CONFIG = {
      "max_output_tokens": 65536,  # 65k - never truncate
      "temperature": 0.1,          # Low for consistency
      "response_mime_type": "application/json",
  }
  
  # NO RETRIES. If it fails, it fails.
  # Common failure = maxOutputTokens too low → we set it to 65k
  ```

- [ ] Create `pricing/phase_prompts/` directory with detailed prompts:

  - [ ] `phase_1_scope_definition.txt` (Pro):
    ```
    TASK: Define the complete transformation scope.
    
    You have:
    - TARGET PIR: What the listing looks like now
    - COMPARABLE PIRs: What similar properties look like after renovation
    - PHOTOS: Visual evidence of current state and target state
    
    PRINCIPLES:
    - Properties vary in size, layout, and room composition
    - Some properties have multiple instances of the same room type
    - Building systems span across rooms but need per-room considerations
    - Material choices often repeat across rooms for consistency
    
    OUTPUT REQUIRED:
    1. ROOMS: Identify every distinct space in the property
       - Count all instances of each room type
       - Note room sizes from PIR
       - Identify room function and usage patterns
    
    2. SYSTEMS: Map all building systems that need work
       - Electrical: age, capacity, distribution
       - Plumbing: age, material, fixture count
       - HVAC: type, efficiency, distribution
       - Consider age-related implications from year_context
    
    3. SURFACES & FINISHES: Per-room material specifications
       - Floors, walls, ceilings
       - Wet area requirements
       - Current vs target condition
    
    4. CROSS-ROOM CONSISTENCY: Items that apply across spaces
       - Unified flooring types
       - Paint colors and finishes
       - Hardware and fixtures style
    
    COMPLETENESS CHECK:
    - Every space from listing accounted for
    - All systems evaluated
    - Baseline minimum: 5 items per space
    ```

  - [ ] `phase_2_scope_check.txt` (Flash):
    ```
    TASK: Verify scope completeness. ADD items, NEVER remove.
    
    INPUT: Draft scope from Phase 1
    
    PRINCIPLES:
    - Properties have different room types, and often multiple instances of the same type
    - Each room type has a typical complexity level based on its function
    - Wet rooms (bathrooms, kitchens) require more items than dry rooms
    - Every scope item typically needs: demolition, preparation, installation, finishing
    
    MINIMUM ITEM THRESHOLDS BY ROOM TYPE:
    - Wet rooms with fixtures (bathrooms): ≥15 items
    - Wet rooms with appliances (kitchens): ≥20 items
    - Living spaces: ≥10 items
    - Sleeping spaces: ≥8 items
    - Transition spaces (hallways, entries): ≥5 items
    
    SYSTEM COMPLETENESS:
    - Electrical: panel, circuits, outlets, switches, lighting per room
    - Plumbing: supply lines, drainage, fixtures per wet room
    - HVAC: heating/cooling units, distribution, controls
    
    VERIFICATION LOGIC:
    □ Every room from listing appears in scope (including all instances of same type)
    □ Each room meets minimum threshold for its type
    □ All building systems are addressed appropriately
    
    If ANY room has fewer items than its type requires, ADD what's missing.
    Output verified_scope with items_added array.
    ```

  - [ ] `phase_3_work_phases.txt` (Pro):
    ```
    TASK: Expand scope into full Bill of Quantities with work phases.
    
    For EACH scope item, create detailed line items:
    - Demolition (if replacing something)
    - Preparation (leveling, waterproofing, priming)
    - Installation (the actual work)
    - Finishing (painting, sealing, cleaning)
    
    Include NON-MATERIAL work:
    - Site setup and protection
    - Waste removal (containers, trips)
    - Site management
    - Final cleaning
    - Professional fees (architect if needed, permits)
    
    CALCULATE QUANTITIES:
    - Use room m² from PIR
    - Add 10% waste factor for materials
    - Calculate linear meters for perimeters
    ```

  - [ ] `phase_4_boq_check.txt` (Flash):
    ```
    TASK: Verify BOQ completeness. ADD items, NEVER remove.
    
    DEPENDENCY PRINCIPLES:
    Construction work follows logical sequences. Every task has prerequisites 
    and successors. Missing any step in the chain creates incomplete work.
    
    WORK SEQUENCE PATTERNS:
    1. REMOVAL → INSTALLATION
       - Any new installation requires removal of what it replaces
       - Cannot install new surfaces without removing old ones
       
    2. PREPARATION → APPLICATION
       - Surfaces need preparation before new materials
       - Walls need priming before painting
       - Floors need leveling before tiling
       - Wet areas need waterproofing before tiling
       
    3. ROUGH → FINISH
       - Infrastructure (MEP rough-in) before surfaces
       - Framing before drywall
       - Electrical circuits before outlets
       
    4. SUPPORT WORK:
       - Demolition generates waste → waste removal required
       - Any construction → final cleaning required
       - Significant work → site protection required
    
    VERIFICATION LOGIC:
    □ For every REMOVAL item, verify corresponding INSTALLATION exists
    □ For every INSTALLATION, verify required PREPARATION exists
    □ For every MEP fixture, verify infrastructure item exists
    □ Waste removal scaled to demolition volume
    □ Final cleaning included
    
    QUANTITY RULES:
    - Waste removal: approximately 1 container per 50m² of demolition
    - Site protection: proportional to total work area
    
    Output verified_boq with items_added array and dependency_checks.
    ```

  - [ ] `phase_5_pricing_strategy.txt` (Pro):
    ```
    TASK: Price each BOQ line item using BCCA and FFE indexes.
    
    You have in context:
    - BCCA INDEX: 12,565 construction items with prices
    - FFE INDEX: 202 furniture/fixture items with tier prices
    
    PRICING RULES:
    1. Search INDEX for matching item
    2. If exact match: use that code and price
    3. If close match: adapt with reasoning
    4. If no match: use FFE or estimate with justification
    
    ADAPTATION EXAMPLES:
    - "01RST00010 (demolición tabique) at €18/m² is close to our 
       partition demo. Using as base, adjusting +20% for older 
       construction = €21.60/m²"
    
    OUTPUT per line item:
    - bcca_code (or "FFE" or "ESTIMATE")
    - unit, quantity, unit_price, total
    - adaptation_reasoning (if not exact match)
    ```

  - [ ] `phase_6_pricing_adjustments.txt` (Flash):
    ```
    TASK: Apply regional and situational adjustments.
    
    BASE: Andalucía pricing (BCCA source)
    
    REGIONAL MULTIPLIERS:
    - Madrid: +15%
    - Barcelona: +20%
    - País Vasco: +18%
    - Rest of Spain: ±0%
    
    SITUATIONAL ADJUSTMENTS:
    - No elevator + floor >2: +10% (material handling)
    - Narrow access street: +5%
    - Historic building: +15% (preservation requirements)
    - Occupied building (coordinated work): +5%
    
    OUTPUT:
    - List each adjustment applied with percentage and reasoning
    - Show adjusted total
    ```

  - [ ] `phase_7_timeline_validation.txt` (Flash):
    ```
    TASK: Validate and create timeline from BOQ.
    
    PHASE STRUCTURE:
    1. Pre-construction (permits, ordering) - 2-4 weeks
    2. Demolition - based on m² and complexity
    3. Rough work (MEP, structural) - 2-3 weeks
    4. Installation (tiles, kitchen, bathroom) - by room
    5. Finishing (paint, trim, cleanup) - 1-2 weeks
    6. Furnishing (if FFE included) - 1 week
    
    CONSTRAINTS:
    - Max 2 trades working simultaneously (small apartment)
    - Weekends off
    - MEP inspection points (add buffer)
    
    OUTPUT:
    - Phase breakdown with duration
    - Critical path
    - Total weeks
    - Milestones for client checkpoints
    ```

  - [ ] `phase_8_energy_check.txt` (Flash):
    ```
    TASK: Verify energy compliance and calculate impact.
    
    IF property has poor CEE rating (E, F, G):
    □ Windows replacement included?
    □ Insulation improvements included?
    □ HVAC upgrade included?
    □ Hot water system considered?
    
    ESTIMATE RATING CHANGE:
    - Window upgrade: +1 letter
    - Full insulation: +1-2 letters
    - Heat pump: +1 letter
    - Combined: may achieve +2-3 letters
    
    IF not improving energy:
    - Note in output why (budget constraint, already good rating)
    - Suggest future improvement options
    ```

  - [ ] `phase_9_final_sanity.txt` (Pro):
    ```
    TASK: Final sanity check before output.
    
    COMPLETENESS:
    □ Every room from listing has items in BOQ
    □ Total line items ≥ (rooms × 10)
    □ No room has <5 line items
    
    PRICING SANITY:
    □ Cost per m² is €800-2000 (flag if outside)
    □ Renovation cost < 30% property value
    □ No single item >20% of total (flag if so)
    
    TIMELINE SANITY:
    □ Duration 4-16 weeks for typical apartment
    □ No phase >4 weeks without milestone
    
    YEAR CONTEXT:
    □ Year-implied issues addressed or flagged for inspection
    □ Disclaimer text included
    
    IF ANY CHECK FAILS:
    - Flag the issue
    - Suggest correction
    - Include in inspection_recommendations
    
    OUTPUT: Final UnifiedEstimate with all checks passed or flagged
    ```

---

### 📋 IMPLEMENTATION PHASE 4: Context Assembly (Day 2, ~4 hours)

- [ ] Create `pricing/context_builder.py`:
  - [ ] Load Knowledge Graph JSON
  - [ ] Load BCCA INDEX txt
  - [ ] Load FFE INDEX txt
  - [ ] Load supporting knowledge (energy, process, interior)
  - [ ] Format target PIR
  - [ ] Format comparable PIRs
  - [ ] Assemble into single context string
  - [ ] Validate token count < 800K

- [ ] Create `pricing/data/system_instruction_base.txt`:
  - [ ] Role definition
  - [ ] 9-phase workflow overview
  - [ ] Anti-Pareto rules
  - [ ] Minimum items per room type
  - [ ] Dependency pair requirements

---

### 📋 IMPLEMENTATION PHASE 5: Anti-Pareto Measures (Day 2, ~2 hours)

> **PRINCIPLE**: The system must prevent incomplete estimates through structural checks,
> not through memorizing specific items. The rules should work for any property type.

- [ ] Add to Phase 2 (Scope Check) prompt:
  ```
  MINIMUM ITEM THRESHOLDS BY ROOM FUNCTION:
  
  Room complexity correlates with function:
  - Wet rooms with fixtures (bathrooms, utility): Higher complexity
  - Wet rooms with appliances (kitchens): Highest complexity
  - Living/social spaces: Medium complexity
  - Sleeping/private spaces: Lower complexity
  - Transition spaces: Lowest complexity
  
  Thresholds reflect typical renovation scope:
  - High complexity rooms: ≥15-20 items
  - Medium complexity rooms: ≥10 items
  - Lower complexity rooms: ≥5-8 items
  
  If any room falls below its type's threshold, ADD what's missing.
  ```

- [ ] Add to Phase 4 (BOQ Check) prompt:
  ```
  DEPENDENCY CHAIN VERIFICATION:
  
  Construction follows logical sequences. Verify chains are complete:
  
  1. REMOVAL → INSTALLATION chains
     Every new element requires removal of what it replaces
     
  2. PREPARATION → APPLICATION chains
     Surfaces need preparation before new materials
     
  3. INFRASTRUCTURE → FIXTURE chains
     MEP rough-in before fixtures
  
  For each item in BOQ, trace its dependency chain.
  If any predecessor is missing, ADD it.
  ```

- [ ] Add to Phase 9 (Final Sanity) prompt:
  ```
  COMPLETENESS VERIFICATION:
  
  ROOM COVERAGE:
  □ Every room from listing appears in BOQ
  □ Total line items proportional to property complexity
  □ No room falls below minimum threshold for its type
  
  COST REASONABLENESS:
  □ Cost per m² within typical renovation range
  □ Total cost proportional to property value
  □ No single item dominates the budget unexpectedly
  
  TIMELINE REASONABLENESS:
  □ Duration proportional to scope
  □ Phases have appropriate milestones
  ```

---

### 📋 IMPLEMENTATION PHASE 6: Price Lookup Tool (Day 2, ~1 hour)

- [ ] Create `pricing/bcca_price_lookup.py`:
  ```python
  def get_bcca_price(code: str) -> Dict:
      """Simple lookup after Gemini finds code in INDEX."""
      # Returns: code, price, unit, full_desc, found
  ```

- [ ] Register as Gemini function_declaration for Phase 5

---

### 📋 IMPLEMENTATION PHASE 7: Pipeline Integration (Day 3, ~3 hours)

- [ ] Update `v032_orchestrator.py`:
  - [ ] Import `MultiPhaseEstimator`
  - [ ] Replace old EstimatorV3 call with `estimator.estimate()`
  - [ ] Handle phase-by-phase logging
  - [ ] Store phase outputs for debugging

- [ ] Update API routes:
  - [ ] Add `/api/estimate/v4` endpoint
  - [ ] Return full `FinalUnifiedEstimate`
  - [ ] Add phase output inspection endpoint for debugging

---

### 📋 IMPLEMENTATION PHASE 8: Testing (Day 3-4, ~4 hours)

- [ ] Create `tests/test_multi_phase_estimator.py`:
  - [ ] Test context assembly (token count validation)
  - [ ] Test Phase 1 output schema
  - [ ] Test Phase 2 adds items (anti-Pareto)
  - [ ] Test Phase 5 pricing adaptation reasoning
  - [ ] Test Phase 6 regional adjustments
  - [ ] Test full 9-phase flow end-to-end

- [ ] Test on real listings:
  - [ ] Listing 12 (known problematic)
  - [ ] A simple 1-bedroom apartment
  - [ ] A complex 3-bed with 2 bathrooms
  - [ ] A property with poor energy rating

- [ ] Verify anti-Pareto:
  - [ ] Every room has items
  - [ ] Dependencies are satisfied
  - [ ] Minimum items per room met

---

### 📋 IMPLEMENTATION PHASE 9: Clustering Integration (Day 3, ~2 hours)

- [ ] Extract P1 clustering from `pipeline/steps/photo_analysis.py`:
  - [ ] Create new `pipeline/steps/cluster_photos.py`
  - [ ] Move `get_p1_clustering_prompt()` function
  - [ ] Move `run_p1_clustering()` function (rename to `cluster_photos()`)
  - [ ] Move `cluster_photos_direct()` function
  - [ ] Verify it works with target photos
  - [ ] Verify it works with comparable photos
  - [ ] Output format: `{cluster_name: str, photo_indices: List[int], room_type: str}`

- [ ] Delete P2/P3 from `photo_analysis.py` (replaced by PIR)

- [ ] Create `pipeline/steps/cluster_all_properties.py`:
  ```python
  async def cluster_all_properties(
      target_photos: List[str],
      comparable_photos: Dict[int, List[str]]  # property_id → photos
  ) -> Dict:
      """
      Cluster photos for target AND all comparables.
      Returns: {
          "target": PhotoClusters,
          "comparables": {property_id: PhotoClusters, ...}
      }
      """
  ```

---

### 📋 IMPLEMENTATION PHASE 10: PIR Generation for All Properties (Day 3-4, ~4 hours)

- [ ] Update `pipeline/steps/property_intelligence.py`:
  - [ ] Add `year_context` generation (from rules_engine.json)
  - [ ] Add `likely_prior_upgrades` for comparables
  - [ ] Ensure ALL listing data is passed (m2_plot, energy_rating, etc.)
  - [ ] Support running on comparables (different DB destination)
  
  **CRITICAL: Gemini Configuration for PIR**
  ```python
  PIR_CONFIG = {
      "max_output_tokens": 65536,  # 65k - PIR can be large
      "temperature": 0.2,          # Slightly higher for observations
      "response_mime_type": "application/json",
  }
  
  # NO FALLBACKS. If PIR generation fails, raise immediately.
  ```

- [ ] Create `pipeline/steps/generate_all_pirs.py`:
  ```python
  async def generate_all_pirs(
      target_listing: Dict,
      target_clusters: PhotoClusters,
      target_photos: List[bytes],
      comparables: List[ComparableProperty],
      comparable_clusters: Dict[int, PhotoClusters],
      comparable_photos: Dict[int, List[bytes]]
  ) -> Dict:
      """
      Generate PIRs for target AND all comparables.
      
      Returns: {
          "target_pir": PropertyIntelligenceReportV048,
          "comparable_pirs": {property_id: PIR, ...}
      }
      """
      # Run target PIR with smart_year_estimation (cadastre)
      # Run comparable PIRs with their construction_year
  ```

---

### 📋 IMPLEMENTATION PHASE 11: Package Orchestrator (Day 4, ~4 hours)

- [ ] Create `pipeline/package_orchestrator.py`:
  ```python
  class PackageOrchestrator:
      """
      Main entry point for "Make Packages" button.
      Orchestrates the entire V0.4.8 pipeline.
      """
      
      async def make_packages(
          self,
          listing_id: int,
          comparables: List[ComparableProperty]
      ) -> PackageResult:
          """
          COMPLETE PIPELINE:
          1. Fetch target photos from Supabase
          2. Fetch comparable photos (already have from Casafari)
          3. Cluster ALL photos (target + 9 comparables)
          4. Get year_built (cadastre for target, Casafari for comparables)
          5. Generate PIRs for ALL (target + 9 comparables)
          6. Bucket comparables by price (fast_sell/fair_market/out_of_market)
          7. Run 9-phase estimator ×3 (one per bucket)
          8. Generate visuals ×3 (V1-V4 per package)
          9. Format for UI
          10. Store results
          11. Return formatted packages
          """
  ```

- [ ] Wire to API endpoint (background job pattern):
  ```python
  # routes/renovation.py
  from fastapi import BackgroundTasks
  
  @router.post("/renovation/{listing_id}/make-packages")
  async def make_packages(listing_id: int, background_tasks: BackgroundTasks):
      """
      Start package generation in background.
      Returns immediately with job_id.
      Frontend polls /renovation/{listing_id}/package-progress for status.
      """
      # Create progress record
      job_id = await create_progress_record(listing_id)
      
      # Start background job (continues even if user closes browser)
      background_tasks.add_task(run_pipeline_background, listing_id)
      
      return {"job_id": job_id, "status": "started"}
  
  async def run_pipeline_background(listing_id: int):
      """Runs in background thread, not tied to HTTP connection."""
      orchestrator = PackageOrchestrator()
      try:
          await orchestrator.make_packages(listing_id)
          await update_progress(listing_id, status="complete")
      except Exception as e:
          await update_progress(listing_id, status="error", error=str(e))
          raise  # Still log the full error
  ```

- [ ] Add progress streaming endpoint (for frontend progress bar):
  ```python
  @router.get("/renovation/{listing_id}/package-progress")
  async def package_progress(listing_id: int):
      """
      Returns current progress of package generation.
      Frontend polls this every 2 seconds.
      
      Response:
      {
          "status": "running" | "complete" | "error",
          "current_phase": 5,
          "phase_name": "Pricing Strategy",
          "packages_complete": 1,  # of 3
          "estimated_remaining_seconds": 120,
          "error": null | "Error message"
      }
      """
  ```

- [ ] Define comparable bucketing logic:
  ```python
  def bucket_comparables(comparables: List[Comparable], target_price: int) -> Dict:
      """
      Bucket 9 comparables into 3 groups of 3.
      
      Logic:
      - Sort comparables by price
      - fast_sell: 3 lowest-priced comparables (below target price)
      - fair_market: 3 middle comparables (around target price)  
      - out_of_market: 3 highest-priced comparables (above target price)
      
      Returns:
      {
          "fast_sell": [comp1, comp2, comp3],
          "fair_market": [comp4, comp5, comp6],
          "out_of_market": [comp7, comp8, comp9]
      }
      """
  ```

- [ ] Add error handling - FAIL LOUD AND FAST (no retries, no fallbacks):
  ```python
  class PackageOrchestrator:
      """
      NO RETRIES. NO FALLBACKS.
      
      If something fails:
      1. Log the exact error with full context
      2. Raise immediately with clear message
      3. Let the user know what went wrong
      
      Common failure causes (and how to prevent):
      - maxOutputTokens too low → Set to 65536 for PIR and estimates
      - Context too large → Validate token count before calling
      - Invalid schema → Pydantic validation catches this
      """
      
      async def make_packages(self, listing_id: int, comparables: List) -> PackageResult:
          # No try/except wrapper - let errors propagate
          # Each step validates its output and raises if invalid
          
          clusters = await self._cluster_all(...)  # Raises on failure
          pirs = await self._generate_pirs(...)     # Raises on failure
          estimates = await self._run_estimator(...) # Raises on failure
          visuals = await self._generate_visuals(...) # Raises on failure
          
          return self._format_response(...)
  ```

---

### 📋 IMPLEMENTATION PHASE 12: Visuals Integration (Day 4-5, ~3 hours)

- [ ] Review existing `pipeline/steps/visuals.py` (ALREADY IMPLEMENTED):
  - [x] `run_v1_defurnish()` - Remove furniture from photos (Gemini 2.5 Flash Image)
  - [x] `run_v2_select_before()` - Select best "before" photo (kitchen focus)
  - [x] `run_v3_prompts()` - Generate rendering prompt from scope
  - [x] `run_v4_render()` - Render "after" image (Gemini 2.5 Flash Image)

- [ ] **KEY UPDATE**: Wire visuals to use `UnifiedEstimate.scope` from 9-phase:
  - [ ] V3 currently reads from old scope format
  - [ ] Update to read from new `UnifiedEstimate.rooms[].items[]` format
  - [ ] Pass package_type to distinguish visual styles

- [ ] Create `pipeline/steps/generate_package_visuals.py`:
  ```python
  async def generate_package_visuals(
      package: str,  # "fast_sell" | "fair_market" | "out_of_market"
      target_photos: List[bytes],
      target_clusters: PhotoClusters,
      estimate: UnifiedEstimate
  ) -> PackageVisuals:
      """
      Generate before/after images for one package.
      
      Returns:
          before_url: str (Supabase URL)
          after_url: str (Supabase URL)
          room_shown: str ("kitchen")
      """
      # V1: Defurnish kitchen photo
      # V2: Select best kitchen photo
      # V3: Build prompt from estimate scope
      # V4: Render after image
      # Upload both to Supabase
  ```

---

### 📋 IMPLEMENTATION PHASE 13: Database Migrations (Day 1, ~1 hour)

- [ ] Create `supabase/migrations/009_v048_package_progress.sql`:
  ```sql
  -- Track package generation progress (for frontend polling)
  CREATE TABLE package_generation_progress (
      id BIGSERIAL PRIMARY KEY,
      listing_id BIGINT REFERENCES listings(id) UNIQUE,
      
      -- Progress tracking
      status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, complete, error
      current_phase INTEGER DEFAULT 0,
      phase_name TEXT,
      packages_complete INTEGER DEFAULT 0,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      error_message TEXT,
      
      -- Store intermediate results for resume
      phase_outputs JSONB DEFAULT '{}',
      
      CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'complete', 'error'))
  );
  
  CREATE INDEX idx_progress_listing ON package_generation_progress(listing_id);
  ```

- [ ] Create `supabase/migrations/010_v048_estimates.sql`:
  ```sql
  -- Store 9-phase estimates (3 per listing: fast_sell, fair_market, out_of_market)
  CREATE TABLE unified_estimates_v048 (
      id BIGSERIAL PRIMARY KEY,
      listing_id BIGINT REFERENCES listings(id),
      package_type TEXT NOT NULL,  -- 'fast_sell', 'fair_market', 'out_of_market'
      comparable_ids BIGINT[],     -- IDs of the 3 comparables used for this package
      
      -- Price summary
      total_price INTEGER NOT NULL,
      margin INTEGER,              -- Calculated: comparable_avg_price - target_price - reno_cost
      
      -- Raw estimate JSON (full UnifiedEstimate schema)
      estimate_json JSONB NOT NULL,
      
      -- Cached formatted views (avoid re-formatting on each load)
      customer_view_json JSONB,    -- Pre-formatted for frontend modal
      architect_view_json JSONB,   -- Pre-formatted for PDF export
      
      -- Phase outputs for debugging (optional, can be large)
      phase_outputs JSONB,
      
      -- Visuals
      before_photo_url TEXT,
      after_photo_url TEXT,
      
      -- Quality metrics
      rooms_count INTEGER,
      line_items_count INTEGER,
      bcca_coverage_pct FLOAT,     -- % of items with valid BCCA codes
      
      -- Metadata
      created_at TIMESTAMPTZ DEFAULT NOW(),
      model_version TEXT DEFAULT 'v0.4.8',
      generation_time_seconds INTEGER,
      
      UNIQUE(listing_id, package_type)
  );
  
  CREATE INDEX idx_estimates_listing ON unified_estimates_v048(listing_id);
  ```

- [ ] Create `supabase/migrations/011_v048_pirs.sql`:
  ```sql
  -- Enhanced PIRs with year_context (for target AND comparables)
  CREATE TABLE property_intelligence_reports_v048 (
      id BIGSERIAL PRIMARY KEY,
      
      -- Can be listing OR comparable (one must be set)
      listing_id BIGINT REFERENCES listings(id),
      comparable_id BIGINT REFERENCES listing_comparables(id),  -- NULL for target
      
      -- Full PIR JSON
      pir_json JSONB NOT NULL,
      
      -- Year context extracted for quick access (for listing tab card)
      year_built INTEGER,
      year_source TEXT,  -- 'cadastre', 'listing', 'visual_estimate', etc.
      confirmed_issues JSONB,  -- [{system: "electrical", detail: "Panel pre-2002"}]
      possible_issues JSONB,   -- [{system: "plumbing", detail: "Possible lead pipes"}]
      discarded_issues JSONB,  -- [{system: "windows", reason: "PVC visible"}]
      
      -- Room summary extracted for quick access
      rooms_count INTEGER,
      room_types JSONB,  -- ["living_room", "kitchen", "bathroom", "bedroom"]
      
      -- Metadata
      created_at TIMESTAMPTZ DEFAULT NOW(),
      
      -- Either listing_id or comparable_id must be set
      CONSTRAINT pir_must_have_property CHECK (
          (listing_id IS NOT NULL AND comparable_id IS NULL) OR
          (listing_id IS NULL AND comparable_id IS NOT NULL)
      ),
      
      UNIQUE(listing_id) WHERE listing_id IS NOT NULL,
      UNIQUE(comparable_id) WHERE comparable_id IS NOT NULL
  );
  
  CREATE INDEX idx_pir_listing ON property_intelligence_reports_v048(listing_id) WHERE listing_id IS NOT NULL;
  CREATE INDEX idx_pir_comparable ON property_intelligence_reports_v048(comparable_id) WHERE comparable_id IS NOT NULL;
  ```

- [ ] Create `supabase/migrations/012_v048_clusters.sql`:
  ```sql
  -- Photo clusters for target AND comparables
  CREATE TABLE photo_clusters_v048 (
      id BIGSERIAL PRIMARY KEY,
      
      -- Can be listing OR comparable
      listing_id BIGINT REFERENCES listings(id),
      comparable_id BIGINT REFERENCES listing_comparables(id),  -- NULL for target
      
      -- Cluster data
      cluster_name TEXT NOT NULL,        -- "Salón", "Cocina", etc.
      room_type TEXT NOT NULL,           -- "living_room", "kitchen", etc.
      photo_indices INTEGER[],           -- [0, 1, 2] - indices into photo array
      photo_urls TEXT[],                 -- Full URLs for convenience
      description TEXT,
      confidence FLOAT,
      is_ai_generated BOOLEAN DEFAULT FALSE,
      
      -- Metadata
      created_at TIMESTAMPTZ DEFAULT NOW(),
      
      CONSTRAINT cluster_must_have_property CHECK (
          (listing_id IS NOT NULL AND comparable_id IS NULL) OR
          (listing_id IS NULL AND comparable_id IS NOT NULL)
      )
  );
  
  CREATE INDEX idx_cluster_listing ON photo_clusters_v048(listing_id) WHERE listing_id IS NOT NULL;
  CREATE INDEX idx_cluster_comparable ON photo_clusters_v048(comparable_id) WHERE comparable_id IS NOT NULL;
  ```

**Database Storage Flow:**
```
"Make Packages" clicked
    │
    ├─→ INSERT INTO package_generation_progress (status='running')
    │
    ├─→ Clustering → INSERT INTO photo_clusters_v048 (10 rows: 1 target + 9 comparables)
    │
    ├─→ PIR Generation → INSERT INTO property_intelligence_reports_v048 (10 rows)
    │
    ├─→ 9-Phase Estimator × 3 → INSERT INTO unified_estimates_v048 (3 rows)
    │
    ├─→ Visuals → Upload to Supabase Storage → UPDATE unified_estimates_v048 (photo URLs)
    │
    └─→ UPDATE package_generation_progress (status='complete')
```

**Supabase Storage Buckets:**
```
supabase-storage/
├── listing-photos/              # Original scraped photos (already exists)
│   └── {listing_id}/
│       ├── photo_001.jpg
│       └── ...
│
├── package-visuals/             # V0.4.8 before/after images (CREATE NEW)
│   └── {listing_id}/
│       ├── fast_sell/
│       │   ├── before.jpg       # Selected kitchen/main room photo
│       │   ├── before_defurnished.jpg  # V1 output (if needed)
│       │   └── after.jpg        # V4 rendered image
│       ├── fair_market/
│       │   └── ...
│       └── out_of_market/
│           └── ...
│
└── comparable-photos/           # Photos from Casafari (already exists)
    └── {comparable_id}/
        └── ...
```

**URL Pattern:**
```
Before: https://{project}.supabase.co/storage/v1/object/public/package-visuals/{listing_id}/fast_sell/before.jpg
After:  https://{project}.supabase.co/storage/v1/object/public/package-visuals/{listing_id}/fast_sell/after.jpg
```

---

### 📋 IMPLEMENTATION PHASE 14: Frontend Integration (Day 5, ~4 hours)

- [ ] Update "Make Packages" button handler with progress tracking:
  ```typescript
  // components/PackageGenerator.tsx
  const [progress, setProgress] = useState<PackageProgress | null>(null);
  
  const handleMakePackages = async () => {
      setLoading(true);
      
      // Start the package generation
      await fetch(`/api/renovation/${listingId}/make-packages`, { method: 'POST' });
      
      // Poll for progress
      const pollProgress = async () => {
          const res = await fetch(`/api/renovation/${listingId}/package-progress`);
          const data = await res.json();
          setProgress(data);
          
          if (data.status === 'running') {
              setTimeout(pollProgress, 2000);  // Poll every 2 seconds
          } else if (data.status === 'complete') {
              // Fetch final packages
              const pkgRes = await fetch(`/api/renovation/${listingId}/packages`);
              const packages = await pkgRes.json();
              setPackages(packages);
              setLoading(false);
          } else if (data.status === 'error') {
              setError(data.error);
              setLoading(false);
          }
      };
      
      pollProgress();
  };
  ```

- [ ] Create progress UI component:
  ```typescript
  // components/PackageProgressBar.tsx
  interface PackageProgress {
      status: 'running' | 'complete' | 'error';
      current_phase: number;  // 1-9
      phase_name: string;
      packages_complete: number;  // 0-3
      estimated_remaining_seconds: number;
  }
  
  const PackageProgressBar = ({ progress }: { progress: PackageProgress }) => (
      <div className="w-full p-4 bg-gray-800 rounded-lg">
          <div className="flex justify-between mb-2">
              <span>Phase {progress.current_phase}/9: {progress.phase_name}</span>
              <span>{progress.packages_complete}/3 packages</span>
          </div>
          <div className="w-full bg-gray-600 rounded-full h-2">
              <div 
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${(progress.current_phase / 9) * 100}%` }}
              />
          </div>
          <p className="text-sm text-gray-400 mt-2">
              ~{Math.ceil(progress.estimated_remaining_seconds / 60)} min remaining
          </p>
      </div>
  );
  ```

- [ ] Update Package Cards component:
  ```typescript
  // components/PackageCards.tsx
  interface Package {
      package_type: 'fast_sell' | 'fair_market' | 'out_of_market';
      display_name: string;  // "Venta Rápida", "Precio Justo", "Premium"
      total_price: number;
      margin: number;
      duration_weeks: number;
      before_photo_url: string;
      after_photo_url: string;
      rooms_count: number;
      line_items_count: number;
  }
  
  const PackageCards = ({ packages }: { packages: Package[] }) => (
      <div className="grid grid-cols-3 gap-4">
          {packages.map(pkg => (
              <div 
                  key={pkg.package_type}
                  className="cursor-pointer hover:ring-2 ring-blue-500"
                  onClick={() => openModal(pkg)}
              >
                  <img src={pkg.after_photo_url} className="w-full h-48 object-cover" />
                  <h3>{pkg.display_name}</h3>
                  <p className="text-2xl font-bold">€{pkg.total_price.toLocaleString()}</p>
                  <p className="text-green-500">+€{pkg.margin.toLocaleString()} margin</p>
                  <p>{pkg.duration_weeks} weeks</p>
              </div>
          ))}
      </div>
  );
  ```

- [ ] Update Package Modal with new sections:
  ```typescript
  // components/PackageModal.tsx
  const PackageModal = ({ pkg, estimate }: Props) => (
      <Modal>
          {/* Existing sections */}
          <ElCalculoSection price={estimate.total_price} breakdown={estimate.breakdown} />
          <TransformacionSection scope={estimate.scope_summary} />
          <QueIncluyeSection items={estimate.all_line_items} />
          <DesglosePorZonaSection rooms={estimate.rooms} />
          <CronogramaSection timeline={estimate.timeline} />
          
          {/* NEW V0.4.8 sections */}
          <ProximosPasosSection 
              recommendations={estimate.inspection_recommendations} 
          />
          <BeforeAfterCarousel 
              before={pkg.before_photo_url}
              after={pkg.after_photo_url}
          />
          
          {/* Footer with disclaimer and export */}
          <ModalFooter>
              <DisclaimerText text={estimate.disclaimer.customer_version} />
              <ExportButton onClick={() => exportArchitectPDF(estimate)} />
          </ModalFooter>
      </Modal>
  );
  ```

- [ ] Create "Contexto del Edificio" card for Listing Tab:
  ```typescript
  // components/BuildingContextCard.tsx
  interface YearContext {
      year_built: number;
      year_source: string;
      confirmed_issues: Array<{ system: string; detail: string }>;
      possible_issues: Array<{ system: string; detail: string }>;
      discarded_issues: Array<{ system: string; reason: string }>;
  }
  
  const BuildingContextCard = ({ yearContext }: { yearContext: YearContext }) => (
      <div className="bg-gray-800 rounded-lg p-4 mt-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
              🏗️ Contexto del Edificio
          </h3>
          
          <div className="mt-2">
              <p>Año construcción: <strong>{yearContext.year_built}</strong></p>
              <p className="text-sm text-gray-400">Fuente: {yearContext.year_source} ✓</p>
          </div>
          
          <hr className="my-3 border-gray-600" />
          
          {yearContext.confirmed_issues.length > 0 && (
              <div className="mb-2">
                  <span className="text-green-400">✅ Confirmado visualmente:</span>
                  <ul className="ml-4">
                      {yearContext.confirmed_issues.map((issue, i) => (
                          <li key={i}>• {issue.detail}</li>
                      ))}
                  </ul>
              </div>
          )}
          
          {yearContext.possible_issues.length > 0 && (
              <div className="mb-2">
                  <span className="text-yellow-400">❓ Posible (inspección recomendada):</span>
                  <ul className="ml-4">
                      {yearContext.possible_issues.map((issue, i) => (
                          <li key={i}>• {issue.detail}</li>
                      ))}
                  </ul>
              </div>
          )}
          
          {yearContext.discarded_issues.length > 0 && (
              <div className="mb-2">
                  <span className="text-red-400">❌ Descartado visualmente:</span>
                  <ul className="ml-4">
                      {yearContext.discarded_issues.map((issue, i) => (
                          <li key={i}>• {issue.detail} ({issue.reason})</li>
                      ))}
                  </ul>
              </div>
          )}
          
          <p className="text-xs text-gray-500 mt-3">
              ℹ️ Este análisis se basa en el año de construcción y las fotos del anuncio.
          </p>
      </div>
  );
  ```

- [ ] Wire BuildingContextCard to Listing Tab:
  ```typescript
  // app/listing/[id]/page.tsx
  // After listing info section, before photo gallery:
  {pir?.year_context && <BuildingContextCard yearContext={pir.year_context} />}
  ```

---

### 📋 IMPLEMENTATION PHASE 14B: Background Jobs + Checkpointing (Day 5, ~2 hours)

- [ ] Update `package_generation_progress` table to support checkpointing:
  ```sql
  ALTER TABLE package_generation_progress ADD COLUMN checkpoints JSONB DEFAULT '{}';
  -- Example: {"clustering_complete": true, "pir_target_complete": true, ...}
  ```

- [ ] Create `pipeline/checkpoint_manager.py`:
  ```python
  class CheckpointManager:
      async def save_checkpoint(self, listing_id: int, checkpoint: str):
          """Save checkpoint to DB."""
      
      async def get_checkpoints(self, listing_id: int) -> Dict[str, bool]:
          """Get all checkpoints for listing."""
      
      async def should_skip(self, listing_id: int, checkpoint: str) -> bool:
          """Check if step already completed."""
  ```

- [ ] Add checkpoint calls to `PackageOrchestrator`:
  ```python
  if not await self.checkpoint.should_skip(listing_id, "clustering_complete"):
      clusters = await self._cluster_all(...)
      await self.checkpoint.save_checkpoint(listing_id, "clustering_complete")
  else:
      logger.info("⏭️  Skipping clustering (checkpoint exists)")
      clusters = await self._load_clusters(listing_id)
  ```

- [ ] Create `scripts/test_v048_pipeline.py`:
  - [ ] CLI args: `--listing-id`, `--clear-data`, `--from-checkpoint`, `--verbose`
  - [ ] `clear_v048_data()` function (keeps comparables)
  - [ ] Run pipeline with foreground logging
  - [ ] Print summary on success/failure

- [ ] Configure logging for foreground readability:
  - [ ] Format: `HH:MM:SS | LEVEL | message`
  - [ ] Clear step headers with `=====`
  - [ ] Checkmarks for completed items: `✓`
  - [ ] Checkpoint saves marked: `💾`

---

### 📋 IMPLEMENTATION PHASE 15: End-to-End Testing (Day 5-6, ~4 hours)

**TESTING WORKFLOW: Fix and retest until green**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TERMINAL TESTING LOOP                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: Find latest listing with comparables                                │
│  $ SELECT id FROM listings ORDER BY created_at DESC LIMIT 1;                │
│                                                                              │
│  Step 2: Clear V0.4.8 data (keep comparables)                               │
│  $ python scripts/test_v048_pipeline.py --listing-id 12345 --clear-data     │
│                                                                              │
│  Step 3: Run pipeline with verbose logging                                   │
│  $ python scripts/test_v048_pipeline.py --listing-id 12345 --verbose        │
│                                                                              │
│  Step 4: If fails → Fix the issue → Re-run from checkpoint                  │
│  $ python scripts/test_v048_pipeline.py --listing-id 12345 \                │
│      --from-checkpoint pir_target_complete                                   │
│                                                                              │
│  Step 5: Repeat until SUCCESS                                                │
│                                                                              │
│  Step 6: Confirm ready → Test from frontend                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

- [ ] Create test script with clear logging:
  ```bash
  # Expected output format:
  09:15:32 | INFO | ============================================================
  09:15:32 | INFO | STEP 1: CLUSTERING | listing_id=12345
  09:15:32 | INFO | ============================================================
  09:15:32 | INFO |   → Found 15 photos for target
  09:15:32 | INFO |   → Found 9 comparables with 120 total photos
  09:15:35 | INFO |   ✓ Created 6 clusters for target
  09:15:35 | INFO |     - living_room: 3 photos
  09:15:35 | INFO |     - kitchen: 2 photos
  09:15:35 | INFO |     - bathroom_1: 2 photos
  09:15:35 | INFO |     - bathroom_2: 2 photos
  09:15:35 | INFO |     - bedroom_1: 3 photos
  09:15:35 | INFO |     - bedroom_2: 3 photos
  09:15:35 | INFO |   💾 CHECKPOINT: clustering_complete
  09:15:35 | INFO | ============================================================
  09:15:35 | INFO | STEP 2: SMART YEAR ESTIMATION
  09:15:35 | INFO | ============================================================
  ... etc ...
  ```

- [ ] Test complete flow in terminal with **listing 12**:
  ```bash
  # 1. Clear V0.4.8 data for listing 12 (KEEP comparables)
  python scripts/test_v048_pipeline.py --listing-id 12 --clear-data
  
  # 2. Run full pipeline with verbose logging
  python scripts/test_v048_pipeline.py --listing-id 12 --verbose
  
  # 3. Expected: SUCCESS with 3 packages
  # 4. If fails: Fix → Resume from checkpoint → Repeat
  # 5. Only tell user when test passes
  ```

- [ ] Fix-and-retest loop until green:
  - [ ] If clustering fails → Fix → `--from-checkpoint` (none, restarts)
  - [ ] If PIR fails → Fix → `--from-checkpoint clustering_complete`
  - [ ] If estimate fails → Fix → `--from-checkpoint pir_comparables_complete`
  - [ ] If visuals fail → Fix → `--from-checkpoint estimate_out_of_market_complete`

- [ ] Once terminal test passes:
  ```
  ============================================================
  ✅ SUCCESS!
  ============================================================
    Packages generated: 3
      - fast_sell: €45,000
      - fair_market: €62,000
      - out_of_market: €89,000
    
    Total time: 2m 34s
    Checkpoints: 8/8 complete
  ============================================================
  
  ✅ READY FOR FRONTEND TEST
  ```

- [ ] Then test from frontend:
  ```
  1. Open listing page
  2. Click "Get Comparables" → 9 comparables appear
  3. Click "Make Packages" → Loading with progress bar...
  4. → 3 Package cards appear with images
  5. Click each card → Verify modal content
  6. Verify "Contexto del Edificio" card on listing tab
  7. Click "Export for Architect" → PDF downloads
  ```

- [ ] Verify anti-Pareto measures:
  - [ ] Every room from listing has items in BOQ
  - [ ] Wet rooms meet complexity thresholds
  - [ ] Every removal has corresponding installation

---

### 📋 IMPLEMENTATION PHASE 16: Documentation & Cleanup (Day 6, ~2 hours)

- [ ] Update audit doc with V0.4.8 completion
- [ ] Update Master Index
- [ ] Add example phase outputs to docs
- [ ] Deprecate `renovation_resolver.py` (move to `/deprecated/`)
- [ ] Deprecate `kg_estimator.py`
- [ ] Deprecate old pipeline steps (see deprecation list)
- [ ] Remove V1 fallback code from routes
- [ ] Clean up unused imports

---

### ✅ DEFINITION OF DONE (V0.4.8 Complete)

**AUTONOMOUS IMPLEMENTATION**: No user input required during implementation.
**TEST LISTING**: listing_id = 12
**USER CONTACT**: Only when terminal test passes and ready for frontend.

**The implementation is COMPLETE when ALL of these are true:**

```
TERMINAL TEST (listing 12) - MUST PASS BEFORE CONTACTING USER:
□ 1. User opens listing page (e.g., /listing/12)
□ 2. User clicks "Get Comparables" button
□ 3. → 9 comparables appear from Casafari
□ 4. User clicks "Make Packages" button
□ 5. → Loading indicator shows with phase progress
□ 6. → After ~2-3 minutes, 3 package cards appear:
       • Fast Sell (lowest price, quickest timeline)
       • Fair Market (balanced)
       • Out of Market (premium, longer timeline)
□ 7. Each card shows: price, margin, duration, before/after thumbnail
□ 8. User clicks "Fast Sell" card
□ 9. → Modal opens with FULL DETAILS:
       • El Cálculo (price breakdown)
       • Transformación (scope summary)
       • Qué incluye (itemized list)
       • Desglose por zona (room-by-room)
       • Cronograma (timeline phases)
       • Próximos Pasos (inspection recommendations)
       • Before/After carousel
□ 10. User clicks "Export for Architect" button
□ 11. → PDF/JSON downloads with FULL TECHNICAL DETAILS

LISTING TAB:
□ 12. "Contexto del Edificio" card is visible below listing info
       • Shows year_built + source
       • Shows confirmed/possible/descartado issues

BACKEND VERIFICATION:
□ 13. All 9 phases completed for each package
□ 14. Phase outputs stored in database (for debugging)
□ 15. UnifiedEstimate stored per package
□ 16. Images stored in Supabase storage

ANTI-PARETO VERIFICATION:
□ 17. Every room from listing has items in BOQ
□ 18. Wet rooms meet higher complexity thresholds
□ 19. All rooms meet minimum threshold for their type
□ 20. Every removal has corresponding installation
□ 21. All dependency chains are complete (removal → prep → install)

CODE CLEANUP:
□ 22. All deprecated files moved to /deprecated/ folder
□ 23. No import errors in remaining code
□ 24. All tests pass
```

---

### 📊 IMPLEMENTATION TIMELINE SUMMARY

| Phase | Description | Days | Hours |
|-------|-------------|------|-------|
| **0** | **Code Extraction (CRITICAL FIRST!)** | Day 0 | 1h |
| 1 | Data Exports (BCCA, FFE indexes) | Day 1 | 2h |
| 2 | Schemas (phase outputs, unified estimate) | Day 1 | 3h |
| 3 | 9-Phase Orchestrator | Day 1-2 | 6h |
| 4 | Context Assembly | Day 2 | 4h |
| 5 | Anti-Pareto Measures | Day 2 | 2h |
| 6 | Price Lookup Tool | Day 2 | 1h |
| 7 | Pipeline Integration | Day 3 | 3h |
| 8 | Testing 9-Phase | Day 3-4 | 4h |
| 9 | Clustering Integration | Day 3 | 2h |
| 10 | PIR Generation All | Day 3-4 | 4h |
| 11 | Package Orchestrator | Day 4 | 4h |
| 12 | Visuals Integration | Day 4-5 | 3h |
| 13 | Database Migrations | Day 1 | 1h |
| 14 | Frontend Integration | Day 5 | 4h |
| 14B | Background Jobs + Checkpointing | Day 5 | 2h |
| 15 | Terminal Testing (fix-and-retest loop) | Day 5-6 | 4h |
| 16 | Frontend Testing | Day 6 | 2h |
| 17 | Documentation & Cleanup | Day 6 | 2h |
| **TOTAL** | | **6 days** | **~54h** |

### 🔴 CRITICAL PATH (Must Be Done In Order)

```
Phase 0: Code Extraction
    │
    ├─→ Phase 13: Database Migrations (can run in parallel)
    │
    ▼
Phase 1: Data Exports (BCCA + FFE indexes)
    │
    ▼
Phase 2: Schemas
    │
    ├─→ Phase 9: Clustering Integration (can run in parallel)
    │
    ▼
Phase 3: 9-Phase Orchestrator
    │
    ▼
Phase 4: Context Assembly
    │
    ├─→ Phase 5: Anti-Pareto Measures (prompts)
    │
    ▼
Phase 6: Price Lookup Tool
    │
    ▼
Phase 7: Pipeline Integration
    │
    ├─→ Phase 10: PIR Generation All
    │
    ▼
Phase 11: Package Orchestrator
    │
    ├─→ Phase 12: Visuals Integration
    │
    ▼
Phase 8: Testing 9-Phase
    │
    ▼
Phase 14: Frontend Integration
    │
    ▼
Phase 15: End-to-End Testing
    │
    ▼
Phase 16: Documentation & Cleanup
```

---

### FFE Database Status (COMPLETE)

**Created**: 2026-01-11
**Total Items**: 202
**Categories**: Living (20), Dining (20), Bedroom (39), Bathroom (21), Kitchen (20), Lighting (21), Textiles (21), Outdoor (20), Office (20)

**Schema includes**:
- 4 price tiers with low/mid/high values each
- Brand references per tier
- Style tags for adaptation matching
- Basis notes documenting sources

---

### BCCA Index Status (COMPLETE)

**Paraphrased**: 2026-01-11
**Total Items**: 12,565
**Model Used**: Gemini 2.5 Flash Lite
**Column Added**: `desc_100` (100-char AI summaries)

**Next**: Export to `bcca_index.txt` for context inclusion

---

## Part 7A: Enhanced PIR Generation (Pre-Processing)

> **CRITICAL**: The Property Intelligence Report (PIR) is generated BEFORE the 9-phase estimator runs.
> It must be comprehensive enough for both architects AND homeowners.

### Pre-Processing Flow with Cached Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     STEP 1: ZERO-SHOT CLUSTERING                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: ALL photos from listing (no limit)                                  │
│  Output: Room clusters with photo assignments                               │
│                                                                             │
│  [photo_001] ──┐                                                            │
│  [photo_002] ──┼──→ CLUSTER: "living_001" (living room)                    │
│  [photo_003] ──┘                                                            │
│                                                                             │
│  [photo_004] ──┬──→ CLUSTER: "kitchen_001" (kitchen)                       │
│  [photo_005] ──┘                                                            │
│                                                                             │
│  [photo_006] ──┬──→ CLUSTER: "bathroom_001" (master bath)                  │
│  [photo_007] ──┘                                                            │
│                                                                             │
│  Also detects: AI-generated renders, virtual staging                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               STEP 2: PROPERTY INTELLIGENCE REPORT (PIR)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ONE COMPREHENSIVE GEMINI CALL per property with CACHED CONTEXT             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ CACHED CONTEXT (same for ALL properties, cache_control.ttl=3600)    │   │
│  │ ────────────────────────────────────────────────────────────────────│   │
│  │ • System Instruction (PIR generation guidelines)                    │   │
│  │ • energy_knowledge.json (climate zones, age→rating, interventions)  │   │
│  │ • renovation_process_knowledge.json (triggers, permits, phases)     │   │
│  │ • interior_design_knowledge.json (styles, tiers, materials, eras)   │   │
│  │ • rules_engine_v2.json (age-based construction rules)               │   │
│  │ • Uniclass Ss (systems) and Pr (products) codes                     │   │
│  │                                                                      │   │
│  │ ~150K tokens, cached = $0.0046875/call after first                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PROPERTY-SPECIFIC INPUT (per property, uncached)                    │   │
│  │ ────────────────────────────────────────────────────────────────────│   │
│  │                                                                      │   │
│  │ PHOTOS:                                                              │   │
│  │ • ALL photos (with cluster/room assignments from Step 1)            │   │
│  │ • No limit on photo count                                           │   │
│  │                                                                      │   │
│  │ LISTING DATA (COMPLETE):                                             │   │
│  │ • title, description (original listing text)                        │   │
│  │ • price_eur, bedrooms, bathrooms                                    │   │
│  │ • m2_built, m2_useful, m2_plot                                      │   │
│  │ • property_subtype (flat, penthouse, duplex, chalet, etc.)          │   │
│  │ • condition (new, good, renovate)                                   │   │
│  │ • floor_level, floor_number                                         │   │
│  │ • has_elevator, is_exterior, has_terrace, has_balcony               │   │
│  │ • has_pool, has_garage, has_garden, has_storage                     │   │
│  │ • has_air_conditioning, has_wardrobes, is_accessible                │   │
│  │ • balcony_orientation, terrace_orientation                          │   │
│  │ • features[], amenities[], additionalFeatures[]                     │   │
│  │ • roomsAndAmenities (free text)                                     │   │
│  │                                                                      │   │
│  │ LOCATION DATA:                                                       │   │
│  │ • address, street_name, city, neighborhood, region                  │   │
│  │ • postal_code, lat, lng                                             │   │
│  │ • address_resolution, coords_resolution                             │   │
│  │                                                                      │   │
│  │ CADASTRE DATA (if available):                                        │   │
│  │ • year_built (from cadastre)                                        │   │
│  │ • plot_area, building_area                                          │   │
│  │                                                                      │   │
│  │ ENERGY DATA (if available):                                          │   │
│  │ • CEE rating (A-G)                                                  │   │
│  │ • CEE certificate date                                              │   │
│  │                                                                      │   │
│  │ CLUSTER ASSIGNMENTS (from Step 1):                                   │   │
│  │ • [photo_001, photo_002] → "living_001"                             │   │
│  │ • [photo_003] → "kitchen_001"                                       │   │
│  │ • etc.                                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  OUTPUT: PropertyIntelligenceReport (PIR)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Complete Property Data Schema for PIR Input

```python
@dataclass
class PropertyDataForPIR:
    """
    COMPLETE property data to pass to PIR generator.
    Include EVERYTHING we know - the more context, the better the analysis.
    """
    # ═══════════════════════════════════════════════════════════════════════
    # CORE IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    listing_id: int
    source_url: str
    title: Optional[str]
    description: Optional[str]  # Full original listing text - CRITICAL
    
    # ═══════════════════════════════════════════════════════════════════════
    # MEASUREMENTS
    # ═══════════════════════════════════════════════════════════════════════
    price_eur: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    m2_built: Optional[int]      # Constructed area
    m2_useful: Optional[int]     # Usable area
    m2_plot: Optional[int]       # Plot/land area (houses)
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROPERTY TYPE & CONDITION
    # ═══════════════════════════════════════════════════════════════════════
    property_subtype: Optional[str]  # flat, penthouse, duplex, studio, 
                                      # chalet_detached, chalet_semi, 
                                      # chalet_terraced, rustic
    condition: Optional[str]          # new, good, renovate
    housing_situation: Optional[str]  # free, rented, bare_ownership, squatted, auction
    ad_origin: Optional[str]          # standard, bank
    
    # ═══════════════════════════════════════════════════════════════════════
    # FLOOR & BUILDING
    # ═══════════════════════════════════════════════════════════════════════
    floor_level: Optional[str]    # ground, intermediate, top
    floor_number: Optional[int]   # Actual floor number
    
    # ═══════════════════════════════════════════════════════════════════════
    # BOOLEAN AMENITIES (explicit true/false from listing)
    # ═══════════════════════════════════════════════════════════════════════
    has_elevator: Optional[bool]
    is_exterior: Optional[bool]          # Exterior-facing (more light)
    has_terrace: Optional[bool]
    has_balcony: Optional[bool]
    has_pool: Optional[bool]
    has_garage: Optional[bool]
    has_garden: Optional[bool]
    has_storage: Optional[bool]          # Trastero
    has_air_conditioning: Optional[bool]
    has_wardrobes: Optional[bool]        # Built-in wardrobes
    is_accessible: Optional[bool]
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORIENTATIONS
    # ═══════════════════════════════════════════════════════════════════════
    balcony_orientation: Optional[str]   # N, S, E, W, NE, etc.
    terrace_orientation: Optional[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # FEATURES & AMENITIES (lists from listing)
    # ═══════════════════════════════════════════════════════════════════════
    features: List[str]            # Generic features
    amenities: List[str]           # Specific amenities
    additional_features: List[str] # Extra features
    rooms_and_amenities: Optional[str]  # Free-text room description
    
    # ═══════════════════════════════════════════════════════════════════════
    # LOCATION
    # ═══════════════════════════════════════════════════════════════════════
    address: Optional[str]
    street_name: Optional[str]
    city: Optional[str]
    neighborhood: Optional[str]
    region: Optional[str]          # Andalucía, Cataluña, etc.
    postal_code: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    address_resolution: Optional[str]  # res_10 (precise) to res_0 (unknown)
    coords_resolution: Optional[str]   # building, street, neighborhood, city
    
    # ═══════════════════════════════════════════════════════════════════════
    # CADASTRE DATA (from external lookup)
    # ═══════════════════════════════════════════════════════════════════════
    cadastre_year_built: Optional[int]
    cadastre_area: Optional[float]
    cadastre_reference: Optional[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # ENERGY CERTIFICATE (if available)
    # ═══════════════════════════════════════════════════════════════════════
    energy_rating: Optional[str]       # A, B, C, D, E, F, G
    energy_consumption: Optional[float] # kWh/m²/year
    energy_emissions: Optional[float]   # kg CO2/m²/year
    energy_cert_date: Optional[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # PHOTOS & CLUSTERING
    # ═══════════════════════════════════════════════════════════════════════
    photo_urls: List[str]
    photo_clusters: Dict[str, List[int]]  # {"living_001": [0, 1, 2], ...}
    ai_renders_detected: List[int]         # Indices of AI-generated images
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGENCY (context for trust assessment)
    # ═══════════════════════════════════════════════════════════════════════
    agency_name: Optional[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    scraped_at: Optional[datetime]
    reference: Optional[str]  # Listing reference number
```

### PIR Caching Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIR GENERATION CACHING ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CACHE KEY: ""                                            │
│  TTL: 3600 seconds (1 hour)                                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CACHED CONTEXT (~150K tokens)                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  1. SYSTEM INSTRUCTION                             (~5K tokens)       │  │
│  │     └── PIR generation guidelines, output format                      │  │
│  │                                                                       │  │
│  │  2. ENERGY KNOWLEDGE                               (~15K tokens)      │  │
│  │     ├── Climate zones by province                                     │  │
│  │     ├── Age → expected rating mapping                                 │  │
│  │     ├── Construction era characteristics                              │  │
│  │     └── Energy intervention types                                     │  │
│  │                                                                       │  │
│  │  3. RENOVATION PROCESS KNOWLEDGE                   (~20K tokens)      │  │
│  │     ├── CSCAE renovation triggers                                     │  │
│  │     ├── Permit requirements by intervention                           │  │
│  │     └── Phase sequencing rules                                        │  │
│  │                                                                       │  │
│  │  4. INTERIOR DESIGN KNOWLEDGE                      (~25K tokens)      │  │
│  │     ├── Construction eras (pre-1940 to post-2020)                     │  │
│  │     ├── Style vocabulary                                              │  │
│  │     ├── Material specifications                                       │  │
│  │     └── Finish tier definitions                                       │  │
│  │                                                                       │  │
│  │  5. RULES ENGINE V2                                (~30K tokens)      │  │
│  │     ├── Age-based construction rules                                  │  │
│  │     ├── Building code requirements                                    │  │
│  │     └── Common defects by era                                         │  │
│  │                                                                       │  │
│  │  6. UNICLASS CODES                                 (~50K tokens)      │  │
│  │     ├── Ss codes (building systems)                                   │  │
│  │     └── Pr codes (products)                                           │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  COST MATH:                                                                 │
│  ├── First property: 150K × $0.0000125 = $1.875 (full price)               │
│  ├── Subsequent:     150K × $0.00003125 = $0.0046875 (cached, 75% off)     │
│  └── Per 10 properties: $1.875 + (9 × $0.0047) = $1.92                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### PIR Generator Implementation

```python
class PIRGenerator:
    """
    Property Intelligence Report Generator with cached context.
    
    Architecture:
    - Static knowledge bases cached for 1 hour
    - Each property sends only photos + listing data
    - Same model (gemini-3-pro-preview) for quality
    """
    
    def __init__(self):
        self._cached_context = None
        self._cache_time = None
        self._cache_ttl = 3600  # 1 hour
        
    def _build_cached_context(self) -> str:
        """Build the static context that's same for all properties."""
        parts = []
        
        # 1. System instruction
        parts.append(PIR_SYSTEM_INSTRUCTION)
        
        # 2. Energy knowledge
        energy_kb = load_energy_knowledge()
        parts.append(f"\n\n# ENERGY KNOWLEDGE\n```json\n{json.dumps(energy_kb)}\n```")
        
        # 3. Renovation process knowledge
        process_kb = load_process_knowledge()
        parts.append(f"\n\n# RENOVATION PROCESS KNOWLEDGE\n```json\n{json.dumps(process_kb)}\n```")
        
        # 4. Interior design knowledge
        design_kb = load_design_knowledge()
        parts.append(f"\n\n# INTERIOR DESIGN KNOWLEDGE\n```json\n{json.dumps(design_kb)}\n```")
        
        # 5. Rules engine
        rules = load_rules_engine()
        parts.append(f"\n\n# AGE-BASED CONSTRUCTION RULES\n```json\n{json.dumps(rules)}\n```")
        
        # 6. Uniclass codes
        uniclass_ss = load_uniclass_ss()
        uniclass_pr = load_uniclass_pr()
        parts.append(f"\n\n# UNICLASS SYSTEM CODES (Ss)\n```json\n{json.dumps(uniclass_ss)}\n```")
        parts.append(f"\n\n# UNICLASS PRODUCT CODES (Pr)\n```json\n{json.dumps(uniclass_pr)}\n```")
        
        return "\n".join(parts)
    
    def _get_cached_context(self) -> str:
        """Get cached context, rebuilding if expired."""
        now = time.time()
        if self._cached_context is None or (now - self._cache_time) > self._cache_ttl:
            self._cached_context = self._build_cached_context()
            self._cache_time = now
            logger.info(f"Built PIR cached context: {len(self._cached_context)} chars")
        return self._cached_context
    
    async def generate_pir(
        self,
        property_data: PropertyDataForPIR,
        photos: List[bytes]
    ) -> PropertyIntelligenceReportV048:
        """
        Generate PIR for a single property.
        
        Uses cached knowledge context + property-specific data.
        """
        
        # Build property-specific prompt
        property_prompt = self._build_property_prompt(property_data)
        
        # Prepare photo parts with cluster labels
        photo_parts = []
        for cluster_name, photo_indices in property_data.photo_clusters.items():
            for idx in photo_indices:
                if idx < len(photos):
                    is_ai = idx in property_data.ai_renders_detected
                    label = f"[{cluster_name}]" + (" [AI-GENERATED]" if is_ai else "")
                    photo_parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(photos[idx]).decode()
                        }
                    })
                    photo_parts.append({"text": label})
        
        # Make the call with cached context
        response = await genai.generate_content_async(
            model="gemini-3-pro-preview",
            contents=[
                # Cached context (cheap after first call)
                {
                    "role": "user",
                    "parts": [{"text": self._get_cached_context()}],
                    "cache_control": {"ttl_seconds": self._cache_ttl}
                },
                # Property-specific (always full price but small)
                {
                    "role": "user", 
                    "parts": [{"text": property_prompt}] + photo_parts
                }
            ],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": PropertyIntelligenceReportV048
            }
        )
        
        return PropertyIntelligenceReportV048.model_validate_json(response.text)
    
    def _build_property_prompt(self, data: PropertyDataForPIR) -> str:
        """Build the property-specific part of the prompt."""
        return f"""
═══════════════════════════════════════════════════════════════════════════════
PROPERTY TO ANALYZE
═══════════════════════════════════════════════════════════════════════════════

LISTING ID: {data.listing_id}
SOURCE: {data.source_url}

─────────────────────────────────────────────────────────────────────────────
LISTING TEXT (ORIGINAL - extract all clues)
─────────────────────────────────────────────────────────────────────────────
Title: {data.title or "N/A"}

Description:
{data.description or "No description provided"}

Rooms & Amenities Text:
{data.rooms_and_amenities or "N/A"}

─────────────────────────────────────────────────────────────────────────────
MEASUREMENTS
─────────────────────────────────────────────────────────────────────────────
Price: €{data.price_eur:,} if data.price_eur else "N/A"
Bedrooms: {data.bedrooms or "N/A"}
Bathrooms: {data.bathrooms or "N/A"}
Built Area: {data.m2_built or "N/A"} m²
Useful Area: {data.m2_useful or "N/A"} m²
Plot Area: {data.m2_plot or "N/A"} m²

─────────────────────────────────────────────────────────────────────────────
PROPERTY TYPE & CONDITION
─────────────────────────────────────────────────────────────────────────────
Subtype: {data.property_subtype or "N/A"}
Condition (per listing): {data.condition or "N/A"}
Housing Situation: {data.housing_situation or "N/A"}
Ad Origin: {data.ad_origin or "N/A"}

─────────────────────────────────────────────────────────────────────────────
FLOOR & BUILDING
─────────────────────────────────────────────────────────────────────────────
Floor Level: {data.floor_level or "N/A"}
Floor Number: {data.floor_number or "N/A"}

─────────────────────────────────────────────────────────────────────────────
AMENITIES (from listing checkboxes)
─────────────────────────────────────────────────────────────────────────────
Elevator: {data.has_elevator}
Exterior-facing: {data.is_exterior}
Terrace: {data.has_terrace} (orientation: {data.terrace_orientation or "N/A"})
Balcony: {data.has_balcony} (orientation: {data.balcony_orientation or "N/A"})
Pool: {data.has_pool}
Garage: {data.has_garage}
Garden: {data.has_garden}
Storage (trastero): {data.has_storage}
Air Conditioning: {data.has_air_conditioning}
Built-in Wardrobes: {data.has_wardrobes}
Accessible: {data.is_accessible}

─────────────────────────────────────────────────────────────────────────────
FEATURES & AMENITIES LISTS
─────────────────────────────────────────────────────────────────────────────
Features: {", ".join(data.features) if data.features else "None listed"}
Amenities: {", ".join(data.amenities) if data.amenities else "None listed"}
Additional: {", ".join(data.additional_features) if data.additional_features else "None listed"}

─────────────────────────────────────────────────────────────────────────────
LOCATION
─────────────────────────────────────────────────────────────────────────────
Address: {data.address or "N/A"}
Street: {data.street_name or "N/A"}
City: {data.city or "N/A"}
Neighborhood: {data.neighborhood or "N/A"}
Region: {data.region or "N/A"}
Postal Code: {data.postal_code or "N/A"}
Coordinates: {data.lat}, {data.lng} if data.lat else "N/A"
Address Resolution: {data.address_resolution or "N/A"}

─────────────────────────────────────────────────────────────────────────────
CADASTRE DATA (if available)
─────────────────────────────────────────────────────────────────────────────
Year Built: {data.cadastre_year_built or "Not available - ESTIMATE from photos"}
Cadastre Area: {data.cadastre_area or "N/A"} m²
Reference: {data.cadastre_reference or "N/A"}

─────────────────────────────────────────────────────────────────────────────
ENERGY CERTIFICATE (if available)
─────────────────────────────────────────────────────────────────────────────
Rating: {data.energy_rating or "Not available - ESTIMATE from age/photos"}
Consumption: {data.energy_consumption or "N/A"} kWh/m²/year
Emissions: {data.energy_emissions or "N/A"} kg CO2/m²/year

─────────────────────────────────────────────────────────────────────────────
PHOTO CLUSTERS (from zero-shot clustering)
─────────────────────────────────────────────────────────────────────────────
{self._format_clusters(data.photo_clusters)}

AI-Generated Images Detected: {data.ai_renders_detected if data.ai_renders_detected else "None"}

─────────────────────────────────────────────────────────────────────────────
YOUR TASK
─────────────────────────────────────────────────────────────────────────────
Analyze ALL photos and ALL data above.
Use the knowledge bases in your context to:
1. Identify construction era and apply relevant rules
2. Assess energy profile based on location (climate zone) and age
3. Inventory all systems (Uniclass Ss) and products (Uniclass Pr)
4. Assess design style and finish tier
5. Note what an architect would see (technical)
6. Note what a homeowner would feel (livability)
7. Identify renovation triggers

Output a complete PropertyIntelligenceReport.
"""
```

### Enhanced PIR Schema (V0.4.8)

The PIR must capture BOTH architect-level details AND homeowner-level observations:

```python
# =============================================================================
# ENHANCED PROPERTY INTELLIGENCE REPORT - V0.4.8
# =============================================================================

class StructuralObservations(BaseModel):
    """What an architect would notice about structure."""
    structural_system: Literal["load_bearing_masonry", "concrete_frame", "steel_frame", "mixed", "unknown"]
    load_bearing_walls_identified: List[str]  # "Wall between living and kitchen appears load-bearing"
    floor_construction: Literal["concrete_slab", "wood_joists", "steel_deck", "unknown"]
    ceiling_type: Literal["concrete", "plasterboard", "exposed_beams", "coffered", "false_ceiling", "unknown"]
    ceiling_height_estimate: Literal["low_2.4m", "standard_2.5m", "high_2.7m", "very_high_3m+"]
    visible_beams_columns: List[str]  # "Exposed concrete beam in living room"
    foundation_visible: bool
    structural_concerns: List[str]  # "Crack pattern suggests settlement"

class TechnicalSystems(BaseModel):
    """Technical systems assessment for architects."""
    # Electrical
    electrical_panel_type: Optional[str]  # "Old fuse box", "Modern breaker panel"
    electrical_era: Literal["pre_1970s", "1970s_80s", "1990s", "2000s", "modern"]
    outlet_density: Literal["insufficient", "adequate", "good", "excellent"]
    visible_wiring_concerns: List[str]
    
    # Plumbing
    plumbing_material: Optional[Literal["galvanized", "copper", "pex", "cpvc", "mixed", "unknown"]]
    water_pressure_indicators: Optional[str]
    drainage_concerns: List[str]
    water_heater_type: Optional[str]
    
    # HVAC
    heating_system: Optional[str]  # "Individual gas boiler", "Central heating", "Electric radiators"
    cooling_system: Optional[str]  # "Split AC", "Central AC", "None"
    ventilation_type: Literal["natural", "extract_fans", "mechanical", "none_visible"]
    hvac_age_estimate: Optional[str]
    
    # Smart/Tech
    smart_home_features: List[str]  # "Video doorbell", "Smart thermostat"
    internet_infrastructure: Optional[str]  # "Fiber ready", "Coax only"

class WindowDoorAssessment(BaseModel):
    """Detailed window and door analysis."""
    window_frame_material: Literal["aluminum_old", "aluminum_thermal_break", "pvc", "wood", "mixed"]
    glazing_type: Literal["single", "double", "triple", "unknown"]
    window_condition: Literal["poor", "fair", "good", "excellent"]
    window_operation: List[str]  # "Sliding", "Tilt-turn", "Fixed"
    thermal_bridge_indicators: List[str]  # "Condensation on frames", "Cold spots visible"
    
    door_quality: Literal["basic", "standard", "high_end"]
    door_hardware: str  # "Basic chrome handles", "Designer brass"
    interior_door_style: str  # "Flush panel", "Paneled traditional", "Glass"
    
class MaterialsInventory(BaseModel):
    """Complete materials inventory."""
    # Flooring by room
    flooring: Dict[str, str]  # {"living": "Oak parquet", "bathroom": "Ceramic tile 30x30"}
    flooring_condition: Dict[str, str]
    
    # Walls
    wall_finishes: Dict[str, str]  # {"living": "Painted plaster", "bathroom": "Ceramic tile to ceiling"}
    wall_condition: Dict[str, str]
    
    # Ceilings
    ceiling_finishes: Dict[str, str]
    
    # Woodwork
    skirting_type: str
    architrave_type: str
    built_in_joinery: List[str]  # "Fitted wardrobes in master", "Kitchen cabinets"
    
    # Kitchen specifics
    kitchen_cabinets: str  # "Melamine white", "Solid wood shaker"
    kitchen_countertop: str  # "Laminate", "Granite", "Silestone"
    kitchen_backsplash: str
    kitchen_appliances_included: List[str]
    kitchen_appliances_quality: Literal["basic", "mid_range", "high_end", "professional"]
    
    # Bathroom specifics
    bathroom_fixtures: Dict[str, str]  # Per bathroom
    bathroom_tiles: Dict[str, str]
    bathroom_sanitaryware_brand: Optional[str]

class HomeownerFeel(BaseModel):
    """What a homeowner would notice - the "feel" of the space."""
    # Atmosphere
    overall_atmosphere: Literal["cold_institutional", "dated_tired", "neutral", "warm_inviting", "luxurious"]
    brightness: Literal["dark", "somewhat_dark", "bright", "very_bright"]
    sense_of_space: Literal["cramped", "compact", "comfortable", "spacious", "grand"]
    
    # Natural light
    natural_light_quality: Literal["poor", "fair", "good", "excellent"]
    natural_light_notes: str  # "North-facing living room, limited afternoon sun"
    
    # Livability
    storage_adequacy: Literal["insufficient", "adequate", "good", "excellent"]
    storage_notes: str
    privacy_assessment: str  # "Ground floor with street-facing bedrooms"
    noise_indicators: List[str]  # "Near main road", "Thin partition walls visible"
    
    # Emotional response
    first_impression: str  # Open-ended: "Tired but with potential"
    standout_features: List[str]  # "Original terracotta floors", "Double-height ceiling"
    immediate_concerns: List[str]  # "Dated bathroom", "Kitchen too small"
    
    # Lifestyle fit
    family_friendly: bool
    entertaining_space: Literal["none", "limited", "good", "excellent"]
    work_from_home_suitable: bool
    outdoor_space: str  # "Small balcony", "Large terrace", "None"

class EnhancedRoomAnalysis(BaseModel):
    """Complete room analysis combining all perspectives."""
    room_id: str
    room_type: str
    photos: List[str]  # Photo indices from clustering
    
    # Dimensions
    area_m2_estimate: Optional[float]
    ceiling_height: str
    shape: Literal["rectangular", "L_shaped", "irregular", "open_plan_section"]
    
    # Technical (architect view)
    structural_elements: List[str]  # "Load-bearing wall on west side"
    technical_systems: List[str]  # "Radiator under window", "AC split unit"
    materials: Dict[str, str]  # {"floor": "Ceramic 45x45", "walls": "Painted white"}
    condition_technical: Literal["needs_major_work", "needs_updates", "acceptable", "good", "excellent"]
    
    # Aesthetic (homeowner view)
    style_detected: str
    finish_tier: Literal["builder_grade", "mid_range", "high_end", "luxury"]
    atmosphere: str
    natural_light: str
    
    # Issues & Opportunities
    visible_defects: List[str]
    renovation_opportunities: List[str]
    
    # Classifications (for matching)
    uniclass_systems: List[str]  # Ss codes
    uniclass_products: List[str]  # Pr codes

class PropertyIntelligenceReportV048(BaseModel):
    """
    Enhanced Property Intelligence Report V0.4.8
    
    Comprehensive analysis capturing BOTH:
    - Architect-level technical details (structure, systems, materials)
    - Homeowner-level feel and livability
    
    Used as input to the 9-phase estimator.
    """
    # Metadata
    listing_id: int
    created_at: datetime
    version: str = "v0.4.8"
    
    # Input summary
    photos_analyzed: int
    clusters_identified: int
    ai_renders_detected: int
    
    # Building-level
    building_profile: BuildingProfile  # From existing schema
    structural: StructuralObservations
    technical_systems: TechnicalSystems
    windows_doors: WindowDoorAssessment
    
    # Property-level
    materials_inventory: MaterialsInventory
    design_profile: OverallDesignProfile
    homeowner_feel: HomeownerFeel
    
    # Room-by-room
    rooms: List[EnhancedRoomAnalysis]
    
    # Regulatory & Triggers
    regulatory_assessment: RegulatoryAssessment
    triggers: List[RenovationTrigger]
    
    # For estimator matching
    comparison_attributes: ComparisonAttributes
    
    # Open-ended insights
    architect_summary: str  # "Post-war construction with cavity walls, pre-thermal bridge era..."
    homeowner_summary: str  # "Dated but solid apartment with good bones, needs full refresh..."
```

### System Instruction for PIR Generator

The PIR generator needs a comprehensive system instruction:

```python
PIR_SYSTEM_INSTRUCTION = """
You are an expert property analyst with dual expertise:
1. ARCHITECT'S EYE: Technical assessment of structure, systems, materials, construction quality
2. HOMEOWNER'S EYE: Livability, atmosphere, feel, lifestyle fit

You are analyzing a Spanish residential property for renovation planning.

═══════════════════════════════════════════════════════════════════════════════
YOUR KNOWLEDGE BASES (Reference these for standardized vocabulary)
═══════════════════════════════════════════════════════════════════════════════

{ENERGY_KNOWLEDGE}

{PROCESS_KNOWLEDGE}

{INTERIOR_DESIGN_KNOWLEDGE}

{RULES_ENGINE}

═══════════════════════════════════════════════════════════════════════════════
ANALYSIS FRAMEWORK
═══════════════════════════════════════════════════════════════════════════════

For EACH observation, consider:

STRUCTURAL (Architect perspective):
- Is this a load-bearing wall? Look for: thickness, position, continuity
- What's the construction era? Match to interior_design_knowledge eras
- What structural system? (masonry, concrete frame, steel)
- What floor construction? (wood joists creak, concrete is solid)
- Any structural concerns? (cracks, settlement, damp)

SYSTEMS (Technical perspective):
- Electrical: Panel type, outlet density, wire age indicators
- Plumbing: Pipe material visible, fixture age, water pressure clues
- HVAC: System type, age, adequacy for climate zone
- Ventilation: Natural vs mechanical, adequacy

MATERIALS (Specification perspective):
- Be SPECIFIC: "Oak parquet 10cm boards" not just "wood floor"
- Note condition: "Good condition, minor scratches" 
- Note era: "Original 1970s terrazzo" or "Recently updated ceramic"

ATMOSPHERE (Homeowner perspective):
- How does it FEEL? Dark? Bright? Cramped? Airy?
- What's the emotional response? Tired? Inviting? Cold?
- Would YOU want to live here? Why/why not?

═══════════════════════════════════════════════════════════════════════════════
PHOTO ANALYSIS RULES
═══════════════════════════════════════════════════════════════════════════════

1. Analyze ALL photos provided - no limits
2. Photos are pre-clustered into rooms - trust the clustering
3. Look for CONSISTENCY across photos of same room
4. Look for CLUES in reflections, shadows, background details
5. Note what's NOT visible - "No radiators visible, heating unknown"

═══════════════════════════════════════════════════════════════════════════════
YEAR CONTEXT GENERATION (CRITICAL FOR V0.4.8)
═══════════════════════════════════════════════════════════════════════════════

You are provided with `year_built` and `year_source` from cadastre/listing/estimate.
Use the RULES_ENGINE to generate `year_context`:

1. CONSULT RULES_ENGINE for year thresholds:
   - Pre-2002 (REBT): Electrical may be non-compliant
   - Pre-1980 (RD 140): Possible lead pipes  
   - Pre-2006 (CTE DB-HE): Likely poor thermal insulation
   - Pre-1985: Likely no grounding system

2. FOR EACH implied possibility, CHECK VISUAL EVIDENCE:
   - Does what you SEE confirm or contradict the year-implied issue?
   
   Example for 1975 building:
   - Year implies: "Pre-2002 electrical possible"
   - Visual evidence: "Modern consumer panel visible in hallway photo"
   - Conclusion: confidence = "unlikely" (visual contradicts year implication)
   
   Example for 1975 building:
   - Year implies: "Pre-2002 electrical possible"  
   - Visual evidence: "2-pin outlets visible, surface-mounted wiring"
   - Conclusion: confidence = "confirmed" (visual confirms year implication)
   
   Example for 1975 building:
   - Year implies: "Pre-1980 lead pipes possible"
   - Visual evidence: "No pipes visible in photos"
   - Conclusion: confidence = "possible" (cannot confirm or rule out)

3. FOR COMPARABLES: Generate `likely_prior_upgrades`:
   If a 1970 building is in "very_good" condition, what upgrades PROBABLY happened?
   - If electrical indicators look modern: "electrical_likely_upgraded"
   - If bathroom fixtures are contemporary: "plumbing_likely_upgraded"
   - Include reasoning: "1970 building in 'very good' condition with modern fixtures
     suggests electrical and plumbing were likely upgraded during previous renovation"

4. YEAR CONTEXT FRAMING:
   - DO NOT present year-implied issues as REQUIREMENTS
   - Present as POSSIBILITIES that visual evidence confirms/contradicts/leaves unknown
   - The estimator will use this to decide what to RECOMMEND FOR INSPECTION
   - NOT to mandate specific work

═══════════════════════════════════════════════════════════════════════════════
OUTPUT REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

Be COMPREHENSIVE but ACTIONABLE:
- Every observation should inform renovation decisions
- Use standardized vocabulary from knowledge bases
- Be specific about locations ("living room west wall")
- Quantify where possible ("~15m² estimate")
- Flag uncertainties ("appears to be" vs "clearly visible")

Your analysis will be used by an AI estimator to:
1. Compare this property to renovated comparables
2. Identify what needs to change
3. Price the renovation accurately
4. Generate realistic timeline

Missing or vague observations = wrong estimates = unhappy customers.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE GOOD OUTPUT
═══════════════════════════════════════════════════════════════════════════════

WRONG: "The kitchen looks dated"
RIGHT: "Kitchen has melamine white cabinets (1990s style), laminate countertop 
       (wear visible), ceramic 20x20 floor tiles (original installation, 
       grouting yellowed), vinyl single-pane window. Finish tier: builder_grade.
       Atmosphere: functional but tired."

WRONG: "Bathroom needs work"
RIGHT: "Bathroom 1: ~5m², ceramic wall tiles 15x15 to 1.5m height (1980s style,
       some cracked), terrazzo floor (original, good condition), wall-hung sink
       (Roca basic, circa 1990), bathtub with shower hose (no screen), 
       aluminum single-glazed window with condensation staining.
       Electrical: surface-mounted wiring suggests pre-2002 installation.
       Atmosphere: cramped, poor natural light, dated but functional."
"""
```

### Implementation Checklist for Enhanced PIR

Add to Phase 1 implementation:

- [ ] Update `pipeline/schemas/property_intelligence.py` with V0.4.8 schema
- [ ] Add `StructuralObservations` class
- [ ] Add `TechnicalSystems` class  
- [ ] Add `WindowDoorAssessment` class
- [ ] Add `MaterialsInventory` class
- [ ] Add `HomeownerFeel` class
- [ ] Add `YearContext` class with `implied_possibilities`, `confirmed_by_visual`, etc.
- [ ] Add `YearImpliedPossibility` dataclass
- [ ] Update `EnhancedRoomAnalysis` class
- [ ] Create comprehensive `PIR_SYSTEM_INSTRUCTION` with YEAR CONTEXT section
- [ ] Ensure `rules_engine.json` loaded into PIR context
- [ ] Ensure `smart_year_estimation()` called for target (from cadastre_client.py)
- [ ] Use `construction_year` from Casafari for comparables
- [ ] Test year_context generation for various eras (pre-1980, 1980-2002, post-2006)
- [ ] Ensure ALL knowledge bases loaded into context
- [ ] Test with 20+ photo properties
- [ ] Verify output is actionable for estimator
- [ ] Verify year_context.likely_prior_upgrades populated for comparables

---

## Part 7B: Deprecation & Deletion Plan

> **CRITICAL**: V0.4.8 replaces the entire old estimation pipeline. This section lists exactly what to deprecate and delete.

### 🗑️ FILES TO DELETE (Old Code)

#### pricing/ directory - REPLACE ENTIRELY

| File | Size | Why Delete |
|------|------|------------|
| `pricing/renovation_resolver.py` | 97KB | **THE BIG ONE** - Old V1/V2/V3 estimator. Replaced by `MultiPhaseEstimator` |
| `pricing/kg_estimator.py` | 35KB | Old KG-based estimator. Logic now in 9-phase orchestrator |
| `pricing/room_inference.py` | 14KB | Old room detection. Now handled in Phase 1 scope definition |
| `pricing/bcca_embeddings.npy` | 19MB | **DELETE** - Embeddings no longer used (full INDEX in context) |
| `pricing/bcca_prices.db` | 0KB | Empty file, never used |
| `pricing/system_instruction.txt` | 5KB | Old system instruction. Replaced by phase prompts |

**KEEP these in pricing/:**
- `construction.db` - Source for BCCA INDEX export
- `kg_context.yaml` - Still needed for KG content
- `bcca_context.yaml` - May be useful reference
- `hybrid_renovation_graph.json` - KG source
- `flatten_*.py` - Utility scripts, may still be useful
- `enrich_kg_quantity_guidance.py` - Utility script
- `data/ffe.db` - FFE database (keep!)

#### pipeline/steps/ - DELETE THESE

| File | Size | Why Delete |
|------|------|------------|
| `pipeline/steps/scope.py` | 30KB | Old scope expansion. Now Phase 1+2 |
| `pipeline/steps/scope_search.py` | 14KB | Old scope search. Now semantic matching in context |
| `pipeline/steps/map_to_scope.py` | 12KB | Old mapping. Now Phase 3 |
| `pipeline/steps/comparative_gap_analysis.py` | 14KB | Old gap analysis. Now Phase 1 |
| `pipeline/steps/estimate_timeline.py` | 13KB | Old timeline. Now Phase 7 |
| `pipeline/steps/photo_analysis.py` | 33KB | Old P1/P2/P3 approach. Replaced by `property_intelligence.py` |
| `pipeline/steps/analyze_comparables.py` | 22KB | Old comparable analysis. Now Phase 1 |
| `pipeline/steps/analyze_room.py` | 28KB | Old room analysis. Now part of PIR |
| `pipeline/steps/assess_uniclass.py` | 11KB | Replaced by `property_intelligence.py` |
| `pipeline/steps/verify_rules.py` | 11KB | Replaced by `property_intelligence.py` |
| `pipeline/steps/_archive/` | (dir) | Already archived, safe to delete entirely |

**KEEP these in pipeline/steps/:**
- `property_intelligence.py` - **KEEP** - Generates PIR (V0.3.2 unified analysis)
- `text_analysis.py` - **KEEP** - Extracts listing data before PIR generation

**DELETE these in pipeline/steps/ (superseded by property_intelligence.py):**
- `photo_analysis.py` - **DELETE** - Old P1/P2/P3 approach, replaced by PIR generator
- `analyze_comparables.py` - **DELETE** - Now handled in Phase 1 of 9-phase estimator
- `analyze_room.py` - **DELETE** - Now part of PIR generation
- `assess_uniclass.py` - **DELETE** - Replaced by property_intelligence.py
- `verify_rules.py` - **DELETE** - Replaced by property_intelligence.py

**REVIEW these (may still be useful outside estimation):**
- `context_research.py` - Location research, may be useful
- `architect*.py` - May have utility functions
- `visuals.py` - Image processing utilities

#### pipeline/ - DELETE THESE

| File | Size | Why Delete |
|------|------|------------|
| `pipeline/gap_analysis.py` | 40KB | Old gap analysis module. Replaced by Phase 1 |
| `pipeline/orchestrator.py` | 15KB | Old orchestrator. Replaced by `MultiPhaseEstimator` |

**KEEP these in pipeline/:**
- `v032_orchestrator.py` - Update to use new estimator, don't delete yet
- `gemini_client.py` - Still needed
- `db_helpers.py` - Still needed
- `cadastre_client.py` - Still needed
- `schemas/` - Update, don't delete

#### pipeline/schemas/ - UPDATE THESE

| File | Action |
|------|--------|
| `gap_analysis.py` | DEPRECATE - Replace with `phase_outputs.py` |
| `renovation.py` | DEPRECATE - Replace with `unified_estimate.py` |
| `property_intelligence.py` | KEEP - Still needed |

#### pipeline/prompts/ - DELETE THESE

| File | Why Delete |
|------|------------|
| `scope_mapper_v2.py` | Replaced by phase prompts |
| `rule_verification.py` | Integrated into Phase 4 check |
| `condition_assessment_v2.py` | Review - may still be needed for PIR |
| `uniclass_assessment.py` | Review - may still be needed |

#### routes/ - UPDATE

| File | Action |
|------|--------|
| `routes/renovation.py` | UPDATE to use `MultiPhaseEstimator` |

#### Test files - DELETE

| File | Why Delete |
|------|------------|
| `test_renovation_report.py` | Old tests for old code |
| `test_renovation_route.py` | Old tests, replace with new tests |

---

### 📚 DOCS TO ARCHIVE (Move to `docs/_archive/`)

| Doc | Why Archive |
|-----|-------------|
| `PETER_AGENTIC_V0.1.md` | Superseded by V0.4.8 |
| `PETER_AGENTIC_V0.2_IMPLEMENTATION.md` | Superseded by V0.4.8 |
| `PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md` | Superseded by V0.4.8 |
| `PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md` | Merged into V0.4.8 |
| `PETER_AGENTIC_V0.3.2_UNIFIED_PROPERTY_INTELLIGENCE.md` | Merged into V0.4.8 |
| `RENOVATION_PIPELINE_V3_PLAN.md` | Old plan, superseded |
| `RENOVATION_PIPELINE_INDEX.md` | Old index, superseded |
| `V3_QUALITY_FIX_PLAN.md` | Old fixes, superseded |
| `V3_TECH_DEBT_AUDIT.md` | Old audit, superseded |
| `KG_TRAVERSAL_ARCHITECTURE.md` | Approach changed in V0.4.8 |

**KEEP these docs:**
- `PETER_AGENTIC_V0.4_UNIFIED_ESTIMATOR.md` - THE CURRENT PLAN
- `PETER_AGENTIC_MASTER_INDEX.md` - Update to point to V0.4.8
- `PETER_AGENTIC_IMPLEMENTATION_AUDIT.md` - Update with V0.4.8 status
- `PETER_AGENTIC_ARCHITECTURE_DECISION.md` - Historical context
- `ANALYSIS_PIPELINE_ARCHITECTURE.md` - Still relevant for non-pricing
- `MARKET_COMPARISON_ARCHITECTURE.md` - Still relevant

---

### 🔧 DEPRECATION SCRIPT

Create `scripts/deprecate_old_code.py`:

```python
#!/usr/bin/env python3
"""
Deprecation script for V0.4.8 migration.
Run with --dry-run first to see what will be affected.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

BASE = Path("/root/puedo_casa/Lean MVP/backend")
DOCS = Path("/root/puedo_casa/Lean MVP/docs")
ARCHIVE = Path("/root/puedo_casa/Lean MVP/backend/_deprecated_v048")
DOCS_ARCHIVE = DOCS / "_archive"

# Files to DELETE (move to _deprecated)
DELETE_FILES = [
    # pricing/ - old estimators
    "pricing/renovation_resolver.py",
    "pricing/kg_estimator.py",
    "pricing/room_inference.py",
    "pricing/bcca_embeddings.npy",
    "pricing/bcca_prices.db",
    "pricing/system_instruction.txt",
    
    # pipeline/steps/ - old estimation pipeline
    "pipeline/steps/scope.py",
    "pipeline/steps/scope_search.py",
    "pipeline/steps/map_to_scope.py",
    "pipeline/steps/comparative_gap_analysis.py",
    "pipeline/steps/estimate_timeline.py",
    
    # pipeline/steps/ - replaced by property_intelligence.py (V0.3.2)
    "pipeline/steps/photo_analysis.py",      # Old P1/P2/P3 approach
    "pipeline/steps/analyze_comparables.py", # Now in Phase 1
    "pipeline/steps/analyze_room.py",        # Now part of PIR
    "pipeline/steps/assess_uniclass.py",     # Replaced by PIR generator
    "pipeline/steps/verify_rules.py",        # Replaced by PIR generator
    
    # pipeline/ - old orchestration
    "pipeline/gap_analysis.py",
    "pipeline/orchestrator.py",
    
    # pipeline/schemas/ - replaced by phase_outputs.py
    "pipeline/schemas/gap_analysis.py",
    "pipeline/schemas/renovation.py",
    
    # pipeline/prompts/ - old prompts
    "pipeline/prompts/scope_mapper_v2.py",
    "pipeline/prompts/rule_verification.py",
    
    # tests - old tests
    "test_renovation_report.py",
    "test_renovation_route.py",
]

# Directories to DELETE (move to _deprecated)
DELETE_DIRS = [
    "pipeline/steps/_archive",
]

# Docs to ARCHIVE
ARCHIVE_DOCS = [
    "PETER_AGENTIC_V0.1.md",
    "PETER_AGENTIC_V0.2_IMPLEMENTATION.md",
    "PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md",
    "PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md",
    "PETER_AGENTIC_V0.3.2_UNIFIED_PROPERTY_INTELLIGENCE.md",
    "RENOVATION_PIPELINE_V3_PLAN.md",
    "RENOVATION_PIPELINE_INDEX.md",
    "V3_QUALITY_FIX_PLAN.md",
    "V3_TECH_DEBT_AUDIT.md",
    "KG_TRAVERSAL_ARCHITECTURE.md",
]

def deprecate(dry_run=True):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create archive directories
    if not dry_run:
        ARCHIVE.mkdir(exist_ok=True)
        DOCS_ARCHIVE.mkdir(exist_ok=True)
    
    print(f"{'DRY RUN - ' if dry_run else ''}Deprecating old code...")
    print(f"Archive location: {ARCHIVE}")
    print()
    
    # Move files
    for f in DELETE_FILES:
        src = BASE / f
        if src.exists():
            dst = ARCHIVE / f
            print(f"  MOVE: {f}")
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
        else:
            print(f"  SKIP (not found): {f}")
    
    # Move directories
    for d in DELETE_DIRS:
        src = BASE / d
        if src.exists():
            dst = ARCHIVE / d
            print(f"  MOVE DIR: {d}")
            if not dry_run:
                shutil.move(str(src), str(dst))
    
    # Archive docs
    print()
    print("Archiving docs...")
    for d in ARCHIVE_DOCS:
        src = DOCS / d
        if src.exists():
            dst = DOCS_ARCHIVE / d
            print(f"  ARCHIVE: {d}")
            if not dry_run:
                shutil.move(str(src), str(dst))
    
    print()
    print("Done!" if not dry_run else "DRY RUN complete. Run without --dry-run to execute.")

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or len(sys.argv) == 1
    deprecate(dry_run)
```

---

### 📋 DEPRECATION CHECKLIST

**Before deprecating:**
- [ ] Ensure V0.4.8 is fully implemented and tested
- [ ] Backup the entire repository
- [ ] Run deprecation script with `--dry-run` first
- [ ] Review the list of affected files

**Deprecation steps:**
- [ ] Run `python scripts/deprecate_old_code.py` (without --dry-run)
- [ ] Update `PETER_AGENTIC_MASTER_INDEX.md` to point to V0.4.8
- [ ] Update `v032_orchestrator.py` to use `MultiPhaseEstimator`
- [ ] Run full test suite to verify nothing broke
- [ ] Commit with message: "chore: deprecate old estimation code for V0.4.8"

**After deprecating:**
- [ ] Verify all imports still work
- [ ] Verify API routes still work
- [ ] Keep `_deprecated_v048/` for 30 days, then delete permanently

---

## Summary: V0.3 → V0.4.8 Evolution

| Version | Architecture | Problem |
|---------|--------------|---------|
| **V0.3** | 4 separate stages | Handoffs = information loss |
| **V0.4.0** | 1 unified Gemini call | Risk of Pareto-ing (skip 20%) |
| **V0.4.7** | Full BCCA+FFE in context | Better matching, but still single-call |
| **V0.4.8** | **9 phases, cached context** | **Completeness guaranteed** |

### V0.4.8 Key Guarantees

| Guarantee | How It's Enforced |
|-----------|-------------------|
| **No missing rooms** | Phase 2 checks every room from listing |
| **No missing dependencies** | Phase 4 validates dependency pairs |
| **No Pareto-ing** | Minimum items per room type enforced |
| **Full reasoning chain** | Every phase output preserved |
| **Cost efficiency** | Context caching = 60% cheaper |
| **Quality + Speed** | Pro for generation, Flash for checks |

### Cost Comparison

| Approach | Cost per Estimate |
|----------|-------------------|
| V0.3 (4 stages, no caching) | ~$15-20 |
| V0.4.0 (1 call, no index) | ~$5-8 |
| V0.4.7 (1 call, full index) | ~$8-10 |
| **V0.4.8 (9 phases, cached)** | **~$4.10** |

**The key insight**: Gemini's 1M token context window and tool calling means we don't need to split the pipeline. Put everything in, let it reason, get everything out.

---

## Summary: V0.4 → V0.4.1 Changes (SQL Discovery)

| V0.4 Original (Embeddings) | V0.4.1 (SQL + LLM Selection) |
|----------------------------|------------------------------|
| `search_bcca` with BM25+embedding | `discover_bcca` with SQL filtering |
| Returns top-3 by score | Returns candidate pool (30 items) |
| LLM trusts scores | LLM reads descriptions and selects |
| "Score 0.78" - why? | "Selected 30x30 because comparable is modern" |
| Generic embedding model | LLM reads actual Spanish |
| ~100ms per search | ~10ms per discovery |
| Black box selection | Transparent selection with reasoning |

**The key insight**: We were using embeddings as a proxy for understanding, but the LLM IS understanding. SQL for structure (chapters, units), LLM for reading and selecting.

**Why this is better**:
1. **Uses each tool for its strength**: SQL for filtering, LLM for comprehension
2. **Leverages BCCA-speak properly**: Chapter/unit knowledge becomes SQL WHERE clauses
3. **Transparent and debuggable**: See all candidates, see selection reasoning
4. **Faster**: SQL ~10ms vs embedding ~100ms

---

## Part 7C: Complete Lean MVP Audit & Process Flow

> **CRYSTAL CLEAR**: What we have, what we're building, what's untouched.

### The Core Process Flow (V0.4.8 Estimator)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      V0.4.8 RENOVATION ESTIMATOR FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. TARGET LISTING SCRAPED                                                  │
│     └── URL → Scrapfly → ScrapedData (all fields + photos)                 │
│                                                                             │
│  2. COMPARABLES FETCHED (Casafari API - already working)                    │
│     └── casafari_client.py → 9 comparables with full photos                │
│     └── Buckets: fast_sell / fair_market / out_of_market                   │
│                                                                             │
│  3. ZERO-SHOT CLUSTERING (SAME approach for ALL properties)                 │
│     ├── Target listing → Room clusters                                     │
│     └── Each comparable → Room clusters                                    │
│                                                                             │
│  4. PIR GENERATION (SAME approach for ALL properties)                       │
│     ├── Target → PIR → DB: listings_pir                                    │
│     └── Each comparable → PIR → DB: comparables_pir                        │
│     └── Same code, same cached context, different DB destination           │
│                                                                             │
│  5. 9-PHASE UNIFIED ESTIMATOR                                               │
│     └── target_PIR + comparable_PIRs + Photos + Cached Context             │
│     └── → Scope → BOQ → Pricing → Timeline → Energy → Sanity               │
│                                                                             │
│  6. VISUALS (AFTER estimator - visuals.py V1-V4)                            │
│     └── V1: Defurnish photos                                               │
│     └── V2: Select best before photo per tier                              │
│     └── V3: Generate rendering prompts                                     │
│     └── V4: Render after images                                            │
│                                                                             │
│  7. FINAL PACKAGE OUTPUT (per tier/bracket)                                 │
│     └── Scope (what's done)                                                 │
│     └── Price (total + breakdown by room/system)                           │
│     └── Timeline (phases, milestones, dependencies)                        │
│     └── Before/After Images (from step 6)                                  │
│     └── Permits (what's needed, how long)                                  │
│     └── Energy impact (expected rating improvement)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**YES, your understanding is CORRECT:**
> Target Listing Scraped → Comparables (Casafari) → Clusters (same for all) → PIR (same for all) → 9-Phase Estimator → Visuals → Package per bracket

### Complete Lean MVP Folder Audit

#### ✅ PART OF V0.4.8 ESTIMATOR (Being Built/Updated)

| Component | Location | Status |
|-----------|----------|--------|
| **PIR Generator** | `backend/pipeline/steps/property_intelligence.py` | 📝 To be updated to V0.4.8 schema |
| **PIR Schema** | `backend/pipeline/schemas/property_intelligence.py` | 📝 To be updated |
| **9-Phase Estimator** | NEW: `backend/pipeline/unified_estimator.py` | 🆕 To be created |
| **Gemini Client** | `backend/pipeline/gemini_client.py` | ✅ Keep (caching support) |
| **BCCA Database** | `backend/pricing/data/bcca.db` | ✅ Keep (paraphrased) |
| **FFE Database** | `backend/pricing/data/ffe.db` | ✅ Keep (202 items) |
| **Knowledge Graph** | `backend/pricing/kg_context.yaml` | ✅ Keep (for context) |
| **Standards/Knowledge** | `standards/*.json` (energy, process, design, rules) | ✅ Keep |
| **Uniclass Codes** | `standards/uniclass_ss_residential.json`, `uniclass_pr_residential.json` | ✅ Keep |

#### ❌ TO BE DEPRECATED (V0.4.8 Replaces These)

| Component | Location | Why Deprecated |
|-----------|----------|----------------|
| `renovation_resolver.py` | `backend/pricing/` | Replaced by 9-phase estimator |
| `kg_estimator.py` | `backend/pricing/` | Replaced by unified approach |
| `room_inference.py` | `backend/pricing/` | Replaced by PIR room analysis |
| `bcca_embeddings.npy` | `backend/pricing/` | SQL lookup replaces embeddings |
| `system_instruction.txt` | `backend/pricing/` | New instruction in estimator |
| `gap_analysis.py` | `backend/pipeline/` | Merged into Phase 1-2 |
| `orchestrator.py` | `backend/pipeline/` | New MultiPhaseEstimator |
| `v032_orchestrator.py` | `backend/pipeline/` | Same |
| `photo_analysis.py` | `backend/pipeline/steps/` | Merged into PIR |
| `assess_uniclass.py` | `backend/pipeline/steps/` | Merged into PIR |
| `verify_rules.py` | `backend/pipeline/steps/` | Merged into PIR |
| `map_to_scope.py` | `backend/pipeline/steps/` | Replaced by Phase 3 |
| `scope_search.py` | `backend/pipeline/steps/` | Replaced by Phase 5 |
| `scope.py` | `backend/pipeline/steps/` | Replaced by Phases 1-4 |
| `estimate_timeline.py` | `backend/pipeline/steps/` | Replaced by Phase 7 |
| `architect.py` | `backend/pipeline/steps/` | A1/A2/A3 replaced by Phases 1-4 |
| `analyze_room.py` | `backend/pipeline/steps/` | Merged into PIR |
| `comparative_gap_analysis.py` | `backend/pipeline/steps/` | Replaced by Phase 1-2 |
| `comparable_workflow.py` | `backend/pipeline/steps/` | Entirely replaced by PIR on comparables |
| Old prompts | `backend/pipeline/prompts/*.py` | New prompts in estimator |

#### ✅ KEEP AS-IS (Working, Not Part of V0.4.8 Core Changes)

| Component | Location | Status |
|-----------|----------|--------|
| `casafari_client.py` | `backend/clients/` | **KEEP** - Fetches comparables via API (2-call strategy for full photos) |
| `visuals.py` | `backend/pipeline/steps/` | **KEEP** - V1-V4 image gen runs AFTER 9-phase estimator |

#### ⚠️ PARTIALLY DEPRECATED (Keep Some, Delete Rest)

| Component | Location | Keep | Delete |
|-----------|----------|------|--------|
| `analyze_comparables.py` | `backend/pipeline/steps/` | Casafari call + save to DB | Analysis part (verify_rules, assess_uniclass) → replaced by PIR |

#### 🟡 TO REVIEW LATER (Not V0.4.8 Core)

| Component | Location | Status |
|-----------|----------|--------|
| `text_analysis.py` | `backend/pipeline/steps/` | **KEEP** - T1-T4 text extraction. May help Viewing Tab checklist. Review later. |

#### 🔵 UNTOUCHED - SEPARATE FEATURES (Not Part of Estimator)

| Feature | Backend | Frontend | Purpose |
|---------|---------|----------|---------|
| **Scraping** | `backend/scraper/*` | `/api/scrape/` | URL → Listing data (KEEP) |
| **Translation** | `backend/services/translation_service.py` | Translation hooks | Multi-language support |
| **Viewing Tab** | `backend/pipeline/steps/architect_difficulty.py` | `Section4ConfirmInPerson.tsx` | **§4: What to Confirm In Person** |
| **Research Tab** | `backend/pipeline/steps/architect_condition.py` | `Section2MaintenanceComplexity.tsx` | **§2: Maintenance Complexity** |
| **Neighborhood Tour** | `backend/services/tour_*.py` | `NeighborhoodMap.tsx` | Hood exploration |
| **Place Curation** | `backend/routes/curation_v2.py` | Curated places UI | POI recommendations |
| **Building Context** | `backend/routes/building_context.py` | - | Cadastre lookup |
| **Context Research** | `backend/pipeline/steps/context_research.py` | - | Risk research |
| **Smart M2** | `backend/pipeline/steps/smart_m2.py` | - | Area estimation |

#### External Clients (KEEP - For Research Tab & Hood Tour)

| Client | Purpose | Used By |
|--------|---------|---------|
| `google_places_client.py` | POI data | Curation, Hood Tour |
| `foursquare_client.py` | POI data | Curation |
| `overture_client.py` | Places data | Curation |
| `streetview_client.py` | Street images | Hood Tour |
| `geoapify_isochrone.py` | Travel times | Research |
| `transitland_client.py` | Transit data | Research |
| `casafari_client.py` | Comparables | ✅ KEEP - Used by Make Packages |

### Frontend Tabs Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LISTING PAGE TABS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📋 LISTING TAB (Default)                                                   │
│  └── Shows: Property details, photos, map, agency info                     │
│  └── Data: ScrapedData, Photos                                             │
│  └── Status: ✅ WORKS                                                       │
│                                                                             │
│  🔧 RENOVATION TAB ← V0.4.8 ESTIMATOR OUTPUT GOES HERE                      │
│  └── Shows: Comparables, brackets, scope, pricing, timeline                │
│  └── Data: UnifiedEstimate, PIRs                                           │
│  └── Status: 📝 TO BE UPDATED with V0.4.8 output                           │
│                                                                             │
│  👁️ VIEWING TAB (UNTOUCHED)                                                 │
│  └── Shows: Section4ConfirmInPerson - what to check at viewing             │
│  └── Data: architect_difficulty output                                     │
│  └── Backend: /api/renovation/[id]/condition-v2                            │
│  └── Status: ✅ SEPARATE FEATURE, NOT V0.4.8                                │
│                                                                             │
│  🔬 RESEARCH TAB (UNTOUCHED)                                                 │
│  └── Shows: Section2MaintenanceComplexity - ownership costs/risks          │
│  └── Data: architect_condition output                                      │
│  └── Backend: /api/renovation/[id]/condition-assessment                    │
│  └── Status: ✅ SEPARATE FEATURE, NOT V0.4.8                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Routes Status

| Route | Purpose | V0.4.8 Impact |
|-------|---------|---------------|
| `/api/scrape/*` | Scrape listings | KEEP - feeds into estimator |
| `/api/listings/*` | CRUD listings | KEEP |
| `/api/listings/[id]/photos` | Get photos | KEEP |
| `/api/listings/[id]/photo-clusters` | Get clusters | KEEP |
| `/api/listings/[id]/room-analyses` | Room data | 📝 May be updated for PIR |
| `/api/listings/[id]/buyer-intelligence` | Research data | KEEP (Research tab) |
| `/api/listings/[id]/curated-places` | POI data | KEEP (untouched) |
| `/api/renovation/[id]/comparables/*` | Comparable analysis | 📝 Update for V0.4.8 |
| `/api/renovation/[id]/brackets` | Bracket output | 📝 Update for V0.4.8 |
| `/api/renovation/[id]/package-scopes` | Scope output | 📝 Update for V0.4.8 |
| `/api/renovation/[id]/v032-analysis` | Old analysis | ❌ Deprecate |
| `/api/renovation/[id]/condition-v2` | Viewing tab | KEEP (untouched) |
| `/api/renovation/[id]/condition-assessment` | Research tab | KEEP (untouched) |
| `/api/translate/*` | Translation | KEEP (untouched) |
| `/api/pipeline/*` | Old pipeline | 📝 Review |

### Standards & Knowledge Files

| File | Purpose | V0.4.8 Use |
|------|---------|------------|
| `energy_knowledge.json` | Climate zones, ratings, interventions | ✅ In PIR cached context |
| `renovation_process_knowledge.json` | CSCAE triggers, permits, phases | ✅ In PIR cached context |
| `interior_design_knowledge.json` | Styles, tiers, materials, eras | ✅ In PIR cached context |
| `rules_engine_v2.json` | Age-based construction rules | ✅ In PIR cached context |
| `uniclass_ss_residential.json` | System codes | ✅ In PIR cached context |
| `uniclass_pr_residential.json` | Product codes | ✅ In PIR cached context |
| `BCCA2023_V02.*` | Cost database source | ✅ Used to build bcca.db |
| `CTE-DB-*.pdf/txt` | Building codes (reference) | 📖 Reference only |
| `CSCAE_Guia_*.pdf/txt` | Renovation guide (reference) | 📖 Reference only |
| `IDAE_*.pdf/txt` | Energy guides (reference) | 📖 Reference only |

### Summary: What's In Scope vs Out of Scope

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCOPE CLARITY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ IN SCOPE (V0.4.8 Unified Estimator):                                    │
│  ├── Scraping (input - target listing)                                     │
│  ├── Casafari API (comparables - KEEP AS-IS)                               │
│  ├── Zero-shot clustering (same approach for ALL properties)               │
│  ├── PIR generation (same approach for ALL, different DB tables)           │
│  ├── 9-phase estimation                                                    │
│  ├── Visuals (AFTER estimator - before/after images)                       │
│  ├── Bracket/package output                                                │
│  └── Renovation tab display                                                │
│                                                                             │
│  🔵 OUT OF SCOPE (Untouched, separate features):                            │
│  ├── Viewing tab (§4 Confirm In Person)                                    │
│  ├── Research tab (§2 Maintenance Complexity)                              │
│  ├── Text analysis (T1-T4) - review later for Viewing Tab                  │
│  ├── Neighborhood tour generation                                          │
│  ├── Place curation                                                        │
│  ├── Translation service                                                   │
│  ├── Building context (cadastre)                                           │
│  └── External clients (Google Places, Foursquare, etc.)                    │
│                                                                             │
│  ✅ KEEP AS-IS (Working components):                                        │
│  ├── casafari_client.py (Casafari API calls)                               │
│  └── visuals.py (V1-V4 - runs after estimator)                             │
│                                                                             │
│  ⚠️ PARTIALLY DEPRECATED:                                                   │
│  └── analyze_comparables.py (keep Casafari call, delete OLD analysis)      │
│                                                                             │
│  ❌ TO DELETE (Replaced by V0.4.8):                                         │
│  ├── Old estimators (renovation_resolver, kg_estimator)                    │
│  ├── Old pipeline steps (gap_analysis, scope_search, comparable_workflow)  │
│  ├── Old orchestrators                                                     │
│  └── Embedding files (bcca_embeddings.npy)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 7D: Complete Data Alignment Audit

> **CRITICAL**: Ensure all inputs/outputs are aligned and maxed out.

### Data Sources Comparison: Listing vs Comparable

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           LISTING (Scraped)          vs       COMPARABLE (Casafari)         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FIELD                    LISTING                   COMPARABLE              │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                             │
│  IDENTITY                                                                   │
│  ──────────                                                                 │
│  id                       listing.id (BIGINT)       casafari_property_id    │
│  source_url               ✅ source_url (TEXT)      ✅ property_url (TEXT)  │
│  reference                ✅ reference (TEXT)       ❌ N/A                  │
│                                                                             │
│  PRICING                                                                    │
│  ───────                                                                    │
│  price                    ✅ price_eur (INT)        ✅ sale_price (INT)     │
│  price_per_sqm            ❌ Calculated             ✅ price_per_sqm (INT)  │
│                                                                             │
│  AREAS                                                                      │
│  ─────                                                                      │
│  m2_built                 ✅ m2_built (INT)         ✅ total_area (INT)     │
│  m2_useful                ✅ m2_useful (INT)        ✅ living_area (INT)    │
│  m2_plot                  ✅ m2_plot (INT)          ✅ plot_area (INT)      │
│                                                                             │
│  ROOMS                                                                      │
│  ─────                                                                      │
│  bedrooms                 ✅ bedrooms (INT)         ✅ bedrooms (INT)       │
│  bathrooms                ✅ bathrooms (INT)        ✅ bathrooms (INT)      │
│                                                                             │
│  BUILDING                                                                   │
│  ────────                                                                   │
│  year_built               ❌ (from cadastre)        ✅ construction_year    │
│  condition                ✅ condition (TEXT)       ✅ condition (TEXT)     │
│  energy_rating            ❌ (from listing text)    ✅ energy_rating (TEXT) │
│  property_type            ✅ property_subtype       ✅ property_type        │
│                                                                             │
│  LOCATION                                                                   │
│  ────────                                                                   │
│  address                  ✅ address (TEXT)         ✅ address (TEXT)       │
│  city                     ✅ city (TEXT)            ❌ (in features JSONB)  │
│  neighborhood             ✅ neighborhood (TEXT)    ❌ (in features JSONB)  │
│  lat/lng                  ✅ lat, lng (FLOAT)       ✅ coordinates (JSONB)  │
│  distance_km              ❌ N/A (is target)        ✅ distance_km (FLOAT)  │
│                                                                             │
│  FLOOR                                                                      │
│  ─────                                                                      │
│  floor_level              ✅ floor_level (TEXT)     ❌ (in features JSONB)  │
│  floor_number             ✅ floor_number (INT)     ❌ (in features JSONB)  │
│                                                                             │
│  AMENITIES                                                                  │
│  ─────────                                                                  │
│  has_elevator             ✅ has_elevator (BOOL)    ❌ (in features JSONB)  │
│  has_terrace              ✅ has_terrace (BOOL)     ❌ (in features JSONB)  │
│  has_balcony              ✅ has_balcony (BOOL)     ❌ (in features JSONB)  │
│  has_pool                 ✅ has_pool (BOOL)        ❌ (in features JSONB)  │
│  has_garage               ✅ has_garage (BOOL)      ❌ (in features JSONB)  │
│  has_garden               ✅ has_garden (BOOL)      ❌ (in features JSONB)  │
│  has_storage              ✅ has_storage (BOOL)     ❌ (in features JSONB)  │
│  has_air_conditioning     ✅ has_ac (BOOL)          ❌ (in features JSONB)  │
│  has_wardrobes            ✅ has_wardrobes (BOOL)   ❌ N/A                  │
│  is_exterior              ✅ is_exterior (BOOL)     ❌ N/A                  │
│  is_accessible            ✅ is_accessible (BOOL)   ❌ N/A                  │
│                                                                             │
│  TEXT                                                                       │
│  ────                                                                       │
│  title                    ✅ title (TEXT)           ❌ N/A                  │
│  description              ✅ description (TEXT)     ❌ N/A                  │
│  roomsAndAmenities        ✅ roomsAndAmenities      ❌ N/A                  │
│  features                 ✅ features[] (JSONB)     ✅ features{} (JSONB)   │
│  amenities                ✅ amenities[] (JSONB)    ❌ N/A                  │
│  additionalFeatures       ✅ additionalFeatures[]   ❌ N/A                  │
│                                                                             │
│  PHOTOS                                                                     │
│  ──────                                                                     │
│  photos                   ✅ listing_photos table   ✅ photo_urls[] (JSONB) │
│  count                    ✅ 20-50 typical          ✅ Up to 20 per comp    │
│                                                                             │
│  ORIENTATIONS                                                               │
│  ────────────                                                               │
│  balcony_orientation      ✅ balcony_orientation    ❌ (in features JSONB)  │
│  terrace_orientation      ✅ terrace_orientation    ❌ (in features JSONB)  │
│                                                                             │
│  AGENCY                                                                     │
│  ──────                                                                     │
│  agency                   ✅ agency (JSONB)         ❌ N/A                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Differences & How to Handle

| Issue | Listing | Comparable | Solution |
|-------|---------|------------|----------|
| **Year built** | ❌ Not in scraped data | ✅ `construction_year` | Get from cadastre for listing |
| **Energy rating** | ❌ Not explicit field | ✅ Direct field | Extract from listing description or get from PIR inference |
| **Amenities** | ✅ Explicit booleans | ❌ In `features` JSONB | Parse Casafari `features` to extract bools |
| **Floor info** | ✅ Explicit fields | ❌ In `features` JSONB | Parse Casafari `features` |
| **City/neighborhood** | ✅ Explicit fields | ❌ Maybe in `features` | May need to reverse geocode from coords |
| **Description** | ✅ Full text | ❌ None | Comparables analyzed from photos only |

### Unified Input Schema for PIR Generator

Both listings AND comparables must be converted to this unified format:

```python
@dataclass
class UnifiedPropertyInput:
    """
    Unified input for PIR generation.
    Works for BOTH scraped listings AND Casafari comparables.
    """
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY (required)
    # ═══════════════════════════════════════════════════════════════════════
    property_id: int                    # listing_id OR casafari_property_id
    source: Literal["listing", "comparable"]
    source_url: Optional[str]           # Original URL if available
    
    # ═══════════════════════════════════════════════════════════════════════
    # PRICING
    # ═══════════════════════════════════════════════════════════════════════
    price_eur: Optional[int]
    price_per_sqm: Optional[int]        # Calculated if not provided
    price_bucket: Optional[str]         # Only for comparables
    
    # ═══════════════════════════════════════════════════════════════════════
    # AREAS
    # ═══════════════════════════════════════════════════════════════════════
    m2_built: Optional[int]             # total_area for comparables
    m2_useful: Optional[int]            # living_area for comparables
    m2_plot: Optional[int]              # plot_area for comparables
    
    # ═══════════════════════════════════════════════════════════════════════
    # ROOMS
    # ═══════════════════════════════════════════════════════════════════════
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    
    # ═══════════════════════════════════════════════════════════════════════
    # BUILDING (critical for PIR)
    # ═══════════════════════════════════════════════════════════════════════
    year_built: Optional[int]           # construction_year for comparables
    year_source: Optional[str]          # "cadastre", "listing", "casafari", "estimate"
    condition: Optional[str]            # "new", "good", "renovate"
    energy_rating: Optional[str]        # A-G if known
    property_subtype: Optional[str]     # flat, penthouse, chalet, etc.
    
    # ═══════════════════════════════════════════════════════════════════════
    # LOCATION
    # ═══════════════════════════════════════════════════════════════════════
    address: Optional[str]
    city: Optional[str]
    neighborhood: Optional[str]
    region: Optional[str]               # For climate zone inference
    postal_code: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    distance_km: Optional[float]        # Only for comparables (from target)
    
    # ═══════════════════════════════════════════════════════════════════════
    # FLOOR
    # ═══════════════════════════════════════════════════════════════════════
    floor_level: Optional[str]          # ground, intermediate, top
    floor_number: Optional[int]
    
    # ═══════════════════════════════════════════════════════════════════════
    # AMENITIES (explicit booleans)
    # ═══════════════════════════════════════════════════════════════════════
    has_elevator: Optional[bool]
    is_exterior: Optional[bool]
    has_terrace: Optional[bool]
    has_balcony: Optional[bool]
    has_pool: Optional[bool]
    has_garage: Optional[bool]
    has_garden: Optional[bool]
    has_storage: Optional[bool]
    has_air_conditioning: Optional[bool]
    has_wardrobes: Optional[bool]
    is_accessible: Optional[bool]
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORIENTATIONS
    # ═══════════════════════════════════════════════════════════════════════
    balcony_orientation: Optional[str]
    terrace_orientation: Optional[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # TEXT (listings only - comparables don't have this)
    # ═══════════════════════════════════════════════════════════════════════
    title: Optional[str]                # None for comparables
    description: Optional[str]          # None for comparables
    rooms_and_amenities: Optional[str]  # None for comparables
    features: List[str]                 # May be extracted from JSONB
    amenities: List[str]                # Listing only
    additional_features: List[str]      # Listing only
    
    # ═══════════════════════════════════════════════════════════════════════
    # PHOTOS
    # ═══════════════════════════════════════════════════════════════════════
    photo_urls: List[str]               # From listing_photos OR photo_urls JSONB
    photo_clusters: Dict[str, List[int]]  # From zero-shot clustering
    ai_renders_detected: List[int]      # Indices of AI-generated images
    
    # ═══════════════════════════════════════════════════════════════════════
    # RAW DATA (for debugging)
    # ═══════════════════════════════════════════════════════════════════════
    raw_features: Optional[Dict[str, Any]]  # Original features JSONB
```

### Converter Functions

```python
def listing_to_unified_input(
    listing: Listing,
    photos: List[str],
    clusters: Dict[str, List[int]],
    cadastre_year: Optional[int] = None
) -> UnifiedPropertyInput:
    """Convert scraped listing to unified input."""
    
    scraped = listing.scraped_data or {}
    
    return UnifiedPropertyInput(
        property_id=listing.id,
        source="listing",
        source_url=listing.source_url,
        
        price_eur=listing.price_eur,
        price_per_sqm=_calc_price_per_sqm(listing.price_eur, listing.m2_built),
        price_bucket=None,
        
        m2_built=listing.m2_built,
        m2_useful=listing.m2_useful,
        m2_plot=listing.m2_plot,
        
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        
        year_built=cadastre_year or _extract_year_from_description(scraped.get("description")),
        year_source="cadastre" if cadastre_year else "estimate",
        condition=listing.condition,
        energy_rating=_extract_energy_from_description(scraped.get("description")),
        property_subtype=listing.property_subtype,
        
        address=listing.address,
        city=listing.city,
        neighborhood=listing.neighborhood,
        region=listing.region,
        postal_code=scraped.get("postal_code"),
        lat=listing.lat,
        lng=listing.lng,
        distance_km=None,
        
        floor_level=listing.floor_level,
        floor_number=listing.floor_number,
        
        has_elevator=listing.has_elevator,
        is_exterior=listing.is_exterior,
        has_terrace=listing.has_terrace,
        has_balcony=listing.has_balcony,
        has_pool=listing.has_pool,
        has_garage=listing.has_garage,
        has_garden=listing.has_garden,
        has_storage=listing.has_storage,
        has_air_conditioning=listing.has_air_conditioning,
        has_wardrobes=listing.has_wardrobes,
        is_accessible=listing.is_accessible,
        
        balcony_orientation=scraped.get("balcony_orientation"),
        terrace_orientation=scraped.get("terrace_orientation"),
        
        title=listing.title,
        description=listing.description,
        rooms_and_amenities=scraped.get("roomsAndAmenities"),
        features=listing.features or [],
        amenities=scraped.get("amenities", []),
        additional_features=scraped.get("additionalFeatures", []),
        
        photo_urls=photos,
        photo_clusters=clusters,
        ai_renders_detected=[],  # From clustering step
        
        raw_features=None
    )


def comparable_to_unified_input(
    comparable: Dict[str, Any],  # From listing_comparables table
    clusters: Dict[str, List[int]]
) -> UnifiedPropertyInput:
    """Convert Casafari comparable to unified input."""
    
    # Parse features JSONB for amenities
    features = comparable.get("features", {}) or {}
    
    return UnifiedPropertyInput(
        property_id=comparable["casafari_property_id"],
        source="comparable",
        source_url=comparable.get("property_url"),
        
        price_eur=comparable.get("sale_price"),
        price_per_sqm=comparable.get("price_per_sqm"),
        price_bucket=comparable.get("price_bucket"),
        
        m2_built=comparable.get("total_area"),
        m2_useful=comparable.get("living_area"),
        m2_plot=comparable.get("plot_area"),
        
        bedrooms=comparable.get("bedrooms"),
        bathrooms=comparable.get("bathrooms"),
        
        year_built=comparable.get("construction_year"),
        year_source="casafari" if comparable.get("construction_year") else None,
        condition=comparable.get("condition"),
        energy_rating=comparable.get("energy_rating"),
        property_subtype=comparable.get("property_type"),
        
        address=comparable.get("address"),
        city=features.get("city"),
        neighborhood=features.get("neighborhood"),
        region=None,  # Would need reverse geocode
        postal_code=comparable.get("zip_code"),
        lat=comparable.get("coordinates", {}).get("latitude"),
        lng=comparable.get("coordinates", {}).get("longitude"),
        distance_km=comparable.get("distance_km"),
        
        floor_level=_parse_floor_level(features),
        floor_number=features.get("floor"),
        
        has_elevator=_parse_bool_from_features(features, "elevator"),
        is_exterior=_parse_bool_from_features(features, "exterior"),
        has_terrace=_parse_bool_from_features(features, "terrace"),
        has_balcony=_parse_bool_from_features(features, "balcony"),
        has_pool=_parse_bool_from_features(features, "swimming_pool"),
        has_garage=_parse_bool_from_features(features, "garage"),
        has_garden=_parse_bool_from_features(features, "garden"),
        has_storage=_parse_bool_from_features(features, "storage"),
        has_air_conditioning=_parse_bool_from_features(features, "air_conditioning"),
        has_wardrobes=None,  # Not in Casafari
        is_accessible=None,  # Not in Casafari
        
        balcony_orientation=features.get("balcony_orientation"),
        terrace_orientation=features.get("terrace_orientation"),
        
        # NO TEXT DATA for comparables
        title=None,
        description=None,
        rooms_and_amenities=None,
        features=_extract_feature_list(features),
        amenities=[],
        additional_features=[],
        
        photo_urls=comparable.get("photo_urls", []),
        photo_clusters=clusters,
        ai_renders_detected=[],
        
        raw_features=features
    )


def _parse_bool_from_features(features: Dict, key: str) -> Optional[bool]:
    """Parse boolean from Casafari features JSONB."""
    characteristics = features.get("characteristics", [])
    if isinstance(characteristics, list):
        return key in characteristics
    return None


def _parse_floor_level(features: Dict) -> Optional[str]:
    """Parse floor level from Casafari features."""
    floor = features.get("floor")
    if floor is None:
        return None
    if floor == 0:
        return "ground"
    if floor >= 5 or features.get("is_top_floor"):
        return "top"
    return "intermediate"
```

### Migration Plan for V0.4.8

```sql
-- ============================================================================
-- Migration 009: V0.4.8 PIR Tables
-- ============================================================================

-- 1. Enhanced PIR table (replaces property_intelligence_reports)
CREATE TABLE IF NOT EXISTS property_intelligence_reports_v048 (
    id BIGSERIAL PRIMARY KEY,
    
    -- Source identity
    source_type TEXT NOT NULL CHECK (source_type IN ('listing', 'comparable')),
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    comparable_id BIGINT REFERENCES listing_comparables(id) ON DELETE CASCADE,
    
    -- Exactly one must be set
    CHECK (
        (source_type = 'listing' AND listing_id IS NOT NULL AND comparable_id IS NULL) OR
        (source_type = 'comparable' AND comparable_id IS NOT NULL AND listing_id IS NULL)
    ),
    
    -- Full PIR data (V0.4.8 enhanced schema)
    report_data JSONB NOT NULL,
    
    -- Key searchable fields (extracted from report_data)
    year_built INTEGER,
    year_source TEXT,
    energy_rating TEXT,
    energy_expected TEXT,
    finish_tier TEXT,
    dominant_style TEXT,
    construction_era TEXT,
    
    -- New V0.4.8 fields
    structural_system TEXT,
    electrical_era TEXT,
    plumbing_material TEXT,
    window_frame_material TEXT,
    glazing_type TEXT,
    
    -- Homeowner feel
    overall_atmosphere TEXT,
    brightness TEXT,
    sense_of_space TEXT,
    
    -- Room analysis summary
    rooms_analyzed JSONB,
    room_count INTEGER,
    
    -- Comparison attributes
    comparison_attributes JSONB,
    
    -- Triggers & Regulatory
    triggers JSONB,
    trigger_count INTEGER,
    regulatory_assessment JSONB,
    
    -- Summaries
    architect_summary TEXT,
    homeowner_summary TEXT,
    
    -- Metadata
    version TEXT DEFAULT 'v0.4.8',
    photos_analyzed INTEGER,
    clusters_identified INTEGER,
    ai_renders_detected INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(source_type, listing_id, comparable_id)
);

-- Indexes
CREATE INDEX idx_pir_v048_listing ON property_intelligence_reports_v048(listing_id);
CREATE INDEX idx_pir_v048_comparable ON property_intelligence_reports_v048(comparable_id);
CREATE INDEX idx_pir_v048_type ON property_intelligence_reports_v048(source_type);
CREATE INDEX idx_pir_v048_era ON property_intelligence_reports_v048(construction_era);
CREATE INDEX idx_pir_v048_finish ON property_intelligence_reports_v048(finish_tier);

-- 2. Comparable photo clusters (new table)
CREATE TABLE IF NOT EXISTS comparable_photo_clusters (
    id BIGSERIAL PRIMARY KEY,
    comparable_id BIGINT NOT NULL REFERENCES listing_comparables(id) ON DELETE CASCADE,
    
    cluster_data JSONB NOT NULL,  -- {"living_001": [0,1,2], "kitchen_001": [3,4], ...}
    room_count INTEGER,
    ai_renders_detected JSONB,    -- [5, 12] - indices of AI images
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(comparable_id)
);

-- 3. Unified estimates (9-phase output)
CREATE TABLE IF NOT EXISTS unified_estimates_v048 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Input PIRs used
    target_pir_id BIGINT NOT NULL REFERENCES property_intelligence_reports_v048(id),
    comparable_pir_ids BIGINT[],  -- Array of PIR IDs used
    
    -- Full estimate data
    estimate_data JSONB NOT NULL,
    
    -- Summary fields for quick access
    scope_level TEXT,
    total_cost_eur INTEGER,
    timeline_weeks INTEGER,
    energy_improvement_letters INTEGER,
    
    -- Per-tier summaries
    tiers JSONB,  -- {cosmetic: {...}, systems: {...}, structure: {...}}
    
    -- Phase outputs (for debugging/audit)
    phase_outputs JSONB,
    
    -- Metadata
    version TEXT DEFAULT 'v0.4.8',
    model_used TEXT,
    total_tokens INTEGER,
    cached_tokens INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id)
);

-- Indexes
CREATE INDEX idx_ue_v048_listing ON unified_estimates_v048(listing_id);
CREATE INDEX idx_ue_v048_scope ON unified_estimates_v048(scope_level);

-- RLS
ALTER TABLE property_intelligence_reports_v048 ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparable_photo_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE unified_estimates_v048 ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Allow all" ON property_intelligence_reports_v048 FOR ALL USING (true);
CREATE POLICY "Allow all" ON comparable_photo_clusters FOR ALL USING (true);
CREATE POLICY "Allow all" ON unified_estimates_v048 FOR ALL USING (true);
```

### Checklist: Data Completeness

**Listing Input (from scraping):** ✅ ALL IMPLEMENTED

| Field | Status | Notes |
|-------|--------|-------|
| title, description | ✅ | Full text |
| price_eur | ✅ | Integer |
| bedrooms, bathrooms | ✅ | Integers |
| m2_built, m2_useful | ✅ | In areas object |
| m2_plot | ✅ | **ADDED** - Regex: `parcela\|terreno\|plot\|land` |
| energy_rating | ✅ | **ADDED** - Regex extracts A-G rating |
| construction_year | ✅ | **ADDED** - Regex for año/built |
| All 11 boolean amenities | ✅ | elevator, terrace, pool, etc. |
| floor_level, floor_number | ✅ | Text + Integer |
| Location fields | ✅ | address, city, neighborhood, region, postal_code |
| property_subtype, condition | ✅ | Text enums |
| features[], amenities[] | ✅ | Arrays |
| photos | ✅ | Via listing_photos table |

**Comparable Input (from Casafari):** ✅ ALREADY COMPLETE

| Field | Status | Notes |
|-------|--------|-------|
| sale_price, price_per_sqm | ✅ | Integers |
| total_area, living_area, plot_area | ✅ | All three area types |
| bedrooms, bathrooms | ✅ | Integers |
| construction_year | ✅ | Direct field |
| energy_rating | ✅ | Direct field |
| condition | ✅ | Text |
| coordinates | ✅ | JSONB `{latitude, longitude}` |
| photo_urls | ✅ | **2-call strategy gets up to 20 full photos** |
| features | ✅ | JSONB with amenities |

**Parser Changes Made:**
1. `backend/scraper/rules.py` - Added `m2_plot`, `energy_rating`, `construction_year` regexes
2. `backend/scraper/parsers/idealista.py` - Added extraction for all three new fields
3. `backend/scraper/parsers/gemini_universal.py` - Already had m2_plot, added energy_rating + construction_year
4. `backend/scraper/normalizer.py` - Added passthrough for all new fields
5. `backend/schema.py` - Added `energy_rating` and `construction_year` to ScrapedData

**Casafari Status:**
- ✅ Already uses 2-call strategy for full photos (up to 20 per comparable)
- ✅ Returns construction_year and energy_rating directly
- ✅ Returns plot_area for houses
- Need to parse `features.characteristics[]` for boolean amenities when creating PIR

### Year Built: Smart Cadastre Integration ✅ FULLY IMPLEMENTED

**Why Year Matters (from `rules_engine.json`):**

| Year Threshold | Regulation | Implication |
|----------------|------------|-------------|
| Pre-1973 | - | No earth wire (grounding) |
| Pre-1980 | RD 140/2003 | Possible lead pipes |
| Pre-1985 | REBT | Missing grounding system |
| Pre-2002 | REBT 2002 | Non-compliant electrical |
| Pre-2006 | CTE DB-HE | Non-compliant thermal insulation |
| Pre-2009 | CTE DB-HR | Non-compliant acoustics |

**Smart Year Estimation (`backend/pipeline/steps/analyze_room.py:smart_year_estimation`):**

```
Priority Chain (explicit provenance tracking, NOT error fallbacks):
1. Listing data (fastest) → year_source = "listing"
2. Cadastre API (coordinates first, then address) → year_source = "cadastre" 
3. Street sampling (if street-only address) → year_source = "street_sample"
4. Neighborhood sampling (Google Places + Gemini addresses) → year_source = "neighborhood_sample"
5. Last resort → year_source = "estimate" (1975 conservative assumption)

NOTE: year_source is ALWAYS set - the UI shows where the data came from.
This is data acquisition with provenance, not silent error fallback.
If year_source = "estimate", the PIR clearly indicates this is an assumption.
```

**Cadastre Client (`backend/pipeline/cadastre_client.py`):**

| Function | Purpose | Notes |
|----------|---------|-------|
| `lookup_year_from_cadastre()` | Main entry point | Tries coords → address → street → neighborhood |
| `get_refcat_from_coordinates()` | Direct coordinate lookup | Most reliable method |
| `lookup_by_address()` | Parsed address query | Requires province, municipality, street |
| `sample_street_years()` | Street sampling | For "Calle X" without door number |
| `sample_neighborhood_years()` | Neighborhood average | Uses Google Places + Gemini for addresses |
| `generate_neighborhood_addresses()` | Gemini address gen | Uses `gemini-3-flash-preview` |

**Visual Age Estimation (`rules_engine.json:age_estimation`):**

When Cadastre fails, PIR uses visual indicators:
- **Pre-1960**: Cast iron radiators, terrazzo floors, high ceilings, decorative moldings
- **1960-1979**: Silver aluminum frames, two-pin outlets, formica countertops
- **1980-1999**: White PVC frames (first gen), gres tiles, drop ceilings
- **2000-2010**: Double-glazed PVC, large format tiles, walk-in showers
- **Post-2010**: Floor-to-ceiling windows, LED strips, smart home controls

**Year Source Tracking in PIR:**

```python
# In property_intelligence.py
year_source: Literal["cadastre", "listing", "street_sample", "neighborhood_sample", "estimate"]

# PIR generates appropriate disclaimers:
if year_source == "cadastre":
    "Year verified ({year}) via official Catastro."
elif year_source in ["street_sample", "neighborhood_sample"]:  
    "Year estimated ({year}) from nearby buildings. Visual findings take priority."
else:
    "Year estimated ({year}) conservatively. Prioritize visual assessment."
```

**Status:** ✅ KEEP AS-IS - Fully implemented, integrates with PIR and rules engine

### Type Reference: All Fields

| Field | Listing Type | Comparable Type | DB Type | Notes |
|-------|-------------|-----------------|---------|-------|
| **ID** | | | | |
| id | `int` | `int` | `BIGINT` | PK |
| source_url | `str` | `str` | `TEXT` | |
| reference | `str` | - | `TEXT` | Listing only |
| **PRICING** | | | | |
| price_eur | `int` | `int` | `INTEGER` | |
| price_per_sqm | - | `int` | `INTEGER` | Calculated for listing |
| price_bucket | - | `str` | `TEXT` | Comparable only |
| **AREAS** | | | | |
| m2_built | `int` | `int` | `INTEGER` | Casafari: `total_area` |
| m2_useful | `int` | `int` | `INTEGER` | Casafari: `living_area` |
| m2_plot | `int` | `int` | `INTEGER` | **FIX: Add to parser** |
| **ROOMS** | | | | |
| bedrooms | `int` | `int` | `INTEGER` | |
| bathrooms | `int` | `int` | `INTEGER` | |
| **BUILDING** | | | | |
| year_built | `int` | `int` | `INTEGER` | **FIX: From cadastre** |
| condition | `str` | `str` | `TEXT` | new/good/renovate |
| energy_rating | `str` | `str` | `TEXT` | **FIX: Add extraction** |
| property_subtype | `str` | `str` | `TEXT` | |
| **LOCATION** | | | | |
| address | `str` | `str` | `TEXT` | |
| street_name | `str` | - | `TEXT` | |
| street_number | `str` | - | `TEXT` | |
| city | `str` | - | `TEXT` | |
| neighborhood | `str` | - | `TEXT` | |
| region | `str` | - | `TEXT` | |
| postal_code | `str` | `str` | `TEXT` | |
| lat | `float` | `float` | `NUMERIC` | |
| lng | `float` | `float` | `NUMERIC` | |
| distance_km | - | `float` | `NUMERIC` | Comparable only |
| **FLOOR** | | | | |
| floor_level | `str` | `str` | `TEXT` | ground/intermediate/top |
| floor_number | `int` | `int` | `INTEGER` | |
| **AMENITIES** | | | | Type: `bool` |
| has_elevator | `bool` | `bool` | `BOOLEAN` | |
| is_exterior | `bool` | `bool` | `BOOLEAN` | |
| has_terrace | `bool` | `bool` | `BOOLEAN` | |
| has_balcony | `bool` | `bool` | `BOOLEAN` | |
| has_pool | `bool` | `bool` | `BOOLEAN` | |
| has_garage | `bool` | `bool` | `BOOLEAN` | |
| has_garden | `bool` | `bool` | `BOOLEAN` | |
| has_storage | `bool` | `bool` | `BOOLEAN` | |
| has_air_conditioning | `bool` | `bool` | `BOOLEAN` | |
| has_wardrobes | `bool` | - | `BOOLEAN` | Listing only |
| is_accessible | `bool` | - | `BOOLEAN` | Listing only |
| **ORIENTATIONS** | | | | |
| balcony_orientation | `str` | - | `TEXT` | N/S/E/W/NE/etc |
| terrace_orientation | `str` | - | `TEXT` | |
| **TEXT** | | | | |
| title | `str` | - | `TEXT` | Listing only |
| description | `str` | - | `TEXT` | Listing only |
| rooms_and_amenities | `str` | - | `TEXT` | |
| **FEATURES** | | | | |
| features | `List[str]` | `Dict` | `JSONB` | Different types! |
| amenities | `List[str]` | - | `JSONB` | Listing only |
| additional_features | `List[str]` | - | `JSONB` | Listing only |
| **PHOTOS** | | | | |
| photo_urls | `List[str]` | `List[str]` | `JSONB[]` / table | |
| **CLUSTERS** | | | | |
| photo_clusters | `Dict[str,List[int]]` | `Dict[str,List[int]]` | `JSONB` | From clustering |
| ai_renders_detected | `List[int]` | `List[int]` | `JSONB` | Indices |
| **AGENCY** | | | | |
| agency | `Dict` | - | `JSONB` | Listing only |

---

## Part 8: PropertyIntelligenceReport (PIR) Schema - V0.4.8

> **PIR is ENHANCED in V0.4.8** - See Part 7A for full pre-processing architecture.

The 9-phase estimator receives PIRs for both TARGET and COMPARABLES. 
PIR captures EVERYTHING about a property from two perspectives:
1. **Architect's Eye** - Technical: structure, systems, materials
2. **Homeowner's Eye** - Feel: atmosphere, livability, impression

**Location**: `backend/pipeline/schemas/property_intelligence.py` (to be updated)

### PIR Input Chain

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PIR → ESTIMATOR INPUT FLOW                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. SCRAPE                                                                   │
│     └── ScrapedData (all listing fields, photos)                            │
│                                                                              │
│  2. CLUSTER (zero-shot)                                                      │
│     └── PhotoClusters (room assignments, AI detection)                      │
│                                                                              │
│  3. PIR GENERATION (Gemini + cached context)                                 │
│     ├── Input: ScrapedData + PhotoClusters + ALL photos                     │
│     └── Output: PropertyIntelligenceReportV048                              │
│                                                                              │
│  4. ESTIMATOR (9-phase)                                                      │
│     ├── Input: target_pir + comparable_pirs + raw photos                    │
│     └── Output: UnifiedEstimate                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key PIR Sections for Estimator

```python
class PropertyIntelligenceReportV048:
    """Enhanced PIR for V0.4.8 - Full architect + homeowner perspective."""
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    listing_id: int
    version: str = "v0.4.8"
    photos_analyzed: int
    clusters_identified: int
    ai_renders_detected: int
    
    # ═══════════════════════════════════════════════════════════════════════
    # BUILDING-LEVEL (from photos + cadastre + listing)
    # ═══════════════════════════════════════════════════════════════════════
    building_profile:
        year_built: int  # From cadastre or estimated
        year_source: str  # "cadastre" | "listing" | "estimate"
        construction_era: str  # From interior_design_knowledge
        building_type: str  # multi_family_block, townhouse, etc.
        floor: Optional[int]
        total_floors: Optional[int]
        orientation: Optional[str]
        facade_material: Optional[str]
        energy: EnergyProfile
    
    # ═══════════════════════════════════════════════════════════════════════
    # STRUCTURAL (Architect's technical eye)
    # ═══════════════════════════════════════════════════════════════════════
    structural:
        structural_system: str  # load_bearing_masonry, concrete_frame, etc.
        load_bearing_walls_identified: List[str]
        floor_construction: str
        ceiling_type: str
        ceiling_height_estimate: str
        visible_beams_columns: List[str]
        structural_concerns: List[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # TECHNICAL SYSTEMS (What needs updating)
    # ═══════════════════════════════════════════════════════════════════════
    technical_systems:
        electrical_era: str
        electrical_panel_type: Optional[str]
        outlet_density: str
        visible_wiring_concerns: List[str]
        plumbing_material: Optional[str]
        drainage_concerns: List[str]
        water_heater_type: Optional[str]
        heating_system: Optional[str]
        cooling_system: Optional[str]
        ventilation_type: str
        smart_home_features: List[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # WINDOWS & DOORS (Energy + aesthetic)
    # ═══════════════════════════════════════════════════════════════════════
    windows_doors:
        window_frame_material: str
        glazing_type: str
        window_condition: str
        thermal_bridge_indicators: List[str]
        door_quality: str
        interior_door_style: str
    
    # ═══════════════════════════════════════════════════════════════════════
    # MATERIALS INVENTORY (For pricing)
    # ═══════════════════════════════════════════════════════════════════════
    materials_inventory:
        flooring: Dict[str, str]  # {"living": "Oak parquet 10cm"}
        flooring_condition: Dict[str, str]
        wall_finishes: Dict[str, str]
        ceiling_finishes: Dict[str, str]
        skirting_type: str
        kitchen_cabinets: str
        kitchen_countertop: str
        kitchen_appliances_quality: str
        bathroom_fixtures: Dict[str, str]
        bathroom_tiles: Dict[str, str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # DESIGN PROFILE (For comparable matching)
    # ═══════════════════════════════════════════════════════════════════════
    design_profile:
        dominant_style: str
        era_authenticity: str
        updates_detected: List[str]
        finish_quality_overall: str
        color_palette_overall: List[str]
        layout: LayoutAssessment
        natural_light_assessment: Dict[str, str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # HOMEOWNER FEEL (Livability assessment)
    # ═══════════════════════════════════════════════════════════════════════
    homeowner_feel:
        overall_atmosphere: str  # cold_institutional → luxurious
        brightness: str
        sense_of_space: str
        natural_light_quality: str
        storage_adequacy: str
        privacy_assessment: str
        noise_indicators: List[str]
        first_impression: str  # Open-ended
        standout_features: List[str]
        immediate_concerns: List[str]
        family_friendly: bool
        entertaining_space: str
        work_from_home_suitable: bool
        outdoor_space: str
    
    # ═══════════════════════════════════════════════════════════════════════
    # ROOM-BY-ROOM (Detailed per-room analysis)
    # ═══════════════════════════════════════════════════════════════════════
    rooms: List[EnhancedRoomAnalysis]
        room_id: str
        room_type: str
        photos: List[str]
        area_m2_estimate: Optional[float]
        ceiling_height: str
        shape: str
        structural_elements: List[str]
        technical_systems: List[str]
        materials: Dict[str, str]
        condition_technical: str
        style_detected: str
        finish_tier: str
        atmosphere: str
        natural_light: str
        visible_defects: List[str]
        renovation_opportunities: List[str]
        uniclass_systems: List[str]  # Ss codes
        uniclass_products: List[str]  # Pr codes
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGULATORY & TRIGGERS (For permit/timeline planning)
    # ═══════════════════════════════════════════════════════════════════════
    regulatory_assessment:
        cte_concerns: List[CTEConcern]
        rebt: REBTAssessment
        ite: ITEProjection
    
    triggers: List[RenovationTrigger]
    
    # ═══════════════════════════════════════════════════════════════════════
    # YEAR-IMPLIED POSSIBILITIES (Context, NOT requirements)
    # ═══════════════════════════════════════════════════════════════════════
    # Based on construction year and rules_engine.json regulatory thresholds.
    # These are POSSIBILITIES for the estimator to consider, not mandates.
    # PIR validates what's VISIBLE vs what's IMPLIED by year.
    # ═══════════════════════════════════════════════════════════════════════
    year_context:
        year_built: int                    # From cadastre/listing/estimate
        year_source: str                   # "cadastre" | "listing" | "street_sample" | "estimate"
        year_confidence: str               # "verified" | "sampled" | "estimated"
        
        # What MIGHT be behind the walls based on construction era
        implied_possibilities: List[YearImpliedPossibility]
            system: str                    # "electrical" | "plumbing" | "insulation" | etc.
            rule_id: str                   # "ELEC_001", "PLUMB_001"
            regulation: str                # "REBT 2002", "CTE DB-HE"
            year_threshold: int            # Pre-this year = possible issue
            possibility: str               # "Pre-2002 electrical system possible"
            visual_evidence: Optional[str] # "Visible 2-pin outlets confirm"
            visual_contradicts: Optional[str] # "Modern panel visible - likely upgraded"
            confidence: str                # "confirmed" | "possible" | "unlikely"
            
        # Systems where visual evidence CONFIRMS year-implied issue
        confirmed_by_visual: List[str]     # ["electrical_panel_old", "lead_pipe_visible"]
        
        # Systems where visual evidence CONTRADICTS year-implied issue
        contradicted_by_visual: List[str]  # ["electrical_appears_modern", "copper_pipes_visible"]
        
        # For COMPARABLES: What we think was UPGRADED to achieve current condition
        # (Only populated for comparables, empty for target)
        likely_prior_upgrades: List[str]   # ["electrical_upgraded", "plumbing_upgraded"]
        upgrade_reasoning: Optional[str]   # "1970 building in 'very good' condition..."
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMPARISON ATTRIBUTES (Structured for matching)
    # ═══════════════════════════════════════════════════════════════════════
    comparison_attributes:
        energy_rating: Optional[str]
        envelope_condition: str
        window_type: str
        electrical_era: str
        finish_era: str
        finish_tier: str
        flooring_type: str
        layout_type: str
        kitchen_open: bool
        natural_light: str
        style: str
        structural_concerns: bool
        humidity_visible: bool
        maintenance_level: str
    
    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARIES (For quick reference)
    # ═══════════════════════════════════════════════════════════════════════
    architect_summary: str  # Technical summary paragraph
    homeowner_summary: str  # Livability summary paragraph
```

### How PIR Feeds into Estimator

The 9-phase estimator uses PIR data like this:

| Phase | PIR Data Used |
|-------|--------------|
| Phase 1: Scope Definition | `comparison_attributes`, `triggers`, `rooms[].renovation_opportunities` |
| Phase 2: Scope Check | `rooms[]`, `structural`, `technical_systems` - verify nothing missed |
| Phase 3: Work Phases | `structural`, `technical_systems`, `regulatory_assessment` |
| Phase 4: BOQ Check | `materials_inventory`, `rooms[].materials`, `rooms[].area_m2_estimate` |
| Phase 5: Pricing Strategy | `design_profile`, `homeowner_feel` for tier matching |
| Phase 6: Regional Adjust | `building_profile.year_built`, location data |
| Phase 7: Timeline | `regulatory_assessment`, `structural` |
| Phase 8: Energy | `building_profile.energy`, `windows_doors`, `technical_systems` |
| Phase 9: Sanity Check | All sections for final verification |

**How PIR is Generated**: See Part 7A (Pre-Processing) and `backend/pipeline/steps/property_intelligence.py`

---

## Part 9: Energy Task Enrichment (From V0.3.1)

47 KG tasks are energy-relevant and should have `energy_impact` metadata.

**Tasks to Enrich** (patterns):
- `*insulation*` - Wall, roof, floor insulation
- `*window*`, `*ventana*` - Window replacement
- `*hvac*`, `*climatizacion*`, `*calefaccion*` - HVAC systems
- `*solar*` - Solar thermal, PV
- `*aislamiento*` - General insulation
- `*fachada*` with thermal intent - Facade upgrades

**Energy Impact Schema**:
```yaml
task_id: wall_insulation_sate
energy_impact:
  affects_u_value: true
  element: "wall"  # wall, roof, floor, window, system
  typical_letters_improvement: 1.5  # Average letter improvement
  climate_sensitivity: "high"  # high/medium/low - more impact in cold climates
  notes: "SATE/ETICS system, exterior application, no interior space loss"
```

**Implementation**: 
1. Script identifies 47 tasks by pattern matching
2. Gemini enriches each with energy_impact based on energy_knowledge.json
3. `flatten_kg.py` includes energy_impact in kg_context.yaml
4. System instruction references energy_impact for intervention selection

**Status**: ❌ NOT YET DONE - Add to implementation Phase 2

---

## Part 10: Preserved Decisions from Audit

These decisions were made during V0.3.x development and MUST carry through:

### ✅ BACKGROUND EXECUTION + CHECKPOINTING + LOGGING

**Architecture**: Pipeline runs in background, not tied to HTTP connection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKGROUND JOB ARCHITECTURE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend: POST /make-packages → Returns job_id immediately                  │
│            GET /package-progress/{job_id} → Poll for status                  │
│                                                                              │
│  Backend: Job runs in background thread/process                              │
│           User can close browser - job continues                             │
│           Progress stored in DB - survives server restart                    │
│                                                                              │
│  Checkpoints: After each major step, save to DB                              │
│               If downstream fails, resume from last checkpoint               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Checkpointing Strategy**:
```python
CHECKPOINTS = {
    "clustering_complete": "photo_clusters_v048 populated",
    "year_estimation_complete": "year_built in progress table",
    "pir_target_complete": "PIR for target in property_intelligence_reports_v048",
    "pir_comparables_complete": "PIRs for all 9 comparables",
    "estimate_fast_sell_complete": "unified_estimates_v048 row for fast_sell",
    "estimate_fair_market_complete": "unified_estimates_v048 row for fair_market",
    "estimate_out_of_market_complete": "unified_estimates_v048 row for out_of_market",
    "visuals_complete": "All before/after images uploaded",
}

# Resume logic
async def make_packages(listing_id: int):
    progress = await get_progress(listing_id)
    
    if not progress.get("clustering_complete"):
        await run_clustering(listing_id)
        await save_checkpoint(listing_id, "clustering_complete")
    
    if not progress.get("pir_target_complete"):
        await run_pir_target(listing_id)
        await save_checkpoint(listing_id, "pir_target_complete")
    
    # ... etc - each step checks checkpoint before running
```

**Logging Strategy** (foreground-friendly):
```python
import logging

# Configure for readable foreground output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("v048_pipeline")

# Log with context
logger.info("=" * 60)
logger.info(f"STEP 1: CLUSTERING | listing_id={listing_id}")
logger.info("=" * 60)
logger.info(f"  → Found {len(photos)} photos for target")
logger.info(f"  → Found {len(comparables)} comparables with photos")

# Log progress
logger.info(f"  → Clustering target photos...")
logger.info(f"  ✓ Created {len(clusters)} clusters")
for c in clusters:
    logger.info(f"    - {c['room_type']}: {len(c['photos'])} photos")

# Log checkpoints
logger.info(f"  💾 CHECKPOINT: clustering_complete")
```

**Test Script** (`scripts/test_v048_pipeline.py`):
```python
#!/usr/bin/env python3
"""
Test V0.4.8 pipeline from terminal.

Usage:
    python scripts/test_v048_pipeline.py --listing-id 12345 --clear-data
    
Options:
    --listing-id: Which listing to test
    --clear-data: Clear all V0.4.8 data EXCEPT comparables (save Casafari calls)
    --from-checkpoint: Resume from specific checkpoint
    --verbose: Extra logging
"""
import asyncio
import argparse
from pipeline.package_orchestrator import PackageOrchestrator

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--clear-data", action="store_true")
    parser.add_argument("--from-checkpoint", type=str, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    
    if args.clear_data:
        print(f"🗑️  Clearing V0.4.8 data for listing {args.listing_id}...")
        await clear_v048_data(args.listing_id, keep_comparables=True)
        print(f"   ✓ Cleared (kept comparables)")
    
    print(f"\n🚀 Starting V0.4.8 pipeline for listing {args.listing_id}")
    print("=" * 60)
    
    orchestrator = PackageOrchestrator(verbose=args.verbose)
    
    try:
        result = await orchestrator.make_packages(
            listing_id=args.listing_id,
            from_checkpoint=args.from_checkpoint
        )
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"  Packages generated: {len(result['packages'])}")
        for pkg in result['packages']:
            print(f"    - {pkg['package_type']}: €{pkg['total_price']:,}")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
```

**Clear Data Function**:
```python
async def clear_v048_data(listing_id: int, keep_comparables: bool = True):
    """
    Clear V0.4.8 pipeline data for a listing.
    Keeps comparables by default to save Casafari API calls.
    """
    tables_to_clear = [
        "package_generation_progress",
        "photo_clusters_v048",
        "property_intelligence_reports_v048",
        "unified_estimates_v048",
    ]
    
    for table in tables_to_clear:
        await supabase.table(table).delete().eq("listing_id", listing_id).execute()
    
    # Delete visuals from storage
    await supabase.storage.from_("package-visuals").remove([f"{listing_id}/*"])
    
    if not keep_comparables:
        # This would also clear listing_comparables table
        await supabase.table("listing_comparables").delete().eq("listing_id", listing_id).execute()
    
    logger.info(f"Cleared V0.4.8 data for listing {listing_id}, keep_comparables={keep_comparables}")
```

---

### ✅ FAIL LOUD AND FAST - NO RETRIES, NO FALLBACKS

**Philosophy**: If something fails, we want to know immediately. No silent degradation.

**Gemini Configuration**:
```python
# PIR Generation
PIR_CONFIG = {
    "max_output_tokens": 65536,  # 65k ensures no truncation
    "temperature": 0.2,
}

# 9-Phase Estimator  
ESTIMATION_CONFIG = {
    "max_output_tokens": 65536,  # 65k ensures no truncation
    "temperature": 0.1,
}
```

**Error Handling**:
```python
# WRONG - Silent fallback
try:
    result = await gemini_call(...)
except Exception:
    return DEFAULT_VALUE  # ❌ Never do this

# RIGHT - Fail immediately
result = await gemini_call(...)  # Let it raise
# If we get here, it worked
```

**Why 65k maxOutputTokens?**
- PIR for large property: ~20-30k tokens
- 9-phase estimate: ~30-40k tokens
- 65k gives headroom without ever truncating

### ✅ NO V1 FALLBACKS
- If validation fails, raise exception with structured error
- NEVER fall back to old renovation_resolver.py
- Old system produced garbage (€53 bathrooms, 75% "General")

### ✅ NO PRICE SANITY RANGES
- Don't hardcode "tiles should cost €25-60/m²"
- This creates bias and rejects valid BCCA matches
- Let BCCA prices speak for themselves

### ✅ NO CHAPTER 18 CODES
- Chapter 18 = test items, not real construction
- Filter at load in bcca_search.py (line 319)
- Don't tell LLM "avoid Chapter 18" - just don't include them

### ✅ STRUCTURAL KEYWORD PATTERNS
- Don't give specific examples like "for tiles, search 'alicatado azulejo'"
- Instead give patterns: [action] + [material] + [specification]
- Prevents pigeonholing, enables universal application

### ✅ ROOM ATTRIBUTION VALIDATION
- Target: <30% of costs in "General"
- Each task should have specific room
- Only whole-property work (electrical panel, water main) goes to "General"

### ✅ REASONING CHAINS REQUIRED
- Every BoQ line item needs:
  - Why this task (gap → intervention → task)
  - Why this BCCA code (query → results → selection reason)
  - Why this quantity (dimensions → formula → result)
- This enables debugging and customer trust

### ✅ FULL QUANTITY GUIDANCE IN KG
- kg_context.yaml includes full quantity_guidance per task
- scope, typical_rules, constraints, unit
- Don't strip this - Gemini needs it for quantity reasoning

---

## Part 11: Structured Error Response

When validation fails, return structured error (not just exception):

```python
class EstimationError(BaseModel):
    """Structured error for API responses."""
    success: bool = False
    error_code: str  # "ROOM_ATTRIBUTION_LOW", "KG_GROUNDING_FAILED", etc.
    error_message: str
    details: Dict[str, Any]  # Specific issues found
    suggestions: List[str]  # How to fix
    partial_result: Optional[UnifiedEstimate]  # If any useful output

# Example error response
{
    "success": false,
    "error_code": "ROOM_ATTRIBUTION_LOW",
    "error_message": "65% of costs attributed to 'General' (target: <30%)",
    "details": {
        "general_cost": 15000,
        "total_cost": 23000,
        "general_items": ["electrical_upgrade", "plumbing_main", "painting_general"]
    },
    "suggestions": [
        "Review 'painting_general' - can this be split by room?",
        "Check if bathroom/kitchen-specific items are marked correctly"
    ],
    "partial_result": null
}
```

**Implementation**: Update `_validate()` to return structured errors instead of raising.

---

## Part 12: UI Specification (Mobile-First)

This section defines the complete UI for the Renovation tab and modal, ensuring the `UnifiedEstimate` output maps cleanly to the frontend.

### 12.1 Renovation Tab - Package Cards

The Renovation tab shows 3 package cards (based on comparable brackets):

```
┌─────────────────────────────────────┐
│  Renovation            [Language]   │
├─────────────────────────────────────┤
│                                     │
│  Tu Propiedad vs Comparables        │
│  Premium                            │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 🟢 FAST SELL PATH         [→]  ││
│  │                                 ││
│  │ €45,000 renovation • 4-6 weeks ││
│  │                                 ││
│  │ ┌─────┐    ┌─────┐              ││
│  │ │ANTES│ →  │DESP │  Cocina     ││
│  │ └─────┘    └─────┘              ││
│  │                                 ││
│  │ Margin: +€25,000                ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 🟡 FAIR MARKET PATH       [→]  ││
│  │                                 ││
│  │ €68,000 renovation • 8-10 weeks││
│  │                                 ││
│  │ ┌─────┐    ┌─────┐              ││
│  │ │ANTES│ →  │DESP │  Cocina     ││
│  │ └─────┘    └─────┘              ││
│  │                                 ││
│  │ Margin: +€42,000                ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 🔴 PREMIUM PATH           [→]  ││
│  │                                 ││
│  │ €95,000 renovation • 12-14 wks ││
│  │ ...                             ││
│  └─────────────────────────────────┘│
│                                     │
├─────────────────────────────────────┤
│ [Listing] [Renov●] [View] [Research]│
└─────────────────────────────────────┘
```

**CRITICAL**: Before/after shows **ONE ROOM only** (kitchen as hero image).

**Data Mapping**:
```typescript
interface PackageCard {
  bracket_name: string;        // "FAST SELL PATH" / "FAIR MARKET" / "PREMIUM"
  renovation_cost: number;     // From UnifiedEstimate.bill_of_quantities.grand_total
  duration_weeks: string;      // "4-6 weeks" - derived from scope complexity
  margin: number;              // target_price - (asking_price + renovation_cost)
  before_image: string;        // Target property kitchen photo URL
  after_image: string;         // Comparable property kitchen photo URL
}
```

### 12.2 Full-Screen Modal - Customer View

Triggered when user taps a package card:

```
┌─────────────────────────────────────┐
│ ← Back    FAIR MARKET PATH   [Share]│
│           Target: €410,000          │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────────┐│
│  │        💰 EL CÁLCULO            ││
│  │                                 ││
│  │  Precio Pedido       €280,000   ││
│  │  + Reforma            €68,000   ││
│  │  ─────────────────────────      ││
│  │  = Tu Inversión      €348,000   ││
│  │                                 ││
│  │  Valor Objetivo      €410,000   ││
│  │  ═════════════════════════      ││
│  │  = Margen Potencial  +€62,000   ││
│  │                                 ││
│  │  ⏱ 8-10 semanas                 ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  TRANSFORMACIÓN                 ││
│  │                                 ││
│  │  📊 Energía: G → C (+4 letras)  ││
│  │  🎨 Estilo: 1970s → Contemp.    ││
│  │  🔧 Alcance: Reforma integral   ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ANTES / DESPUÉS                ││
│  │  ┌───────────────────────┐      ││
│  │  │                       │      ││
│  │  │   ◄══════════════►    │      ││
│  │  │   COCINA SLIDER       │      ││
│  │  │                       │      ││
│  │  └───────────────────────┘      ││
│  │  ← Desliza para comparar →      ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  QUÉ INCLUYE                    ││
│  │                                 ││
│  │  ✓ Ventanas alta eficiencia     ││
│  │  ✓ Aislamiento SATE             ││
│  │  ✓ Instalación eléctrica nueva  ││
│  │  ✓ Cocina completa              ││
│  │  ✓ Baño spa walk-in             ││
│  │  ✓ Suelos madera                ││
│  │  ✓ Apertura cocina-salón        ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  🔨 DESGLOSE POR ZONA           ││
│  │                                 ││
│  │  ┌─────────────────────────┐    ││
│  │  │ Cocina        €22,500  ▼│    ││
│  │  └─────────────────────────┘    ││
│  │  ┌─────────────────────────┐    ││
│  │  │ Baño          €14,200  ▼│    ││
│  │  │ • Demolición    €800     │    ││
│  │  │ • Fontanería  €2,400     │    ││
│  │  │ • Alicatado   €4,200     │    ││
│  │  │ • Sanitarios  €3,800     │    ││
│  │  │ • Mampara     €1,200     │    ││
│  │  │ • Otros       €1,800     │    ││
│  │  └─────────────────────────┘    ││
│  │  ┌─────────────────────────┐    ││
│  │  │ Salón          €8,300  ▼│    ││
│  │  └─────────────────────────┘    ││
│  │  ┌─────────────────────────┐    ││
│  │  │ Instalaciones €18,500  ▼│    ││
│  │  └─────────────────────────┘    ││
│  │                                 ││
│  │  PEM (Material)     €52,000    ││
│  │  + Gastos Generales  €6,760    ││
│  │  + Beneficio Ind.    €3,120    ││
│  │  + IVA (21%)        €13,005    ││
│  │  ─────────────────────────      ││
│  │  Total              €68,000    ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  📅 CRONOGRAMA                  ││
│  │                                 ││
│  │  ▓▓░░░░░░ Demolición    S1-2   ││
│  │  ░░▓▓▓░░░ Instalaciones S3-5   ││
│  │  ░░░░░▓▓░ Acabados      S6-8   ││
│  │  ░░░░░░░▓ Repasos       S9-10  ││
│  │                                 ││
│  │  Estimado: 8-10 semanas         ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  COMPARABLES USADOS             ││
│  │  ┌────┐ ┌────┐ ┌────┐ ←scroll   ││
│  │  │ 📷 │ │ 📷 │ │ 📷 │          ││
│  │  │€410k│ │€395k│ │€425k│        ││
│  │  │95m² │ │92m² │ │98m² │        ││
│  │  └────┘ └────┘ └────┘          ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ☑️ CHECKLIST PARA VISITA       ││
│  │  ☐ Verificar estado ventanas    ││
│  │  ☐ Localizar cuadro eléctrico   ││
│  │  ☐ Revisar humedades baño       ││
│  │  ☐ Confirmar orientación        ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  🛡️ NORMATIVA APLICABLE         ││
│  │  ✓ Cédula de Habitabilidad     ││
│  │  ✓ REBT 2002 (eléctrico)       ││
│  │  ✓ CTE DB-HE (energía)         ││
│  │                                 ││
│  │  📚 Fuentes: CTE 2022 · IDAE    ││
│  │             CE3X · CSCAE        ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  [Exportar para Arquitecto]     ││
│  └─────────────────────────────────┘│
│                                     │
│           [Cerrar]                  │
└─────────────────────────────────────┘
```

**Data Mapping for Customer Modal**:
```typescript
interface CustomerModal {
  // THE MATH
  asking_price: number;              // From listing data
  renovation_cost: number;           // UnifiedEstimate.bill_of_quantities.grand_total
  total_investment: number;          // asking_price + renovation_cost
  target_price: number;              // Comparable bracket average
  margin: number;                    // target_price - total_investment
  duration_weeks: string;            // Derived from scope
  
  // TRANSFORMATION
  energy_gap: {
    from: string;                    // "G"
    to: string;                      // "C"
    letters_improved: number;        // 4
  };
  style_change: {
    from: string;                    // "Traditional 1970s"
    to: string;                      // "Contemporary"
  };
  scope_level: string;               // "Reforma integral"
  
  // BEFORE/AFTER (ONE ROOM ONLY - KITCHEN)
  before_image: string;              // Target property kitchen photo
  after_image: string;               // Comparable property kitchen photo
  room_shown: "kitchen";             // Always kitchen for hero
  
  // QUÉ INCLUYE (bullets from gap analysis)
  included_items: string[];          // Human-readable summaries from gap_analysis.identified_gaps
  
  // DESGLOSE POR ZONA
  room_breakdown: Array<{
    room_name: string;               // "Cocina"
    room_total: number;              // From bill_of_quantities.room_totals
    expanded: boolean;               // UI state
    line_items: Array<{              // From bill_of_quantities.line_items filtered by room
      task_name: string;
      total: number;
    }>;
  }>;
  
  // COST SUMMARY
  pem: number;                       // Material execution budget
  gastos_generales: number;          // 13% of PEM
  beneficio_industrial: number;      // 6% of PEM
  iva: number;                       // 10% or 21% depending on conditions
  grand_total: number;               // Final total
  
  // CRONOGRAMA
  timeline: Array<{
    phase: string;                   // "Demolición"
    weeks: string;                   // "S1-2"
    progress_bar: number;            // 0-1 for bar width
  }>;
  
  // COMPARABLES
  comparables: Array<{
    image_url: string;
    price: number;
    area_m2: number;
    casafari_url: string;
  }>;
  
  // CHECKLIST
  viewing_checklist: string[];       // Generated from gap analysis
  
  // NORMATIVA
  applicable_standards: Array<{
    name: string;                    // "Cédula de Habitabilidad"
    status: "required" | "recommended";
  }>;
  sources: string[];                 // "CTE 2022", "IDAE", "CE3X", "CSCAE"
}
```

### 12.3 Architect Export View

Full technical detail for professionals:

```
┌─────────────────────────────────────┐
│ INFORME TÉCNICO DE REFORMA          │
│ Listing #123 • Fair Market Path     │
├─────────────────────────────────────┤

1. DATOS DEL INMUEBLE
────────────────────────────────────
Dirección: [From listing]
Superficie: [m² from listing]
Año construcción: [From PIR building_profile]
Zona climática: [From PIR + energy_knowledge]
Certificación energética: [from] → [to]

2. SISTEMAS EXISTENTES (Uniclass)
────────────────────────────────────
[For each room from PIR.room_analyses]:
  ROOM_NAME:
  • Ss_XX_XX System: [description]
    Estado ITE: [condition]
  • Pr_XX_XX Product: [description]
    Material: [material], Estado: [condition]

3. MEDICIONES Y PRESUPUESTO (BCCA 2024)
────────────────────────────────────

[For each room from bill_of_quantities.room_totals]:

ROOM_NAME (€room_total)
────────────────────────────────────
| Código    | Descripción          | Ud  | Cant | PU    | Total |
|-----------|---------------------|-----|------|-------|-------|
[For each line_item in room]:
| bcca_code | bcca_description    | unit| qty  | price | total |

RESUMEN ECONÓMICO
────────────────────────────────────
PEM (Presupuesto Ejecución Material)     €[sum of all tasks]
Gastos Generales (13%)                   €[13% of PEM]
Beneficio Industrial (6%)                €[6% of PEM]
────────────────────────────────────────────────────
PEC (Presupuesto Ejecución Contrata)     €[PEM + GG + BI]
IVA (10% reforma vivienda)               €[10% or 21%]
────────────────────────────────────────────────────
TOTAL PRESUPUESTO                        €[grand_total]

4. CRONOGRAMA
────────────────────────────────────
[Timeline breakdown with week ranges]

5. NORMATIVA APLICABLE
────────────────────────────────────
• CTE DB-HE 2022 - Ahorro de energía
• CTE DB-HS 2022 - Salubridad
• REBT 2002 - Reglamento electrotécnico
• [Other applicable standards]

6. ANEXOS
────────────────────────────────────
• A: Comparables utilizados (URLs)
• B: Fichas BCCA de partidas principales
• C: Trazabilidad KG (reasoning chains from UnifiedEstimate.reasoning_chain)

────────────────────────────────────
Generado por Reformia V0.4
Fuentes: BCCA 2024, CTE 2022, IDAE CE3X
Disclaimer: Presupuesto orientativo...
```

**Data Mapping for Architect View**:
```typescript
interface ArchitectExport {
  // Full UnifiedEstimate passed through
  estimate: UnifiedEstimate;
  
  // Additional PIR data
  pir: PropertyIntelligenceReport;
  
  // Listing data
  listing: {
    address: string;
    area_m2: number;
    asking_price: number;
  };
  
  // Format options
  output_format: "pdf" | "json" | "excel";
}
```

### 12.4 Customer View vs Architect Export - Quick Reference

```
┌──────────────────────────────────────────────────────────────────────────────┐
│            CUSTOMER VIEW (Mobile Modal)  vs  ARCHITECT EXPORT (PDF/JSON)     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PURPOSE                                                                     │
│  ───────                                                                     │
│  Customer: "Should I buy this property?" → Simplicity, trust, investment    │
│  Architect: "How do I quote/execute this?" → Full detail, nothing hidden    │
│                                                                              │
│  WHAT'S SHOWN                                                                │
│  ────────────                                                                │
│  Customer:                          Architect:                               │
│  ✓ The Math (investment vs value)   ✓ Full BCCA codes per line item         │
│  ✓ What's included (bullets)        ✓ Quantities + units (m², ud, ml)       │
│  ✓ Room totals (collapsed)          ✓ All room line items (expanded)        │
│  ✓ Timeline (phase bars)            ✓ Detailed scheduling                   │
│  ✓ Before/After (1 room only)       ✓ Full reasoning chain (Annex C)        │
│  ✓ Viewing checklist                ✓ Uniclass system codes                 │
│  ✓ Next steps (inspections)         ✓ KG task references                    │
│  ✓ Simplified disclaimer            ✓ Full professional disclaimer          │
│                                                                              │
│  WHAT'S HIDDEN                                                               │
│  ─────────────                                                               │
│  Customer:                          Architect:                               │
│  × BCCA codes                       (nothing hidden)                         │
│  × Unit prices                                                               │
│  × Reasoning steps                                                           │
│  × Validation metrics                                                        │
│  × Technical dependencies                                                    │
│                                                                              │
│  LANGUAGE                                                                    │
│  ────────                                                                    │
│  Customer: Friendly Spanish         Architect: Technical Spanish             │
│  "Cocina completa"                  "09ACE00130 - Alicatado gres porcelánico"│
│                                                                              │
│  FORMAT                                                                      │
│  ──────                                                                      │
│  Customer: Mobile-first modal       Architect: PDF / JSON / Excel            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.4.1 Data Flow: UnifiedEstimate → UI

```
UnifiedEstimate
├── gap_analysis
│   ├── comparisons[]            → Customer: "Transformación" section
│   │   └── energy_gap, style    → Architect: Section 1 analysis
│   └── identified_gaps[]        → Customer: "Qué incluye" bullets
│                                → Customer: "Checklist para visita"
│
├── scope
│   ├── rooms[]                  → Both: Room names for breakdown
│   └── interventions[]          → Architect: KG task references
│
├── bill_of_quantities
│   ├── line_items[]             → Customer: Collapsed (totals only)
│   │                            → Architect: Full table with BCCA codes
│   ├── room_totals[]            → Customer: "Desglose por zona" headers
│   │                            → Architect: Room subtotals
│   └── grand_total              → Customer: "El Cálculo" renovation cost
│                                → Architect: PEM line in summary
│
├── reasoning_chain[]            → Customer: (hidden)
│                                → Architect: Annex C full chain
│
├── inspection_recommendations[] → Customer: "Próximos Pasos" section  ⭐ V0.4.8
│                                → Architect: Section 7 - Pre-purchase inspections
│
├── year_context_summary         → Customer: "Contexto del Edificio" card  ⭐ V0.4.8
│                                → Architect: Section 1 - Building analysis
│
├── disclaimer                   → Customer: Footer (simplified)  ⭐ V0.4.8
│                                → Architect: Full legal text
│
└── validation
    ├── room_attribution_pct     → Customer: (hidden)
    ├── kg_grounding_pct         → Architect: QA metrics
    └── bcca_match_pct           → (internal only)
```

### 12.4.2 New V0.4.8 Sections Mapping

| New Field | Location | Customer View | Architect View |
|-----------|----------|--------------|----------------|
| `year_context_summary` | **LISTING TAB** (below listing info) | "Contexto del Edificio" card | Section 1: Building analysis |
| `inspection_recommendations[]` | Package Modal | "Próximos Pasos" card | Section 7: Pre-purchase inspections |
| `disclaimer` | Package Modal footer | 3-line simplified | Full legal text |

**LISTING TAB - "Contexto del Edificio" Card:**
```
┌─────────────────────────────────────────────────────────────────┐
│  LISTING TAB (Property Page)                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🏠 Listing Info Card (existing)                        │   │
│  │  €280,000 · 3 bed · 2 bath · 95m²                       │   │
│  │  Calle Example 15, Centro, Madrid                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🏗️ CONTEXTO DEL EDIFICIO                    ⭐ NEW V0.4.8 │
│  │                                                         │   │
│  │  Año construcción: 1975                                 │   │
│  │  Fuente: Catastro oficial ✓                             │   │
│  │                                                         │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │                                                         │   │
│  │  ✅ Confirmado visualmente:                             │   │
│  │     • Panel eléctrico antiguo (pre-2002)               │   │
│  │                                                         │   │
│  │  ❓ Posible (inspección recomendada):                   │   │
│  │     • Tuberías originales (no visibles)                │   │
│  │     • Aislamiento térmico limitado (pre-CTE)           │   │
│  │                                                         │   │
│  │  ❌ Descartado visualmente:                             │   │
│  │     • Ventanas: PVC reciente visible                   │   │
│  │                                                         │   │
│  │  ℹ️ Este análisis se basa en el año de construcción    │   │
│  │     y las fotos del anuncio.                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Photo Gallery (existing)                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**PACKAGE MODAL - "Próximos Pasos" Card:**
```
┌─────────────────────────────────────────┐
│  📋 PRÓXIMOS PASOS                      │
│                                         │
│  Antes de comprar, recomendamos:        │
│                                         │
│  ⚡ Inspección eléctrica                │
│     Motivo: Sistema pre-2002 posible    │
│     Coste aprox: €100-150               │
│                                         │
│  🔧 Revisión fontanería                 │
│     Motivo: No visible en fotos         │
│     Coste aprox: €80-120                │
│                                         │
│  💡 Estos presupuestos son para la      │
│     inspección, no la reforma.          │
└─────────────────────────────────────────┘
```

**Data Source:**
- `year_context_summary` comes from the **PIR** (property-level analysis)
- Displayed on Listing Tab for ALL users viewing the property
- NOT tied to a specific package - it's property context

### 12.5 UI Component Checklist

| Component | Data Source | Status |
|-----------|-------------|--------|
| Package cards (3) | `grand_total`, `duration`, `margin` | ⬜ Implement |
| Before/After slider | Target/Comparable kitchen photos | ⬜ ONE ROOM ONLY |
| "El Cálculo" | Listing price + `grand_total` | ⬜ Implement |
| "Transformación" | `gap_analysis.comparisons` energy/style | ⬜ Implement |
| "Qué incluye" | `gap_analysis.identified_gaps` → bullets | ⬜ Implement |
| "Desglose por zona" | `bill_of_quantities.room_totals` | ⬜ Expandable accordion |
| Room line items | `bill_of_quantities.line_items` | ⬜ Inside accordion |
| Cost summary | PEM + GG + BI + IVA | ⬜ Implement |
| Timeline | Derived from scope complexity | ⬜ Phase bars |
| Comparables carousel | From bracket selection | ⬜ Horizontal scroll |
| Viewing checklist | From `gap_analysis` | ⬜ Checkboxes |
| Standards compliance | From PIR regulatory | ⬜ List |
| Architect export button | Full `UnifiedEstimate` | ⬜ PDF/JSON |

### 12.6 Before/After Image Rules

**CRITICAL: ONE ROOM ONLY**

```typescript
// CORRECT - Kitchen only as hero
const beforeAfterConfig = {
  room: "kitchen",  // ALWAYS kitchen for MVP
  before: targetPropertyKitchenPhoto,
  after: comparablePropertyKitchenPhoto
};

// WRONG - Multiple rooms (future enhancement)
const beforeAfterConfig = {
  rooms: ["kitchen", "bathroom", "living"] // NOT FOR MVP
};
```

**Why kitchen?**
1. Highest renovation impact visually
2. Most comparable across properties
3. Best represents quality delta
4. Single image reduces complexity

**Future enhancement**: Carousel of multiple rooms (post-MVP).

---

## Part 13: Complete System Summary

### 13.1 The Full Pipeline (Visual)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      V0.4: UNIFIED PROPERTY INTELLIGENCE                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 0: KNOWLEDGE EXTRACTION (One-time setup) ✅ DONE                     │
│  ──────────────────────────────────────────────                             │
│  ├── energy_knowledge.json ✅ DONE                                          │
│  ├── renovation_process_knowledge.json ✅ DONE                              │
│  └── interior_design_knowledge.json ✅ DONE                                 │
│      └── Gemini synthesized: styles, finishes, materials, eras             │
│                                                                             │
│  PHASE 1: PROPERTY INTELLIGENCE REPORT (Per property) ⬜ IMPLEMENT          │
│  ────────────────────────────────────────────────────────                   │
│  One Gemini call per property → Comprehensive "study"                       │
│  Output: PropertyIntelligenceReport (PIR)                                   │
│                                                                             │
│  PHASE 2: UNIFIED ESTIMATOR (Target vs Comparables) ⬜ IMPLEMENT            │
│  ──────────────────────────────────────────────────────                     │
│  ONE Gemini call with:                                                      │
│  - System instruction (250K tokens: KG + KBs + BCCA-speak)                 │
│  - Target PIR + photos + listing                                            │
│  - Comparable PIRs                                                          │
│  - discover_bcca tool for pricing (SQL + LLM selection)                    │
│  Output: UnifiedEstimate (gap + scope + BoQ + reasoning)                   │
│                                                                             │
│  PHASE 3: FORMAT VIEWS (Customer + Architect) ⬜ IMPLEMENT                  │
│  ─────────────────────────────────────────────                              │
│  Python formatting from UnifiedEstimate →                                   │
│  - Customer view (layman summary)                                           │
│  - Architect view (full BCCA technical detail)                              │
│                                                                             │
│  PHASE 4: MOBILE-FIRST UI ⬜ IMPLEMENT                                      │
│  ────────────────────────                                                   │
│  - Renovation tab: 3 package cards                                          │
│  - Full-screen modal: customer-friendly breakdown                           │
│  - Before/After: ONE ROOM ONLY (kitchen)                                    │
│  - Architect export: PDF/JSON                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 What Gets Built

> **NOTE**: See [Part 7: Implementation Checklist](#part-7-implementation-checklist-v048---9-phase-architecture) for the COMPLETE and up-to-date file inventory.

**Legacy file list (kept for reference, see Part 7 for authoritative version):**

| Component | Status |
|-----------|--------|
| `pricing/data/ffe.db` | ✅ DONE (202 items) |
| `scripts/parse_ffe_research.py` | ✅ DONE |
| `scripts/research_ffe_expansion.py` | ✅ DONE |
| `scripts/paraphrase_bcca_descriptions.py` | ✅ DONE (12,565 items) |
| All other files | See Part 7 for complete list |

### 13.3 What Already Exists (Reuse)

| Asset | Location | Status |
|-------|----------|--------|
| Knowledge Graph (683 tasks) | `data/hybrid_renovation_graph.json` | ✅ Ready |
| KG flattened | `pricing/kg_context.yaml` | ✅ 214K tokens |
| BCCA database | `pricing/data/construction.db` | ✅ 12K items |
| ~~BCCA embeddings~~ | ~~`pricing/data/bcca_embeddings.npy`~~ | ❌ Deprecated (V0.4 uses SQL) |
| **FFE database** | **`pricing/data/ffe.db`** | **✅ 202 items (Gemini 3 Pro research)** |
| Energy knowledge | `standards/energy_knowledge.json` | ✅ Ready |
| Process knowledge | `standards/renovation_process_knowledge.json` | ✅ Ready |
| Interior design KB | `standards/interior_design_knowledge.json` | ✅ Ready |
| PIR schema | `pipeline/schemas/property_intelligence.py` | ✅ Exists |
| UI components | `frontend/src/components/renovation/` | ⬜ Needs data wiring |

### 13.3.1 FFE Database Details (ffe.db)

**Created**: 2026-01-11 via Gemini 3 Pro research
**Items**: 202 granular FF&E items
**Schema features**:
- 4 price tiers (budget/mid/high/luxury) with low/mid/high values each
- Brand references per tier (Spanish market: IKEA, Kave Home, Marset, Poliform, etc.)
- Style matching tags for adaptation framework
- Investment priority (76 alta, 79 media, 47 baja)
- Lifespan and energy relevance metadata
- Documented basis_notes per item

**Categories**:
| Category | Items |
|----------|-------|
| Mobiliario de Dormitorio (includes kids) | 39 |
| Accesorios de Baño | 21 |
| Iluminación Decorativa | 21 |
| Textiles y Complementos | 21 |
| Mobiliario de Comedor | 20 |
| Despacho / Oficina en Casa (includes home tech) | 20 |
| Electrodomésticos de Cocina | 20 |
| Mobiliario de Salón | 20 |
| Mobiliario Exterior | 20 |

### 13.4 Critical Rules (Never Violate)

| Rule | Rationale |
|------|-----------|
| **NO V1 FALLBACKS** | V1 produced garbage (€53 bathrooms, 75% "General") |
| **NO HARDCODED PRICES** | Creates bias, rejects valid BCCA matches |
| **NO CHAPTER 18 CODES** | Test items, not real construction |
| **KITCHEN ONLY FOR BEFORE/AFTER** | MVP simplicity, highest impact |
| **<30% GENERAL ATTRIBUTION** | Forces room-level granularity |
| **100% KG GROUNDING** | Every task must trace to KG |
| **100% BCCA GROUNDING** | Every price must come from discover_bcca (LLM selects from candidates) |
| **REASONING CHAINS REQUIRED** | Explainable AI for trust and debugging |

### 13.5 Token Budget Summary

```
┌────────────────────────────────────────────┐
│           GEMINI 2.5 PRO BUDGET            │
├────────────────────────────────────────────┤
│ SYSTEM INSTRUCTION           ~242,000 tokens│
│   ├─ Role & Rules                ~3,000    │
│   ├─ BCCA-Speak Guide           ~5,000    │
│   ├─ Quantity Formulas          ~2,000    │
│   ├─ Knowledge Graph          ~214,000    │
│   ├─ Energy Knowledge           ~6,000    │
│   ├─ Process Knowledge          ~4,000    │
│   └─ Interior Design            ~8,000    │
├────────────────────────────────────────────┤
│ USER PROMPT                   ~30,000 tokens│
│   ├─ Target PIR + listing       ~5,000    │
│   ├─ Photos (10 images)        ~10,000    │
│   └─ Comparable PIRs (3)       ~15,000    │
├────────────────────────────────────────────┤
│ TOOL RESPONSES               ~10,000 tokens│
│   └─ ~10 discover_bcca calls   ~10,000    │
│       (returns candidate pools, not top-3) │
├────────────────────────────────────────────┤
│ OUTPUT                        ~30,000 tokens│
│   └─ UnifiedEstimate JSON      ~30,000    │
├────────────────────────────────────────────┤
│ TOTAL                        ~307,000 tokens│
│ GEMINI LIMIT                1,000,000 tokens│
│ HEADROOM                      ~693,000 ✅   │
└────────────────────────────────────────────┘
```

### 13.6 Success Criteria

Before marking V0.4 as complete:

- [ ] **Listing 12 produces valid estimate** (known problematic)
- [ ] **Bathroom costs €5,000-20,000** (not €53)
- [ ] **<30% costs in "General"** (room attribution)
- [ ] **100% tasks trace to KG** (KG grounding)
- [ ] **100% prices from BCCA** (no invented prices)
- [ ] **Reasoning chains complete** (why this task, why this price, why this qty)
- [ ] **Customer modal renders** (mobile-first)
- [ ] **Architect export works** (PDF with full BCCA detail)
- [ ] **Before/After shows kitchen only** (one room)
- [ ] **Energy gap displayed** (G → C with letters)

### 13.7 What This Document IS and IS NOT

**IS:**
- ✅ The SINGLE SOURCE OF TRUTH for V0.4 implementation
- ✅ Complete specification with code snippets
- ✅ All architectural decisions documented
- ✅ UI specification with data mappings
- ✅ Implementation checklist

**IS NOT:**
- ❌ A summary (it's exhaustive)
- ❌ Dependent on other docs (self-contained)
- ❌ Aspirational (everything here is implementable)
- ❌ V0.3.x (those are superseded)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| V0.4.0 | 2026-01-10 | Initial unified architecture |
| V0.4.1 | 2026-01-10 | Added Parts 8-11 (PIR, Energy, Decisions, Errors) |
| V0.4.2 | 2026-01-10 | Added Part 12 (UI Specification - Mobile First) |
| V0.4.3 | 2026-01-10 | Added Part 13 (Complete System Summary), TOC |
| V0.4.4 | 2026-01-11 | SQL-based `discover_bcca` replaces embedding search |
| V0.4.5 | 2026-01-11 | Added Part 2B: `discover_ffe` Tool + FFE-SPEAK Guide + Style Matching Framework |
| V0.4.6 | 2026-01-11 | **FFE Database Complete**: 202 items from Gemini 3 Pro research, style tags, tier pricing |
| V0.4.7 | 2026-01-11 | **FULL CONTEXT ARCHITECTURE**: BCCA + FFE indexes IN context (~700K tokens). Gemini sees ALL items, matches semantically. SQL only for price lookup. AI-paraphrasing 12K BCCA items to 100 chars via Gemini 2.5 Flash Lite. |
| V0.4.8 | 2026-01-11 | **9-PHASE ORCHESTRATOR**: Complete rewrite of execution model. 9 phases with cached context (60% cheaper). Pro for generation, Flash for checks. Explicit scope→BOQ→pricing→validation flow. No Pareto-ing possible - every phase verified by next phase. Full reasoning chain preserved. |

---

**END OF DOCUMENT**

*This is the implementation guide. Follow it exactly.*

