Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.3.1: Knowledge Integration Extension

> **Date**: January 2026  
> **Author**: Peter Neyra + Claude  
> **Status**: Implementation Plan  
> **Parent**: V0.3 (Hybrid KG + BCCA Architecture)

---

## What This Extension Adds

V0.3 established the **hybrid architecture**:
- Full KG in context (214K tokens)
- BCCA via RAG tool (12K items)
- BCCA-speak translation guide

**V0.3.1 adds GROUNDED KNOWLEDGE:**
- Energy knowledge synthesized from FULL Spanish building codes
- Process knowledge from CSCAE Guía Vecinal
- Source tracking for UI disclaimers and professional verification

---

## Knowledge Extraction Approach

### The Philosophy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│    FULL SOURCE DOCUMENTS (320K tokens)                                      │
│    ├── CTE-DB-HE (37K) - Energy code                                        │
│    ├── CTE-DB-HS (116K) - Ventilation/health                                │
│    ├── IDAE CE3X Manual (13K) - Professional rating methodology             │
│    ├── IDAE Rehabilitación (9K) - Homeowner-friendly language               │
│    ├── IDAE Ayudas 2021 (98K) - Subsidy pathways                            │
│    ├── Decreto Extremadura (18K) - Habitability requirements                │
│    └── CSCAE Guía Vecinal (30K) - 10-step process for homeowners            │
│                                                                             │
│                           ↓ Gemini Pro (one-time extraction)                │
│                                                                             │
│    SYNTHESIZED KNOWLEDGE (~40K tokens)                                      │
│    ├── energy_knowledge.json (26KB) ← Technical specs, U-values, ratings    │
│    └── renovation_process_knowledge.json (15KB) ← Process, decisions, FAQs  │
│                                                                             │
│                           ↓ Used in every request                           │
│                                                                             │
│    GAP/SCOPING SYSTEM INSTRUCTION                                           │
│    ├── KG (~214K)                                                           │
│    ├── Energy KB flattened (~6K)                                            │
│    ├── Process KB flattened (~4K)                                           │
│    └── BCCA-speak guide (~2K)                                               │
│    = ~226K tokens (23% of 1M limit) ✅                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why not put full docs in every request?**
1. **Redundancy** - Re-reading 320K tokens every time
2. **Latency** - More tokens = slower
3. **Cost** - Input tokens cost money
4. **Focus** - LLM attention diluted across regulatory prose

**The synthesis IS the full docs, just pre-digested:**
- Every piece of knowledge cites its source: `"sources": ["CTE-DB-HE", "IDAE-CE3X"]`
- UI can show "Based on CTE DB-HE 2022" with link to PDF
- Professional verification possible

---

## Knowledge Bases Created

### 1. Energy Knowledge (`energy_knowledge.json`)

**Source Documents (287K tokens):**
| Document | Tokens | Content |
|----------|--------|---------|
| CTE-DB-HE | ~37K | Spanish energy code - U-value limits, nZEB requirements |
| CTE-DB-HS | ~116K | Ventilation requirements (affects energy) |
| IDAE CE3X Manual | ~13K | Professional rating methodology |
| IDAE Rehabilitación | ~9K | Homeowner-friendly explanations |
| IDAE Ayudas 2021 | ~98K | Subsidy eligibility, pathways |
| Decreto Extremadura | ~18K | Habitability requirements |

**Extracted Knowledge:**

