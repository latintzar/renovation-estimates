Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Renovation Pipeline V3 - Complete Plan

## Executive Summary

**Goal:** "How to achieve those newly renovated houses' efficiency/functionality/design/look/finish, and how much would it cost."

**Philosophy:** 
- LLM for creative analysis (where it shines)
- KG for completeness (where it shines)  
- Code for math (where it shines)
- No hallucination, no missed tasks, no convoluted architecture

---

## Current State vs Target State

```
CURRENT (V2):                           TARGET (V3):
═════════════                           ═════════════

Gap Analysis                            Gap Analysis
    │                                       │
    ▼                                       ▼
Freeform task text ──────────────▶     Rich prose per room
    │                                       │
    ▼                                       ▼
Gemini GUESSES KG tasks ─────────▶     Gemini EXTRACTS terminal tasks
(lossy, misses stuff)                  (structured, from KG vocabulary)
    │                                       │
    ▼                                       ▼
Selective traversal ─────────────▶     FULL backward traversal
(filtered, incomplete)                 (all prerequisites found)
    │                                       │
    ▼                                       ▼
Generic task list ───────────────▶     Two outputs:
                                       • Customer: Layman summary
                                       • Architect: Full BoQ + specs
```

---

## The Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RENOVATION PIPELINE V3                               │
│                                                                              │
│  "Make it like those nice renovated houses - what does it take?"            │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │  INPUT: Property + Comparables   │
                    │  • Photos per room               │
                    │  • Scraped data                  │
                    │  • Similar sold properties       │
                    │  • Target bracket                │
                    └───────────────┬─────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 1: GAP ANALYSIS              │   WHO: LLM (Gemini)
 (Creative, Nuanced)               │   WHY: Pattern recognition, context
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  Gemini analyzes:               │
                    │  • What's wrong with target?    │
                    │  • What do comparables have?    │
                    │  • What's the gap?              │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  OUTPUT: Rich prose per room (GapAnalysisResult)                      │
    │                                                                       │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │ room_id: "baño_principal"                                       │  │
    │  │ room_type: "wet"                                                │  │
    │  │                                                                 │  │
    │  │ gap_narrative: """                                              │  │
    │  │   El baño presenta un aspecto anticuado con sanitarios de los  │  │
    │  │   años 80 (cisterna vista, modelo Roca Victoria), azulejos de  │  │
    │  │   15x15 en mal estado con juntas ennegrecidas y múltiples      │  │
    │  │   grietas. La instalación eléctrica carece de diferencial      │  │
    │  │   visible y presenta cables expuestos en zona de ducha         │  │
    │  │   (incumplimiento grave REBT ITC-BT-27).                       │  │
    │  │                                                                 │  │
    │  │   Los comparables en este rango de precio muestran baños       │  │
    │  │   modernos con inodoro suspendido, ducha a ras de suelo con    │  │
    │  │   mampara fija, porcelánico rectificado gran formato, y        │  │
    │  │   iluminación LED perimetral integrada.                        │  │
    │  │ """                                                             │  │
    │  │                                                                 │  │
    │  │ transformation_summary: """                                     │  │
    │  │   Renovación integral: Nuevos sanitarios suspendidos, ducha    │  │
    │  │   extraplana con mampara, revestimiento porcelánico premium,   │  │
    │  │   instalación eléctrica nueva con iluminación LED.             │  │
    │  │ """                                                             │  │
    │  │                                                                 │  │
    │  │ visible_outcomes: [                                            │  │
    │  │   "Inodoro suspendido de diseño",                              │  │
    │  │   "Ducha a ras de suelo con mampara fija",                     │  │
    │  │   "Porcelánico rectificado 60x120",                            │  │
    │  │   "Grifería termostática",                                     │  │
    │  │   "Iluminación LED perimetral"                                 │  │
    │  │ ]                                                               │  │
    │  │                                                                 │  │
    │  │ compliance_issues: [                                           │  │
    │  │   {"code": "REBT ITC-BT-27", "issue": "Sin diferencial"},      │  │
    │  │   {"code": "CTE DB-HS1", "issue": "Juntas deterioradas"}       │  │
    │  │ ]                                                               │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                       │
    │  This is RICH, NUANCED, CONTEXTUAL. The LLM understands what         │
    │  "modern" means for THIS property vs THESE comparables.              │
    │                                                                       │
    │  This prose will be shown DIRECTLY to the customer later.            │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 2: TERMINAL TASK EXTRACTION  │   WHO: LLM (Gemini)
 (Structured Mapping)              │   WHY: Maps prose to KG vocabulary
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  Gemini extracts:               │
                    │  "Given this description and    │
                    │   the KG task list, which       │
                    │   tasks are the END GOALS?"     │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  OUTPUT: Terminal task IDs per room                                   │
    │                                                                       │
    │  {                                                                    │
    │    "baño_principal": [                                                │
    │      "TASK_INSTA_EQUIP_SANIT_13b7a3c6",   // Sanitarios              │
    │      "TASK_PLATO_DUCHA_EXTRA_a2b3c4d5",   // Plato ducha             │
    │      "TASK_MAMPA_DUCHA_FIJA_b3c4d5e6",    // Mampara                 │
    │      "TASK_ALICA_PORCE_RECTI_c4d5e6f7",   // Porcelánico             │
    │      "TASK_GRIFE_TERMO_d5e6f7g8",         // Grifería                │
    │      "TASK_ILUMIN_LED_PERIM_e6f7g8h9",    // LED                     │
    │      "TASK_BOLET_ELECT_f7g8h9i0"          // Certificación           │
    │    ]                                                                  │
    │  }                                                                    │
    │                                                                       │
    │  These are the VISIBLE DELIVERABLES - what the customer will see.    │
    │  They are the END POINTS of the work chains.                         │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 3: KG BACKWARD TRAVERSAL     │   WHO: Code (Deterministic)
 (Complete Prerequisite Discovery) │   WHY: KG knows all dependencies
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  For each terminal task, traverse ALL `requires` edges backward       │
    │                                                                       │
    │  TASK_INSTA_EQUIP_SANIT (Install toilet)                             │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_REJUN_CERAM (Grouting)                                         │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_ALICA_COMPL (Tiling)                                           │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_IMPER_ZONA (Waterproofing)                                     │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_INSTA_FONTA (Plumbing rough-in)                                │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_DEMOL_REVES (Demolition)                                       │
    │      │                                                                │
    │      │ requires                                                       │
    │      ▼                                                                │
    │  TASK_PROTE_ZONAS (Protection)   ◄── ROOT (no prerequisites)         │
    │                                                                       │
    │  = 19 tasks found for bathroom alone                                  │
    │                                                                       │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │  def full_backward_traversal(task_id, visited=None):           │  │
    │  │      if visited is None: visited = set()                       │  │
    │  │      if task_id in visited: return set()                       │  │
    │  │      visited.add(task_id)                                      │  │
    │  │                                                                 │  │
    │  │      result = {task_id}                                        │  │
    │  │      task = KG_TASKS.get(task_id, {})                          │  │
    │  │                                                                 │  │
    │  │      # NO FILTERING - follow ALL requires edges                │  │
    │  │      for req_id in task.get('requires', []):                   │  │
    │  │          result.update(full_backward_traversal(req_id, visited))│  │
    │  │                                                                 │  │
    │  │      return result                                             │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                       │
    │  NO HALLUCINATION. The KG has the edges. We just follow them.        │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 4: TOPOLOGICAL SORT          │   WHO: Code (Algorithm)
 (Correct Execution Order)         │   WHY: Prerequisites before dependents
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  Order tasks so prerequisites come first                              │
    │                                                                       │
    │  Input:  {TASK_A, TASK_B, TASK_C, ...} (unordered set)               │
    │  Output: [TASK_C, TASK_B, TASK_A, ...] (ordered list)                │
    │                                                                       │
    │  Execution order for bathroom:                                        │
    │  1. Protección de zonas                                              │
    │  2. Demolición de revestimientos                                     │
    │  3. Instalación fontanería                                           │
    │  4. Instalación electricidad                                         │
    │  5. Impermeabilización                                               │
    │  6. Alicatado                                                        │
    │  7. Solado                                                           │
    │  8. Rejuntado                                                        │
    │  9. Instalación sanitarios                                           │
    │  10. Grifería                                                        │
    │  11. Mampara                                                         │
    │  12. Accesorios                                                      │
    │  13. Limpieza final                                                  │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 5: QUANTITY CALCULATION      │   WHO: Code + KG guidance
 (Deterministic Math)              │   WHY: No guessing, use formulas
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  For each task, calculate quantity using KG's quantity_guidance       │
    │                                                                       │
    │  Task: TASK_ALICA_COMPL (Alicatado completo)                         │
    │  KG guidance:                                                         │
    │    quantity_type: "area_m2"                                          │
    │    scope: "per_room"                                                 │
    │    typical_rules: ["wall_perimeter × height - openings"]             │
    │    constraints: {min: 1, max_per_room: 100}                          │
    │                                                                       │
    │  Room data: baño_principal, 6.5m², 2.5m height, perimeter ~11m       │
    │  Calculation: 11m × 2.5m = 27.5m² (minus door ~2m² = 25.5m²)        │
    │                                                                       │
    │  No hallucination - deterministic math within KG constraints.        │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 6: BCCA PRICING              │   WHO: Code (Database lookup)
 (Standardized Unit Prices)        │   WHY: Official Spanish price database
