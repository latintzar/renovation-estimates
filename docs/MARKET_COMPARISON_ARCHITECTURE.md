Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Market Comparison Architecture

> **Purpose**: Compare a listing's condition against market comparables to determine what renovations are needed to reach each price bracket.

---

## Table of Contents

### Part 1: Methodology & Compliance
1. [Overview](#overview)
2. [Regulatory Framework & Methodology](#regulatory-framework--methodology)
3. [Compliance Readiness Assessment](#compliance-readiness-assessment)
4. [Where Professionals Fit In](#where-professionals-fit-in)
5. [Energy Efficiency Loans & Subsidies](#energy-efficiency-loans--subsidies)

### Part 2: Technical Architecture
6. [Data Sources](#data-sources)
7. [Architecture Diagram](#architecture-diagram)
8. [Data Flow](#data-flow)
9. [Comparison Matrix Structure](#comparison-matrix-structure)
10. [Gap Analysis Logic](#gap-analysis-logic)
11. [Gemini Integration](#gemini-integration)
12. [Response Schema](#response-schema)
13. [Database Tables](#database-tables)
14. [API Endpoints](#api-endpoints)
15. [UI Components](#ui-components)
16. [Disclaimers & Limitations](#disclaimers--limitations)
17. [Inspection Framework Summary](#inspection-framework-summary)

---

## Overview

### What This Does

Given a listing that has been analyzed with:
- `verify_rules.py` → Building code compliance (behind the walls)
- `assess_uniclass.py` → Visible elements inventory
- Energy rating → Efficiency class (A-G)

And comparable properties from Casafari (also analyzed), we:

1. **Compare** the listing against 3 price brackets (fast_sell, fair_market, out_of_market)
2. **Identify gaps** in rules compliance, energy efficiency, and visible finishes
3. **Generate recommendations** for what upgrades are needed to reach each bracket
4. **Pass scope items to KGEstimator** for BCCA-based pricing (separate step)

### Why This Matters

A buyer looking at a €320,000 property wants to know:
- "What would it take to make this worth €445,000 (fair market)?"
- "Is the gap mostly hidden systems (expensive) or just finishes (cheaper)?"
- "What's the energy upgrade path?"

---

## Regulatory Framework & Methodology

### The Rules Engine: Built on Spanish Law

Our `rules_engine_v2.json` is **not arbitrary** - it's derived from **8+ official Spanish regulatory sources**:

| Code | Full Name | What It Covers | Year | Key Rules |
|------|-----------|----------------|------|-----------|
| **REBT 2002** | Reglamento Electrotécnico para Baja Tensión | Electrical safety standards | 2002 | `ELEC_REBT_001`, `ELEC_GROUND_002` |
| **CTE DB-HS** | Código Técnico de la Edificación - Salubridad | Health/hygiene (ventilation, waterproofing, drainage) | 2006 | `PLUMB_*`, `HYGIENE_*` |
| **CTE DB-HE** | Código Técnico - Ahorro de Energía | Energy efficiency (windows, insulation, thermal bridge) | 2006/2019 | `ENV_WIN_001`, `ENV_INSUL_*` |
| **CTE DB-HR** | Código Técnico - Protección frente al Ruido | Acoustic requirements | 2008 | `ENV_ACOUSTIC_*` |
| **ITE** | Inspección Técnica de Edificios | Building conservation (structural, damp, facades) | Varies | `STRUCT_CRACK_*`, `DAMP_*` |
| **RITE 2013** | Reglamento de Instalaciones Térmicas en Edificios | HVAC/thermal installations | 2013 | `PLUMB_HEATER_003` |
| **RD 140/2003** | Real Decreto sobre Agua Potable | Lead pipes replacement mandatory | 2003 | `PLUMB_LEAD_001` |
| **CE 2020** | Código Estructural | Structural code | 2020 | `STRUCT_*` |

### How Each Rule Is Structured

```json
{
  "id": "ELEC_REBT_001",           // Unique identifier
  "system": "electrical",          // Building system category
  "room_types": ["cocina", "baño"], // Where to check
  "year_trigger": 2002,            // Buildings BEFORE this year need checking
  "visual_triggers": [             // What AI looks for in photos
    "black fuse box", 
    "ceramic fuses",
    "2-pin sockets", 
    "cloth wiring"
  ],
  "condition_assessment": {
    "prompt_instruction": "...",   // AI guidance for photo analysis
    "risk_label": "Non-Compliant (REBT 2002)",
    "risk_description": "Installation predates safety standards. High fire risk."
  },
  "remedial_action": {
    "task_id": "rewrite_electrical_installation",
    "bcca_keyword": "instalación eléctrica vivienda completa",  // For cost lookup
    "package": "ESSENTIAL",        // ESSENTIAL vs MODERN
    "category": "SAFETY",          // SAFETY, HYGIENE, ENERGY, STRUCTURAL
    "regulation_ref": "RD 842/2002 Art. 10"  // Legal reference
  }
}
```

### The Logic Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RULES ENGINE EVALUATION                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   STEP 1: AGE CHECK                                                             │
│   ─────────────────                                                             │
│   year_built (1975) < year_trigger (2002) ? → YES → Rule applies                │
│                                                                                 │
│   STEP 2: VISUAL DETECTION                                                      │
│   ────────────────────────                                                      │
│   Photo shows "ceramic fuses" ∈ visual_triggers ? → YES → Issue detected        │
│                                                                                 │
│   STEP 3: STATUS ASSIGNMENT                                                     │
│   ────────────────────────                                                      │
│   ┌───────────────┬───────────────────────────────────────────┐                │
│   │ Status        │ Meaning                                   │                │
│   ├───────────────┼───────────────────────────────────────────┤                │
│   │ "confirmed"   │ Visual evidence proves NON-compliance     │                │
│   │ "rejected"    │ Visual evidence proves COMPLIANCE         │                │
│   │ "not_visible" │ Cannot determine from photos              │                │
│   └───────────────┴───────────────────────────────────────────┘                │
│                                                                                 │
│   STEP 4: REMEDIAL ACTION MAPPING                                               │
│   ──────────────────────────────                                                │
│   status == "confirmed" → remedial_action required                              │
│   → Links to BCCA cost database via bcca_keyword                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### What "Very Good Condition" Means for Market Comparison

When Casafari returns properties in `condition: "very-good"`, those properties:

1. **Have already passed inspections** (Cédula, ITE if applicable)
2. **Meet current building codes** (or were grandfathered)
3. **Have modern finishes** (visible quality indicators)

Our comparison identifies the **GAP** between your listing and these properties:

```
YOUR LISTING                        "VERY GOOD" COMPARABLES
═══════════════                     ═══════════════════════

Rules Compliance:                   Rules Compliance:
• ELEC_REBT_001: confirmed ❌       • ELEC_REBT_001: rejected ✅ (modern wiring)
• PLUMB_LEAD_001: confirmed ❌      • PLUMB_LEAD_001: rejected ✅ (no lead pipes)

Uniclass Elements:                  Uniclass Elements:
• Ss_25_10_95 (Windows): 4/10       • Ss_25_10_95 (Windows): 8/10 (double glazing)
• Ss_32_20_30 (Flooring): 6/10      • Ss_32_20_30 (Flooring): 9/10 (quality finish)

Energy Rating:                      Energy Rating:
• Class F                           • Average: Class C

                  ↓
        GAP ANALYSIS
        ════════════
        To reach "Fair Market" bracket:
        • Full electrical rewiring (REBT 2002)
        • Replace lead pipes (RD 140/2003)
        • Window upgrade (CTE DB-HE 2019)
        • Expected energy improvement: F → C
```

---

## Compliance Readiness Assessment

### What We CAN and CANNOT Guarantee

| We CAN Provide | We CANNOT Provide |
|----------------|-------------------|
| Visual risk indicators | Official certification |
| Age-based compliance flags | Measurements (room sizes, lux levels) |
| Checklist of likely requirements | Hidden defect detection |
| Remedial action recommendations | Professional sign-off |

### Official Inspections vs Our Assessment

| Inspection Type | Official Requirement | Our Coverage | Gap |
|-----------------|---------------------|--------------|-----|
| **Cédula de Habitabilidad** | Physical inspection by Arquitecto | Visual assessment + age flags | ⚠️ Room dimensions, ventilation calcs |
| **ITE** | On-site inspection by Técnico Competente | Photo analysis of visible elements | ⚠️ Foundations, roof membrane, common areas |
| **Boletín Eléctrico** | Inspection by Instalador Autorizado | Visual triggers for pre-REBT | ⚠️ Load calculation, cable sizing |
| **Certificado Energético** | Energy modeling by Técnico Certificador | Estimated upgrade path | ⚠️ Actual consumption data |

### The Three Compliance Frameworks We Reference

#### 1. Cédula de Habitabilidad (Habitability Certificate)

```
REQUIREMENTS WE CAN ASSESS:
✅ Electrical installation exists and appears modern/old
✅ Plumbing/drainage visible and condition
✅ Water heater type (sealed vs open-flue)
✅ Window condition (single vs double glazing)

REQUIREMENTS WE CANNOT ASSESS:
❌ Minimum room dimensions (requires measurement)
❌ Natural lighting ratio (requires calculation)  
❌ Ventilation adequacy (requires flow measurement)
❌ Gas installation safety (requires certified inspection)
```

#### 2. ITE (Technical Building Inspection)

```
APPLICABLE TO: Buildings over 30-50 years (varies by region)

WHAT WE CAN FLAG:
✅ Visible cracks (with severity estimate)
✅ Damp/moisture stains
✅ Facade condition (from exterior photos if available)
✅ Installation age indicators

WHAT REQUIRES ON-SITE INSPECTION:
❌ Foundation condition
❌ Structural load capacity
❌ Roof waterproofing membrane
❌ Common areas (in apartments)
```

#### 3. REBT (Electrical Regulations)

```
VISUAL INDICATORS OF NON-COMPLIANCE:
✅ Ceramic fuses → Pre-1970s installation
✅ Black/bakelite switches → Pre-1970s
✅ 2-pin sockets (no earth) → Pre-1985
✅ Cloth-covered wiring → Pre-1960s
✅ No differential (RCD) visible → Pre-REBT 2002

TO OBTAIN COMPLIANCE:
→ Full rewiring by Instalador Autorizado
→ Boletín Eléctrico issued
→ Registered with distributor
```

### Compliance Readiness Output Format

```json
{
  "compliance_readiness": {
    "cedula_habitabilidad": {
      "likely_status": "AT_RISK",
      "confidence": "MEDIUM",
      "issues_detected": [
        {
          "requirement": "Electrical Installation Safety",
          "status": "LIKELY_FAIL",
          "evidence": "Ceramic fuses detected (rule ELEC_REBT_001)",
          "regulation": "REBT 2002 (RD 842/2002)",
          "action_required": "Full electrical rewiring + boletín"
        },
        {
          "requirement": "Lead-Free Water Supply",
          "status": "LIKELY_FAIL",
          "evidence": "Grey pipes visible (rule PLUMB_LEAD_001)",
          "regulation": "RD 140/2003",
          "action_required": "Replace lead pipes with PEX/copper"
        }
      ],
      "requires_professional_verification": [
        "Minimum room dimensions (Art. 3.1 Decree 10/2019)",
        "Natural lighting ratio (Art. 4.2)",
        "Ventilation adequacy (CTE DB-HS3)"
      ]
    },
    
    "ite_readiness": {
      "applicable": true,
      "reason": "Building year (1975) > 30 years old",
      "likely_status": "PARTIAL_RISK",
      "issues_detected": [
        {
          "section": "1.3.5 Installations",
          "status": "AT_RISK",
          "evidence": "Pre-2002 electrical, single glazing windows",
          "action_required": "Upgrade before inspection"
        }
      ],
      "cannot_assess_from_photos": [
        "1.3.1 Foundations",
        "1.3.4 Roof waterproofing",
        "Common areas (if apartment building)"
      ]
    },
    
    "rebt_compliance": {
      "likely_status": "NON_COMPLIANT",
      "confidence": "HIGH",
      "visual_evidence": [
        "Ceramic fuses (photo_03.jpg)",
        "2-pin sockets in kitchen (photo_07.jpg)",
        "No visible earth wire at junction box"
      ],
      "path_to_compliance": [
        "1. Hire Instalador Autorizado (registered electrician)",
        "2. Full rewiring with modern consumer unit (cuadro eléctrico)",
        "3. Install RCDs (diferenciales) per circuit",
        "4. Replace all outlets with grounded (schuko) type",
        "5. Install earth system (toma de tierra)",
        "6. Obtain Boletín Eléctrico (electrical certificate)",
        "7. Register installation with distributor"
      ]
    }
  }
}
```

---

## Where Professionals Fit In

### Our System vs Human Experts

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    THE PROFESSIONAL HIERARCHY                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   OUR SYSTEM                                                                  ║
║   ══════════                                                                  ║
║   ┌─────────────────────────────────────────────────────────────┐            ║
║   │  AI VISUAL ANALYSIS + RULES ENGINE                          │            ║
║   │  • Photo-based detection                                     │            ║
║   │  • Age-based compliance flags                                │            ║
║   │  • Gap identification vs market                              │            ║
║   │  • Preliminary scope of work                                 │            ║
║   │                                                              │            ║
║   │  OUTPUT: "Here's what LIKELY needs fixing based on what we   │            ║
║   │           can see. An architect should verify."              │            ║
║   └─────────────────────────────────────────────────────────────┘            ║
║                              │                                                ║
║                              ▼                                                ║
║   ARQUITECTO / ARQUITECTO TÉCNICO                                             ║
║   ═══════════════════════════════                                             ║
║   ┌─────────────────────────────────────────────────────────────┐            ║
║   │  • Physical site visit                                       │            ║
║   │  • Measurements (room sizes, ceiling heights)                │            ║
║   │  • Hidden defect investigation                               │            ║
║   │  • Official project drafting (Proyecto de Reforma)           │            ║
║   │  • License application (if needed)                           │            ║
║   │  • Cédula/ITE report signing                                 │            ║
║   │                                                              │            ║
║   │  OUTPUT: Official documentation with professional liability  │            ║
║   └─────────────────────────────────────────────────────────────┘            ║
║                              │                                                ║
║                              ▼                                                ║
║   SPECIALIST CONTRACTORS                                                      ║
║   ══════════════════════                                                      ║
║   ┌─────────────────────────────────────────────────────────────┐            ║
║   │  Instalador Autorizado (Electrician)                         │            ║
║   │  • Executes electrical work                                  │            ║
║   │  • Issues Boletín Eléctrico                                  │            ║
║   │  • Registers with distributor                                │            ║
║   │                                                              │            ║
║   │  Fontanero (Plumber)                                         │            ║
║   │  • Pipe replacement                                          │            ║
║   │  • Water heater installation                                 │            ║
║   │                                                              │            ║
║   │  Empresa Constructora (General Contractor)                   │            ║
║   │  • Major structural/envelope work                            │            ║
║   │  • Coordinates trades                                        │            ║
║   └─────────────────────────────────────────────────────────────┘            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### How to Explain to a Surveyor/Buyer

> **"How reliable is your AI method?"**

**Answer:**

> "Our system provides a **preliminary condition assessment** based on:
> 
> 1. **Visual AI analysis** of property photos using computer vision
> 2. **Building age** cross-referenced against Spanish regulatory timelines
> 3. **Structured rules engine** mapping 8+ official building codes (REBT, CTE, RITE, etc.)
> 
> We identify **likely issues** and flag properties for professional verification. We explicitly state what we **can** and **cannot** assess from photos.
> 
> **This is NOT a substitute for:**
> - Physical inspection by a qualified Arquitecto/Aparejador
> - Official Cédula de Habitabilidad or ITE reports
> - Boletín Eléctrico from an Instalador Autorizado
> 
> **This IS useful for:**
> - Initial screening and triage (which properties need most work?)
> - Scope estimation before engaging an architect
> - Comparing properties against market standards
> - Identifying likely upgrade paths and cost ranges"

### Professional Integration Points

| Stage | Our System | Architect | Contractor |
|-------|-----------|-----------|------------|
| **Discovery** | ✅ Visual analysis, gap identification | — | — |
| **Verification** | — | ✅ Site visit, measurements | — |
| **Planning** | Scope suggestions | ✅ Official project | — |
| **Licensing** | — | ✅ Permits (if needed) | — |
| **Execution** | — | ✅ Direction | ✅ Work |
| **Certification** | — | ✅ Cédula/ITE sign-off | ✅ Boletín |

---

## Energy Efficiency Loans & Subsidies

### How Our Assessment Affects Financing

Spanish energy efficiency renovation subsidies require **specific documentation** that our assessment can help prepare:

#### 1. PREE (Programa de Rehabilitación Energética de Edificios)

```
REQUIREMENTS:
• Pre-renovation energy certificate (Certificado Energético)
• Proyecto de rehabilitación energética by Arquitecto
• Post-renovation energy certificate showing improvement

HOW WE HELP:
✅ Identify current energy inefficiencies (single glazing, no insulation)
✅ Map upgrade path (CTE DB-HE 2019 compliance)
✅ Estimate expected energy class improvement
✅ Provide preliminary scope for architect to formalize
```

#### 2. ICO Renovation Loans (Next Generation EU Funds)

```
REQUIREMENTS:
• Energy improvement of at least 30% (or 2 letter grades)
• Certified by Técnico Competente
• Registered company performs work

HOW WE HELP:
✅ Pre-screen if property is eligible (enough improvement potential?)
✅ Identify which upgrades have most energy impact:
   - Windows (Ss_25_10_95) → CTE DB-HE compliance
   - Insulation (if visible facade degradation)
   - HVAC (water heater type, heating system)
```

#### 3. Regional Subsidies (Plan Vivienda, etc.)

```
VARIES BY AUTONOMOUS COMMUNITY

Extremadura (Decreto 10/2019):
• Up to 40% subsidy for habitability improvements
• Requires informe técnico previo

HOW WE HELP:
✅ Generate preliminary technical report format
✅ Identify which issues qualify for subsidy
✅ Map to official inspection requirements
```

### Energy Upgrade Path in Comparison

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         ENERGY UPGRADE MAPPING                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   YOUR LISTING: Energy Class F                                                ║
║                                                                               ║
║   COMPARABLES AVERAGE (Fair Market): Energy Class C                           ║
║                                                                               ║
║   GAP ANALYSIS:                                                               ║
║   ─────────────                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │ Element              │ Your Property   │ Target (Class C)   │ Delta │    ║
║   ├──────────────────────┼─────────────────┼───────────────────┼───────┤    ║
║   │ Windows              │ Single glazing  │ Double low-E      │ ⬆️ HIGH │    ║
║   │ (Ss_25_10_95)        │ Aluminum frame  │ PVC/thermal break │        │    ║
║   │                      │                 │                   │        │    ║
║   │ Water Heater         │ Open-flue gas   │ Condensing boiler │ ⬆️ MED  │    ║
║   │ (PLUMB_HEATER_003)   │ or electric     │ or heat pump      │        │    ║
║   │                      │                 │                   │        │    ║
║   │ Facade Insulation    │ None visible    │ SATE/ETICS system │ ⬆️ HIGH │    ║
║   │ (if applicable)      │                 │ 6cm+ EPS          │        │    ║
║   │                      │                 │                   │        │    ║
║   │ Lighting             │ Incandescent/   │ LED throughout    │ ⬆️ LOW  │    ║
║   │                      │ halogen         │                   │        │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   ESTIMATED IMPROVEMENT: F → C/D (2-3 letter grades)                          ║
║   SUBSIDY ELIGIBILITY: ✅ Likely qualifies for PREE (>30% improvement)       ║
║                                                                               ║
║   ⚠️ CAVEAT: Official Certificado Energético required by Técnico Certificador║
║              Our estimate is based on visual indicators only                  ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Data Sources

### Your Listing

| Source | What It Provides | Table |
|--------|------------------|-------|
| `verify_rules.py` | Rule compliance status (confirmed/rejected/not_visible) | `room_rule_verifications` |
| `assess_uniclass.py` | Visible elements + condition scores | `room_uniclass_assessments` |
| Listing data | Energy rating, year built, sqm | `listings` |

### Comparable Properties

| Source | What It Provides | Table |
|--------|------------------|-------|
| Casafari API | Property data, photos, energy ratings | `listing_comparables` |
| `verify_rules.py` | Rule compliance for each comparable | `listing_comparables.rule_verifications` |
| `assess_uniclass.py` | Elements for each comparable | `listing_comparables.uniclass_assessments` |

### Standards Reference

| File | Contents | Usage |
|------|----------|-------|
| `/standards/CTE-DB-HE.txt` | Energy efficiency requirements | Energy upgrade recommendations |
| `/standards/CTE-DB-HS.txt` | Water/sanitation requirements | Plumbing upgrade context |
| `/standards/CTE-DB-HR.txt` | Acoustic requirements | Sound insulation context |
| `rules_engine_v2.json` | Spanish building codes (REBT, etc.) | Rule remediation guidance |

---

## Architecture Diagram

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         MARKET COMPARISON PIPELINE                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  STEP 1: DATA COLLECTION                                                      ║
║  ═══════════════════════                                                      ║
║                                                                               ║
║  ┌─────────────────────────┐         ┌─────────────────────────────────┐     ║
║  │     YOUR LISTING        │         │   COMPARABLES (from Casafari)   │     ║
║  │     (listing_id)        │         │   Already analyzed via:         │     ║
║  ├─────────────────────────┤         │   • verify_rules.py             │     ║
║  │ FROM: room_rule_        │         │   • assess_uniclass.py          │     ║
║  │       verifications     │         ├─────────────────────────────────┤     ║
║  │ • rule_id               │         │ GROUPED BY PRICE BUCKET:        │     ║
║  │ • status (confirmed/    │         │                                 │     ║
║  │   rejected/not_visible) │         │ fast_sell (3 props)             │     ║
║  │ • visual_evidence       │         │   └─ avg_price: €398K           │     ║
║  │                         │         │   └─ rule_verifications[]       │     ║
║  │ FROM: room_uniclass_    │         │   └─ uniclass_assessments[]     │     ║
║  │       assessments       │         │                                 │     ║
║  │ • code (Ss_xx, Pr_xx)   │         │ fair_market (3 props)           │     ║
║  │ • condition (good/      │         │   └─ avg_price: €445K           │     ║
║  │   fair/poor)            │         │   └─ rule_verifications[]       │     ║
║  │                         │         │   └─ uniclass_assessments[]     │     ║
║  │ FROM: listings          │         │                                 │     ║
║  │ • energy_rating         │         │ out_of_market (3 props)         │     ║
║  │ • year_built            │         │   └─ avg_price: €492K           │     ║
║  │ • sqm                   │         │   └─ rule_verifications[]       │     ║
║  └─────────────────────────┘         │   └─ uniclass_assessments[]     │     ║
║             │                         └───────────────┬─────────────────┘     ║
║             │                                         │                       ║
║             └────────────────┬────────────────────────┘                       ║
║                              │                                                ║
║                              ▼                                                ║
║  STEP 2: AGGREGATION                                                          ║
║  ═══════════════════                                                          ║
║                                                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │                    BRACKET AGGREGATION                            │        ║
║  │                    (Python - No Gemini)                           │        ║
║  ├──────────────────────────────────────────────────────────────────┤        ║
║  │  For each bracket (fast_sell, fair_market, out_of_market):       │        ║
║  │                                                                   │        ║
║  │  RULES: Calculate pass_rate per rule                              │        ║
║  │    rule_pass_rates[rule_id] = count(rejected) / total             │        ║
║  │    • "rejected" = concern NOT confirmed = PASSED                  │        ║
║  │    • "confirmed" = concern IS confirmed = FAILED                  │        ║
║  │                                                                   │        ║
║  │  UNICLASS: Calculate presence & avg condition                     │        ║
║  │    element_profiles[code] = {                                     │        ║
║  │      presence_rate: count(present) / total,                       │        ║
║  │      avg_condition: mean(condition_scores)                        │        ║
║  │    }                                                              │        ║
║  │    • condition_scores: good=3, fair=2, poor=1                     │        ║
║  │                                                                   │        ║
║  │  ENERGY: Calculate average rating                                 │        ║
║  │    avg_energy = mean(energy_scores)                               │        ║
║  │    • energy_scores: A=7, B=6, C=5, D=4, E=3, F=2, G=1             │        ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                              │                                                ║
║                              ▼                                                ║
║  STEP 3: GAP ANALYSIS                                                         ║
║  ════════════════════                                                         ║
║                                                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │                    COMPARISON MATRIX                              │        ║
║  │                    (Python - Structured)                          │        ║
║  ├──────────────────────────────────────────────────────────────────┤        ║
║  │  For each bracket, calculate deltas:                              │        ║
║  │                                                                   │        ║
║  │  RULES_DELTA = [                                                  │        ║
║  │    for each rule where:                                           │        ║
║  │      your_status == "confirmed" (you FAIL)                        │        ║
║  │      AND bracket_pass_rate >= 0.67 (2/3 comps PASS)               │        ║
║  │    → GAP IDENTIFIED                                               │        ║
║  │  ]                                                                │        ║
║  │                                                                   │        ║
║  │  UNICLASS_DELTA = [                                               │        ║
║  │    for each element where:                                        │        ║
║  │      bracket_presence_rate >= 0.67 (common element)               │        ║
║  │      AND (you_missing OR your_condition < bracket_avg - 0.5)      │        ║
║  │    → GAP IDENTIFIED                                               │        ║
║  │  ]                                                                │        ║
║  │                                                                   │        ║
║  │  ENERGY_DELTA = {                                                 │        ║
║  │    your_rating vs bracket_avg_rating                              │        ║
║  │    gap_levels = bracket_score - your_score                        │        ║
║  │  }                                                                │        ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                              │                                                ║
║                              ▼                                                ║
║  STEP 4: GEMINI SYNTHESIS                                                     ║
║  ════════════════════════                                                     ║
║                                                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │                         GEMINI                                    │        ║
║  │            (Synthesis & Recommendations ONLY)                     │        ║
║  │            (NO COSTING - that's separate)                         │        ║
║  ├──────────────────────────────────────────────────────────────────┤        ║
║  │  INPUT:                                                           │        ║
║  │    • comparison_matrix (structured JSON)                          │        ║
║  │    • property_context (year, sqm, rooms)                          │        ║
║  │    • cte_context (extracted from /standards/*.txt)                │        ║
║  │                                                                   │        ║
║  │  PROMPT:                                                          │        ║
║  │    "Given these gaps between the listing and market comparables,  │        ║
║  │     recommend specific upgrade actions for each bracket.          │        ║
║  │     Reference CTE standards where applicable.                     │        ║
║  │     DO NOT estimate costs."                                       │        ║
║  │                                                                   │        ║
║  │  OUTPUT (via ResponseSchema):                                     │        ║
║  │    • analysis_summary (severity per category)                     │        ║
║  │    • upgrade_paths (per bracket)                                  │        ║
║  │    • room_recommendations (per room)                              │        ║
║  │    • disclaimers                                                  │        ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                              │                                                ║
║                              ▼                                                ║
║  STEP 5: OUTPUT                                                               ║
║  ══════════════                                                               ║
║                                                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │                    SAVED TO DATABASE                              │        ║
║  │                    (listing_market_comparison)                    │        ║
║  ├──────────────────────────────────────────────────────────────────┤        ║
║  │  • listing_id                                                     │        ║
║  │  • comparison_matrix (JSONB)                                      │        ║
║  │  • gemini_recommendations (JSONB)                                 │        ║
║  │  • created_at                                                     │        ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                              │                                                ║
║                              ▼                                                ║
║  FUTURE STEP: COSTING (Separate Pipeline)                                     ║
║  ═════════════════════════════════════════                                    ║
║                                                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │                    BCCA PRICING LOOKUP                            │        ║
║  │                    (NOT part of this pipeline)                    │        ║
║  ├──────────────────────────────────────────────────────────────────┤        ║
║  │  Takes: upgrade_paths actions                                     │        ║
║  │  Maps: actions → BCCA line items                                  │        ║
║  │  Returns: cost_estimates per action                               │        ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Data Flow

### Phase 1: Data Collection

```python
# 1. Get your listing's analysis
your_listing = {
    "listing_id": 123,
    "year_built": 1975,
    "sqm": 120,
    "energy_rating": "G",
    "price": 320000,
    
    # From room_rule_verifications table
    "rule_verifications": [
        {"room_id": "kitchen_1", "rule_id": "ELEC_PRE_2002", "status": "confirmed", "evidence": "Old fuse box"},
        {"room_id": "kitchen_1", "rule_id": "LEAD_PIPES", "status": "confirmed", "evidence": "Visible joints"},
        {"room_id": "bathroom_1", "rule_id": "NO_GROUND", "status": "not_visible", "evidence": None}
    ],
    
    # From room_uniclass_assessments table
    "uniclass_assessments": [
        {"room_id": "kitchen_1", "code": "Ss_70_30_80", "title": "Small power systems", "condition": "poor"},
        {"room_id": "kitchen_1", "code": "Pr_40_20_87_55", "title": "Mixer taps", "condition": "fair"},
        {"room_id": "bathroom_1", "code": "Ss_45_10_30", "title": "Hot/cold water", "condition": "poor"}
    ]
}

# 2. Get comparables (already analyzed)
comparables = {
    "fast_sell": [comp1, comp2, comp3],      # 3 properties ≤ €398K
    "fair_market": [comp4, comp5, comp6],    # 3 properties €398K-€445K
    "out_of_market": [comp7, comp8, comp9]   # 3 properties > €445K
}
```

### Phase 2: Bracket Aggregation

```python
def aggregate_bracket(comparables: List[Dict]) -> BracketProfile:
    """
    Aggregate 3 comparables into a single bracket profile.
    """
    
    # --- RULES AGGREGATION ---
    rule_results = {}
    for comp in comparables:
        for rule in comp.get("rule_verifications", []):
            rule_id = rule["rule_id"]
            if rule_id not in rule_results:
                rule_results[rule_id] = {"passed": 0, "failed": 0, "unknown": 0}
            
            if rule["status"] == "rejected":
                rule_results[rule_id]["passed"] += 1      # Concern rejected = PASS
            elif rule["status"] == "confirmed":
                rule_results[rule_id]["failed"] += 1      # Concern confirmed = FAIL
            else:
                rule_results[rule_id]["unknown"] += 1     # Not visible
    
    # Calculate pass rates
    rule_pass_rates = {}
    for rule_id, counts in rule_results.items():
        total = counts["passed"] + counts["failed"]
        if total > 0:
            rule_pass_rates[rule_id] = counts["passed"] / total
    
    # --- UNICLASS AGGREGATION ---
    element_data = {}
    for comp in comparables:
        for element in comp.get("uniclass_assessments", []):
            code = element["code"]
            condition = condition_to_score(element["condition"])  # good=3, fair=2, poor=1
            
            if code not in element_data:
                element_data[code] = {"conditions": [], "count": 0}
            
            element_data[code]["conditions"].append(condition)
            element_data[code]["count"] += 1
    
    element_profiles = {}
    for code, data in element_data.items():
        element_profiles[code] = {
            "presence_rate": data["count"] / len(comparables),
            "avg_condition": sum(data["conditions"]) / len(data["conditions"])
        }
    
    # --- ENERGY AGGREGATION ---
    energy_scores = []
    for comp in comparables:
        rating = comp.get("energy_rating")
        if rating:
            energy_scores.append(energy_to_score(rating))
    
    avg_energy_score = sum(energy_scores) / len(energy_scores) if energy_scores else None
    
    return {
        "avg_price": mean([c["sale_price"] for c in comparables]),
        "rule_pass_rates": rule_pass_rates,
        "element_profiles": element_profiles,
        "avg_energy_score": avg_energy_score
    }
```

### Phase 3: Gap Calculation

```python
def calculate_gaps(your_listing: Dict, bracket: BracketProfile) -> GapAnalysis:
    """
    Identify gaps between your listing and the bracket profile.
    """
    gaps = {
        "rules_delta": [],
        "uniclass_delta": [],
        "energy_delta": None
    }
    
    # --- RULES GAPS ---
    your_rules = {r["rule_id"]: r["status"] for r in your_listing["rule_verifications"]}
    
    for rule_id, pass_rate in bracket["rule_pass_rates"].items():
        your_status = your_rules.get(rule_id, "unknown")
        
        # Gap exists if: you FAIL and 2/3+ comparables PASS
        if your_status == "confirmed" and pass_rate >= 0.67:
            gaps["rules_delta"].append({
                "rule_id": rule_id,
                "your_status": "FAIL",
                "bracket_pass_rate": pass_rate,
                "gap_type": "MUST_FIX"
            })
        elif your_status == "confirmed" and pass_rate >= 0.33:
            gaps["rules_delta"].append({
                "rule_id": rule_id,
                "your_status": "FAIL",
                "bracket_pass_rate": pass_rate,
                "gap_type": "CONSIDER_FIX"
            })
    
    # --- UNICLASS GAPS ---
    your_elements = {e["code"]: e for e in your_listing["uniclass_assessments"]}
    
    for code, profile in bracket["element_profiles"].items():
        if profile["presence_rate"] < 0.67:
            continue  # Not a common element in this bracket
        
        your_element = your_elements.get(code)
        
        if not your_element:
            # You're MISSING this element
            gaps["uniclass_delta"].append({
                "code": code,
                "gap_type": "MISSING",
                "your_condition": None,
                "bracket_avg_condition": profile["avg_condition"]
            })
        else:
            your_score = condition_to_score(your_element["condition"])
            if your_score < profile["avg_condition"] - 0.5:
                # Your element is significantly WORSE
                gaps["uniclass_delta"].append({
                    "code": code,
                    "gap_type": "UPGRADE",
                    "your_condition": your_element["condition"],
                    "your_score": your_score,
                    "bracket_avg_condition": profile["avg_condition"]
                })
    
    # --- ENERGY GAP ---
    your_energy = energy_to_score(your_listing.get("energy_rating", "G"))
    bracket_energy = bracket["avg_energy_score"]
    
    if bracket_energy and bracket_energy > your_energy:
        gaps["energy_delta"] = {
            "your_rating": your_listing.get("energy_rating"),
            "your_score": your_energy,
            "bracket_avg_score": bracket_energy,
            "bracket_avg_rating": score_to_energy(round(bracket_energy)),
            "gap_levels": bracket_energy - your_energy
        }
    
    return gaps
```

---

## Comparison Matrix Structure

### Complete Matrix JSON

```json
{
  "listing_id": 123,
  "generated_at": "2026-01-07T18:00:00Z",
  
  "your_listing": {
    "price": 320000,
    "year_built": 1975,
    "sqm": 120,
    "energy_rating": "G",
    "rooms": ["kitchen", "bathroom", "living", "bedroom_1", "bedroom_2"],
    
    "rules_summary": {
      "total_rules_checked": 8,
      "confirmed": 3,
      "rejected": 2,
      "not_visible": 3
    },
    
    "rules": [
      {
        "rule_id": "ELEC_PRE_2002",
        "status": "confirmed",
        "evidence": "Old fuse box visible in kitchen",
        "rooms_affected": ["kitchen"]
      },
      {
        "rule_id": "LEAD_PIPES",
        "status": "confirmed", 
        "evidence": "Visible lead joints under sink",
        "rooms_affected": ["kitchen", "bathroom"]
      },
      {
        "rule_id": "NO_GROUND",
        "status": "not_visible",
        "evidence": null,
        "rooms_affected": []
      }
    ],
    
    "uniclass": [
      {
        "room": "kitchen",
        "code": "Ss_70_30_80",
        "title": "Small power systems",
        "condition": "poor",
        "condition_score": 1
      },
      {
        "room": "kitchen",
        "code": "Pr_40_20_87_55",
        "title": "Mixer taps",
        "condition": "fair",
        "condition_score": 2
      }
    ]
  },
  
  "brackets": {
    "fast_sell": {
      "avg_price": 398000,
      "price_delta": 78000,
      "comparable_count": 3,
      
      "aggregated_rules": {
        "ELEC_PRE_2002": {"pass_rate": 0.33, "passed": 1, "failed": 2},
        "LEAD_PIPES": {"pass_rate": 0.67, "passed": 2, "failed": 1}
      },
      
      "aggregated_uniclass": {
        "Ss_70_30_80": {"presence_rate": 1.0, "avg_condition": 2.0},
        "Pr_40_20_87_55": {"presence_rate": 1.0, "avg_condition": 2.3}
      },
      
      "avg_energy_rating": "F",
      "avg_energy_score": 2.0,
      
      "gaps": {
        "rules_delta": [
          {
            "rule_id": "LEAD_PIPES",
            "your_status": "FAIL",
            "bracket_pass_rate": 0.67,
            "gap_type": "MUST_FIX"
          }
        ],
        "uniclass_delta": [
          {
            "code": "Ss_70_30_80",
            "gap_type": "UPGRADE",
            "your_condition": "poor",
            "bracket_avg_condition": 2.0
          }
        ],
        "energy_delta": {
          "your_rating": "G",
          "bracket_avg_rating": "F",
          "gap_levels": 1
        }
      }
    },
    
    "fair_market": {
      "avg_price": 445000,
      "price_delta": 125000,
      "comparable_count": 3,
      
      "aggregated_rules": {
        "ELEC_PRE_2002": {"pass_rate": 1.0, "passed": 3, "failed": 0},
        "LEAD_PIPES": {"pass_rate": 1.0, "passed": 3, "failed": 0},
        "NO_GROUND": {"pass_rate": 0.67, "passed": 2, "failed": 1}
      },
      
      "aggregated_uniclass": {
        "Ss_70_30_80": {"presence_rate": 1.0, "avg_condition": 2.7},
        "Pr_40_20_87_55": {"presence_rate": 1.0, "avg_condition": 3.0},
        "Pr_35_57_22_14": {"presence_rate": 0.67, "avg_condition": 2.5}
      },
      
      "avg_energy_rating": "C",
      "avg_energy_score": 5.0,
      
      "gaps": {
        "rules_delta": [
          {
            "rule_id": "ELEC_PRE_2002",
            "your_status": "FAIL",
            "bracket_pass_rate": 1.0,
            "gap_type": "MUST_FIX"
          },
          {
            "rule_id": "LEAD_PIPES",
            "your_status": "FAIL",
            "bracket_pass_rate": 1.0,
            "gap_type": "MUST_FIX"
          }
        ],
        "uniclass_delta": [
          {
            "code": "Ss_70_30_80",
            "gap_type": "UPGRADE",
            "your_condition": "poor",
            "bracket_avg_condition": 2.7
          },
          {
            "code": "Pr_35_57_22_14",
            "gap_type": "MISSING",
            "your_condition": null,
            "bracket_avg_condition": 2.5
          }
        ],
        "energy_delta": {
          "your_rating": "G",
          "bracket_avg_rating": "C",
          "gap_levels": 4
        }
      }
    },
    
    "out_of_market": {
      "avg_price": 492000,
      "price_delta": 172000,
      "comparable_count": 3,
      "gaps": { /* similar structure */ }
    }
  }
}
```

---

## Gap Analysis Logic

### Approach: ONE Gemini Call, Qualitative Judgment

Gap analysis is done with **ONE Gemini 3 Pro Preview call** that sees everything together.

**No deterministic thresholds.** Gemini makes qualitative judgments based on the full context.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ONE GEMINI 3 PRO PREVIEW CALL                                              │
│                                                                             │
│  Input (send ALL of this together):                                         │
│  • ALL listing room analyses (rules, uniclass, condition per room)          │
│  • ALL comparable room analyses for the selected bracket                    │
│  • Property context (year built, sqm, energy rating, asking price)          │
│  • Bracket target price                                                     │
│                                                                             │
│  Gemini does:                                                               │
│  • Qualitative comparison - what's actually different?                      │
│  • Room-by-room breakdown with coherent house-level view                    │
│  • Identifies what upgrades matter for THIS bracket                         │
│  • Generates viewing checklist items                                        │
│                                                                             │
│  Benefits:                                                                  │
│  • Sees everything together → coherent recommendations                      │
│  • No magic numbers or arbitrary thresholds                                 │
│  • Can weigh context (1975 vs 2010 building, rural vs urban)               │
│  • Natural language reasoning visible in output                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Output Structure

```python
class GapAnalysisResult:
    rules_gaps: List[RuleGap]       # Rules that fail in listing, pass in comps
    elements_gaps: List[ElementGap]  # Elements worse in listing than comps
    energy_gap: EnergyGap           # Energy rating difference
    viewing_checklist: List[str]    # What to verify in person
    reasoning: str                  # Gemini's qualitative explanation
```

---

## Gemini Integration

### Gap Analysis Prompt

```python
GAP_ANALYSIS_PROMPT = """
You are a Spanish renovation architect comparing a property against market comparables.

## Property Context
- Year Built: {year_built}
- Size: {sqm} m²
- Asking Price: €{asking_price:,}
- Energy Rating: {energy_rating}

## Target Bracket
- Bracket: {bracket} (e.g., fair_market)
- Target Price: €{target_price:,}
- Gap to Target: €{price_gap:,}

## Listing Analysis (ALL ROOMS)
{listing_room_analyses_json}

## Comparable Properties (ALL ROOMS, this bracket only)
{comparable_room_analyses_json}

## Your Task
Compare the listing against these "very good" condition comparables and identify:

1. **Rules Gaps**: Which building code issues exist in the listing but NOT in comparables?
   - Be specific about which rooms and which rules
   - Reference REBT, CTE-DB-HS, CTE-DB-HE where applicable

2. **Elements Gaps**: Which visible elements are worse in the listing?
   - Compare condition levels (poor vs good)
   - Note missing elements that comparables have

3. **Energy Gap**: What's the energy rating difference and what causes it?

4. **Viewing Checklist**: What should be verified in person during a viewing?

Think holistically - you're seeing the whole house, so your recommendations should be coherent.

DO NOT estimate costs - that will be calculated separately.
"""
```

### Gemini Call

```python
from pipeline.gemini_client import call_gemini

response = await call_gemini(
    prompt=prompt,
    model="pro",                          # gemini-3-pro-preview
    temperature=0.3,
    max_tokens=30000,
    response_schema=GAP_ANALYSIS_RESPONSE_SCHEMA,
    response_mime_type="application/json"
)
```

---

## Response Schema

```python
MARKET_COMPARISON_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis_summary": {
            "type": "object",
            "description": "High-level summary of gaps by category",
            "properties": {
                "rules_gap_severity": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high"],
                    "description": "Severity of building code compliance gaps"
                },
                "energy_gap_severity": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high"],
                    "description": "Severity of energy efficiency gap"
                },
                "uniclass_gap_severity": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high"],
                    "description": "Severity of visible finishes gap"
                },
                "overall_assessment": {
                    "type": "string",
                    "description": "2-3 sentence summary of the property's position vs market"
                }
            },
            "required": ["rules_gap_severity", "energy_gap_severity", "uniclass_gap_severity", "overall_assessment"]
        },
        
        "upgrade_paths": {
            "type": "object",
            "description": "Recommended upgrades per price bracket",
            "properties": {
                "fast_sell": {"$ref": "#/$defs/bracket_path"},
                "fair_market": {"$ref": "#/$defs/bracket_path"},
                "out_of_market": {"$ref": "#/$defs/bracket_path"}
            },
            "required": ["fast_sell", "fair_market", "out_of_market"]
        },
        
        "room_recommendations": {
            "type": "array",
            "description": "Room-by-room upgrade recommendations",
            "items": {
                "type": "object",
                "properties": {
                    "room_name": {"type": "string"},
                    "room_type": {"type": "string"},
                    "rules_upgrades": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rule_id": {"type": "string"},
                                "issue_description": {"type": "string"},
                                "recommended_action": {"type": "string"},
                                "standard_reference": {"type": "string"},
                                "priority": {"type": "string", "enum": ["critical", "important", "optional"]}
                            },
                            "required": ["rule_id", "recommended_action", "priority"]
                        }
                    },
                    "energy_upgrades": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "element": {"type": "string"},
                                "current_state": {"type": "string"},
                                "recommended_action": {"type": "string"},
                                "cte_reference": {"type": "string"},
                                "energy_impact": {"type": "string", "enum": ["high", "medium", "low"]}
                            },
                            "required": ["element", "recommended_action", "energy_impact"]
                        }
                    },
                    "uniclass_upgrades": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "uniclass_code": {"type": "string"},
                                "element_name": {"type": "string"},
                                "current_condition": {"type": "string", "nullable": true},
                                "target_condition": {"type": "string"},
                                "recommended_action": {"type": "string"}
                            },
                            "required": ["uniclass_code", "element_name", "recommended_action"]
                        }
                    }
                },
                "required": ["room_name", "room_type"]
            }
        },
        
        "disclaimers": {
            "type": "array",
            "description": "Important caveats about the analysis",
            "items": {"type": "string"}
        }
    },
    "required": ["analysis_summary", "upgrade_paths", "room_recommendations", "disclaimers"],
    
    "$defs": {
        "bracket_path": {
            "type": "object",
            "properties": {
                "target_price": {"type": "integer"},
                "target_description": {"type": "string"},
                "scope_level": {
                    "type": "string",
                    "enum": ["minimal", "moderate", "comprehensive"]
                },
                "rules_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string"},
                            "action": {"type": "string"},
                            "scope": {"type": "string"},
                            "standard_reference": {"type": "string"}
                        },
                        "required": ["rule_id", "action"]
                    }
                },
                "energy_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "element": {"type": "string"},
                            "action": {"type": "string"},
                            "expected_rating_improvement": {"type": "string"}
                        },
                        "required": ["element", "action"]
                    }
                },
                "uniclass_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "element_name": {"type": "string"},
                            "action": {"type": "string"}
                        },
                        "required": ["code", "action"]
                    }
                }
            },
            "required": ["target_description", "scope_level"]
        }
    }
}
```

---

## Database Tables

### New Table: `listing_market_comparison`

```sql
CREATE TABLE listing_market_comparison (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Input data (for audit/debugging)
    comparison_matrix JSONB NOT NULL,         -- Full matrix sent to Gemini
    
    -- Gemini output
    gemini_recommendations JSONB NOT NULL,    -- Structured recommendations
    
    -- Summary fields for quick access
    rules_gap_severity TEXT,                  -- none/low/medium/high
    energy_gap_severity TEXT,
    uniclass_gap_severity TEXT,
    
    -- Metadata
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id)
);

