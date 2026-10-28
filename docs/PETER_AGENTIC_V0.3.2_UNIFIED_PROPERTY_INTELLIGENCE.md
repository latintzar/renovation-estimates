Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.3.2: Unified Property Intelligence

> **Date**: January 2026  
> **Author**: Peter Neyra + Claude  
> **Status**: ✅ IMPLEMENTED  
> **Parent**: V0.3.1 (Knowledge Integration) → V0.3 (Hybrid Architecture)

## Implementation Summary (January 10, 2026)

All phases completed:

| Phase | Status | Files Created |
|-------|--------|---------------|
| Interior Design KB | ✅ | `standards/interior_design_knowledge.json` (113KB) |
| PIR Schema | ✅ | `pipeline/schemas/property_intelligence.py` |
| PIR Generator | ✅ | `pipeline/steps/property_intelligence.py` |
| Gap Analysis Schema | ✅ | `pipeline/schemas/gap_analysis.py` |
| Gap Analysis Generator | ✅ | `pipeline/steps/comparative_gap_analysis.py` |
| Pipeline Orchestrator | ✅ | `pipeline/v032_orchestrator.py` |
| Database Migration | ✅ | `supabase/migrations/007_property_intelligence_reports.sql` |
| TypeScript Types | ✅ | `frontend/src/types/property-intelligence.ts` |
| UI Components | ✅ | `frontend/src/components/renovation/PropertyIntelligenceCard.tsx`, `GapAnalysisCard.tsx` |
| API Routes | ✅ | `frontend/src/app/api/renovation/[id]/v032-analysis/route.ts`, `backend/routes/renovation.py` |

---

## What This Extension Adds

**V0.3** established: Hybrid KG + BCCA RAG architecture  
**V0.3.1** added: Energy + Process knowledge bases  
**V0.3.2** adds: Unified property analysis replacing fragmented pipeline

### The Problem Being Solved

Current pipeline has **3 separate Gemini calls per property**:
- `assess_uniclass.py` - "What's visible?" (Systems, Products)
- `verify_rules.py` - "Behind the walls?" (Age-based rules)
- `gap_analysis.py` - "What's the delta?" (Comparison)

**Problems:**
1. Each call misses context from the others
2. Seeing a crack doesn't simultaneously inform Uniclass, rules, AND energy
3. Multiple API calls = slower, costlier
4. Gap analysis re-reads everything instead of using pre-computed

### The Solution

**2-Stage Architecture:**
1. **Property Intelligence Report** - One comprehensive call per property
2. **Comparative Gap Analysis** - One call comparing pre-computed reports

---

## New Knowledge Base: Interior Design

**Similar to V0.3.1's energy/process extraction, we need design vocabulary.**

### Why We Need This

Without standardized vocabulary, Gemini might say:
- "Nice kitchen" vs "Modern kitchen" vs "Updated kitchen"
- Inconsistent, not comparable, not actionable

With interior_design_knowledge.json:
- "Contemporary style, high-end finish tier, Silestone counters"
- Structured, comparable, maps to renovation scope

### Source

Unlike energy (CTE) and process (CSCAE), interior design has no single authority.

**Approach:** Use Gemini to synthesize from its training knowledge, structured into:
- Design styles (with indicators)
- Finish quality tiers (with observable evidence)
- Materials vocabulary (with tier mapping)
- Spanish construction eras (with typical finishes)

### Schema: interior_design_knowledge.json

