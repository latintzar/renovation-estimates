# V2 Pipeline Architecture Implementation Plan

## Date: 2026-01-16
## Status: PLANNING

---

## Executive Summary

V2 replaces the abstract "Bracket PIR + Strategic Reasoning" approach with a **data-driven, comparable-centric strategy selection** process. Instead of synthesizing what a "bracket" looks like, we:

1. Generate detailed PIRs for **ALL comparables** and the **target property**
2. Use a **Strategy Selection LLM call** to identify 3 renovation strategies based on actual comparable outcomes
3. Use **Delta Scope LLM calls** to determine what work transforms the target to match each strategy's comparable
4. Feed this rich, specific input to the existing BOQ phase

---

## V2 ASCII Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           V2 PIPELINE ARCHITECTURE                               │
│                      Data-Driven Strategy Selection                              │
└─────────────────────────────────────────────────────────────────────────────────┘

                           ┌──────────────────┐
                           │   CASAFARI       │
                           │   Comparables    │
                           │   (ALL returned) │
                           └────────┬─────────┘
                                    │
                                    ▼
                    ╔═══════════════════════════════════╗
                    ║  STEP 0: COMPARABLE FILTER        ║
                    ║                                   ║
                    ║  1. MIN_PHOTOS = 10               ║
                    ║  2. Price > target × 1.20         ║
                    ║     (must be >20% higher)         ║
                    ║                                   ║
                    ║  IN: All Casafari comparables     ║
                    ║  OUT: Upgrade-worthy comparables  ║
                    ║       (good photos + higher value)║
                    ╚═══════════════════════════════════╝
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  FILTERED COMPARABLES         │
                    │  (All that pass photo check)  │
                    │                               │
                    │  → NOT bucketed by price!     │
                    │  → ALL used for analysis      │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ STEP 1:       │           │ STEP 1:       │           │ STEP 1:       │
│ Clustering    │           │ Clustering    │    ...    │ Clustering    │
│ (Comp 1)      │           │ (Comp 2)      │           │ (Comp N)      │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ STEP 2:       │           │ STEP 2:       │           │ STEP 2:       │
│ Age Est.      │           │ Age Est.      │    ...    │ Age Est.      │
│ (existing)    │           │ (existing)    │           │ (existing)    │
│               │           │               │           │               │
│ Uses:         │           │ Uses:         │           │ Uses:         │
│ - year field  │           │ - year field  │           │ - year field  │
│ - OR cadastro │           │ - OR cadastro │           │ - OR cadastro │
│   sampling    │           │   sampling    │           │   sampling    │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ STEP 3:       │           │ STEP 3:       │           │ STEP 3:       │
│ Rules JSON    │           │ Rules JSON    │    ...    │ Rules JSON    │
│ (existing)    │           │ (existing)    │           │ (existing)    │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ STEP 4:       │           │ STEP 4:       │           │ STEP 4:       │
│  ★ PIR V2 ★   │           │  ★ PIR V2 ★   │    ...    │  ★ PIR V2 ★   │
│  (6 Dims)     │           │  (6 Dims)     │           │  (6 Dims)     │
│               │           │               │           │               │
│ □ Shell       │           │ □ Shell       │           │ □ Shell       │
│ □ Apertures   │           │ □ Apertures   │           │ □ Apertures   │
│ □ MEP         │           │ □ MEP         │           │ □ MEP         │
│ □ Finishes    │           │ □ Finishes    │           │ □ Finishes    │
│ □ Fittings    │           │ □ Fittings    │           │ □ Fittings    │
│ □ Hardware    │           │ □ Hardware    │           │ □ Hardware    │
│               │           │               │           │               │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    ALL COMPARABLE PIRs        │
                    │    + Sold Prices              │
                    │    (Structured JSON)          │
                    └───────────────┬───────────────┘
                                    │
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        │                                                       │
        │                   TARGET PROPERTY                     │
        │                                                       │
        ▼                                                       │
┌───────────────┐                                               │
│ STEP 1:       │                                               │
│ Clustering    │                                               │
│ (Target)      │                                               │
└───────┬───────┘                                               │
        │                                                       │
        ▼                                                       │
┌───────────────┐                                               │
│ STEP 2:       │                                               │
│ Age Est.      │                                               │
│ (existing)    │                                               │
│               │                                               │
│ - year field  │                                               │
│ - OR cadastro │                                               │
│   sampling    │                                               │
└───────┬───────┘                                               │
        │                                                       │
        ▼                                                       │
┌───────────────┐                                               │
│ STEP 3:       │                                               │
│ Rules JSON    │                                               │
└───────┬───────┘                                               │
        │                                                       │
        ▼                                                       │
