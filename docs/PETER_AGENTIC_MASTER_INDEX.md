Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC Architecture - Master Index

> **Last Updated**: January 10, 2026  
> **Current Version**: V0.4 (Unified Estimator)  
> **Status**: ✅ READY FOR IMPLEMENTATION

---

## ⚠️ IMPORTANT: V0.4 is the SINGLE SOURCE OF TRUTH

**V0.3.x documents are superseded. Use V0.4 for implementation.**

| Old Approach (V0.3.x) | Current Approach (V0.4) |
|-----------------------|-------------------------|
| 4 separate stages | 1 unified Gemini call |
| Multiple Gemini calls | Single call with tool calling |
| Information loss at boundaries | Full context preserved |
| Complex EstimatorV3 orchestration | Simple UnifiedEstimator |
| 4 separate documents | **1 complete document** |

**Implementation Guide**: `PETER_AGENTIC_V0.4_UNIFIED_ESTIMATOR.md`

---

## Quick Reference

| Need to understand... | Read this document |
|-----------------------|-------------------|
| **EVERYTHING (implementation)** | **V0.4** |
| Historical context only | V0.3, V0.3.1, V0.3.2 (superseded) |
| What went wrong | IMPLEMENTATION_AUDIT.md |

---

## V0.4 Architecture (Current)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      V0.4: UNIFIED PROPERTY INTELLIGENCE                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 0: KNOWLEDGE EXTRACTION (One-time setup) ✅ DONE                     │
│  ──────────────────────────────────────────────                             │
│  ├── energy_knowledge.json ✅                                               │
│  ├── renovation_process_knowledge.json ✅                                   │
│  ├── interior_design_knowledge.json ✅                                      │
│  └── kg_context.yaml (214K tokens) ✅                                       │
│                                                                             │
│  PHASE 1: PROPERTY INTELLIGENCE REPORT (Per property) ⬜ TO BUILD          │
│  ────────────────────────────────────────────────────────                   │
│  One Gemini call per property → Comprehensive "study"                       │
│                                                                             │
│  PHASE 2: UNIFIED ESTIMATOR (Target vs Comparables) ⬜ TO BUILD            │
│  ──────────────────────────────────────────────────────                     │
│  ONE Gemini call with:                                                      │
│  - System instruction (~250K tokens)                                        │
│  - Target PIR + photos + listing                                            │
│  - Comparable PIRs                                                          │
│  - search_bcca tool for pricing                                             │
│  Output: UnifiedEstimate (gap + scope + BoQ + reasoning)                   │
│                                                                             │
│  PHASE 3: FORMAT VIEWS (Customer + Architect) ⬜ TO BUILD                  │
│  ─────────────────────────────────────────────                              │
│  - Customer view (layman summary, mobile-first)                             │
│  - Architect view (full BCCA technical detail)                              │
│                                                                             │
│  PHASE 4: MOBILE-FIRST UI ⬜ TO BUILD                                      │
│  ────────────────────────                                                   │
│  - Renovation tab: 3 package cards                                          │
│  - Full-screen modal: customer-friendly breakdown                           │
│  - Before/After: ONE ROOM ONLY (kitchen)                                    │
│  - Architect export: PDF/JSON                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## V0.4 Document Structure (Parts 1-13)

| Part | Content | Lines |
|------|---------|-------|
| 1 | System Instruction Template | ~170 |
| 2 | search_bcca Tool Implementation | ~150 |
| 3 | Response Schema (UnifiedEstimate) | ~200 |
| 4 | Unified Estimator Implementation | ~250 |
| 5 | View Formatters | ~100 |
| 6 | Token Budget | ~30 |
| 7 | Implementation Checklist | ~50 |
| 8 | PIR Schema Reference | ~50 |
| 9 | Energy Task Enrichment | ~50 |
| 10 | Preserved Decisions | ~80 |
| 11 | Structured Error Response | ~40 |
| 12 | **UI Specification (Mobile-First)** | ~300 |
| 13 | **Complete System Summary** | ~150 |

**Total**: ~1,700 lines - Complete implementation guide

---

## Knowledge Bases (All Ready)