CREATE INDEX idx_market_comparison_listing ON listing_market_comparison(listing_id);
```

---

## API Endpoints

```
GET  /api/renovation/{listing_id}/market-comparison
     → Returns existing comparison if available

POST /api/renovation/{listing_id}/market-comparison
     → Runs comparison pipeline
     → Requires: comparables already fetched
     → Requires: listing already analyzed (rules + uniclass)
```

---

## UI Components

### MarketComparisonCard.tsx

Displays:
1. **Summary badges** - Gap severity per category
2. **Bracket tabs** - fast_sell | fair_market | out_of_market
3. **Upgrade list** - Actions per bracket with room breakdown
4. **Disclaimers** - Professional inspection notices

---

## Disclaimers & Limitations

### The Fundamental Limitation

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        ⚠️ CRITICAL UNDERSTANDING ⚠️                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   WE ANALYZE PHOTOS.                                                          ║
║   A HUMAN INSPECTS WALLS, MEASURES ROOMS, TESTS CIRCUITS.                    ║
║                                                                               ║
║   These are DIFFERENT activities.                                             ║
║                                                                               ║
║   Our output is: "Based on what we can SEE and the building AGE,             ║
║                   here are LIKELY issues that a professional should verify." ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Standard Disclaimers (Include in All Outputs)

| Category | Disclaimer Text |
|----------|-----------------|
| **Visual Limitation** | "This assessment is based on AI analysis of property photographs. It cannot detect issues hidden behind walls, under floors, or in inaccessible areas." |
| **Not a Certification** | "This report does NOT constitute a Cédula de Habitabilidad, ITE, Boletín Eléctrico, or any official certification. Official certificates require physical inspection by licensed professionals." |
| **Professional Required** | "Before purchasing or renovating, we recommend engaging a qualified Arquitecto or Arquitecto Técnico to verify findings and conduct a full site assessment." |
| **Market Comparison** | "Comparable property analysis is based on Casafari market data. Actual market conditions and property-specific factors may result in different valuations." |
| **Regulation Timeline** | "Regulatory compliance is assessed based on building age estimates. Actual requirements depend on the specific date of project approval, which may differ from construction completion." |
| **Cost Estimates** | "Cost estimates (when provided separately) are indicative ranges based on BCCA reference data. Actual costs depend on local contractors, material specifications, and site conditions." |

### Methodology Confidence Levels

```
CONFIDENCE MATRIX

