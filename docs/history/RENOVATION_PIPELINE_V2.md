# Renovation Pipeline V2 - Implementation Plan

## 📋 Executive Summary

**What Was Built (V1):** A monolithic pipeline that generates two packages (Essential/Modern) in one shot with aggregated pricing.

**What You Want (V2):** Three **separate, sequential cards** with individual Run buttons:
1. **Card 1: Condition Assessment** → Room-by-room defect detection (THE DIAGNOSIS)
2. **Card 2: Package Scopes** → Remedial actions mapped to packages (THE RECOMMENDATION)
3. **Card 3: Pricing Breakdown** → KG Estimator with full BoQ (THE EVIDENCE)

**Critical Workflow:** Each card outputs must be **verified visually** before running the next card. No automatic chaining.

Each card depends on the previous card's output. Integration comes later.

---

## 🧠 The Rules Engine Schema (Enhanced)

The `rules_engine.json` is the **lens** for Gemini. Each rule contains its own inspection prompt:

```json
{
  "id": "ELEC_REBT_001",
  "system": "electrical",
  "year_trigger": 2002,
  "visual_triggers": ["black fuse box", "ceramic fuses", "2-pin sockets", "cloth wiring"],
  "condition_assessment": {
    "prompt_instruction": "Inspect electrical points. Are mechanisms modern (white/plastic) or vintage (black/bakelite)? Look for earth pins.",
    "risk_label": "Non-Compliant (REBT 2002)",
    "risk_description": "Installation predates current safety standards. High risk of fire and inspection failure."
  },
  "remedial_action": {
    "task_id": "rewrite_electrical_installation",
    "bcca_keyword": "instalación eléctrica vivienda completa",
    "package": "ESSENTIAL"
  }
}
```

**Key Fields:**
- `prompt_instruction` — Tells Gemini exactly what to look for (per rule)
- `bcca_keyword` — Direct search term for Knowledge Graph (no hallucination)
- `trigger_type` — Output will show "implied_by_age" vs "visual_match"

---

## 🔄 Key Differences from V1

| Aspect | V1 (What I Built) | V2 (What You Want) |
|--------|-------------------|-------------------|
| **Output Granularity** | Whole-house totals | Room-by-room breakdown |
| **Pipeline Flow** | Single Run button, 4 phases | 3 separate Run buttons |
| **Pricing Engine** | Simplified unit prices | Full KG Estimator (`RenovationEstimator`) |
| **Package Logic** | Age-based + visual triggers | Strict ITE/CTE compliance mapping |
| **Essential Definition** | "Safety" (vague) | **ITE + Cédula de Habitabilidad** (specific) |
| **Modern Definition** | "Comfort" (vague) | **CTE 2025 + Green Mortgage** (specific) |
| **Frontend** | Two package cards | Three pipeline stage cards |

---

## 🏗️ The V2 Architecture

### Card 1: Condition Assessment (Forensic Analysis)

**Purpose:** Detect defects room-by-room using Rules Engine + Gemini Vision

**Input:**
- Photo clusters (from existing P1 step)
- Year built (from listing)
- `rules_engine.json`

**Output Schema:**
```json
{
  "listing_id": 6,
  "year_built": 1988,
  "room_assessments": [
    {
      "room_id": "kitchen_01",
      "room_type": "cocina",
      "room_name": "Kitchen",
      "photo_urls": ["..."],
      "detected_conditions": [
        {
          "rule_id": "ELEC_REBT_001",
          "trigger_type": "implied_by_age",
          "system": "electrical",
          "observation": "Building is 1988. No visual evidence of renovation. Wiring is assumed original.",
          "confidence": "High",
          "risk_label": "Non-Compliant (REBT 2002)",
          "package": "ESSENTIAL"
        },
        {
          "rule_id": "ENV_WIN_001",
          "trigger_type": "visual_match",
          "system": "envelope",
          "observation": "Detected silver aluminum sliding windows. Non-compliant with CTE.",
          "confidence": "High",
          "risk_label": "Thermal Bridge / Low Efficiency",
          "package": "MODERN"
        }
      ]
    }
  ]
}
```

**Key Distinction:**
- `trigger_type: "implied_by_age"` — We didn't SEE it, but year dictates it
- `trigger_type: "visual_match"` — We SAW it in the photos

