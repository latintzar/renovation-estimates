Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Analysis Pipeline Architecture

**Date**: 2026-01-08  
**Status**: Approved Design  
**Purpose**: Clean separation of concerns for listing and comparable analysis

> **📋 COMPANION DOC**: This document defines **CODE STRUCTURE** (where things live, how to build).  
> For **DETAILED METHODOLOGY** (thresholds, schemas, constraints), see **`MARKET_COMPARISON_ARCHITECTURE.md`**.  
> Always consult both documents when implementing. See [Methodology Cross-References](#methodology-cross-references) section.

---

## Overview

The analysis pipeline has three layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: CORE AI FUNCTIONS                          │
│                                                                             │
│  Pure functions. Photos in → Analysis out. NO database knowledge.           │
│                                                                             │
│  Location: Lean MVP/backend/pipeline/core/                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                      LAYER 2: ENTITY WORKFLOWS                               │
│                                                                              │
│  ┌─────────────────────────┐              ┌─────────────────────────┐       │
│  │   LISTING WORKFLOW      │              │  COMPARABLE WORKFLOW    │       │
│  │                         │              │                         │       │
│  │  • Read listing_photos  │              │  • Read comparable_*    │       │
│  │  • Call core functions  │              │  • Call core functions  │       │
│  │  • Save to listing_*    │              │  • Save to comparable_* │       │
│  └─────────────────────────┘              └─────────────────────────┘       │
│                                                                              │
│  Location: Lean MVP/backend/pipeline/workflows/                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LAYER 3: BRACKET ANALYSIS                              │
│                                                                             │
│  Shared workflow that runs AFTER both listing and comparables are analyzed. │
│  Identical for each price bracket (fast_sell / fair_market / out_of_market) │
│                                                                             │
│  • Gap Analysis: Compare listing vs analyzed comparables                    │
│  • Scope Builder: Generate renovation tasks                                 │
│  • KG Pricing: Calculate costs                                              │
│  • Timeline: Estimate duration                                              │
│  • Visuals: Generate before/after images                                    │
│                                                                             │
│  Location: Lean MVP/backend/pipeline/bracket_analysis/                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Core AI Functions

**Location**: `Lean MVP/backend/pipeline/core/`

These are **pure functions** that:
- Take photos/data as input
- Return analysis results
- Have NO knowledge of database tables
- Have NO knowledge of whether input is from listing or comparable

### Files

```
core/
├── __init__.py
├── photo_clustering.py      # P1: Zero-shot room clustering
├── room_analysis.py         # P3: Room-by-room condition analysis
├── rule_verification.py     # Spanish building code checks
├── uniclass_assessment.py   # Element identification
└── property_analysis.py     # P2: Whole property 8-lens assessment
```

### Function Signatures

```python
# core/photo_clustering.py
async def cluster_photos(
    photo_urls: List[str],
    property_context: PropertyContext  # title, price, sqm, beds, baths, description
) -> ClusteringResult:
    """
    Zero-shot clustering of photos into rooms.
    
    Returns:
        ClusteringResult:
            clusters: List[PhotoCluster]  # room groups
            excluded_content: List[ExcludedPhoto]  # floorplans, renders, etc.
            ai_image_summary: Dict  # stats on AI-generated images
    """

# core/room_analysis.py
async def analyze_room(
    photo_urls: List[str],
    room_type: str,
    room_name: str
) -> RoomAnalysisResult:
    """
    Analyze a single room's condition.
    
    Returns:
        RoomAnalysisResult:
            condition_score: int (0-100)
            condition_label: str
            condition_summary: str
            elements: Dict[str, ElementCondition]
            renovation_needs: List[RenovationNeed]
    """

# core/rule_verification.py
async def verify_rules(
    photo_urls: List[str],
    room_type: str,
    building_year: int,
    rules_engine: Dict
) -> RuleVerificationResult:
    """
    Check room against Spanish building codes.
    
    Returns:
        RuleVerificationResult:
            verifications: List[RuleVerification]
            compliance_score: float
            issues_found: List[str]
    """

# core/uniclass_assessment.py
async def assess_uniclass(
    photo_urls: List[str],
    room_type: str
) -> UniclassResult:
    """
    Identify building elements using Uniclass codes.
    
    Returns:
        UniclassResult:
            systems: List[UniclassSystem]
            products: List[UniclassProduct]
            not_assessable: List[str]
    """

# core/property_analysis.py
async def analyze_whole_property(
    photo_urls: List[str],
    property_context: PropertyContext
) -> WholePropertyResult:
    """
    8-lens whole property assessment.
    
    Returns:
        WholePropertyResult:
            condition_score: int
            condition_label: str
            structure: Dict
            finishes: Dict
            lighting: Dict
            issues: List[str]
            strengths: List[str]
    """
```

---

## Layer 2: Entity Workflows

**Location**: `Lean MVP/backend/pipeline/workflows/`

These handle database read/write for specific entity types.

### Files

```
workflows/
├── __init__.py
├── listing_workflow.py      # Full analysis for target listings
└── comparable_workflow.py   # Full analysis for comparable properties
```

### Listing Workflow

```python
# workflows/listing_workflow.py

async def run_listing_analysis(
    db: PipelineDB,
    listing_id: int,
    steps: List[str] = ["clustering", "room_analysis", "rules", "uniclass"]
) -> ListingAnalysisResult:
    """
    Run full analysis pipeline on a target listing.
    
    Reads from:
        - listings (property context)
        - listing_photos (photo URLs)
    
    Calls core functions:
        - cluster_photos()
        - analyze_room() for each cluster
        - verify_rules() for each cluster
        - assess_uniclass() for each cluster
    
    Saves to:
        - photo_clusters
        - room_analyses
        - room_rule_verifications
        - room_uniclass_assessments
        - whole_property_analysis
    """
```

### Comparable Workflow

```python
# workflows/comparable_workflow.py

async def run_comparable_analysis(
    db: PipelineDB,
    comparable_id: int,
    steps: List[str] = ["clustering", "room_analysis", "rules", "uniclass"]
) -> ComparableAnalysisResult:
    """
    Run full analysis pipeline on a comparable property.
    
    Reads from:
        - listing_comparables (property context + photo_urls)
    
    Calls core functions:
        - cluster_photos()
        - analyze_room() for each cluster
        - verify_rules() for each cluster
        - assess_uniclass() for each cluster
    
    Saves to:
        - comparable_photos (individual photo records)
        - comparable_photo_clusters
        - comparable_room_analyses
        - comparable_rule_verifications
        - comparable_uniclass_assessments
        - comparable_whole_property_analysis
    
    Updates:
        - listing_comparables.full_analysis_status
        - listing_comparables.clusters_count
        - listing_comparables.rooms_analyzed
        - listing_comparables.overall_condition_score
    """
```

---

## Layer 3: Bracket Analysis

**Location**: `Lean MVP/backend/pipeline/bracket_analysis/`

This is the **shared workflow** that runs after both the target listing AND the comparables in a bracket have been analyzed.

### Files

```
bracket_analysis/
├── __init__.py
├── gap_analysis.py          # Compare listing vs comparables
├── scope_builder.py         # Generate renovation tasks
├── kg_pricing.py            # Calculate costs from KG database
├── timeline.py              # Estimate duration
├── visuals.py               # Generate before/after images
└── orchestrator.py          # Coordinate the full bracket flow
```

### Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BRACKET ANALYSIS FLOW                               │
│                                                                             │
│  Input:                                                                     │
│    • listing_id (already analyzed via listing_workflow)                     │
│    • bracket (fast_sell | fair_market | out_of_market)                     │
│    • comparable_ids (already analyzed via comparable_workflow)              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: GAP ANALYSIS (ONE Gemini Call, Qualitative)                        │
│                                                                             │
│  Send to Gemini 3 Pro Preview in ONE call:                                  │
│  • ALL listing room analyses (rules, uniclass, condition)                   │
│  • ALL comparable room analyses for this bracket                            │
│  • Property context (year, sqm, energy rating)                              │
│                                                                             │
│  Gemini makes qualitative judgments:                                        │
│  • What's different between listing and "very good" comparables?            │
│  • What upgrades actually matter for this bracket?                          │
│  • Room-by-room breakdown with coherent house-level view                    │
│                                                                             │
│  NO deterministic thresholds. Gemini sees everything together.              │
│                                                                             │
│  Output: GapAnalysisResult                                                  │
│    • rules_gaps: List[RuleGap]                                              │
│    • elements_gaps: List[ElementGap]                                        │
│    • energy_gap: EnergyGap                                                  │
│    • viewing_checklist: List[ChecklistItem]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: SCOPE BUILDER                                                      │
│                                                                             │
│  Convert gaps into actionable renovation tasks:                             │
│                                                                             │
│  • Map rules_gaps → fix tasks (e.g., "Replace electrical panel")            │
│  • Map elements_gaps → replacement tasks (e.g., "New kitchen countertops")  │
│  • Add bracket-specific finishes (standard vs premium materials)            │
│  • Include permit requirements                                              │
│                                                                             │
│  Output: ScopeOfWork                                                        │
│    • line_items: List[LineItem]  # with BCCA codes                         │
│    • categories: Dict[str, CategoryTotal]                                   │
│    • permits_required: List[Permit]                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: KG PRICING                                                         │
│                                                                             │
│  Price each line item using BCCA/KG cost database:                          │
│                                                                             │
│  • Look up unit costs by BCCA keyword                                       │
│  • Calculate quantities from listing m²                                     │
│  • Apply location multiplier                                                │
│  • Add GG (13%) + BI (6%) + IVA (21%)                                      │
│                                                                             │
│  Output: PricingResult                                                      │
│    • pem_subtotal: int                                                      │
│    • overhead_profit: int                                                   │
│    • iva: int                                                               │
│    • total: int                                                             │
│    • line_items_priced: List[PricedLineItem]                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: TIMELINE                                                           │
│                                                                             │
│  Estimate renovation duration:                                              │
│                                                                             │
│  • Group line items by trade/phase                                          │
│  • Calculate parallel vs sequential work                                    │
│  • Add permit processing time                                               │
│  • Account for dependencies                                                 │
│                                                                             │
│  Output: TimelineResult                                                     │
│    • total_weeks_min: int                                                   │
│    • total_weeks_max: int                                                   │
│    • phases: List[Phase]                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: VISUALS (Simple Constraints)                                       │
│                                                                             │
│  Generate before/after visualization:                                       │
│                                                                             │
│  1. Select best "before" photo from listing clusters                        │
│  2. Generate "after" render with Gemini image generation                    │
│                                                                             │
│  Render instruction (simple):                                               │
│  • LOCK: Camera angle (must match original exactly)                         │
│  • LOCK: Structural features (walls, doors, windows positions)              │
│  • INSTRUCTION: "Render [this room] with [bracket] level finishes"          │
│                                                                             │
│  That's it. No overcomplicated constraint lists.                            │
│                                                                             │
│  Output: VisualsResult                                                      │
│    • before_photo_url: str                                                  │
│    • after_photo_url: str                                                   │
│    • render_prompt: str                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  FINAL OUTPUT: BracketAnalysis                                              │
│                                                                             │
│  Saved to: listing_bracket_analyses                                         │
│                                                                             │
│  • listing_id                                                               │
│  • bracket                                                                  │
│  • target_price (from market_stats for this bracket)                       │
│  • asking_price (listing.price_eur)                                         │
│  • gap (target - asking)                                                    │
│  • renovation_cost (total from KG pricing)                                  │
│  • total_investment (asking + renovation_cost)                              │
│  • potential_margin (target - total_investment)                             │
│  • scope_of_work (JSON)                                                     │
│  • timeline_breakdown (JSON)                                                │
│  • before_photo_url                                                         │
│  • after_photo_url                                                          │
│  • viewing_checklist (JSON)                                                 │
│  • compliance_notes (JSON)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. USER ADDS LISTING                                                       │
│     → Scrape from Idealista                                                 │
│     → Save to: listings, listing_photos                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. RUN LISTING ANALYSIS (automatic or on-demand)                           │
│     → listing_workflow.run_listing_analysis()                               │
│     → Uses: core/photo_clustering, core/room_analysis, etc.                 │
│     → Saves to: photo_clusters, room_analyses, room_rule_verifications, etc.│
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. FETCH COMPARABLES                                                       │
│     → Casafari API OR manual scraping                                       │
│     → Save to: listing_comparables (with photo_urls), listing_market_stats  │
│     → NO analysis yet - just raw data                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. USER CLICKS "ANALYZE" ON A BRACKET                                      │
│                                                                             │
│     a) Get comparables in that bracket (3-9 properties)                     │
│                                                                             │
│     b) FOR EACH COMPARABLE:                                                 │
│        → comparable_workflow.run_comparable_analysis()                      │
│        → Uses: core/photo_clustering, core/room_analysis, etc.              │
│        → Saves to: comparable_photo_clusters, comparable_room_analyses, etc.│
│                                                                             │
│     c) RUN BRACKET ANALYSIS:                                                │
│        → bracket_analysis.run_bracket_analysis()                            │
│        → Uses: gap_analysis, scope_builder, kg_pricing, timeline, visuals   │
│        → Saves to: listing_bracket_analyses                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. DISPLAY RESULTS                                                         │
│     → THE MATH: asking + renovation_cost = total_investment vs target       │
│     → BEFORE/AFTER: slider with generated visualization                     │
│     → SCOPE OF WORK: categorized line items with prices                     │
│     → TIMELINE: phased schedule                                             │
│     → VIEWING CHECKLIST: items to verify in person                          │
│     → COMPARABLES: cards showing the "very good" properties used            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Tables Summary