┌─────────────────────────────┬────────────┬─────────────────────────────────────┐
│ What We Assess              │ Confidence │ Why                                 │
├─────────────────────────────┼────────────┼─────────────────────────────────────┤
│ Age-based compliance flags  │ HIGH       │ Regulation dates are definitive     │
│ Visual element detection    │ MEDIUM     │ AI vision accuracy ~85-95%          │
│ Condition scoring           │ MEDIUM     │ Subjective but calibrated           │
│ Energy class estimation     │ LOW-MED    │ Many factors not visible            │
│ Hidden system status        │ LOW        │ Cannot see behind walls             │
│ Structural condition        │ LOW        │ Requires engineering inspection     │
│ Room dimensions             │ NONE       │ Cannot measure from photos          │
└─────────────────────────────┴────────────┴─────────────────────────────────────┘
```

### FAQ: Defending the Methodology

#### Q: "How reliable is your AI method?"

> **A:** "Our system provides preliminary condition assessment, not certification. We combine:
> 
> 1. **Computer vision** - Detecting visual indicators (ceramic fuses, single glazing, etc.)
> 2. **Regulatory knowledge** - 8+ Spanish building codes mapped to visual triggers
> 3. **Market comparison** - Properties in 'very-good' condition as benchmark
> 
> Reliability varies by assessment type:
> - **Age-based flags (e.g., 'pre-REBT 2002')**: Very reliable - based on documented regulation dates
> - **Visual detection (e.g., 'lead pipes visible')**: Depends on photo quality (~85-95% accuracy)
> - **Hidden systems**: We flag likelihood based on age, but cannot confirm without inspection
> 
> We explicitly state what requires professional verification."

#### Q: "Where does an architect fit in?"

> **A:** "We are **pre-architect screening**, not architect replacement.
> 
> | Stage | Our System | Arquitecto |
> |-------|-----------|------------|
> | Initial assessment | ✅ Photo + age analysis | ❌ Not cost-effective for screening |
> | Issue identification | ✅ Likely problems flagged | ✅ Confirmed with physical inspection |
> | Measurements | ❌ Cannot measure | ✅ Required for Cédula, permits |
> | Official project | ❌ Not qualified | ✅ Proyecto de Reforma |
> | Certifications | ❌ Not qualified | ✅ Signs off on Cédula/ITE |
> 
> We help buyers understand **renovation potential** before paying for architect site visits."

#### Q: "How does this affect energy efficiency loan eligibility?"

> **A:** "We identify **potential eligibility** for subsidies like PREE or ICO Next Generation funds, which require:
> 
> 1. **Energy improvement ≥30%** (or 2 letter grades) - We estimate improvement potential
> 2. **Pre/post Certificado Energético** - Must be done by Técnico Certificador
> 3. **Proyecto by Arquitecto** - Official documentation
> 
> Our assessment shows: 'This property appears to have F-rated windows and old heating - improvement potential suggests PREE eligibility, but official energy certificate required.'
> 
> We do NOT issue energy certificates or guarantee subsidy approval."

#### Q: "What if you're wrong about something?"

> **A:** "We operate on a **flag-and-verify** model:
> 
> - We may **flag** an issue that doesn't exist (false positive) → Architect confirms no issue
> - We may **miss** an issue not visible in photos (false negative) → This is why architect verification is mandatory
> 
> Our value is **reducing surprises**, not eliminating them. A €500 photo assessment that identifies 80% of issues before a €50,000 purchase decision is valuable even if imperfect."

#### Q: "What Spanish regulations do you reference?"

> **A:** "Our rules engine explicitly references:
> 
> | Regulation | Code | Our Rules |
> |------------|------|-----------|
> | REBT 2002 | RD 842/2002 | `ELEC_REBT_001`, `ELEC_GROUND_002` |
> | CTE DB-HS | 2006/2019 | Plumbing, waterproofing rules |
> | CTE DB-HE | 2006/2019 | Energy efficiency (windows, insulation) |
> | RD 140/2003 | Lead pipes | `PLUMB_LEAD_001` |
> | RITE 2013 | RD 1027/2007 | Water heater rules |
> | ITE Model | Regional | Structural/damp flags |
> 
> Each rule in our system cites the specific regulation and article number."

---

## Inspection Framework Summary

### How Spanish Property Inspections Work

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SPANISH PROPERTY INSPECTION FRAMEWORK                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   INSPECTION 1: CÉDULA DE HABITABILIDAD                                       ║
║   ═══════════════════════════════════════                                     ║
║                                                                               ║
║   Purpose: Certify dwelling meets minimum habitability conditions             ║
║   Scope: Individual unit (apartment/house)                                    ║
║   Required for: Sale, rental, utility connections (varies by region)          ║
║   Who signs: Arquitecto or Arquitecto Técnico                                 ║
║   Validity: 10-15 years                                                       ║
║                                                                               ║
║   What it checks:                                                             ║
║   ┌───────────────────────────────────────────────────────────────────────┐  ║
║   │ ✅ Water supply exists and functions                                   │  ║
║   │ ✅ Sanitation/drainage connected and working                           │  ║
║   │ ✅ Electrical installation safe (may require boletín)                  │  ║
║   │ ✅ Gas installation safe (if applicable)                               │  ║
║   │ ✅ Ventilation adequate (natural or mechanical)                        │  ║
║   │ ✅ Natural lighting in habitable rooms                                 │  ║
║   │ ✅ Minimum room dimensions met                                         │  ║
║   │ ✅ Basic security provisions                                           │  ║
║   └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────────┐║
║   │ OUR COVERAGE: We flag likely issues in electrical, plumbing, windows.  │║
║   │ We CANNOT measure room dimensions or calculate lighting ratios.        │║
║   └─────────────────────────────────────────────────────────────────────────┘║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   INSPECTION 2: ITE (Inspección Técnica de Edificios)                        ║
║   ════════════════════════════════════════════════════                        ║
║                                                                               ║
║   Purpose: Assess building conservation state                                 ║
║   Scope: Entire building (common elements + structure)                        ║
║   Required for: Buildings over 30-50 years (varies by region)                 ║
║   Who signs: Arquitecto or Arquitecto Técnico                                 ║
║   Validity: 10 years                                                          ║
║                                                                               ║
║   What it checks:                                                             ║
║   ┌───────────────────────────────────────────────────────────────────────┐  ║
║   │ 1.3.1 FOUNDATIONS - Settlement, cracks, dampness                       │  ║
║   │ 1.3.2 STRUCTURE - Beams, columns, slabs, load-bearing walls            │  ║
║   │ 1.3.3 FACADES & PARTY WALLS - Condition, weatherproofing               │  ║
║   │ 1.3.4 ROOFS & TERRACES - Waterproofing, drainage                       │  ║
║   │ 1.3.5 INSTALLATIONS - Electrical, plumbing, gas, elevators             │  ║
║   └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║   Rating system:                                                              ║
║   • FAVORABLE - No significant issues                                         ║
║   • FAVORABLE CON DEFICIENCIAS LEVES - Minor issues, no deadline             ║
║   • DESFAVORABLE - Deficiencies requiring repair within deadline              ║
║   • MUY DESFAVORABLE - Immediate intervention required                        ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────────┐║
║   │ OUR COVERAGE: We flag visible cracks, damp, installation age.          │║
║   │ We CANNOT inspect foundations, roof membranes, or common areas.        │║
║   └─────────────────────────────────────────────────────────────────────────┘║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   CERTIFICATION 3: BOLETÍN ELÉCTRICO                                         ║
║   ══════════════════════════════════                                          ║
║                                                                               ║
║   Purpose: Certify electrical installation is safe and REBT-compliant         ║
║   Scope: Entire electrical installation in a dwelling                         ║
║   Required for: New contracts with distributor, after rewiring                ║
║   Who signs: Instalador Autorizado (licensed electrician)                     ║
║                                                                               ║
║   What it certifies:                                                          ║
║   ┌───────────────────────────────────────────────────────────────────────┐  ║
║   │ ✅ Consumer unit (cuadro) with modern circuit breakers                 │  ║
║   │ ✅ Differential switches (RCDs) per circuit                            │  ║
║   │ ✅ Earth system (toma de tierra) installed and tested                  │  ║
║   │ ✅ Grounded outlets (schuko type) throughout                           │  ║
║   │ ✅ Cable sizing appropriate for load                                   │  ║
║   │ ✅ Proper circuit separation (lighting, power, dedicated)              │  ║
║   └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────────┐║
║   │ OUR COVERAGE: We detect visual indicators (old fuses, 2-pin sockets).  │║
║   │ We CANNOT test circuits, measure loads, or verify earth resistance.    │║
║   └─────────────────────────────────────────────────────────────────────────┘║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   CERTIFICATION 4: CERTIFICADO DE EFICIENCIA ENERGÉTICA                      ║
║   ══════════════════════════════════════════════════════                      ║
║                                                                               ║
║   Purpose: Rate building energy efficiency (A to G scale)                     ║
║   Scope: Entire dwelling                                                      ║
║   Required for: Sale, rental, applying for energy subsidies                   ║
║   Who signs: Técnico Certificador (qualified energy assessor)                 ║
║   Validity: 10 years                                                          ║
║                                                                               ║
║   What it assesses:                                                           ║
║   ┌───────────────────────────────────────────────────────────────────────┐  ║
║   │ • Building envelope (walls, roof, floor U-values)                      │  ║
║   │ • Windows (glazing type, frame thermal break)                          │  ║
║   │ • HVAC system efficiency                                               │  ║
║   │ • Hot water system                                                     │  ║
║   │ • Lighting (in non-residential)                                        │  ║
║   │ → Calculates kWh/m²/year → Assigns letter grade (A best, G worst)     │  ║
║   └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────────┐║
║   │ OUR COVERAGE: We detect visible indicators (window type, heater type). │║
║   │ We CANNOT calculate U-values or model energy consumption.              │║
║   └─────────────────────────────────────────────────────────────────────────┘║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Our Role in the Inspection Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PROPERTY DISCOVERY FLOW                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   STAGE 1: DISCOVERY (We provide information)                                   │
│   ═══════════════════════════════════════════                                   │
│                                                                                 │
│   Buyer sees properties on Idealista                                            │
│   ↓                                                                             │
│   Agent provides: Renovation potential analysis via Puedo Casa                  │
│   ↓                                                                             │
│   Output: "Renovation cost ~€49k, comparable value ~€445k, timeline ~10 weeks"  │
│   ↓                                                                             │
│   Buyer understands renovation potential before viewing                         │
│                                                                                 │
│   VALUE: Buyers can "window shop" renovation potential instantly                │
│                                                                                 │
│   ─────────────────────────────────────────────────────────────────────────────│
│                                                                                 │
│   STAGE 2: VERIFICATION (Architect does this)                                   │
│   ═══════════════════════════════════════════                                   │
│                                                                                 │
│   Architect visits shortlisted properties                                       │
│   ↓                                                                             │
│   Physical inspection: Measurements, hidden areas, structural assessment        │
│   ↓                                                                             │
│   Confirms/refutes our flags + discovers issues we couldn't see                 │
│   ↓                                                                             │
│   Provides renovation scope and official project (if proceeding)                │
│                                                                                 │
│   VALUE: Architect time focused on serious candidates only                      │
│                                                                                 │
│   ─────────────────────────────────────────────────────────────────────────────│
│                                                                                 │
│   STAGE 3: EXECUTION (Contractors + Certifiers)                                 │
│   ═════════════════════════════════════════════                                 │
│                                                                                 │
│   Instalador Autorizado → Electrical work + Boletín                             │
│   Fontanero cualificado → Plumbing work                                         │
│   Empresa constructora → Major works                                            │
│   ↓                                                                             │
│   Arquitecto signs off on completed work                                        │
│   ↓                                                                             │
│   Applications submitted: Cédula, ITE update, energy certificate                │
│                                                                                 │
│   VALUE: Work done correctly, certifications obtained                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### The "Very Good Condition" Standard

When we compare against Casafari's "very-good" condition properties, we're benchmarking against properties that:

1. **Have valid Cédula** (or equivalent) - They can be legally sold/rented
2. **Would pass ITE** (if applicable) - No major conservation issues
3. **Have compliant installations** - Modern enough to not trigger red flags
4. **Have good energy efficiency** - Typically C-D rating or better
5. **Have quality finishes** - Visible indicators of recent renovation

Our comparison asks: **"What gap exists between your property and these standards?"**

```
YOUR PROPERTY (as-is)          GAP ANALYSIS              "VERY GOOD" STANDARD
═══════════════════════        ════════════              ════════════════════