```yaml
interior_design_knowledge:
  $schema: "interior_design_knowledge_v1"
  $version: "1.0.0"
  $approach: "Gemini synthesis from design knowledge"
  
  # ============================================================
  # DESIGN STYLES
  # ============================================================
  styles:
    contemporary:
      description: "Clean lines, neutral palette, minimal ornamentation"
      indicators:
        - "Flat-panel cabinets"
        - "Integrated appliances"
        - "Hidden storage"
        - "Large format tiles"
        - "Minimal hardware"
      color_palette: ["white", "grey", "natural wood", "black accents"]
      era_association: "2010s-present"
      
    mediterranean_spanish:
      description: "Terracotta, wrought iron, decorative tiles, warmth"
      indicators:
        - "Azulejos (decorative tiles)"
        - "Dark wood beams"
        - "Arched doorways"
        - "Terracotta flooring"
        - "Wrought iron details"
      color_palette: ["terracotta", "ochre", "cream", "blue accents"]
      era_association: "Traditional, revived 1990s-2000s"
      
    industrial:
      description: "Exposed structure, raw materials, urban aesthetic"
      indicators:
        - "Exposed brick"
        - "Metal fixtures"
        - "Concrete elements"
        - "Open ductwork"
        - "Edison bulbs"
      color_palette: ["grey", "black", "rust", "natural materials"]
      era_association: "2000s-present (urban lofts)"
      
    scandinavian:
      description: "Light, minimal, functional, natural materials"
      indicators:
        - "White walls"
        - "Light wood"
        - "Simple furniture"
        - "Natural textiles"
        - "Plants"
      color_palette: ["white", "light grey", "pale wood", "muted colors"]
      era_association: "2010s-present"
      
    mid_century_modern:
      description: "Organic curves, bold colors, statement pieces"
      indicators:
        - "Tapered legs"
        - "Geometric patterns"
        - "Teak/walnut wood"
        - "Statement lighting"
        - "Open plan"
      color_palette: ["mustard", "teal", "orange", "wood tones"]
      era_association: "1950s-1970s, revived 2010s"
      
    traditional_spanish_dated:
      description: "1960s-1980s Spanish construction, original finishes"
      indicators:
        - "Gotelé texture walls"
        - "Terrazzo floors"
        - "Dark wood doors"
        - "Small rooms"
        - "Decorative moldings"
      color_palette: ["beige", "brown", "cream", "earth tones"]
      era_association: "1960s-1980s (unrenovated)"
      note: "This is 'what needs renovation' - the baseline"
  
  # ============================================================
  # FINISH QUALITY TIERS (Observable evidence)
  # ============================================================
  finish_quality:
    builder_grade:
      description: "Minimum specification, cost-driven, functional"
      kitchen:
        countertops: ["Laminate", "Basic ceramic tile"]
        cabinets: ["Melamine", "Basic MDF", "No soft-close"]
        appliances: ["White/black standard", "Entry-level brands"]
      bathroom:
        fixtures: ["Basic ceramic", "Chrome plastic"]
        surfaces: ["Small format ceramic tile", "Acrylic tub"]
        shower: ["Over-bath with curtain", "Basic enclosure"]
      flooring: ["Vinyl", "Basic ceramic", "Entry laminate"]
      doors: ["Hollow-core", "Basic hardware"]
      
    mid_range:
      description: "Upgraded materials, design consideration, durability"
      kitchen:
        countertops: ["Granite", "Entry quartz"]
        cabinets: ["Lacquered MDF", "Soft-close", "Some organization"]
        appliances: ["Stainless steel", "Mid-tier brands (Bosch, Siemens)"]
      bathroom:
        fixtures: ["Quality porcelain", "Chrome metal"]
        surfaces: ["Large format tiles", "Quality porcelain"]
        shower: ["Fixed glass panel", "Quality fittings"]
      flooring: ["Quality ceramic", "Engineered wood", "Good laminate"]
      doors: ["Solid-core", "Quality hardware"]
      
    high_end:
      description: "Premium materials, designer elements, craftsmanship"
      kitchen:
        countertops: ["Silestone/Caesarstone", "Dekton", "Natural stone"]
        cabinets: ["Custom lacquer", "Integrated handles", "Full organization"]
        appliances: ["Integrated panels", "Premium brands (Miele, Gaggenau)"]
      bathroom:
        fixtures: ["Wall-hung", "Designer brands (Roca, Duravit)"]
        surfaces: ["Large format porcelain", "Natural stone accents"]
        shower: ["Frameless walk-in", "Rain shower", "Niches"]
      flooring: ["Solid hardwood", "Premium porcelain", "Natural stone"]
      doors: ["Solid wood", "Designer hardware", "Hidden frames"]
      
    luxury:
      description: "Bespoke, rare materials, architectural features"
      indicators:
        - "Custom millwork"
        - "Rare stones (marble, onyx)"
        - "Smart home integration"
        - "Designer fixtures (Dornbracht, Fantini)"
        - "Architectural lighting"
        - "Wine storage, dedicated spaces"
  
  # ============================================================
  # MATERIALS VOCABULARY
  # ============================================================
  materials:
    countertops:
      - name: "Laminate"
        tier: "builder"
        durability: "low"
        note: "Budget option, prone to damage"
      - name: "Ceramic tile"
        tier: "builder"
        durability: "medium"
        note: "Dated, grout maintenance"
      - name: "Granite"
        tier: "mid"
        durability: "high"
        note: "Natural variation, requires sealing"
      - name: "Quartz (Silestone/Caesarstone)"
        tier: "mid-high"
        durability: "very high"
        note: "Engineered, consistent, low maintenance"
      - name: "Dekton/Neolith"
        tier: "high"
        durability: "extreme"
        note: "Ultra-compact, heat/scratch resistant"
      - name: "Marble"
        tier: "luxury"
        durability: "medium"
        note: "Beautiful but requires care, stains"
        
    flooring:
      - name: "Vinyl/PVC"
        tier: "builder"
        durability: "medium"
        note: "Budget, can look cheap"
      - name: "Terrazzo"
        tier: "context-dependent"
        note: "Original 1970s = dated; New polished = trendy"
      - name: "Ceramic tile"
        tier: "builder-mid"
        durability: "high"
        note: "Common, grout maintenance"
      - name: "Porcelain tile"
        tier: "mid-high"
        durability: "very high"
        note: "Modern standard, many finishes"
      - name: "Laminate"
        tier: "builder-mid"
        durability: "medium"
        note: "Wood look, water-sensitive"
      - name: "Engineered wood"
        tier: "mid-high"
        durability: "medium-high"
        note: "Real wood top, stable"
      - name: "Solid hardwood"
        tier: "high"
        durability: "high (with care)"
        note: "Premium, can refinish"
        
    cabinets:
      - name: "Melamine"
        tier: "builder"
        note: "Functional, limited durability"
      - name: "Thermofoil"
        tier: "builder-mid"
        note: "Smooth finish, can peel"
      - name: "Lacquered MDF"
        tier: "mid-high"
        note: "Good finish, many colors"
      - name: "Solid wood"
        tier: "high"
        note: "Traditional, durable"
      - name: "Custom lacquer"
        tier: "luxury"
        note: "Bespoke, perfect finish"
  
  # ============================================================
  # SPANISH CONSTRUCTION ERAS (Typical original finishes)
  # ============================================================
  construction_eras:
    pre_1940:
      period: "Pre-Civil War / Early Franco"
      construction: "Load-bearing walls, high ceilings, thick walls"
      typical_finishes:
        floors: "Hydraulic tile (baldosa hidráulica), wood"
        walls: "Plaster, high quality"
        doors: "Solid wood, ornate"
        kitchens: "Minimal, often relocated"
        bathrooms: "Often added later"
      condition_today: "Character if maintained, problematic if neglected"
      renovation_approach: "Restoration vs modernization tension"
      
    1940_1960:
      period: "Post-War / Autarky"
      construction: "Austerity, basic materials, small units"
      typical_finishes:
        floors: "Terrazzo, basic ceramic"
        walls: "Basic plaster, often gotelé added later"
        doors: "Simple wood"
        kitchens: "Minimal, basic"
        bathrooms: "Basic, small"
      condition_today: "Usually needs complete renovation"
      renovation_approach: "Full gut, modernize layout"
      
    1960_1980:
      period: "Desarrollo / Construction Boom"
      construction: "Mass housing, variable quality, concrete blocks"
      typical_finishes:
        floors: "Terrazzo (most common)"
        walls: "Gotelé texture"
        doors: "Dark wood veneer"
        kitchens: "Formica, basic tiles"
        bathrooms: "Colored suites (green, pink, blue)"
      condition_today: "Most common renovation candidates"
      renovation_approach: "Full renovation, improve layout"
      energy_note: "No insulation, single-pane windows"
      
    1980_2000:
      period: "Democracy / EU Entry"
      construction: "Improved standards (NBE-CT-79), still dated"
      typical_finishes:
        floors: "Large ceramic tiles, some parquet"
        walls: "Smooth plaster, some gotelé"
        doors: "Wood, better quality"
        kitchens: "Granite, wood cabinets"
        bathrooms: "White suites, better quality"
      condition_today: "Functional but visually dated"
      renovation_approach: "Selective updates possible"
      
    2000_2015:
      period: "Boom and Crisis"
      construction: "CTE 2006 onwards, modern standards"
      typical_finishes:
        floors: "Parquet, quality ceramic"
        walls: "Smooth, neutral colors"
        kitchens: "Granite/silestone, modern cabinets"
        bathrooms: "Modern white, better layouts"
      condition_today: "Often acceptable, selective updates"
      renovation_approach: "Cosmetic updates, specific improvements"
      
    2015_present:
      period: "Post-Crisis / Current"
      construction: "Current standards, energy focus"
      typical_finishes:
        floors: "Porcelain, engineered wood"
        walls: "Smooth, often white"
        kitchens: "Quartz, integrated appliances"
        bathrooms: "Walk-in showers, large tiles"
      condition_today: "Current market standard"
      renovation_approach: "Usually not needed, personalization only"
```