### Target Listing Tables (existing)
- `listings` - Property metadata
- `listing_photos` - Individual photos
- `photo_clusters` - P1 clustering results
- `room_analyses` - P3 room analysis
- `room_rule_verifications` - Rules per room
- `room_uniclass_assessments` - Elements per room
- `whole_property_analysis` - P2 8-lens

### Comparable Tables (new - migration applied)
- `listing_comparables` - Comparable metadata + photo_urls
- `comparable_photos` - Individual photos (populated during analysis)
- `comparable_photo_clusters` - P1 clustering results
- `comparable_room_analyses` - P3 room analysis
- `comparable_rule_verifications` - Rules per room
- `comparable_uniclass_assessments` - Elements per room
- `comparable_whole_property_analysis` - P2 8-lens

### Market Data Tables (existing)
- `listing_market_stats` - Price thresholds from Casafari

### Output Tables (existing)
- `listing_bracket_analyses` - Final bracket analysis results

---

## API Endpoints

### Existing
- `POST /api/renovation/{listing_id}/comparables` - Fetch from Casafari
- `GET /api/renovation/{listing_id}/comparables` - Get saved comparables
- `GET /api/renovation/{listing_id}/market-stats` - Get price thresholds

### New (to implement)
- `POST /api/renovation/{listing_id}/analyze-bracket`
  - Body: `{ "bracket": "fair_market", "force_reanalysis": false }`
  - Runs comparable analysis + bracket analysis
  - Returns: BracketAnalysis result

- `POST /api/renovation/{listing_id}/comparable/{comparable_id}/analyze`
  - Runs full analysis on a single comparable
  - For manual/debugging purposes

- `POST /api/renovation/{listing_id}/add-comparable`
  - Body: `{ "source_listing_id": 123, "price_bucket": "fair_market" }`
  - Converts a scraped listing to a comparable
  - Copies all data including photos

---

## File Structure

```
Lean MVP/backend/pipeline/
├── core/                           # Layer 1: Pure AI functions
│   ├── __init__.py
│   ├── photo_clustering.py
│   ├── room_analysis.py
│   ├── rule_verification.py
│   ├── uniclass_assessment.py
│   └── property_analysis.py
│
├── workflows/                      # Layer 2: Entity-specific DB handling
│   ├── __init__.py
│   ├── listing_workflow.py
│   └── comparable_workflow.py
│
├── bracket_analysis/               # Layer 3: Shared bracket flow
│   ├── __init__.py
│   ├── gap_analysis.py
│   ├── scope_builder.py
│   ├── kg_pricing.py
│   ├── timeline.py
│   ├── visuals.py
│   └── orchestrator.py
│
├── steps/                          # Legacy (to be migrated)
│   ├── photo_analysis.py          # → core/ + workflows/
│   ├── verify_rules.py            # → core/rule_verification.py
│   ├── assess_uniclass.py         # → core/uniclass_assessment.py
│   └── analyze_comparables.py     # → workflows/comparable_workflow.py
│
└── ...
```

---

## Migration Plan

1. **Phase 1**: Create `core/` with extracted pure functions (no DB calls)
2. **Phase 2**: Create `workflows/` that use core functions + handle DB
3. **Phase 3**: Create `bracket_analysis/` orchestrator
4. **Phase 4**: Update routes to use new structure
5. **Phase 5**: Deprecate `steps/` once everything works

---

---

## Layer 4: Output Packaging

**Location**: `Lean MVP/backend/pipeline/output/`

After bracket analysis completes, results are packaged for two audiences:

### Files

```
output/
├── __init__.py
├── user_package.py          # Format for UI display
├── architect_export.py      # Detailed PDF for professionals
└── templates/
    ├── architect_report.html    # PDF template
    └── scope_summary.html       # Condensed scope template
```