Cédula: At Risk                →  Electrical rewiring    Cédula: Valid
(old electrical, lead pipes)      Pipe replacement

ITE: At Risk                   →  Window replacement     ITE: Favorable
(single glazing, visible damp)    Damp treatment

Energy: F                      →  Insulation + windows   Energy: C
                                  Heat pump

Finishes: Fair (6/10)          →  Kitchen/bath upgrade   Finishes: Very Good (8/10)
```

---

## Stage 4: Pricing with KGEstimator

### What KGEstimator Does

The KGEstimator (`experiments/renovation_costing/kg_estimator.py`) is a Knowledge Graph-powered pricing engine that converts scope items into professional Spanish construction budgets.

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      KG ESTIMATOR PIPELINE                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  INPUT: Scope items from gap analysis                                         ║
║  ═══════════════════════════════════                                          ║
║  [                                                                            ║
║    "Full electrical rewiring (REBT 2002 compliance)",                         ║
║    "Replace lead pipes with PEX",                                             ║
║    "Window upgrade to double glazing"                                         ║
║  ]                                                                            ║
║                                                                               ║
║  STEP 1: INTENT EXTRACTION (Gemini)                                           ║
║  ─────────────────────────────────                                            ║
║  "Full electrical rewiring" → room: general, intents: [instalación eléctrica] ║
║                                                                               ║
║  STEP 2: KG TASK MATCHING (Semantic Search)                                   ║
║  ─────────────────────────────────────────                                    ║
║  Intent "instalación eléctrica" → Task: "T_ELEC_REWIRE"                       ║
║  Similarity: 0.87                                                             ║
║                                                                               ║
║  STEP 3: DEPENDENCY INJECTION (Knowledge Graph Edges)                         ║
║  ────────────────────────────────────────────────────                         ║
║  T_ELEC_REWIRE requires:                                                      ║
║    → T_DEMO_CHANNELS (rozas para cableado)                                    ║
║    → T_PROTECT_FLOORS (protección suelos)                                     ║
║  T_ELEC_REWIRE triggers:                                                      ║
║    → T_PATCH_PLASTER (enlucido rozas)                                         ║
║    → T_DISPOSAL (gestión residuos)                                            ║
║                                                                               ║
║  STEP 4: VARIANT RESOLUTION (Room Context)                                    ║
║  ─────────────────────────────────────────                                    ║
║  T_ELEC_REWIRE + room: cocina → bcca_keyword: "instalación eléctrica cocina"  ║
║  T_ELEC_REWIRE + room: baño → bcca_keyword: "instalación eléctrica baño"     ║
║                                                                               ║
║  STEP 5: BCCA SEARCH (Semantic Match to Price Database)                       ║
║  ─────────────────────────────────────────────────────                        ║
║  bcca_keyword: "instalación eléctrica cocina"                                 ║
║  → BCCA Code: E1234 "Instalación eléctrica completa cocina" | €1,850/ud       ║
║                                                                               ║
║  STEP 6: BOQ GENERATION (Gemini with Quantities)                              ║
║  ───────────────────────────────────────────────                              ║
║  LLM calculates quantities based on dimensions (from listing or defaults)     ║
║  Generates professional Bill of Quantities                                    ║
║                                                                               ║
║  STEP 7: SPANISH PRICING STRUCTURE                                            ║
║  ─────────────────────────────────                                            ║
║  ┌────────────────────────────────────────────────────────────┐              ║
║  │ PEM (Presupuesto Ejecución Material):    €12,450.00        │              ║
║  │ + GG 13% (Gastos Generales):              €1,618.50        │              ║
║  │ + BI 6% (Beneficio Industrial):             €747.00        │              ║
║  │ ═══════════════════════════════════════════════════════    │              ║
║  │ PEC (Presupuesto Ejecución Contrata):    €14,815.50        │              ║
║  │ + IVA 21%:                                €3,111.26        │              ║
║  │ ═══════════════════════════════════════════════════════    │              ║
║  │ TOTAL:                                   €17,926.76        │              ║
║  └────────────────────────────────────────────────────────────┘              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### KGEstimator Components

| Component | Description | Data Source |
|-----------|-------------|-------------|
| **Knowledge Graph** | 683 tasks, 2789 dependency edges | `hybrid_renovation_graph.json` |
| **BCCA Database** | Spanish construction price book | `construction.db` (SQLite) |
| **Sentence Transformer** | Semantic search embeddings | `paraphrase-multilingual-MiniLM-L12-v2` |
| **Room-Task Matrix** | Room-specific task variants | Part of KG JSON |
| **Resolved Keywords** | Room-specific BCCA search terms | Part of KG JSON |

### Integration with Gap Analysis

```python
# In compare_to_market.py

from experiments.renovation_costing.kg_estimator import KGEstimator

async def price_upgrade_path(gap_analysis: dict, listing_sqm: float) -> dict:
    """Convert gap analysis scope into priced BoQ."""
    
    estimator = KGEstimator()
    
    priced_brackets = {}
    
    for bracket_name, gaps in gap_analysis["brackets"].items():
        scope_items = []
        
        # Convert rules gaps to scope items
        for rule_gap in gaps["rules_delta"]:
            if rule_gap["gap_type"] == "MUST_FIX":
                # Get remedial action from rules engine
                rule = rules_engine[rule_gap["rule_id"]]
                scope_items.append({
                    "description": rule["remedial_action"]["task_id"],
                    "bcca_keyword": rule["remedial_action"]["bcca_keyword"],
                    "category": rule["remedial_action"]["category"]
                })
        
        # Convert uniclass gaps to scope items
        for element_gap in gaps["uniclass_delta"]:
            if element_gap["gap_type"] in ["UPGRADE", "MISSING"]:
                scope_items.append({
                    "description": f"Upgrade {element_gap['code']} to market standard",
                    "bcca_keyword": uniclass_to_bcca_mapping.get(element_gap["code"]),
                    "category": "FINISHES"
                })
        
        # Convert energy gap to scope items
        if gaps.get("energy_delta"):
            scope_items.extend(get_energy_upgrade_items(gaps["energy_delta"]))
        
        # Price each scope item with KGEstimator
        priced_items = []
        for item in scope_items:
            query = f"{item['description']} para vivienda de {listing_sqm}m2"
            result = estimator.estimate(query)
            priced_items.append({
                "scope_item": item,
                "boq_lines": [asdict(line) for line in result.boq_lines],
                "pem": result.pem_subtotal,
                "total_with_iva": result.total_with_iva
            })
        
        priced_brackets[bracket_name] = {
            "priced_items": priced_items,
            "total_pem": sum(p["pem"] for p in priced_items),
            "total_with_iva": sum(p["total_with_iva"] for p in priced_items)
        }
    
    return priced_brackets
```

### Example Output

```json
{
  "fair_market": {
    "price_gap_to_reach": 125000,
    "renovation_cost_estimate": {
      "pem": 45780.00,
      "overhead_19pct": 8698.20,
      "pec": 54478.20,
      "iva_21pct": 11440.42,
      "total_with_iva": 65918.62
    },
    "boq_summary": [
      {
        "category": "ELECTRICAL",
        "items": 4,
        "subtotal": 12450.00,
        "tasks": ["Full rewiring", "New consumer unit", "Earth system", "Socket upgrade"]
      },
      {
        "category": "PLUMBING",
        "items": 3,
        "subtotal": 8750.00,
        "tasks": ["Lead pipe replacement", "Hot water system", "Bathroom fixtures"]
      },
      {
        "category": "ENVELOPE",
        "items": 2,
        "subtotal": 18500.00,
        "tasks": ["Window replacement (8 units)", "Thermal bridge correction"]
      },
      {
        "category": "FINISHES",
        "items": 5,
        "subtotal": 6080.00,
        "tasks": ["Kitchen cabinets", "Bathroom tiles", "Flooring", "Paint", "Doors"]
      }
    ],
    "totals": {
      "renovation_cost": 65918.62,
      "comparable_value_increase": 125000,
      "notes": "Based on comparable properties in 'very good' condition"
    }
  }
}
```

### Why This Approach Works

1. **Professional Standards**: Uses actual BCCA codes (Spanish standard price book)
2. **Dependency Awareness**: KG knows "if you rewire, you need patching"
3. **Room Context**: Kitchen tiling has different spec than bathroom
4. **Complete Pricing**: Includes 19% overhead + 21% IVA (Spanish standard)
5. **Auditable**: Every line item has BCCA code and unit price

### Limitations

| What We Provide | What We Don't |
|----------------|---------------|
| Indicative budget range | Fixed-price quote |
| BCCA reference prices | Contractor negotiated prices |
| Standard quantities | Site-specific quantities |
| Typical specifications | Custom material choices |

---

## Implementation Checklist

> **Updated 2026-01-08**: Simplified to match the actual "Analyse" flow.

### What "Analyse" Does (The Full Pipeline)

When user clicks **Analyse** on a bracket above asking price:

```
1. SCOPE OF WORK  ← From verify_rules + assess_uniclass (detected conditions)
2. PRICING        ← KGEstimator prices scope items from BCCA
3. TIMELINE       ← Gemini estimates from BoQ complexity
4. IMAGES         ← V1-V4 pipeline (defurnish → select → prompt → render)
5. EXPORT         ← Button generates architect PDF
```

### Core Infrastructure ✅ DONE

| Component | File | Status |
|-----------|------|--------|
| Casafari API client | `casafari_client.py` | ✅ |
| Database tables | `009_comparables_tables.sql` | ✅ |
| API endpoints | `renovation.py` (4 routes) | ✅ |
| ComparablesCard UI | `ComparablesCard.tsx` | ✅ |
| State machine | initial → brackets → analysing → options | ✅ |
| Dual view (Raw/Filtered) | In UI | ✅ |
| "Analyse All" button | In UI | ✅ |

### Per-Bracket Analysis Pipeline

| Step | What | Current State | TODO |
|------|------|---------------|------|
| **1. Scope** | Detected conditions → work items | ⚠️ Placeholder | Wire up verify_rules + assess_uniclass results |
| **2. Pricing** | KGEstimator → BCCA line items | ⚠️ Heuristic | Integrate KGEstimator |
| **3. Timeline** | Gemini → phase breakdown | ⚠️ Estimate | Call Gemini with BoQ |
| **4. Images** | V1→V2→V3→V4 visuals | ❌ Not wired | Call `run_v1_defurnish` → `run_v2_select` → `run_v3_prompts` → `run_v4_render` |
| **5. Export** | Generate architect PDF | ❌ Not built | Implement `GET /{id}/handover?format=pdf` |

### Deleted (Old Code to Remove)
- ~~Section3FeasiblePaths.tsx~~ - Replaced by ComparablesCard
- ~~feasible-paths API route~~ - No longer needed
- ~~TierModal.tsx~~ - Replaced by RenovationOptionCard
- ~~tier_assessment, tier_designs, final_scope tables~~ - Replaced by listing_bracket_analyses

---

## CTE-Grounded Energy Assessment

### Source Documents (In Our Standards Folder)

All energy calculations MUST reference these actual files:

| File | Path | Contents |
|------|------|----------|
| **CTE-DB-HE** | `/standards/CTE-DB-HE.txt` | Full energy efficiency code |
| **CTE-DB-HS** | `/standards/CTE-DB-HS.txt` | Health/hygiene requirements |
| **Decreto 10/2019** | `/standards/decreto-10-2019-extremadura.txt` | Cédula requirements (Extremadura) |
| **ITE Model** | `/standards/modelo-informe-ite.txt` | Technical inspection format |
| **Rules Engine** | `/backend/pipeline/rules_engine_v2.json` | Visual triggers → regulations |

### CTE-DB-HE Official Tables (Extracted from Our File)

#### Table 3.1.a-HE0: Energy Consumption Limits (kWh/m²/year)

*Source: `/standards/CTE-DB-HE.txt` lines 511-554*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                VALOR LÍMITE Cep,nren,lim [kWh/m²·año]                       │
│                       USO RESIDENCIAL PRIVADO                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ZONA CLIMÁTICA DE INVIERNO                          │
│                    α      A      B      C      D      E                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Edificios nuevos    20     25     28     32     38     43                   │
│ y ampliaciones                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Cambios de uso      40     50     55     65     70     80                   │
│ y reformas                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
  
  Note: In Balearic Islands, Canaries, Ceuta, Melilla → multiply by 1.25
```

#### Table 3.1.1.a-HE1: U-Value Limits (Maximum Allowed)

*Source: `/standards/CTE-DB-HE.txt` lines 1083-1139*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              VALORES LÍMITE DE TRANSMITANCIA TÉRMICA, Ulim [W/m²K]          │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ZONA CLIMÁTICA DE INVIERNO                          │
│ Elemento                      α     A     B     C     D     E               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Muros y suelos               0.80  0.70  0.56  0.49  0.41  0.37             │
│ (contacto exterior)                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Cubiertas                    0.55  0.50  0.44  0.40  0.35  0.33             │
│ (contacto exterior)                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Muros/suelos/cubiertas       0.90  0.80  0.75  0.70  0.65  0.59             │
│ (terreno o no habitable)                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Huecos (ventanas)            3.20  2.70  2.30  2.10  1.80  1.80             │
│ (marco+vidrio+cajón)                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Puertas (<50% vidrio)        5.70  5.70  5.70  5.70  5.70  5.70             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Table a-Anejo E: Orientative U-Values for Compliance

*Source: `/standards/CTE-DB-HE.txt` lines 3915-3960*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│         TRANSMITANCIA TÉRMICA ORIENTATIVA DEL ELEMENTO, U [W/m²K]           │
│                  (Para cumplir coeficiente K global)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ZONA CLIMÁTICA DE INVIERNO                          │
│ Elemento                      α     A     B     C     D     E               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Muros y suelos               0.56  0.50  0.38  0.29  0.27  0.23             │
│ (contacto exterior)                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Cubiertas                    0.50  0.44  0.33  0.23  0.22  0.19             │
│ (contacto exterior)                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Terreno/no habitable         0.80  0.80  0.69  0.48  0.48  0.48             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Huecos (ventanas)            2.70  2.70  2.00  2.00  1.60  1.50             │
└─────────────────────────────────────────────────────────────────────────────┘

  Note: "Los valores anteriores presuponen un correcto tratamiento de los 
         puentes térmicos." (CTE-DB-HE Anejo E)
```

#### Table a-Anejo B: Climate Zones by Province

*Source: `/standards/CTE-DB-HE.txt` lines 3217-3535*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ZONAS CLIMÁTICAS POR PROVINCIA                           │
│                        (altitud ≤50m sobre nivel del mar)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Provincia          │ Zona   │ Provincia          │ Zona                     │
├────────────────────┼────────┼────────────────────┼──────────────────────────┤
│ Valencia           │ B3     │ Madrid             │ D3                       │
│ Barcelona          │ C2     │ Sevilla            │ B4                       │
│ Málaga             │ A3     │ Alicante           │ B4                       │
│ Zaragoza           │ D3     │ Bilbao/Bizkaia     │ C1                       │
│ Murcia             │ B3     │ Palmas, Las        │ α3                       │
│ Baleares           │ B3     │ Tenerife           │ α3                       │
│ Granada            │ C3     │ Asturias           │ C1                       │
└─────────────────────────────────────────────────────────────────────────────┘

  Format: [Winter Zone][Summer Zone]
  Winter: α (mildest) < A < B < C < D < E (coldest)
  Summer: 1 (mildest) < 2 < 3 < 4 (hottest)
```

### Our Estimation Methodology

#### Step 1: Determine Climate Zone from GPS

```python
# In our pipeline - MUST implement this lookup
def get_climate_zone(lat: float, lng: float) -> str:
    """
    Get CTE climate zone from coordinates.
    
    Source: CTE-DB-HE Anejo B (lines 3217-3535 in /standards/CTE-DB-HE.txt)
    
    Returns: Zone string like "B3", "D3", "C2"
    """
    # TODO: Implement province lookup from coordinates
    # Then apply altitude correction per Anejo B tables
    pass
```

#### Step 2: Estimate Current U-Values from Building Age + Visual Evidence

```python
# Historical U-values by construction era (estimated from typical practices)
# These are NOT from CTE - they are our estimates of what buildings had BEFORE regulations

HISTORICAL_U_VALUES = {
    # Pre-NBE-CT 79 (before 1979) - NO thermal regulations existed
    "pre_1979": {
        "walls": 2.5,      # Solid brick, no insulation
        "windows": 5.7,    # Single glazing, metal frame (CTE limit for doors)
        "roof": 2.0        # Uninsulated flat roof
    },
    
    # NBE-CT 79 era (1979-2006) - First thermal regs, minimal insulation
    "1979_2006": {
        "walls": 1.4,      # Some cavity insulation
        "windows": 3.5,    # Still mostly single glazing
        "roof": 1.0        # Basic insulation
    },
    
    # CTE 2006 era (2006-2019) - Modern requirements
    "2006_2019": {
        "walls": 0.73,     # Per CTE-DB-HE 2006
        "windows": 2.7,    # Double glazing standard
        "roof": 0.5
    },
    
    # CTE 2019+ (current) - Strictest requirements
    "post_2019": {
        "walls": 0.41,     # Per Table 3.1.1.a-HE1 zone D
        "windows": 1.8,    # Per Table 3.1.1.a-HE1 zone D
        "roof": 0.35
    }
}

# Visual detection overrides - from photos we can CONFIRM certain elements
VISUAL_U_VALUE_ESTIMATES = {
    # Window detection from photos (rules_engine_v2.json: ENV_WIN_001)
    "single_glazing_aluminum": 5.7,    # Worst case (CTE door limit)
    "single_glazing_wood": 4.5,
    "double_glazing_aluminum": 3.0,    # No thermal break
    "double_glazing_pvc": 2.0,         # With thermal break
    "double_glazing_low_e": 1.4,       # Low-E coating
    "triple_glazing": 0.8
}
```