```yaml
rating_scale:
  A: { kWh/m²: zone-specific limits, description, typical_building }
  B: { ... }
  C: { ... }
  D: { ... }
  E: { ... }
  F: { ... }
  G: { ... }

climate_zones:
  zone_A: { cities, U_wall: 0.80, U_roof, U_window, HDD }
  zone_B: { cities, U_wall: 0.70, ... }
  zone_C: { cities, U_wall: 0.56, ... }  # Barcelona, Bilbao
  zone_D: { cities, U_wall: 0.49, ... }  # Madrid
  zone_E: { cities, U_wall: 0.37, ... }  # Burgos, Soria

age_correlation:
  pre_1940: { typical_rating: G, regulation: "none", issues }
  1940_1979: { typical_rating: F-G, regulation: "MV-1974" }
  1980_2006: { typical_rating: D-E, regulation: "NBE-CT-79" }
  2007_2013: { typical_rating: C, regulation: "CTE 2006" }
  2014_2019: { typical_rating: B, regulation: "CTE 2013" }
  post_2020: { typical_rating: A, regulation: "CTE 2019 nZEB" }

interventions:  # 13 types
  window_replacement:
    description_technical: "Sustitución de huecos..."
    description_homeowner: "Instalación de un 'abrigo'..."  # IDAE language!
    u_value_typical_old: 5.7
    u_value_achievable: 1.5
    typical_improvement_letters: 1
    climate_sensitivity: "Crítico en zonas D y E"
    subsidy_eligible: true
    sources: ["CTE-DB-HE", "IDAE-CE3X", "IDAE-Rehabilitacion"]
  
  wall_insulation_sate: { ... }  # +2 letters
  wall_insulation_trasdosado: { ... }
  roof_insulation: { ... }
  floor_insulation: { ... }
  heat_pump_aerothermal: { ... }  # +2 letters
  heat_pump_geothermal: { ... }
  solar_thermal_acs: { ... }
  photovoltaic: { ... }
  condensing_boiler: { ... }
  mechanical_ventilation: { ... }
  led_lighting: { ... }
  hvac_controls: { ... }

upgrade_pathways:
  G_to_E: { min_improvement: 30%, interventions, subsidy_bracket }
  E_to_C: { min_improvement: 45%, ... }
  C_to_A: { min_improvement: 60%, ... }

homeowner_tips:
  comfort: "Una vivienda aislada mantiene temperatura estable..."
  savings: "Rehabilitación puede reducir factura hasta 50%..."
  efecto_termo: "Un edificio bien aislado funciona como un termo..."
```

### 2. Process Knowledge (`renovation_process_knowledge.json`)

**Source Document (30K tokens):**
- CSCAE Guía Vecinal de Rehabilitación (4th Edition 2023)
- Published by Spanish Architects' Council + Neighborhood Associations
- Written FOR homeowners, not professionals

**Extracted Knowledge:**

```yaml
ten_steps:
  - step: 1
    name_es: "El detonante de la rehabilitación"
    name_en: "The trigger for rehabilitation"
    description: "ITE failure, high bills, accessibility need..."
    participants: ["vecinos"]
    homeowner_tip: "Cualquier problema puede ser oportunidad..."
  
  - step: 2
    name_es: "Primer contacto con el/la arquitecto/a"
    name_en: "First contact with architect"
    description: "Ask for a building checkup"
    how_to_find: "Oficinas de Apoyo a la Rehabilitación"
  
  ... (10 steps total)

triggers:
  regulatory: ["ITE desfavorable", "Obligación retirar amianto"]
  economic: ["Facturas excesivas", "Derramas constantes"]
  comfort: ["Falta accesibilidad", "Frío/calor excesivo"]
  building_problems: ["Desprendimientos", "Humedades", "Grietas"]

community_decisions:
  voting_requirements:
    simple_majority: "Eficiencia energética si coste < 12 mensualidades"
    qualified_majority: "3/5 para obras mayores"
  how_to_propose: "Incluir en orden del día de junta..."

professionals:
  arquitecto: { role, when_needed, how_to_find }
  administrador_fincas: { role, coordination }
  constructora: { selection, minimum_quotes: 3, criteria }
  oficinas_apoyo: { what_are_they, services }

homeowner_faqs:
  - question: "Why fix whole building if only one piece fell?"
    answer: "Problemas puntuales son síntomas de deterioro global..."
  
  - question: "Can I close my balcony without permission?"
    answer: "Necesitas consultar estatutos y votar en junta..."

communication_phrases:
  explaining_benefits:
    - "La rehabilitación no es un gasto, es una inversión"
    - "Mejorar el 'abrigo' del edificio es la mejor forma de ahorrar"
  setting_expectations:
    - "Un buen diagnóstico previo evita sorpresas"
    - "El proceso es largo, pero planificarlo por fases lo hace asumible"
```