### 4A: User Package (UI Display)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER PACKAGE                                        │
│                                                                             │
│  Optimized for: Quick understanding, decision-making, sharing               │
│  Format: JSON API response → React components                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  THE MATH (Hero Section)                                                    │
│  ───────────────────────                                                    │
│  • asking_price: €375,000                                                   │
│  • renovation_cost: €62,400                                                 │
│  • total_investment: €437,400                                               │
│  • target_value: €485,000                                                   │
│  • potential_margin: €47,600 ✅                                             │
│  • margin_percentage: 10.9%                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  BEFORE/AFTER (Visual Impact)                                               │
│  ─────────────────────────────                                              │
│  • before_photo_url: Original listing photo                                 │
│  • after_photo_url: AI-generated renovation render                          │
│  • slider_default_position: 50%                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SCOPE OF WORK (Grouped by Category)                                        │
│  ───────────────────────────────────                                        │
│  Categories with totals:                                                    │
│  • ELECTRICAL: €8,200                                                       │
│  • PLUMBING: €6,800                                                         │
│  • FINISHES: €18,400                                                        │
│  • ENVELOPE: €12,000                                                        │
│  • PERMITS: €4,200                                                          │
│  • DEMOLITION: €3,800                                                       │
│                                                                             │
│  Each category has:                                                         │
│  • items: List of work items (human-readable descriptions)                  │
│  • subtotal: Category total                                                 │
│  • icon: Category icon for UI                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  TIMELINE (Visual Gantt)                                                    │
│  ───────────────────────                                                    │
│  • total_weeks: "6-8 weeks"                                                 │
│  • phases: [                                                                │
│      { name: "Demolition & Prep", weeks: "1-2", color: "#..." },           │
│      { name: "Electrical & Plumbing", weeks: "2-4", color: "#..." },       │
│      { name: "Finishes", weeks: "4-6", color: "#..." },                    │
│      { name: "Final Touches", weeks: "6-8", color: "#..." }                │
│    ]                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  COMPARABLES (Evidence Cards)                                               │
│  ────────────────────────────                                               │
│  3-9 cards showing "very good" properties that justify target price:        │
│  • thumbnail: First photo                                                   │
│  • price: €485,000                                                          │
│  • sqm: 130m²                                                               │
│  • price_per_sqm: €3,731/m²                                                │
│  • distance: 1.2km                                                          │
│  • condition_label: "Muy buen estado"                                       │
│  • key_features: ["Reformado 2020", "Cocina nueva", ...]                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  VIEWING CHECKLIST (Actionable)                                             │
│  ──────────────────────────────                                             │
│  Items to verify during physical viewing:                                   │
│  • □ Electrical panel - does it have modern breakers?                       │
│  • □ Water pressure - run multiple taps simultaneously                      │
│  • □ Windows - check for drafts, condensation                               │
│  • □ Walls - tap for hollow sounds (damp issues)                           │
│  • □ Floor levelness - place a ball, see if it rolls                       │
│                                                                             │
│  Each item linked to a gap finding with severity indicator                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  COMPLIANCE NOTES (Trust Building)                                          │
│  ─────────────────────────────────                                          │
│  • standards_met: ["Cédula de Habitabilidad", "REBT 2002", "CTE-DB-HE"]    │
│  • disclaimer: "Final certification requires architect sign-off"            │
│  • export_cta: "Download detailed specs for your architect"                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4B: Architect Export (PDF/Professional)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ARCHITECT EXPORT                                      │
│                                                                             │
│  Optimized for: Professional review, permit applications, contractor bids   │
│  Format: PDF (via HTML template → Puppeteer/WeasyPrint)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  COVER PAGE                                                                 │
│  ──────────                                                                 │
│  • Property address                                                         │
│  • Listing reference (Idealista URL)                                        │
│  • Report date                                                              │
│  • Bracket analyzed: "Fair Market Path → €485,000"                         │
│  • Generated by: Puedo Casa AI                                              │
│  • Disclaimer: "AI-assisted analysis - requires professional verification"  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 1: PROPERTY OVERVIEW                                               │
│  ────────────────────────────                                               │
│  • Address, cadastral reference (if available)                              │
│  • Built area: 130m², Plot area: 379m²                                     │
│  • Year built: 1975 (estimated from visual analysis)                        │
│  • Current condition score: 45/100 - "Necesita reforma integral"           │
│  • Target condition: "Muy buen estado" (comparable average)                 │
│  • Key photos with annotations                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 2: CONDITION ASSESSMENT BY ROOM                                    │
│  ───────────────────────────────────────                                    │
│  For each room cluster:                                                     │
│  • Room name & type                                                         │
│  • Photos analyzed                                                          │
│  • Condition score                                                          │
│  • Elements identified (Uniclass codes)                                     │
│  • Issues found (with photo evidence)                                       │
│  • Renovation needs                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 3: REGULATORY COMPLIANCE                                           │
│  ────────────────────────────────                                           │
│  For each Spanish building code checked:                                    │
│  • Rule ID & name                                                           │
│  • Status: ✅ Compliant / ⚠️ Uncertain / ❌ Non-compliant                  │
│  • Evidence: Photo + AI reasoning                                           │
│  • Required action (if non-compliant)                                       │
│  • Applicable standard reference                                            │
│                                                                             │
│  Codes covered:                                                             │
│  • Cédula de Habitabilidad (minimum habitability)                          │
│  • REBT 2002 (electrical safety)                                           │
│  • CTE-DB-HE (energy efficiency)                                           │
│  • CTE-DB-HS (health & hygiene)                                            │
│  • CTE-DB-SI (fire safety)                                                 │
│  • Accessibility requirements                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 4: DETAILED SCOPE OF WORK                                          │
│  ─────────────────────────────────                                          │
│  Full BOQ (Bill of Quantities) format:                                      │
│                                                                             │
│  | Item | Description | Uniclass | BCCA Code | Qty | Unit | €/Unit | Total │
│  |------|-------------|----------|-----------|-----|------|--------|-------|
│  | 1.1  | Demolición  | Ss_25_10 | BCCA-001  | 130 | m²   | 12.50  | 1,625 │
│  |      | pavimento   |          |           |     |      |        |       │
│  | 1.2  | Retirada    | Ss_25_10 | BCCA-002  | 1   | ud   | 450    | 450   │
│  |      | sanitarios  |          |           |     |      |        |       │
│  | ...  | ...         | ...      | ...       | ... | ...  | ...    | ...   │
│                                                                             │
│  Subtotals by trade:                                                        │
│  • Demolición: €3,800                                                       │
│  • Albañilería: €8,200                                                     │
│  • Electricidad: €8,200                                                     │
│  • Fontanería: €6,800                                                      │
│  • Carpintería: €4,500                                                     │
│  • Pintura: €3,200                                                         │
│  • Cerrajería: €2,400                                                      │
│                                                                             │
│  Cost breakdown:                                                            │
│  • PEM (Material Execution Budget): €53,400                                │
│  • GG 13% (General Expenses): €6,942                                       │
│  • BI 6% (Industrial Benefit): €3,204                                      │
│  • PEC (Contract Execution Budget): €63,546                                │
│  • IVA 21%: €13,345                                                        │
│  • TOTAL: €76,891                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 5: PERMITS REQUIRED                                                │
│  ───────────────────────────                                                │
│  • Permit type: Obra Menor / Obra Mayor / Comunicación Previa              │
│  • Issuing authority: Ayuntamiento de [city]                               │
│  • Estimated processing time                                                │
│  • Required documents checklist                                             │
│  • Approximate fees                                                         │
│  • Special considerations (heritage zone, etc.)                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 6: PROJECT TIMELINE                                                │
│  ───────────────────────────                                                │
│  Gantt chart with:                                                          │
│  • Phases and their dependencies                                            │
│  • Critical path highlighted                                                │
│  • Permit wait times factored in                                           │
│  • Milestone dates                                                          │
│                                                                             │
│  Phase breakdown:                                                           │
│  • Pre-construction: Permits, contractor selection (2-4 weeks)             │
│  • Phase 1: Demolition & structural (1-2 weeks)                            │
│  • Phase 2: MEP rough-in (2-3 weeks)                                       │
│  • Phase 3: Finishes (2-3 weeks)                                           │
│  • Phase 4: Punch list & inspection (1 week)                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTION 7: MARKET JUSTIFICATION                                            │
│  ───────────────────────────────                                            │
│  Evidence that target price is achievable:                                  │
│                                                                             │
│  Market statistics:                                                         │
│  • Average €/m² in area: €3,731                                            │
│  • Properties sold last 6 months: 23                                        │
│  • Average days on market: 45                                               │
│                                                                             │
│  Comparable properties analyzed:                                            │
│  • [Address 1]: €485,000 (130m²) - Condition analysis summary              │
│  • [Address 2]: €470,000 (125m²) - Condition analysis summary              │
│  • [Address 3]: €510,000 (140m²) - Condition analysis summary              │
│                                                                             │
│  Gap analysis summary:                                                      │
│  • Key differences from comparables                                         │
│  • How renovation addresses each gap                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  APPENDICES                                                                 │
│  ──────────                                                                 │
│  A. Full photo gallery with room labels                                     │
│  B. Uniclass element inventory                                              │
│  C. BCCA cost database excerpts (sources)                                  │
│  D. Comparable property detail sheets                                       │
│  E. AI model information & confidence scores                               │
│  F. Methodology notes                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FULL PIPELINE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │ USER ADDS    │
     │ LISTING      │
     └──────┬───────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: CORE AI FUNCTIONS                                                 │
│  ─────────────────────────                                                  │
│  • cluster_photos() ─────────────────────────────────────────────┐         │
│  • analyze_room()   ─────────────────────────────────────────────┤         │
│  • verify_rules()   ─────────────────────────────────────────────┤         │
│  • assess_uniclass()─────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
            │                                             │
            │                                             │
            ▼                                             ▼
┌───────────────────────────┐              ┌───────────────────────────┐
│  LAYER 2A: LISTING        │              │  LAYER 2B: COMPARABLE     │
│  WORKFLOW                 │              │  WORKFLOW                 │
│  ─────────────────        │              │  ─────────────────        │
│  Read: listing_photos     │              │  Read: listing_comparables│
│  Save: photo_clusters     │              │  Save: comparable_*       │
│        room_analyses      │              │        (all tables)       │
│        room_rule_*        │              │                           │
│        room_uniclass_*    │              │  Triggered: On bracket    │
│                           │              │  analysis request         │
│  Triggered: On listing    │              │                           │
│  creation or manually     │              │                           │
└───────────────────────────┘              └───────────────────────────┘
            │                                             │
            │                                             │
            └──────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: BRACKET ANALYSIS                                                  │