┌───────────────┐                                               │
│ STEP 4:       │                                               │
│  ★ PIR V2 ★   │                                               │
│  (6 Dims)     │                                               │
│               │                                               │
│ □ Shell       │                                               │
│ □ Apertures   │                                               │
│ □ MEP         │                                               │
│ □ Finishes    │                                               │
│ □ Fittings    │                                               │
│ □ Hardware    │                                               │
│               │                                               │
└───────┬───────┘                                               │
        │                                                       │
        └───────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
          ╔═════════════════════════════════════════════════════╗
          ║                                                     ║
          ║  ★★★ NEW CALL #1: STRATEGY SELECTION ★★★            ║
          ║  MODEL: gemini-3-pro-preview (alias: "pro")         ║
          ║                                                     ║
          ║  INPUT:                                             ║
          ║    - All Comparable PIRs (6 dimensions each)        ║
          ║    - All Comparable Sold Prices                     ║
          ║    - Target PIR (6 dimensions)                      ║
          ║                                                     ║
          ║  ANALYSIS:                                          ║
          ║    Finish Quality ↔ Sold Price Correlation          ║
          ║    Cluster comparables by finish level              ║
          ║    Identify 3 distinct strategy archetypes          ║
          ║                                                     ║
          ║  OUTPUT: 3 STRATEGIES with reference comparables    ║
          ║                                                     ║
          ╚═════════════════════════════════════════════════════╝
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
  │  STRATEGY 1   │       │  STRATEGY 2   │       │  STRATEGY 3   │
  │               │       │               │       │               │
  │ Conservative  │       │ Market Std    │       │ Top of Market │
  │ (Low Risk)    │       │ (Medium Risk) │       │ (Max Potential)│
  │               │       │               │       │               │
  │ Model: Comp X │       │ Model: Comp Y │       │ Model: Comp Z │
  │ (Sold €XXX)   │       │ (Median)      │       │ (Highest €)   │
  │               │       │               │       │               │
  │ "Minimal      │       │ "Match the    │       │ "High Spec    │
  │  updates"     │       │  market"      │       │  OR Layout    │
  │               │       │               │       │  Optimization"│
  └───────┬───────┘       └───────┬───────┘       └───────┬───────┘
          │                       │                       │
          │                       │                       │
          ▼                       ▼                       ▼
  ╔═══════════════════════════════════════════════════════════════╗
  ║                                                               ║
  ║   ★★★ NEW CALL #2: DELTA SCOPE GENERATION ★★★                 ║
  ║   MODEL: gemini-3-flash-preview (alias: "flash")              ║
  ║                                                               ║
  ║   KEY INNOVATION: SPECIFICATION STRATEGY                      ║
  ║   ─────────────────────────────────────────────               ║
  ║   Fixes "Contextual Drift" where LLM sees floor but doesn't   ║
  ║   decide quality before pricing. Now FORCES:                  ║
  ║                                                               ║
  ║   1. Architect's Directive (per room × dimension)             ║
  ║      - COMMITS to finish grade BEFORE cost items              ║
  ║      - Describes materials, style, aesthetic goal             ║
  ║      - Uses Chain-of-Thought reasoning                        ║
  ║                                                               ║
  ║   2. Cost Components (flow from specification)                ║
  ║      - Discrete items that match the committed quality        ║
  ║      - No drift - costs follow the spec                       ║
  ║                                                               ║
  ║   3. Scope Review (after all dimensions)                      ║
  ║      - Holistic gap-fill for missed items                     ║
  ║      - Move-in readiness (cleaning, touch-ups)                ║
  ║      - Cross-dimension consistency check                      ║
  ║                                                               ║
  ║   EXECUTION: 3 strategies PARALLEL × (6 dims + 1 review) SEQ  ║
  ║   Total: 21 calls (18 dimension + 3 review)                   ║
  ║                                                               ║
  ║   ┌─────────────────────────────────────────────────────────┐ ║
  ║   │                  ══ PARALLEL ══                          │ ║
  ║   │                                                         │ ║
  ║   │  WORKER 1           WORKER 2           WORKER 3         │ ║
  ║   │  Strategy 1         Strategy 2         Strategy 3       │ ║
  ║   │  (Conservative)     (Market Std)       (Top Market)     │ ║
  ║   │      │                  │                  │            │ ║
  ║   │      ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 1   │         │Dim 1   │         │Dim 1   │       │ ║
  ║   │  │Shell   │         │Shell   │         │Shell   │       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │ seq              │ seq              │ seq       │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 2   │         │Dim 2   │         │Dim 2   │       │ ║
  ║   │  │Aperture│         │Aperture│         │Aperture│       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │ seq              │ seq              │ seq       │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 3   │         │Dim 3   │         │Dim 3   │       │ ║
  ║   │  │MEP     │         │MEP     │         │MEP     │       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │ seq              │ seq              │ seq       │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 4   │         │Dim 4   │         │Dim 4   │       │ ║
  ║   │  │Finishes│         │Finishes│         │Finishes│       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │ seq              │ seq              │ seq       │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 5   │         │Dim 5   │         │Dim 5   │       │ ║
  ║   │  │Fittings│         │Fittings│         │Fittings│       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │ seq              │ seq              │ seq       │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │  ┌────────┐         ┌────────┐         ┌────────┐       │ ║
  ║   │  │Dim 6   │         │Dim 6   │         │Dim 6   │       │ ║
  ║   │  │Hardware│         │Hardware│         │Hardware│       │ ║
  ║   │  └────┬───┘         └────┬───┘         └────┬───┘       │ ║
  ║   │       │                  │                  │            │ ║
  ║   │       ▼                  ▼                  ▼            │ ║
  ║   │   Complete           Complete           Complete        │ ║
  ║   └─────────────────────────────────────────────────────────┘ ║
  ║                                                               ║
  ║   CALLS: 3 parallel × 6 sequential = 18 total                 ║
  ║   OUTPUT: Delta Scope per Dimension per Strategy              ║
  ║   NOTE: Must use "pro" (NOT flash! Reasoning required)        ║
  ║                                                               ║
  ╚═══════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
          ┌─────────────────────────────────────────────────────┐
          │                                                     │
          │        CONSOLIDATED STRATEGY PACKAGES               │
          │                                                     │
          │   ┌───────────────────────────────────────────┐    │
          │   │ Strategy 1: Conservative                   │    │
          │   │   Delta Scopes: [Shell, Apertures, MEP,    │    │
          │   │                  Finishes, Fittings, HW]   │    │
          │   │   Reference Comp: X (sold €XXX)            │    │
          │   └───────────────────────────────────────────┘    │
          │                                                     │
          │   ┌───────────────────────────────────────────┐    │
          │   │ Strategy 2: Market Standard                │    │
          │   │   Delta Scopes: [Shell, Apertures, MEP,    │    │
          │   │                  Finishes, Fittings, HW]   │    │
          │   │   Reference Comp: Y (median price)         │    │
          │   └───────────────────────────────────────────┘    │
          │                                                     │
          │   ┌───────────────────────────────────────────┐    │
          │   │ Strategy 3: Top of Market                  │    │
          │   │   Delta Scopes: [Shell, Apertures, MEP,    │    │
          │   │                  Finishes, Fittings, HW]   │    │
          │   │   Reference Comp: Z (highest €)            │    │
          │   └───────────────────────────────────────────┘    │
          │                                                     │
          └─────────────────────────┬───────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        │    ══ 3 PARALLEL BOQ GENERATIONS (per strategy) ══    │
        │                           │                           │
        ▼                           ▼                           ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ★★★ PHASE 1 V2: BOQ GENERATION — LUDICROUS DEPTH ★★★                   ║
