# V0.5 Renovation Pipeline - Discrete Output Architecture

## Overview

This is the complete renovation estimation pipeline. It takes a listing URL and produces:
- Property Intelligence Reports (PIRs) 
- Bracket PIRs (synthesized from comparables)
- 10-phase renovation estimates with DISCRETE OUTPUT schemas
- AI-generated after images
- Viewing guides

## V0.5 Key Changes

### Discrete Output Architecture
Each phase has its OWN output schema with only the fields it's responsible for:

| Phase | Schema | Fields Output | Can Output Prices? |
|-------|--------|---------------|-------------------|
| 1-2 | SCOPE_ITEM_SCHEMA | identity, scope | ❌ NO |
| 3-4 | SCHEDULED_ITEM_SCHEMA | + scheduling | ❌ NO |
| 5 | PRICED_ITEM_SCHEMA | + pricing | ✅ YES (from index) |
| 6 | ADJUSTED_ITEM_SCHEMA | + adjustments | ✅ YES |

**Why this matters:** Phases 1-4 literally CANNOT hallucinate prices because the output schema doesn't include pricing fields.

### Cumulative Context
Each phase receives ALL items from previous phases (cumulative), but only OUTPUTS the fields in its schema (discrete).

### ALL PHASES USE PRO MODEL
No more flash for "simpler" phases. All phases use `gemini-2.5-pro` with `thinking_level="HIGH"`.

### Bracket PIR Architecture
Instead of abstract quality tiers (budget/mid/luxury), V0.5 uses **Bracket PIRs**:
- Comparables are assigned to brackets by price percentiles
- A representative PIR is SYNTHESIZED from comparable PIRs in each bracket
- Scope decisions are driven by observable features in the bracket PIR

### NO FALLBACKS
The ONLY fallback in the system is for Gemini rate limits. All data fallbacks are removed:
- If bracket has <2 comparables → `DataMissingError` (FAIL)
- If room has <minimum items → `AntiParetoViolation` (FAIL)
- If items are lost between phases → `SchemaContinuityError` (FAIL)

## Architecture

```
URL Input
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. LOAD & FILTER                                                        │
│    - Load listing from database                                         │
│    - Load comparables (filter to 10+ photos)                           │
│    - Validate photo availability                                        │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. CLUSTERING (no_fallback=True)                                        │
│    - Cluster target photos by room (Gemini Pro - FAIL if unavailable)  │
│    - Cluster comparable photos by room (parallel)                      │
│    - Store canonical room_ids (single source of truth)                 │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. IMAGE CACHING                                                        │
│    - Download comparable images to Supabase Storage                    │
│    - Update cluster photo_urls with cached URLs                        │
│    - Ensures reliable access during PIR generation                     │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. PIR GENERATION (Parallel)                                            │
│    - Target PIR: Full analysis (triggers, regulatory, design)          │
│    - Comparable PIRs: Design/finish focus                              │
│    - Canonical room_ids enforced in all PIRs                          │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. BRACKET PIR SYNTHESIS (V0.5 NEW)                                     │
│    - Assign comparables to brackets by price percentiles               │
│    - Synthesize representative PIR per bracket (NOT averaging)         │
│    - FAIL FAST if <2 comparables per bracket                          │
│    - Save to database for checkpoint resume                            │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. ESTIMATION (per package, parallel)                                   │
│    Package types: fast_sell, fair_market, out_of_market               │
│                                                                         │
│    SCHEMA CONTINUITY PHASES:                                           │
│    Phase 1: Scope Definition (Pro)    → Creates items with scope fields│
│    Phase 2: Scope Check (Flash)       → Can ADD items, validates       │
│         → Anti-Pareto validation (min items per room)                  │
│    Phase 3: Scheduling (Pro)          → Fills scheduling fields        │
│    Phase 4: Logistics Check (Flash)   → Can ADD logistics items        │
│    Phase 5: Pricing (Pro)             → Fills pricing fields           │
│         → validate_pricing_complete() (FAIL if missing prices)         │
│    Phase 6: Adjustments (Pro)         → Fills adjustment fields        │
│                                                                         │
│    VALIDATION PHASES:                                                   │
│    Phase 7: Timeline Validation (Flash)                                │
│    Phase 8: Energy Check (Flash)                                       │
│    Phase 9: Final Sanity (Pro)                                         │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. VISUAL GENERATION                                                    │
│    Phase 10: Rendering Prompts (Pro)   - Transformation descriptions   │
│    Image Gen: Gemini Pro (parallel)    - Before → After images         │
│    Storage: Supabase Storage           - Permanent URLs                │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. VIEWING GUIDE                                                        │
│    Phase 11: Viewing Guide (Flash)     - 20-minute checklist           │
│    - Mode 1: Sensory (0-5 min)                                         │
│    - Mode 2: Inspect (5-15 min)                                        │
│    - Mode 3: Ask Agent (15-20 min)                                     │
└─────────────────────────────────────────────────────────────────────────┘
    ↓
Complete Estimate (stored in unified_estimates with v05_schema_continuity=true)
```