│  ─────────────────────────                                                  │
│  Input: Analyzed listing + Analyzed comparables for bracket                 │
│                                                                             │
│  Steps:                                                                     │
│  1. Gap Analysis ──────► What's different?                                  │
│  2. Scope Builder ─────► What work is needed?                               │
│  3. KG Pricing ────────► What does it cost?                                 │
│  4. Timeline ──────────► How long will it take?                             │
│  5. Visuals ───────────► What will it look like?                            │
│                                                                             │
│  Save: listing_bracket_analyses                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               │
            ┌──────────────────┴──────────────────────┐
            │                                         │
            ▼                                         ▼
┌───────────────────────────┐              ┌───────────────────────────┐
│  LAYER 4A: USER PACKAGE   │              │  LAYER 4B: ARCHITECT      │
│  ─────────────────────    │              │  EXPORT                   │
│                           │              │  ─────────────────        │
│  Format: JSON → React     │              │  Format: HTML → PDF       │
│                           │              │                           │
│  Contents:                │              │  Contents:                │
│  • The Math (hero)        │              │  • Cover page             │
│  • Before/After slider    │              │  • Property overview      │
│  • Scope by category      │              │  • Room-by-room assess.   │
│  • Timeline visual        │              │  • Regulatory compliance  │
│  • Comparable cards       │              │  • Full BOQ with codes    │
│  • Viewing checklist      │              │  • Permits required       │
│  • Compliance notes       │              │  • Detailed timeline      │
│                           │              │  • Market justification   │
│  Purpose: Decision-making │              │  • Appendices             │
│  Audience: Buyer          │              │                           │
│                           │              │  Purpose: Professional    │
│  ┌─────────────────────┐  │              │  review, permits, bids    │
│  │  "Share Analysis"   │  │              │  Audience: Architect,     │
│  │  "Get Financing"    │  │              │  contractor, bank         │
│  └─────────────────────┘  │              │                           │
│                           │              │  ┌─────────────────────┐  │
│                           │              │  │  "Download PDF"     │  │
│                           │              │  │  "Send to Architect"│  │
│                           │              │  └─────────────────────┘  │
└───────────────────────────┘              └───────────────────────────┘
```

---

## Notes

- **Thumbnails Issue**: Casafari only provides 350px thumbnails. For full photos, either:
  - Scrape Casafari property pages (extra API calls)
  - Manual comparable scraping provides full photos (preferred)
  
- **Reusability**: Core functions work identically for listings and comparables
  
- **Testing**: Each layer can be tested independently:
  - Core: Unit tests with mock photos
  - Workflows: Integration tests with test DB
  - Bracket: End-to-end tests with full flow

---

## Methodology Cross-References

> **CRITICAL**: This document defines CODE STRUCTURE. The detailed METHODOLOGY lives in `MARKET_COMPARISON_ARCHITECTURE.md`. Always consult both documents when implementing.

### Where to Find Detailed Methodology

| When Implementing... | MARKET_COMPARISON Section | Status |
|---------------------|---------------------------|--------|
| **Gap Analysis** | "Gap Analysis Logic" - ONE Gemini call, qualitative | ✅ |
| **Before/After Renders** | "Before/After Photo Generation" - Lock camera + positions | ✅ |
| **Rules Engine** | "The Logic Flow" - 4-step process | ✅ |
| **KG Pricing** | "KG Estimator Pipeline" - 7 steps | ✅ |
| **Timeline Estimation** | "Typical Renovation Phases" - Input to Gemini | ✅ |
| **Energy Assessment** | "CTE-Grounded Energy Assessment" | ✅ |
| **Gemini Response Schema** | "Response Schema" | ✅ |
| **Architect Handover** | "Architect Handover Export" | ✅ |
| **User Package Format** | "Simplified JSON Response for UI" | ✅ |
| **ComparablesCard UI** | "Comparables Card V2" | ✅ |

### Key Principles

1. **Gap Analysis = ONE Gemini Call, Qualitative**
   - ONE Gemini 3 Pro Preview call
   - Send: Target listing (all rooms) + 1-3 comparables (all rooms) together
   - Gemini makes qualitative judgment about what upgrades matter
   - Benefits from seeing everything together → coherent house-level view
   - No magic numbers, no deterministic formulas

---

## Casafari API Strategy: 2-Call Pattern

> **Problem**: Comparables API only returns 350px thumbnails, which are too small for analysis.  
> **Solution**: Chain two API calls to get full-size photos.

### The 2-Call Pattern

```
┌──────────────────────────────────────────────────────────────────┐
│  CALL 1: Comparables Search                                      │
│  POST /v1/comparables/search                                     │
│  → Returns: property info + primary_listing_id for each comp     │
│  → Up to 50 comparables per call                                 │
│  → thumbnails[] = 350px (IGNORE THESE)                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  CALL 2: Bulk Listings Fetch                                     │
│  POST /v1/listings/search                                        │
│  Body: {                                                         │
│    "listing_ids": [id1, id2, id3...],                           │
│    "search_operations": ["sale", "sold"]                         │
│  }                                                               │
│  → Returns: FULL pictures[] for ALL comparables in ONE call      │
│  → Up to 100 listing_ids per call                                │
└──────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# Lean MVP/backend/pipeline/casafari_client.py

async def fetch_comparables_with_full_photos(
    coordinates: dict,
    distance_km: float,
    property_type: str,
    bedrooms: int,
    total_area: int,
    comparables_count: int = 20
) -> dict:
    """
    Fetch comparables with full-size photos in exactly 2 API calls.
    
    Returns:
        {
            "results": [...],      # Comparables with pictures[] added
            "statistics": {...},
            "estimated_prices": {...}
        }
    """
    
    # CALL 1: Comparables search
    comparables_response = await casafari_post("/v1/comparables/search", {
        "comparables_count": comparables_count,
        "location_boundary": {
            "circle": {
                "coordinates": coordinates,
                "distance": distance_km
            }
        },
        "operation": "sale",
        "comparables_types": [property_type],
        "bedrooms": bedrooms,
        "total_area": total_area,
        "sold_or_rented_after": "2024-01-01"  # Last ~18 months
    })
    
    results = comparables_response.get("results", [])
    if not results:
        return comparables_response
    
    # Extract listing IDs for bulk photo fetch
    listing_ids = [r["primary_listing_id"] for r in results]
    
    # CALL 2: Bulk listings fetch (gets full pictures[])
    listings_response = await casafari_post("/v1/listings/search", {
        "listing_ids": listing_ids,
        "search_operations": ["sale", "sold", "sale_hold"]
    })
    
    # Build lookup: listing_id -> pictures[]
    photos_map = {
        listing["listing_id"]: listing.get("pictures", [])
        for listing in listings_response.get("results", [])
    }
    
    # Merge full photos into comparables
    for comp in results:
        lid = comp["primary_listing_id"]
        comp["pictures"] = photos_map.get(lid, [])
        # Keep thumbnails as fallback, but prefer pictures
        comp["photo_urls"] = comp["pictures"] or comp.get("thumbnails", [])
    
    return comparables_response
```

### What We Get Per Comparable

From Comparables API:
- `property_id`, `primary_listing_id`
- `coordinates`, `address`, `zip_code`
- `total_area`, `bedrooms`, `bathrooms`, `condition`
- `sale_price`, `sale_status`, `sold_at`
- `thumbnails[]` (350px - ignore)
- `listing_urls[]` (original site URLs - fallback for scraping)

From Listings API (merged in):
- `pictures[]` (FULL SIZE photos from original source)
- `listing_url` (original listing URL)
- `description` (full text)

### API Call Budget

| Scenario | Comparables | API Calls |
|----------|-------------|-----------|
| Single bracket analysis | 1-3 | 2 |
| All 3 brackets | 3-9 | 2 |
| Full comparable fetch | Up to 50 | 2 |

**Always 2 calls** regardless of comparable count (up to 50 comps / 100 listing IDs).

### Fallback: Original URL Scraping

If Listings API fails or photos missing, use `listing_urls[]` from Comparables:

```python
# listing_urls contains original portal URLs
# e.g., ["https://www.idealista.com/inmueble/12345678/"]