**UI Card:**
```
┌─────────────────────────────────────────────┐
│ 🔍 Condition Assessment                [Run]│
├─────────────────────────────────────────────┤
│ Year Built: 1988                            │
│ Implied Risks: 3 (Pre-REBT, Pre-CTE, etc)   │
│                                             │
│ ▼ Living Room (2 defects)                   │
│   ├─ ⚠️ Electrical: No grounding [SAFETY]   │
│   └─ ⚠️ Windows: Single glazing [ENERGY]    │
│                                             │
│ ▼ Kitchen (3 defects)                       │
│   ├─ ⚠️ Plumbing: Galvanized pipes [HEALTH] │
│   ├─ ⚠️ Electrical: Insufficient circuits   │
│   └─ ⚠️ Ventilation: No extraction [LEGAL]  │
│                                             │
│ ▼ Bathroom (1 defect)                       │
│   └─ ⚠️ Waterproofing: None visible [LEGAL] │
└─────────────────────────────────────────────┘
```

---

### Card 2: Package Scopes (Remedial Mapping)

**Purpose:** Map defects → remedial actions → packages (ESSENTIAL vs MODERN)

**Input:**
- `condition_assessment` from Card 1
- `rules_engine.json` (remedial_action lookup)

**Logic:**
```python
for defect in all_defects:
    action = rules_engine[defect.rule_triggered].remedial_action
    
    if defect.category in ["SAFETY", "LEGAL", "STRUCTURAL", "HYGIENE"]:
        essential_scope.append(action)  # Minimum spec
    
    if defect.category in ["ENERGY", "COMFORT", "ACOUSTIC"]:
        modern_scope.append(action)  # CTE spec

# Modern INHERITS all Essential items (upgraded spec)
modern_scope = essential_scope + modern_scope
```

**Output Schema:**
```json
{
  "listing_id": 6,
  "packages": {
    "essential": {
      "name": "ESSENTIAL",
      "goal": "Pass ITE + Obtain Cédula de Habitabilidad",
      "standard": "REBT 2002, CTE DB-HS 4",
      "scopes": [
        {
          "room": "Kitchen",
          "tasks": [
            {
              "task_id": "rewrite_electrical_installation",
              "title": "Complete Electrical Rewire",
              "bcca_keyword": "instalación eléctrica vivienda completa",
              "defect_source": "ELEC_REBT_001",
              "trigger_type": "implied_by_age",
              "risk_label": "Non-Compliant (REBT 2002)",
              "regulation": "REBT 2002"
            }
          ]
        }
      ]
    },
    "modern": {
      "name": "MODERN",
      "goal": "Meet CTE 2025 + Green Mortgage Eligible",
      "standard": "CTE DB-HE 1, CTE DB-HE 4, CTE DB-HR",
      "scopes": [
        {
          "room": "Kitchen",
          "tasks": [
            {
              "task_id": "rewrite_electrical_installation",
              "title": "Complete Electrical Rewire",
              "bcca_keyword": "instalación eléctrica vivienda completa",
              "inherited_from": "ESSENTIAL",
              "spec_upgrade": "Enhanced capacity for heat pump + EV"
            },
            {
              "task_id": "install_pvc_windows",
              "title": "Replace Windows (PVC Triple Glazing)",
              "bcca_keyword": "ventana pvc oscilobatiente 120x120",
              "defect_source": "ENV_WIN_001",
              "trigger_type": "visual_match",
              "risk_label": "Thermal Bridge / Low Efficiency",
              "regulation": "CTE DB-HE 1"
            }
          ]
        }
      ]
    }
  }
}
```

**⚠️ CONSTRAINT:** Card 2 outputs **NO PRICES**. Just the clean list of "What Needs To Be Done" with `bcca_keyword` for later lookup. Verify this matches the photos before running Card 3.