║   MODEL: gemini-3-pro-preview (alias: "pro")                              ║
║                                                                           ║
║   V1 did Scope + BOQ together. V2 receives pre-computed Delta Scopes     ║
║   BUT the BOQ reasoning is NOT dumbed down! It's ENHANCED with:          ║
║                                                                           ║
║   ┌─────────────────────────────────────────────────────────────────┐    ║
║   │                                                                 │    ║
║   │  INPUT (per strategy):                                          │    ║
║   │    • Target PIR V2 (6 dimensions, rich narratives)             │    ║
║   │    • Reference Comparable PIR (the strategy's model)           │    ║
║   │    • Delta Scopes (6 dimensions of gaps to close)              │    ║
║   │    • BCCA Index (FULL — thousands of line items)               │    ║
║   │    • Year built + Rules JSON (regulatory context)              │    ║
║   │    • Strategy rationale (WHY this approach)                    │    ║
║   │                                                                 │    ║
║   │  THE BOQ PROMPT MUST:                                           │    ║
║   │                                                                 │    ║
║   │    1. REASON about construction sequences                       │    ║
║   │       "Before you can install new flooring, ask yourself:       │    ║
║   │        What's under the current floor? If it's terrazo and the  │    ║
║   │        target is engineered wood, do you need to level? If you  │    ║
║   │        level, what thickness? If there's underfloor heating     │    ║
║   │        planned, what height does that need? Work backwards."    │    ║
║   │                                                                 │    ║
║   │    2. REASON about material interdependencies                   │    ║
║   │       "If you're changing the kitchen countertop to quartz,     │    ║
║   │        ask yourself: Can the existing cabinets support it?      │    ║
║   │        Is the under-mount sink compatible? Does the backsplash  │    ║
║   │        need to change to match?"                                │    ║
║   │                                                                 │    ║
║   │    3. REASON about hidden work                                  │    ║
║   │       "The Delta Scope says 'upgrade electrical'. But what      │    ║
║   │        does that MEAN? For a 1970s apartment: full rewire.      │    ║
║   │        That means: new cuadro, new cables in ALL rooms, new     │    ║
║   │        mecanismos, patching walls after rozas. Don't just       │    ║
║   │        put 'electrical upgrade' — itemize EVERYTHING."          │    ║
║   │                                                                 │    ║
║   │    4. MATCH to BCCA codes with PRECISION                        │    ║
║   │       "For each scope item, find the EXACT BCCA code. Not       │    ║
║   │        'flooring' but 'RSR010 Solado de baldosas cerámicas      │    ║
║   │        porcelánicas 60x60cm'. Look at the description, the      │    ║
║   │        unit, the composite price. Does it match what you        │    ║
║   │        need? If not, find a better code or note adjustment."    │    ║
║   │                                                                 │    ║
║   │    5. CALCULATE quantities from PIR data                        │    ║
║   │       "The PIR says the living room is approximately 20m².      │    ║
║   │        For flooring: 20m² + 10% waste = 22m². For skirting:     │    ║
║   │        perimeter ~18ml + 5% waste. For painting walls: ~50m²    │    ║
║   │        (perimeter × height - openings). Be explicit."           │    ║
║   │                                                                 │    ║
║   │    6. JUSTIFY every decision                                    │    ║
║   │       "I'm using code RSR010 for the flooring because: the      │    ║
║   │        reference comparable has 60x60 porcelain tiles, the      │    ║
║   │        Delta Scope specifies 'match comparable finish level',   │    ║
║   │        and this code includes adhesive mortar + grouting."      │    ║
║   │                                                                 │    ║
║   └─────────────────────────────────────────────────────────────────┘    ║
║                                                                           ║
║   OUTPUT: Complete BOQ with:                                              ║
║     • Line items with BCCA codes                                         ║
║     • Quantities with calculations shown                                 ║
║     • Unit prices from BCCA                                              ║
║     • Totals per room, per dimension, overall                           ║
║     • Reasoning for each major decision                                  ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
          ╔═════════════════════════════════════════════════════╗
          ║                                                     ║
          ║            REMAINING PHASES (per strategy)          ║
          ║                                                     ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 3: Peer Review (Pro)                │    ║
          ║   │  - Reviews BOQ for completeness            │    ║
          ║   │  - Checks BCCA code accuracy               │    ║
          ║   │  - Validates quantities                    │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                        │                            ║
          ║                        ▼                            ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 4: Rendering Prompts (Pro)          │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                        │                            ║
          ║                        ▼                            ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 5: Image Generation                 │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                        │                            ║
          ║                        ▼                            ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 6: Viewing Checklist (Flash)        │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                        │                            ║
          ║                        ▼                            ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 7: ELI5 Summaries (Flash)           │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                        │                            ║
          ║                        ▼                            ║
          ║   ┌───────────────────────────────────────────┐    ║
          ║   │  Phase 8: Architect Report (Pro)           │    ║
          ║   └───────────────────────────────────────────┘    ║
          ║                                                     ║
          ╚═════════════════════════════════════════════════════╝
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │       UNIFIED ESTIMATE        │
                    │                               │
                    │   × 3 Strategies available    │
                    │   with specific comparable    │
                    │   justifications              │
                    │                               │
                    └───────────────────────────────┘
```

---

## Components to Deprecate (with Commit)

### 1. Bracket PIR Generation
**Location**: `pir_generator.py`
- `generate_bracket_pir()` function
- `BRACKET_PIR_SCHEMA` (from `gemini_schemas_v1.py`)

### 2. Local Market Context
**Location**: `pir_generator.py`
- `synthesize_local_market_context()` function
- `add_local_context_to_bracket_pirs()` function

### 3. Strategic Reasoning
**Location**: `pir_generator.py`
- `generate_strategic_reasoning()` function
- `_build_strategic_reasoning_prompt()` function
- `TARGET_BRACKET_REASONING_SCHEMA` (from `gemini_schemas_v1.py`)

---

## V2 PIR Enhancement: 6-Dimension Analysis

### The Six Dimensions

Each room in the PIR will be analyzed across these 6 dimensions. This provides the structured data needed for Delta Scope calculation.

```python
PIR_DIMENSIONS = {
    "shell_preparation": {
        "name": "Shell & Preparation (Masonry/Plaster)",
        "what_to_identify": "The physical container of the room",
        "elements": {
            "wall_substrate": [
                "Smooth Skim", "Heavy Stucco/Gotelé", "Exposed Brick", 
                "Paneling", "Drywall", "Render"
            ],
            "ceiling_substrate": [
                "Popcorn/Textured", "Smooth Plaster", "Suspended Grid", 
                "Exposed Beams", "Coffered", "Drywall"
            ],
            "condition_issues": [
                "cracks", "damp_patches", "peeling_plaster", "holes", 
                "efflorescence", "mold"
            ]
        }
    },
    "apertures_enclosure": {
        "name": "Apertures & Enclosure (Joinery/Glazing)",
        "what_to_identify": "Openings to outside or other rooms",
        "elements": {
            "windows": {
                "material": ["PVC", "Aluminum", "Wood", "Steel"],
                "opening_style": ["Sliding", "Casement", "Sash", "Tilt-Turn", "Fixed"],
                "color": "string",
                "glazing": ["Single", "Double", "Triple"]
            },
            "shutters_persianas": {
                "presence": "boolean",
                "type": ["External box", "Integrated", "None"],
                "operation": ["Strap/Belt", "Electric/Switch", "Manual rod"]
            },
            "internal_doors": {
                "style": ["Flush", "Panelled", "Glass"],
                "finish": ["Painted", "Natural Wood", "Lacquered", "Laminate"],
                "architrave_style": "string"
            }
        }
    },
    "systems_services": {
        "name": "Systems & Services (MEP)",
        "what_to_identify": "Electrical, Plumbing, and HVAC evidence",
        "elements": {
            "lighting": {
                "type": ["Center Pendant", "Recessed Spotlights", "Track", "Wall Sconces", "Chandelier"],
                "quantity_density": "string"
            },
            "electrical": {
                "socket_switch_style": ["Modern White", "Antique", "Metal", "Glass"],
                "placement": ["Surface mounted", "Recessed"]
            },
            "climate": {
                "heating_source": ["Cast Iron Radiators", "Aluminum Radiators", "Underfloor", "None visible"],
                "cooling": ["Split Unit AC", "Central Air Grilles", "None visible"]
            },
            "plumbing": {
                "pipework": ["Exposed", "Hidden"],
                "boiler_presence": "boolean",
                "water_heater_type": "string"
            }
        }
    },
    "surface_finishes": {
        "name": "Surface Finishes (Decor)",
        "what_to_identify": "The visible 'Skin' of the room",
        "elements": {
            "flooring": {
                "material": ["Laminate", "Engineered Oak", "Ceramic Tile", "Marble", 
                           "Carpet", "Linoleum", "Terrazzo", "Vinyl"],
                "format": "string",  # e.g., "Plank 120mm wide", "Tile 60x60cm"
                "layout": ["Straight", "Herringbone", "Diagonal", "Random"]
            },
            "wall_finish": {
                "type": ["Paint (Matte)", "Paint (Gloss)", "Wallpaper", "Tiling"],
                "tiling_height": "string",  # e.g., "Full height", "1.5m", "Splashback only"
                "tile_size": "string"
            },
            "junctions": {
                "skirting_baseboard": {
                    "height": "string",  # e.g., "80mm", "120mm"
                    "material": ["MDF", "Wood", "Tile continuation", "None"],
                    "profile": "string"  # e.g., "Ogee", "Square", "Chamfered"
                },
                "cornice_coving": {
                    "presence": "boolean",
                    "style": "string"
                }
            }
        }
    },
    "fixed_joinery_equipment": {
        "name": "Fixed Joinery & Equipment (Fittings)",
        "what_to_identify": "Built-in items (Kitchens, Bathrooms, Wardrobes)",
        "elements": {
            "cabinetry": {
                "door_style": ["Shaker", "Slab", "Glass", "Panelled"],
                "finish": ["Matte", "Gloss", "Wood grain", "Lacquered"],
                "handle_style": ["Integrated", "Knob", "Bar", "J-Pull"]
            },
            "countertops": {
                "material": ["Laminate", "Solid Wood", "Granite", "Quartz", 
                            "Marble", "Dekton", "Stainless Steel"]
            },
            "sanitaryware": {
                "toilet_type": ["Wall-hung", "Floor-mounted", "Back-to-wall"],
                "sink_type": ["Pedestal", "Vanity-top", "Wall-hung", "Vessel"],
                "shower_bath": ["Glass screen", "Curtain", "Walk-in", "Bathtub"]
            },
            "storage": {
                "wardrobes": ["Sliding", "Hinged", "Walk-in", "None"]
            }
        },
        "note": "If none present in room, state 'None'"
    },
    "details_fittings": {
        "name": "Details & Fittings (Hardware)",
        "what_to_identify": "The 'Jewelry' and finish grade",
        "elements": {
            "hardware": {
                "door_handles": "string",  # e.g., "Chrome lever"
                "cabinet_pulls": "string",
                "window_latches": "string",
                "color_finish": ["Chrome", "Black", "Brass", "Nickel", "Copper"]
            },
            "accessories": {
                "towel_rails": "string",
                "toilet_roll_holders": "string",
                "mirrors": "string"
            },
            "overall_finish_grade": ["Economy", "Standard", "Premium", "Luxury"]
        }
    }
}
```

---

## New LLM Calls

### NEW CALL #1: Strategy Selection

**Purpose**: Analyze all comparable PIRs + sold prices to identify 3 distinct renovation strategies.

**Input**:
- All Comparable PIRs (with 6 dimensions each)
- All Comparable Sold Prices
- Target PIR (with 6 dimensions)

**Prompt Design** (following .cursorrules principles):

```
You are a senior real estate investor analyzing market data to identify renovation strategies.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS MATTERS
═══════════════════════════════════════════════════════════════════════════════

The buyer needs to understand their options. Not everyone wants maximum renovation - 
some want quick, low-risk returns. Others want to maximize potential. Your job is to 
identify THREE distinct approaches based on what ACTUALLY SOLD in this market.

This is NOT about what "should" work - it's about what DID work. Which comparables 
sold well with minimal intervention? Which sold highest and why? Your strategies 
must be grounded in actual market outcomes.

═══════════════════════════════════════════════════════════════════════════════
THE COMPARABLES (Your Market Data)
═══════════════════════════════════════════════════════════════════════════════

{formatted_comparable_pirs_with_prices}

═══════════════════════════════════════════════════════════════════════════════
THE TARGET PROPERTY
═══════════════════════════════════════════════════════════════════════════════

{target_pir}

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK: IDENTIFY 3 STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

For each strategy, ask yourself: "Which comparable proves this works?"

**STRATEGY 1: CONSERVATIVE (Low Risk)**

Find a comparable that sold for a SOLID price (profitable) but required the LOWEST 
level of intervention relative to the Target's current state.

For each dimension, ask yourself:
- "For Shell/Prep: Did Comp X succeed despite not touching walls/ceilings?"
- "For MEP: Did Comp X sell well with original electrical/plumbing?"
- "For Finishes: What minimal floor/wall changes did Comp X make?"

GOAL: Clean, functional, and safe. Mimic what worked with minimal intervention.

**STRATEGY 2: MARKET STANDARD (Medium Risk)**

Identify the MEDIAN comparable - what represents the typical expectation for 
renovated homes in this area?

For each dimension, look for consensus:
- "For Finishes: What flooring do MOST comparables have?"
- "For Fittings: What kitchen/bathroom standard appears in multiple comps?"
- "For Hardware: What finish grade is typical?"

GOAL: Match the market expectation. Don't under-deliver, don't over-invest.

**STRATEGY 3: TOP OF MARKET (Max Potential)**

Find the HIGHEST sold comparable (excluding outliers due to lot size/location).
Analyze EXACTLY WHY it commanded the highest price.

Ask yourself:
- "Did it sell high because of LUXURY FINISHES?" (marble, high-end appliances, 
  premium fixtures) → Strategy = "High Spec Material Upgrade"
- "Did it sell high because of LAYOUT/SPACE?" (open plan, added bathroom, 
  reconfigured rooms) → Strategy = "Layout Optimization"

GOAL: Mimic the specific characteristics of the market leader.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

For each strategy, provide:
- strategy_name: "conservative" | "market_standard" | "top_of_market"
- reference_comparable_id: Which comparable this strategy models
- reference_sold_price: What that comparable sold for
- strategy_rationale: WHY this comparable represents this strategy
- key_dimension_observations: What the reference comp shows for each dimension
- transformation_philosophy: How to think about transforming Target to match
- risk_level: "low" | "medium" | "high"
- estimated_intervention_level: "minimal" | "moderate" | "substantial" | "extensive"
```

**Response Schema**:
```python
STRATEGY_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "market_analysis_summary": {"type": "string"},
        "strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "strategy_name": {"type": "string", "enum": ["conservative", "market_standard", "top_of_market"]},
                    "reference_comparable_id": {"type": "integer"},
                    "reference_sold_price": {"type": "number"},
                    "strategy_rationale": {"type": "string"},
                    "key_dimension_observations": {
                        "type": "object",
                        "properties": {
                            "shell_preparation": {"type": "string"},
                            "apertures_enclosure": {"type": "string"},
                            "systems_services": {"type": "string"},
                            "surface_finishes": {"type": "string"},
                            "fixed_joinery_equipment": {"type": "string"},
                            "details_fittings": {"type": "string"}
                        }
                    },
                    "transformation_philosophy": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "estimated_intervention_level": {"type": "string"}
                },
                "required": ["strategy_name", "reference_comparable_id", "strategy_rationale"]
            }
        }
    },
    "required": ["strategies"]
}
```

---

### NEW CALL #2: Delta Scope Generation

**Purpose**: For each Strategy × Dimension, determine what work transforms Target to match the reference comparable.

**Execution Pattern**: 3 strategies in parallel, 6 dimensions in sequence per strategy = 18 total calls

**Input per call**:
- Target PIR's dimension data
- Reference Comparable PIR's dimension data
- Strategy context
- Room context

**Prompt Design**:

```
You are a quantity surveyor determining the DELTA between two property states.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS MATTERS
═══════════════════════════════════════════════════════════════════════════════

