Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC Implementation Audit & Remediation Plan

> **Date**: January 10, 2026  
> **Updated**: January 10, 2026 (V0.4 Resolution Added)  
> **Purpose**: Track what was documented vs implemented, and resolution path  
> **Status**: V0.3.x ABANDONED → V0.4 UNIFIED ARCHITECTURE ADOPTED

---

## Executive Summary

### The Original Issue (V0.3.x)
- V0.3 → V0.3.1 → V0.3.2 documentation evolved correctly
- But IMPLEMENTATION only created peripheral components
- The CORE V0.3 architecture was never built
- V0.3.2 components don't integrate with V0.3 (because V0.3 doesn't exist)

### The Resolution (V0.4)
**V0.3.x was overengineered.** Splitting into 4 stages (PIR → Gap → Scope → Pricing) 
created complexity, handoff points, and information loss.

**V0.4 simplifies to ONE Gemini call** with:
- Full context (~242K tokens in system instruction)
- Tool calling (search_bcca) for BCCA lookups
- Response schema enforcement for structured output
- All reasoning happens in ONE coherent context

```
V0.3.x (ABANDONED):
PIR → Gap Analysis → Scope Expansion → EstimatorV3 → Format
      (separate)      (separate)        (separate)     (separate)
      
V0.4 (ADOPTED):
PIR → UNIFIED ESTIMATOR (Gap + Scope + Pricing in ONE call) → Format Views
      (all context + tools in single Gemini call)
```

**See**: `PETER_AGENTIC_V0.4_UNIFIED_ESTIMATOR.md` for complete specification.

---

## What You Actually Wanted

**Original Goal (from Master Index):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 YOUR GOAL: Full Pipeline                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 1: Property Intelligence Report ──────────────────────────────────   │
│  Input: Listing + Photos + Cadastre                                         │
│  Output: Building profile, room analysis, regulatory, comparison attrs      │
│                                                                             │
│  STAGE 2-4 (V0.3.x): Separate Gap → Scope → Pricing ◄── OVERCOMPLICATED    │
│  STAGE 2 (V0.4): UNIFIED Estimator                   ◄── CORRECT APPROACH  │
│  Input: Target PIR + Comparable PIRs + Photos                               │
│  Process: Gap analysis + KG traversal + BCCA pricing (in one Gemini call)   │
│  Output: Complete UnifiedEstimate with BoQ + reasoning chains               │
│                                                                             │
│  VALIDATION: Fail-fast, NO V1 fallback ──────────────────────────────────   │
│  Gates: Room attribution, KG grounding, BCCA matching, reasoning chains     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Context Layer (System Instruction ~242K tokens):**

```
├── Role + Grounding Rules (~3K)
├── Knowledge Graph YAML (~214K) ◄── 683 tasks with deps + quantity_guidance
├── Energy Knowledge (~6K flattened) ◄── From V0.3.1
├── Process Knowledge (~4K flattened) ◄── From V0.3.1  
├── Interior Design (~8K flattened) ◄── From V0.3.2
└── BCCA-Speak Guide (~5K) ◄── From V0.3
```

**Tool Layer:**

```
search_bcca(queries: [{keyword, chapter, intent}, ...])
├── Batch queries for efficiency
├── Hybrid BM25 + embedding search
└── Returns top 3 matches per query with prices
```

---

## Part 1: V0.3 Requirements Audit

### What V0.3 MANDATED (from `PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md`)

| Requirement | Lines | Implemented? | Notes |
|-------------|-------|--------------|-------|
| **System Instruction with cached context** | 147-368 | ❌ NO | Complete template documented but never used |
| **Full KG YAML in system instruction** | 351-367 | ❌ NO | `kg_context.yaml` exists but not used in system_instruction |
| **BCCA-Speak translation guide** | 186-255 | ❌ NO | Documented but not in any code |
| **Chapter index** | 193-205 | ❌ NO | Not in any system instruction |
| **search_bcca() tool** | 372-598 | ❌ NO | Complete implementation in doc, NOT in code |
| **validate_bcca_match() tool** | 600-692 | ❌ NO | Complete implementation in doc, NOT in code |
| **EstimatorV3 class** | 696-1125 | ❌ NO | 400+ lines of code documented, NEVER created |
| **Context caching** | 779-856 | ❌ NO | Gemini caching not implemented |
| **ReAct tool calling loop** | 902-949 | ❌ NO | No tool calling in any pipeline code |
| **Fail-fast validation gates** | 1046-1116 | ❌ NO | No validation implemented |
| **NO V1 fallback** | 1129-1195 | ❌ NO | Old renovation.py still exists and is used |