## Key Files

| File | Purpose |
|------|---------|
| `package_orchestrator.py` | Main pipeline orchestration with bracket PIR synthesis |
| `pir_generator.py` | Property Intelligence Reports + `generate_bracket_pir()` |
| `multi_phase_estimator.py` | Schema continuity estimation engine |
| `image_cache.py` | Comparable image caching |
| `phase_prompts.py` | V0.5 prompts enforcing schema continuity |
| `schemas/gemini_schemas.py` | Phase-specific schemas (SCOPE, SCHEDULED, PRICED, ADJUSTED) |
| `schemas/phase_outputs.py` | FAIL FAST validation functions |

## V0.5 Validation Functions

| Function | Purpose |
|----------|---------|
| `validate_items_preserved()` | Items cannot be lost between phases |
| `validate_pricing_complete()` | All items must have prices after Phase 5 |
| `validate_room_coverage()` | All canonical rooms must have items |
| `validate_anti_pareto()` | Minimum items per room type enforced |

## V0.5 Exceptions (FAIL FAST)

| Exception | When Raised |
|-----------|-------------|
| `SchemaContinuityError` | Items lost between phases |
| `PricingIncompleteError` | Items missing prices after Phase 5 |
| `RoomCoverageError` | Canonical room not covered |
| `AntiParetoViolation` | Room has fewer than minimum items |
| `DataMissingError` | Bracket has <2 comparables |

## Database Tables

| Table | Purpose |
|-------|---------|
| `listings` | Source property data |
| `listing_comparables` | Comparable properties |
| `photo_clusters_v048` | Target room clusters |
| `comparable_photo_clusters` | Comparable room clusters |
| `comparable_image_cache` | Cached Supabase URLs |
| `property_intelligence_reports_v048` | PIR storage (target, comparable, bracket_*) |
| `unified_estimates_v048` | Complete estimates with v05_schema_continuity flag |
| `viewing_guides_v048` | Viewing checklists |
| `package_generation_progress` | Checkpoints |

Note: Table names include `v048` for historical reasons but support both V0.4.8 and V0.5 data via `model_version` column.

## Checkpoints

The pipeline saves progress after each major step:
1. `clustering_complete`
2. `year_estimation_complete`
3. `images_cached`
4. `pir_target_complete`
5. `pir_comparables_complete`
6. `bracket_pirs_synthesized` (V0.5 NEW)
7. `estimate_fast_sell_complete`
8. `estimate_fair_market_complete`
9. `estimate_out_of_market_complete`
10. `visuals_complete`
11. `viewing_guide_complete`

Resume from any checkpoint: `from_checkpoint="clustering_complete"`

## Minimum Requirements

| Item | Requirement |
|------|-------------|
| Target photos | 10+ images, 3+ rooms |
| Comparable photos | 10+ images |
| Comparables per bracket | 2+ (NO FALLBACK) |
| Items per bathroom | 15+ |
| Items per kitchen | 20+ |
| Items per bedroom | 8+ |
| Items per living room | 10+ |

## Usage

```python
from pricing.package_orchestrator import PackageOrchestrator
from database import Database

db = Database()
orchestrator = PackageOrchestrator(db=db)

result = await orchestrator.generate_packages(
    listing_id=12,
    force_restart=True  # Ignore checkpoints, run fresh
)

# V0.5 output includes bracket_pirs
print(f"Packages: {list(result['packages'].keys())}")
print(f"Bracket PIRs: {list(result['bracket_pirs'].keys())}")

# Each package has v05_schema_continuity=True
for pkg_name, pkg in result['packages'].items():
    print(f"{pkg_name}: {pkg['line_items_count']} items, €{pkg['final_total_with_iva']:,.2f}")
```
