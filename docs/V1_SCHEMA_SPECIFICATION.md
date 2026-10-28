Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V1.0 Schema Specification
## Complete Data Model for 8-Phase Pipeline

**Status:** Finalized  
**Date:** January 2026  
**Migration:** `011_v1_pipeline_schema.sql`

---

## Overview

This document specifies ALL data schemas for the V1.0 8-phase pipeline:
1. **Gemini Schemas** — JSON structures for LLM input/output
2. **Database Schemas** — PostgreSQL tables for persistence
3. **Item Evolution** — How items transform through phases

---

## Part 1: Item Schema Evolution

Items evolve as they flow through phases. Each phase ADDS fields; none are removed.

### Phase 1: SCOPE_BOQ_ITEM

```typescript
interface ScopeBoqItem {
  // Identity
  item_id: string;          // "ITEM_001"
  room_id: string;          // From canonical room list or "general"
  room_name: string;        // Human readable
  
  // Description
  name: string;             // Spanish task name
  description: string;      // Detailed description
  system: "demolition" | "plumbing" | "electrical" | "finishes" | "hvac" | "carpentry" | "ffe" | "logistics";
  
  // BCCA Reference
  bcca_code: string;        // "09ACE00145"
  bcca_description: string;
  
  // FFE (if applicable)
  ffe_code?: string;
  ffe_install_bcca?: string;
  
  // Quantities
  unit: string;             // "m2", "ud", "ml"
  quantity: number;
  quantity_formula: string; // "6.3m × 4.0m = 25.2m²"
  
  // Schedule
  phase_week: number;       // 1-10+
  depends_on: string[];     // Item IDs
  duration_hours?: number;
  
  // Context
  comparable_reference?: string;
  energy_impact?: string;
}
```

**Required fields:** `item_id`, `room_id`, `name`, `bcca_code`, `unit`, `quantity`, `phase_week`

### Phase 2: PRICED_ITEM (Code adds these)

```typescript
interface PricedItem extends ScopeBoqItem {
  // Pricing (added by code lookup)
  unit_price: number;       // From BCCA database
  ffe_price?: number;       // FFE item cost
  ffe_install_price?: number;
  line_total: number;       // quantity × unit_price + FFE
  price_source: "BCCA" | "FFE" | "NOT_FOUND";
}
```

**New required fields:** `unit_price`, `line_total`

### Phase 3: ADJUSTED_ITEM (LLM adds these)

```typescript
interface AdjustedItem extends PricedItem {
  // Adjustments
  price_multiplier?: number;    // Regional adjustment (e.g., 1.15)
  adjusted_price: number;       // line_total × multiplier
  adjustment_reason?: string;   // "Barcelona centro +15%"
}
```

**New required fields:** `adjusted_price`

---

## Part 2: Phase Output Schemas

### Phase 1: Scope + BoQ

```typescript
interface Phase1Output {
  items: ScopeBoqItem[];
  rooms_coverage: Array<{
    room_id: string;
    item_count: number;
  }>;
  total_weeks: number;
  critical_path: string[];     // Item IDs
  energy_improvements_included: string[];
  reasoning_notes: string[];
  total_items: number;
}
```

### Phase 3: Peer Review

```typescript
interface Phase3Output {
  items: AdjustedItem[];       // COMPLETE array with adjustments
  
  // Changes made
  items_added: string[];
  items_added_reasoning: string[];
  items_removed: string[];
  items_removed_reasoning: string[];
  sequencing_fixes: Array<{
    item_id: string;
    old_week?: number;
    new_week: number;
    reason: string;
  }>;
  regional_adjustments: Array<{
    factor: string;
    percentage: number;
    reason: string;
  }>;
  
  // Totals
  pem_subtotal: number;
  overhead_13pct: number;
  profit_6pct: number;
  iva_21pct: number;
  final_total_with_iva: number;
  cost_per_sqm: number;
  cost_per_sqm_assessment: string;
  
  // Energy
  energy_compliance: {
    current_rating: string;
    target_rating: string;
    improvement_letters: number;
    measures_included: string[];
    pathway_valid: boolean;
  };
  
  // Quality
  confidence_score: number;    // 1-100
  sanity_check_passed: boolean;
  risk_flags: Array<{
    flag: string;
    severity: string;
    mitigation?: string;
  }>;
  recommendations: string[];
  review_notes: string[];
}
```