════════════════════════════════════╪════════════════════════════════════════
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  Match each task to BCCA item using hybrid search (BM25 + vector)     │
    │                                                                       │
    │  Task: TASK_ALICA_COMPL                                              │
    │  Keyword: "Alicatado porcelánico rectificado"                        │
    │  BCCA match: 10SCS90040 - "Alicatado gres porcelánico"               │
    │  Unit price: €32.50/m²                                               │
    │                                                                       │
    │  Line total: 25.5m² × €32.50 = €828.75                               │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪════════════════════════════════════════
 STEP 7: OUTPUT GENERATION         │   WHO: Code (Formatting)
 (Two Audiences)                   │   WHY: Customer ≠ Architect needs
════════════════════════════════════╪════════════════════════════════════════
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌───────────────────────────────────┐ ┌───────────────────────────────────────┐
│                                   │ │                                       │
│  CUSTOMER OUTPUT                  │ │  ARCHITECT OUTPUT                     │
│  (Layman, Trustworthy)            │ │  (Technical, Complete)                │
│                                   │ │                                       │
│  Uses gap_narrative directly      │ │  Full BoQ with:                       │
│  from Step 1 - already written    │ │  • BCCA codes                         │
│  by LLM in context.               │ │  • Unit quantities                    │
│                                   │ │  • Unit prices                        │
│  ┌─────────────────────────────┐  │ │  • Line totals                        │
│  │ 🛁 BAÑO PRINCIPAL           │  │ │  • Chapter subtotals                  │
│  │                             │  │ │  • PEM/GG/BI/PEC/IVA breakdown        │
│  │ El baño presenta un        │  │ │  • Technical notes                    │
│  │ aspecto anticuado con      │  │ │  • Compliance references              │
│  │ sanitarios de los años 80  │  │ │                                       │
│  │ y una instalación          │  │ │  ┌─────────────────────────────────┐  │
│  │ eléctrica que no cumple    │  │ │  │ PRESUPUESTO DE EJECUCIÓN       │  │
│  │ normativa.                 │  │ │  │ BAÑO PRINCIPAL - 6.5 m²         │  │
│  │                             │  │ │  │                                 │  │
│  │ Qué haremos:               │  │ │  │ CAP 1: DEMOLICIONES            │  │
│  │                             │  │ │  │ ─────────────────────────────  │  │
│  │ ✓ Sanitarios suspendidos   │  │ │  │ 1.1 Protección zonas paso     │  │
│  │ ✓ Ducha a ras de suelo     │  │ │  │     18BSV00101                 │  │
│  │ ✓ Porcelánico premium      │  │ │  │     6.50 m² × €2.50 = €16.25  │  │
│  │ ✓ Iluminación LED          │  │ │  │                                 │  │
│  │                             │  │ │  │ 1.2 Demolición alicatado      │  │
│  │ ─────────────────────────  │  │ │  │     18BSV00201                 │  │
│  │ Inversión: €8,500          │  │ │  │     25.50 m² × €8.20 = €209.10│  │
│  │ Duración: 3 semanas        │  │ │  │                                 │  │
│  │ ─────────────────────────  │  │ │  │ ...                            │  │
│  │                             │  │ │  │                                 │  │
│  │ [Ver presupuesto detallado]│  │ │  │ ═══════════════════════════════│  │
│  └─────────────────────────────┘  │ │  │ PEM:     €7,024.79            │  │
│                                   │ │  │ GG+BI:   €1,334.71 (19%)      │  │
│                                   │ │  │ PEC:     €8,359.50            │  │
│                                   │ │  │ IVA:     €1,755.50 (21%)      │  │
│                                   │ │  │ ─────────────────────────────  │  │
│                                   │ │  │ TOTAL:   €10,115.00           │  │
│                                   │ │  │                                 │  │
│                                   │ │  │ NOTAS TÉCNICAS:               │  │
│                                   │ │  │ • Impermeabilización según    │  │
│                                   │ │  │   CTE DB-HS1, sistema bicapa  │  │
│                                   │ │  │ • Instalación eléctrica según │  │
│                                   │ │  │   REBT ITC-BT-25/27           │  │
│                                   │ │  │ • Licencia: Obra menor        │  │
│                                   │ │  └─────────────────────────────────┘  │
└───────────────────────────────────┘ └───────────────────────────────────────┘
```

---

## Files to Modify

### 1. Gap Analysis (`/backend/pipeline/gap_analysis.py`)

**Changes:**
- Add `gap_narrative` field (rich prose for customer)
- Add `transformation_summary` field (what we'll do)
- Add `visible_outcomes` field (bullet points)
- Keep existing fields for backward compatibility

```python
@dataclass
class RoomGap:
    room_id: str
    room_name: str
    room_type: str
    
    # NEW: Rich narrative for customer display
    gap_narrative: str  # Full prose description of gap
    transformation_summary: str  # What we'll do (for customer)
    visible_outcomes: List[str]  # Bullet points of end results
    
    # Existing fields
    remediation_items: List[Dict]
    compliance_issues: List[Dict]
    viewing_checks: List[str]