---

## Property Intelligence Report Schema

**One Gemini call per property produces this complete report.**

### Context Provided to Gemini

```yaml
system_instruction_additions:
  # From V0.3.1
  - energy_knowledge.json (flattened ~6K tokens)
  - renovation_process_knowledge.json (flattened ~4K tokens)
  
  # New for V0.3.2
  - interior_design_knowledge.json (flattened ~8K tokens)
  - uniclass_residential.json (Ss + Pr codes, ~10K tokens)
  - rules_engine.json (age-based rules, ~5K tokens)
  
  # From V0.3
  - KG context (~214K tokens) - for task awareness
```

### Input Per Property

```yaml
property_input:
  listing_data:
    title: "Piso en venta en Chamberí"
    price: 450000
    area_m2: 85
    rooms: 3
    bathrooms: 1
    floor: 3
    year_built: 1975  # From cadastre or estimate
    energy_rating: "G"  # If available
    description: "..."
  
  photos:
    - photo_url: "..."
      room_assignment: "living_room"  # From clustering
    - photo_url: "..."
      room_assignment: "kitchen"
    # ... all photos
  
  cadastre_data:  # If available
    year_built: 1975
    area_constructed: 92
    facade_length: 8.5
```

### Output Schema

```yaml
property_intelligence_report:
  
  # ============================================================
  # SECTION A: BUILDING PROFILE
  # Hard facts from listing + cadastre + inference
  # ============================================================
  building_profile:
    year_built: 1975
    year_source: "cadastre"  # or "listing", "estimate"
    construction_era: "1960_1980"  # From interior_design_knowledge
    building_type: "multi_family_block"
    floor: 3
    total_floors: 6  # If determinable
    orientation: "south"  # If determinable
    facade_material: "brick_rendered"  # If visible
    
    # Energy profile (from V0.3.1 energy_knowledge)
    energy:
      rating_actual: "G"  # From listing
      rating_expected: "F-G"  # From age correlation
      climate_zone: "D"  # Madrid
      envelope_assessment: "poor"
      visible_deficiencies:
        - "Single-pane aluminum windows"
        - "No visible wall insulation"
        - "Cajón persiana uninsulated"
  
  # ============================================================
  # SECTION B: ROOM-BY-ROOM ANALYSIS
  # Combines Uniclass inventory + condition + design assessment
  # ============================================================
  rooms:
    - room_id: "living_001"
      room_type: "living_room"
      photos: ["photo_001.jpg", "photo_002.jpg"]
      
      # Dimensions (if measurable/inferable)
      dimensions:
        area_m2_estimate: 18
        ceiling_height: "standard"  # or "high", "low"
        natural_light: "moderate"
      
      # Systems inventory (Uniclass Ss codes)
      systems:
        - code: "Ss_25_10_30"
          title: "External wall systems"
          presence: "visible"
          condition_ite: "leve"  # ITE grade
          notes: "Gotelé texture, minor cracks near window"
          
        - code: "Ss_32_20"
          title: "Floor systems"
          presence: "visible"
          condition_ite: "leve"
          notes: "Terrazzo, intact but dated"
          
        - code: "Ss_70_30_80"
          title: "Small power systems"
          presence: "visible"
          condition_ite: "importante"
          notes: "Insufficient outlets, surface-mounted"
      
      # Products inventory (Uniclass Pr codes)
      products:
        - code: "Pr_40_50_85"
          title: "Windows"
          material: "Single-pane aluminum"
          condition: "functional_poor_thermal"
          age_estimate: "original_1975"
          
        - code: "Pr_35_57_22_14"
          title: "Floor tiles"
          material: "Terrazzo"
          condition: "fair"
          pattern: "1970s geometric"
          
        - code: "Pr_40_30_35"
          title: "Interior doors"
          material: "Dark wood veneer"
          condition: "functional"
          style: "traditional_1970s"
      
      # Rule verifications (from rules_engine)
      rule_verifications:
        - rule_id: "REBT_PRE_2002"
          status: "concern"
          evidence: "Old outlets, no visible modern panel"
          
        - rule_id: "INSULATION_PRE_1980"
          status: "confirmed"
          evidence: "No insulation visible, era construction"
      
      # Design assessment (from interior_design_knowledge)
      design_assessment:
        style_detected: "traditional_spanish_dated"
        style_indicators:
          - "Gotelé walls"
          - "Terrazzo floor"
          - "Dark wood doors"
        finish_tier: "builder_grade"
        color_palette: ["beige", "brown", "cream"]
        overall_impression: "Original 1970s, functional but dated"
      
      # Summary for this room
      condition_summary: "Dated but structurally sound, needs full refresh"
      key_issues:
        - "Thermal: Single-pane window"
        - "Electrical: Insufficient outlets"
        - "Aesthetic: Original 1970s finishes"
    
    - room_id: "kitchen_001"
      room_type: "kitchen"
      photos: ["photo_003.jpg"]
      
      dimensions:
        area_m2_estimate: 8
        layout_type: "galley_closed"
      
      systems:
        - code: "Ss_45_10"
          title: "Sanitary pipework"
          presence: "visible"
          condition_ite: "importante"
          notes: "Galvanized pipes visible under sink"
          
        - code: "Ss_60_40_35"
          title: "Ventilation"
          presence: "absent"
          notes: "No mechanical extraction visible"
      
      products:
        - code: "Pr_40_30"
          title: "Kitchen units"
          material: "Melamine white"
          condition: "worn"
          age_estimate: "1990s_update"
          
        - code: "Pr_40_50_20"
          title: "Countertop"
          material: "Laminate"
          condition: "poor"
          notes: "Chipped edges, staining"
          
        - code: "Pr_40_20_87"
          title: "Kitchen taps"
          material: "Chrome"
          condition: "dated"
          type: "Separate hot/cold"
      
      design_assessment:
        style_detected: "traditional_spanish_dated"
        finish_tier: "builder_grade"
        kitchen_specific:
          countertops: "laminate"
          cabinets: "melamine_basic"
          appliances: "mixed_basic"
          layout: "closed_galley"
        overall_impression: "Functional but cramped and dated, needs full renovation"
      
      condition_summary: "Needs complete renovation"
      key_issues:
        - "Plumbing: Galvanized pipes (lead risk)"
        - "Ventilation: No extraction"
        - "Layout: Closed, inefficient"
        - "Finishes: All at end of life"
    
    # ... bathroom, bedrooms, etc.
  
  # ============================================================
  # SECTION C: REGULATORY ASSESSMENT
  # Spanish standards compliance
  # ============================================================
  regulatory_assessment:
    
    # CTE compliance concerns
    cte:
      db_he:  # Energy
        status: "non_compliant"
        issues:
          - area: "HE1"
            description: "Windows exceed U-value limit"
            evidence: "Single-pane aluminum (~5.7 vs limit 1.8 W/m²K)"
          - area: "HE1"
            description: "No wall insulation"
            evidence: "Era construction, no SATE visible"
            
      db_hs:  # Health/Salubridad
        status: "concern"
        issues:
          - area: "HS3"
            description: "Ventilation inadequate"
            evidence: "No mechanical ventilation in kitchen/bath"
          - area: "HS5"
            description: "Drainage age concern"
            evidence: "Pre-1980 installation"
    
    # REBT electrical compliance
    rebt:
      status: "pre_2002_concern"
      evidence:
        - "Old-style fuse box visible"
        - "Insufficient circuit breakers"
        - "Surface-mounted wiring in places"
      likely_scope: "Full electrical upgrade needed"
    
    # ITE projection
    ite:
      applicable: true  # Building >50 years
      likely_findings:
        - category: "Fachada"
          severity: "leve-importante"
          evidence: "Minor cracks, thermal deficiency"
        - category: "Instalaciones"
          severity: "importante"
          evidence: "Pre-REBT electrical, old plumbing"
  
  # ============================================================
  # SECTION D: OVERALL DESIGN PROFILE
  # Aggregated from all rooms
  # ============================================================
  design_profile:
    dominant_style: "traditional_spanish_dated"
    era_authenticity: "largely_original_1975"
    updates_detected:
      - "Kitchen cabinets possibly 1990s"
      - "Some light fixtures updated"
    
    finish_quality_overall: "builder_grade"
    
    material_summary:
      flooring: "Terrazzo throughout (original)"
      walls: "Gotelé texture (original)"
      woodwork: "Dark veneer doors (original)"
      kitchen: "Laminate/melamine (dated update)"
      bathroom: "Basic ceramic (original or minimal update)"
    
    color_palette_overall: ["beige", "brown", "cream", "earth_tones"]
    
    layout_assessment:
      type: "compartmentalized"
      issues:
        - "Closed kitchen"
        - "Narrow hallway"
        - "Small bedrooms"
      potential: "Wall removal possible for open plan"
    
    natural_light_assessment:
      level: "low_moderate"
      reasons:
        - "Small windows (era typical)"
        - "Deep rooms"
        - "Single orientation"
  
  # ============================================================
  # SECTION E: RENOVATION TRIGGERS
  # From V0.3.1 process_knowledge - what would motivate action
  # ============================================================
  triggers:
    - category: "economic"
      trigger: "Facturas de energía excesivas"
      evidence: "Poor thermal envelope, rating G"
      urgency: "high"
      
    - category: "regulatory"
      trigger: "ITE probable deficiencias"
      evidence: "Building >50 years, visible issues"
      urgency: "medium"
      timeline: "Required inspection"
      
    - category: "comfort"
      trigger: "Frío/calor excesivo"
      evidence: "No insulation, single-pane windows"
      urgency: "high"
      
    - category: "building_problems"
      trigger: "Instalación eléctrica obsoleta"
      evidence: "Pre-REBT 2002 indicators"
      urgency: "high"
      safety: true
      
    - category: "aesthetic"
      trigger: "Aspecto anticuado"
      evidence: "Original 1970s finishes throughout"
      urgency: "medium"
      note: "Personal preference but affects resale"
  
  # ============================================================
  # SECTION F: COMPARISON-READY ATTRIBUTES
  # Structured for direct comparison with comparables
  # ============================================================
  comparison_attributes:
    # Energy
    energy_rating: "G"
    envelope_condition: "poor"
    window_type: "single_pane_aluminum"
    insulation_visible: false
    hvac_type: "individual_gas_radiators"
    
    # Systems
    electrical_era: "pre_2002"
    plumbing_material: "galvanized_visible"
    ventilation_mechanical: false
    
    # Finishes
    finish_era: "1970s_original"
    finish_tier: "builder_grade"
    kitchen_last_update: "1990s_partial"
    bathroom_last_update: "original"
    flooring_type: "terrazzo"
    
    # Layout
    layout_type: "compartmentalized"
    kitchen_open: false
    natural_light: "low_moderate"
    
    # Design
    style: "traditional_spanish_dated"
    color_palette: "earth_tones"
    
    # Condition
    structural_concerns: false
    humidity_visible: false
    maintenance_level: "fair"
```