### Phase 4: Rendering Prompts

```typescript
interface Phase4Output {
  room_prompts: Array<{
    room_id: string;
    room_name: string;
    photo_index?: number;
    transformation_prompt: string;  // MUST include boilerplate
    key_changes: string[];
    preserve_elements?: string[];
    style_reference?: string;
  }>;
  hero_room_id: string;
  hero_room_reason?: string;
  overall_style: string;
  color_palette: string[];
}
```

### Phase 6: Viewing Checklist

```typescript
interface Phase6Output {
  address: string;
  total_duration_minutes: number;
  mode1_sensory: Array<{
    id: string;
    action: string;
    detail?: string;
    why?: string;
  }>;
  mode2_inspect: Array<{
    room_id: string;
    room_name?: string;
    checks: string[];
  }>;
  mode3_ask: Array<{
    id: string;
    question: string;
    context?: string;
  }>;
}
```

### Phase 7: ELI5 Summaries

```typescript
interface Phase7Output {
  property_summary: {
    address: string;
    total_cost: number;
    total_weeks: number;
    rooms_count?: number;
  };
  energy_eli5: {
    current_rating: string;
    target_rating: string;
    improvement_letters: number;
    explanation: string;           // Plain language with analogy
    main_improvements: string[];
    expected_savings?: string;
  };
  rooms: Array<{
    room_id: string;
    room_name: string;
    eli5_summary: string;          // 2-3 sentences
    cost: number;
    cost_percentage?: number;
    weeks?: string;                // "3-6"
    key_changes_eli5: string[];    // Bullets with emojis
    why_this_matters?: string;
    what_stays?: string;
  }>;
  general_items_eli5: {
    eli5_summary: string;
    cost: number;
    key_items: string[];
  };
  timeline_eli5: {
    total_weeks: number;
    explanation: string;
    critical_waits?: string[];
  };
}
```

### Phase 8: Architect Report

```typescript
interface Phase8Output {
  document_header: {
    title: string;
    subtitle?: string;
    bracket_label?: string;
    reference: string;
    date: string;
    version?: string;
  };
  executive_summary: {
    asking_price?: number;
    renovation_cost: number;
    total_investment: number;
    target_price?: number;
    potential_margin?: number;
    weeks_range?: { min: number; max: number };
    line_items_count: number;
    rooms_count?: number;
  };
  cost_breakdown: {
    pem: number;
    overhead_13pct?: number;
    profit_6pct?: number;
    subtotal?: number;
    iva_21pct?: number;
    total_with_iva: number;
  };
  by_trade: Array<{
    trade_code: string;           // BCCA chapter code
    trade_name: string;
    subtotal: number;
    items: Array<{
      item_id: string;
      bcca_code: string;
      description: string;
      room_id?: string;
      quantity: number;
      unit: string;
      unit_price?: number;
      line_total: number;
    }>;
  }>;
  by_room?: Array<{
    room_id: string;
    room_name?: string;
    items_count?: number;
    subtotal: number;
    percentage?: number;
  }>;
  timeline?: {
    total_weeks: { min: number; max: number };
    phases: Array<{
      name: string;
      week_start: number;
      week_end: number;
      trades?: string[];
      tasks?: string[];
    }>;
    milestones?: Array<{
      week: number;
      description: string;
    }>;
    critical_path?: string[];
  };
  energy_compliance?: {
    current_rating: string;
    target_rating: string;
    improvement_letters: number;
    climate_zone?: string;
    meets_cte_db_he?: boolean;
    measures?: Array<{
      improvement: string;
      impact?: string;
      included_in_scope: boolean;
    }>;
  };
  compliance_notes?: {
    standards?: string[];
    permits_required?: string[];
    note?: string;
  };
  risk_flags?: Array<{
    flag: string;
    severity: string;
    mitigation?: string;
  }>;
  recommendations?: Array<{
    recommendation: string;
    priority?: string;
  }>;
  confidence_score: number;
  sanity_check_passed?: boolean;
}
```