**UI Card:**
```
┌─────────────────────────────────────────────┐
│ 📦 Package Scopes                      [Run]│
├─────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ 🛡️ ESSENTIAL    │ │ 🌿 MODERN           │ │
│ │ ITE + Cédula    │ │ CTE 2025 + Green    │ │
│ │                 │ │                     │ │
│ │ 5 tasks         │ │ 12 tasks            │ │
│ │ 3 rooms         │ │ 4 rooms             │ │
│ └─────────────────┘ └─────────────────────┘ │
│                                             │
│ ▼ ESSENTIAL Scope                           │
│   Living Room:                              │
│   ├─ Complete Electrical Rewire [REBT 2002] │
│   Kitchen:                                  │
│   ├─ Replace Galvanized Pipes [CTE DB-HS]   │
│   ├─ Install Kitchen Extraction [CTE DB-HS] │
│   Bathroom:                                 │
│   └─ Waterproof Wet Areas [CTE DB-HS]       │
│                                             │
│ ▼ MODERN Scope (includes Essential)         │
│   + All ESSENTIAL items (upgraded spec)     │
│   + Window Replacement (Triple Glazing)     │
│   + Wall Insulation (SATE/Internal)         │
│   + Heat Pump Installation (Aerotermia)     │
└─────────────────────────────────────────────┘
```

---

### Card 3: Pricing Breakdown (KG Estimator)

**Purpose:** Price each scope using `RenovationEstimator` (the Knowledge Graph)

**Input:**
- `package_scopes` from Card 2
- `RenovationEstimator` (existing in `experiments/renovation_costing/`)

**Process:**
```python
from experiments.renovation_costing.renovation_resolver import RenovationResolver

resolver = RenovationResolver()

for package in ["essential", "modern"]:
    for scope in package.scopes:
        for task in scope.tasks:
            # Generate search keywords for BCCA
            keywords = generate_bcca_keywords(task)
            
            # Run through KG Estimator
            result = resolver.estimate(
                task_description=task.title,
                room=scope.room,
                quality_tier="economy" if package == "essential" else "standard"
            )
            
            task.boq = result.boq_lines
            task.total = result.total_pec
```

**Output Schema:**
```json
{
  "listing_id": 6,
  "packages": {
    "essential": {
      "total_pec": 12500,
      "total_pem": 10200,
      "trades": [
        {
          "trade": "Electricidad",
          "subtotal": 4500,
          "items": [
            {
              "bcca_code": "IEE010",
              "description": "Instalación eléctrica completa vivienda",
              "unit": "m²",
              "quantity": 75,
              "unit_price": 48.50,
              "total": 3637.50
            }
          ]
        }
      ],
      "room_breakdown": [
        {
          "room": "Living Room",
          "tasks": [
            {
              "title": "Complete Electrical Rewire",
              "boq_lines": [...],
              "subtotal": 1200
            }
          ],
          "room_total": 1200
        }
      ]
    },
    "modern": {
      "total_pec": 38000,
      ...
    }
  }
}
```

**UI Card:**
```
┌─────────────────────────────────────────────┐
│ 💰 Pricing Breakdown                   [Run]│
├─────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ 🛡️ ESSENTIAL    │ │ 🌿 MODERN           │ │
│ │ €12,500         │ │ €38,000             │ │
│ │ PEC (inc. 19%)  │ │ PEC (inc. 19%)      │ │
│ └─────────────────┘ └─────────────────────┘ │
│                                             │
│ ▼ ESSENTIAL Breakdown by Trade              │
│   Electricidad: €4,500                      │
│   ├─ IEE010 Instalación eléctrica (75m²)    │
│   │  48.50€/m² = €3,637.50                  │
│   └─ IEP010 Punto de luz (12ud)             │
│      35.20€/ud = €422.40                    │
│   Fontanería: €3,200                        │
│   ├─ IFB010 Tubería PEX (45ml)              │
│   └─ IFC010 Calentador (1ud)                │
│   Albañilería: €2,800                       │
│   └─ ...                                    │
│                                             │
│ ▼ ESSENTIAL Breakdown by Room               │
│   Living Room: €1,200                       │
│   Kitchen: €4,800                           │
│   Bathroom: €3,500                          │
│   General: €3,000                           │
└─────────────────────────────────────────────┘
```

---

## 📁 Files to Create/Modify

### Backend (`Lean MVP/backend/`)