```

**Prompt changes:**
- Ask Gemini to write for the CUSTOMER, not for developers
- Request specific visible outcomes
- Emphasize the transformation story

---

### 2. Resolver (`/backend/pricing/renovation_resolver.py`)

**Changes:**

**A. Remove selective traversal (lines ~1029-1044)**
```python
# BEFORE (selective):
for req_id in task.get('requires', []):
    if any(kw in req_name for kw in ['apeo', 'apuntal', 'refuerz']):
        traverse(req_id, ...)

# AFTER (complete):
for req_id in task.get('requires', []):
    traverse(req_id, chain, visited, depth + 1)
```

**B. Add topological sort**
```python
def topological_sort(task_ids: Set[str], kg_tasks: Dict) -> List[str]:
    """Sort tasks so prerequisites come before dependents."""
    # Kahn's algorithm implementation
    ...
```

**C. Update `resolve_from_gap_analysis`**
```python
async def resolve_from_gap_analysis(gap_analysis, room_sizes, floor_area):
    # Step 2: Extract terminal tasks from gap narratives
    terminal_tasks = await extract_terminal_tasks(gap_analysis)
    
    # Step 3: Full backward traversal
    all_tasks = set()
    for room, task_ids in terminal_tasks.items():
        for task_id in task_ids:
            all_tasks.update(full_backward_traversal(task_id))
    
    # Step 4: Topological sort
    ordered_tasks = topological_sort(all_tasks, self.tasks)
    
    # Steps 5-6: Quantities and pricing (existing)
    ...