#### Step 3: Calculate Heat Loss Reduction from Upgrades

```python
def calculate_window_upgrade_savings(
    window_area_m2: float,
    current_u: float,      # Estimated from age/visual
    target_u: float,       # CTE requirement for zone
    climate_zone: str,     # e.g., "B3"
    floor_area_m2: float
) -> dict:
    """
    Calculate energy savings from window upgrade.
    
    Based on CTE-DB-HE simplified method:
    Heat loss Q = U × A × ΔT × time
    
    For annual estimation, we use degree-days (DD) approximation.
    
    Returns dict with savings and CTE references.
    """
    # Degree-days by winter zone (approximate values for heating season)
    # Source: Derived from CTE climate data files
    DEGREE_DAYS = {
        "α": 600, "A": 900, "B": 1200, 
        "C": 1500, "D": 1800, "E": 2100
    }
    
    winter_zone = climate_zone[0]  # First letter is winter zone
    dd = DEGREE_DAYS.get(winter_zone, 1200)
    
    # Heat loss per m² floor area (kWh/m²·year)
    # Formula: U × window_area × DD × 24h / 1000 / floor_area
    current_loss = current_u * window_area_m2 * dd * 24 / 1000 / floor_area_m2
    target_loss = target_u * window_area_m2 * dd * 24 / 1000 / floor_area_m2
    savings = current_loss - target_loss
    
    return {
        "intervention": "Window upgrade",
        "element": "Huecos (UH)",
        "current_u": current_u,
        "target_u": target_u,
        "cte_limit": get_cte_limit("windows", winter_zone),  # From Table 3.1.1.a
        "cte_orientative": get_cte_orientative("windows", winter_zone),  # From Anejo E
        "area_m2": window_area_m2,
        "estimated_savings_kwh_m2_year": round(savings, 1),
        "cte_reference": "CTE-DB-HE Table 3.1.1.a-HE1",
        "calculation_method": "Simplified degree-day method",
        "disclaimer": "Actual savings depend on usage patterns and building specifics"
    }

def get_cte_limit(element: str, winter_zone: str) -> float:
    """
    Get U-value limit from Table 3.1.1.a-HE1.
    Source: /standards/CTE-DB-HE.txt lines 1083-1139
    """
    LIMITS = {
        "walls": {"α": 0.80, "A": 0.70, "B": 0.56, "C": 0.49, "D": 0.41, "E": 0.37},
        "roof": {"α": 0.55, "A": 0.50, "B": 0.44, "C": 0.40, "D": 0.35, "E": 0.33},
        "windows": {"α": 3.20, "A": 2.70, "B": 2.30, "C": 2.10, "D": 1.80, "E": 1.80}
    }
    return LIMITS.get(element, {}).get(winter_zone, 2.0)

def get_cte_orientative(element: str, winter_zone: str) -> float:
    """
    Get orientative U-value from Anejo E.
    Source: /standards/CTE-DB-HE.txt lines 3915-3960
    """
    ORIENTATIVE = {
        "walls": {"α": 0.56, "A": 0.50, "B": 0.38, "C": 0.29, "D": 0.27, "E": 0.23},
        "roof": {"α": 0.50, "A": 0.44, "B": 0.33, "C": 0.23, "D": 0.22, "E": 0.19},
        "windows": {"α": 2.70, "A": 2.70, "B": 2.00, "C": 2.00, "D": 1.60, "E": 1.50}
    }
    return ORIENTATIVE.get(element, {}).get(winter_zone, 2.0)
```

---

## Architect Handover Export

### Purpose

When a user has completed the analysis pipeline, we generate a **professional handover document** that:

1. Summarizes all findings with evidence
2. Provides CTE-grounded recommendations
3. Clearly states what requires professional verification
4. Includes annotated photos
5. Is suitable for giving to an architect before their site visit

### Export Format

#### JSON Schema for Handover Data

```json
{
  "meta": {
    "generated_at": "2026-01-07T18:00:00Z",
    "listing_id": 12345,
    "listing_url": "https://idealista.com/inmueble/12345678",
    "puedo_casa_version": "1.0.0",
    "disclaimer": "This is a preliminary visual assessment. Physical inspection by a qualified Arquitecto or Arquitecto Técnico is required for certification."
  },
  
  "property": {
    "address": "Calle Example 123, 46001 Valencia",
    "coordinates": {"lat": 39.4699, "lng": -0.3763},
    "listed_price": 320000,
    "floor_area_m2": 95,
    "year_built": 1975,
    "year_source": "listing_description",
    "bedrooms": 3,
    "bathrooms": 1,
    "energy_rating": "G",
    "energy_source": "listing",
    "property_type": "apartment",
    "floor": 3,
    "building_floors": 6
  },
  
  "climate_context": {
    "province": "Valencia",
    "climate_zone": "B3",
    "winter_zone": "B",
    "summer_zone": "3",
    "cte_reference": "CTE-DB-HE Anejo B (Table a-Anejo B)",
    "source_file": "/standards/CTE-DB-HE.txt lines 3217-3535"
  },
  
  "rules_assessment": {
    "total_rules_checked": 15,
    "confirmed_issues": 4,
    "rejected_issues": 3,
    "not_visible": 8,
    
    "issues": [
      {
        "rule_id": "ELEC_REBT_001",
        "status": "confirmed",
        "system": "electrical",
        "evidence": {
          "description": "Ceramic fuses visible in consumer unit",
          "photo_refs": ["photo_07.jpg"],
          "confidence": "high"
        },
        "regulation": {
          "code": "REBT 2002",
          "legal_ref": "RD 842/2002",
          "requirement": "Modern consumer unit with RCDs required"
        },
        "risk": {
          "label": "Non-Compliant",
          "description": "Installation predates current safety standards",
          "affects_cedula": true,
          "affects_ite": true
        },
        "remediation": {
          "action": "Full electrical rewiring",
          "bcca_keyword": "instalación eléctrica vivienda completa",
          "requires_boletin": true,
          "typical_duration_days": "5-7"
        }
      },
      {
        "rule_id": "PLUMB_LEAD_001",
        "status": "confirmed",
        "system": "plumbing",
        "evidence": {
          "description": "Grey lead pipes visible under kitchen sink",
          "photo_refs": ["photo_09.jpg"],
          "confidence": "high"
        },
        "regulation": {
          "code": "RD 140/2003",
          "legal_ref": "Real Decreto 140/2003",
          "requirement": "Lead pipes prohibited in potable water supply"
        },
        "risk": {
          "label": "Health Hazard",
          "description": "Lead contamination risk in water supply",
          "affects_cedula": true,
          "affects_ite": true
        },
        "remediation": {
          "action": "Replace lead pipes with PEX or copper",
          "bcca_keyword": "sustitución tubería plomo agua",
          "typical_duration_days": "2-3"
        }
      },
      {
        "rule_id": "ENV_WIN_001",
        "status": "confirmed",
        "system": "envelope",
        "evidence": {
          "description": "Aluminum sliding windows, single glazing visible",
          "photo_refs": ["photo_03.jpg", "photo_12.jpg", "photo_18.jpg"],
          "confidence": "high"
        },
        "regulation": {
          "code": "CTE-DB-HE",
          "legal_ref": "Table 3.1.1.a-HE1",
          "requirement": "UH ≤ 2.30 W/m²K for zone B"
        },
        "risk": {
          "label": "Energy Non-Compliant",
          "description": "Single glazing estimated U=5.7 exceeds limit of 2.30",
          "affects_cedula": false,
          "affects_ite": true,
          "affects_energy_cert": true
        },
        "remediation": {
          "action": "Replace windows with double-glazed PVC",
          "target_u": 2.0,
          "bcca_keyword": "ventana PVC doble acristalamiento RPT",
          "cte_reference": "Anejo E orientative: U=2.0 for zone B"
        }
      }
    ]
  },
  
  "energy_assessment": {
    "current_rating": "G",
    "current_consumption_estimate": {
      "kwh_m2_year": 185,
      "estimation_method": "Building age + visual indicators",
      "confidence": "low-medium",
      "disclaimer": "Actual consumption requires official Certificado Energético"
    },
    
    "envelope_analysis": {
      "windows": {
        "estimated_current_u": 5.7,
        "estimation_basis": "Visual: aluminum sliding, single glazing",
        "cte_limit": 2.30,
        "cte_orientative": 2.00,
        "compliant": false,
        "cte_reference": "CTE-DB-HE Table 3.1.1.a-HE1, Anejo E"
      },
      "walls": {
        "estimated_current_u": 2.5,
        "estimation_basis": "Building year 1975 (pre-NBE-CT 79)",
        "cte_limit": 0.56,
        "cte_orientative": 0.38,
        "compliant": false,
        "note": "Cannot verify from photos - architect must assess"
      },
      "roof": {
        "estimated_current_u": null,
        "estimation_basis": "Not accessible (floor 3 of 6)",
        "note": "Top-floor assessment only"
      }
    },
    
    "upgrade_path": {
      "target_rating": "C",
      "estimated_target_consumption": 55,
      "interventions": [
        {
          "intervention": "Window replacement",
          "current_u": 5.7,
          "target_u": 2.0,
          "estimated_savings_kwh_m2_year": 45,
          "calculation": {
            "method": "Simplified degree-day",
            "window_area_m2": 12,
            "floor_area_m2": 95,
            "degree_days": 1200,
            "formula": "(U_old - U_new) × Area × DD × 24 / 1000 / floor_area"
          },
          "cte_reference": "CTE-DB-HE Anejo E Table a-Anejo E"
        },
        {
          "intervention": "Heating system upgrade",
          "current_system": "Old gas boiler (estimated 75% efficiency)",
          "target_system": "Condensing boiler (95%+ efficiency)",
          "estimated_savings_kwh_m2_year": 28,
          "cte_reference": "CTE-DB-HE Table 4.5-HE0 (reference systems)"
        }
      ],
      
      "estimated_total_improvement": 73,
      "subsidy_eligibility": {
        "pree_eligible": true,
        "reason": "Improvement >30% (estimated 39%)",
        "ico_nextgen_eligible": true,
        "reason2": "Improvement ≥2 letter grades (G→C = 4 grades)"
      }
    }
  },
  
  "cedula_readiness": {
    "overall_status": "AT_RISK",
    "likely_to_pass": ["hygiene_conditions", "room_program", "entry_security"],
    "likely_to_fail": ["electrical_safety", "water_supply_material"],
    "requires_verification": [
      {
        "requirement": "Minimum room dimensions",
        "regulation": "Decreto 10/2019 Extremadura Art. 3",
        "source_file": "/standards/decreto-10-2019-extremadura.txt",
        "note": "Cannot measure from photos"
      },
      {
        "requirement": "Ceiling heights",
        "regulation": "Decreto 10/2019 Extremadura",
        "minimums": {
          "habitable_rooms": "2.50m",
          "bathrooms": "2.20m",
          "corridors": "2.20m"
        }
      },
      {
        "requirement": "Ventilation adequacy",
        "regulation": "CTE-DB-HS3",
        "source_file": "/standards/CTE-DB-HS.txt",
        "note": "Requires air flow calculation"
      }
    ]
  },
  
  "ite_readiness": {
    "applicable": true,
    "reason": "Building year 1975 exceeds 30-year threshold",
    "sections_assessed": {
      "1.3.1_foundations": {"status": "cannot_assess", "note": "Not visible from interior photos"},
      "1.3.2_structure": {"status": "no_issues_visible", "note": "No cracks observed"},
      "1.3.3_facades": {"status": "cannot_assess", "note": "No exterior photos available"},
      "1.3.4_roofs": {"status": "not_applicable", "note": "Unit is floor 3 of 6"},
      "1.3.5_installations": {"status": "at_risk", "note": "Electrical and plumbing issues detected"}
    },
    "source_file": "/standards/modelo-informe-ite.txt"
  },
  
  "market_comparison": {
    "comparables_source": "Casafari API",
    "comparables_count": 9,
    "search_criteria": {
      "radius_km": 3,
      "condition": "very-good",
      "property_type": "apartment",
      "bedrooms": 3
    },
    "price_brackets": {
      "fast_sell": {"price": 398000, "gap_from_listing": 78000},
      "fair_market": {"price": 445000, "gap_from_listing": 125000},
      "out_of_market": {"price": 520000, "gap_from_listing": 200000}
    },
    "key_gaps_vs_fair_market": [
      "100% of comparables pass ELEC_REBT_001 (you fail)",
      "100% of comparables pass PLUMB_LEAD_001 (you fail)",
      "Average window condition: 8.3/10 (you: 4/10)",
      "Average energy rating: C (you: G)"
    ]
  },
  
  "scope_summary": {
    "essential_works": [
      {"item": "Full electrical rewiring + boletín", "bcca_keyword": "instalación eléctrica vivienda completa"},
      {"item": "Lead pipe replacement", "bcca_keyword": "sustitución tubería plomo agua"},
      {"item": "Water heater upgrade", "bcca_keyword": "calentador estanco gas natural"}
    ],
    "recommended_works": [
      {"item": "Window replacement (8 units)", "bcca_keyword": "ventana PVC doble acristalamiento"},
      {"item": "Kitchen renovation", "bcca_keyword": "reforma cocina completa"},
      {"item": "Bathroom renovation", "bcca_keyword": "reforma baño completo"}
    ],
    "optional_works": [
      {"item": "Flooring replacement", "bcca_keyword": "solado laminado"},
      {"item": "Interior painting", "bcca_keyword": "pintura plástica interior"}
    ]
  },
  
  "architect_checklist": {
    "priority_verifications": [
      {"item": "Electrical consumer unit", "location": "Utility area (Photo #7)", "check": "Confirm ceramic fuses, assess replacement scope"},
      {"item": "Pipe material", "location": "Under kitchen sink (Photo #9)", "check": "Confirm lead, assess extent of lead piping"},
      {"item": "Water heater type", "location": "Utility area (Photo #11)", "check": "Confirm open-flue, assess ventilation"},
      {"item": "Window glazing", "location": "All rooms", "check": "Confirm single glazing, count units, measure"},
      {"item": "Room dimensions", "location": "All rooms", "check": "Measure for Decreto 10/2019 compliance"},
      {"item": "Ceiling heights", "location": "All rooms", "check": "Verify ≥2.50m habitable, ≥2.20m wet rooms"}
    ],
    "measurements_required": [
      "Floor area (verify claimed 95m²)",
      "Each room dimensions",
      "Ceiling heights",
      "Window dimensions (for replacement quote)",
      "Balcony railing height"
    ]
  },
  
  "disclaimers": [
    "This assessment is based on AI analysis of property photographs and is NOT a certification.",
    "Actual Cédula de Habitabilidad requires physical inspection by a qualified Arquitecto or Arquitecto Técnico.",
    "ITE must be performed by a qualified Técnico Competente with on-site inspection.",
    "REBT compliance requires inspection and boletín from an Instalador Autorizado.",
    "Energy class estimates are indicative only - official Certificado Energético required.",
    "Cost estimates (if provided) are indicative ranges based on BCCA reference data.",
    "Hidden defects behind walls, floors, or ceilings cannot be detected from photographs."
  ],
  
  "cte_references_used": [
    {"document": "CTE-DB-HE", "version": "14 June 2022", "file": "/standards/CTE-DB-HE.txt"},
    {"document": "CTE-DB-HS", "file": "/standards/CTE-DB-HS.txt"},
    {"document": "Decreto 10/2019 Extremadura", "file": "/standards/decreto-10-2019-extremadura.txt"},
    {"document": "Modelo Informe ITE", "file": "/standards/modelo-informe-ite.txt"},
    {"document": "Rules Engine V2", "file": "/backend/pipeline/rules_engine_v2.json"}
  ]
}
```

### Visual Export: Infographic Generation

We generate a visual summary image for the user to share or review:

#### Image Generation Approach

```python
# In backend/export/generate_infographic.py

from PIL import Image, ImageDraw, ImageFont
import json

def generate_handover_infographic(handover_data: dict) -> bytes:
    """
    Generate a visual infographic summarizing the property assessment.
    
    Layout (1200x1800 pixels):
    ┌────────────────────────────────────────────────────────────────────┐
    │  PUEDO CASA - PROPERTY ASSESSMENT SUMMARY                          │
    │  [Property Photo]  │  Address, Price, Year, Size                   │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  COMPLIANCE STATUS                                                 │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐                              │
    │  │ CÉDULA  │ │   ITE   │ │  REBT   │                              │
    │  │ AT RISK │ │ AT RISK │ │  FAIL   │                              │
    │  │   ⚠️    │ │   ⚠️    │ │   ❌    │                              │
    │  └─────────┘ └─────────┘ └─────────┘                              │
    │                                                                    │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  ISSUES DETECTED (4)                                               │
    │  ┌──────────────────────────────────────────────────────────────┐ │
    │  │ ❌ Electrical: Ceramic fuses (REBT 2002)                      │ │
    │  │ ❌ Plumbing: Lead pipes (RD 140/2003)                         │ │
    │  │ ❌ Windows: Single glazing (CTE-DB-HE)                        │ │
    │  │ ⚠️ Water heater: Open-flue (RITE 2013)                        │ │
    │  └──────────────────────────────────────────────────────────────┘ │
    │                                                                    │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  ENERGY ASSESSMENT                                                 │
    │  Current: [G] ────────────────────────────────────▶ Target: [C]    │
    │           185 kWh/m²/year                              55          │
    │                                                                    │
    │  Key interventions:                                                │
    │  • Window upgrade: -45 kWh/m²/year                                │
    │  • Heating system: -28 kWh/m²/year                                │
    │                                                                    │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  MARKET POSITION                                                   │
    │  ┌────────────────────────────────────────────────────────────┐   │
    │  │ €320k ──────┬────────┬─────────┬────────────▶              │   │
    │  │       Your  │ Fast   │ Fair    │ Out of                   │   │
    │  │     Listing │ Sell   │ Market  │ Market                   │   │
    │  │             │ €398k  │ €445k   │ €520k                    │   │
    │  └────────────────────────────────────────────────────────────┘   │
    │                                                                    │
    │  Gap to Fair Market: €125,000                                      │
    │                                                                    │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  NEXT STEPS FOR ARCHITECT                                          │
    │  □ Verify electrical installation                                  │
    │  □ Check pipe material throughout                                  │
    │  □ Measure all room dimensions                                     │
    │  □ Assess ventilation adequacy                                     │
    │                                                                    │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  ⚠️ DISCLAIMER: This is a preliminary visual assessment.           │
    │     Physical inspection by qualified professional required.        │
    │                                                                    │
    │  Generated: 2026-01-07 | Puedo Casa v1.0                          │
    └────────────────────────────────────────────────────────────────────┘
    """
    
    # Create image
    width, height = 1200, 1800
    img = Image.new('RGB', (width, height), color='#FDFBF7')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_heading = ImageFont.truetype("arial.ttf", 20)
        font_body = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_heading = font_title
        font_body = font_title
    
    # Draw sections...
    # [Implementation details]
    
    # Convert to bytes
    import io
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
```

#### Alternative: HTML Template → PDF