| File | Action | Purpose |
|------|--------|---------|
| `pipeline/rules_engine.json` | **MODIFY** | Add `prompt_instruction`, `bcca_keyword`, enhanced schema |
| `pipeline/steps/analyze_room.py` | **CREATE** | Card 1: Room-by-room Gemini analysis |
| `pipeline/steps/map_to_scope.py` | **CREATE** | Card 2: Defect → Remedial Action mapper |
| `pipeline/steps/price_scope.py` | **CREATE** | Card 3: KG Estimator integration |
| `pipeline/orchestrator.py` | **MODIFY** | Add sections 5, 6, 7 |

### Frontend (`Lean MVP/frontend/`)

| File | Action | Purpose |
|------|--------|---------|
| `src/components/renovation/ConditionCard.tsx` | **CREATE** | Card 1 UI |
| `src/components/renovation/ScopesCard.tsx` | **CREATE** | Card 2 UI |
| `src/components/renovation/PricingCard.tsx` | **CREATE** | Card 3 UI |
| `src/types/renovation.ts` | **MODIFY** | Add new schemas |
| `src/app/listing/[id]/page.tsx` | **MODIFY** | Add 3 cards to Renovation tab |

### Database

| Table | Action | Purpose |
|-------|--------|---------|
| `condition_assessments` | **CREATE** | Store Card 1 output |
| `package_scopes` | **CREATE** | Store Card 2 output |
| `package_pricing` | **CREATE** | Store Card 3 output |

---

## 🔧 Implementation Order

### Phase 1: Card 1 - Condition Assessment (Standalone)
1. Create `condition_assessment.py` with Gemini Vision analysis
2. Create `ConditionCard.tsx` with room accordion UI
3. Add pipeline section 5: "Condition Assessment"
4. Test: Run on listing 6, verify room-by-room output

### Phase 2: Card 2 - Package Scopes (Depends on Card 1)
1. Create `package_scopes.py` with defect→action mapping
2. Create `ScopesCard.tsx` with Essential/Modern split
3. Add pipeline section 6: "Package Scopes"
4. Test: Verify correct categorization (SAFETY→Essential, ENERGY→Modern)

### Phase 3: Card 3 - Pricing (Depends on Card 2)
1. Integrate `RenovationResolver` from `experiments/`
2. Create `package_pricing.py` with KG estimation
3. Create `PricingCard.tsx` with trade/room breakdown
4. Add pipeline section 7: "Package Pricing"
5. Test: Verify BoQ matches BCCA codes

### Phase 4: Integration (Later)
1. Chain the three cards together
2. Add "Run All" button
3. Add progress indicator showing which stage is complete

---

## ✅ Acceptance Criteria

### Card 1: Condition Assessment
- [ ] Shows year built and implied risks
- [ ] Lists defects PER ROOM (not aggregated)
- [ ] Each defect has: system, observation, evidence level, rule triggered
- [ ] Accordion expands to show photo evidence
- [ ] Run button triggers only this step

### Card 2: Package Scopes
- [ ] Shows ESSENTIAL and MODERN as separate sections
- [ ] ESSENTIAL only includes SAFETY/LEGAL/STRUCTURAL/HYGIENE
- [ ] MODERN inherits ALL Essential items
- [ ] Each task shows: title, spec, regulation citation
- [ ] Run button triggers only this step (requires Card 1 complete)

### Card 3: Pricing Breakdown
- [ ] Uses `RenovationEstimator` (not simplified prices)
- [ ] Shows breakdown BY TRADE (Electricidad, Fontanería, etc.)
- [ ] Shows breakdown BY ROOM
- [ ] Each line has BCCA code, unit, quantity, unit price, total
- [ ] Shows PEM and PEC (with 19% overhead)
- [ ] Run button triggers only this step (requires Card 2 complete)

---

## 🚨 What Needs to Change from V1

1. **Delete monolithic approach** - Remove `run_full_renovation_report` single step
2. **Update `rules_engine.json`** - Add proper category tags (SAFETY, LEGAL, ENERGY, COMFORT)
3. **Import KG Estimator** - Bring `RenovationResolver` into the Lean MVP backend
4. **Room-centric output** - Restructure all schemas to be room-first, not package-first
5. **Three separate pipeline sections** - Not one section with 4 internal steps

---

---

## 🧹 Phase 0: Clean Slate (Before Any Code)

