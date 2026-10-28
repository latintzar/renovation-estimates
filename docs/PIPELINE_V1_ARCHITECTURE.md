Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V1.0 Pipeline Architecture
## The Ultimate Renovation Estimation System

**Version:** 1.0.0  
**Date:** January 2026  
**Status:** Implementation In Progress

---

## ⚠️ DEPRECATION NOTICE

**See:** `DEPRECATION_PLAN.md` for full migration details.

### Files Being Deprecated (V0.5/V0.6 → V1.0)

| Deprecated File | Replaced By | Status |
|-----------------|-------------|--------|
| `phase_prompts.py` | `phase_prompts_v1.py` | ⚠️ Deprecated (warning on import) |
| `phase_prompts_v2.py` | `phase_prompts_v1.py` | ⚠️ Deprecated (warning on import) |
| `multi_phase_estimator.py` | `multi_phase_estimator_v1.py` | ⚠️ Deprecated (warning on import) |
| `multi_phase_estimator_v2.py` | `multi_phase_estimator_v1.py` | ⚠️ Deprecated (warning on import) |
| `schemas/gemini_schemas.py` | `schemas/gemini_schemas_v1.py` | ⚠️ Deprecated (warning on import) |
| `schemas/gemini_schemas_v2.py` | `schemas/gemini_schemas_v1.py` | ⚠️ Deprecated (warning on import) |
| `schemas/phase_outputs.py` | `schemas/gemini_schemas_v1.py` | ⚠️ Deprecated (warning on import) |

### V1.0 Files (Active)

| File | Purpose | Status |
|------|---------|--------|
| `phase_prompts_v1.py` | 8-phase prompts | ✅ Complete |
| `schemas/gemini_schemas_v1.py` | 8-phase schemas | ✅ Complete |
| `multi_phase_estimator_v1.py` | 8-phase orchestrator | ❌ To create |

---

## Executive Summary

This document defines the **complete 8-phase pipeline** for generating professional renovation estimates.

### The 8 Phases

| # | Name | Model | Purpose |
|---|------|-------|---------|
| 1 | SCOPE + BOQ | Pro | Define scope, select BCCA codes, estimate quantities |
| 2 | PRICE LOOKUP | Code | Deterministic price retrieval and calculation |
| 3 | PEER REVIEW | Pro | Add missing, remove bad, fix sequencing |
| 4 | RENDERING PROMPTS | Pro | Generate AI image transformation prompts |
| 5 | IMAGE GENERATION | Gemini Flash Image | 16:9 before→after images |
| 6 | VIEWING CHECKLIST | Flash | 20-minute property inspection guide |
| 7 | ELI5 ROOM SUMMARIES | Flash | Explain like buyer is 5, per room |
| 8 | ARCHITECT REPORT | Pro | Professional structure by trades |

### Design Principles (Non-Negotiable)

1. **Explain WHY** — "WHY IT MATTERS" sections guide reasoning
2. **Intelligent Peer** — Gemini is treated as equally intelligent colleague
3. **Examples in Prose** — Examples woven into explanations, not isolated
4. **Questions Guide Reasoning** — "For each X, ask yourself..." patterns
5. **Goal Before Task** — Role + context established before instructions
6. **Reasoning Over Checklists** — Questions over checkbox lists
7. **No Rigid Templates** — Flexibility with clear intent

---

## Cached Context Architecture

### Token Budget

| Component | Tokens | Notes |
|-----------|--------|-------|
| BCCA Index | ~328,000 | 12,565 items with prices |
| FFE Index | ~11,000 | 202 items with tiered pricing |
| Knowledge Graphs | ~44,000 | Energy, process, design |
| Dynamic Context | ~25,000 | PIRs, listing, prior phases |
| **Total** | **~408,000** | **Well within 1M limit** |

### Static Context (Every Request)

```
BCCA INDEX (~328K tokens)
└── 12,565 construction items: CODE|DESCRIPTION|PRICE
└── Composite prices (labor + materials + overhead)

FFE INDEX (~11K tokens)
└── 202 furniture/fixture items: CODE|NAME|DESC|BUDGET|MID|HIGH|LUXURY

KNOWLEDGE GRAPHS (~44K tokens)
├── energy_knowledge.json — CTE compliance, ratings
├── renovation_process_knowledge.json — CSCAE process
└── interior_design_knowledge.json — style guidance
```

### Dynamic Context (Per Request)

```
TARGET PIR — Property as it exists today
BRACKET PIR — What properties at this price point look like
STRATEGIC REASONING — Target vs bracket alignment analysis
CANONICAL ROOM IDS — Exact room identifiers from PIR
LISTING DATA — Address, price, area, floor, building info
PREVIOUS PHASE OUTPUTS — Cumulative through pipeline
```