```

---

### 3. Routes (`/backend/routes/renovation.py`)

**Changes:**
- Pass `gap_narrative` through to response
- Structure output for both customer and architect views

```python
# In the pricing response, include:
{
    "customer_view": {
        "rooms": [
            {
                "name": "Baño Principal",
                "icon": "🛁",
                "narrative": gap_result.rooms[0].gap_narrative,
                "transformation": gap_result.rooms[0].transformation_summary,
                "outcomes": gap_result.rooms[0].visible_outcomes,
                "cost": 8500,
                "duration_weeks": 3
            }
        ],
        "total_cost": 45000,
        "total_duration": "8-10 semanas"
    },
    "architect_view": {
        "boq_by_chapter": {...},  # Existing
        "technical_notes": [...],
        "compliance_refs": [...],
        "permit_type": "obra_menor"
    }
}
```

---

### 4. Frontend (`/frontend/src/app/...`)

**Changes:**
- Card 2 (Package Scopes) shows customer view per room
- Modal/detail view shows architect BoQ
- PDF export generates architect document

```tsx
// Customer view component
<RoomScopeCard>
  <RoomIcon>{room.icon}</RoomIcon>
  <RoomName>{room.name}</RoomName>
  
  <Narrative>{room.narrative}</Narrative>
  
  <OutcomesList>
    {room.outcomes.map(outcome => (
      <Outcome>✓ {outcome}</Outcome>
    ))}
  </OutcomesList>
  
  <CostBadge>€{room.cost.toLocaleString()}</CostBadge>
  <DurationBadge>{room.duration_weeks} semanas</DurationBadge>
  
  <DetailButton onClick={() => showArchitectView(room)}>
    Ver presupuesto detallado
  </DetailButton>