### 0.1 Archive V1 Code
```bash
# Move old renovation_report.py to archive
mv pipeline/steps/renovation_report.py pipeline/steps/_archive/renovation_report_v1.py

# Remove section 5 from orchestrator (we'll re-add properly)
```

### 0.2 Define Shared Schemas
**Backend:** `pipeline/schemas/renovation.py`
```python
@dataclass
class DetectedCondition:
    rule_id: str
    trigger_type: str  # "implied_by_age" | "visual_match"
    system: str
    observation: str
    confidence: str
    risk_label: str
    package: str  # "ESSENTIAL" | "MODERN"

@dataclass
class RoomAssessment:
    room_id: str
    room_type: str
    room_name: str
    photo_urls: List[str]
    detected_conditions: List[DetectedCondition]

@dataclass
class ScopeTask:
    task_id: str
    title: str
    bcca_keyword: str
    defect_source: str
    trigger_type: str
    risk_label: str
    regulation: str
    inherited_from: Optional[str] = None
    spec_upgrade: Optional[str] = None

@dataclass
class BoQLine:
    bcca_code: str
    description: str
    unit: str
    quantity: float
    unit_price: float
    total: float
```

**Frontend:** `types/renovation-v2.ts` (matching TypeScript interfaces)

### 0.3 Database Migrations
```sql
-- 005_condition_assessments.sql
CREATE TABLE condition_assessments (
  id SERIAL PRIMARY KEY,
  listing_id INTEGER REFERENCES listings(id),
  room_id TEXT NOT NULL,
  room_type TEXT NOT NULL,
  room_name TEXT,
  photo_urls JSONB,
  detected_conditions JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(listing_id, room_id)
);

-- 006_package_scopes.sql
CREATE TABLE package_scopes (
  id SERIAL PRIMARY KEY,
  listing_id INTEGER REFERENCES listings(id),
  package_type TEXT NOT NULL,
  goal TEXT,
  standard TEXT,
  scopes JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(listing_id, package_type)
);

-- 007_package_pricing.sql
CREATE TABLE package_pricing (
  id SERIAL PRIMARY KEY,
  listing_id INTEGER REFERENCES listings(id),
  package_type TEXT NOT NULL,
  total_pem NUMERIC,
  total_pec NUMERIC,
  trade_breakdown JSONB,
  room_breakdown JSONB,
  boq_lines JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(listing_id, package_type)
);
```

---

## 📦 Phase 1: Card 1 - Condition Assessment

### 1.1 Enhanced Rules Engine
**File:** `pipeline/rules_engine_v2.json`

Generate from `standards/*.md` with this structure per rule:
```json
{
  "id": "ELEC_REBT_001",
  "system": "electrical",
  "room_types": ["cocina", "salon", "dormitorio", "baño"],
  "year_trigger": 2002,
  "visual_triggers": ["black fuse box", "ceramic fuses", "2-pin sockets", "cloth wiring"],
  "condition_assessment": {
    "prompt_instruction": "Inspect electrical points. Are mechanisms modern (white/plastic) or vintage (black/bakelite)? Look for earth pins.",
    "risk_label": "Non-Compliant (REBT 2002)",
    "risk_description": "Installation predates current safety standards."
  },
  "remedial_action": {
    "task_id": "rewrite_electrical_installation",
    "bcca_keyword": "instalación eléctrica vivienda completa",
    "package": "ESSENTIAL",
    "category": "SAFETY"
  }
}
```

### 1.2 Room Analyzer Script
**File:** `pipeline/steps/analyze_room.py`

```python
async def analyze_room(listing_id: int, room_id: str, photos: List[str], year_built: int) -> RoomAssessment:
    """
    Analyze a single room for defects using Rules Engine + Gemini Vision.
    
    1. Load rules_engine_v2.json
    2. Filter rules relevant to room_type
    3. Check age triggers (implied_by_age)
    4. Send photos to Gemini with rule.prompt_instruction
    5. Check visual triggers (visual_match)
    6. Return RoomAssessment with detected_conditions
    """

async def run_condition_assessment(orchestrator, listing_id: int) -> Dict:
    """
    Pipeline step handler for Section 5.
    Analyzes ALL rooms for a listing.
    Saves results to condition_assessments table.
    """
```