| Knowledge Base | Source | Size | Status |
|----------------|--------|------|--------|
| `kg_context.yaml` | KG flattened | ~214K tokens | ✅ Ready |
| `energy_knowledge.json` | CTE, IDAE | 26KB | ✅ Ready |
| `renovation_process_knowledge.json` | CSCAE | 15KB | ✅ Ready |
| `interior_design_knowledge.json` | Gemini synthesis | 113KB | ✅ Ready |
| BCCA database | construction.db | 12K items | ✅ Ready |
| BCCA embeddings | bcca_embeddings.npy | 384-dim | ✅ Ready |

---

## File Locations

### Documentation
```
Lean MVP/docs/
├── PETER_AGENTIC_MASTER_INDEX.md          ← This file
├── PETER_AGENTIC_V0.4_UNIFIED_ESTIMATOR.md ← IMPLEMENTATION GUIDE
├── PETER_AGENTIC_IMPLEMENTATION_AUDIT.md   ← Historical (why V0.4 exists)
├── PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md    ← SUPERSEDED
├── PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md  ← SUPERSEDED
└── PETER_AGENTIC_V0.3.2_UNIFIED_PROPERTY_INTELLIGENCE.md ← SUPERSEDED
```

### Knowledge Bases
```
Lean MVP/standards/
├── energy_knowledge.json
├── renovation_process_knowledge.json
├── interior_design_knowledge.json
├── uniclass_ss_residential.json
├── uniclass_pr_residential.json
└── rules_engine.json

Lean MVP/backend/pricing/
├── kg_context.yaml
├── data/construction.db
└── data/bcca_embeddings.npy
```

### Code to Build (V0.4)
```
Lean MVP/backend/pricing/
├── bcca_search.py              ← TO BUILD
├── system_instruction_template.txt ← TO BUILD
├── unified_estimator.py        ← TO BUILD
├── format_views.py             ← TO BUILD
└── schemas/
    ├── unified_estimate.py     ← TO BUILD
    └── estimation_error.py     ← TO BUILD
```

---

## Implementation Status

| Component | Status | Blocking? |
|-----------|--------|-----------|
| Knowledge bases | ✅ Complete | No |
| KG flattened | ✅ Complete | No |
| BCCA embeddings | ✅ Complete | No |
| **V0.4 Documentation** | ✅ Complete | No |
| bcca_search.py | ⬜ Not started | **YES** |
| unified_estimator.py | ⬜ Not started | **YES** |
| format_views.py | ⬜ Not started | No |
| UI data wiring | ⬜ Not started | No |

---

## Critical Rules (From V0.4 Part 10)

| Rule | Rationale |
|------|-----------|
| NO V1 FALLBACKS | V1 produced garbage |
| NO HARDCODED PRICES | Creates bias |
| NO CHAPTER 18 CODES | Test items, not real construction |
| KITCHEN ONLY FOR BEFORE/AFTER | MVP simplicity |
| <30% GENERAL ATTRIBUTION | Forces room-level granularity |
| 100% KG GROUNDING | Every task must trace to KG |
| 100% BCCA GROUNDING | Every price must come from search_bcca |
| REASONING CHAINS REQUIRED | Explainable AI |

---

## Version History

| Version | Date | Status | Description |
|---------|------|--------|-------------|
| V0.1 | Jan 2026 | ❌ Abandoned | Initial thinking |
| V0.2 | Jan 2026 | ❌ Abandoned | Long context (hit token limits) |
| V0.3 | Jan 2026 | ❌ Superseded | Hybrid (never implemented) |
| V0.3.1 | Jan 2026 | ❌ Superseded | Knowledge integration |
| V0.3.2 | Jan 2026 | ❌ Superseded | Unified Property Intelligence |
| **V0.4** | Jan 2026 | ✅ **CURRENT** | Unified Estimator (complete doc) |

---

## Next Steps

1. **Follow V0.4 Implementation Checklist** (Part 7)
2. Build Phase 1: Core Implementation
3. Build Phase 2: Knowledge Integration
4. Build Phase 3: Pipeline Wiring
5. Build Phase 4: Testing & Validation
6. Build Phase 5: Documentation & Cleanup

**Start here**: Open `PETER_AGENTIC_V0.4_UNIFIED_ESTIMATOR.md` and follow Part 7.