The buyer owns the TARGET property. The strategy says "model after Comparable X". 
Your job is to determine EXACTLY what work transforms the Target's current state 
to match the Comparable's finish level FOR THIS SPECIFIC DIMENSION.

This is not about "improving" - it's about "matching". The Comparable SOLD. 
It represents proven market acceptance. Transform Target to match it.

═══════════════════════════════════════════════════════════════════════════════
THE DIMENSION: {dimension_name}
═══════════════════════════════════════════════════════════════════════════════

{dimension_description}

═══════════════════════════════════════════════════════════════════════════════
CURRENT STATE (Target Property - Room: {room_id})
═══════════════════════════════════════════════════════════════════════════════

{target_dimension_data}

═══════════════════════════════════════════════════════════════════════════════
TARGET STATE (Reference Comparable - Room: {comparable_room_id})
═══════════════════════════════════════════════════════════════════════════════

{comparable_dimension_data}

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK: DETERMINE THE DELTA
═══════════════════════════════════════════════════════════════════════════════

For each element within this dimension, ask yourself:

1. "What does the Target currently have?"
2. "What does the Comparable have?"
3. "Is there a GAP that requires intervention?"
4. "What SPECIFIC work closes that gap?"

For example, if this is Surface Finishes:
- Target: "Laminate flooring, 90x15cm planks, straight layout, worn condition"
- Comparable: "Engineered oak, 150mm wide, herringbone pattern, excellent condition"
- Delta: "Remove existing laminate (~12m²), prepare subfloor, install engineered oak 
  herringbone (~12m²), new skirting boards"