### 1.3 Frontend Card
**File:** `components/renovation/ConditionCard.tsx`

```tsx
// UI Structure:
// ┌─────────────────────────────────────────────┐
// │ 🔍 Condition Assessment                [Run]│
// ├─────────────────────────────────────────────┤
// │ Year Built: 1988                            │
// │                                             │
// │ ▼ Kitchen (3 defects)                       │
// │   ├─ ⚠️ Electrical [implied_by_age]         │
// │   ├─ ❌ Windows [visual_match]              │
// │   └─ ℹ️ Finishes [visual_match]             │
// │                                             │
// │ ▼ Bathroom (1 defect)                       │
// │   └─ ⚠️ Waterproofing [implied_by_age]      │
// └─────────────────────────────────────────────┘
```

### 1.4 API Routes
- Backend: `GET/POST /api/listings/{id}/condition-assessment`
- Frontend proxy: `app/api/listings/[id]/condition-assessment/route.ts`

### 1.5 Definition of Done (Production-Ready)

**UI Must Work:**
- [ ] Card visible in Renovation tab at `/listing/6`
- [ ] Run button triggers real pipeline (no mock data)
- [ ] Loading state shows during Gemini analysis
- [ ] Results persist in database (refresh page, data still there)
- [ ] Error states handled (no photos, API failure)

**Data Quality (Anti-Pareto):**
- [ ] ALL rooms from photo_clusters analyzed (not just "main" rooms)
- [ ] ALL systems checked: Electrical, Plumbing, Windows, Structure, Finishes, HVAC
- [ ] Age-implied risks generated even if no photos show defects
- [ ] Each condition has: rule_id, trigger_type, observation, risk_label
- [ ] Empty room handled gracefully (shows "No defects detected")

**Test on Listing 6:**
- [ ] Run analysis, verify each room appears
- [ ] Check trigger_type accuracy (implied vs visual)
- [ ] Refresh page, data persists
- [ ] Run again, updates existing data (no duplicates)

**⛔ DO NOT proceed to Phase 2 until all boxes checked**

---

## 📦 Phase 2: Card 2 - Package Scopes

### 2.1 Scope Mapper Script
**File:** `pipeline/steps/map_to_scope.py`

```python
async def map_defects_to_scope(listing_id: int) -> Dict:
    """
    Map detected conditions to remedial actions.
    
    1. Load condition_assessments from DB
    2. For each condition, lookup remedial_action in rules_engine
    3. Categorize:
       - SAFETY, LEGAL, STRUCTURAL, HYGIENE → ESSENTIAL
       - ENERGY, COMFORT, ACOUSTIC → MODERN
    4. Modern inherits all Essential (with spec_upgrade)
    5. Save to package_scopes table
    
    OUTPUT: bcca_keyword list per package (NO PRICES)
    """
```

### 2.2 Frontend Card
**File:** `components/renovation/ScopesCard.tsx`

```tsx
// UI Structure:
// ┌─────────────────────────────────────────────┐
// │ 📦 Package Scopes                      [Run]│
// ├─────────────────────────────────────────────┤
// │ ┌─────────────┐ ┌───────────────────────┐   │
// │ │ 🛡️ ESSENTIAL│ │ 🌿 MODERN             │   │
// │ │ 5 tasks     │ │ 12 tasks              │   │
// │ └─────────────┘ └───────────────────────┘   │
// │                                             │
// │ ▼ ESSENTIAL Scope                           │
// │   Kitchen:                                  │
// │   ├─ Electrical Rewire [REBT 2002]          │
// │   ├─ Replace Pipes [CTE DB-HS]              │
// │                                             │
// │ ▼ MODERN Scope                              │
// │   + All ESSENTIAL items                     │
// │   + Window Replacement [CTE DB-HE]          │
// └─────────────────────────────────────────────┘
// 
// ⚠️ NO PRICES SHOWN - just tasks with bcca_keyword
```

### 2.3 Definition of Done (Production-Ready)

**UI Must Work:**
- [ ] Card visible in Renovation tab at `/listing/6`
- [ ] Run button DISABLED if Card 1 not complete (shows tooltip)
- [ ] Run button triggers real mapping (no mock data)
- [ ] Results persist in database
- [ ] Shows ESSENTIAL and MODERN as separate expandable sections