For more complex layouts, we generate an HTML template and convert to PDF:

```html
<!-- templates/architect_handover.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        @page { size: A4; margin: 20mm; }
        body { font-family: 'Helvetica Neue', sans-serif; }
        .header { background: #1a365d; color: white; padding: 20px; }
        .status-badge { 
            display: inline-block; 
            padding: 8px 16px; 
            border-radius: 4px; 
            font-weight: bold;
        }
        .status-pass { background: #c6f6d5; color: #22543d; }
        .status-fail { background: #fed7d7; color: #822727; }
        .status-risk { background: #feebc8; color: #744210; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #e2e8f0; }
        .cte-reference { font-size: 10px; color: #718096; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Puedo Casa - Property Assessment</h1>
        <p>{{ property.address }}</p>
        <p>Generated: {{ meta.generated_at }}</p>
    </div>
    
    <div class="section">
        <h2>Compliance Status</h2>
        <div class="status-badge {{ cedula_class }}">
            Cédula: {{ cedula_readiness.overall_status }}
        </div>
        <!-- ... more status badges ... -->
    </div>
    
    <!-- ... more sections ... -->
    
    <div class="section disclaimer">
        <h3>⚠️ Important Disclaimer</h3>
        {% for disclaimer in disclaimers %}
        <p>{{ disclaimer }}</p>
        {% endfor %}
    </div>
    
    <div class="section references">
        <h3>CTE References Used</h3>
        <ul>
        {% for ref in cte_references_used %}
            <li>{{ ref.document }} - {{ ref.file }}</li>
        {% endfor %}
        </ul>
    </div>
</body>
</html>
```

### API Endpoint for Export

```python
# In backend/routes/renovation.py

@router.get("/{listing_id}/handover")
async def get_architect_handover(listing_id: int, format: str = "json"):
    """
    Generate architect handover document.
    
    Formats:
    - json: Full structured data
    - pdf: Printable PDF document
    - png: Visual infographic summary
    """
    # Gather all analysis data
    handover_data = await compile_handover_data(listing_id)
    
    if format == "json":
        return JSONResponse(handover_data)
    
    elif format == "pdf":
        pdf_bytes = await generate_handover_pdf(handover_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=handover_{listing_id}.pdf"}
        )
    
    elif format == "png":
        img_bytes = await generate_handover_infographic(handover_data)
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=summary_{listing_id}.png"}
        )
```

### UI Component for Export

```tsx
// components/renovation/HandoverExportCard.tsx

export const HandoverExportCard: React.FC<{ listingId: number }> = ({ listingId }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  
  const handleExport = async (format: 'json' | 'pdf' | 'png') => {
    setIsGenerating(true);
    try {
      const response = await fetch(`/api/renovation/${listingId}/handover?format=${format}`);
      const blob = await response.blob();
      
      // Download file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `property_assessment_${listingId}.${format}`;
      a.click();
    } finally {
      setIsGenerating(false);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Architect Handover</CardTitle>
        <CardDescription>
          Generate a professional document to share with your architect
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4">
          <Button onClick={() => handleExport('pdf')} disabled={isGenerating}>
            <FileText className="w-4 h-4 mr-2" />
            Download PDF
          </Button>
          <Button onClick={() => handleExport('png')} variant="outline" disabled={isGenerating}>
            <Image className="w-4 h-4 mr-2" />
            Summary Image
          </Button>
          <Button onClick={() => handleExport('json')} variant="ghost" disabled={isGenerating}>
            <Code className="w-4 h-4 mr-2" />
            Raw Data (JSON)
          </Button>
        </div>
        
        <p className="text-xs text-gray-500 mt-4">
          ⚠️ This document is for preliminary assessment only. 
          Physical inspection by a qualified professional is required.
        </p>
      </CardContent>
    </Card>
  );
};
```

---

## In-App Buyer View (Simplified)

### What Buyers Want to Know

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   THREE QUESTIONS:                                                          │
│                                                                             │
│   1. 💰 WHAT WOULD RENOVATION COST?                                         │
│   2. 🏠 WHAT WOULD THE HOME BE WORTH AFTER?                                 │
│   3. ⏱️  HOW LONG WOULD IT TAKE?                                            │
│                                                                             │
│   (They decide if it's worth it - we just provide the information)          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Business Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   WHO PAYS:     Real estate agents (to accelerate renovation property sales)│
│   WHO USES:     Buyers (to understand renovation potential)                 │
│   OUR ROLE:     Neutral information provider                                │
│                                                                             │
│   WE DO NOT:    Recommend buy/don't buy                                     │
│   WE DO:        Show "the art of the possible" for each property            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Card Design: The "Renovation Potential" Card

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   RENOVATION POTENTIAL                                                        ║
║   Calle Example 123, Valencia                                                 ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   THE NUMBERS                                                                 ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                                                                     │    ║
║   │   ASKING PRICE              €320,000                                │    ║
║   │   + RENOVATION              €49,400   (inc. IVA)                    │    ║
║   │   ─────────────────────────────────────                             │    ║
║   │   = TOTAL INVESTMENT        €369,400                                │    ║
║   │                                                                     │    ║
║   │   TARGET VALUE              €445,000  (comparable sales)            │    ║
║   │   ─────────────────────────────────────                             │    ║
║   │   = POTENTIAL MARGIN        €75,600                                 │    ║
║   │                                                                     │    ║
║   │   TIMELINE                  8-10 weeks                              │    ║
║   │                                                                     │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   WHERE THESE NUMBERS COME FROM:                                              ║
║                                                                               ║
║   • Target value: Average of 3 comparable "very good" condition sales         ║
║     within 3km, sold in last 9 months (via Casafari)                          ║
║                                                                               ║
║   • Renovation cost: BCCA price book + 19% overhead + 21% IVA                 ║
║     Based on detected condition and required upgrades                         ║
║                                                                               ║
║   ─────────────────────────────────────────────────────────────────────────  ║
║                                                                               ║
║   WHAT RENOVATION INCLUDES:                                                   ║
║   • Full electrical upgrade (safety compliance)                               ║
║   • Plumbing replacement (health compliance)                                  ║
║   • New windows (energy improvement G→C)                                      ║
║   • Kitchen & bathroom renovation                                             ║
║   • Flooring and painting                                                     ║
║                                                                               ║
║   ─────────────────────────────────────────────────────────────────────────  ║
║                                                                               ║
║   [📄 Download Full Report]  [📞 Contact Agent]                              ║
║                                                                               ║
║   ─────────────────────────────────────────────────────────────────────────  ║
║   Estimates only. Actual costs and values may vary.                           ║
║   Professional verification recommended before purchase.                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Simplified JSON Response for UI

```json
{
  "listing_id": 12345,
  "listing_price": 320000,
  
  "renovation_scenarios": {
    "essential": {
      "label": "Essential Only",
      "description": "Compliance + basic finishes",
      
      "the_math": {
        "asking_price": 320000,
        "renovation_cost": 35200,
        "total_investment": 355200,
        "target_value": 398000,
        "potential_margin": 42800
      },
      
      "timeline_weeks": "6-8",
      "scope_summary": "Safety & habitability compliance",
      
      "target_value_source": {
        "method": "Casafari comparables",
        "condition_filter": "very-good",
        "radius_km": 3,
        "sample_count": 3,
        "date_range": "last 9 months"
      },
      
      "renovation_cost_source": {
        "method": "BCCA price book",
        "overhead_percent": 19,
        "iva_percent": 21,
        "line_items_count": 24
      }
    },
    
    "standard": {
      "label": "Standard Renovation",
      "description": "Full renovation to 'very good' condition",
      
      "the_math": {
        "asking_price": 320000,
        "renovation_cost": 49400,
        "total_investment": 369400,
        "target_value": 445000,
        "potential_margin": 75600
      },
      
      "timeline_weeks": "8-10",
      "scope_summary": "Complete modernization",
      
      "target_value_source": {
        "method": "Casafari comparables",
        "condition_filter": "very-good",
        "radius_km": 3,
        "sample_count": 3,
        "date_range": "last 9 months"
      },
      
      "renovation_cost_source": {
        "method": "BCCA price book",
        "overhead_percent": 19,
        "iva_percent": 21,
        "line_items_count": 47
      }
    },
    
    "premium": {
      "label": "Premium Finish",
      "description": "High-end materials and features",
      
      "the_math": {
        "asking_price": 320000,
        "renovation_cost": 78500,
        "total_investment": 398500,
        "target_value": 520000,
        "potential_margin": 121500
      },
      
      "timeline_weeks": "12-16",
      "scope_summary": "Luxury standard renovation",
      
      "target_value_source": {
        "method": "Casafari comparables",
        "condition_filter": "very-good",
        "radius_km": 3,
        "sample_count": 3,
        "date_range": "last 9 months"
      },
      
      "renovation_cost_source": {
        "method": "BCCA price book + premium materials",
        "overhead_percent": 19,
        "iva_percent": 21,
        "line_items_count": 62
      }
    }
  },
  
  "scope_includes": [
    "Electrical upgrade (safety compliance)",
    "Plumbing replacement (health compliance)",
    "Window upgrade (energy improvement)",
    "Kitchen renovation",
    "Bathroom renovation"
  ],
  
  "post_renovation_status": {
    "cedula_eligible": true,
    "expected_energy_class": "C",
    "notes": "Subject to professional verification"
  },
  
  "credibility_notes": {
    "target_value": "Based on actual sales of similar properties in similar condition within 3km",
    "renovation_cost": "Based on official BCCA construction price book used by Spanish quantity surveyors"
  },
  
  "disclaimer": "Estimates only. Actual costs and values may vary. Professional verification recommended before purchase."
}
```

---

## Timeline Estimation Methodology

### The Problem

We have detailed costs from KGEstimator + BCCA, but **no timeline data** in BCCA.

### The Solution: Gemini Timeline Synthesis

After costing is complete, we pass the full BoQ to Gemini to estimate timeline:

```python
# In backend/pipeline/steps/estimate_timeline.py

async def estimate_renovation_timeline(
    boq_lines: List[BoQLine],
    property_info: dict,
    scope_summary: dict
) -> dict:
    """
    Use Gemini to estimate realistic renovation timeline.
    
    Input: Full BoQ with all line items + property context
    Output: Timeline breakdown by phase
    """
    
    # Build context for Gemini
    boq_summary = "\n".join([
        f"- {line.description}: {line.quantity} {line.unit} @ €{line.unit_price}"
        for line in boq_lines
    ])
    
    prompt = f"""You are a Spanish renovation project manager estimating timelines.

PROPERTY:
- Type: {property_info['property_type']}
- Size: {property_info['floor_area_m2']}m²
- Bedrooms: {property_info['bedrooms']}
- Current condition: Requires full renovation

BILL OF QUANTITIES:
{boq_summary}

SCOPE SUMMARY:
- Essential works: {scope_summary['essential']}
- Recommended works: {scope_summary['recommended']}
- Optional works: {scope_summary['optional']}

TASK: Estimate a realistic renovation timeline considering:
1. Spanish construction practices
2. Logical sequencing (demo → structure → MEP → finishes)
3. Typical crew sizes for residential renovation
4. Drying/curing times (plaster, paint, etc.)
5. Municipal permit timelines if needed
6. No parallel work that would conflict

Respond in JSON:
{{
  "total_weeks": {{
    "min": X,
    "max": Y,
    "typical": Z
  }},
  "phases": [
    {{
      "phase": "Phase name",
      "duration_days": X,
      "works": ["list", "of", "works"],
      "dependencies": "What must complete first",
      "can_overlap": true/false
    }}
  ],
  "critical_path": ["Phase A", "Phase B", "..."],
  "risks_to_timeline": [
    "Risk 1: description",
    "Risk 2: description"
  ],
  "assumptions": [
    "Assumption 1",
    "Assumption 2"
  ]
}}
"""

    response = await call_gemini(prompt, model="gemini-2.5-flash")
    return parse_timeline_response(response)
```

### Typical Renovation Phases (Reference Data)

```python
# Standard phase durations for Spanish residential renovation
# Used as sanity check against Gemini estimates

TYPICAL_PHASE_DURATIONS = {
    "permits_and_prep": {
        "description": "Licencia de obra menor, materials ordering",
        "days_min": 5,
        "days_max": 15,
        "notes": "Obra menor: 5-10 days. Obra mayor: 30-60 days"
    },
    "demolition": {
        "description": "Stripping out, removing old installations",
        "days_per_100m2": 5,
        "notes": "Includes waste removal (gestión residuos)"
    },
    "structural": {
        "description": "Any structural modifications",
        "days_min": 0,
        "days_max": 10,
        "notes": "Only if walls being moved"
    },
    "plumbing_rough": {
        "description": "New pipe runs, drain relocations",
        "days_per_bathroom": 2,
        "days_for_kitchen": 1
    },
    "electrical_rough": {
        "description": "Rewiring, new circuits, rozas",
        "days_per_100m2": 4,
        "notes": "Includes patching rozas after"
    },
    "hvac": {
        "description": "Heating/cooling installation",
        "days_min": 2,
        "days_max": 5
    },
    "windows": {
        "description": "Window replacement",
        "days_per_5_windows": 2
    },
    "plastering": {
        "description": "Wall finishing, including drying time",
        "days_per_100m2": 5,
        "notes": "Includes 2-3 days drying"
    },
    "tiling": {
        "description": "Bathroom/kitchen tiling",
        "days_per_bathroom": 4,
        "days_for_kitchen_splash": 1
    },
    "flooring": {
        "description": "Floor installation",
        "days_per_50m2": 2,
        "notes": "Laminate faster than tile"
    },
    "kitchen_fit": {
        "description": "Kitchen cabinet and appliance installation",
        "days_min": 3,
        "days_max": 5
    },
    "bathroom_fit": {
        "description": "Sanitary ware installation",
        "days_per_bathroom": 2
    },
    "painting": {
        "description": "Interior painting (2 coats + drying)",
        "days_per_100m2": 4
    },
    "doors_trim": {
        "description": "Interior doors, baseboards, trim",
        "days_per_5_doors": 2
    },
    "final_fix": {
        "description": "Electrical fixtures, final connections",
        "days_min": 2,
        "days_max": 3
    },
    "cleaning": {
        "description": "Final clean, snagging",
        "days_min": 1,
        "days_max": 2
    }
}

def calculate_baseline_timeline(property_info: dict, scope: dict) -> dict:
    """
    Calculate a baseline timeline estimate before Gemini refinement.
    """
    floor_area = property_info['floor_area_m2']
    bathrooms = scope.get('bathrooms_to_renovate', 1)
    windows = scope.get('windows_to_replace', 0)
    
    timeline_days = 0
    
    # Permits (assume obra menor)
    timeline_days += 7
    
    # Demo
    timeline_days += max(3, floor_area / 100 * 5)
    
    # MEP (can partially overlap)
    if scope.get('electrical_rewire'):
        timeline_days += floor_area / 100 * 4
    if scope.get('plumbing_replace'):
        timeline_days += bathrooms * 2 + 1
    
    # Windows (can happen during MEP)
    # Not added to timeline if MEP is longer
    
    # Plastering
    timeline_days += floor_area / 100 * 5
    
    # Tiling
    timeline_days += bathrooms * 4
    if scope.get('kitchen_renovate'):
        timeline_days += 1
    
    # Flooring
    timeline_days += floor_area / 50 * 2
    
    # Kitchen fit
    if scope.get('kitchen_renovate'):
        timeline_days += 4
    
    # Bathroom fit
    timeline_days += bathrooms * 2
    
    # Painting
    timeline_days += floor_area / 100 * 4
    
    # Final fix + cleaning
    timeline_days += 4
    
    # Convert to weeks
    working_days_per_week = 5
    weeks = timeline_days / working_days_per_week
    
    return {
        "baseline_days": round(timeline_days),
        "baseline_weeks_min": round(weeks * 0.85),
        "baseline_weeks_max": round(weeks * 1.3),
        "baseline_weeks_typical": round(weeks)
    }
```

### Timeline Output Format

```json
{
  "timeline": {
    "total_weeks": {
      "min": 8,
      "max": 12,
      "typical": 10
    },
    
    "gantt_simplified": [
      {"phase": "Permits & Prep", "week_start": 1, "week_end": 1},
      {"phase": "Demolition", "week_start": 2, "week_end": 2},
      {"phase": "Electrical & Plumbing", "week_start": 3, "week_end": 4},
      {"phase": "Windows", "week_start": 3, "week_end": 3},
      {"phase": "Plastering", "week_start": 5, "week_end": 5},
      {"phase": "Tiling", "week_start": 6, "week_end": 7},
      {"phase": "Kitchen Fit", "week_start": 7, "week_end": 8},
      {"phase": "Flooring", "week_start": 8, "week_end": 8},
      {"phase": "Painting", "week_start": 9, "week_end": 9},
      {"phase": "Final Fix", "week_start": 10, "week_end": 10}
    ],
    
    "critical_milestones": [
      {"week": 1, "milestone": "Permits approved, work can begin"},
      {"week": 4, "milestone": "MEP rough-in complete, walls ready for finish"},
      {"week": 7, "milestone": "Wet rooms complete, kitchen installed"},
      {"week": 10, "milestone": "Final inspection, property ready"}
    ],
    
    "assumptions": [
      "Obra menor license (no structural work)",
      "Single contractor team managing all trades",
      "Materials ordered in advance",
      "No unforeseen issues (damp, asbestos, etc.)"
    ],
    
    "risks": [
      "Permit delays (+1-2 weeks)",
      "Material supply issues (+1-2 weeks)",
      "Discovery of hidden problems (variable)",
      "Contractor availability (peak season delays)"
    ]
  }
}
```

### Visual Timeline Component

```tsx
// components/renovation/TimelineCard.tsx

export const TimelineCard: React.FC<{ timeline: TimelineData }> = ({ timeline }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Estimated Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Big number display */}
        <div className="text-center mb-6">
          <div className="text-4xl font-bold text-blue-600">
            {timeline.total_weeks.typical}
          </div>
          <div className="text-gray-500">
            weeks ({timeline.total_weeks.min}-{timeline.total_weeks.max} range)
          </div>
        </div>
        
        {/* Simplified Gantt */}
        <div className="space-y-2">
          {timeline.gantt_simplified.map((phase, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-32 text-sm text-gray-600 truncate">
                {phase.phase}
              </div>
              <div className="flex-1 h-6 bg-gray-100 rounded relative">
                <div
                  className="absolute h-full bg-blue-500 rounded"
                  style={{
                    left: `${(phase.week_start - 1) * 10}%`,
                    width: `${(phase.week_end - phase.week_start + 1) * 10}%`
                  }}
                />
              </div>
              <div className="w-16 text-xs text-gray-400">
                Week {phase.week_start}-{phase.week_end}
              </div>
            </div>
          ))}
        </div>
        
        {/* Key milestones */}
        <div className="mt-6 pt-4 border-t">
          <h4 className="font-medium mb-2">Key Milestones</h4>
          <div className="space-y-1 text-sm">
            {timeline.critical_milestones.map((m, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-blue-600 font-medium">Week {m.week}:</span>
                <span className="text-gray-600">{m.milestone}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Disclaimer */}
        <p className="text-xs text-gray-400 mt-4">
          ⚠️ Timeline assumes no unforeseen issues. Actual duration may vary.
        </p>
      </CardContent>
    </Card>
  );
};
```

---

## Complete View: The Renovation Potential Panel

### React Component: `RenovationPotentialPanel.tsx`

```tsx
// components/renovation/RenovationPotentialPanel.tsx

interface TheMath {
  asking_price: number;
  renovation_cost: number;
  total_investment: number;
  target_value: number;
  potential_margin: number;
}

interface RenovationScenario {
  label: string;
  description: string;
  the_math: TheMath;
  timeline_weeks: string;
  scope_summary: string;
  target_value_source: {
    method: string;
    sample_count: number;
    radius_km: number;
  };
  renovation_cost_source: {
    method: string;
    line_items_count: number;
  };
}

interface RenovationData {
  listing_price: number;
  renovation_scenarios: {
    essential: RenovationScenario;
    standard: RenovationScenario;
    premium: RenovationScenario;
  };
  scope_includes: string[];
  post_renovation_status: {
    cedula_eligible: boolean;
    expected_energy_class: string;
  };
}

export const RenovationPotentialPanel: React.FC<{ 
  listingId: number;
  data: RenovationData;
}> = ({ listingId, data }) => {
  const [selectedScenario, setSelectedScenario] = useState<string>('standard');
  const scenario = data.renovation_scenarios[selectedScenario];
  const math = scenario.the_math;
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <h2 className="text-xl font-bold mb-2">Renovation Potential</h2>
      <p className="text-sm text-gray-500 mb-6">
        What this property could become with renovation
      </p>
      
      {/* Scenario selector */}
      <div className="flex gap-2 mb-6">
        {Object.entries(data.renovation_scenarios).map(([key, s]) => (
          <button
            key={key}
            onClick={() => setSelectedScenario(key)}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition border
              ${selectedScenario === key 
                ? 'bg-slate-800 text-white border-slate-800' 
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      
      {/* THE MATH - Clear breakdown */}
      <div className="bg-slate-50 rounded-lg p-4 mb-6 font-mono text-sm">
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-600">Asking Price</span>
            <span className="font-semibold">€{math.asking_price.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">+ Renovation</span>
            <span className="font-semibold">€{math.renovation_cost.toLocaleString()}</span>
          </div>
          <div className="border-t border-gray-300 pt-2 flex justify-between">
            <span className="text-gray-700 font-medium">= Total Investment</span>
            <span className="font-bold">€{math.total_investment.toLocaleString()}</span>
          </div>
          
          <div className="h-3" /> {/* Spacer */}
          
          <div className="flex justify-between">
            <span className="text-gray-600">Target Value</span>
            <span className="font-semibold text-blue-600">€{math.target_value.toLocaleString()}</span>
          </div>
          <div className="border-t border-gray-300 pt-2 flex justify-between">
            <span className="text-gray-700 font-medium">= Potential Margin</span>
            <span className={`font-bold ${math.potential_margin > 0 ? 'text-green-600' : 'text-red-600'}`}>
              €{math.potential_margin.toLocaleString()}
            </span>
          </div>
        </div>
        
        {/* Timeline */}
        <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between">
          <span className="text-gray-600">Timeline</span>
          <span className="font-semibold">{scenario.timeline_weeks} weeks</span>
        </div>
      </div>
      
      {/* Where these numbers come from - credibility */}
      <div className="mb-6 text-xs text-gray-500 space-y-1">
        <div className="flex items-start gap-1">
          <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
          <span>
            Target value: {scenario.target_value_source.sample_count} comparable sales 
            within {scenario.target_value_source.radius_km}km ({scenario.target_value_source.method})
          </span>
        </div>
        <div className="flex items-start gap-1">
          <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
          <span>
            Renovation cost: {scenario.renovation_cost_source.line_items_count} line items 
            from {scenario.renovation_cost_source.method}
          </span>
        </div>
      </div>
      
      {/* What's included */}
      <div className="mb-6">
        <h3 className="font-medium mb-2 text-gray-700">Renovation Includes:</h3>
        <ul className="text-sm text-gray-600 space-y-1">
          {data.scope_includes.map((item, i) => (
            <li key={i} className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
              {item}
            </li>
          ))}
        </ul>
      </div>
      
      {/* Post-renovation status */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-medium mb-2 text-gray-700">After Renovation:</h3>
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1">
            <Info className="w-4 h-4 text-gray-400" />
            <span>Cédula eligible: {data.post_renovation_status.cedula_eligible ? 'Yes' : 'TBD'}</span>
          </div>
          <div className="flex items-center gap-1">
            <Info className="w-4 h-4 text-gray-400" />
            <span>Energy: {data.post_renovation_status.expected_energy_class}</span>
          </div>
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex gap-3">
        <Button className="flex-1" variant="default">
          <FileText className="w-4 h-4 mr-2" />
          Download Full Report
        </Button>
        <Button className="flex-1" variant="outline">
          <Phone className="w-4 h-4 mr-2" />
          Contact Agent
        </Button>
      </div>
      
      {/* Disclaimer */}
      <p className="text-xs text-gray-400 mt-4 text-center">
        Estimates only. Actual costs and values may vary.
        Professional verification recommended before purchase.
      </p>
    </div>
  );
};
```

---

---

## Before/After Photo Generation

### Philosophy: Simple

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   1. Select ONE best "before" photo                                         │
│   2. Generate "after" render for the selected bracket                       │
│   3. Lock camera angle and structural positions                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Render Constraints (Simple)

Only TWO things are locked:

1. **Camera angle** - Must match original photo exactly
2. **Structural positions** - Walls, doors, windows stay in same POSITIONS
   - (You CAN upgrade/replace them, just not move them)

Everything else is fair game for the renovation render.

### Photo Selection

Select the photo that:
- Shows the most renovatable surfaces (floors, walls, cabinets)
- Has good lighting
- Is kitchen or bathroom (most dramatic transformations)

### Render Prompt (Simple)

```python
RENDER_PROMPT = """
Render this {room_type} photo showing a {bracket} level renovation.

LOCKED:
- Camera angle (must match original exactly)
- Wall positions (don't move walls)
- Door positions (don't move doors)  
- Window positions (don't move windows)

You CAN upgrade/replace walls, doors, windows - just keep them in the same positions.

Apply {bracket} level finishes appropriate for this room.
"""
```


def build_render_prompt_for_bracket(
    bracket: str,  # "essential", "standard", "premium"
    detected_issues: List[Dict],
    comparable_finishes: Dict
) -> str:
    """
    Build render prompt for specific bracket.
    
    essential: Fix compliance issues only
    standard: Full modernization to "very good" condition
    premium: High-end materials and finishes
    """
    
    if bracket == "essential":
        return f"""Apply MINIMAL changes to bring this room to basic compliance:

CHANGES TO APPLY:
{format_essential_changes(detected_issues)}

STYLE: Clean, safe, functional
MATERIALS: Basic quality, neutral colors

{STRICT_RENDER_CONSTRAINTS}"""
    
    elif bracket == "standard":
        return f"""Apply STANDARD renovation finishes to achieve "very good" condition:

CHANGES TO APPLY:
{format_standard_changes(detected_issues, comparable_finishes)}

STYLE: Modern, clean, neutral palette
MATERIALS: 
- Floors: Porcelain tile or quality laminate
- Walls: Fresh white/light gray paint
- Kitchen: White/gray cabinets, quartz counters
- Bathroom: Modern tiles, chrome fixtures
- Lighting: Recessed LED or modern pendants

{STRICT_RENDER_CONSTRAINTS}"""
    
    elif bracket == "premium":
        return f"""Apply PREMIUM renovation finishes for high-end appearance:

CHANGES TO APPLY:
{format_premium_changes(detected_issues, comparable_finishes)}

STYLE: Luxury, designer aesthetic
MATERIALS:
- Floors: Large format porcelain or hardwood
- Walls: Designer paint colors, accent walls
- Kitchen: Custom cabinets, marble/dekton counters
- Bathroom: Designer tiles, brushed gold fixtures
- Lighting: Statement fixtures, integrated lighting

{STRICT_RENDER_CONSTRAINTS}"""
```

### Pipeline Flow: Photos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   PHOTO GENERATION PIPELINE                                                 │
│                                                                             │
│   1. V2: Select ONE best photo                                              │
│      ├─ Criteria: Most visible elements, best lighting                      │
│      └─ Output: single_before_photo                                         │
│                                                                             │
│   2. V1: Defurnish (optional)                                               │
│      ├─ Remove furniture from selected photo                                │
│      └─ Output: defurnished_photo                                           │
│                                                                             │
│   3. V4: Render THREE after images                                          │
│      ├─ Essential: Compliance fixes only                                    │
│      ├─ Standard: Full modernization                                        │
│      └─ Premium: High-end finishes                                          │
│                                                                             │
│   OUTPUT:                                                                   │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    │
│   │   BEFORE    │   │  ESSENTIAL  │   │  STANDARD   │   │   PREMIUM   │    │
│   │   (Photo)   │ → │   (Render)  │   │  (Render)   │   │   (Render)  │    │
│   │             │   │  Basic fix  │   │ Modernized  │   │  High-end   │    │
│   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema for Photos

```sql
-- Single before photo selection (replaces tier_before_photos)
CREATE TABLE IF NOT EXISTS listing_before_photo (
    id SERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id),
    cluster_id TEXT NOT NULL,
    photo_url TEXT NOT NULL,
    room_name TEXT,
    selection_reason TEXT,
    visible_elements JSONB,  -- ["flooring", "cabinets", "walls", ...]
    defurnished_data TEXT,   -- Base64 of defurnished version
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id)  -- Only ONE photo per listing
);