### V0.3 Files That Should Exist But Don't

```
SHOULD EXIST (per V0.3 doc)              ACTUALLY EXISTS?
─────────────────────────────────────────────────────────
pricing/bcca_search.py                   ❌ NO
pricing/process_validation.py            ❌ NO  
pricing/estimator_v3.py                  ❌ NO
pricing/system_instruction_v3.txt        ❌ NO (only system_instruction.txt stub)
```

### What V0.3 Said Would Use The Architecture

```
V0.3 Architecture Flow (DOCUMENTED):
────────────────────────────────────
Gap Analysis Input
       │
       ▼
┌─────────────────────────────────┐
│ EstimatorV3.estimate()          │
│                                 │
│ Uses:                           │
│ • System instruction (cached)   │
│   - Full KG YAML (214K tok)     │
│   - BCCA-speak guide (5K tok)   │
│   - Grounding rules (3K tok)    │
│                                 │
│ • Tools:                        │
│   - search_bcca()               │
│   - validate_bcca_match()       │
│                                 │
│ • ReAct loop for tool calls     │
└─────────────────────────────────┘
       │
       ▼
BoQ with reasoning chains
```

---

## Part 2: V0.3.1 Requirements Audit

### What V0.3.1 MANDATED (from `PETER_AGENTIC_V0.3.1_KNOWLEDGE_INTEGRATION.md`)

| Phase | Requirement | Lines | Implemented? | Notes |
|-------|-------------|-------|--------------|-------|
| **Phase 0** | Extract energy knowledge | 256-265 | ✅ YES | `energy_knowledge.json` created |
| **Phase 0** | Extract process knowledge | 256-265 | ✅ YES | `renovation_process_knowledge.json` created |
| **Phase 1** | Create Energy Context Section | 276-323 | ❌ NO | Documented but never added to system instruction |
| **Phase 1** | Create Process Context Section | 325-344 | ❌ NO | Documented but never added |
| **Phase 1** | Update System Instruction Template | 346-352 | ❌ NO | No system instruction uses knowledge |
| **Phase 2** | Identify 47 energy-relevant KG tasks | 354-370 | ❌ NO | Never done |
| **Phase 2** | Add energy_impact metadata to KG | 372-386 | ❌ NO | KG unchanged |
| **Phase 2** | Update flatten_kg.py for energy | 388-390 | ❌ NO | Not updated |
| **Phase 3** | Verify Idealista energy extraction | 394-402 | ❓ UNKNOWN | Not verified |
| **Phase 3** | Use energy rating in gap analysis | 404-412 | ❌ NO | Gap analysis doesn't use energy |

### V0.3.1 Dependency on V0.3

**Critical**: V0.3.1 EXTENDS V0.3. It adds knowledge to the system instruction.

```
V0.3.1 REQUIRES V0.3 to exist:
──────────────────────────────
V0.3.1 Phase 1 says:
  "Add to system instruction (after KG, before BCCA-speak)"

But there IS no system instruction being used!
V0.3.1 can't be implemented without V0.3 first.
```

---

## Part 3: V0.3.2 Requirements Audit

### What V0.3.2 MANDATED (from `PETER_AGENTIC_V0.3.2_UNIFIED_PROPERTY_INTELLIGENCE.md`)

| Requirement | Implemented? | Notes |
|-------------|--------------|-------|
| Extract interior_design_knowledge.json | ✅ YES | 113KB created |
| PropertyIntelligenceReport schema | ✅ YES | Pydantic models created |
| PropertyIntelligenceReport generator | ⚠️ PARTIAL | Created but doesn't use system instruction |
| ComparativeGapAnalysis schema | ✅ YES | Pydantic models created |
| ComparativeGapAnalysis generator | ⚠️ PARTIAL | Created but doesn't use V0.3 |
| Database tables | ✅ YES | Migration applied |
| UI components | ✅ YES | Cards created |
| **Integration with V0.3 Scope→Pricing** | ❌ NO | This is the missing link! |