---

## Part 3: Smart M² Schema

### Enhanced Schema (V1.0)

```typescript
interface SmartM2Data {
  rooms: Array<{
    cluster_name: string;
    cluster_id: string;
    estimated_m2: number;
    
    // NEW: Dimensions
    estimated_dimensions: {
      length_m: number;
      width_m: number;
      aspect_ratio: "square" | "rectangular" | "elongated" | "narrow";
      dimension_confidence: "high" | "medium" | "low";
    };
    
    // NEW: Named walls
    wall_descriptions: Array<{
      name: "long_wall" | "short_wall" | "window_wall" | "entrance_wall" | "back_wall" | "countertop_wall" | "appliance_wall";
      name_es: string;       // "pared larga", "pared con ventana"
      length_m: number;
      features: string[];    // ["windows", "door", "countertop"]
    }>;
    
    estimated_height_m: number;
    perimeter_m: number;     // 2 × (length + width)
    wall_area_m2: number;    // perimeter × height
    
    confidence: "high" | "medium" | "low";
    reasoning: string;
  }>;
  
  circulation_and_walls_m2: number;
  total_check: number;       // Must equal listings.sqm
  dimension_methodology: string;
}
```

---

## Part 4: Database Tables

### smart_m2 (Enhanced)

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| listing_id | BIGINT | FK to listings |
| rooms | JSONB | Enhanced room data with dimensions |
| circulation_and_walls_m2 | NUMERIC | Shared space |
| total_check | NUMERIC | Validation sum |
| dimension_methodology | TEXT | How dimensions calculated |
| schema_version | TEXT | "v1.0" for enhanced |
| model_used | TEXT | Gemini model |
| created_at | TIMESTAMPTZ | |

### unified_estimates_v1

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| listing_id | BIGINT | FK to listings |
| package_type | TEXT | fast_sell/fair_market/out_of_market |
| phase_1_scope_boq | JSONB | Phase 1 output |
| phase_2_priced_items | JSONB | Phase 2 output |
| phase_3_peer_review | JSONB | Phase 3 output |
| phase_4_rendering_prompts | JSONB | Phase 4 output |
| phase_5_generated_images | JSONB | Phase 5 output |
| phase_6_viewing_checklist | JSONB | Phase 6 output |
| phase_7_eli5_summaries | JSONB | Phase 7 output |
| phase_8_architect_report | JSONB | Phase 8 output |
| total_cost | DECIMAL | Summary |
| cost_per_sqm | DECIMAL | Summary |
| total_weeks | INTEGER | Summary |
| rooms_count | INTEGER | Summary |
| line_items_count | INTEGER | Summary |
| pem_subtotal | DECIMAL | Cost breakdown |
| overhead_13pct | DECIMAL | Cost breakdown |
| profit_6pct | DECIMAL | Cost breakdown |
| iva_21pct | DECIMAL | Cost breakdown |
| final_total_with_iva | DECIMAL | Final cost |
| confidence_score | INTEGER | 1-100 |
| sanity_check_passed | BOOLEAN | Quality flag |
| energy_current_rating | TEXT | E.g., "G" |
| energy_target_rating | TEXT | E.g., "D" |
| energy_improvement_letters | INTEGER | E.g., 3 |
| energy_pathway_valid | BOOLEAN | |
| risk_flags | JSONB | |
| recommendations | JSONB | |
| phase_times | JSONB | Duration tracking |
| phases_completed | INTEGER | 0-8 |
| model_version | TEXT | "V1.0" |
| pipeline_version | TEXT | "8-phase" |
| generated_at | TIMESTAMPTZ | |