**Data Quality (Anti-Pareto):**
- [ ] EVERY detected_condition from Card 1 maps to a remedial_action
- [ ] NO orphan defects (every defect → task)
- [ ] ESSENTIAL contains ONLY: SAFETY, LEGAL, STRUCTURAL, HYGIENE categories
- [ ] MODERN contains: ALL Essential items + ENERGY, COMFORT, ACOUSTIC
- [ ] Each task has: task_id, title, bcca_keyword, defect_source, regulation
- [ ] Permits included if structural work detected
- [ ] Cleanup/demolition tasks included where applicable

**Test on Listing 6:**
- [ ] Run scope mapping after Card 1 complete
- [ ] Verify ESSENTIAL task count matches SAFETY/LEGAL defects
- [ ] Verify MODERN inherits all ESSENTIAL tasks
- [ ] Check bcca_keyword exists for EVERY task (no nulls)
- [ ] Refresh page, data persists

**⛔ DO NOT proceed to Phase 3 until all boxes checked**

---

## 📦 Phase 3: Card 3 - Pricing

### 3.1 KG Estimator Integration
**File:** `pipeline/steps/price_scope.py`

```python
async def price_packages(listing_id: int) -> Dict:
    """
    Price package scopes using RenovationEstimator (Knowledge Graph).
    
    1. Load package_scopes from DB
    2. Import RenovationResolver from experiments/renovation_costing/
    3. For each task:
       - Pass bcca_keyword to resolver
       - Get BoQ lines with BCCA codes, quantities, prices
    4. Aggregate by trade (Electricidad, Fontanería, etc.)
    5. Aggregate by room
    6. Calculate PEM and PEC (+19% overhead)
    7. Save to package_pricing table
    """
```

### 3.2 Frontend Card
**File:** `components/renovation/PricingCard.tsx`

```tsx
// UI Structure:
// ┌─────────────────────────────────────────────┐
// │ 💰 Pricing Breakdown                   [Run]│
// ├─────────────────────────────────────────────┤
// │ ┌─────────────┐ ┌───────────────────────┐   │
// │ │ 🛡️ ESSENTIAL│ │ 🌿 MODERN             │   │
// │ │ €12,500     │ │ €38,000               │   │
// │ └─────────────┘ └───────────────────────┘   │
// │                                             │
// │ [By Trade] [By Room]                        │
// │                                             │
// │ ▼ Electricidad: €4,500                      │
// │   ├─ IEE010 Instalación (75m²) €3,637       │
// │   └─ IEP010 Puntos luz (12ud) €422          │
// │                                             │
// │ ▼ Fontanería: €3,200                        │
// │   └─ ...                                    │
// └─────────────────────────────────────────────┘
```

### 3.3 Definition of Done (Production-Ready)

**UI Must Work:**
- [ ] Card visible in Renovation tab at `/listing/6`
- [ ] Run button DISABLED if Card 2 not complete (shows tooltip)
- [ ] Run button triggers real KG Estimator (no mock prices)
- [ ] Results persist in database
- [ ] Shows totals for ESSENTIAL and MODERN
- [ ] Toggle between "By Trade" and "By Room" views
- [ ] Expandable sections show full BoQ lines

**Data Quality (Anti-Pareto):**
- [ ] EVERY task from Card 2 has pricing (no unpriced tasks)
- [ ] BCCA codes are REAL (exist in BCCA database)
- [ ] Quantities calculated from property m² (not hardcoded)
- [ ] Unit prices from BCCA (not invented)
- [ ] PEM calculated (sum of line items)
- [ ] PEC calculated (PEM × 1.19 for overheads)
- [ ] Trade breakdown sums to total
- [ ] Room breakdown sums to total
- [ ] Permits line item included if structural work
- [ ] Cleanup/waste disposal line items included

**Test on Listing 6 (130m²):**
- [ ] Run pricing after Card 2 complete
- [ ] Verify ESSENTIAL total is reasonable (€10k-30k range for 1988 property)
- [ ] Verify MODERN total > ESSENTIAL (inherits + adds)
- [ ] Spot-check 3 BCCA codes manually (are they real?)
- [ ] Verify electrical quantity ~= 130m² × factor
- [ ] Refresh page, data persists