-- Three rendered after photos
CREATE TABLE IF NOT EXISTS listing_after_photos (
    id SERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id),
    bracket TEXT NOT NULL,  -- "essential", "standard", "premium"
    before_url TEXT NOT NULL,
    after_data TEXT NOT NULL,  -- Base64 of rendered image
    render_prompt TEXT,  -- The prompt used
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, bracket)
);
```

### UI: Before/After Comparison

```tsx
// components/renovation/BeforeAfterCard.tsx

export const BeforeAfterCard: React.FC<{
  beforeUrl: string;
  afterPhotos: {
    essential: string;
    standard: string;
    premium: string;
  };
  selectedBracket: "essential" | "standard" | "premium";
}> = ({ beforeUrl, afterPhotos, selectedBracket }) => {
  
  return (
    <div className="space-y-4">
      {/* Comparison slider */}
      <div className="relative aspect-video rounded-lg overflow-hidden">
        <ComparisonSlider
          beforeImage={beforeUrl}
          afterImage={afterPhotos[selectedBracket]}
          beforeLabel="Current"
          afterLabel={selectedBracket === "essential" ? "Essential" : 
                      selectedBracket === "standard" ? "Standard" : "Premium"}
        />
      </div>
      
      {/* What changed */}
      <div className="text-sm text-gray-500">
        <p className="font-medium text-gray-700 mb-1">Changes shown:</p>
        {selectedBracket === "essential" && (
          <p>Basic compliance upgrades - safety and habitability fixes</p>
        )}
        {selectedBracket === "standard" && (
          <p>Full modernization - new finishes throughout</p>
        )}
        {selectedBracket === "premium" && (
          <p>Premium renovation - high-end materials and fixtures</p>
        )}
      </div>
      
      {/* Disclaimer */}
      <p className="text-xs text-gray-400">
        Visualization only. Actual results may vary. Structure unchanged.
      </p>
    </div>
  );
};
```

---

## Summary: Two Outputs, Two Audiences

| Aspect | In-App (Buyer) | PDF Export (Architect) |
|--------|----------------|------------------------|
| **Purpose** | Understand renovation potential | Professional verification |
| **Content** | Cost, value, timeline | Full CTE references, methodology |
| **Complexity** | 3 numbers | 3,400+ lines of detail |
| **Disclaimers** | Clear "not advice" | Full legal coverage |
| **CTE Citations** | Hidden | Every claim cited |
| **Visual Style** | Clean cards, neutral tone | Professional report format |
| **Recommendations** | NONE - impartial info only | Architect checklist |

### Key Principle: Show The Math, Not The Advice

```
WE SHOW (Factual Information):
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   Asking Price         €320,000  ← From listing                    │
│   + Renovation         €49,400   ← From BCCA price book            │
│   ─────────────────────────────                                    │
│   = Total Investment   €369,400  ← Simple addition                 │
│                                                                    │
│   Target Value         €445,000  ← From comparable sales           │
│   ─────────────────────────────                                    │
│   = Potential Margin   €75,600   ← Simple subtraction              │
│                                                                    │
│   Timeline             8-10 weeks                                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

WE DO NOT SAY:
- "This is a good investment" ❌
- "You should buy this" ❌
- "Proceed with purchase" ❌

WE DO SAY:
- "Here are the numbers" ✅
- "Here's where they come from" ✅
- "You decide" ✅

CREDIBILITY:
- Target value: Actual comparable sales from Casafari (not estimates)
- Renovation cost: BCCA official price book (used by Spanish QS)
- Both sources are verifiable and industry-standard

WHO PAYS US:
- Real estate agents (to accelerate renovation property sales)

WHO USES THIS:
- Buyers (to window-shop renovation potential with clear numbers)
- Agents (to provide value-add service with credible data)
```

---

---

## Comparables Card V2: Dual View Architecture

> **Added**: 2026-01-07  
> **Purpose**: Agent-friendly presentation with analyse-on-demand for brackets above asking price.

### The Problem

Casafari's price estimates use fuzzy matching (similarity scoring, not exact filters). This can:
- Include properties with very different plot sizes
- Mix conditions (new/very-good/used appear together)
- Give misleading valuations for unique properties

### The Solution: Dual View + Selective Analysis

Show two views side-by-side, let the user choose which brackets to analyze:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MARKET COMPARABLES                                │
│                                                                          │
│  Asking Price: €530,000 (para reformar)                                 │
│  Property: 130m² built | 379m² plot | 3bd/2ba                           │
│                                                                          │
├──────────────────────────────────┬──────────────────────────────────────┤
│  📊 CASAFARI RAW                 │  📊 FILTERED (±20% land size)        │
│  (All matching properties)       │  (Tighter comparable match)          │
├──────────────────────────────────┼──────────────────────────────────────┤
│                                  │                                      │
│  🟢 Fast Sell:    €470,059       │  🟢 Fast Sell:    €330,000           │
│     ⚠️ Below asking              │     ⚠️ Below asking                  │
│                                  │                                      │
│  🟡 Fair Market:  €505,440       │  🟡 Fair Market:  €502,250           │
│     ⚠️ Below asking              │     ⚠️ Below asking                  │
│                                  │                                      │
│  🔴 Premium:      €540,821       │  🔴 Premium:      €590,000           │
│     ✅ Above asking [Analyse]    │     ✅ Above asking [Analyse]        │
│                                  │                                      │
│  Comparables: 6                  │  Comparables: 4 (filtered)           │
│  Condition: very-good            │  Condition: very-good                │
│                                  │                                      │
└──────────────────────────────────┴──────────────────────────────────────┘
```

### View A: Casafari Raw

- Uses Casafari's estimated_prices directly
- Shows `fast_sell_price`, `fair_market_price`, `out_of_market_price`
- Labels each as "Above Asking" or "Below Asking"
- [Analyse] button only appears for brackets ABOVE asking

### View B: Filtered (Our Calculation)

**Filtering Logic:**
```python
# For houses/chalets: filter by plot_area
target_plot = listing.m2_plot or listing.m2_built
tolerance = 0.20  # ±20%

filtered = [
    comp for comp in casafari_results
    if comp.condition == "very-good"
    and comp.plot_area >= target_plot * (1 - tolerance)
    and comp.plot_area <= target_plot * (1 + tolerance)
]

# For apartments: filter by total_area (no plot)
if not listing.m2_plot:
    filtered = [
        comp for comp in casafari_results
        if comp.condition == "very-good"
        and comp.total_area >= listing.m2_built * (1 - tolerance)
        and comp.total_area <= listing.m2_built * (1 + tolerance)
    ]

# Calculate our own brackets
prices = sorted([c.sale_price for c in filtered])
fast_sell = prices[int(len(prices) * 0.10)]      # 10th percentile
fair_market = sum(prices) // len(prices)          # Average
premium = prices[int(len(prices) * 0.90)]         # 90th percentile
```

### The [Analyse] Button

Only shows for brackets **above asking price**.

When clicked, opens a modal with full renovation analysis:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RENOVATION ANALYSIS                                   │
│                    Target: Premium Bracket (€590,000)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📈 THE DELTA                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│     Current asking (para reformar):    €530,000                         │
│     Target bracket (very-good):        €590,000                         │
│     ────────────────────────────────────────────                        │
│     Gap to target:                     +€60,000                         │
│                                                                          │
│  💰 PRICING (via KGEstimator)                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│     Scope items: 47 line items from BCCA price book                     │
│     PEM (materials + labor):           €38,200                          │
│     Overhead + profit (19%):           €7,258                           │
│     IVA (21%):                         €9,546                           │
│     ────────────────────────────────────────────                        │
│     Total renovation cost:             €55,004                          │
│                                                                          │
│  📊 THE MATH                                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│     Asking price:                      €530,000                         │
│     + Renovation:                      €55,004                          │
│     ────────────────────────────────────────────                        │
│     = Total investment:                €585,004                         │
│                                                                          │
│     Target value:                      €590,000                         │
│     ────────────────────────────────────────────                        │
│     = Potential margin:                €4,996 ✅                        │
│                                                                          │
│  ⏱️ TIMING                                                               │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│     Estimated duration:                8-10 weeks                       │
│     (Based on scope complexity and typical crew availability)           │
│                                                                          │
│  🖼️ VISUALIZATION                                                        │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│     ┌─────────────────┐    ┌─────────────────┐                          │
│     │                 │    │                 │                          │
│     │    BEFORE       │ →  │    AFTER        │                          │
│     │  (current)      │    │  (renovated)    │                          │
│     │                 │    │                 │                          │
│     └─────────────────┘    └─────────────────┘                          │
│                                                                          │
│  Source notes:                                                           │
│  • Target value: Comparable sales from Casafari (filtered ±20% plot)    │
│  • Renovation cost: 47 line items from BCCA official price book         │
│  • Timeline: Gemini estimate based on BoQ complexity                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Design Works for Agents

1. **No accusation of overpricing** - We show the data, they interpret
2. **Choice** - Agent picks which view/bracket to analyze
3. **Trusted advisor positioning** - "I'm showing you what the market says"
4. **Actionable** - Each analysis shows path to that price point
5. **Credible sources** - Casafari comparables + BCCA pricing

### API Endpoints

```
GET  /api/renovation/{id}/comparables
     → Returns both views (raw + filtered) with brackets labeled

POST /api/renovation/{id}/comparables/analyse
     Body: { bracket: "premium", view: "filtered" }
     → Triggers full analysis: delta + pricing + timing + images
```

### Database Tables