# Can scrape these with existing scraper if needed
```

---

## TEMPORARY: Manual Comparable Selection (Until Casafari Paid)

> **Status**: Workaround for testing  
> **Remove when**: Casafari credits available

### Purpose

Allow using OTHER LISTINGS from the DB as "comparables" for testing, bypassing Casafari.

### UI Addition (ComparablesCard)

Add a collapsible section below the Casafari brackets:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MARKET COMPARABLES                                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [Casafari brackets - existing UI]                                          │
│  ...                                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  🧪 MANUAL COMPARABLE (Testing Only)                            [▼ Expand]  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Select another listing from the DB to use as a comparable:                 │
│                                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                        │
│  │ [photo] │  │ [photo] │  │ [photo] │  │ [photo] │                        │
│  │ Listing │  │ Listing │  │ Listing │  │ Listing │                        │
│  │ #7      │  │ #8      │  │ #12     │  │ #15     │                        │
│  │ €485k   │  │ €520k   │  │ €445k   │  │ €510k   │                        │
│  │ 3bd/2ba │  │ 3bd/2ba │  │ 3bd/1ba │  │ 4bd/2ba │                        │
│  │[Analyse]│  │[Analyse]│  │[Analyse]│  │[Analyse]│                        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘                        │
│                                                                             │
│  ⚠️ This uses a DB listing as a single comparable. For testing only.       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
NORMAL FLOW (Casafari):
1. User clicks [Analyse] on bracket
2. Get comparables from: listing_comparables WHERE price_bucket = bracket
3. Run analysis with those comparables

MANUAL FLOW (Testing):
1. User clicks [Analyse] on a listing card
2. Get that listing from: listings WHERE id = selected_id
3. Run analysis with that ONE listing as the comparable
4. Flag: source = "manual_listing" (not "casafari")
```

### API Changes

```python
# New endpoint for manual comparable
POST /api/renovation/{listing_id}/analyze-with-listing
Body: {
    "comparable_listing_id": 7,   # The other listing to use as comparable
    "target_price": 485000        # What price we're targeting (their price)
}

Response: Same as normal bracket analysis, but:
- comparable_source: "manual_listing"
- comparable_listing_ids: [7]
```

### Pipeline Awareness

The bracket analysis flow needs to know the source:

```python
async def run_bracket_analysis(
    db: PipelineDB,
    listing_id: int,
    bracket: str = None,                    # For Casafari flow
    comparable_source: str = "casafari",    # "casafari" | "manual_listing"
    manual_comparable_ids: List[int] = None # For manual flow
) -> BracketAnalysisResult:
    
    if comparable_source == "casafari":
        # Normal flow - get from listing_comparables
        comparables = await get_comparables_for_bracket(db, listing_id, bracket)
        # Each comparable has: rule_verifications, uniclass_assessments from comparable_* tables
        
    elif comparable_source == "manual_listing":
        # Manual flow - get from listings table
        # The "comparable" is actually a fully analyzed listing
        comparables = await get_listings_as_comparables(db, manual_comparable_ids)
        # Each comparable has: rule_verifications, uniclass_assessments from listing_* tables
        
    # Rest of pipeline is identical
    gap_result = await run_gap_analysis(listing, comparables)
    # ...
```

### What Stays the Same

- Gap analysis Gemini call (same input format)
- Scope building
- KG pricing
- Timeline estimation
- After-image rendering

Only the **data source** changes - whether we read from `listing_comparables` or `listings`.

### Database Query Difference

```python
# CASAFARI COMPARABLE
async def get_comparable_analysis(db, comparable_id: int):
    # Read from comparable_* tables
    return {
        "photo_clusters": await db.get("comparable_photo_clusters", comparable_id),
        "room_analyses": await db.get("comparable_room_analyses", comparable_id),
        "rule_verifications": await db.get("comparable_rule_verifications", comparable_id),
        "uniclass_assessments": await db.get("comparable_uniclass_assessments", comparable_id),
    }

# MANUAL LISTING AS COMPARABLE
async def get_listing_as_comparable(db, listing_id: int):
    # Read from listing_* tables (same as target listing)
    return {
        "photo_clusters": await db.get("photo_clusters", listing_id),
        "room_analyses": await db.get("room_analyses", listing_id),
        "rule_verifications": await db.get("room_rule_verifications", listing_id),
        "uniclass_assessments": await db.get("room_uniclass_assessments", listing_id),
    }
```

### Removal Plan

When Casafari is available:
1. Delete the "Manual Comparable" UI section from ComparablesCard
2. Delete the `/analyze-with-listing` endpoint
3. Remove the `manual_listing` branch from `run_bracket_analysis`

---

2. **Render Constraints = Simple**
   - Lock: Camera angle (must match original)
   - Lock: Structural POSITIONS (walls, doors, windows stay in place)
   - You CAN upgrade/replace elements, just don't move them
   - Instruction: "Render [room] with [bracket] finishes"

3. **Spanish Pricing Structure**:
   ```
   PEM (Presupuesto Ejecución Material)
   + GG 13% (Gastos Generales)
   + BI 6% (Beneficio Industrial)
   = PEC (Presupuesto Ejecución Contrata)
   + IVA 21%
   = TOTAL
   ```

4. **CTE Climate Zones**:
   - Format: `[Winter][Summer]` e.g., "B3" = Winter zone B, Summer zone 3
   - U-value limits vary by zone

5. **Timeline**:
   - Phase templates as INPUT to Gemini
   - Gemini estimates based on actual scope complexity

---

## Implementation Plan: Code Audit & Build Order

**Date**: 2026-01-08
**Status**: Ready to Build

### Existing Code Audit

#### ✅ USE AS-IS (No Changes Required)

| File | Function | What It Does | Status |
|------|----------|--------------|--------|
| `gemini_client.py` | `call_gemini()`, `call_gemini_image()`, `call_gemini_json()`, `fetch_images_batch()` | All Gemini API interactions | **WORKS** |
| `kg_estimator.py` | `price_scope_items()` | BCCA + KG pricing | **WORKS** |
| `rules_engine_v2.json` | - | Spanish building code rules | **DATA** |
| `prompts/*.py` | All prompts | Rule/Uniclass/Condition prompts | **WORKS** |
| `estimate_timeline.py` | `estimate_timeline()` | Timeline estimation from scope | **WORKS** |
| `gap_analysis.py` | `run_gap_analysis()` | Gap identification | **WORKS** |
| `scope_builder.py` | `build_scope()` | Scope item generation | **WORKS** |
| `visuals.py` | `run_v4_render()` | After-image generation | **WORKS** |

#### 🔧 MINOR ADDITIONS (No Refactoring - Add Entry Points Only)

| File | Current State | Change Needed |
|------|---------------|---------------|
| `photo_analysis.py` | `run_p1_clustering()` works perfectly | **ADD** `cluster_photos_direct(photo_urls)` - ~15 lines, same Gemini logic, skips DB read |
| `verify_rules.py` | `verify_rules_for_room(cluster, year, rules)` | **NO CHANGE** - already takes any cluster |
| `assess_uniclass.py` | `assess_room_uniclass(cluster)` | **NO CHANGE** - already takes any cluster |
| `analyze_comparables.py` | `analyze_comparable_photos(comp, rules, year)` | **NO CHANGE** - already works with ComparableProperty |

**Key Principle**: The existing code is pristine. We don't touch it. We just add a second entry point for comparables that bypasses the listing_id lookup and goes straight to the Gemini call.

#### 🆕 BUILD NEW (Bracket Analysis Workflow)

| What | Purpose | Based On |
|------|---------|----------|
| **Bracket Analysis Orchestrator** | Run full analysis on bracket comparables | Combines existing functions |
| **Comparable Full Workflow** | P1 → Rules → Uniclass → Room Analysis for each comp | Reuses existing core functions |

### Final Directory Structure

```
Lean MVP/backend/pipeline/
├── gemini_client.py                 # ✅ NO CHANGE - all Gemini calls
├── gap_analysis.py                  # ✅ NO CHANGE - gap identification  
├── scope_builder.py                 # ✅ NO CHANGE - scope generation
├── rules_engine_v2.json             # ✅ NO CHANGE - building codes
├── db_helpers.py                    # ✅ NO CHANGE - database operations
├── orchestrator.py                  # 🔧 LIGHT EDIT - add bracket workflow trigger
│
├── steps/                           # ✅ EXISTING - All Steps Work
│   ├── photo_analysis.py            # 🔧 ADD cluster_photos_direct() - 15 lines
│   ├── verify_rules.py              # ✅ NO CHANGE - already takes any cluster
│   ├── assess_uniclass.py           # ✅ NO CHANGE - already takes any cluster
│   ├── analyze_room.py              # ✅ NO CHANGE
│   ├── analyze_comparables.py       # 🔧 LIGHT EDIT - add full analysis trigger
│   ├── estimate_timeline.py         # ✅ NO CHANGE
│   ├── visuals.py                   # ✅ NO CHANGE
│   └── ...other steps...
│
├── workflows/                       # 🆕 NEW FOLDER - Orchestration
│   ├── __init__.py
│   └── comparable_workflow.py       # Orchestrates: cluster → rules → uniclass for comps
│
├── bracket/                         # 🆕 NEW FOLDER - Bracket Analysis
│   ├── __init__.py
│   └── bracket_analysis.py          # Orchestrate: comps → gap → scope → price → timeline → render
│
├── pricing/                         # ✅ EXISTING
│   ├── __init__.py
│   └── kg_estimator.py              # ✅ NO CHANGE
│
└── prompts/                         # ✅ EXISTING
    ├── condition_assessment_v2.py   # ✅ NO CHANGE
    ├── rule_verification.py         # ✅ NO CHANGE
    ├── uniclass_assessment.py       # ✅ NO CHANGE
    └── scope_mapper_v2.py           # ✅ NO CHANGE
```

**Note**: No `core/` folder needed. Existing step functions already work with any cluster input. We just add one thin entry point (`cluster_photos_direct`) that bypasses the DB lookup.

### Exact Code Changes

#### 1. ADD to `photo_analysis.py` (~15 lines)