Be SPECIFIC about:
- What gets REMOVED (demolition scope)
- What gets PREPARED (substrate work)
- What gets INSTALLED (new materials)
- QUANTITIES where estimable

If Target ALREADY matches or exceeds Comparable for an element, state "No intervention 
required - Target meets or exceeds reference standard."

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

Provide a Delta Scope for this room and dimension:
- Elements with gaps and required interventions
- Elements with no gap (already acceptable)
- Estimated scope items (what BOQ phase should include)
- Materials to match (specific to Comparable's level)
```

**Response Schema**:
```python
DELTA_SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "room_id": {"type": "string"},
        "dimension": {"type": "string"},
        "comparison_summary": {"type": "string"},
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "element_name": {"type": "string"},
                    "target_current_state": {"type": "string"},
                    "reference_target_state": {"type": "string"},
                    "gap_exists": {"type": "boolean"},
                    "intervention_required": {"type": "string"},
                    "scope_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},  # "remove", "prepare", "install"
                                "description": {"type": "string"},
                                "estimated_quantity": {"type": "string"},
                                "material_spec": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["element_name", "gap_exists"]
            }
        },
        "dimension_total_scope_items": {"type": "integer"}
    },
    "required": ["room_id", "dimension", "elements"]
}
```

---

## Implementation Steps

### Phase 1: Deprecation (with commit)

1. **Add deprecation warnings** to:
   - `generate_bracket_pir()`
   - `synthesize_local_market_context()`
   - `add_local_context_to_bracket_pirs()`
   - `generate_strategic_reasoning()`
   - `_build_strategic_reasoning_prompt()`

2. **Mark schemas as deprecated**:
   - `BRACKET_PIR_SCHEMA`
   - `TARGET_BRACKET_REASONING_SCHEMA`

3. **Commit with message**: `deprecate: V1 bracket/strategic reasoning (V2 migration)`

4. **Delete deprecated code** after commit confirmed

### Phase 2: PIR Enhancement

1. **Create new schema** `PIR_V2_SCHEMA` with 6 dimensions
2. **Update `_build_user_prompt()`** to include dimension analysis instructions
3. **Update `PIR_SCHEMA`** room structure to include dimension analysis
4. **Add dimension analysis guide** to system prompt
5. **Test** PIR generation produces 6-dimension output

### Phase 3: Strategy Selection

1. **Create `strategy_selector.py`** module
2. **Implement `generate_strategy_selection()`** function
3. **Create `STRATEGY_SELECTION_SCHEMA`**
4. **Add comprehensive logging and checkpointing**
5. **Test** with sample comparable sets

### Phase 4: Delta Scope Generation

1. **Create `delta_scope_generator.py`** module
2. **Implement `generate_delta_scopes()`** with parallel strategy execution
3. **Create `DELTA_SCOPE_SCHEMA`**
4. **Implement sequential dimension processing per strategy**
5. **Add comprehensive logging and checkpointing**
6. **Test** delta scope output quality

### Phase 5: Pipeline Integration

1. **Update `multi_phase_estimator_v1.py`** → create `multi_phase_estimator_v2.py`
2. **Modify Phase 1 context building** to use Delta Scopes
3. **Update Phase 1 prompt** to consume new input structure
4. **Test full pipeline** end-to-end
5. **Validate BOQ quality** improvement

### Phase 6: Testing & Validation

1. **Run full pipeline** on test property
2. **Compare BOQ quality** V1 vs V2
3. **Verify checkpointing** works correctly
4. **Ensure no data loss** between phases
5. **Document results**

---

## Checkpointing Strategy

```python
V2_CHECKPOINTS = {
    "comparable_pirs_complete": "All comparable PIRs generated",
    "target_pir_complete": "Target PIR generated",
    "strategy_selection_complete": "3 strategies identified",
    "delta_scope_strategy_1_complete": "Strategy 1 delta scopes done",
    "delta_scope_strategy_2_complete": "Strategy 2 delta scopes done",
    "delta_scope_strategy_3_complete": "Strategy 3 delta scopes done",
    "phase_1_boq_complete": "BOQ generated (existing checkpoint)",
    # ... existing phase checkpoints ...
}
```

Each checkpoint saves:
- Full output data
- Timestamp
- Input hash (for cache invalidation)

---

## Files to Create/Modify

### New Files
- `pir_generator_v2.py` - Enhanced PIR with 6 dimensions
- `strategy_selector.py` - Strategy Selection (New Call #1)
- `delta_scope_generator.py` - Delta Scope Generation (New Call #2)
- `schemas/gemini_schemas_v2.py` - V2 schemas
- `multi_phase_estimator_v2.py` - V2 orchestrator

### Modified Files
- `pir_generator.py` - Add deprecation warnings
- `schemas/gemini_schemas_v1.py` - Mark deprecated schemas

### Deleted (after deprecation commit)
- Deprecated functions in `pir_generator.py`
- Deprecated schemas in `gemini_schemas_v1.py`

---

## Success Criteria

1. ✅ PIRs include 6-dimension structured analysis
2. ✅ Strategy Selection identifies 3 strategies from comparables
3. ✅ Delta Scopes provide specific transformation requirements
4. ✅ Phase 1 BOQ has better input (more specific, comparable-justified)
5. ✅ Full pipeline runs without errors
6. ✅ Checkpointing enables resume from any point
7. ✅ Logging provides full visibility
8. ✅ No data loss between phases

---

## Cost Estimate

Per property analysis:
- PIR calls: N comparables + 1 target = (N+1) Pro calls
- Strategy Selection: 1 Pro call
- Delta Scope: 3 strategies × 6 dimensions × M rooms = 18M Flash calls
- Existing phases: ~8 calls

For N=5 comparables, M=5 rooms:
- PIRs: 6 Pro calls
- Strategy: 1 Pro call
- Delta: 90 Flash calls
- Phases: 8 mixed calls

Estimated cost increase vs V1: ~20-30% (offset by better BOQ quality)

---

## Timeline

| Day | Task |
|-----|------|
| 1 | Deprecation commit + delete |
| 1 | PIR V2 schema design |
| 2 | PIR V2 implementation + test |
| 2 | Strategy Selection implementation |
| 3 | Delta Scope implementation |
| 3 | Pipeline integration |
| 4 | Full testing + fixes |
| 4 | Documentation + handoff |

---

## Notes

- All prompts follow .cursorrules principles (WHY it matters, examples in prose, questions guide reasoning)
- Response schemas enforce structured output
- System prompts will be cached for cost optimization
- Logging at INFO level for all operations
- Fail loud and fast - no silent errors