```sql
-- Store both Casafari raw and our filtered calculations
CREATE TABLE listing_market_comparisons (
    listing_id BIGINT PRIMARY KEY REFERENCES listings(id),
    
    -- Casafari Raw
    casafari_fast_sell INT,
    casafari_fair_market INT,
    casafari_premium INT,
    casafari_comparables_count INT,
    
    -- Our Filtered
    filtered_fast_sell INT,
    filtered_fair_market INT,
    filtered_premium INT,
    filtered_comparables_count INT,
    filter_tolerance DECIMAL(3,2) DEFAULT 0.20,
    
    -- Metadata
    asking_price INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    raw_response JSONB  -- Full Casafari response for debugging
);

-- Store analysis results per bracket
CREATE TABLE listing_bracket_analyses (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id),
    view_type TEXT NOT NULL,  -- 'casafari' or 'filtered'
    bracket TEXT NOT NULL,    -- 'fast_sell', 'fair_market', 'premium'
    
    -- Delta
    target_price INT,
    gap_to_target INT,
    
    -- Pricing (from KGEstimator)
    renovation_cost INT,
    line_items_count INT,
    boq_summary JSONB,
    
    -- Math
    total_investment INT,
    potential_margin INT,
    
    -- Timing
    estimated_weeks_min INT,
    estimated_weeks_max INT,
    
    -- Images
    before_photo_url TEXT,
    after_photo_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### UI Component Structure & State Machine

**State Flow:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMPARABLES CARD                                 │
│                                                                          │
│  STATE: 'initial'                                                        │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Market Comparables                              [Run Analysis]   │  │
│  │                                                                   │  │
│  │  Click Run to fetch market data and identify renovation paths.   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                              ↓ Click [Run]                              │
│                                                                          │
│  STATE: 'loading'                                                        │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Market Comparables                                               │  │
│  │                                                                   │  │
│  │  ⏳ Fetching market data from Casafari...                        │  │
│  │  ⏳ Filtering comparables by property characteristics...          │  │
│  │  ⏳ Calculating price brackets...                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                              ↓ Data loaded                              │
│                                                                          │
│  STATE: 'brackets'                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Market Comparables                                               │  │
│  │  Asking: €530,000                                                 │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐        │  │
│  │  │ 📊 CASAFARI RAW         │  │ 📊 FILTERED (±20%)      │        │  │
│  │  │ 🟢 Fast:  €470k ⚠️      │  │ 🟢 Fast:  €330k ⚠️      │        │  │
│  │  │ 🟡 Fair:  €505k ⚠️      │  │ 🟡 Fair:  €502k ⚠️      │        │  │
│  │  │ 🔴 Prem:  €541k [Anal]  │  │ 🔴 Prem:  €590k [Anal]  │        │  │
│  │  │ 6 comparables           │  │ 4 comparables           │        │  │
│  │  └─────────────────────────┘  └─────────────────────────┘        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                   ↓ Click [Analyse] on Premium (€590k)                  │
│                                                                          │
│  CARD TRANSFORMS → Multiple "Renovation Option" cards appear            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    RENOVATION OPTIONS (replaces Comparables Card)        │
│                                                                          │
│  STATE: 'renovation_options'                                             │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🔴 PREMIUM PATH                                     [← Back]     │  │
│  │  Target: €590,000 | Gap: +€60,000                                 │  │
│  │  ─────────────────────────────────────────────────────────────    │  │
│  │  💰 Reno Cost: €55,004  |  ⏱️ 8-10 weeks  |  📈 Margin: €4,996   │  │
│  │                                                                   │  │
│  │  [Before] ────────────────────────────────────► [After]          │  │
│  │                                                                   │  │
│  │                                              [View Full Plan ▼]   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🟡 FAIR MARKET PATH (if above asking)               [← Back]     │  │
│  │  Target: €505,440 | Gap: -€24,560 ⚠️ Below asking                │  │
│  │  ─────────────────────────────────────────────────────────────    │  │
│  │  (Analysis not available - target below asking price)             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

                          ↓ Click [View Full Plan]

┌─────────────────────────────────────────────────────────────────────────┐
│                    EXPANDED RENOVATION PLAN                              │
│                                                                          │
│  STATE: 'plan_expanded'                                                  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  🔴 PREMIUM PATH - Full Analysis                     [Collapse ▲] │  │
│  │  Target: €590,000                                                 │  │
│  │                                                                   │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │  📊 THE MATH                                                      │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │                                                                   │  │
│  │     Asking price:           €530,000                             │  │
│  │     + Renovation:           €55,004                              │  │
│  │     ─────────────────────────────────                            │  │
│  │     = Total Investment:     €585,004                             │  │
│  │                                                                   │  │
│  │     Target Value:           €590,000                             │  │
│  │     ─────────────────────────────────                            │  │
│  │     = Potential Margin:     €4,996 ✅                            │  │
│  │                                                                   │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │  📋 SCOPE OF WORK (47 line items)                                │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │                                                                   │  │
│  │  ELECTRICAL (€8,200)                                             │  │
│  │    • Full rewiring to REBT 2002                                  │  │
│  │    • New consumer unit with RCD                                  │  │
│  │    • Earthing system upgrade                                     │  │
│  │                                                                   │  │
│  │  PLUMBING (€6,400)                                               │  │
│  │    • Replace lead pipes                                          │  │
│  │    • New water heater                                            │  │
│  │    • Bathroom fixtures                                           │  │
│  │                                                                   │  │
│  │  FINISHES (€22,800)                                              │  │
│  │    • Kitchen cabinets & countertops                              │  │
│  │    • Bathroom tiles & vanity                                     │  │
│  │    • Flooring throughout                                         │  │
│  │    • Paint all rooms                                             │  │
│  │                                                                   │  │
│  │  [View Full BoQ PDF →]                                           │  │
│  │                                                                   │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │  ⏱️ TIMELINE                                                      │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │                                                                   │  │
│  │  Week 1-2:  Demolition, electrical rough-in                      │  │
│  │  Week 3-4:  Plumbing, framing                                    │  │
│  │  Week 5-6:  Drywall, tiling                                      │  │
│  │  Week 7-8:  Finishes, fixtures                                   │  │
│  │  Week 9-10: Final touches, cleaning                              │  │
│  │                                                                   │  │
│  │  Estimated Duration: 8-10 weeks                                  │  │
│  │                                                                   │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │  🖼️ VISUALIZATION                                                 │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │                                                                   │  │
│  │  ┌─────────────┐     ┌─────────────┐                             │  │
│  │  │   BEFORE    │  →  │   AFTER     │                             │  │
│  │  │             │     │  (Premium)  │                             │  │
│  │  └─────────────┘     └─────────────┘                             │  │
│  │                                                                   │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │  🏠 COMPARABLE PROPERTIES (Premium Bracket)                       │  │
│  │  ═══════════════════════════════════════════════════════════════ │  │
│  │                                                                   │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │  │
│  │  │ [photo] │  │ [photo] │  │ [photo] │  │ [photo] │             │  │
│  │  │ €600k   │  │ €580k   │  │ €590k   │  │ €595k   │             │  │
│  │  │ 150m²   │  │ 112m²   │  │ 135m²   │  │ 128m²   │             │  │
│  │  │ 400m²pl │  │ 431m²pl │  │ 380m²pl │  │ 350m²pl │             │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘             │  │
│  │  ← Swipe for more →                                              │  │
│  │                                                                   │  │
│  │  🔗 ORIGINAL LISTINGS:                                            │  │
│  │  • casafari.com/home-sale/property-20658331616                   │  │
│  │  • casafari.com/home-sale/property-17581321624                   │  │
│  │  • casafari.com/home-sale/property-54393976469                   │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Component Hierarchy:**
```
ComparablesCard (stateful)
├── state: 'initial' → RunButton
├── state: 'loading' → LoadingSpinner
├── state: 'brackets' → BracketsView
│   ├── CasafariRawView
│   │   └── BracketRow (×3) with [Analyse] buttons
│   └── FilteredView
│       └── BracketRow (×3) with [Analyse] buttons
│
└── state: 'renovation_options' → RenovationOptionsView
    └── RenovationOptionCard (×N, one per bracket above asking)
        ├── CollapsedView (summary: cost, time, margin)
        └── ExpandedView
            ├── TheMath
            ├── ScopeOfWork
            ├── Timeline
            ├── BeforeAfterImages
            ├── ComparableCarousel (mini listing cards)
            └── OriginalLinks
```

**When [Analyse] is Clicked - Pipeline:**
```
1. User clicks [Analyse] on Premium bracket (€590,000)
   ↓
2. POST /api/renovation/{id}/comparables/analyse
   Body: { bracket: "premium", view: "filtered", target_price: 590000 }
   ↓
3. Backend Pipeline:
   a) Calculate delta (€590,000 - €530,000 = €60,000)
   b) Get detected_conditions from verify_rules
   c) Get visible_elements from assess_uniclass
   d) Build scope of work for delta
   e) Run KGEstimator for pricing
   f) Run Gemini for timeline estimate
   g) Run V1-V4 visuals pipeline for before/after
   h) Filter comparables for this bracket
   i) Save to listing_bracket_analyses table
   ↓
4. UI transforms: brackets view → renovation_options view
   ↓
5. RenovationOptionCard displays with summary
   ↓
6. User clicks [View Full Plan] → expands to show everything
```

```tsx
// components/renovation/ComparablesCard.tsx

type CardState = 'initial' | 'loading' | 'brackets' | 'renovation_options';

export const ComparablesCard: React.FC<{ listingId: number }> = ({ listingId }) => {
  const [state, setState] = useState<CardState>('initial');
  const [bracketsData, setBracketsData] = useState<BracketsData | null>(null);
  const [renovationOptions, setRenovationOptions] = useState<RenovationOption[]>([]);
  const [expandedBracket, setExpandedBracket] = useState<string | null>(null);
  
  // Fetch brackets on Run
  const handleRun = async () => {
    setState('loading');
    const data = await fetchComparables(listingId);
    setBracketsData(data);
    setState('brackets');
  };
  
  // Analyse a bracket - fires full pipeline
  const handleAnalyse = async (view: string, bracket: string, targetPrice: number) => {
    setState('loading');
    
    // This triggers: delta → pricing → timeline → images
    const result = await analysebracket(listingId, view, bracket, targetPrice);
    
    setRenovationOptions(result.options);
    setState('renovation_options');
  };
  
  // Back to brackets view
  const handleBack = () => {
    setState('brackets');
    setExpandedBracket(null);
  };
  
  return (
    <Card>
      {state === 'initial' && (
        <>
          <CardHeader>
            <CardTitle>Market Comparables</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-500 mb-4">
              Click Run to fetch market data and identify renovation paths.
            </p>
            <Button onClick={handleRun}>Run Analysis</Button>
          </CardContent>
        </>
      )}
      
      {state === 'loading' && (
        <CardContent className="py-8">
          <LoadingSpinner />
          <p className="text-center text-gray-500 mt-4">
            Fetching market data...
          </p>
        </CardContent>
      )}
      
      {state === 'brackets' && bracketsData && (
        <BracketsView
          data={bracketsData}
          onAnalyse={handleAnalyse}
        />
      )}
      
      {state === 'renovation_options' && (
        <RenovationOptionsView
          options={renovationOptions}
          expandedBracket={expandedBracket}
          onExpand={setExpandedBracket}
          onBack={handleBack}
        />
      )}
    </Card>
  );
};
```

```tsx
// components/renovation/RenovationOptionCard.tsx

export const RenovationOptionCard: React.FC<{
  option: RenovationOption;
  isExpanded: boolean;
  onExpand: () => void;
  onBack: () => void;
}> = ({ option, isExpanded, onExpand, onBack }) => {
  const { bracket, targetPrice, gap, renovationCost, timeline, margin, 
          scopeOfWork, beforeImage, afterImage, comparables, links } = option;
  
  const bracketEmoji = bracket === 'premium' ? '🔴' : bracket === 'fair_market' ? '🟡' : '🟢';
  const bracketLabel = bracket === 'premium' ? 'PREMIUM' : bracket === 'fair_market' ? 'FAIR MARKET' : 'FAST SELL';
  
  if (!isExpanded) {
    // Collapsed summary view
    return (
      <div className="border rounded-lg p-4 mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold">{bracketEmoji} {bracketLabel} PATH</h3>
          <button onClick={onBack} className="text-sm text-gray-500">← Back</button>
        </div>
        <p className="text-gray-600 mb-2">
          Target: €{targetPrice.toLocaleString()} | Gap: {gap >= 0 ? '+' : ''}€{gap.toLocaleString()}
        </p>
        <div className="flex gap-4 text-sm">
          <span>💰 Reno: €{renovationCost.toLocaleString()}</span>
          <span>⏱️ {timeline}</span>
          <span className={margin >= 0 ? 'text-green-600' : 'text-red-600'}>
            📈 Margin: €{margin.toLocaleString()}
          </span>
        </div>
        
        {/* Mini before/after preview */}
        <div className="flex gap-2 mt-3">
          <img src={beforeImage} className="w-20 h-14 rounded object-cover" />
          <span className="self-center">→</span>
          <img src={afterImage} className="w-20 h-14 rounded object-cover" />
        </div>
        
        <button 
          onClick={onExpand}
          className="mt-3 text-blue-600 text-sm"
        >
          View Full Plan ▼
        </button>
      </div>
    );
  }
  
  // Expanded full view
  return (
    <div className="border rounded-lg p-6 mb-4 bg-white">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">{bracketEmoji} {bracketLabel} PATH - Full Analysis</h3>
        <button onClick={onExpand} className="text-sm text-gray-500">Collapse ▲</button>
      </div>
      
      {/* THE MATH */}
      <section className="mb-6 p-4 bg-gray-50 rounded">
        <h4 className="font-semibold mb-3">📊 THE MATH</h4>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span>Asking price:</span>
            <span>€{option.askingPrice.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>+ Renovation:</span>
            <span>€{renovationCost.toLocaleString()}</span>
          </div>
          <div className="flex justify-between border-t pt-1 font-medium">
            <span>= Total Investment:</span>
            <span>€{(option.askingPrice + renovationCost).toLocaleString()}</span>
          </div>
          <div className="flex justify-between mt-2">
            <span>Target Value:</span>
            <span>€{targetPrice.toLocaleString()}</span>
          </div>
          <div className="flex justify-between border-t pt-1 font-medium">
            <span>= Potential Margin:</span>
            <span className={margin >= 0 ? 'text-green-600' : 'text-red-600'}>
              €{margin.toLocaleString()} {margin >= 0 ? '✅' : '❌'}
            </span>
          </div>
        </div>
      </section>
      
      {/* SCOPE OF WORK */}
      <section className="mb-6">
        <h4 className="font-semibold mb-3">📋 SCOPE OF WORK ({scopeOfWork.totalItems} line items)</h4>
        {scopeOfWork.categories.map(cat => (
          <div key={cat.name} className="mb-3">
            <div className="flex justify-between text-sm font-medium">
              <span>{cat.name}</span>
              <span>€{cat.total.toLocaleString()}</span>
            </div>
            <ul className="text-sm text-gray-600 ml-4">
              {cat.items.slice(0, 3).map((item, i) => (
                <li key={i}>• {item}</li>
              ))}
              {cat.items.length > 3 && (
                <li className="text-gray-400">+ {cat.items.length - 3} more items</li>
              )}
            </ul>
          </div>
        ))}
      </section>
      
      {/* TIMELINE */}
      <section className="mb-6">
        <h4 className="font-semibold mb-3">⏱️ TIMELINE</h4>
        <div className="text-sm space-y-1">
          {option.timelineBreakdown.map((phase, i) => (
            <div key={i} className="flex justify-between">
              <span className="text-gray-600">{phase.weeks}:</span>
              <span>{phase.description}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 font-medium">Estimated Duration: {timeline}</p>
      </section>
      
      {/* BEFORE/AFTER */}
      <section className="mb-6">
        <h4 className="font-semibold mb-3">🖼️ VISUALIZATION</h4>
        <div className="flex gap-4">
          <div className="flex-1">
            <p className="text-xs text-gray-500 mb-1">Before</p>
            <img src={beforeImage} className="w-full rounded" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-gray-500 mb-1">After ({bracketLabel})</p>
            <img src={afterImage} className="w-full rounded" />
          </div>
        </div>
      </section>
      
      {/* COMPARABLE CAROUSEL */}
      <section className="mb-6">
        <h4 className="font-semibold mb-3">🏠 COMPARABLE PROPERTIES ({bracketLabel} Bracket)</h4>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {comparables.map(comp => (
            <MiniListingCard key={comp.id} comparable={comp} />
          ))}
        </div>
      </section>
      
      {/* ORIGINAL LINKS */}
      <section>
        <h4 className="font-semibold mb-2">🔗 ORIGINAL LISTINGS</h4>
        <ul className="text-sm text-blue-600 space-y-1">
          {links.map((link, i) => (
            <li key={i}>
              <a href={link} target="_blank" rel="noopener noreferrer">
                {link}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};
```

```tsx
// components/renovation/MiniListingCard.tsx
// Same style as the main listing card but compact

export const MiniListingCard: React.FC<{
  comparable: ComparableProperty;
}> = ({ comparable }) => {
  return (
    <div className="flex-shrink-0 w-40 border rounded-lg overflow-hidden">
      <img 
        src={comparable.photo_urls[0]} 
        className="w-full h-24 object-cover"
        alt="Property"
      />
      <div className="p-2">
        <p className="font-semibold text-sm">€{comparable.sale_price.toLocaleString()}</p>
        <p className="text-xs text-gray-500">{comparable.total_area}m²</p>
        <p className="text-xs text-gray-500">{comparable.plot_area}m² plot</p>
        <a 
          href={comparable.property_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600"
        >
          View →
        </a>
      </div>
    </div>
  );
};
```
```

### API Endpoints for Comparables Card V2

```
# Initial fetch - just brackets, no full analysis yet
GET /api/renovation/{id}/comparables
    Response: {
      asking_price: 530000,
      casafari: {
        fast_sell: 470059,
        fair_market: 505440,
        premium: 540821,
        count: 6,
        comparables: [...] // Raw list with property_url, photos, etc.
      },
      filtered: {
        fast_sell: 330000,
        fair_market: 502250,
        premium: 590000,
        count: 4,
        comparables: [...] // Filtered list
      }
    }

# Analyse a specific bracket - triggers full pipeline
POST /api/renovation/{id}/comparables/analyse
    Body: {
      view: "filtered",           // or "casafari"
      bracket: "premium",         // "fast_sell" | "fair_market" | "premium"
      target_price: 590000
    }
    
    Response: {
      options: [{
        bracket: "premium",
        view: "filtered",
        target_price: 590000,
        asking_price: 530000,
        gap: 60000,
        
        // From KGEstimator
        renovation_cost: 55004,
        scope_of_work: {
          total_items: 47,
          categories: [
            { name: "ELECTRICAL", total: 8200, items: [...] },
            { name: "PLUMBING", total: 6400, items: [...] },
            ...
          ]
        },
        
        // The math
        total_investment: 585004,
        margin: 4996,
        
        // Timeline
        timeline: "8-10 weeks",
        timeline_breakdown: [
          { weeks: "Week 1-2", description: "Demolition, electrical rough-in" },
          ...
        ],
        
        // Visuals
        before_image: "https://...",
        after_image: "https://...",
        
        // Comparables for this bracket
        comparables: [
          {
            property_id: 123,
            sale_price: 600000,
            total_area: 150,
            plot_area: 400,
            photo_urls: [...],
            property_url: "https://casafari.com/..."
          },
          ...
        ],
        
        // Original links
        links: [
          "https://casafari.com/home-sale/property-20658331616",
          ...
        ]
      }]
    }
```

### Agent Script When Premium is Above Asking

> "Based on comparable renovated properties in the area:
> 
> Your listing at **€530,000** is positioned **below the premium bracket** (€590,000).
> 
> For buyers, this means:
> - Renovation budget of ~€55,000 could unlock €590,000 value
> - Total investment: €585,000
> - Potential margin: €5,000
> 
> This positions the property as a **value-add opportunity** for renovation buyers."

### Agent Script When All Brackets Below Asking

> "Based on comparable renovated properties in the area:
> 
> The market data shows renovated properties selling at **€505,440** (fair market).
> 
> Your listing at **€530,000** is positioned in the **aspirational range**.
> 
> This may require:
> - Patient buyers recognizing unique value
> - Negotiation flexibility
> - Highlighting features not captured in basic comparables"

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-07 | Initial architecture design |
| 1.1 | 2026-01-07 | Added Comparables Card V2 dual-view architecture |
| 1.2 | 2026-01-08 | **IMPLEMENTATION COMPLETE**: Casafari API, database tables, API endpoints, ComparablesCard UI with state machine, dual view, "Analyse All" button. Updated checklist with completion status. |

---

*Document maintained by: Puedo Casa Engineering*

