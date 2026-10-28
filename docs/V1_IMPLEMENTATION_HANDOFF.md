Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V1.0 Pipeline Implementation Handoff

---

## ⚠️ FIRST: Read the Workspace Rules

**File:** `/root/puedo_casa/.cursorrules`

Before you write a single line of code, read the `.cursorrules` file. It contains two critical sections:

1. **LLM Prompt Writing Principles** — If you modify any prompts, follow these
2. **Pipeline Implementation Principles** — These are NON-NEGOTIABLE for this task

The Pipeline Implementation Principles cover:
- Asynchronous checkpointing (how to save/resume)
- Foreground logging (how to test)
- Fail Loud and Fast (how to handle errors)
- No Legacy Support (what NOT to import)
- Protected Test Data (what NEVER to delete for Listing 12)
- Use Existing Services (what NOT to reimplement)
- Full Cached Context (what MUST be included)

These rules exist because we learned them the hard way. Violating them will cause pain.

---

## Your Role and Why You're Here

You are implementing the V1.0 8-phase renovation estimation pipeline. This is not a greenfield project — you're building on top of a working V0.6 system, preserving its battle-tested patterns while restructuring for new capabilities.

**Why this matters:** The V0.6 pipeline works. It has solved dozens of edge cases around JSON parsing, error recovery, image handling, and Gemini quirks. Your job is NOT to reinvent these solutions — it's to reorganize them into the new 8-phase structure while adding the missing pieces.

Think of yourself as an architect renovating a building while keeping it habitable. You can't demolish everything and start over. You must understand what exists, what works, and carefully transplant the good parts.

---

## The Documents You Have and How to Read Them

### Primary Implementation Specification

**File:** `/root/puedo_casa/lean-mvp/docs/V1_IMPLEMENTATION_PLAN.md`

This is your blueprint. But don't read it as a checklist to execute blindly. Read it as a conversation with a senior architect who has thought deeply about this system.

When you read Part 1 (Complexity to Preserve), ask yourself: "Why did they call this out? What would go wrong if I skipped this?" The JSON sanitization section exists because Gemini sometimes returns malformed JSON with markdown fences or trailing commas. If you write a "clean" implementation that doesn't handle this, you'll spend hours debugging mysterious parsing failures.

When you read Part 2 (New Requirements), think about the dependencies. Phase 2 (PRICE LOOKUP) is code-based, not LLM-based. Why? Because price lookups are deterministic — they don't benefit from reasoning, and they're expensive to do via LLM. The architecture chose to move this to code. Understand WHY before implementing HOW.

When you read Part 8 (Testing Strategy), take the warnings about Listing 12 seriously. The clustering data took significant effort to create. Deleting it means re-doing manual work. The SQL scripts are there to help you reset safely.

### Prompt Specifications

**File:** `/root/puedo_casa/lean-mvp/docs/PIPELINE_V1_PROMPTS.md`

This documents what each LLM phase should accomplish and how. But more importantly, it documents the REASONING PRINCIPLES that each prompt must embody.

When you implement `phase_prompts_v1.py`, don't just copy the text. Understand why each section exists:
- "WHY THIS TASK MATTERS" — Gemini performs better when it understands purpose
- "HOW TO READ [CONTEXT]" — The model has 400K tokens of context; it needs guidance on what to prioritize
- "WHAT TO DOUBT" — Prevents overconfident outputs

### Schema Specifications

**File:** `/root/puedo_casa/lean-mvp/docs/V1_SCHEMA_SPECIFICATION.md`

This defines the data contracts between phases. Each phase's output becomes the next phase's input.

Ask yourself: "What happens if Phase 1 outputs an item without a `bcca_code`?" Phase 2 (PRICE LOOKUP) will fail to find a price. Is that acceptable? The schema says `bcca_code` is required for BCCA items. But what about FFE items? They have `ffe_code` instead. Your Phase 2 implementation must handle both.

### Deprecation Plan

**File:** `/root/puedo_casa/lean-mvp/docs/DEPRECATION_PLAN.md`

This tells you what NOT to import. The V0.5/V0.6 files have been marked deprecated with warnings.

When you see `from pricing.multi_phase_estimator_v2 import ...`, stop and think: "Is this deprecated? Should I be importing from V1 instead?" The deprecation warnings will fire at runtime, but you should catch these at code-review time.

### Architecture Overview

**File:** `/root/puedo_casa/lean-mvp/docs/PIPELINE_V1_ARCHITECTURE.md`

This gives you the bird's-eye view. Read it first to understand the flow, then dive into the implementation details.

---

## The Code You're Building On

### The V0.6 Estimator (To Study, Not Import)

**File:** `/root/puedo_casa/lean-mvp/backend/pricing/multi_phase_estimator_v2.py`

This is the current working implementation. Study it deeply before writing V1.

Look at `_build_context()` (around line 473). This is how context caching works. Your V1 implementation will do something similar but with additional knowledge graphs.

Look at `_execute_phase()` (around line 600). This shows the pattern: build prompt → call Gemini → parse response → validate → checkpoint. Your V1 will follow this same pattern.