---

## Source Tracking for UI

Every knowledge base includes a `references` section:

```json
{
  "references": {
    "disclaimer_es": "La información se basa en normativa española oficial. Para certificación, consulte a un técnico certificador.",
    "disclaimer_en": "Information based on official Spanish regulations. For certification, consult a certified technician.",
    "primary_sources": {
      "CTE-DB-HE": {
        "title": "Código Técnico de la Edificación - DB HE",
        "short_title": "CTE DB-HE 2022",
        "url": "https://www.codigotecnico.org/pdf/Documentos/HE/DBHE.pdf",
        "authority": "Ministerio de Transportes",
        "year": 2022
      },
      "IDAE-CE3X": {
        "title": "Guía de recomendaciones - CE³X",
        "url": "https://www.certificadosenergeticos.com/...",
        "authority": "IDAE",
        "year": 2012
      }
    }
  }
}
```

**UI Usage:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Eficiencia Energética Estimada: E → C                          │
│                                                                 │
│  Mejoras recomendadas:                                          │
│  • Aislamiento SATE (+2 letras)                                 │
│  • Sustitución ventanas (+1 letra)                              │
│                                                                 │
│  📚 Fuentes: CTE DB-HE 2022 · IDAE CE3X                        │
│  ℹ️  Esta estimación es orientativa. Para certificación        │
│     oficial, consulte a un técnico certificador.                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### PHASE 0: Knowledge Extraction ✅ COMPLETE

| Task | Status | Output |
|------|--------|--------|
| Create `extract_energy_knowledge.py` | ✅ | Script with 65K output |
| Feed FULL source docs to Gemini (287K tokens) | ✅ | Synthesis complete |
| Generate `energy_knowledge.json` | ✅ | 26KB, 7 ratings, 13 interventions |
| Create `extract_process_knowledge.py` | ✅ | Script for CSCAE guide |
| Generate `renovation_process_knowledge.json` | ✅ | 15KB, 10 steps, FAQs |

**Scripts created:**
- `/Lean MVP/backend/scripts/extract_energy_knowledge.py`
- `/Lean MVP/backend/scripts/extract_process_knowledge.py`

**Knowledge bases created:**
- `/Lean MVP/standards/energy_knowledge.json`
- `/Lean MVP/standards/renovation_process_knowledge.json`

---

### PHASE 1: System Instruction Module 🔲 PENDING

**Goal:** Integrate synthesized knowledge into the system instruction.

#### Step 1.1: Create Energy Context Section

Add to system instruction (after KG, before BCCA-speak):

```yaml
# ============================================================
# ENERGY RATING KNOWLEDGE
# Source: CTE DB-HE 2022, IDAE CE3X, IDAE Guides
# ============================================================

## Spanish Climate Zones (CTE DB-HE)
| Zone | Cities | U_wall_limit |
|------|--------|--------------|
| A | Almería, Málaga costa | ≤ 0.80 W/m²K |
| B | Sevilla, Valencia | ≤ 0.70 W/m²K |
| C | Barcelona, Bilbao | ≤ 0.56 W/m²K |
| D | Madrid, Zaragoza | ≤ 0.49 W/m²K |
| E | Burgos, Soria, Ávila | ≤ 0.37 W/m²K |

## Building Age → Expected Rating
| Period | Regulation | Typical Rating |
|--------|------------|----------------|
| Pre-1940 | None | G |
| 1940-1979 | MV-1974 | F-G |
| 1980-2006 | NBE-CT-79 | D-E |
| 2007-2013 | CTE 2006 | C |
| 2014-2019 | CTE 2013 | B |
| Post-2020 | CTE nZEB | A |

## Intervention Energy Impacts
| Intervention | U-value change | Letters |
|--------------|----------------|---------|
| Window replacement | 5.7 → 1.5 | +1 |
| Wall SATE | 1.8 → 0.3 | +2 |
| Wall trasdosado | 1.8 → 0.4 | +1 |
| Roof insulation | 2.0 → 0.33 | +1 |
| Heat pump (aerothermal) | - | +2 |

## When to Consider Energy
- If listing has energy rating: compare to target
- If building age known: infer baseline rating
- If "high bills" mentioned: prioritize envelope
- If "cold in winter": check windows + walls
```

