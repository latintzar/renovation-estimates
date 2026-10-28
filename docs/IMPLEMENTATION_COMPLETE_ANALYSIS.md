Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Complete Bracket Analysis Implementation

**Purpose**: When a buyer clicks "Analyse" on a price bracket, show them exactly what renovation would achieve that price point.

**Date**: 2026-01-08  
**Status**: Implementation Ready

---

## What The Buyer Sees

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FAIR MARKET PATH                                │
│                     Target: €485,000                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ THE MATH ──────────────────────────────────────────────────┐   │
│  │  Asking Price:        €375,000                              │   │
│  │  + Renovation Cost:    €62,400                              │   │
│  │  ─────────────────────────────                              │   │
│  │  = Total Investment:  €437,400                              │   │
│  │                                                              │   │
│  │  Target Value:        €485,000                              │   │
│  │  ─────────────────────────────                              │   │
│  │  = Potential Margin:   €47,600 ✅                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ BEFORE / AFTER ────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │                                                     │    │   │
│  │  │    [═══════════════|═══════════════]                │    │   │
│  │  │    ← BEFORE        |      AFTER →                   │    │   │
│  │  │       (drag slider to compare)                      │    │   │
│  │  │                                                     │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ SCOPE OF WORK ─────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ELECTRICAL                                    €8,200       │   │
│  │  • Replace consumer unit (cuadro eléctrico)                 │   │
│  │  • Upgrade outlets to REBT standard                         │   │
│  │  • LED lighting throughout                                  │   │
│  │                                                              │   │
│  │  PLUMBING                                      €6,800       │   │
│  │  • Replace galvanized pipes with PEX                        │   │
│  │  • New water heater (A-rated)                               │   │
│  │  • Update bathroom fixtures                                 │   │
│  │                                                              │   │
│  │  FINISHES                                     €18,400       │   │
│  │  • Wood-look flooring throughout                            │   │
│  │  • Repaint all walls (neutral palette)                      │   │
│  │  • Kitchen cabinet fronts                                   │   │
│  │  • Bathroom tiles                                           │   │
│  │                                                              │   │
│  │  ENVELOPE                                     €12,000       │   │
│  │  • Double-glazed windows (PVC)                              │   │
│  │  • Weatherstripping on doors                                │   │
│  │                                                              │   │
│  │  PERMITS & FEES                                €4,200       │   │
│  │  • Obra menor license                                       │   │
│  │  • Boletín eléctrico                                        │   │
│  │                                                              │   │
│  │  DEMOLITION & CLEANUP                          €3,800       │   │
│  │  • Strip existing finishes                                  │   │
│  │  • Waste removal                                            │   │
│  │                                                              │   │
│  │  ────────────────────────────────────────────────────       │   │
│  │  SUBTOTAL (PEM):                              €53,400       │   │
│  │  + 13% GG + 6% BI:                            €10,146       │   │
│  │  + 21% IVA:                                   €13,345       │   │
│  │  ────────────────────────────────────────────────────       │   │
│  │  TOTAL:                                       €76,891       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ TIMELINE ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Week 1-2:  Demolition & Prep                               │   │
│  │  Week 2-4:  Electrical & Plumbing                           │   │
│  │  Week 4-6:  Finishes (floors, paint, tiles)                 │   │
│  │  Week 6-7:  Windows & Final touches                         │   │
│  │  Week 7-8:  Cleanup & Inspections                           │   │
│  │                                                              │   │
│  │  ESTIMATED DURATION: 6-8 weeks                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ COMPARABLE PROPERTIES ─────────────────────────────────────┐   │
│  │                                                              │   │
│  │  [Card 1]  [Card 2]  [Card 3]  →  (swipe for more)         │   │
│  │                                                              │   │
│  │  These similar properties in "very good" condition          │   │
│  │  sold for €470k-€510k, averaging €485k.                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ VIEWING CHECKLIST ─────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  When you visit, check these items to confirm our analysis: │   │
│  │                                                              │   │
│  │  □ Electrical panel - does it have modern breakers?         │   │
│  │  □ Water pressure - run multiple taps simultaneously        │   │
│  │  □ Windows - check for drafts, condensation                 │   │
│  │  □ Walls - tap for hollow sounds (damp issues)              │   │
│  │  □ Floor levelness - place a ball, see if it rolls          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ STANDARDS COMPLIANCE ──────────────────────────────────────┐   │
│  │                                                              │   │
│  │  This renovation is designed to meet:                       │   │
│  │  • Cédula de Habitabilidad requirements                     │   │
│  │  • REBT 2002 electrical safety                              │   │
│  │  • CTE-DB-HE energy efficiency guidelines                   │   │
│  │                                                              │   │
│  │  Note: Final certification requires architect sign-off.     │   │
│  │  Export detailed specs for your architect's review.         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                    ┌──────────────────────┐                        │
│                    │  🔗 Share / Export   │                        │
│                    └──────────────────────┘                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [Phase 1: Photo Analysis](#phase-1-photo-analysis)
3. [Phase 2: Gap Analysis](#phase-2-gap-analysis)
4. [Phase 3: Scope Builder](#phase-3-scope-builder)
5. [Phase 4: KG Pricing](#phase-4-kg-pricing)
6. [Phase 5: Timeline Estimation](#phase-5-timeline-estimation)
7. [Phase 6: Image Generation](#phase-6-image-generation)
8. [Phase 7: Frontend Modal](#phase-7-frontend-modal)
9. [Phase 8: PDF Export](#phase-8-pdf-export)
10. [File Reference](#file-reference)
11. [Implementation Checklist](#implementation-checklist)

---

## 1. Data Flow Overview

When the user clicks "Analyse" for a bracket, this is the complete pipeline:

```
TRIGGER: User clicks "Analyse All" on ComparablesCard
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: PHOTO ANALYSIS                                             │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:  Listing photos from Supabase storage                       │
│                                                                     │
│  Process:                                                           │
│    1. verify_rules.py → Check each photo against 8 Spanish codes    │
│    2. assess_uniclass.py → Identify systems/elements in photos      │
│                                                                     │
│  Output:                                                            │
│    • room_rule_verifications: [{rule_id, status, evidence}]         │
│    • room_uniclass_assessments: [{code, element, condition}]        │
│                                                                     │
│  Stored in: idealista_info_extraction.room_rule_verifications       │
│             idealista_info_extraction.room_uniclass_assessments     │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: GAP ANALYSIS                                               │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:                                                             │
│    • Listing's rule_verifications (what's wrong)                    │
│    • Listing's uniclass_assessments (element conditions)            │
│    • Comparable properties' data (target standard)                  │
│                                                                     │
│  Process:                                                           │
│    Compare listing vs "very good" condition properties:             │
│    • Rules: Which issues exist in listing but not in comparables?   │
│    • Uniclass: Which elements are "poor" vs comparables' "good"?    │
│    • Energy: What's the gap in estimated energy rating?             │
│                                                                     │
│  Output:                                                            │
│    • rules_gap: [{rule_id, description, priority}]                  │
│    • elements_gap: [{uniclass_code, current_condition, target}]     │
│    • energy_gap: {current_rating, target_rating, upgrades_needed}   │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: SCOPE BUILDER                                              │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:                                                             │
│    • rules_gap (code violations to fix)                             │
│    • elements_gap (deteriorated elements to replace)                │
│    • energy_gap (efficiency upgrades needed)                        │
│    • bracket (fast_sell / fair_market / premium)                    │
│                                                                     │
│  Process:                                                           │
│    Convert gaps into concrete work items with BCCA keywords:        │
│    • Rule violation → Work item (e.g., "no grounding" → "puesta     │
│      a tierra vivienda")                                            │
│    • Poor element → Replacement (e.g., "Ss_70_30_27 poor" →         │
│      "cuadro eléctrico vivienda")                                   │
│    • Energy gap → Upgrades (e.g., "E→D rating" → "ventana PVC       │
│      doble cristal")                                                │
│                                                                     │
│  Output:                                                            │
│    scope_items: [                                                   │
│      {                                                              │
│        id: "ELEC_001",                                              │
│        description: "Replace consumer unit",                        │
│        category: "ELECTRICAL",                                      │
│        bcca_keyword: "cuadro eléctrico vivienda",                   │
│        room: "general",                                             │
│        priority: "high",                                            │
│        source: "rule_violation",                                    │
│        source_id: "REBT_001"                                        │
│      },                                                             │
│      ...                                                            │
│    ]                                                                │
│                                                                     │
│  Always included:                                                   │
│    • Demolition and site prep                                       │
│    • Construction waste removal                                     │
│    • Final cleaning                                                 │
│    • Obra menor license (or obra mayor if structural)               │
│    • Boletín eléctrico (if electrical work)                         │
│    • Gas certificate (if gas work)                                  │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: KG PRICING                                                 │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:                                                             │
│    • scope_items (with bcca_keywords)                               │
│    • listing area (m²)                                              │
│                                                                     │
│  Process:                                                           │
│    KGEstimator does:                                                │
│    1. Semantic search BCCA database for each keyword                │
│    2. Find matching price entries (€/m², €/unit, €/ml)              │
│    3. Calculate quantities based on room sizes                      │
│    4. Apply regional factors                                        │
│    5. Sum into Bill of Quantities                                   │
│                                                                     │
│  Output:                                                            │
│    boq: {                                                           │
│      line_items: [                                                  │
│        {                                                            │
│          description: "Cuadro eléctrico 12 módulos",                │
│          unit: "ud",                                                │
│          quantity: 1,                                               │
│          unit_price: 485.00,                                        │
│          total: 485.00,                                             │
│          bcca_code: "IEP010"                                        │
│        },                                                           │
│        ...                                                          │
│      ],                                                             │
│      pem_subtotal: 53400.00,      # Direct costs                    │
│      gastos_generales: 6942.00,   # 13% overhead                    │
│      beneficio_industrial: 3204.00, # 6% profit                     │
│      base_imponible: 63546.00,                                      │
│      iva: 13345.00,               # 21% VAT                         │
│      total_with_iva: 76891.00                                       │
│    }                                                                │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: TIMELINE ESTIMATION                                        │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:                                                             │
│    • scope_items (categorized work)                                 │
│    • boq (total cost indicates complexity)                          │
│    • property_info (m² affects duration)                            │
│                                                                     │
│  Process:                                                           │
│    Gemini analyzes scope and produces realistic timeline:           │
│    • Considers trade sequencing (electrical before plaster)         │
│    • Accounts for permit wait times                                 │
│    • Factors in Spanish construction norms                          │
│                                                                     │
│  Output:                                                            │
│    timeline: {                                                      │
│      total_weeks: {min: 6, max: 8},                                 │
│      phases: [                                                      │
│        {                                                            │
│          name: "Demolition & Prep",                                 │
│          week_start: 1,                                             │
│          week_end: 2,                                               │
│          tasks: ["Strip finishes", "Remove debris"],                │
│          category: "PREP"                                           │
│        },                                                           │
│        {                                                            │
│          name: "First Fix",                                         │
│          week_start: 2,                                             │
│          week_end: 4,                                               │
│          tasks: ["Electrical rough-in", "Plumbing rough-in"],       │
│          category: "MEP"                                            │
│        },                                                           │
│        ...                                                          │
│      ],                                                             │
│      milestones: [                                                  │
│        {week: 2, description: "Demolition complete"},               │
│        {week: 4, description: "First fix sign-off"},                │
│        {week: 8, description: "Handover"}                           │
│      ],                                                             │
│      critical_path: ["Electrical", "Tiling", "Final inspection"]    │
│    }                                                                │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6: IMAGE GENERATION                                           │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Input:                                                             │
│    • Listing photos                                                 │
│    • Room analyses (which room is which)                            │
│    • Scope items (what changes)                                     │
│    • Bracket (styling level)                                        │
│                                                                     │
│  Process:                                                           │
│                                                                     │
│    V2 - SELECT PHOTO:                                               │
│      • Find BIGGEST INTERIOR room (living room > kitchen > etc)     │
│      • Use Gemini to estimate room size from photo                  │
│      • ONE photo selected for ALL brackets                          │
│                                                                     │
│    V1 - DEFURNISH:                                                  │
│      • Remove furniture from selected photo                         │
│      • Keep walls, floors, windows, structure                       │
│                                                                     │
│    V3 - GENERATE PROMPTS:                                           │
│      • Create bracket-specific styling prompt                       │
│      • fast_sell: "basic refresh, neutral, clean"                   │
│      • fair_market: "modern update, quality finishes"               │
│      • premium: "high-end, designer materials"                      │
│                                                                     │
│    V4 - RENDER:                                                     │
│      • Apply prompt to defurnished image                            │
│      • STRICT: No structural changes (same walls/doors/windows)     │
│      • Output: Photorealistic "after" image                         │
│                                                                     │
│  Output:                                                            │
│    • before_url: Original photo                                     │
│    • after_url: Rendered "after" photo for this bracket             │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 7: SAVE TO DATABASE                                           │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  All results saved to: listing_bracket_analyses                     │
│                                                                     │
│  {                                                                  │
│    listing_id: 6,                                                   │
│    view_type: "casafari",                                           │
│    bracket: "fair_market",                                          │
│    target_price: 485000,                                            │
│    asking_price: 375000,                                            │
│    renovation_cost: 76891,                                          │
│    total_investment: 451891,                                        │
│    potential_margin: 33109,                                         │
│    scope_of_work: {...},                                            │
│    boq: {...},                                                      │
│    timeline: {...},                                                 │
│    before_image: "https://...",                                     │
│    after_image: "https://...",                                      │
│    comparables: [...],                                              │
│    viewing_checklist: [...],                                        │
│    compliance_notes: {...}                                          │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 8: DISPLAY IN MODAL                                           │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Frontend receives analysis data and renders:                       │
│    • The Math (investment calculation)                              │
│    • Before/After slider                                            │
│    • Scope of Work (categorized, with costs)                        │
│    • Timeline (phases with weeks)                                   │
│    • Comparable properties carousel                                 │
│    • Viewing checklist                                              │
│    • Share/Export button                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Photo Analysis

**Goal**: Analyze listing photos to identify code violations and element conditions.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pipeline/steps/verify_rules.py` | Check photos against Spanish building codes |
| `backend/pipeline/steps/assess_uniclass.py` | Identify systems/elements and their condition |
| `backend/pipeline/schemas/rules_engine_v2.json` | Rule definitions with visual evidence markers |
| `standards/uniclass-ss-systems.csv` | System codes (electrical, plumbing, etc.) |
| `standards/uniclass-pr-products.csv` | Product codes (fixtures, materials, etc.) |

### What verify_rules.py Does

Checks each photo against 8 Spanish regulatory sources:

1. **CTE-DB-HE** (Energy) - Window quality, insulation evidence
2. **CTE-DB-HS** (Health) - Ventilation, waterproofing
3. **CTE-DB-SI** (Fire) - Fire doors, extinguishers
4. **CTE-DB-SUA** (Safety) - Handrails, non-slip floors
5. **REBT 2002** (Electrical) - Panel type, outlet standards
6. **RITE** (HVAC) - Heating/cooling systems
7. **Cédula** (Habitability) - Minimum room sizes, light
8. **ITE** (Inspection) - Structural, facade, installations

For each rule, outputs:
```json
{
  "rule_id": "REBT_001",
  "rule_name": "Electrical Panel Modern",
  "status": "FAIL",
  "confidence": 0.85,
  "evidence": "Visible fuse box with ceramic fuses, pre-1980s design",
  "photo_url": "https://..."
}
```

### What assess_uniclass.py Does

Identifies building elements using Uniclass 2015 taxonomy:

```json
{
  "uniclass_code": "Ss_70_30_27",
  "element_name": "Electrical distribution boards",
  "condition": "poor",
  "confidence": 0.82,
  "evidence": "Outdated panel with no RCD protection visible",
  "photo_url": "https://..."
}
```

Condition scale: `excellent` → `good` → `fair` → `poor` → `very_poor`

### API Endpoint

```
POST /api/listings/{id}/analyze-photos
```

Runs both analyses on all listing photos. Results stored in `idealista_info_extraction` table.

---

## Phase 2: Gap Analysis

**Goal**: Compare listing condition to "very good" condition comparables to identify what needs fixing.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pipeline/gap_analysis.py` | Compare listing vs comparables |

### Logic

```python
def analyze_gap(
    listing_rule_verifications: List[Dict],
    listing_uniclass_assessments: List[Dict],
    comparable_data: List[Dict]  # From Casafari "very-good" condition
) -> GapAnalysis:
    
    rules_gap = []
    elements_gap = []
    
    # 1. RULES GAP
    # Find rules that FAIL in listing
    for rule in listing_rule_verifications:
        if rule["status"] == "FAIL":
            rules_gap.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["rule_name"],
                "description": RULES_ENGINE[rule["rule_id"]]["description"],
                "priority": RULES_ENGINE[rule["rule_id"]]["priority"],
                "fix_category": RULES_ENGINE[rule["rule_id"]]["category"],
                "evidence": rule["evidence"]
            })
    
    # 2. ELEMENTS GAP
    # Find elements in poor/very_poor condition
    for element in listing_uniclass_assessments:
        if element["condition"] in ["poor", "very_poor"]:
            elements_gap.append({
                "uniclass_code": element["uniclass_code"],
                "element_name": element["element_name"],
                "current_condition": element["condition"],
                "target_condition": "good",  # Standard for "very good" property
                "evidence": element["evidence"]
            })
    
    # 3. ENERGY GAP
    # Estimate current vs target energy rating
    energy_gap = estimate_energy_gap(
        listing_uniclass_assessments,
        listing_rule_verifications
    )
    
    return GapAnalysis(
        rules_gap=rules_gap,
        elements_gap=elements_gap,
        energy_gap=energy_gap
    )
```

### Energy Gap Estimation

Based on visible evidence (windows, heating, insulation), estimate rating:

| Evidence | Estimated Rating |
|----------|------------------|
| Single-glazed windows, old radiators | E or F |
| Double-glazed PVC, modern boiler | C or D |
| Triple-glazed, heat pump visible | A or B |

Target for "very good" comparable: C rating (minimum for post-2020 sales)

---

## Phase 3: Scope Builder

**Goal**: Convert gaps into concrete work items with BCCA keywords for pricing.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pipeline/scope_builder.py` | Convert gaps to work items |

### Mapping Tables

**Rules to Scope Items:**

```python
RULE_TO_SCOPE = {
    "REBT_001": {  # Outdated electrical panel
        "description": "Replace electrical consumer unit",
        "bcca_keyword": "cuadro eléctrico vivienda monofásico",
        "category": "ELECTRICAL",
        "priority": "high"
    },
    "REBT_002": {  # No grounding
        "description": "Install grounding system",
        "bcca_keyword": "puesta a tierra vivienda",
        "category": "ELECTRICAL",
        "priority": "critical"
    },
    "CTE_HS_003": {  # Poor ventilation
        "description": "Install mechanical ventilation",
        "bcca_keyword": "extractor baño vivienda",
        "category": "HVAC",
        "priority": "medium"
    },
    # ... all rules mapped
}
```

**Uniclass to Scope Items:**

```python
UNICLASS_TO_SCOPE = {
    "Ss_70_30_27": {  # Distribution boards
        "description": "Replace distribution board",
        "bcca_keyword": "cuadro eléctrico vivienda",
        "category": "ELECTRICAL"
    },
    "Ss_70_60_93": {  # Water supply systems
        "description": "Replace water supply pipes",
        "bcca_keyword": "fontanería vivienda PEX multicapa",
        "category": "PLUMBING"
    },
    "Ss_25_60_95": {  # Windows
        "description": "Replace windows with double glazing",
        "bcca_keyword": "ventana PVC doble cristal RPT",
        "category": "ENVELOPE"
    },
    # ... all codes mapped
}
```

### Always Included Items

```python
ALWAYS_INCLUDE = [
    {
        "description": "Demolition and site preparation",
        "bcca_keyword": "demolición interior vivienda",
        "category": "DEMOLITION"
    },
    {
        "description": "Construction waste removal",
        "bcca_keyword": "gestión residuos construcción contenedor",
        "category": "DEMOLITION"
    },
    {
        "description": "Final construction cleaning",
        "bcca_keyword": "limpieza obra vivienda",
        "category": "OTHER"
    }
]

# Conditional permits
PERMITS = {
    "any_work": {
        "description": "Obra menor license",
        "bcca_keyword": "licencia obra menor ayuntamiento",
        "category": "PERMITS",
        "notes": "Processing: 5-10 business days"
    },
    "electrical": {
        "description": "Electrical certificate (Boletín)",
        "bcca_keyword": "boletín eléctrico instalador autorizado",
        "category": "PERMITS"
    },
    "gas": {
        "description": "Gas installation certificate",
        "bcca_keyword": "certificado instalación gas",
        "category": "PERMITS"
    },
    "structural": {
        "description": "Obra mayor license + architect project",
        "bcca_keyword": "licencia obra mayor proyecto técnico",
        "category": "PERMITS",
        "notes": "Processing: 30-60 business days"
    }
}
```

### Build Scope Function

```python
def build_scope(
    rules_gap: List[Dict],
    elements_gap: List[Dict],
    energy_gap: Dict,
    bracket: str  # fast_sell, fair_market, premium
) -> List[ScopeItem]:
    
    scope = []
    categories_touched = set()
    
    # 1. Add items from rules gap
    for rule in rules_gap:
        if rule["rule_id"] in RULE_TO_SCOPE:
            item = RULE_TO_SCOPE[rule["rule_id"]].copy()
            item["source"] = "rule_violation"
            item["source_id"] = rule["rule_id"]
            scope.append(item)
            categories_touched.add(item["category"])
    
    # 2. Add items from elements gap
    for element in elements_gap:
        if element["uniclass_code"] in UNICLASS_TO_SCOPE:
            item = UNICLASS_TO_SCOPE[element["uniclass_code"]].copy()
            item["source"] = "element_condition"
            item["source_id"] = element["uniclass_code"]
            scope.append(item)
            categories_touched.add(item["category"])
    
    # 3. Add energy upgrades based on gap and bracket
    energy_items = get_energy_upgrades(energy_gap, bracket)
    scope.extend(energy_items)
    
    # 4. Add bracket-specific finishes
    finish_items = get_finish_scope(bracket)
    scope.extend(finish_items)
    
    # 5. Add always-included items
    scope.extend(ALWAYS_INCLUDE)
    
    # 6. Add required permits
    scope.append(PERMITS["any_work"])
    if "ELECTRICAL" in categories_touched:
        scope.append(PERMITS["electrical"])
    if "GAS" in categories_touched:
        scope.append(PERMITS["gas"])
    
    return scope
```

### Bracket-Specific Finishes

```python
BRACKET_FINISHES = {
    "fast_sell": [
        {"description": "Repaint walls (white)", "bcca_keyword": "pintura plástica mate blanca", "category": "FINISHES"},
        {"description": "Basic floor refinish", "bcca_keyword": "pulido terrazo", "category": "FINISHES"},
    ],
    "fair_market": [
        {"description": "Repaint walls (neutral palette)", "bcca_keyword": "pintura plástica satinada", "category": "FINISHES"},
        {"description": "Laminate flooring", "bcca_keyword": "tarima flotante AC4", "category": "FINISHES"},
        {"description": "Update kitchen fronts", "bcca_keyword": "frentes cocina melamina", "category": "FINISHES"},
        {"description": "Bathroom tiles", "bcca_keyword": "alicatado baño porcelánico", "category": "FINISHES"},
    ],
    "premium": [
        {"description": "Designer paint finish", "bcca_keyword": "pintura decorativa efecto", "category": "FINISHES"},
        {"description": "Engineered hardwood flooring", "bcca_keyword": "parquet multicapa roble", "category": "FINISHES"},
        {"description": "Full kitchen renovation", "bcca_keyword": "cocina completa lacada", "category": "FINISHES"},
        {"description": "Premium bathroom remodel", "bcca_keyword": "reforma baño completo porcelánico rectificado", "category": "FINISHES"},
        {"description": "LED ambient lighting", "bcca_keyword": "iluminación LED empotrada dimable", "category": "ELECTRICAL"},
    ]
}
```

---

## Phase 4: KG Pricing

**Goal**: Price each scope item using BCCA database and generate Bill of Quantities.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pricing/kg_estimator.py` | KG-powered pricing engine |
| `data/bcca_prices.json` | BCCA database (Spanish construction prices) |

### How KGEstimator Works

```python
class KGEstimator:
    def __init__(self):
        self.bcca_db = load_bcca_database()
        self.embeddings = load_bcca_embeddings()  # Pre-computed
    
    def estimate(self, scope_items: List[Dict], area_m2: float) -> BoQ:
        line_items = []
        
        for item in scope_items:
            # 1. Semantic search for BCCA match
            matches = self.search_bcca(item["bcca_keyword"])
            best_match = matches[0]  # Highest similarity
            
            # 2. Calculate quantity
            quantity = self.calculate_quantity(
                bcca_entry=best_match,
                item=item,
                area_m2=area_m2
            )
            
            # 3. Create line item
            line_items.append({
                "description": best_match["descripcion"],
                "unit": best_match["unidad"],  # m², ud, ml
                "quantity": quantity,
                "unit_price": best_match["precio"],
                "total": quantity * best_match["precio"],
                "bcca_code": best_match["codigo"],
                "scope_item": item["description"]
            })
        
        # 4. Calculate totals
        pem = sum(item["total"] for item in line_items)
        gg = pem * 0.13  # 13% Gastos Generales
        bi = pem * 0.06  # 6% Beneficio Industrial
        base = pem + gg + bi
        iva = base * 0.21  # 21% IVA
        
        return BoQ(
            line_items=line_items,
            pem_subtotal=pem,
            gastos_generales=gg,
            beneficio_industrial=bi,
            base_imponible=base,
            iva=iva,
            total_with_iva=base + iva
        )
    
    def calculate_quantity(self, bcca_entry, item, area_m2):
        unit = bcca_entry["unidad"]
        
        if unit == "m²":
            # Scale by property area
            if item["category"] == "FINISHES":
                return area_m2 * 0.8  # ~80% paintable/tileable
            elif item["category"] == "ENVELOPE":
                return area_m2 * 0.15  # ~15% window area
            else:
                return area_m2
        
        elif unit == "ud":
            # Count units
            if "baño" in item["description"].lower():
                return 1  # Assume 1 bathroom
            elif "cocina" in item["description"].lower():
                return 1
            elif "ventana" in item["description"].lower():
                return max(4, area_m2 // 20)  # ~1 window per 20m²
            else:
                return 1
        
        elif unit == "ml":
            # Linear meters
            if "fontanería" in item["description"].lower():
                return area_m2 * 0.5  # ~0.5ml pipe per m²
            elif "eléctrico" in item["description"].lower():
                return area_m2 * 0.8  # ~0.8ml cable per m²
            else:
                return area_m2 * 0.3
        
        return 1  # Default
```

### Sample BCCA Entry

```json
{
  "codigo": "IEP010",
  "descripcion": "Cuadro general de mando y protección para vivienda unifamiliar, formado por caja empotrable de material aislante con puerta opaca, para alojamiento del interruptor de control de potencia (ICP) en compartimento independiente y target protección (RCD) de 40A/30mA, 2 interruptores automáticos de 10A, 2 de 16A, 1 de 25A.",
  "unidad": "ud",
  "precio": 485.32,
  "capitulo": "Instalaciones eléctricas"
}
```

---

## Phase 5: Timeline Estimation

**Goal**: Generate realistic renovation timeline based on scope and Spanish construction norms.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pipeline/steps/estimate_timeline.py` | Gemini-powered timeline generation |

### Prompt to Gemini

```python
TIMELINE_PROMPT = """You are a Spanish construction project manager.
Given this scope of work and total cost, provide a realistic renovation timeline.

SCOPE OF WORK:
{scope_summary}

TOTAL COST (with IVA): €{total_cost}
PROPERTY SIZE: {area_m2} m²

Consider:
- Spanish construction practices and typical team sizes
- Trade sequencing (electrical before plastering, etc.)
- Permit processing times (obra menor: 5-10 days)
- Weather considerations for exterior work
- Standard working hours (8:00-18:00, Mon-Fri)

Return a JSON object with:
- total_weeks: {min, max}
- phases: array of {name, week_start, week_end, tasks, category}
- milestones: array of {week, description}
- critical_path: array of task names on critical path
"""
```

### Standard Phase Durations

| Phase | Small (<50m²) | Medium (50-100m²) | Large (>100m²) |
|-------|---------------|-------------------|----------------|
| Demolition | 3-5 days | 5-7 days | 7-10 days |
| First Fix (MEP) | 5-7 days | 7-10 days | 10-14 days |
| Plastering | 3-5 days | 5-7 days | 7-10 days |
| Flooring | 3-5 days | 5-7 days | 7-10 days |
| Second Fix | 3-5 days | 5-7 days | 7-10 days |
| Painting | 3-5 days | 5-7 days | 7-10 days |
| Final/Snagging | 2-3 days | 3-5 days | 5-7 days |

---

## Phase 6: Image Generation

**Goal**: Create before/after visualization showing renovation result.

### Files Involved

| File | Purpose |
|------|---------|
| `backend/pipeline/steps/visuals.py` | V1-V4 image pipeline |

### V2: Select Best Photo

```python
async def select_best_before_photo(photos: List[str], room_analyses: List[Dict]) -> Dict:
    """
    Select the BIGGEST INTERIOR room for visualization.
    
    Priority:
    1. Largest room by estimated area
    2. Prefer: living room > kitchen > bedroom > bathroom
    3. Must be interior (not exterior/garden/parking)
    """
    candidates = []
    
    for photo_url, analysis in zip(photos, room_analyses):
        room_type = analysis.get("room_type", "unknown")
        
        # Skip exterior
        if room_type in ["exterior", "facade", "garden", "parking", "terrace"]:
            continue
        
        # Estimate room size using Gemini
        estimated_area = await estimate_room_size(photo_url)
        
        # Calculate score
        score = estimated_area
        PRIORITY_BONUS = {"living_room": 20, "salon": 20, "kitchen": 15, "bedroom": 10, "bathroom": 5}
        score += PRIORITY_BONUS.get(room_type.lower(), 0)
        
        candidates.append({
            "photo_url": photo_url,
            "room_type": room_type,
            "estimated_area_m2": estimated_area,
            "score": score,
            "visible_elements": analysis.get("uniclass_elements", [])
        })
    
    # Return highest scoring
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[0] if candidates else None
```

### V1: Defurnish

```python
async def defurnish_photo(photo_url: str) -> str:
    """
    Remove furniture from photo, keeping structure.
    
    Uses Gemini image editing to:
    - Remove sofas, tables, chairs, decorations
    - Keep walls, floors, windows, doors, built-in fixtures
    """
    prompt = """Remove all movable furniture from this room photo.
    
    REMOVE:
    - Sofas, chairs, tables
    - Rugs, curtains, decorations
    - Personal items, plants
    
    KEEP EXACTLY AS-IS:
    - Walls, floors, ceilings
    - Windows, doors
    - Built-in cabinets, counters
    - Light fixtures (ceiling)
    
    Make the room look empty but clean."""
    
    result = await call_gemini_image_edit(photo_url, prompt)
    return await store_image(result.image_data, "defurnished")
```

### V3: Generate Prompts

```python
BRACKET_STYLES = {
    "fast_sell": {
        "style": "clean, fresh, neutral, move-in ready",
        "materials": "white walls, basic laminate floor, standard fixtures",
        "mood": "bright, airy, neutral palette"
    },
    "fair_market": {
        "style": "modern, contemporary, quality finishes",
        "materials": "light grey walls, wood-look flooring, chrome fixtures",
        "mood": "warm, inviting, Scandinavian-inspired"
    },
    "premium": {
        "style": "luxury, designer, high-end materials",
        "materials": "feature wall, hardwood floors, brushed nickel fixtures",
        "mood": "sophisticated, magazine-worthy, premium feel"
    }
}

def generate_render_prompt(bracket: str, room_type: str, scope_items: List[Dict]) -> str:
    style = BRACKET_STYLES[bracket]
    
    changes = [item["description"] for item in scope_items if item["category"] == "FINISHES"]
    
    return f"""Transform this {room_type} to a {bracket.replace('_', ' ')} renovation standard.

STYLE: {style['style']}
MATERIALS: {style['materials']}
MOOD: {style['mood']}

SPECIFIC CHANGES:
{chr(10).join(f'- {c}' for c in changes)}

⚠️ CRITICAL CONSTRAINTS - DO NOT MODIFY:
- Room dimensions and shape
- Window positions and sizes
- Door positions
- Ceiling height
- Any structural elements

ONLY change surface finishes: paint, flooring, tiles, fixtures, lighting.

Make it photorealistic and naturally lit."""
```

### V4: Render After Image

```python
async def render_after_image(defurnished_url: str, prompt: str, bracket: str) -> str:
    """Generate photorealistic after image."""
    
    result = await call_gemini_image_edit(
        source_image_url=defurnished_url,
        edit_prompt=prompt,
        model="gemini-2.5-flash-image"
    )
    
    if result.success and result.image_data:
        return await store_image(result.image_data, f"after_{bracket}")
    
    return None
```

---

## Phase 7: Frontend Modal

**Goal**: Display analysis results in mobile-friendly full-screen modal with before/after slider.

### Files Involved

| File | Purpose |
|------|---------|
| `frontend/src/components/renovation/BracketAnalysisModal.tsx` | Full-screen modal |
| `frontend/src/components/renovation/BeforeAfterSlider.tsx` | Interactive slider component |

### BeforeAfterSlider Component

```tsx
'use client';

import React, { useState, useRef, useCallback } from 'react';

interface BeforeAfterSliderProps {
  beforeImage: string;
  afterImage: string;
  beforeLabel?: string;
  afterLabel?: string;
}

export const BeforeAfterSlider: React.FC<BeforeAfterSliderProps> = ({
  beforeImage,
  afterImage,
  beforeLabel = "Before",
  afterLabel = "After"
}) => {
  const [position, setPosition] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const handleMove = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setPosition(pct);
  }, []);

  return (
    <div 
      ref={containerRef}
      className="relative w-full aspect-[4/3] overflow-hidden rounded-lg cursor-ew-resize select-none touch-none"
      onMouseDown={() => isDragging.current = true}
      onMouseUp={() => isDragging.current = false}
      onMouseLeave={() => isDragging.current = false}
      onMouseMove={(e) => isDragging.current && handleMove(e.clientX)}
      onTouchMove={(e) => handleMove(e.touches[0].clientX)}
    >
      {/* After (background) */}
      <img src={afterImage} alt={afterLabel} className="absolute inset-0 w-full h-full object-cover" draggable={false} />
      
      {/* Before (clipped) */}
      <div className="absolute inset-0 overflow-hidden" style={{ width: `${position}%` }}>
        <img 
          src={beforeImage} 
          alt={beforeLabel} 
          className="h-full object-cover"
          style={{ width: containerRef.current?.offsetWidth, maxWidth: 'none' }}
          draggable={false}
        />
      </div>
      
      {/* Slider */}
      <div 
        className="absolute top-0 bottom-0 w-1 bg-white shadow-lg"
        style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 bg-white rounded-full shadow-lg flex items-center justify-center">
          <span className="text-gray-400">⇄</span>
        </div>
      </div>
      
      {/* Labels */}
      <div className="absolute top-3 left-3 bg-black/50 text-white text-xs px-2 py-1 rounded">{beforeLabel}</div>
      <div className="absolute top-3 right-3 bg-black/50 text-white text-xs px-2 py-1 rounded">{afterLabel}</div>
    </div>
  );
};
```

### Modal Structure

```tsx
export const BracketAnalysisModal: React.FC<Props> = ({ analysis, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 bg-white overflow-y-auto">
      {/* Sticky Header */}
      <header className="sticky top-0 bg-white border-b p-4 flex items-center justify-between z-10">
        <button onClick={onClose}><ArrowLeft /></button>
        <h2>{analysis.bracket.toUpperCase()} PATH</h2>
        <ShareExportButton analysis={analysis} />
      </header>

      <main className="p-4 max-w-lg mx-auto space-y-6">
        {/* THE MATH */}
        <section className="bg-gray-50 rounded-lg p-4">
          <h3>THE MATH</h3>
          <div className="space-y-2 text-sm">
            <Row label="Asking Price" value={formatPrice(analysis.asking_price)} />
            <Row label="+ Renovation" value={formatPrice(analysis.renovation_cost)} />
            <Divider />
            <Row label="= Total Investment" value={formatPrice(analysis.total_investment)} bold />
            <Spacer />
            <Row label="Target Value" value={formatPrice(analysis.target_price)} blue />
            <Divider />
            <Row 
              label="= Potential Margin" 
              value={formatPrice(analysis.potential_margin)} 
              color={analysis.potential_margin >= 0 ? 'green' : 'red'} 
              bold 
            />
          </div>
        </section>

        {/* BEFORE/AFTER SLIDER */}
        <section>
          <h3>WHAT IT COULD LOOK LIKE</h3>
          <BeforeAfterSlider
            beforeImage={analysis.before_image}
            afterImage={analysis.after_image}
            beforeLabel="Current"
            afterLabel={`After (${analysis.bracket})`}
          />
        </section>

        {/* SCOPE OF WORK */}
        <section>
          <h3>SCOPE OF WORK</h3>
          {analysis.scope_of_work.categories.map(cat => (
            <CategoryCard key={cat.name} category={cat} />
          ))}
        </section>

        {/* TIMELINE */}
        <section>
          <h3>TIMELINE</h3>
          <TimelineGantt phases={analysis.timeline.phases} />
          <p className="text-center font-semibold mt-4">
            Estimated: {analysis.timeline.total_weeks.min}-{analysis.timeline.total_weeks.max} weeks
          </p>
        </section>

        {/* COMPARABLES */}
        <section>
          <h3>COMPARABLE PROPERTIES</h3>
          <div className="flex gap-3 overflow-x-auto pb-2 snap-x">
            {analysis.comparables.map(comp => (
              <MiniListingCard key={comp.id} comp={comp} />
            ))}
          </div>
        </section>

        {/* VIEWING CHECKLIST */}
        <section>
          <h3>VIEWING CHECKLIST</h3>
          <p className="text-sm text-gray-600 mb-3">
            When you visit, check these items to confirm our analysis:
          </p>
          <ul className="space-y-2">
            {analysis.viewing_checklist.map((item, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <span className="text-gray-400">□</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* COMPLIANCE NOTE */}
        <section className="bg-blue-50 rounded-lg p-4">
          <h3>STANDARDS COMPLIANCE</h3>
          <p className="text-sm text-gray-700">
            This renovation is designed to meet Cédula de Habitabilidad requirements, 
            REBT 2002 electrical safety, and CTE-DB-HE energy guidelines.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Note: Final certification requires architect sign-off. Export detailed specs for review.
          </p>
        </section>
      </main>
    </div>
  );
};
```

---

## Phase 8: PDF Export

**Goal**: Generate detailed architect-ready PDF with full BoQ, CTE references, and compliance checklist.

### Content (For Architects)

```
RENOVATION PROJECT SPECIFICATION
================================
Property: [Address]
Listing ID: [ID]
Target: [Bracket] Renovation
Generated: [Date]

1. EXECUTIVE SUMMARY
   - Current condition assessment
   - Target standard
   - Total budget estimate
   - Timeline estimate

2. BILL OF QUANTITIES
   Full line-item breakdown:
   - BCCA code
   - Description
   - Unit
   - Quantity
   - Unit price
   - Total
   - Source (rule/element gap)

3. TECHNICAL SPECIFICATIONS
   For each scope item:
   - Referenced standard (CTE clause, REBT article)
   - Current condition evidence
   - Required specification
   - Acceptance criteria

4. COMPLIANCE CHECKLIST
   □ Cédula requirements met
   □ REBT compliance items
   □ CTE-DB-HE requirements
   □ ITE-related items

5. PHOTO EVIDENCE
   - Before photos with annotations
   - Rule verification results
   - Uniclass assessments

6. APPENDICES
   A. Rules Engine Reference
   B. CTE-DB-HE Tables (U-values)
   C. BCCA Database Excerpts
```

---

## File Reference

### Backend Files

| File | Purpose | Status |
|------|---------|--------|
| `backend/routes/renovation.py` | API endpoints | ✅ Exists |
| `backend/pipeline/steps/verify_rules.py` | Rule checking | ✅ Exists |
| `backend/pipeline/steps/assess_uniclass.py` | Element assessment | ✅ Exists |
| `backend/pipeline/gap_analysis.py` | Gap calculation | 🔲 Create |
| `backend/pipeline/scope_builder.py` | Scope generation | ✅ Exists (needs update) |
| `backend/pricing/kg_estimator.py` | KG pricing | ✅ Exists |
| `backend/pipeline/steps/estimate_timeline.py` | Timeline | ✅ Exists |
| `backend/pipeline/steps/visuals.py` | Image generation | ✅ Exists (needs update) |

### Frontend Files

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/components/renovation/ComparablesCard.tsx` | Main card | ✅ Exists |
| `frontend/src/components/renovation/BracketAnalysisModal.tsx` | Modal | ✅ Exists (needs slider) |
| `frontend/src/components/renovation/BeforeAfterSlider.tsx` | Slider | 🔲 Create |

### Database Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `listing_market_stats` | Casafari market data | ✅ Exists |
| `listing_comparables` | Individual comparables | ✅ Exists |
| `listing_bracket_analyses` | Full analysis per bracket | ✅ Exists |
| `listing_visual_selections` | Selected before photo | ✅ Exists |
| `listing_defurnished_photos` | Defurnished photos | ✅ Exists |
| `listing_render_prompts` | Rendering prompts | ✅ Exists |
| `listing_after_photos` | Generated after images | ✅ Exists |

---

## Implementation Checklist

### Phase 1: Photo Analysis
- [ ] Run `verify_rules.py` on listing photos
- [ ] Run `assess_uniclass.py` on listing photos
- [ ] Store results in `idealista_info_extraction`
- [ ] Add API endpoint: `POST /api/listings/{id}/analyze-photos`

### Phase 2: Gap Analysis
- [ ] Create `backend/pipeline/gap_analysis.py`
- [ ] Implement `analyze_gap()` function
- [ ] Add energy gap estimation

### Phase 3: Scope Builder
- [ ] Complete RULE_TO_SCOPE mapping (all rules)
- [ ] Complete UNICLASS_TO_SCOPE mapping (all codes)
- [ ] Implement bracket-specific finishes
- [ ] Add permit logic (obra menor/mayor, boletín, gas)

### Phase 4: KG Pricing
- [ ] Verify BCCA keyword matching
- [ ] Test quantity calculations
- [ ] Verify GG/BI/IVA calculations

### Phase 5: Timeline
- [ ] Test Gemini timeline generation
- [ ] Verify phase sequencing logic
- [ ] Add fallback heuristic

### Phase 6: Image Generation
- [ ] Implement V2 (select biggest interior room)
- [ ] Test V1 (defurnish)
- [ ] Implement V3 (bracket-specific prompts)
- [ ] Test V4 (render after images)
- [ ] Store images in Supabase

### Phase 7: Frontend Modal
- [ ] Create `BeforeAfterSlider.tsx`
- [ ] Update `BracketAnalysisModal.tsx` with slider
- [ ] Add viewing checklist section
- [ ] Add compliance note section
- [ ] Implement share functionality (native share API)

### Phase 8: PDF Export
- [ ] Design PDF template
- [ ] Implement PDF generation (react-pdf or server-side)
- [ ] Include full BoQ
- [ ] Include CTE references
- [ ] Include compliance checklist
- [ ] Include photo evidence

### Integration Testing
- [ ] Test full pipeline for listing 6
- [ ] Verify database saves correctly
- [ ] Test mobile modal display
- [ ] Test before/after slider (touch + mouse)
- [ ] Test share functionality
- [ ] Test PDF export

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial complete plan |