Look at `_sanitize_json()`. This handles Gemini's tendency to wrap JSON in markdown code fences or add trailing commas. Copy this logic — it's battle-tested.

Look at the retry logic with exponential backoff. Gemini occasionally fails with 500 errors. The retry logic handles this gracefully.

**CRITICAL:** Don't import from this file in V1. Study it, copy patterns, but keep V1 independent.

### The V0.6 Prompts (To Study, Not Copy)

**File:** `/root/puedo_casa/lean-mvp/backend/pricing/phase_prompts_v2.py`

These are the V0.6 prompts. They work, but they're not as deeply reasoned as the V1 prompts should be.

Compare them to the specifications in `PIPELINE_V1_PROMPTS.md`. Notice how V1 prompts have extensive "WHY" and "HOW TO READ" sections that V0.6 lacks.

### The V1 Prompt Templates (Your Starting Point)

**File:** `/root/puedo_casa/lean-mvp/backend/pricing/phase_prompts_v1.py`

This file already exists with the prompt templates. Your job is to integrate them into the orchestrator.

Read each prompt carefully. Notice the structure:
1. Goal explanation
2. Context reading guidance
3. Deep thinking prompts
4. Output schema

The prompts guide Gemini on HOW to think, not just WHAT to output.

### The V1 Schemas (Your Data Contracts)

**File:** `/root/puedo_casa/lean-mvp/backend/pricing/schemas/gemini_schemas_v1.py`

These define the JSON schemas that Gemini must output. They're used for Gemini's constrained decoding feature.

Notice how schemas evolve across phases:
- Phase 1 outputs `ScopeBoqItem` (with bcca_code/ffe_code, quantity, duration)
- Phase 2 adds `unit_price` and `line_total` (code-based, not LLM)
- Phase 3 outputs `AdjustedItem` (with peer review reasoning)

### The Database Helpers

**File:** `/root/puedo_casa/lean-mvp/backend/pipeline/db_helpers.py`

This contains functions for saving/loading pipeline data. You'll need to add V1-specific functions.

Look at how checkpointing works. Each phase saves its output, and the orchestrator can resume from any checkpoint.

### The PIR Generator (For Smart M² Integration)

**File:** `/root/puedo_casa/lean-mvp/backend/pricing/pir_generator.py`

This generates Property Intelligence Reports. It's been updated to include Smart M² dimensions when available.

Look at how `smart_m2_data` is passed in and integrated into the room descriptions. Phase 1 will use these dimensions for quantity calculations.

### The Smart M² Step

**File:** `/root/puedo_casa/lean-mvp/backend/pipeline/steps/smart_m2.py`

This estimates room dimensions. It runs AFTER clustering and BEFORE PIR generation.

Look at the output structure — it includes `wall_descriptions` with named walls (like "long_wall", "window_wall") and their dimensions. This enables rich descriptions in the PIR.

---

## What You're Building

### `multi_phase_estimator_v1.py`

This is the main orchestrator. It should:

1. **Initialize** — Load listing data, PIR, strategic reasoning, canonical room IDs
2. **Build cached context** — ONCE, at the start, with ALL knowledge graphs and indexes
3. **Execute phases sequentially** — With checkpointing after each
4. **Handle Phase 2 specially** — It's code-based, not LLM

**Think about:**
- What happens if Phase 1 fails halfway through? The checkpoint should save what was produced.
- What happens if the user closes and comes back? The orchestrator should resume from the last checkpoint.
- What happens if Gemini returns malformed JSON? The sanitizer should clean it before parsing.

### Phase 2: PRICE LOOKUP (Code-Based)

This is NOT an LLM phase. It's pure Python:

```python
async def _execute_phase_2_price_lookup(self, items: List[Dict]) -> List[Dict]:
    """
    For each item from Phase 1:
    - If bcca_code: lookup price in BCCA database
    - If ffe_code: lookup price in FFE database
    - Calculate line_total = quantity × unit_price
    """
```

**Think about:**
- What if a code doesn't exist in the database? Log a warning, set price to 0, continue.
- What if quantity is missing? That's a Phase 1 bug — fail loudly.
- What if the item has BOTH bcca_code AND ffe_code? Sum both prices? Or is that invalid?

Look at `/root/puedo_casa/lean-mvp/backend/pricing/bcca_price_lookup.py` for the existing BCCA lookup.
Look at `/root/puedo_casa/lean-mvp/backend/pricing/ffe_lookup.py` for the existing FFE lookup (if it exists) or create it.

### Phase 5: IMAGE GENERATION

This uses the existing Gemini 2.5 Flash Image service. Look at how V0.6 handles image generation in `multi_phase_estimator_v2.py` around the `_execute_phase_5_images()` method.

**CRITICAL:** The transformation prompt from Phase 4 MUST include the boilerplate instructions about camera angle and structural elements. Phase 4 generates these prompts. Phase 5 just executes them.

### Database Tables

The migration script exists at:
**File:** `/root/puedo_casa/lean-mvp/supabase/migrations/011_v1_pipeline_schema.sql`