---

## Comparative Gap Analysis Schema

**Input:** Target Property Intelligence Report + Comparable Property Intelligence Report

**One Gemini call produces direct comparisons.**

```yaml
comparative_gap_analysis:
  target:
    listing_id: 123
    address: "Calle Example 45, Madrid"
  
  comparable:
    listing_id: 456
    address: "Calle Similar 23, Madrid"
    relevance: "Same neighborhood, similar size, recently renovated"
  
  # ============================================================
  # DIRECT ATTRIBUTE COMPARISONS
  # ============================================================
  comparisons:
    
    # ENVELOPE
    - category: "envelope"
      attribute: "windows"
      target:
        value: "Single-pane aluminum, original 1975"
        u_value: "~5.7 W/m²K"
        from_report: "comparison_attributes.window_type"
      comparable:
        value: "Double-glazed PVC with thermal break"
        u_value: "~1.5 W/m²K"
      gap:
        description: "Full window replacement required"
        intervention_ids: ["TASK_WINDOW_REPLACE"]
        energy_impact: "+1 letter"
        priority: "high"
    
    - category: "envelope"
      attribute: "wall_insulation"
      target:
        value: "None visible, solid brick"
        u_value: "~1.8 W/m²K"
      comparable:
        value: "SATE visible on facade"
        u_value: "~0.3 W/m²K"
      gap:
        description: "Exterior insulation system needed"
        intervention_ids: ["TASK_SATE"]
        energy_impact: "+2 letters"
        priority: "high"
        note: "Requires community decision if multi-family"
    
    # SYSTEMS
    - category: "systems"
      attribute: "electrical"
      target:
        value: "Pre-REBT 2002, fuse box, insufficient outlets"
        compliance: "Non-compliant"
      comparable:
        value: "Modern consumer unit, RCDs, abundant outlets"
        compliance: "REBT 2002 compliant"
      gap:
        description: "Full electrical upgrade"
        intervention_ids: ["TASK_ELECTRICAL_PANEL", "TASK_REWIRE", "TASK_OUTLETS"]
        priority: "high"
        safety_critical: true
    
    - category: "systems"
      attribute: "plumbing"
      target:
        value: "Galvanized pipes visible, 1975 original"
        risk: "Corrosion, possible lead"
      comparable:
        value: "Copper/PEX, modern installation"
        risk: "None"
      gap:
        description: "Full plumbing replacement recommended"
        intervention_ids: ["TASK_PLUMBING_REPLACE"]
        priority: "medium-high"
    
    # FINISHES - KITCHEN
    - category: "finishes"
      attribute: "kitchen"
      target:
        layout: "Closed galley, 8m²"
        countertops: "Laminate, chipped"
        cabinets: "Melamine, 1990s"
        appliances: "Mixed basic"
        tier: "builder_grade"
      comparable:
        layout: "Open to living, island, 12m²"
        countertops: "Silestone"
        cabinets: "Lacquer handleless, soft-close"
        appliances: "Integrated Bosch"
        tier: "high_end"
      gap:
        description: "Complete kitchen renovation + layout change"
        intervention_ids: [
          "TASK_KITCHEN_DEMO",
          "TASK_WALL_REMOVE",  # For open plan
          "TASK_KITCHEN_CABINETS",
          "TASK_KITCHEN_COUNTERTOP",
          "TASK_KITCHEN_APPLIANCES",
          "TASK_KITCHEN_ISLAND"
        ]
        design_transformation: "builder_grade → high_end"
        layout_change: true
        structural_assessment_needed: true
    
    # FINISHES - BATHROOM
    - category: "finishes"
      attribute: "bathroom_main"
      target:
        fixtures: "Basic ceramic, 1975 original"
        tiles: "Small format, colored (green)"
        shower: "Over-bath with curtain"
        tier: "builder_grade"
      comparable:
        fixtures: "Wall-hung Roca"
        tiles: "Large format porcelain"
        shower: "Walk-in frameless, rain head"
        tier: "high_end"
      gap:
        description: "Complete bathroom renovation"
        intervention_ids: [
          "TASK_BATHROOM_DEMO",
          "TASK_BATHROOM_WATERPROOF",
          "TASK_BATHROOM_TILE",
          "TASK_BATHROOM_FIXTURES",
          "TASK_SHOWER_WALKIN"
        ]
        design_transformation: "builder_grade → high_end"
    
    # FINISHES - FLOORING
    - category: "finishes"
      attribute: "flooring"
      target:
        material: "Terrazzo throughout"
        condition: "Fair, dated pattern"
        style: "1970s"
      comparable:
        material: "Engineered oak"
        condition: "Excellent"
        style: "Contemporary warm"
      gap:
        description: "Floor replacement throughout"
        intervention_ids: [
          "TASK_FLOOR_DEMO",
          "TASK_FLOOR_LEVEL",
          "TASK_FLOOR_WOOD"
        ]
        area_affected: "all_rooms"
    
    # FINISHES - WALLS
    - category: "finishes"
      attribute: "wall_finish"
      target:
        texture: "Gotelé throughout"
        condition: "Yellowed, dated"
      comparable:
        texture: "Smooth, painted white"
        condition: "Excellent"
      gap:
        description: "Remove gotelé, smooth and paint"
        intervention_ids: [
          "TASK_GOTELE_REMOVE",
          "TASK_PLASTER_SMOOTH",
          "TASK_PAINT"
        ]
        note: "Labor intensive if gotelé removal"
    
    # LAYOUT
    - category: "layout"
      attribute: "kitchen_living_relationship"
      target:
        type: "Closed, separated"
        wall: "Load-bearing unknown"
      comparable:
        type: "Open plan, integrated"
      gap:
        description: "Wall removal for open concept"
        intervention_ids: ["TASK_STRUCTURAL_ASSESS", "TASK_WALL_REMOVE", "TASK_BEAM_INSTALL"]
        requires_permit: "obra_mayor"
        structural_work: true
    
    # DESIGN
    - category: "design"
      attribute: "overall_style"
      target:
        style: "Traditional Spanish 1970s"
        palette: "Earth tones, brown, beige"
        feel: "Dated, dark"
      comparable:
        style: "Contemporary Scandinavian"
        palette: "White, grey, natural wood"
        feel: "Light, airy, modern"
      gap:
        description: "Complete design transformation"
        scope: "All visible finishes, lighting design, color scheme"
        note: "Achieved through cumulative finish changes above"
  
  # ============================================================
  # ENERGY GAP SUMMARY
  # ============================================================
  energy_summary:
    target_rating: "G"
    comparable_rating: "C"
    gap_letters: 4
    upgrade_pathway: "G_to_C"  # From energy_knowledge
    
    interventions_for_energy:
      - intervention: "wall_insulation_sate"
        impact: "+2 letters"
        from_comparison: "envelope.wall_insulation"
      - intervention: "window_replacement"
        impact: "+1 letter"
        from_comparison: "envelope.windows"
      - intervention: "hvac_upgrade"
        impact: "+1 letter"
        note: "Heat pump recommended"
    
    subsidy_notes:
      eligible: true
      pathway: "IDAE Program 3 (>45% improvement)"
      documentation: "CEE before/after required"
  
  # ============================================================
  # SCOPE SUMMARY
  # ============================================================
  scope_summary:
    level: "Comprehensive renovation"
    
    intervention_count: 35  # Total KG tasks after expansion
    
    categories:
      - name: "Envelope"
        interventions: ["windows", "SATE"]
        permit: "May require community approval"
      - name: "Systems"
        interventions: ["electrical", "plumbing"]
        permit: "Obra menor"
      - name: "Finishes"
        interventions: ["kitchen", "bathroom", "flooring", "walls"]
        permit: "Obra menor"
      - name: "Layout"
        interventions: ["wall removal"]
        permit: "Obra mayor (structural)"
    
    permits_required:
      - type: "Obra menor"
        for: "Interior finishes, systems"
      - type: "Obra mayor"
        for: "Structural modification"
        note: "Only if wall removal confirmed structural"
    
    risk_factors:
      - "Hidden electrical issues when walls opened"
      - "Possible asbestos in old materials"
      - "Structural assessment needed for load-bearing wall"
      - "Community approval needed for SATE if multi-family"
    
    estimated_duration: "3-4 months"
```