#### Step 1.2: Create Process Context Section (optional)

For gap analysis, include rehabilitation triggers:

```yaml
# ============================================================
# REHABILITATION TRIGGERS (from CSCAE Guía Vecinal)
# ============================================================

## What Makes Homeowners Act
- regulatory: ITE failure, asbestos removal obligation
- economic: High energy bills, constant derramas
- comfort: Accessibility needs, cold/heat, noise
- building_problems: Facade falling, humidity, cracks

## Homeowner Language to Use
- "La rehabilitación no es un gasto, es una inversión"
- "Mejorar el 'abrigo' del edificio"
- "Efecto termo" (building acts like a thermos)
```

#### Step 1.3: Update System Instruction Template

**Files to update:**
- `renovation_resolver.py` - Add energy/process context
- OR create `system_instruction.txt` template file

---

### PHASE 2: KG Task Enrichment 🔲 PENDING

**Goal:** Add `energy_impact` metadata to the 47 energy-relevant KG tasks.

#### Step 2.1: Identify Energy-Relevant Tasks

Create script to find tasks with energy impact:

```python
ENERGY_RELEVANT_PATTERNS = [
    "insulation", "aislamiento", "ventana", "window",
    "hvac", "caldera", "heat", "calefacción",
    "solar", "photovoltaic", "aerotermia",
    "roof", "cubierta", "facade", "fachada"
]
```

Expected output: ~47 tasks

#### Step 2.2: Generate Energy Impact Metadata

For each energy-relevant task, Gemini adds:

```yaml
task_id: "install_exterior_insulation"
energy_impact:
  affects_u_value: true
  element: "wall"
  typical_improvement_letters: 2
  climate_sensitivity: "high"  # More impact in cold zones
  synergies: ["window_replacement"]
  sources: ["CTE-DB-HE"]
```

#### Step 2.3: Update `flatten_kg.py`

Include `energy_impact` in the flattened YAML output.

---

### PHASE 3: Pipeline Integration 🔲 PENDING

#### Step 3.1: Verify Idealista Energy Extraction

Check that `idealista_info_extraction` table includes:
- `energy_rating` (A-G)
- `energy_consumption` (if available)
- `energy_emissions` (if available)

**Already in pipeline?** Verify and document.

#### Step 3.2: Use Energy in Gap Analysis

Update gap analysis to:
1. Get listing energy rating (from extraction)
2. Get comparable energy ratings
3. Calculate energy improvement needed
4. Select energy-relevant tasks from KG
5. Include in scope with intervention impacts

---

## Token Budget (V0.3.1)

| Component | Tokens | Notes |
|-----------|--------|-------|
| KG (full enrichment) | ~214K | Task structure, dependencies |
| Energy KB (flattened) | ~6K | U-values, ratings, interventions |
| Process KB (flattened) | ~4K | 10 steps, triggers, professionals |
| BCCA-speak guide | ~2K | How to search prices |
| Role + grounding | ~3K | System instruction |
| **CACHED TOTAL** | **~229K** | **23% of 1M limit** |
| Property data (per request) | ~10K | Listing, photos, NL mining |
| **REQUEST TOTAL** | **~239K** | **24% of 1M limit** |