Run this migration before testing. It creates:
- `unified_estimates_v1` — Stores all phase outputs
- `viewing_checklists_v1` — Phase 6 output
- `eli5_summaries_v1` — Phase 7 output
- `architect_reports_v1` — Phase 8 output

---

## Implementation Sequence

### Step 1: Create the Orchestrator Skeleton

Start with the class structure. Define all methods as stubs:

```python
class MultiPhaseEstimatorV1:
    async def run(self, listing_id: int, package_type: str) -> Dict:
        """Main entry point."""
        
    async def _build_cached_context(self, ...) -> str:
        """Build FULL context ONCE."""
        
    async def _execute_phase_1(self, ...) -> List[Dict]:
        """SCOPE + BOQ — LLM."""
        
    async def _execute_phase_2(self, items: List[Dict]) -> List[Dict]:
        """PRICE LOOKUP — Code."""
        
    async def _execute_phase_3(self, ...) -> List[Dict]:
        """PEER REVIEW — LLM."""
        
    # ... etc
```

### Step 2: Implement Cached Context Building

Copy the pattern from V0.6's `_build_context()`, but add:
- ALL THREE knowledge graphs (energy, process, design)
- Smart M² section if available
- V1 system instruction header

### Step 3: Implement LLM Phase Execution

Create a generic `_execute_llm_phase()` that:
1. Gets the prompt from `phase_prompts_v1.py`
2. Appends it to cached context
3. Calls Gemini with the appropriate schema
4. Sanitizes and parses the response
5. Validates the output
6. Checkpoints

### Step 4: Implement Phase 2 (Code-Based)

This is the new piece. No LLM, just database lookups:
1. For each item from Phase 1
2. Look up price by code (BCCA or FFE)
3. Calculate `line_total = quantity × unit_price`
4. Return enriched items

### Step 5: Wire Up to Package Orchestrator

Update `/root/puedo_casa/lean-mvp/backend/pipeline/package_orchestrator.py` to use V1 instead of V0.6.

### Step 6: Test with Listing 12

Use the SQL from `V1_IMPLEMENTATION_PLAN.md` Part 8 to reset Listing 12 (WITHOUT deleting clustering/comparables).

Run the full pipeline. Check:
- Does each phase complete?
- Are checkpoints saved?
- Can you resume from a checkpoint?
- Do the outputs match the schemas?

---

## What to Doubt and Question

### Context Size

The cached context is ~410K tokens. That's within Gemini's 1M limit, but it's large. If you see timeouts or memory issues, check if context is being duplicated somewhere.

### Schema Evolution

Items evolve across phases. Phase 1 outputs `ScopeBoqItem`. Phase 2 adds `unit_price`. Phase 3 outputs `AdjustedItem`. Make sure your code handles these different shapes correctly.

### Checkpoint Granularity

V0.6 checkpoints after each phase. Is that sufficient for V1? What if Phase 1 takes 10 minutes and fails at item #95 of 100? Should you checkpoint mid-phase? The answer is probably no (keep it simple), but think about it.

### Error Messages

When something fails, will the error message tell you WHERE it failed? Add logging that includes:
- Phase number
- Item index (if applicable)
- The actual error
- What was being attempted

### Deprecated Imports

Double-check every import. If you see warnings about deprecated modules, stop and fix them. V1 should have NO dependencies on V0.5/V0.6 code.

---

## Files to Modify

### Create New
- `/root/puedo_casa/lean-mvp/backend/pricing/multi_phase_estimator_v1.py` — Main orchestrator

### Modify
- `/root/puedo_casa/lean-mvp/backend/pipeline/db_helpers.py` — Add V1 save/load functions
- `/root/puedo_casa/lean-mvp/backend/pipeline/package_orchestrator.py` — Switch to V1 imports

### Reference (Don't Modify)
- `/root/puedo_casa/lean-mvp/backend/pricing/phase_prompts_v1.py` — Already created
- `/root/puedo_casa/lean-mvp/backend/pricing/schemas/gemini_schemas_v1.py` — Already created
- `/root/puedo_casa/lean-mvp/backend/pricing/multi_phase_estimator_v2.py` — Study but don't import

---

## Success Criteria

When you're done:

1. **Listing 12 runs through all 8 phases** without errors
2. **Checkpoints work** — You can stop mid-pipeline and resume
3. **Logs are comprehensive** — You can see what's happening at each step
4. **No deprecated imports** — V1 is self-contained
5. **Schemas validate** — Each phase's output matches its schema
6. **Phase 2 is code-based** — No LLM call for price lookup
7. **All knowledge graphs are in context** — Energy, process, design

---

## A Note on Style

This isn't about writing "clever" code. It's about writing code that the NEXT developer can understand and debug.

When you're tempted to write a one-liner, ask: "Will I understand this in 3 months?"

When you're tempted to skip error handling, ask: "What will happen when this fails at 3 AM?"

When you're tempted to copy-paste without understanding, ask: "Do I know WHY this code exists?"

The V0.6 codebase is not perfect. But it works. Your V1 should be better — cleaner, more maintainable, better documented — while preserving everything that made V0.6 work.

Good luck.