### V0.3.2 Pipeline (What Was Documented)

```
DOCUMENTED FLOW:
────────────────
Stage 1: Property Intelligence Report (per property)    ◄── Created
Stage 2: Comparative Gap Analysis (target vs comparable) ◄── Created  
Stage 3: Scope Generation (KG-based expansion)          ◄── NOT INTEGRATED
Stage 4: BCCA Pricing (RAG tool calls)                  ◄── DOESN'T EXIST

Stages 3 & 4 depend on V0.3 EstimatorV3 which doesn't exist!
```

---

## Part 4: What Actually Exists in Code

### Backend Code Audit

```
/Lean MVP/backend/
├── pipeline/
│   ├── gemini_client.py          ✅ EXISTS - Basic Gemini wrapper
│   ├── db_helpers.py             ✅ EXISTS - Database helpers
│   ├── steps/
│   │   ├── property_intelligence.py  ✅ NEW - But doesn't use system_instruction
│   │   ├── comparative_gap_analysis.py ✅ NEW - But no tool calling
│   │   ├── assess_uniclass.py    ⚠️ OLD - Supposed to be deprecated by V0.3.2
│   │   └── verify_rules.py       ⚠️ OLD - Supposed to be deprecated by V0.3.2
│   └── v032_orchestrator.py      ✅ NEW - But doesn't connect to V0.3
│
├── pricing/
│   ├── renovation_resolver.py    ⚠️ OLD V1 - The "garbage" producer
│   ├── flatten_kg.py             ✅ EXISTS - Creates kg_context.yaml
│   ├── kg_context.yaml           ✅ EXISTS - Full KG with quantity_guidance
│   ├── system_instruction.txt    ⚠️ STUB - Incomplete, not used
│   │
│   ├── bcca_search.py            ❌ DOESN'T EXIST (V0.3 mandated)
│   ├── process_validation.py     ❌ DOESN'T EXIST (V0.3 mandated)
│   └── estimator_v3.py           ❌ DOESN'T EXIST (V0.3 mandated)
│
├── routes/
│   └── renovation.py             ⚠️ MIXED - V1 routes + V0.3.2 routes added
│
└── scripts/
    ├── extract_energy_knowledge.py     ✅ WORKS
    ├── extract_process_knowledge.py    ✅ WORKS
    └── extract_interior_design_knowledge.py ✅ WORKS
```

### Standards/Knowledge Files

```
/Lean MVP/standards/
├── energy_knowledge.json              ✅ 26KB - Extracted
├── renovation_process_knowledge.json  ✅ 15KB - Extracted  
├── interior_design_knowledge.json     ✅ 113KB - Extracted
├── CTE-DB-HE.txt                      ✅ Source doc
├── CSCAE_Guia_Vecinal_2023.txt        ✅ Source doc
└── (other source docs)                ✅ Present
```

---

## Part 5: The Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WHAT SHOULD EXIST                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  V0.3 CORE (Foundation) ─────────────────────────────────────────────────   │
│  │                                                                          │
│  ├── bcca_search.py (search_bcca tool)              ❌ MISSING              │
│  ├── process_validation.py (validate_bcca_match)    ❌ MISSING              │
│  ├── estimator_v3.py (EstimatorV3 class)            ❌ MISSING              │
│  └── system_instruction_v3.txt (complete template)  ❌ MISSING              │
│                                                                             │
│  V0.3.1 EXTENSIONS (Adds to system instruction) ─────────────────────────   │
│  │                                                                          │
│  ├── Energy context section in system instruction   ❌ CAN'T DO WITHOUT V0.3│
│  ├── Process context section in system instruction  ❌ CAN'T DO WITHOUT V0.3│
│  └── energy_impact metadata in KG                   ❌ NOT DONE              │
│                                                                             │
│  V0.3.2 COMPONENTS (Use V0.3 for pricing) ───────────────────────────────   │
│  │                                                                          │
│  ├── property_intelligence.py                       ✅ EXISTS (standalone)  │
│  ├── comparative_gap_analysis.py                    ✅ EXISTS (standalone)  │
│  ├── v032_orchestrator.py                           ✅ EXISTS (broken link) │
│  └── UI components                                  ✅ EXISTS               │
│                                                                             │
│  KNOWLEDGE BASES (Ready to use) ─────────────────────────────────────────   │
│  │                                                                          │
│  ├── kg_context.yaml (214K tokens)                  ✅ READY                │
│  ├── energy_knowledge.json (26KB)                   ✅ READY                │
│  ├── renovation_process_knowledge.json (15KB)       ✅ READY                │
│  └── interior_design_knowledge.json (113KB)         ✅ READY                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