**Comparison:**
- V0.2: 714K tokens (over limit)
- V0.3: 225K tokens (no knowledge integration)
- V0.3.1: 239K tokens (with knowledge integration)

---

## Files Structure

```
Lean MVP/
├── standards/
│   ├── energy_knowledge.json          ← NEW (26KB)
│   ├── renovation_process_knowledge.json  ← NEW (15KB)
│   ├── CTE-DB-HE.txt                  ← Source (37K tokens)
│   ├── CTE-DB-HS.txt                  ← Source (116K tokens)
│   ├── IDAE_CE3X_Manual_Mejoras.txt   ← Source (13K tokens)
│   ├── IDAE_Guia_Rehabilitacion_Aislamiento.txt  ← Source (9K tokens)
│   ├── IDAE_Guia_Ayudas_Rehabilitacion_2021.txt  ← Source (98K tokens)
│   ├── CSCAE_Guia_Vecinal_2023.txt    ← Source (30K tokens)
│   └── decreto-10-2019-extremadura.txt ← Source (18K tokens)
├── backend/
│   ├── scripts/
│   │   ├── extract_energy_knowledge.py     ← NEW
│   │   └── extract_process_knowledge.py    ← NEW
│   └── pricing/
│       ├── renovation_resolver.py     ← TO UPDATE (Phase 1)
│       ├── flatten_kg.py              ← TO UPDATE (Phase 2)
│       └── kg_context.yaml            ← Output of flatten_kg
└── docs/
    ├── PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md  ← Parent doc
    └── PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md ← This doc
```

---

## Success Criteria

### Phase 0 ✅
- [x] 287K tokens of source docs fed to Gemini
- [x] energy_knowledge.json with 7 rating levels, 13 interventions
- [x] renovation_process_knowledge.json with 10 steps, FAQs
- [x] All knowledge has source citations

### Phase 1
- [ ] Energy context section in system instruction
- [ ] Climate zone table accessible to LLM
- [ ] Age→rating mapping in context
- [ ] Intervention impacts available for reasoning

### Phase 2
- [ ] 47 energy-relevant tasks identified
- [ ] energy_impact metadata added to KG
- [ ] flatten_kg.py outputs energy_impact
- [ ] kg_context.yaml includes energy metadata

### Phase 3
- [ ] Idealista energy extraction verified
- [ ] Gap analysis uses energy rating delta
- [ ] Energy interventions included in scope
- [ ] U-value improvements in BoQ reasoning

---

## Reference: Source Document URLs

For UI disclaimers and professional verification:

| Source | URL |
|--------|-----|
| CTE DB-HE | https://www.codigotecnico.org/pdf/Documentos/HE/DBHE.pdf |
| CTE DB-HS | https://www.codigotecnico.org/pdf/Documentos/HS/DBHS.pdf |
| IDAE CE3X Manual | https://www.certificadosenergeticos.com/wp-content/uploads/2015/04/Manual_medidas_mejora_CE3X_03.pdf |
| IDAE Rehabilitación | https://www.idae.es/uploads/documentos/documentos_10501_Guia_practica_rehabilitacion_edificios_aislamiento_5266ec2a.pdf |
| IDAE Ayudas 2021 | https://www.idae.es/sites/default/files/documentos/ayudas_y_financiacion/GUIA_PRACTICA_PARA_LA_GESTION_DE_AYUDAS_A_LA_REHABILITACION_ENERGETICA_EDIFICIOS_2021.pdf |
| CSCAE Guía Vecinal | https://portal.coag.es/wp-content/uploads/2023/10/Guia-Vecinal-CSCAE_4aEdicion_Paginas.pdf |
| Decreto Extremadura | https://doe.juntaex.es/pdfs/doe/2019/340o/19040032.pdf |