```python
async def cluster_photos_direct(
    photo_urls: List[str], 
    listing_context: str = "",
    property_flags: List[str] = None
) -> Dict[str, Any]:
    """
    Same zero-shot clustering, but takes URLs directly.
    For use with comparables where we already have photo_urls.
    
    The existing run_p1_clustering() remains UNTOUCHED for listings.
    """
    prompt = get_p1_clustering_prompt(listing_context, len(photo_urls), property_flags)
    images = await fetch_images_batch(photo_urls)
    result = await call_gemini_json(prompt=prompt, images=images, model="pro")
    return result  # Caller handles DB save
```

#### 2. NEW: `workflows/comparable_workflow.py` (~80 lines)

```python
async def analyze_comparable_full(
    db: PipelineDB,
    comparable_id: int,
    photo_urls: List[str],
    year_built: int = 2000
) -> Dict[str, Any]:
    """Run full analysis on a comparable - same as listing pipeline."""
    # Step 1: cluster_photos_direct(photo_urls) - uses existing Gemini logic
    # Step 2: For each cluster:
    #         - verify_rules_for_room(cluster, year, rules) - EXISTING, works as-is
    #         - assess_room_uniclass(cluster) - EXISTING, works as-is
    # Step 3: Save results to comparable_* tables
    # Returns: analysis summary
```

#### 3. NEW: `bracket/bracket_analysis.py` (~120 lines)

```python
async def run_bracket_analysis(
    db: PipelineDB,
    listing_id: int,
    bracket: str,  # "fast_sell" | "fair_market" | "out_of_market"
    use_filtered: bool = False
) -> BracketAnalysisResult:
    """Full bracket analysis workflow."""
    # Step 1: Get comparables for this bracket
    # Step 2: analyze_comparable_full() for each (can parallelize)
    # Step 3: run_gap_analysis(listing, comparables) - EXISTING
    # Step 4: build_scope(gap_analysis) - EXISTING
    # Step 5: price_scope_items(scope) - EXISTING
    # Step 6: estimate_timeline(scope, pricing) - EXISTING
    # Step 7: Generate after-image - EXISTING
    # Step 8: Save to listing_bracket_analyses
```

### Lines of Code Summary

| Component | Lines | Change Type |
|-----------|-------|-------------|
| `photo_analysis.py` | 615 | ✅ UNTOUCHED + 15 new lines |
| `verify_rules.py` | 299 | ✅ NO CHANGE |
| `assess_uniclass.py` | 283 | ✅ NO CHANGE |
| `gap_analysis.py` | 522 | ✅ NO CHANGE |
| `scope_builder.py` | 689 | ✅ NO CHANGE |
| `estimate_timeline.py` | 402 | ✅ NO CHANGE |
| `kg_estimator.py` | 505 | ✅ NO CHANGE |
| `gemini_client.py` | 464 | ✅ NO CHANGE |
| All prompts | ~900 | ✅ NO CHANGE |
| **TOTAL UNTOUCHED** | **~4,700 lines** | |
| **NEW CODE** | **~215 lines** | |

### Build Order (Summary)

See **BUILD PHASES** section below for full implementation details.

---

## BUILD PHASES (Complete Implementation Guide)

### PRE-PHASE 0: Scraper Data Flow Fix (COMPLETED)

> **Issue**: Listings saved without photos, bathrooms, and other scraped data.  
> **Root Cause**: Frontend wasn't passing `photo_urls` fallback and backend `_build_scraped_data` didn't include photos.  
> **Status**: ✅ FIXED

**Files Changed:**

1. **`Lean MVP/frontend/src/app/page.tsx`**
   - Added `photo_urls` fallback: `scrapedData.image_urls || scrapedData.photo_urls || []`
   - Now sends `scraped_data` to preserve all fields
   - Added debug logging

2. **`Lean MVP/backend/database.py`**
   - `_build_scraped_data()` now includes `image_urls` and `photo_urls`
   - Ensures photos are preserved in scraped_data JSONB

**Test Result:**
```
Photos saved: ✅
scraped_data.bathrooms: ✅
scraped_data.image_urls: ✅
```

---

### Current State Audit

| Component | Status | Notes |
|-----------|--------|-------|
| Photo Clustering (P1) | ✅ Working | For listings only |
| Room Analysis (P3) | ✅ Working | For listings only |
| Rule Verification | ✅ Working | Spanish building codes |
| Uniclass Assessment | ✅ Working | Element identification |
| Scope Builder | ✅ Working | Builds from analysis |
| KG Pricing | ✅ Working | BCCA database |
| Timeline Estimator | ✅ Working | Gemini-powered |
| After Image Generation | ✅ Working | Gemini pro-image inline |
| Bracket Analysis Endpoint | ✅ Working | Full pipeline runs |
| ComparablesCard UI | ✅ Working | Shows brackets, triggers analysis |
| BracketAnalysisModal | ✅ Working | Before/after slider, scope, etc |
| Casafari Full Photos | ❌ Missing | Only returns 350px thumbnails |
| Full Comparable Analysis | ❌ Missing | No clustering/room-analysis for comps |
| Qualitative Gap Analysis | ❌ Missing | Currently deterministic |
| Architect PDF Export | ❌ Missing | No export capability |

---

### PHASE 1: Data Quality (Critical Path)

**Goal**: Get usable photo data for comparables + enable testing without Casafari credits.

#### 1.1 Casafari 2-Call Integration

**File**: `Lean MVP/backend/clients/casafari_client.py`

```python
async def fetch_comparables_with_full_photos(
    coordinates: dict,
    distance_km: float,
    property_type: str,
    bedrooms: int,
    total_area: int,
    comparables_count: int = 20,
    condition: str = "very-good"
) -> dict:
    """
    Fetch comparables with full-size photos in exactly 2 API calls.
    
    CALL 1: /v1/comparables/search
      → Returns property info + primary_listing_id per comparable
      → thumbnails[] are 350px (ignore these)
      
    CALL 2: /v1/listings/search with listing_ids
      → Returns full pictures[] for all comparables in ONE call
      → Up to 100 listing_ids per call
    
    Returns: Standard comparables response with pictures[] merged in
    """
    # CALL 1: Comparables search
    comparables_response = await casafari_post("/v1/comparables/search", {
        "comparables_count": comparables_count,
        "location_boundary": {
            "circle": {
                "coordinates": coordinates,
                "distance": distance_km
            }
        },
        "operation": "sale",
        "comparables_types": [property_type],
        "bedrooms": bedrooms,
        "total_area": total_area,
        "condition": condition,
        "sold_or_rented_after": "2024-01-01"
    })
    
    results = comparables_response.get("results", [])
    if not results:
        return comparables_response
    
    # Extract listing IDs
    listing_ids = [r["primary_listing_id"] for r in results]
    
    # CALL 2: Bulk fetch full photos
    listings_response = await casafari_post("/v1/listings/search", {
        "listing_ids": listing_ids,
        "search_operations": ["sale", "sold", "sale_hold"]
    })
    
    # Build lookup: listing_id → pictures[]
    photos_map = {
        listing["listing_id"]: listing.get("pictures", [])
        for listing in listings_response.get("results", [])
    }
    
    # Merge full photos into comparables
    for comp in results:
        lid = comp["primary_listing_id"]
        comp["pictures"] = photos_map.get(lid, [])
        comp["photo_urls"] = comp["pictures"] or comp.get("thumbnails", [])
    
    return comparables_response
```

**Update**: `Lean MVP/backend/pipeline/steps/analyze_comparables.py`

```python
# Change line ~417 from:
result = await casafari.search_comparables(...)

# To:
result = await casafari.fetch_comparables_with_full_photos(
    coordinates={"latitude": lat, "longitude": lng},
    distance_km=distance_km,
    property_type=property_type,
    bedrooms=bedrooms,
    total_area=total_area,
    comparables_count=30,
    condition=condition
)
```

**Effort**: 1 hour

---

#### 1.2 Manual Comparable Selection (Temporary)

**Purpose**: Enable testing without Casafari credits by using other DB listings as comparables.

**File**: `Lean MVP/frontend/src/components/renovation/ComparablesCard.tsx`

Add collapsible section after Casafari brackets:

```tsx
// Add state
const [manualComps, setManualComps] = useState<Listing[]>([]);
const [showManual, setShowManual] = useState(false);

// Fetch other listings on mount
useEffect(() => {
  fetch(`/api/listings?exclude=${listingId}&limit=10`)
    .then(r => r.json())
    .then(data => setManualComps(data.listings || []));
}, [listingId]);

// Add UI section
{showManual && (
  <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
    <div className="flex items-center gap-2 mb-3">
      <span className="text-amber-600">🧪</span>
      <span className="font-medium text-amber-800">Manual Comparable (Testing Only)</span>
    </div>
    <p className="text-sm text-amber-700 mb-3">
      Select another listing from the DB to use as a comparable:
    </p>
    <div className="flex gap-3 overflow-x-auto pb-2">
      {manualComps.map(listing => (
        <div key={listing.id} className="flex-shrink-0 w-36 border rounded-lg p-2 bg-white">
          <img src={listing.photos?.[0]} className="w-full h-20 object-cover rounded" />
          <div className="text-xs mt-1">
            <div className="font-medium">#{listing.id}</div>
            <div className="text-gray-500">{formatPrice(listing.price)}</div>
            <div className="text-gray-400">{listing.bedrooms}bd/{listing.bathrooms}ba</div>
          </div>
          <button 
            onClick={() => handleManualAnalyse(listing.id)}
            className="mt-2 w-full px-2 py-1 bg-amber-500 text-white text-xs rounded hover:bg-amber-600"
          >
            Analyse
          </button>
        </div>
      ))}
    </div>
  </div>
)}
```