DEPENDENCY CHAIN:
─────────────────
V0.3.2 Components ──requires──► V0.3 Core ──uses──► Knowledge Bases
        │                           │                     │
        │                           │                     │
     ✅ Built                    ❌ MISSING            ✅ Ready
```

---

## Part 6: Remediation Plan

### Priority 1: Build V0.3 Core (MUST DO FIRST)

| Task | File to Create | Based on Doc Lines |
|------|---------------|-------------------|
| 1.1 | `pricing/bcca_search.py` | V0.3 lines 376-598 |
| 1.2 | `pricing/process_validation.py` | V0.3 lines 600-692 |
| 1.3 | `pricing/system_instruction_v3.txt` | V0.3 lines 151-367 |
| 1.4 | `pricing/estimator_v3.py` | V0.3 lines 700-1125 |

**Verification**: Run EstimatorV3 on a gap analysis, verify tool calls work.

### Priority 2: Integrate V0.3.1 Knowledge

| Task | Update Required |
|------|-----------------|
| 2.1 | Add energy context to `system_instruction_v3.txt` |
| 2.2 | Add process context to `system_instruction_v3.txt` |
| 2.3 | Identify 47 energy-relevant KG tasks |
| 2.4 | Add `energy_impact` to those tasks in KG |
| 2.5 | Update `flatten_kg.py` to include energy_impact |
| 2.6 | Regenerate `kg_context.yaml` |

**Verification**: System instruction includes energy/process knowledge.

### Priority 3: Wire V0.3.2 to V0.3

| Task | File to Update |
|------|---------------|
| 3.1 | Update `v032_orchestrator.py` to call EstimatorV3 |
| 3.2 | Pass gap analysis output (intervention_ids) to EstimatorV3 |
| 3.3 | Store BoQ results alongside PIR and gap analysis |

**Verification**: Full pipeline produces priced BoQ.

### Priority 4: Retire V1

| Task | Action |
|------|--------|
| 4.1 | Remove or deprecate old `renovation_resolver.py` |
| 4.2 | Update routes to use V0.3 endpoints |
| 4.3 | Remove V1 fallback references |

---

## Part 7: What Components Are Actually Correct

### ✅ Ready to Use (No Changes Needed)

| Component | Status | Notes |
|-----------|--------|-------|
| `kg_context.yaml` | ✅ Good | Full KG with quantity_guidance (214K tokens) |
| `energy_knowledge.json` | ✅ Good | 26KB, 7 ratings, 13 interventions |
| `renovation_process_knowledge.json` | ✅ Good | 15KB, 10 steps, FAQs |
| `interior_design_knowledge.json` | ✅ Good | 113KB, trends, sourcing |
| Extraction scripts | ✅ Good | Can re-run if needed |
| Database migration 007 | ✅ Good | Tables created |
| Frontend types | ✅ Good | TypeScript types match schemas |
| Frontend components | ✅ Good | Cards ready for data |

### ⚠️ Need Integration Work (Partially Correct)

| Component | Issue | Fix |
|-----------|-------|-----|
| `property_intelligence.py` | Doesn't use system_instruction | Update to use V0.3 pattern |
| `comparative_gap_analysis.py` | No tool calling | Either standalone or use V0.3 |
| `v032_orchestrator.py` | Doesn't call EstimatorV3 | Wire up after V0.3 built |
| `renovation.py` routes | V1 + V0.3.2 mixed | Clean up after V0.3 built |

### ❌ Need to Build from Scratch

| Component | Source |
|-----------|--------|
| `bcca_search.py` | V0.3 doc lines 376-598 |
| `process_validation.py` | V0.3 doc lines 600-692 |
| `estimator_v3.py` | V0.3 doc lines 700-1125 |
| `system_instruction_v3.txt` | V0.3 doc lines 151-367 + V0.3.1 additions |

---

## Part 8: Questions to Resolve Before Implementing

1. **Should V0.3.2 PIR/Gap use system_instruction too?**
   - Currently: Regular prompts
   - Option A: Keep as regular prompts (simpler, different purpose)
   - Option B: Also use system_instruction (consistent, but different knowledge needed)

2. **Should PIR/Gap output feed directly into EstimatorV3?**
   - Currently: PIR → Gap → ??? → Pricing
   - Plan: Gap outputs `intervention_ids` → EstimatorV3 expands with KG → Prices

3. **What about the old renovation.py routes?**
   - Option A: Keep them working during transition
   - Option B: Break them now, fix everything at once
   - Option C: Deprecation period with warnings

4. **Context caching - implement now or later?**
   - V0.3 doc describes it but it's optional
   - Can work without caching (just slower/costlier)
   - Implement caching after core works

---

## Part 9: Implementation Order

```
WEEK 1: V0.3 Core
────────────────────────────────────────────
Day 1: bcca_search.py + process_validation.py
Day 2: system_instruction_v3.txt (with KG)
Day 3: estimator_v3.py (basic, no caching)
Day 4: Test on listing 12
Day 5: Fix issues, validate