---

## Integration with V0.3 Scope Generation

**Gap Analysis output feeds into V0.3's KG-based scope expansion.**

```
Gap Analysis                    KG (from V0.3)                   BCCA (from V0.3)
─────────────────────────────────────────────────────────────────────────────────
intervention_ids: [             task: TASK_WINDOW_REPLACE        search_bcca(
  "TASK_WINDOW_REPLACE"    →      requires: [TASK_REMOVE_OLD]  →   "ventana PVC RPT",
]                                 triggers: [TASK_SEAL]            chapter="08"
                                  quantity_guidance: {...}       )
                                                                   → returns price items
```

The gap analysis produces **what** needs to change.
V0.3's KG expansion produces **how** (dependencies, triggers).
V0.3's BCCA RAG produces **how much** (pricing).

---

## File Structure (V0.3.2 additions)

```
Lean MVP/
├── standards/
│   ├── energy_knowledge.json              ← V0.3.1
│   ├── renovation_process_knowledge.json  ← V0.3.1
│   └── interior_design_knowledge.json     ← V0.3.2 NEW
│
├── backend/
│   ├── scripts/
│   │   ├── extract_energy_knowledge.py        ← V0.3.1
│   │   ├── extract_process_knowledge.py       ← V0.3.1
│   │   └── extract_interior_design_knowledge.py  ← V0.3.2 NEW
│   │
│   └── pipeline/
│       ├── steps/
│       │   ├── assess_uniclass.py         ← DEPRECATED by V0.3.2
│       │   ├── verify_rules.py            ← DEPRECATED by V0.3.2
│       │   └── property_intelligence.py   ← V0.3.2 NEW (replaces above)
│       │
│       ├── gap_analysis.py                ← UPDATED in V0.3.2
│       └── schemas/
│           ├── property_intelligence.py   ← V0.3.2 NEW
│           └── gap_analysis.py            ← UPDATED in V0.3.2
│
└── docs/
    ├── PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md      ← Core architecture
    ├── PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md    ← Knowledge bases
    ├── PETER_AGENTIC_V0.3.2_UNIFIED_PROPERTY_INTELLIGENCE.md  ← This doc
    └── PETER_AGENTIC_MASTER_INDEX.md                    ← NEW (next)
```