**File**: `Lean MVP/backend/routes/renovation.py`

Add endpoint:

```python
class ManualAnalyseRequest(BaseModel):
    comparable_listing_id: int
    target_price: int

@router.post("/{listing_id}/comparables/analyse-with-listing", response_model=AnalyseResponse)
async def analyse_with_manual_listing(listing_id: int, request: ManualAnalyseRequest):
    """
    Run bracket analysis using another DB listing as the comparable.
    
    TEMPORARY: For testing until Casafari credits available.
    This uses listing_* tables (not comparable_* tables) for the "comparable".
    """
    # Get target listing analysis
    listing = await db.get_listing(listing_id)
    listing_analysis = await get_listing_full_analysis(db, listing_id)
    
    # Get "comparable" listing (it's actually another listing in our DB)
    comp_listing = await db.get_listing(request.comparable_listing_id)
    comp_analysis = await get_listing_full_analysis(db, request.comparable_listing_id)
    
    # Run gap analysis with this single comparable
    gap_result = await run_gap_analysis_gemini(
        listing_analysis=listing_analysis,
        comparable_analyses=[comp_analysis],
        bracket="manual"
    )
    
    # Rest of pipeline is identical to normal bracket analysis
    scope_items = build_scope_from_gap_analysis(gap_result)
    pricing_result = await price_scope_items(scope_items, floor_area)
    timeline_result = await estimate_timeline(scope_items, pricing_result)
    # ... generate after image, save to DB, return response
```

**Effort**: 1.5 hours

---

### PHASE 2: Analysis Quality

**Goal**: Run full analysis on comparables (same as listings) and make gap analysis qualitative.

#### 2.1 Full Comparable Analysis Workflow

**File**: `Lean MVP/backend/pipeline/steps/photo_analysis.py`

Add direct entry point (15 lines):

```python
async def cluster_photos_direct(
    photo_urls: List[str],
    listing_context: str = "",
    property_flags: List[str] = None
) -> Dict[str, Any]:
    """
    Same zero-shot clustering, but takes URLs directly.
    For use with comparables where we already have photo_urls.
    
    EXISTING run_p1_clustering() remains UNTOUCHED for listings.
    """
    prompt = get_p1_clustering_prompt(listing_context, len(photo_urls), property_flags)
    images = await fetch_images_batch(photo_urls)
    result = await call_gemini_json(prompt=prompt, images=images, model="pro")
    return result  # Caller handles DB save
```

**File**: `Lean MVP/backend/pipeline/workflows/comparable_workflow.py` (NEW)

```python
"""
Comparable Analysis Workflow
============================

Run full analysis pipeline on a comparable property.
Same steps as listing pipeline, different DB tables.
"""

import logging
from typing import Dict, Any, List
from ..db_helpers import PipelineDB
from ..steps.photo_analysis import cluster_photos_direct
from ..steps.verify_rules import verify_rules_for_room, load_rules_engine
from ..steps.assess_uniclass import assess_room_uniclass
from ..steps.analyze_room import analyze_room_condition

logger = logging.getLogger(__name__)


async def analyze_comparable_full(
    db: PipelineDB,
    comparable_id: int,
    photo_urls: List[str],
    property_context: str = "",
    year_built: int = 2000
) -> Dict[str, Any]:
    """
    Run full analysis on a comparable - same as listing pipeline.
    
    Steps:
    1. cluster_photos_direct() - Zero-shot room clustering
    2. For each cluster:
       - analyze_room_condition() - Condition scoring
       - verify_rules_for_room() - Spanish building codes
       - assess_room_uniclass() - Element identification
    3. Save results to comparable_* tables
    
    Returns:
        {
            "comparable_id": int,
            "clusters": [...],
            "room_analyses": [...],
            "rule_verifications": [...],
            "uniclass_assessments": [...],
            "summary": {...}
        }
    """
    logger.info(f"🔍 Analyzing comparable {comparable_id} ({len(photo_urls)} photos)")
    
    # Step 1: Cluster photos
    clustering = await cluster_photos_direct(
        photo_urls=photo_urls,
        listing_context=property_context
    )
    
    clusters = clustering.get("clusters", [])
    logger.info(f"  📸 Found {len(clusters)} room clusters")
    
    # Save clusters
    await save_comparable_clusters(db, comparable_id, clusters)
    
    # Step 2: Analyze each cluster
    rules_engine = load_rules_engine()
    room_analyses = []
    rule_verifications = []
    uniclass_assessments = []
    
    for cluster in clusters:
        room_type = cluster.get("room_type", "general")
        room_name = cluster.get("room_name", room_type)
        cluster_photos = [photo_urls[i] for i in cluster.get("photo_indices", [])]
        
        if not cluster_photos:
            continue
        
        # Build mock cluster for existing functions
        mock_cluster = {
            "cluster_id": f"comp_{comparable_id}_{room_name}",
            "room_type": room_type,
            "room_name": room_name,
            "photo_urls": cluster_photos
        }
        
        # Room condition analysis
        try:
            condition = await analyze_room_condition(mock_cluster)
            room_analyses.append({
                "room_name": room_name,
                "room_type": room_type,
                **condition
            })
        except Exception as e:
            logger.warning(f"  ⚠️ Room analysis failed for {room_name}: {e}")
        
        # Rule verification
        try:
            rules = await verify_rules_for_room(
                cluster=mock_cluster,
                year_built=year_built,
                year_source="assumption",
                rules_engine=rules_engine
            )
            rule_verifications.append({
                "room_name": room_name,
                "room_type": room_type,
                "verifications": rules.get("rule_verifications", [])
            })
        except Exception as e:
            logger.warning(f"  ⚠️ Rule verification failed for {room_name}: {e}")
        
        # Uniclass assessment
        try:
            uniclass = await assess_room_uniclass(cluster=mock_cluster)
            uniclass_assessments.append({
                "room_name": room_name,
                "room_type": room_type,
                "systems": uniclass.get("systems", []),
                "products": uniclass.get("products", [])
            })
        except Exception as e:
            logger.warning(f"  ⚠️ Uniclass assessment failed for {room_name}: {e}")
    
    # Save all results
    await save_comparable_room_analyses(db, comparable_id, room_analyses)
    await save_comparable_rule_verifications(db, comparable_id, rule_verifications)
    await save_comparable_uniclass_assessments(db, comparable_id, uniclass_assessments)
    
    logger.info(f"  ✅ Comparable {comparable_id} analysis complete")
    
    return {
        "comparable_id": comparable_id,
        "clusters": clusters,
        "room_analyses": room_analyses,
        "rule_verifications": rule_verifications,
        "uniclass_assessments": uniclass_assessments,
        "summary": {
            "rooms_analyzed": len(room_analyses),
            "rules_checked": sum(len(r.get("verifications", [])) for r in rule_verifications),
            "elements_identified": sum(
                len(u.get("systems", [])) + len(u.get("products", []))
                for u in uniclass_assessments
            )
        }
    }


# Database helpers (save to comparable_* tables)
async def save_comparable_clusters(db: PipelineDB, comparable_id: int, clusters: List[Dict]):
    # Save to comparable_photo_clusters table
    pass

async def save_comparable_room_analyses(db: PipelineDB, comparable_id: int, analyses: List[Dict]):
    # Save to comparable_room_analyses table
    pass

async def save_comparable_rule_verifications(db: PipelineDB, comparable_id: int, verifications: List[Dict]):
    # Save to comparable_rule_verifications table
    pass

async def save_comparable_uniclass_assessments(db: PipelineDB, comparable_id: int, assessments: List[Dict]):
    # Save to comparable_uniclass_assessments table
    pass
```

**Effort**: 2 hours

---

#### 2.2 Qualitative Gap Analysis (Gemini)

**File**: `Lean MVP/backend/pipeline/gap_analysis.py`

Replace deterministic logic with ONE Gemini call:

```python
"""
Gap Analysis - Qualitative Gemini Approach
==========================================

ONE Gemini call that receives:
- ALL listing room analyses (clusters, conditions, rules, uniclass)
- ALL comparable room analyses (same structure)

Returns qualitative gap assessment - no magic thresholds.
"""

async def run_gap_analysis_gemini(
    listing_analysis: Dict[str, Any],
    comparable_analyses: List[Dict[str, Any]],
    bracket: str
) -> Dict[str, Any]:
    """
    Qualitative gap analysis using Gemini 3 Pro Preview.
    
    Sends ALL rooms from listing + ALL rooms from comparables in ONE call.
    Gemini makes qualitative judgment about what upgrades matter.
    Benefits from seeing everything together → coherent house-level view.
    
    Args:
        listing_analysis: Full analysis of target listing
            {clusters, room_analyses, rule_verifications, uniclass_assessments}
        comparable_analyses: List of full analyses for comparables
            Each has same structure as listing_analysis
        bracket: "fast_sell" | "fair_market" | "premium"
    
    Returns:
        {
            "gaps": [...],           # List of identified gaps
            "priority_upgrades": [...],  # What to fix first
            "viewing_checklist": [...],  # Items to verify in person
            "renovation_strategy": str   # Overall approach summary
        }
    """
    from .gemini_client import call_gemini_json
    
    prompt = f"""You are a Spanish renovation expert comparing a target property to {len(comparable_analyses)} "very good" condition comparable properties.

TARGET LISTING ANALYSIS:
{json.dumps(listing_analysis, indent=2)}

COMPARABLE PROPERTIES ({len(comparable_analyses)} total):
{json.dumps(comparable_analyses, indent=2)}

BRACKET: {bracket}
- fast_sell: Minimal fixes for quick sale
- fair_market: Match "very good" condition standard
- premium: Exceed market standard

TASK: Analyze the GAP between the target listing and the comparables.

For each room type that exists in BOTH the listing and comparables, identify:
1. What the comparables have that the listing lacks
2. What condition differences exist (finishes, fixtures, systems)
3. What the listing needs to reach comparable standard

Return JSON:
{{
    "gaps": [
        {{
            "room_type": "kitchen",
            "listing_condition": "Brief description of listing kitchen",
            "comparable_standard": "What comparables' kitchens have",
            "gap_description": "What's missing/different",
            "upgrade_needed": "Specific upgrade to close the gap",
            "priority": "high" | "medium" | "low",
            "bracket_relevance": {{
                "fast_sell": true/false,
                "fair_market": true/false,
                "premium": true/false
            }}
        }}
    ],
    "priority_upgrades": [
        "Ordered list of most important upgrades"
    ],
    "viewing_checklist": [
        {{
            "item": "What to check during viewing",
            "check": "How to verify",
            "priority": "high" | "medium" | "low"
        }}
    ],
    "renovation_strategy": "2-3 sentence summary of overall approach for this bracket"
}}

Be qualitative - don't use arbitrary thresholds. Use your expertise to judge what matters for a {bracket} renovation."""

    result = await call_gemini_json(prompt=prompt, model="pro")
    return result
```

**Update** `renovation.py` to use new gap analysis:

```python
# Replace lines ~1139-1148 with:
from pipeline.gap_analysis import run_gap_analysis_gemini

# Get full listing analysis
listing_analysis = {
    "room_analyses": room_analyses_from_db,
    "rule_verifications": rule_verifications,
    "uniclass_assessments": uniclass_assessments
}

# Get comparable analyses (from comparable_* tables)
comparable_analyses = await get_comparable_analyses_for_bracket(db, listing_id, bracket)

gap_analysis = await run_gap_analysis_gemini(
    listing_analysis=listing_analysis,
    comparable_analyses=comparable_analyses,
    bracket=request.bracket
)

viewing_checklist = gap_analysis.get("viewing_checklist", [])
```

**Effort**: 1.5 hours

---

### PHASE 3: User Deliverables

**Goal**: Enable users to export/share analysis results.

#### 3.1 Architect PDF Export

**File**: `Lean MVP/backend/pipeline/export/pdf_generator.py` (NEW)

```python
"""
Architect PDF Export
====================

Generate professional PDF report for architect handoff.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image, Spacer
from io import BytesIO
import base64


async def generate_architect_pdf(
    analysis: Dict[str, Any],
    listing: Dict[str, Any]
) -> bytes:
    """
    Generate PDF report for architect export.
    
    Sections:
    1. Property Summary (address, price, area, photos)
    2. Gap Analysis Findings (what needs work)
    3. Scope of Work (all line items with quantities)
    4. Timeline Phases (Gantt-style)
    5. Before/After Visualization
    6. Compliance Notes (CTE, RITE, etc.)
    7. Cost Summary (PEM breakdown)
    
    Returns: PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # 1. Header
    elements.append(Paragraph(f"Renovation Analysis Report", styles['Title']))
    elements.append(Paragraph(f"Property: {listing.get('address', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # 2. Property Summary
    elements.append(Paragraph("Property Summary", styles['Heading2']))
    summary_data = [
        ["Asking Price", f"€{analysis['asking_price']:,}"],
        ["Target Price", f"€{analysis['target_price']:,}"],
        ["Built Area", f"{listing.get('m2_built', '?')} m²"],
        ["Bedrooms", str(listing.get('bedrooms', '?'))],
        ["Bathrooms", str(listing.get('bathrooms', '?'))],
    ]
    elements.append(Table(summary_data))
    elements.append(Spacer(1, 20))
    
    # 3. Gap Analysis
    elements.append(Paragraph("Gap Analysis", styles['Heading2']))
    for gap in analysis.get('gap_analysis', {}).get('gaps', []):
        elements.append(Paragraph(
            f"• <b>{gap['room_type']}</b>: {gap['gap_description']}", 
            styles['Normal']
        ))
    elements.append(Spacer(1, 20))
    
    # 4. Scope of Work
    elements.append(Paragraph("Scope of Work", styles['Heading2']))
    scope = analysis.get('scope_of_work', {})
    for category in scope.get('categories', []):
        elements.append(Paragraph(f"<b>{category['name']}</b> - €{category['total']:,}", styles['Normal']))
        for item in category.get('items', []):
            elements.append(Paragraph(f"  • {item}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # 5. Timeline
    elements.append(Paragraph("Timeline", styles['Heading2']))
    timeline = analysis.get('timeline', {})
    elements.append(Paragraph(
        f"Estimated Duration: {timeline.get('total_weeks_min', '?')}-{timeline.get('total_weeks_max', '?')} weeks",
        styles['Normal']
    ))
    for phase in timeline.get('phases', []):
        elements.append(Paragraph(
            f"• Week {phase['week_start']}-{phase['week_end']}: {phase['name']}",
            styles['Normal']
        ))
    elements.append(Spacer(1, 20))
    
    # 6. Cost Summary
    elements.append(Paragraph("Cost Summary", styles['Heading2']))
    pricing = scope.get('pricing', {})
    cost_data = [
        ["PEM (Materials + Labor)", f"€{pricing.get('pem', 0):,}"],
        ["Overhead (13%)", f"€{pricing.get('overhead_13pct', 0):,}"],
        ["Profit (6%)", f"€{pricing.get('profit_6pct', 0):,}"],
        ["Subtotal", f"€{pricing.get('subtotal', 0):,}"],
        ["IVA (21%)", f"€{pricing.get('iva_21pct', 0):,}"],
        ["TOTAL", f"€{pricing.get('total_with_iva', 0):,}"],
    ]
    elements.append(Table(cost_data))
    elements.append(Spacer(1, 20))
    
    # 7. Compliance Notes
    elements.append(Paragraph("Compliance Notes", styles['Heading2']))
    compliance = analysis.get('compliance_notes', {})
    for standard in compliance.get('standards', []):
        elements.append(Paragraph(f"• {standard}", styles['Normal']))
    elements.append(Paragraph(compliance.get('note', ''), styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
```

**File**: `Lean MVP/backend/routes/renovation.py`

Add export endpoint:

```python
from fastapi.responses import StreamingResponse
from pipeline.export.pdf_generator import generate_architect_pdf

@router.get("/{listing_id}/comparables/analyses/{bracket}/export-pdf")
async def export_architect_pdf(listing_id: int, bracket: str):
    """Export bracket analysis as PDF for architect handoff."""
    # Get analysis from DB
    analysis = await get_bracket_analysis(db, listing_id, bracket)
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    
    # Get listing data
    listing = await db.get_listing(listing_id)
    
    # Generate PDF
    pdf_bytes = await generate_architect_pdf(analysis, listing)
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=renovation-{listing_id}-{bracket}.pdf"
        }
    )
```

**File**: `Lean MVP/frontend/src/components/renovation/BracketAnalysisModal.tsx`

Add export button:

```tsx
<button
  onClick={() => window.open(`/api/renovation/${listingId}/comparables/analyses/${bracket}/export-pdf`)}
  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
>
  <Download className="w-4 h-4" />
  Export for Architect
</button>
```

**Effort**: 2 hours

---

### Build Summary

| Phase | Task | Effort | Priority |
|-------|------|--------|----------|
| **Phase 1** | Casafari 2-call integration | 1 hr | Critical |
| **Phase 1** | Manual comparable UI (temp) | 1.5 hr | Critical |
| **Phase 2** | Full comparable analysis workflow | 2 hr | High |
| **Phase 2** | Qualitative gap analysis (Gemini) | 1.5 hr | High |
| **Phase 3** | Architect PDF export | 2 hr | Medium |
| **TOTAL** | | **8 hours** | |

### Code Impact Summary

| Component | Lines | Change Type |
|-----------|-------|-------------|
| `casafari_client.py` | +50 | 2-call function |
| `photo_analysis.py` | +15 | Entry point |
| `comparable_workflow.py` | +120 | NEW file |
| `gap_analysis.py` | +80 | Rewrite core function |
| `pdf_generator.py` | +150 | NEW file |
| `renovation.py` | +60 | New endpoints |
| `ComparablesCard.tsx` | +50 | Temp UI |
| `BracketAnalysisModal.tsx` | +10 | Export button |
| **TOTAL NEW** | **~535 lines** | |
| **EXISTING UNTOUCHED** | **~4,700 lines** | |