WEEK 2: V0.3.1 Integration
────────────────────────────────────────────
Day 1: Add energy context to system instruction
Day 2: Add process context to system instruction
Day 3: Identify energy-relevant KG tasks
Day 4: Add energy_impact, regenerate kg_context.yaml
Day 5: Test energy reasoning

WEEK 3: V0.3.2 Wiring
────────────────────────────────────────────
Day 1: Wire v032_orchestrator → EstimatorV3
Day 2: Update PIR to pass context forward
Day 3: End-to-end test: PIR → Gap → Scope → BoQ
Day 4: Update UI to display full pipeline
Day 5: Documentation cleanup

WEEK 4: Cleanup
────────────────────────────────────────────
Day 1-2: Deprecate V1 routes
Day 3: Implement context caching (optional)
Day 4-5: Testing, polish
```

---

## Part 10: Success Criteria Checklist

### V0.3 Core Working
- [ ] `search_bcca()` returns valid BCCA items
- [ ] `validate_bcca_match()` validates process integrity
- [ ] System instruction loads with full KG (~214K tokens)
- [ ] EstimatorV3 produces BoQ with tool calls
- [ ] All line items have BCCA codes
- [ ] All line items have reasoning chains
- [ ] Room attribution < 30% "General"
- [ ] Fail-fast on validation failure (no V1 fallback)

### V0.3.1 Knowledge Integrated
- [ ] Energy context in system instruction
- [ ] Process context in system instruction
- [ ] 47 energy-relevant tasks identified
- [ ] `energy_impact` in KG for those tasks
- [ ] LLM can reason about energy improvements

### V0.3.2 Pipeline Complete
- [ ] PIR generates for target property
- [ ] PIR generates for comparable properties
- [ ] Gap analysis compares PIRs
- [ ] Gap analysis outputs `intervention_ids`
- [ ] EstimatorV3 receives intervention_ids
- [ ] EstimatorV3 produces priced BoQ
- [ ] Full result stored in database
- [ ] UI displays complete analysis

### V1 Retired
- [ ] No code path uses old renovation_resolver.py for pricing
- [ ] All routes use V0.3 architecture
- [ ] No "fallback to V1" logic anywhere

---

---

## Part 11: FULL IMPLEMENTATION PLAN (Traced from Docs)

### What the Docs Mandate (Cross-Referenced)

| Master Index Reference | V0.3 Doc Reference | V0.3.1 Doc Reference | V0.3.2 Doc Reference | Status |
|------------------------|--------------------|--------------------|---------------------|--------|
| Lines 57-70: Context Layer | Lines 147-368: System Instruction | Lines 276-344: Add knowledge | - | ❌ NOT BUILT |
| Lines 73-87: Tools Layer | Lines 372-692: search_bcca + validate | - | - | ❌ NOT BUILT |
| Lines 93-102: Stage 1 PIR | - | - | Lines 29-237: PIR Schema | ✅ BUILT (standalone) |
| Lines 104-109: Stage 2 Gap | - | - | Lines 239-350: Gap Schema | ✅ BUILT (standalone) |
| Lines 111-117: Stage 3 Scope | Lines 256-299: KG traversal | - | - | ❌ NOT BUILT |
| Lines 119-125: Stage 4 Pricing | Lines 700-1030: EstimatorV3 | - | - | ❌ NOT BUILT |
| Lines 130-143: Validation | Lines 1046-1195: Fail-fast | - | - | ❌ NOT BUILT |

### The Complete Implementation Steps

```
PHASE 1: BUILD V0.3 CORE (The Foundation)
═════════════════════════════════════════