### viewing_checklists_v1

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| listing_id | BIGINT | FK to listings |
| package_type | TEXT | |
| address | TEXT | |
| total_duration_minutes | INTEGER | ~20 |
| mode1_sensory | JSONB | First impressions |
| mode2_inspect | JSONB | Room checks |
| mode3_ask | JSONB | Agent questions |
| generated_at | TIMESTAMPTZ | |

### eli5_summaries_v1

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| listing_id | BIGINT | FK to listings |
| package_type | TEXT | |
| property_summary | JSONB | |
| energy_eli5 | JSONB | |
| rooms | JSONB | Per-room summaries |
| general_items_eli5 | JSONB | |
| timeline_eli5 | JSONB | |
| total_cost | DECIMAL | For display |
| total_weeks | INTEGER | For display |
| rooms_count | INTEGER | For display |
| generated_at | TIMESTAMPTZ | |

### architect_reports_v1

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| listing_id | BIGINT | FK to listings |
| package_type | TEXT | |
| document_header | JSONB | |
| executive_summary | JSONB | |
| cost_breakdown | JSONB | |
| by_trade | JSONB | Items by BCCA chapter |
| by_room | JSONB | Costs by room |
| timeline | JSONB | |
| energy_compliance | JSONB | |
| compliance_notes | JSONB | |
| risk_flags | JSONB | |
| recommendations | JSONB | |
| confidence_score | INTEGER | |
| sanity_check_passed | BOOLEAN | |
| generated_at | TIMESTAMPTZ | |

---

## Part 5: Checkpoint Values

### V1.0 Checkpoints

| Checkpoint | Description |
|------------|-------------|
| `smart_m2_complete` | M1 with dimensions |
| `phase_1_scope_boq_complete` | Phase 1 done |
| `phase_2_pricing_complete` | Phase 2 done (code) |
| `phase_3_peer_review_complete` | Phase 3 done |
| `phase_4_prompts_complete` | Phase 4 done |
| `phase_5_images_complete` | Phase 5 done (Gemini Flash Image) |
| `phase_6_checklist_complete` | Phase 6 done |
| `phase_7_eli5_complete` | Phase 7 done |
| `phase_8_report_complete` | Phase 8 done |
| `v1_pipeline_complete` | All phases done |

### Legacy Checkpoints (Kept for Backward Compat)

| Checkpoint | Description |
|------------|-------------|
| `clustering_complete` | P1 photo clusters |
| `year_estimation_complete` | Year lookup |
| `images_cached` | Comparables cached |
| `pir_target_complete` | Target PIR |
| `pir_comparables_complete` | Comparable PIRs |
| `bracket_pirs_synthesized` | Bracket PIRs |
| `strategic_reasoning_complete` | Pre-scope reasoning |
| `estimate_fast_sell_complete` | Package done |
| `estimate_fair_market_complete` | Package done |
| `estimate_out_of_market_complete` | Package done |
| `visuals_complete` | Images generated |
| `viewing_guide_complete` | Checklist done |

---

## Part 6: Migration Checklist

### Pre-Migration

- [ ] Backup existing `smart_m2` data
- [ ] Verify no active pipeline runs

### Migration Steps

1. [ ] Run `011_v1_pipeline_schema.sql`
2. [ ] Verify new tables created:
   - [ ] `unified_estimates_v1`
   - [ ] `viewing_checklists_v1`
   - [ ] `eli5_summaries_v1`
   - [ ] `architect_reports_v1`
3. [ ] Verify `smart_m2` columns added:
   - [ ] `dimension_methodology`
   - [ ] `schema_version`
4. [ ] Verify checkpoint constraint updated
5. [ ] Test helper functions:
   - [ ] `get_v1_estimate()`
   - [ ] `is_v1_pipeline_complete()`

### Post-Migration

- [ ] Update `db_helpers.py` with new save/get methods
- [ ] Update `package_orchestrator.py` to use V1 tables
- [ ] Test full pipeline with real listing

---

**Document Version:** 1.0.0