**⛔ Phase 3 complete = FULL PRODUCTION PIPELINE WORKING**

---

## 🛡️ Anti-Pareto Philosophy

**The rule:** Each phase must be COMPLETE before moving on. No "we'll fix it later."

**Applied at EACH phase, not just at the end:**

| Phase | Anti-Pareto Check |
|-------|-------------------|
| Phase 1 | ALL rooms analyzed, ALL systems checked, no skipped clusters |
| Phase 2 | EVERY defect maps to action, permits if structural, cleanup included |
| Phase 3 | EVERY task priced, real BCCA codes, real quantities, waste disposal |

**What "No Pareto" means:**
- ❌ "We'll add permits later" → Must be in Phase 2
- ❌ "Cleanup is boring, skip it" → Must be in Phase 2 & 3
- ❌ "Just price the main items" → Must price ALL items in Phase 3
- ❌ "Mock data for now" → Real data from Phase 1 onwards
- ❌ "Only analyze living room" → ALL rooms from photo_clusters

**Edge cases that MUST work:**
- Empty room (no defects) → Shows "No issues detected"
- No photos for room → Shows "Unable to analyze (no photos)"
- Very old property (pre-1950) → Many implied_by_age flags
- Recently renovated → Few defects, mostly MODERN upgrades

---

## 📁 Final File Structure

```
Lean MVP/backend/
├── pipeline/
│   ├── rules_engine_v2.json
│   ├── schemas/
│   │   └── renovation.py
│   ├── steps/
│   │   ├── analyze_room.py        # Card 1
│   │   ├── map_to_scope.py        # Card 2
│   │   ├── price_scope.py         # Card 3
│   │   └── _archive/
│   │       └── renovation_report_v1.py
│   └── orchestrator.py            # Sections 5, 6, 7
├── routes/
│   └── renovation.py
└── migrations/
    ├── 005_condition_assessments.sql
    ├── 006_package_scopes.sql
    └── 007_package_pricing.sql

Lean MVP/frontend/
├── src/
│   ├── types/
│   │   └── renovation-v2.ts
│   ├── components/renovation/
│   │   ├── ConditionCard.tsx
│   │   ├── ScopesCard.tsx
│   │   ├── PricingCard.tsx
│   │   └── index.ts
│   └── app/api/listings/[id]/
│       ├── condition-assessment/route.ts
│       ├── package-scopes/route.ts
│       └── package-pricing/route.ts
```

---

## 🎯 The Vibe Code Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  rules_engine.json                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • prompt_instruction (per rule)                           │  │
│  │ • year_trigger + visual_triggers                          │  │
│  │ • bcca_keyword (direct KG lookup)                         │  │
│  │ • package: ESSENTIAL | MODERN                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Card 1: analyze_room.py                                   │  │
│  │ • Load rules for room_type                                │  │
│  │ • Gemini: "Check for these visual triggers..."            │  │
│  │ • Output: detected_conditions (implied_by_age | visual)   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                     [VERIFY OUTPUT]                             │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Card 2: map_to_scope.py                                   │  │
│  │ • Defect → remedial_action lookup                         │  │
│  │ • Split into essential_scope / modern_scope               │  │
│  │ • Output: bcca_keyword list (NO PRICES YET)               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                     [VERIFY OUTPUT]                             │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Card 3: price_scope.py                                    │  │
│  │ • Pass bcca_keyword to RenovationEstimator                │  │
│  │ • Output: Full BoQ with BCCA codes, quantities, prices    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Ready to Start?

Which phase should we begin with?

**Recommended:** Start with **Phase 1 (Card 1 - Condition Assessment)** since it's standalone and will give us the foundation for the other cards.

**Phase 1 Deliverables:**
1. Enhanced `rules_engine.json` with `prompt_instruction` and `bcca_keyword`
2. `analyze_room.py` script that outputs `detected_conditions`
3. `ConditionCard.tsx` UI with room accordion
4. Test: Run on listing 6, verify room-by-room output visually

Reply with:
- `"Phase 1"` to start building the Condition Assessment card
- `"Questions"` if anything needs clarification
- `"Modify X"` if you want to change something in this plan