Step 1.1: Create pricing/bcca_search.py
         Source: V0.3 doc lines 376-598
         What: BCCASearchTool class with BM25 + embedding hybrid search
         Output: search_bcca(keyword, chapter, intent) → top 5 BCCA matches

Step 1.2: Create pricing/process_validation.py
         Source: V0.3 doc lines 600-692
         What: validate_bcca_match() for process integrity (not price ranges)
         Output: {valid: bool, errors: []}

Step 1.3: Create pricing/system_instruction_v3.txt
         Source: V0.3 doc lines 147-368
         Content:
           ├── Role: "You are a senior Spanish renovation cost estimator"
           ├── Grounding Rules: Use ONLY KG tasks, call search_bcca for prices
           ├── BCCA-Speak Guide: Chapter index, keyword construction
           ├── Quantity Formulas: floor_m2, wall_m2, perimeter_ml, unit
           └── Output Format: JSON with reasoning chains
         
         Then ADD (from V0.3.1 doc lines 276-344):
           ├── Energy Context: Climate zones, age→rating, intervention impacts
           └── Process Context: Renovation triggers (CSCAE)
         
         Then ADD (from V0.3.2):
           └── Design Context: Quality tiers, style indicators

Step 1.4: Create pricing/estimator_v3.py
         Source: V0.3 doc lines 700-1030
         What: EstimatorV3 class that:
           1. Loads system_instruction_v3.txt + kg_context.yaml
           2. Registers search_bcca and validate_bcca_match as tools
           3. Creates/uses Gemini context cache
           4. Implements ReAct tool calling loop
           5. Parses response and runs validation gates
         
Step 1.5: Implement Validation Gates
         Source: V0.3 doc lines 1046-1116
         Gates:
           ├── Room attribution: <30% "General"
           ├── BCCA grounding: All tasks have valid BCCA codes
           ├── Reasoning chains: All line items have explanation
           └── Tasks exist: BoQ not empty
         On failure: Return structured error, NO V1 fallback

VERIFICATION: 
- Run EstimatorV3 on a simple gap analysis
- Verify tool calls appear in logs
- Verify BoQ has BCCA codes and reasoning


PHASE 2: INTEGRATE V0.3.1 KNOWLEDGE
═══════════════════════════════════

Step 2.1: Flatten energy_knowledge.json for system instruction
         Source: V0.3.1 doc lines 276-323
         Add to system_instruction_v3.txt:
           ├── Climate zones table (A-E with U-value limits)
           ├── Age → Rating mapping table
           └── Intervention impacts table

Step 2.2: Flatten process_knowledge.json for system instruction  
         Source: V0.3.1 doc lines 325-344
         Add to system_instruction_v3.txt:
           └── Renovation triggers (regulatory, economic, comfort, building_problems)

Step 2.3: Identify 47 energy-relevant KG tasks
         Source: V0.3.1 doc lines 354-370
         Script: Find tasks matching insulation, window, hvac, solar patterns

Step 2.4: Add energy_impact to those KG tasks
         Source: V0.3.1 doc lines 372-386
         Add to hybrid_renovation_graph.json:
           energy_impact: {affects_u_value, element, typical_letters, climate_sensitivity}

Step 2.5: Regenerate kg_context.yaml with energy_impact
         Update flatten_kg.py to include energy_impact field

VERIFICATION:
- System instruction includes energy tables
- kg_context.yaml shows energy_impact on relevant tasks


