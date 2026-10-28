Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Renovation Pipeline - Documentation Index

## Quick Reference

| Doc | What It Explains | When To Read |
|-----|------------------|--------------|
| [V5 Implementation Plan (Single Strategy)](./PIPELINE_V5_IMPLEMENTATION_PLAN_SINGLE_STRATEGY.md) | **Strict implementation plan for V5 (market_standard only)** | Start here |
| [Room Tags + Slots (GSO) V1](./ROOM_TAGS_SLOTS_GSO_V1.md) | Canonical room types + slot universe + open-plan rules | When editing schemas/prompts |
| [Slots by Room Type V1](./SLOTS_BY_ROOM_TYPE_V1.md) | Complete room-type → slot protocol mapping | When implementing room slot decider |
| [V5 Slot-first Plan (legacy)](./V5_SLOTS_PIPELINE_IMPLEMENTATION_PLAN.md) | Older multi-strategy V5 plan (superseded) | Reference only |
| [V3 Plan (legacy)](./RENOVATION_PIPELINE_V3_PLAN.md) | Pre-V5 architecture plan | Historical reference |
| [KG Traversal (legacy)](./KG_TRAVERSAL_ARCHITECTURE.md) | How the legacy Knowledge Graph worked | Historical reference |
| [history/RENOVATION_PIPELINE_V2.md](history/RENOVATION_PIPELINE_V2.md) | Previous version (historical) | For context on what changed |

---

## V4 vs V5 (30-second summary)

```text
V4 (CURRENT end-to-end)                                  V5 (TARGET end-to-end)
───────────────────────────────────────────               ───────────────────────────────────────────
Listing → clustering → target PIR (per room, 6 dims)      Listing → constrained clustering (canonical room types)
         + comparable PIR (whole-home, 6 dims)                     → room tags (room_type/env/combined)
         → strategy selection → delta (6 dims)                      → comparable PIR V5 (whole-home, slots from tags)
         → worklist (BCCA-ish text)                                 → target PIR V5 (per room, slot schema)
         → BCCA match → quant plan → forage → BOQ                   → strategy selection V5 (slot targets)
                                                                     → delta V5 (room × slot one-liners)
                                                                     → decompose (cheap LLM → matchable work items)
                                                                     → BCCA match → quant/forage/BOQ (unchanged tail)
```

Key idea:
- V4’s main fragility is the open-ended “write the worklist” bridge.
- V5 replaces that bridge with **slots**, making completeness deterministic and matching cheaper/more stable.

---

## The 30-Second Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   1. WHAT'S WRONG?                        LLM (Creative)                     │
│      └─ Gap analysis compares target      "This bathroom is from the 80s,   │
│         to comparables                     comparables have modern finishes" │
│                                                                              │
│   2. WHAT TASKS?                          KG (Complete)                      │
│      └─ Full backward traversal           "Install toilet" requires         │
│         from terminal tasks               grouting, tiling, waterproofing,  │
│                                           plumbing, demolition, protection   │
│                                                                              │
│   3. HOW MUCH?                            Code (Deterministic)              │
│      └─ Quantities from formulas          25.5 m² × €32.50 = €828.75        │
│         Prices from BCCA database                                           │
│                                                                              │
│   4. TWO OUTPUTS:                                                           │
│      ├─ Customer: Rich narrative + cost   "We'll transform your bathroom"   │
│      └─ Architect: Full BoQ + specs       BCCA codes, quantities, notes     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files

### Backend

| File | Purpose |
|------|---------|
| `/backend/pricing/renovation_resolver.py` | **THE BRAIN** - KG traversal, pricing, BoQ generation |
| `/backend/pipeline/gap_analysis.py` | LLM gap analysis, produces room narratives |
| `/backend/routes/renovation.py` | API endpoints, orchestrates pipeline |
| `/experiments/renovation_costing/hybrid_renovation_graph.json` | **THE KG** - 683 tasks, 2789 edges, quantity guidance |

### Frontend

| File | Purpose |
|------|---------|
| `/frontend/src/app/property/[id]/page.tsx` | Main property page with Card 2 scopes |
| `/frontend/src/components/RenovationTierModal.tsx` | Detail view with architect BoQ |

---

## Current Status

### ✅ Working
- KG with 683 canonical tasks
- 2,789 dependency edges (`requires` + `triggers`)
- `quantity_guidance` for all tasks
- BCCA matching with hybrid search
- Basic gap analysis

### ⚠️ Needs Fix (V3 Plan)
- **Resolver traversal** - Currently selective, needs full traversal
- **Gap analysis output** - Needs customer-focused narrative fields
- **Response structure** - Needs customer vs architect views

### 🔄 In Progress
- Implementing V3 architecture
- Testing full backward traversal

---

## The Philosophy

Each tool does what it's best at. No tool does another's job.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    LLM      │     │     KG      │     │    CODE     │
│             │     │             │     │             │
│  Creative   │ ──▶ │  Complete   │ ──▶ │   Precise   │
│  Nuanced    │     │  Standard   │     │   Determin. │
│  Contextual │     │  Exhaustive │     │   Math      │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Debugging Guide

### "Tasks are missing"
1. Check traversal is following ALL `requires` edges
2. Look for selective filtering in `traverse()` function
3. Test with: `full_backward_traversal(terminal_task_id)`

### "Wrong order"
1. Check topological sort is applied
2. Verify edges in KG are correct
3. Test with: `topological_sort(task_set, kg_tasks)`

### "Quantities seem wrong"
1. Check `quantity_guidance` in KG for that task
2. Verify room dimensions are passed correctly
3. Look at `typical_rules` and `constraints`

### "Prices don't match"
1. Check BCCA match quality score
2. Verify unit compatibility (m² vs ud vs ml)
3. Look at matched BCCA code description

---

## ASCII Diagram: Complete Flow

See [V3 Plan](./RENOVATION_PIPELINE_V3_PLAN.md) for the full annotated flow diagram.

---

## Change Log

| Date | Change | Doc |
|------|--------|-----|
| 2025-01-09 | Created V3 architecture plan | V3_PLAN |
| 2025-01-09 | Documented KG traversal fix | KG_TRAVERSAL |
| 2025-01-08 | Enriched KG with quantity_guidance | - |
| Previous | V2 architecture | PIPELINE_V2 |

---

## Next Steps

1. **Implement full traversal** in `renovation_resolver.py`
2. **Add topological sort** for correct ordering
3. **Update gap analysis** with customer-focused fields
4. **Restructure API response** for customer/architect views
5. **Update frontend** to render both views