---

## Phase Details

See companion document `PIPELINE_V1_PROMPTS.md` for complete prompts.

### Phase 1: SCOPE + BOQ (Pro Model)

**Purpose:** Define complete transformation scope by:
1. Analyzing gap between TARGET PIR and BRACKET PIR
2. Selecting appropriate BCCA code for each work item
3. Estimating quantities with formulas
4. Sequencing into construction schedule

**Why Combined:** When an architect thinks "this bathroom needs new tiles," they immediately think about the type (porcelanato 60x60), area (4.2m²), and timing (after waterproofing). Separating these is artificial.

**Output per item:**
```json
{
  "item_id": "ITEM_001",
  "room_id": "cocina",
  "name": "Alicatado suelo cocina",
  "bcca_code": "09ACE00145",
  "unit": "m2",
  "quantity": 12.5,
  "quantity_formula": "5.0m × 2.5m = 12.5m²",
  "phase_week": 6,
  "depends_on": ["ITEM_023"]
}
```

### Phase 2: PRICE LOOKUP (Code — Not LLM)

**Purpose:** Deterministic price retrieval and math.

```python
for item in items:
    bcca = get_bcca_price(item["bcca_code"])
    item["unit_price"] = bcca["price"]
    item["line_total"] = item["quantity"] * item["unit_price"]
```

**Why Code:** Prices must be traceable, reproducible, auditable. Skeptical humans verify.

### Phase 3: PEER REVIEW (Pro Model)

**Purpose:** Intelligent peer IMPROVES the estimate:
- Adds missing items (waterproofing, certifications)
- Removes inappropriate items
- Fixes sequencing (cure times, dependencies)
- Applies regional adjustments
- Validates energy pathway

**Key Philosophy:** "You're not here to say 'pass' or 'fail'. You're here to MAKE IT BETTER."

### Phase 4: RENDERING PROMPTS (Pro Model)

**Purpose:** Generate photorealistic transformation prompts matching bracket style.

**Critical:** After images must match what properties in this bracket look like. Bracket PIR guides materials, finishes, style.

### Phase 5: IMAGE GENERATION (Gemini 2.5 Flash Image)

**Purpose:** Generate before→after images using Gemini 2.5 Flash Image.

**Details:**
- Model: `gemini-2.5-flash-preview-image` (or latest)
- Aspect ratio: 16:9
- Same approach as current V0.6 implementation
- NOT external (Flux/SDXL) — uses existing Gemini image generation

### Phase 6: VIEWING CHECKLIST (Flash Model)

**Purpose:** 20-minute property viewing guide with 3 modes:
- Mode 1: "Siente el Espacio" (sensory checks)
- Mode 2: "Inspecciona" (room-by-room)
- Mode 3: "Pregunta al Agente" (strategic questions)

### Phase 7: ELI5 ROOM SUMMARIES (Flash Model)

**Purpose:** Explain like the buyer is 5:
- What changes per room
- Cost and timeline
- Energy improvement explained simply
- Glanceable, modular, trustworthy

**Critical:** Simple but not simplistic. Clear but not vague. Skeptical buyers smell oversimplification.

### Phase 8: ARCHITECT REPORT (Pro Model)

**Purpose:** Professional document by trades for:
- Contractor quotes
- Architect review
- Permit applications

---

## Data Flow

```
Phase 1 (SCOPE+BOQ) → Items with BCCA codes
         ↓
Phase 2 (PRICE LOOKUP) → Items with prices
         ↓
Phase 3 (PEER REVIEW) → Improved items + adjustments + totals
         ↓
    ┌────┴────┐
    ↓         ↓
Phase 4    Phase 6
(RENDER)   (CHECKLIST)
    ↓
Phase 5
(IMAGES)
    ↓
Phase 7 (ELI5) → Room summaries with images
    ↓
Phase 8 (ARCHITECT) → Professional report
```

---

## Success Criteria

- [ ] Every canonical room_id has at least one item
- [ ] Every item has valid BCCA code from index
- [ ] Quantities have formulas showing calculation
- [ ] Dependencies form valid DAG (no cycles)
- [ ] Energy improvements included where appropriate
- [ ] ELI5 summaries are clear but not oversimplified
- [ ] Architect report structure matches frontend

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `PIPELINE_V1_PROMPTS.md` | Complete phase prompts with reasoning guidance |
| `DEPRECATION_PLAN.md` | Migration from V0.6 to V1.0, file status |
| `V1_RECHECKS.md` | Quality assurance verification |