---

## Implementation Phases

### Phase 0: Interior Design Knowledge (1 day)
- [ ] Create `extract_interior_design_knowledge.py`
- [ ] Generate `interior_design_knowledge.json`
- [ ] Validate with sample properties

### Phase 1: Property Intelligence Report (2 days)
- [ ] Create `property_intelligence.py` step
- [ ] Define Pydantic schemas
- [ ] Build comprehensive prompt with all knowledge bases
- [ ] Test on sample properties

### Phase 2: Updated Gap Analysis (2 days)
- [ ] Update `gap_analysis.py` to use Property Intelligence Reports
- [ ] Implement direct comparison logic
- [ ] Map comparisons to intervention_ids
- [ ] Test with target + comparable pairs

### Phase 3: Pipeline Integration (1 day)
- [ ] Deprecate `assess_uniclass.py` and `verify_rules.py`
- [ ] Update orchestrator to use new flow
- [ ] Ensure V0.3 scope expansion still works

### Phase 4: UI Updates (2 days)
- [ ] Customer view: Before/after, transformation summary
- [ ] Contractor view: Technical BoQ from scope

---

## Success Criteria

### Property Intelligence Report
- [ ] Single Gemini call produces complete report
- [ ] All Uniclass codes properly assigned
- [ ] All rule verifications included
- [ ] Design assessment uses interior_design_knowledge vocabulary
- [ ] Comparison attributes are structured and consistent

### Gap Analysis
- [ ] Direct attribute-by-attribute comparison
- [ ] Each gap maps to intervention_ids
- [ ] Energy summary with letter improvements
- [ ] No "basic/premium" tier language (direct comparison only)

### Integration
- [ ] Gap intervention_ids feed into V0.3 KG expansion
- [ ] BCCA pricing works with expanded scope
- [ ] Token budget stays under 300K per request