PHASE 3: WIRE V0.3.2 TO V0.3
════════════════════════════

Step 3.1: Update property_intelligence.py
         Current: Uses regular prompts
         Change: Use system_instruction pattern for consistency
         Note: PIR doesn't need BCCA tools, but should share knowledge context

Step 3.2: Update comparative_gap_analysis.py  
         Current: Outputs gaps but no integration
         Change: Ensure output includes intervention_ids that map to KG tasks

Step 3.3: Update v032_orchestrator.py
         Current: Runs PIR → Gap → stops
         Change: Add stages:
           ├── Stage 3: KG expansion (traverse requires/triggers)
           └── Stage 4: Call EstimatorV3 for pricing

Step 3.4: Create scope_expansion.py
         Source: V0.3 doc lines 256-299
         What: Take intervention_ids, traverse KG, return full task list
         Process:
           1. Load KG
           2. For each intervention_id, follow REQUIRES backward
           3. For each task, follow TRIGGERS forward
           4. Return deduplicated task list with quantities

VERIFICATION:
- Full pipeline: PIR → Gap → Scope → BoQ
- End-to-end test on listing 12


PHASE 4: CLEANUP & RETIRE V1
════════════════════════════

Step 4.1: Update Master Index implementation status
         Change all "🔲 Pending" to "✅ Complete" for actually-completed items

Step 4.2: Deprecate old renovation_resolver.py
         Add deprecation warning, point to EstimatorV3

Step 4.3: Update routes/renovation.py
         Remove or disable V1 endpoints
         Keep only V0.3.2 endpoints that use new pipeline

Step 4.4: Remove V1 fallback references
         Search codebase for any "fallback" logic

Step 4.5: Update frontend API calls
         Point to new V0.3.2 endpoints

VERIFICATION:
- No code path uses old renovation_resolver for pricing
- All routes use EstimatorV3
```

### Files To Create (In Order)

```
PHASE 1 FILES:
pricing/bcca_search.py          ← ~200 lines, from V0.3 doc
pricing/process_validation.py   ← ~100 lines, from V0.3 doc
pricing/system_instruction_v3.txt ← ~500 lines, from V0.3 + V0.3.1 docs
pricing/estimator_v3.py         ← ~400 lines, from V0.3 doc

PHASE 3 FILES:
pipeline/steps/scope_expansion.py ← ~150 lines, new

UPDATES TO EXISTING:
pricing/flatten_kg.py           ← Add energy_impact
pipeline/steps/property_intelligence.py ← Use system_instruction pattern
pipeline/steps/comparative_gap_analysis.py ← Ensure intervention_ids output
pipeline/v032_orchestrator.py   ← Add stages 3 & 4
```

### Success State (What You'll Have)

```
When complete, running the pipeline will:

1. INPUT: Listing ID + Comparable IDs

2. STAGE 1 - PIR: 
   → Call Gemini with photos
   → Output: PropertyIntelligenceReport with comparison_attributes

3. STAGE 2 - GAP:
   → Compare target PIR to comparable PIRs
   → Output: ComparativeGapAnalysis with intervention_ids

4. STAGE 3 - SCOPE:
   → Take intervention_ids
   → Traverse KG (requires + triggers)
   → Output: Full task list with quantities per room

5. STAGE 4 - PRICING:
   → EstimatorV3 receives tasks
   → System instruction has: KG + Energy KB + Process KB + Design KB + BCCA-speak
   → LLM calls search_bcca() for each task (tool calling)
   → LLM reflects on results, selects best matches
   → Output: BoQ with BCCA codes, prices, reasoning chains

6. VALIDATION:
   → Check: Room attribution, KG grounding, BCCA matching, reasoning
   → If fail: Structured error (NO fallback)
   → If pass: Complete result

7. OUTPUT:
   → PropertyIntelligenceReport (target)
   → PropertyIntelligenceReports (comparables)
   → ComparativeGapAnalysis
   → Full BoQ with:
     - Every line item traced to KG task
     - Every price traced to BCCA code
     - Reasoning chain for every decision
     - Room attribution for every task
```

---

*This document tracks the gap between documentation and implementation.*
*Update as remediation progresses.*