</RoomScopeCard>
```

---

## Implementation Order

### Phase 1: Backend Core (Day 1)
1. ✅ KG already has edges (2,789 of them)
2. ✅ KG already has quantity_guidance (683 tasks)
3. [ ] Fix resolver traversal (remove filtering)
4. [ ] Add topological sort
5. [ ] Test with existing gap analysis

### Phase 2: Gap Analysis Enhancement (Day 2)
1. [ ] Add new fields to RoomGap dataclass
2. [ ] Update gap analysis prompt for customer-focused prose
3. [ ] Test narrative quality

### Phase 3: Output Restructuring (Day 2-3)
1. [ ] Update route response structure
2. [ ] Pass narratives through to response
3. [ ] Structure customer vs architect views

### Phase 4: Frontend (Day 3-4)
1. [ ] Update Card 2 to show customer view
2. [ ] Add architect detail modal
3. [ ] PDF export for architect document

---

## Success Criteria

1. **Completeness**: Starting from "new toilet", find ALL 19 prerequisite tasks
2. **Order**: Tasks in correct execution sequence
3. **Customer clarity**: Non-technical user understands scope
4. **Architect precision**: Full BoQ with BCCA codes, quantities, specs
5. **No hallucination**: All tasks from KG traversal, not LLM invention

---

## Testing Checklist

```bash
# Test 1: Backward traversal completeness
python3 -c "
from pricing.renovation_resolver import full_backward_traversal
tasks = full_backward_traversal('TASK_INSTA_EQUIP_SANIT_13b7a3c6')
assert len(tasks) >= 15, f'Expected 15+ tasks, got {len(tasks)}'
print(f'✓ Found {len(tasks)} tasks from terminal task')
"

# Test 2: Topological sort correctness
python3 -c "
from pricing.renovation_resolver import topological_sort
# Protection must come before demolition
# Demolition must come before tiling
# etc.
print('✓ Topological sort produces valid order')
"

# Test 3: Customer narrative quality
# Run gap analysis on test listing
# Verify gap_narrative is customer-friendly prose
# Verify visible_outcomes are clear bullet points

# Test 4: End-to-end pricing
# Full pipeline from listing to priced BoQ
# Verify no tasks missing
# Verify quantities reasonable
# Verify prices from BCCA
```

---

## Reference: The Philosophy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   LLM                    KG                      CODE                        │
│   ═══                    ══                      ════                        │
│                                                                              │
│   "What's wrong?"        "What tasks?"           "How much?"                 │
│   "What should it        "In what order?"        "What price?"               │
│    look like?"           "What prerequisites?"   "What total?"               │
│                                                                              │
│   Creative               Complete                Deterministic               │
│   Contextual             Standardized            Mathematical                │
│   Nuanced                Exhaustive              Precise                     │
│                                                                              │
│   ┌───────────┐          ┌───────────┐          ┌───────────┐               │
│   │ Pattern   │    ──▶   │ Graph     │    ──▶   │ Formulas  │               │
│   │ Recogn.   │          │ Traversal │          │ & Lookups │               │
│   └───────────┘          └───────────┘          └───────────┘               │
│                                                                              │
│   Each tool does what it's best at. No tool does another's job.             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Files Reference

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `/backend/pipeline/gap_analysis.py` | LLM gap analysis | Add customer-focused fields |
| `/backend/pricing/renovation_resolver.py` | KG traversal + pricing | Fix traversal, add sort |
| `/backend/routes/renovation.py` | API endpoints | Restructure response |
| `/frontend/src/app/.../page.tsx` | UI components | Customer + architect views |
| `/docs/KG_TRAVERSAL_ARCHITECTURE.md` | Technical docs | ✅ Done |
| `/docs/RENOVATION_PIPELINE_V3_PLAN.md` | This plan | ✅ Done |

