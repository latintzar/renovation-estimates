Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V1.0 Implementation Plan
## Comprehensive Technical Specification

**Status:** Planning Complete  
**Date:** January 2026

---

## Executive Summary

This document specifies the COMPLETE implementation of `multi_phase_estimator_v1.py` with full consideration of technical debt, complexity preservation, and production requirements.

**Philosophy:** No shortcuts. No oversimplification. Every piece of complexity in V0.6 exists for a reason and must be either preserved, evolved, or explicitly deprecated.

---

## Part 1: Complexity Inventory (What MUST Be Preserved)

### 1.1 JSON Sanitization (CRITICAL)

**Location:** `multi_phase_estimator_v2.py:58-79`

**Problem:** Gemini hallucinates excessively long decimal numbers:
```python
"unit_price": 1200.000000000000000000000000000000000000000...
```

**Solution that MUST be preserved:**
```python
def sanitize_gemini_json(text: str) -> str:
    """Truncate numbers with >6 decimal places."""
    pattern = r'(\d+)\.(\d{1,6})\d{7,}'
    # Also handle scientific notation hallucinations
    sci_pattern = r'\d+[eE][+-]?\d{5,}'
```

**V1.0 Action:** Copy this function exactly. Do not simplify.

### 1.2 Data Integrity Validation (CRITICAL)

**Location:** `schemas/phase_outputs.py`

**Functions that MUST be preserved:**
- `validate_items_preserved(prev_items, new_items, phase_num)` — Ensures no items lost between phases
- `validate_pricing_complete(items)` — Ensures every item has `unit_price` and `line_total`

**Exceptions that MUST be preserved:**
- `SchemaContinuityError` — Items were lost (DATA INTEGRITY)
- `PricingIncompleteError` — Items missing prices (DATA INTEGRITY)

**V1.0 Action:** Import and use these validators. They are NOT deprecated.

### 1.3 Error Handling (CRITICAL)

**Location:** `schemas/estimation_error.py`

**Error types that MUST be preserved:**
- `EstimationError` — Base class
- `PhaseError` — Phase-specific failures
- `GeminiError` — LLM call failures
- `DataMissingError` — Required data not found
- `CheckpointError` — Pipeline state errors

**V1.0 Action:** Import and use these. They are NOT deprecated.

### 1.4 Retry Logic with JSON Parse Recovery

**Location:** `multi_phase_estimator_v2.py:594-691`

**Pattern that MUST be preserved:**
```python
max_retries = 2
for attempt in range(max_retries):
    try:
        # ... call Gemini ...
        # ... parse JSON ...
        return result
    except json.JSONDecodeError as e:
        if attempt < max_retries - 1:
            continue  # Retry
        raise PhaseError(...)  # Give up
```

**V1.0 Action:** Preserve this pattern. Gemini occasionally produces unparseable output.

### 1.5 Response Parsing (CRITICAL)

**Location:** `multi_phase_estimator_v2.py:630-669`

**Complexity that MUST be preserved:**
1. Strip markdown wrappers (````json ... ```)
2. Find JSON start (skip any preamble text)
3. Find matching closing brace (count braces)
4. Sanitize decimal hallucinations
5. Parse JSON

**V1.0 Action:** Copy this parsing logic exactly. It handles real edge cases.

### 1.6 Image Handling for Vision Phases

**Location:** `multi_phase_estimator_v2.py:729-798`

**Complexity that MUST be preserved:**
1. Fetch images via async HTTP if only URLs provided
2. Encode as base64
3. Build image parts array with mime types
4. Pass to Gemini with images parameter

**V1.0 Action:** Preserve for Phase 4 (rendering prompts).

### 1.7 Context Building

**Location:** `multi_phase_estimator_v2.py:473-555`

**Sections that MUST be preserved:**
- BCCA INDEX (~328K tokens)
- FFE INDEX (~11K tokens)
- BRACKET PIR (JSON dump)
- STRATEGIC REASONING (all fields)
- TARGET PIR (JSON dump)
- LISTING DATA (JSON dump)
- CANONICAL ROOM IDS (formatted list)

**V1.0 Additions:**
- KNOWLEDGE GRAPHS (energy, process, design)
- These are in `standards/*.json`

### 1.8 Canonical Room ID Validation

**Location:** Throughout `multi_phase_estimator_v2.py`

**Pattern:**
```python
self.canonical_room_ids = canonical_room_ids
self.canonical_room_id_set = {r["room_id"] for r in canonical_room_ids}
```

**V1.0 Action:** Preserve this validation infrastructure.

### 1.9 Unified Estimate Building

**Location:** `multi_phase_estimator_v2.py:385-471`

**Aggregations that MUST be preserved:**
- `cost_by_system` — Sum by item.system
- `cost_by_room` — Sum by item.room_id
- `cost_per_sqm` — Total / sqm
- IVA calculation
- Item counts per phase
- Phase times tracking

**V1.0 Action:** Expand to include new phase outputs.

### 1.10 Package Orchestrator Integration

**Location:** `package_orchestrator.py:83`

```python
from .multi_phase_estimator_v2 import MultiPhaseEstimatorV2 as MultiPhaseEstimator
```

**V1.0 Action:** Update import to use `multi_phase_estimator_v1.py` when ready.

---

## Part 2: V1.0 New Requirements

### 2.1 Phase 2: Code-Based Price Lookup (NEW)

**This is NOT an LLM phase.** It's deterministic code.

**Implementation:**
```python
from .bcca_price_lookup import BCCAPriceLookup

async def _run_phase_2_pricing(self, items: List[Dict]) -> List[Dict]:
    """Phase 2: Deterministic price lookup."""
    lookup = BCCAPriceLookup()
    
    for item in items:
        bcca_code = item.get("bcca_code")
        if bcca_code:
            bcca_item = lookup.get_price(bcca_code)
            if bcca_item:
                item["unit_price"] = bcca_item.price
                item["unit"] = bcca_item.unit
                item["line_total"] = item["quantity"] * bcca_item.price
                item["price_source"] = "BCCA"
            else:
                # Code not found - flag for review
                item["price_source"] = "NOT_FOUND"
                item["unit_price"] = 0
                item["line_total"] = 0
        
        # Handle FFE items
        ffe_code = item.get("ffe_code")
        if ffe_code:
            # FFE lookup implementation
            pass
    
    return items
```

**Why code, not LLM:**
- Prices must be traceable and auditable
- No hallucination risk
- Reproducible results
- Faster execution

### 2.2 Phase 5: Image Generation (Gemini 2.5 Flash Image)

**This uses Gemini 2.5 Flash Image** — the same service we already use.
NOT an external service. NOT Flux/SDXL. This is already implemented.

**Implementation:**
```python
async def _run_phase_5_images(
    self,
    room_prompts: List[Dict],  # From Phase 4
    original_photos: List[Dict]
) -> Dict[str, Any]:
    """Phase 5: Generate before/after images using Gemini 2.5 Flash Image."""
    # Uses existing Gemini image generation
    # 16:9 aspect ratio (standard)
    # Same approach as current V0.6 implementation
    pass
```

**Key details:**
- Model: `gemini-2.5-flash-preview-image` (or latest)
- Aspect ratio: 16:9
- Input: Original room photo + transformation prompt from Phase 4
- Output: Generated "after" image URL

### 2.3 Knowledge Graph Loading (NEW)

**Location:** `standards/*.json`

**Files to load:**
- `energy_knowledge.json` (~25K chars)
- `renovation_process_knowledge.json` (~15K chars)
- `interior_design_knowledge.json` (~113K chars)

**NOT loading (too large, not needed for pricing):**
- `uniclass_pr_residential.json` (~1MB)
- `uniclass_ss_residential.json` (~400K)

**Implementation:**
```python
def _load_knowledge_graphs(self) -> str:
    """Load knowledge graphs for Phase 1 context."""
    kg_dir = Path(__file__).parent.parent / "standards"
    
    sections = []
    for filename in ["energy_knowledge.json", "renovation_process_knowledge.json", 
                     "interior_design_knowledge.json"]:
        path = kg_dir / filename
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            sections.append(f"=== {filename} ===\n{json.dumps(data, indent=2)}")
    
    return "\n\n".join(sections)
```

### 2.4 Two Output Streams (NEW)

**Phase 7:** ELI5 Room Summaries (for buyers)
- Plain language
- Emojis for scannability
- Cost per room
- Timeline per room
- Energy explanation

**Phase 8:** Architect Report (for professionals)
- Structured by trade (BCCA chapters)
- BCCA codes visible
- Professional timeline with milestones
- Compliance notes

**Implementation:** Both are LLM phases with different schemas.

---

## Part 3: Phase-by-Phase Implementation

### 3.1 Phase Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: SCOPE + BOQ (Pro)                                     │
│  - Input: All context (PIRs, BCCA, FFE, KGs)                   │
│  - Output: Items with BCCA codes, quantities, schedule          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: PRICE LOOKUP (Code)                                   │
│  - Input: Items from Phase 1                                    │
│  - Output: Items with unit_price, line_total                    │
│  - Method: BCCAPriceLookup.get_price()                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: PEER REVIEW (Pro)                                     │
│  - Input: Priced items + all context                            │
│  - Output: IMPROVED items + adjustments + totals                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
┌─────────────────────────┐     ┌─────────────────────────┐
│  Phase 4: RENDER (Pro)  │     │  Phase 6: CHECK (Flash) │
│  - Needs room photos    │     │  - Viewing checklist    │
│  - Output: prompts      │     │  - No images needed     │
└─────────────────────────┘     └─────────────────────────┘
              ↓
┌─────────────────────────┐
│  Phase 5: IMAGES (Ext)  │
│  - Calls Flux/SDXL      │
│  - Output: image URLs   │
└─────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 7: ELI5 SUMMARIES (Flash)                                │
│  - Input: All previous outputs + generated images               │
│  - Output: Plain language room summaries                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 8: ARCHITECT REPORT (Pro)                                │
│  - Input: All previous outputs                                  │
│  - Output: Professional document structure                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Class Structure

```python
class MultiPhaseEstimatorV1:
    """V1.0 8-Phase Estimator with Code-Based Pricing."""
    
    def __init__(self, ...):
        self.max_output_tokens = 65536
        self.phase_outputs: Dict[int, Any] = {}
        self.current_items: List[Dict] = []
        self.cached_context: Optional[str] = None
        self.canonical_room_ids: Optional[List[Dict]] = None
        self.phase_times: Dict[int, float] = {}
        
        # V1.0: BCCA lookup instance
        self.bcca_lookup = BCCAPriceLookup()
    
    async def estimate(self, ...) -> Dict[str, Any]:
        """Run 8-phase estimation."""
        # Phase 1: SCOPE + BOQ (LLM)
        # Phase 2: PRICE LOOKUP (Code)
        # Phase 3: PEER REVIEW (LLM)
        # Build unified estimate
        pass
    
    async def generate_visuals(self, room_photos: List[Dict]) -> Dict[str, Any]:
        """Run visual phases (4, 5)."""
        # Phase 4: RENDERING PROMPTS (LLM)
        # Phase 5: IMAGE GENERATION (Gemini 2.5 Flash Image, 16:9)
        pass
    
    async def generate_viewing_checklist(self) -> Dict[str, Any]:
        """Run Phase 6."""
        pass
    
    async def generate_buyer_summaries(self) -> Dict[str, Any]:
        """Run Phase 7."""
        pass
    
    async def generate_architect_report(self) -> Dict[str, Any]:
        """Run Phase 8."""
        pass
    
    # Internal methods (preserve from V0.6)
    async def _run_llm_phase(self, phase_num: int, ...) -> Dict[str, Any]:
        """Run an LLM phase with retry logic."""
        pass
    
    def _run_phase_2_pricing(self, items: List[Dict]) -> List[Dict]:
        """Code-based price lookup (not async, not LLM)."""
        pass
    
    async def _build_context(self, ...) -> str:
        """Build cached context with KGs."""
        pass
    
    def _build_phase_prompt(self, phase_num: int, ...) -> str:
        """Build phase-specific prompt."""
        pass
    
    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM response with sanitization."""
        pass
```

---

## Part 4: Technical Debt Acknowledgment

### 4.1 Debt Being Carried Forward (Intentionally)

| Debt Item | Reason to Keep | Location |
|-----------|----------------|----------|
| JSON sanitization regex | Gemini really hallucinates bad numbers | `sanitize_gemini_json()` |
| Brace-counting JSON parse | Gemini adds text before/after JSON | `_parse_llm_response()` |
| Retry loop for JSON errors | Gemini occasionally fails to output valid JSON | `_run_llm_phase()` |
| Manual markdown stripping | Gemini wraps JSON in markdown sometimes | `_parse_llm_response()` |

### 4.2 Debt Being Paid Down

| Debt Item | V0.6 Problem | V1.0 Solution |
|-----------|--------------|---------------|
| LLM-based pricing | Prices could be hallucinated | Code-based lookup (Phase 2) |
| Single review phase | Limited improvement opportunity | Dedicated peer review (Phase 3) |
| Mixed audience output | One format for all users | ELI5 + Architect Report (Phase 7, 8) |

### 4.3 New Debt Being Accepted (Consciously)

| Debt Item | Why Accepting | Future Fix |
|-----------|---------------|------------|
| FFE lookup incomplete | FFE database needs enhancement | Enhance FFE lookup |
| No caching layer | First implementation | Add Redis/file caching later |

---

## Part 5: Testing Strategy

### 5.1 Unit Tests Required

```python
# test_multi_phase_estimator_v1.py

def test_sanitize_gemini_json():
    """Test decimal truncation."""
    bad = '{"price": 32.000000000000000000001}'
    good = sanitize_gemini_json(bad)
    assert json.loads(good)["price"] == 32.0

def test_phase_2_pricing():
    """Test code-based price lookup."""
    items = [{"bcca_code": "09ACE00130", "quantity": 10}]
    result = estimator._run_phase_2_pricing(items)
    assert result[0]["unit_price"] > 0
    assert result[0]["line_total"] == result[0]["quantity"] * result[0]["unit_price"]

def test_items_preserved():
    """Test no item loss between phases."""
    # Should raise SchemaContinuityError if items lost
    pass
```

### 5.2 Integration Tests Required

```python
async def test_full_pipeline():
    """Test complete 8-phase pipeline."""
    estimator = MultiPhaseEstimatorV1()
    result = await estimator.estimate(
        target_pir=MOCK_TARGET_PIR,
        bracket_pir=MOCK_BRACKET_PIR,
        ...
    )
    assert result["line_items_count"] > 0
    assert result["final_total_with_iva"] > 0
```

---

## Part 6: Migration Checklist

### Step 1.5: Run Database Migration ⏳ BEFORE ORCHESTRATOR

**Migration File:** `supabase/migrations/011_v1_pipeline_schema.sql`

**Schema Document:** `docs/V1_SCHEMA_SPECIFICATION.md`

**Pre-Migration Checks:**
- [ ] Backup existing `smart_m2` data
- [ ] No active pipeline runs in progress

**Run Migration:**
```bash
cd lean-mvp
npx supabase db push
```

**Verify Tables Created:**
- [ ] `unified_estimates_v1` — All 8-phase outputs
- [ ] `viewing_checklists_v1` — Phase 6 output
- [ ] `eli5_summaries_v1` — Phase 7 output
- [ ] `architect_reports_v1` — Phase 8 output

**Verify Columns Added:**
- [ ] `smart_m2.dimension_methodology`
- [ ] `smart_m2.schema_version`

**Verify Checkpoint Constraint Updated:**
- [ ] New checkpoints: `smart_m2_complete`, `phase_1_scope_boq_complete`, etc.

**Test Helper Functions:**
```sql
SELECT get_v1_estimate(123, 'fair_market');
SELECT is_v1_pipeline_complete(123);
```

### Step 2: Create `multi_phase_estimator_v1.py`

**Core Implementation:**
- [ ] Copy class structure from V0.6
- [ ] Update imports to use V1.0 prompts/schemas
- [ ] Implement `_run_phase_2_pricing()` (code-based)
- [ ] Add knowledge graph loading to context builder
- [ ] Update phase definitions for 8 phases
- [ ] Preserve ALL error handling
- [ ] Preserve ALL JSON sanitization
- [ ] Preserve ALL retry logic
- [ ] Add Phase 5 method (Gemini 2.5 Flash Image, 16:9 — existing approach)
- [ ] Add Phase 7 method (ELI5)
- [ ] Add Phase 8 method (Architect Report)

**CRITICAL: Async Checkpointing (MUST preserve):**
- [ ] `_save_checkpoint()` method — saves to `package_generation_progress` table
- [ ] `checkpoints_completed: List[str]` — tracks completed phases
- [ ] Resume from checkpoint — skip phases already completed
- [ ] Each phase saves checkpoint IMMEDIATELY after completion
- [ ] Checkpoint includes phase output data for debugging

**V1.0 Checkpoint Flow:**
```python
# After Phase 1 completes:
await self._save_checkpoint(listing_id, "phase_1_scope_boq_complete", phase_1_output)

# After Phase 2 completes (code):
await self._save_checkpoint(listing_id, "phase_2_pricing_complete", phase_2_output)

# After Phase 3 completes:
await self._save_checkpoint(listing_id, "phase_3_peer_review_complete", phase_3_output)

# ... etc for all 8 phases
```

**CRITICAL: Foreground Logging (MUST preserve):**
- [ ] `_log_step()` method — log major phases with banner
- [ ] Real-time progress logging at INFO level
- [ ] Phase timing logged on completion
- [ ] Item counts logged after each phase
- [ ] Cost totals logged after pricing phases
- [ ] All logging uses `logger.info()` (not print)

**Logging Pattern to Preserve:**
```python
logger.info("=" * 70)
logger.info("  PHASE 1: SCOPE + BOQ (Pro)")
logger.info("=" * 70)

# ... phase execution ...

logger.info(f"  ✓ Phase 1: {len(items)} items created, {total_weeks} weeks")
logger.info(f"  💾 CHECKPOINT: phase_1_scope_boq_complete")
```

**Testing Requirements:**
- [ ] ALL tests run with foreground logging (no timeout)
- [ ] Test with `logging.basicConfig(level=logging.INFO)`
- [ ] Capture full logs on failure for debugging
- [ ] No silent failures — all errors logged before raise

**CRITICAL: Fail Loud and Fast:**
- [ ] NO try/except that swallows errors
- [ ] NO graceful degradation that hides problems
- [ ] NO fallback values when data is missing
- [ ] ALL validation errors raise immediately with context
- [ ] ALL Gemini errors raise with full response text
- [ ] ALL JSON parse errors raise with raw response

**Error Pattern (REQUIRED):**
```python
# CORRECT: Fail loud with context
if not items:
    raise PhaseError(
        phase_number=1,
        phase_name="scope_boq",
        message="Phase 1 produced 0 items. This is a critical failure.",
        context={"prompt_length": len(prompt), "response_length": len(response.text)}
    )

# WRONG: Silent fallback
if not items:
    logger.warning("No items, using empty list")
    items = []  # NEVER DO THIS
```

**CRITICAL: No Legacy Support:**
- [ ] NO imports from deprecated V0.5/V0.6 files
- [ ] NO backward compatibility code paths
- [ ] NO "if old_format" checks
- [ ] NO migration code in production paths
- [ ] Clean implementation — V1.0 only

### Step 2.5: Update `db_helpers.py` for V1.0 Tables

**New Methods Required:**
- [ ] `save_unified_estimate_v1()` — Save to unified_estimates_v1
- [ ] `get_unified_estimate_v1()` — Retrieve estimate
- [ ] `save_viewing_checklist_v1()` — Save Phase 6 output
- [ ] `save_eli5_summary_v1()` — Save Phase 7 output  
- [ ] `save_architect_report_v1()` — Save Phase 8 output
- [ ] Update `save_smart_m2()` to include new columns

### Step 3: Update `package_orchestrator.py`

- [ ] Update import to V1.0 estimator
- [ ] Update checkpoint names to use V1.0 checkpoints
- [ ] Update method calls for new phase structure
- [ ] Add calls to save V1 outputs to new tables
- [ ] Test end-to-end with real listing

### Step 4: Delete Deprecated Files

- [ ] Verify all tests pass with V1.0
- [ ] Delete `multi_phase_estimator.py`
- [ ] Delete `multi_phase_estimator_v2.py`
- [ ] Delete `phase_prompts.py`
- [ ] Delete `phase_prompts_v2.py`
- [ ] Delete `schemas/gemini_schemas.py`
- [ ] Delete `schemas/gemini_schemas_v2.py`
- [ ] Delete `schemas/phase_outputs.py`
- [ ] Update any remaining imports

---

## Part 7: Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `multi_phase_estimator_v1.py` | V1.0 8-phase orchestrator |
| `tests/test_estimator_v1.py` | Unit and integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `package_orchestrator.py` | Update import to V1.0 |
| `schemas/__init__.py` | Export V1.0 schemas |

### Files to Keep (NOT deprecated)

| File | Reason |
|------|--------|
| `bcca_price_lookup.py` | Used by Phase 2 |
| `pir_generator.py` | Used by orchestrator |
| `image_cache.py` | Used by visual phases |
| `schemas/estimation_error.py` | Error types |
| `schemas/unified_estimate.py` | Output types |

---

## Part 8: Testing Strategy — LISTING 12

### ⚠️ CRITICAL: Data Preservation Rules

**USE LISTING 12 FOR ALL V1.0 TESTING.**

Before running V1.0 pipeline, you must reset Listing 12's data. BUT:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🚨 NEVER DELETE CLUSTERING DATA 🚨                                          ║
║                                                                               ║
║   Clustering is EXPENSIVE (time + API calls).                                 ║
║   The clustering pipeline is STABLE and WORKING.                              ║
║   Re-clustering wastes time and money for NO benefit.                         ║
║                                                                               ║
║   PRESERVE:                                                                   ║
║   - photo_clusters_v048 (target clusters)                                     ║
║   - comparable photo clusters                                                 ║
║   - comparables data                                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### What TO Delete (V1.0 Test Reset)

| Table | Delete for Listing 12? | Reason |
|-------|------------------------|--------|
| `unified_estimates_v1` | ✅ YES | V1.0 output — regenerate |
| `unified_estimates_v048` | ✅ YES | Old V0.6 output |
| `viewing_checklists_v1` | ✅ YES | V1.0 Phase 6 output |
| `eli5_summaries_v1` | ✅ YES | V1.0 Phase 7 output |
| `architect_reports_v1` | ✅ YES | V1.0 Phase 8 output |
| `property_intelligence_reports_v048` (target only) | ✅ YES | Regenerate target PIR |
| `package_generation_progress` | ✅ YES | Reset checkpoints |
| `smart_m2` | ✅ YES | Regenerate with new schema |

### What to NEVER Delete

| Table | Delete? | Reason |
|-------|---------|--------|
| `photo_clusters_v048` | ❌ **NEVER** | Clustering is expensive and stable |
| `listing_photos` | ❌ **NEVER** | Source photos |
| `listings` | ❌ **NEVER** | Core listing data |
| `comparables` | ❌ **NEVER** | Comparable listings |
| `comparable_image_cache` | ❌ **NEVER** | Cached comparable images |
| `property_intelligence_reports_v048` (comparables) | ❌ **NEVER** | Comparable PIRs |

### Reset Script for Listing 12

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- V1.0 TEST RESET FOR LISTING 12
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- This script PRESERVES clustering and comparables.
-- Run this BEFORE each V1.0 test run.
--
-- ═══════════════════════════════════════════════════════════════════════════

-- Delete V1.0 outputs
DELETE FROM unified_estimates_v1 WHERE listing_id = 12;
DELETE FROM viewing_checklists_v1 WHERE listing_id = 12;
DELETE FROM eli5_summaries_v1 WHERE listing_id = 12;
DELETE FROM architect_reports_v1 WHERE listing_id = 12;

-- Delete V0.6 outputs (old pipeline)
DELETE FROM unified_estimates_v048 WHERE listing_id = 12;

-- Delete TARGET PIR only (keep comparable PIRs)
DELETE FROM property_intelligence_reports_v048 
WHERE listing_id = 12 AND pir_type = 'target';

-- Delete bracket PIRs and strategic reasoning (will regenerate)
DELETE FROM property_intelligence_reports_v048 
WHERE listing_id = 12 AND pir_type LIKE 'bracket_%';
DELETE FROM property_intelligence_reports_v048 
WHERE listing_id = 12 AND pir_type LIKE 'strategic_%';

-- Reset checkpoints
DELETE FROM package_generation_progress WHERE listing_id = 12;

-- Delete smart_m2 (will regenerate with new schema)
DELETE FROM smart_m2 WHERE listing_id = 12;

-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFICATION: These should NOT be empty after reset
-- ═══════════════════════════════════════════════════════════════════════════

-- Should return rows (clustering data preserved):
SELECT COUNT(*) AS cluster_count FROM photo_clusters_v048 WHERE listing_id = 12;

-- Should return rows (comparables preserved):
SELECT COUNT(*) AS comparable_pir_count FROM property_intelligence_reports_v048 
WHERE listing_id = 12 AND pir_type = 'comparable';

-- ═══════════════════════════════════════════════════════════════════════════
-- DONE - Ready for V1.0 test run
-- ═══════════════════════════════════════════════════════════════════════════
```

### Python Reset Function

```python
async def reset_listing_12_for_v1_test(db: Database):
    """
    Reset Listing 12 for V1.0 testing.
    
    ⚠️ PRESERVES: clustering data, comparables, comparable PIRs
    ⚠️ DELETES: estimates, target PIR, checkpoints, smart_m2
    """
    listing_id = 12
    
    logger.info("=" * 70)
    logger.info("  RESETTING LISTING 12 FOR V1.0 TEST")
    logger.info("=" * 70)
    
    # Delete V1.0 outputs
    await db.execute("DELETE FROM unified_estimates_v1 WHERE listing_id = $1", listing_id)
    await db.execute("DELETE FROM viewing_checklists_v1 WHERE listing_id = $1", listing_id)
    await db.execute("DELETE FROM eli5_summaries_v1 WHERE listing_id = $1", listing_id)
    await db.execute("DELETE FROM architect_reports_v1 WHERE listing_id = $1", listing_id)
    logger.info("  ✓ Deleted V1.0 outputs")
    
    # Delete V0.6 outputs
    await db.execute("DELETE FROM unified_estimates_v048 WHERE listing_id = $1", listing_id)
    logger.info("  ✓ Deleted V0.6 outputs")
    
    # Delete TARGET PIR only (PRESERVE comparable PIRs)
    await db.execute("""
        DELETE FROM property_intelligence_reports_v048 
        WHERE listing_id = $1 AND pir_type IN ('target', 'bracket_fast_sell', 
            'bracket_fair_market', 'bracket_out_of_market',
            'strategic_reasoning_fast_sell', 'strategic_reasoning_fair_market',
            'strategic_reasoning_out_of_market')
    """, listing_id)
    logger.info("  ✓ Deleted target PIR and bracket data (comparable PIRs PRESERVED)")
    
    # Reset checkpoints
    await db.execute("DELETE FROM package_generation_progress WHERE listing_id = $1", listing_id)
    logger.info("  ✓ Reset checkpoints")
    
    # Delete smart_m2
    await db.execute("DELETE FROM smart_m2 WHERE listing_id = $1", listing_id)
    logger.info("  ✓ Deleted smart_m2")
    
    # Verify clustering preserved
    cluster_count = await db.fetchval(
        "SELECT COUNT(*) FROM photo_clusters_v048 WHERE listing_id = $1", listing_id
    )
    if cluster_count == 0:
        raise RuntimeError("❌ CRITICAL: Clustering data was deleted! This should NEVER happen!")
    logger.info(f"  ✓ Verified: {cluster_count} clusters PRESERVED")
    
    # Verify comparable PIRs preserved
    comp_pir_count = await db.fetchval("""
        SELECT COUNT(*) FROM property_intelligence_reports_v048 
        WHERE listing_id = $1 AND pir_type = 'comparable'
    """, listing_id)
    logger.info(f"  ✓ Verified: {comp_pir_count} comparable PIRs PRESERVED")
    
    logger.info("=" * 70)
    logger.info("  RESET COMPLETE - Ready for V1.0 test")
    logger.info("=" * 70)
```

### Test Run Command

```bash
# 1. Reset Listing 12 (preserves clustering)
python -c "
import asyncio
from backend.database import Database
from backend.pricing.test_utils import reset_listing_12_for_v1_test

async def main():
    db = Database()
    await reset_listing_12_for_v1_test(db)

asyncio.run(main())
"

# 2. Run V1.0 pipeline with full logging
python -c "
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from backend.database import Database
from backend.pricing.multi_phase_estimator_v1 import MultiPhaseEstimatorV1
from backend.pricing.package_orchestrator import PackageOrchestrator

async def main():
    db = Database()
    orchestrator = PackageOrchestrator(db=db)
    
    result = await orchestrator.generate_packages(
        listing_id=12,
        package_types=['fair_market'],  # Start with one package
        force_restart=False,  # Use checkpoints
    )
    
    print(f'Success: {result[\"success\"]}')
    print(f'Checkpoints: {result[\"checkpoints\"]}')

asyncio.run(main())
"
```

---

## Part 9: Fail Loud and Fast (NON-NEGOTIABLE)

### Philosophy

**Every failure must be visible, immediate, and informative.**

The worst kind of bug is a silent one. If Phase 1 produces garbage, we want
to know NOW — not discover it in Phase 8 when the architect report is wrong.

### What "Fail Loud" Means

1. **Log the error with full context BEFORE raising**
2. **Include relevant data in the exception**
3. **Never swallow exceptions**
4. **Never use fallback values that hide problems**

### What "Fail Fast" Means

1. **Validate inputs at the START of each phase**
2. **Check outputs IMMEDIATELY after each phase**
3. **Don't continue if prerequisites are invalid**
4. **Raise on first error, don't accumulate**

### Required Validation Points

| Phase | Input Validation | Output Validation |
|-------|------------------|-------------------|
| 1 | PIRs exist, canonical rooms exist | items.length > 0, all items have bcca_code |
| 2 | items from Phase 1 exist | all items have unit_price and line_total |
| 3 | priced items exist | sanity_check_passed, total > 0 |
| 4 | scope items exist, photos exist | prompts for each room |
| 5 | prompts exist | image URLs generated |
| 6 | PIR exists, scope exists | checklist has all 3 modes |
| 7 | all previous outputs exist | rooms array populated |
| 8 | all previous outputs exist | by_trade array populated |

### Anti-Patterns (FORBIDDEN)

```python
# ❌ FORBIDDEN: Silent fallback
def get_items(self):
    try:
        return self._fetch_items()
    except Exception:
        return []  # NEVER DO THIS

# ❌ FORBIDDEN: Graceful degradation
if not bcca_code:
    bcca_code = "UNKNOWN"  # NEVER DO THIS
    
# ❌ FORBIDDEN: Swallowing errors
try:
    result = await call_gemini(...)
except Exception as e:
    logger.warning(f"Gemini failed: {e}")
    # continues anyway... NEVER DO THIS

# ❌ FORBIDDEN: Optional validation
if validate:  # NEVER MAKE VALIDATION OPTIONAL
    check_items(items)
```

### Required Patterns (MANDATORY)

```python
# ✅ REQUIRED: Validate and fail immediately
def validate_phase_1_output(output: Dict) -> None:
    """Validate Phase 1 output. Raises on any issue."""
    items = output.get("items", [])
    
    if not items:
        raise PhaseError(
            phase_number=1,
            phase_name="scope_boq",
            message="Phase 1 produced 0 items",
        )
    
    for item in items:
        if not item.get("bcca_code"):
            raise PhaseError(
                phase_number=1,
                phase_name="scope_boq",
                message=f"Item {item.get('item_id')} missing bcca_code",
                context={"item": item}
            )

# ✅ REQUIRED: Log before raising
async def _run_phase(self, phase_num: int, ...):
    try:
        response = await call_gemini(...)
    except Exception as e:
        logger.error(f"Phase {phase_num} Gemini call failed: {e}")
        logger.error(f"Prompt length: {len(prompt)}")
        raise GeminiError(
            phase_name=phase_config["name"],
            model=phase_config["model"],
            error_message=str(e),
        )
    
    if not response.success:
        logger.error(f"Phase {phase_num} returned error: {response.error}")
        logger.error(f"Response text (first 500): {response.text[:500]}")
        raise GeminiError(...)

# ✅ REQUIRED: Validate between phases
phase_1_output = await self._run_phase_1(...)
validate_phase_1_output(phase_1_output)  # ALWAYS validate
await self._save_checkpoint(...)

phase_2_output = self._run_phase_2_pricing(phase_1_output["items"])
validate_phase_2_output(phase_2_output)  # ALWAYS validate
await self._save_checkpoint(...)
```

---

## Part 10: Cached Context Requirements (CRITICAL)

### Philosophy

**Every LLM phase receives the FULL cached context.**

The cached context is built ONCE at the start and reused across all phases.
This is critical for:
- Cost optimization (context caching)
- Consistency (all phases see same data)
- Completeness (no missing information)

### What MUST Be in Cached Context

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     CACHED CONTEXT REQUIREMENTS                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  1. BCCA INDEX (FULL)                                                         ║
║     - File: data/bcca_index.txt (~12,565 items)                              ║
║     - Format: CODE|DESCRIPTION|PRICE                                          ║
║     - Contains composite prices (labor + materials + overhead)                ║
║     - CRITICAL for Phase 1 BCCA code selection                               ║
║                                                                               ║
║  2. FFE INDEX (FULL)                                                          ║
║     - File: data/ffe_index.txt (~207 items)                                  ║
║     - Format: CODE|NAME|DESCRIPTION|BUDGET_LOW|MID|HIGH|UNIT|CATEGORY        ║
║     - CRITICAL for furniture/fixture selection                                ║
║                                                                               ║
║  3. KNOWLEDGE GRAPHS (ALL THREE)                                              ║
║     - energy_knowledge.json (~25KB) - Energy efficiency, CTE compliance       ║
║     - renovation_process_knowledge.json (~15KB) - Construction sequences      ║
║     - interior_design_knowledge.json (~113KB) - Design standards              ║
║     - CRITICAL for reasoning about scope and dependencies                     ║
║                                                                               ║
║  4. TARGET PIR (Full JSON)                                                    ║
║     - Property Intelligence Report for the target property                    ║
║     - Room-by-room condition analysis                                         ║
║     - With SMART M² dimensions if available                                   ║
║                                                                               ║
║  5. BRACKET PIR (Full JSON)                                                   ║
║     - What properties at this price bracket look like                         ║
║     - Materials, finishes, style expectations                                 ║
║                                                                               ║
║  6. STRATEGIC REASONING (All Fields)                                          ║
║     - structural_realities                                                    ║
║     - inherent_advantages                                                     ║
║     - bracket_alignment_analysis                                              ║
║     - impossibilities                                                         ║
║     - opportunity_zones                                                       ║
║     - strategic_direction                                                     ║
║     - scoper_guidance                                                         ║
║                                                                               ║
║  7. LISTING DATA (Full JSON)                                                  ║
║     - Price, area, bedrooms, bathrooms                                        ║
║     - Location, year built                                                    ║
║     - Description                                                             ║
║                                                                               ║
║  8. CANONICAL ROOM IDS                                                        ║
║     - List of room_id → room_name mappings                                   ║
║     - From clustering (NEVER regenerate)                                      ║
║                                                                               ║
║  9. PHASE SYSTEM INSTRUCTION                                                  ║
║     - Unified item schema                                                     ║
║     - Key principles                                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Context Building Implementation

```python
async def _build_cached_context(
    self,
    target_pir: Dict[str, Any],
    bracket_pir: Dict[str, Any],
    strategic_reasoning: Dict[str, Any],
    listing_data: Dict[str, Any],
    package_type: str,
    smart_m2_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the FULL cached context for all phases.
    
    This is called ONCE at the start and reused for Phases 1, 3, 4, 6, 7, 8.
    """
    # Load ALL indexes
    bcca_index = self._load_file("bcca_index.txt")  # ~12,565 items
    ffe_index = self._load_file("ffe_index.txt")    # ~207 items
    
    # Load ALL knowledge graphs
    energy_kg = self._load_json("energy_knowledge.json")
    process_kg = self._load_json("renovation_process_knowledge.json")
    design_kg = self._load_json("interior_design_knowledge.json")
    
    # Build canonical rooms section
    rooms_section = self._build_canonical_rooms_section(self.canonical_room_ids)
    
    # Build smart m² section if available
    smart_m2_section = ""
    if smart_m2_data:
        smart_m2_section = self._build_smart_m2_section(smart_m2_data)
    
    context = f"""
═══════════════════════════════════════════════════════════════════════════════
V1.0 UNIFIED ESTIMATOR - 8-PHASE PIPELINE
═══════════════════════════════════════════════════════════════════════════════

{PHASE_SYSTEM_INSTRUCTION}

PACKAGE TYPE: {package_type.upper()}

{rooms_section}
{smart_m2_section}
═══════════════════════════════════════════════════════════════════════════════
BRACKET PIR - What This Price Bracket "Looks Like"
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(bracket_pir, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
🔴 STRATEGIC REASONING LAYER - PRE-SCOPE BRIEF (MANDATORY READING) 🔴
═══════════════════════════════════════════════════════════════════════════════

{strategic_reasoning.get('strategic_summary', 'Not available')}

STRUCTURAL REALITIES:
{strategic_reasoning.get('structural_realities', 'Not available')}

INHERENT ADVANTAGES:
{strategic_reasoning.get('inherent_advantages', 'Not available')}

BRACKET ALIGNMENT:
{strategic_reasoning.get('bracket_alignment_analysis', 'Not available')}

IMPOSSIBILITIES:
{strategic_reasoning.get('impossibilities', 'Not available')}

OPPORTUNITY ZONES:
{strategic_reasoning.get('opportunity_zones', 'Not available')}

STRATEGIC DIRECTION:
{strategic_reasoning.get('strategic_direction', 'Not available')}

SCOPER GUIDANCE:
{strategic_reasoning.get('scoper_guidance', 'Not available')}

═══════════════════════════════════════════════════════════════════════════════
TARGET PROPERTY - Current State
═══════════════════════════════════════════════════════════════════════════════

LISTING DATA:
{json.dumps(listing_data, indent=2, ensure_ascii=False)}

PROPERTY INTELLIGENCE REPORT (PIR):
{json.dumps(target_pir, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: ENERGY EFFICIENCY
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(energy_kg, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: RENOVATION PROCESS
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(process_kg, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: INTERIOR DESIGN
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(design_kg, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
BCCA INDEX - {len(bcca_index.splitlines()):,} SPANISH CONSTRUCTION ITEMS
Format: CODE|DESCRIPTION|PRICE (composite: labor + materials + overhead)
═══════════════════════════════════════════════════════════════════════════════

{bcca_index}

═══════════════════════════════════════════════════════════════════════════════
FFE INDEX - FURNITURE, FIXTURES & EQUIPMENT
Format: CODE|NAME|DESCRIPTION|BUDGET_LOW|BUDGET_MID|BUDGET_HIGH|UNIT|CATEGORY
═══════════════════════════════════════════════════════════════════════════════

{ffe_index}
"""
    
    return context
```

### Token Budget

| Component | Estimated Tokens |
|-----------|------------------|
| BCCA Index | ~328,000 |
| FFE Index | ~11,000 |
| Energy KG | ~8,000 |
| Process KG | ~5,000 |
| Design KG | ~38,000 |
| Target PIR | ~10,000 |
| Bracket PIR | ~5,000 |
| Strategic Reasoning | ~3,000 |
| System Instruction | ~2,000 |
| **TOTAL** | **~410,000** |

This fits well within Gemini's 1M token context window.

### BCCA Composite Prices Note

The BCCA prices are **composite prices** that include:
- Labor (man-hours × hourly rate)
- Materials
- Overhead
- Small equipment

They do NOT separately list man-hours. For time estimation, Phase 1
must estimate `duration_hours` based on:
- Standard productivity rates from renovation_process_knowledge.json
- The quantity and complexity of the work
- Dependencies between items

This is why the Knowledge Graphs are critical — they contain the
reasoning context for time estimation that the BCCA prices alone don't provide.

---

## Part 11: No Legacy Support (CLEAN BREAK)

### Philosophy

**V1.0 is a clean implementation. No backward compatibility baggage.**

The deprecated V0.5/V0.6 files exist for reference only. V1.0 does not
import from them, does not support their data formats, and does not
provide migration paths in production code.

### Forbidden Imports

```python
# ❌ FORBIDDEN: Importing from deprecated files
from .phase_prompts import ...      # DEPRECATED
from .phase_prompts_v2 import ...   # DEPRECATED
from .multi_phase_estimator import ...      # DEPRECATED
from .multi_phase_estimator_v2 import ...   # DEPRECATED
from .schemas.gemini_schemas import ...     # DEPRECATED
from .schemas.gemini_schemas_v2 import ...  # DEPRECATED
```

### Allowed Imports

```python
# ✅ ALLOWED: V1.0 files only
from .phase_prompts_v1 import PHASE_PROMPTS, PHASE_SYSTEM_INSTRUCTION
from .schemas.gemini_schemas_v1 import (
    PHASE_1_SCHEMA, PHASE_3_SCHEMA, PHASE_4_SCHEMA,
    PHASE_6_SCHEMA, PHASE_7_SCHEMA, PHASE_8_SCHEMA,
    get_schema_for_phase_v1
)

# ✅ ALLOWED: Shared utilities (not deprecated)
from .bcca_price_lookup import BCCAPriceLookup
from .schemas.estimation_error import PhaseError, GeminiError
```

### No Format Detection

```python
# ❌ FORBIDDEN: Detecting old formats
if "v05_schema_continuity" in estimate:
    # old format handling... NEVER DO THIS

# ❌ FORBIDDEN: Migration in production path
if schema_version == "v0.5":
    data = migrate_to_v1(data)  # NEVER DO THIS
```

### Data Expectations

V1.0 expects V1.0 data. Period.

If old data exists in the database:
1. Run migration scripts BEFORE using V1.0
2. Or delete old data and regenerate
3. Or use `force_restart=True` to ignore old checkpoints

```python
# ✅ CORRECT: Fail if data format is wrong
estimate = await self.db.get_unified_estimate_v1(listing_id, package_type)
if not estimate:
    raise DataMissingError(
        data_type="v1_estimate",
        listing_id=listing_id,
        message="No V1.0 estimate found. Run V1.0 pipeline first."
    )
```

---

## APPENDIX A: Checkpointing Architecture (CRITICAL)

### Why Checkpointing Matters

LLM phases are expensive (time and money). If Phase 6 fails, we don't want to
re-run Phases 1-5. Checkpointing enables "close and come back" architecture.

### Current V0.6 Implementation (MUST preserve)

```python
class PackageOrchestrator:
    def __init__(self):
        self.checkpoints_completed: List[str] = []
    
    async def _save_checkpoint(self, listing_id: int, checkpoint_name: str):
        """Save checkpoint to database."""
        if checkpoint_name not in self.checkpoints_completed:
            self.checkpoints_completed.append(checkpoint_name)
        
        await self.db.save_package_checkpoint(
            listing_id=listing_id,
            checkpoint=checkpoint_name,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"  💾 CHECKPOINT: {checkpoint_name}")
```

### V1.0 Checkpoint Strategy

| Phase | Checkpoint Name | Saved Data |
|-------|-----------------|------------|
| M1 | `smart_m2_complete` | Room dimensions |
| 1 | `phase_1_scope_boq_complete` | Items with BCCA codes |
| 2 | `phase_2_pricing_complete` | Priced items |
| 3 | `phase_3_peer_review_complete` | Adjusted items + totals |
| 4 | `phase_4_prompts_complete` | Rendering prompts |
| 5 | `phase_5_images_complete` | Generated image URLs |
| 6 | `phase_6_checklist_complete` | Viewing checklist |
| 7 | `phase_7_eli5_complete` | ELI5 summaries |
| 8 | `phase_8_report_complete` | Architect report |
| Final | `v1_pipeline_complete` | All done |

### Resume Logic Pattern

```python
async def estimate(self, listing_id: int, ...):
    # Load existing checkpoints
    existing = await self.db.get_package_checkpoints(listing_id)
    self.checkpoints_completed = existing or []
    
    # Phase 1 (skip if checkpoint exists)
    if "phase_1_scope_boq_complete" not in self.checkpoints_completed:
        phase_1_output = await self._run_phase_1(...)
        await self._save_checkpoint(listing_id, "phase_1_scope_boq_complete")
    else:
        logger.info("  ✓ Phase 1 checkpoint found - loading from DB")
        phase_1_output = await self.db.get_phase_output(listing_id, 1)
    
    # Phase 2 (skip if checkpoint exists)
    if "phase_2_pricing_complete" not in self.checkpoints_completed:
        phase_2_output = self._run_phase_2_pricing(phase_1_output["items"])
        await self._save_checkpoint(listing_id, "phase_2_pricing_complete")
    else:
        logger.info("  ✓ Phase 2 checkpoint found - loading from DB")
        phase_2_output = await self.db.get_phase_output(listing_id, 2)
    
    # ... etc for all phases
```

### Fail Fast on Missing Data

```python
if "phase_1_scope_boq_complete" in self.checkpoints_completed:
    phase_1_output = await self.db.get_phase_output(listing_id, 1)
    if not phase_1_output:
        raise DataMissingError(
            data_type="phase_1_output",
            listing_id=listing_id,
            message="Phase 1 checkpoint exists but data not found. "
                    "Run with force_restart=True to regenerate."
        )
```

---

## APPENDIX B: Foreground Logging Requirements

### Why Foreground Logging Matters

LLM phases can take 30-120 seconds each. Without real-time logging:
- No visibility into progress
- Timeouts kill long-running phases
- Debugging failures is impossible

### Logging Pattern (MUST implement)

```python
import logging
logger = logging.getLogger(__name__)

class MultiPhaseEstimatorV1:
    def _log_phase_start(self, phase_num: int, phase_name: str):
        """Log phase start with banner."""
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"  PHASE {phase_num}: {phase_name}")
        logger.info("=" * 70)
    
    def _log_phase_complete(self, phase_num: int, duration: float, **metrics):
        """Log phase completion with metrics."""
        logger.info(f"  ✓ Phase {phase_num} complete in {duration:.1f}s")
        for key, value in metrics.items():
            logger.info(f"     {key}: {value}")
        logger.info(f"  💾 CHECKPOINT: phase_{phase_num}_*_complete")
```

### Testing Configuration

```python
# test_estimator_v1.py

import logging

# CRITICAL: Enable foreground logging for all tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.mark.asyncio
async def test_full_pipeline():
    """Test with NO timeout — LLM phases are slow."""
    estimator = MultiPhaseEstimatorV1()
    
    # No timeout wrapper — let it run to completion
    result = await estimator.estimate(
        listing_id=123,
        ...
    )
    
    # All logs visible in pytest output with -s flag
    assert result["phases_completed"] == 8
```

### Running Tests with Logs

```bash
# CORRECT: Full foreground logs, no timeout
pytest test_estimator_v1.py -s -v --tb=long

# WRONG: Will timeout and hide issues
pytest test_estimator_v1.py --timeout=30
```

---

## APPENDIX C: Smart M² Integration

### Overview

Room dimensions are CRITICAL for Phase 1 (Scope + BoQ) quantity calculations.
Without knowing that a room is "6.3m × 4.0m", quantity formulas become guesswork.

### Pipeline Position

```
Clustering (P1) → Smart M² (M1) → PIR Generation → Phase 1 (Scope + BoQ)
```

Smart M² runs AFTER clustering (needs room list) but BEFORE PIR generation
(PIR needs dimensions for rich descriptions).

### What Smart M² Produces

For each room:
- `estimated_m2`: Total floor area
- `estimated_dimensions`: `{length_m, width_m, aspect_ratio}`
- `wall_descriptions`: Named walls with dimensions
  - `name`: "long_wall", "window_wall", "entrance_wall"
  - `name_es`: "pared larga", "pared con ventana", "pared de entrada"
  - `length_m`: Wall dimension
  - `features`: ["windows", "door", "countertop"]
- `estimated_height_m`: Ceiling height
- `perimeter_m`: 2 × (length + width)
- `wall_area_m2`: perimeter × height (approx)

### PIR Integration

The PIR generator receives `smart_m2_data` as an optional parameter.
When available (always for target listings, never for comparables), the
PIR prompt includes:

```
### DIMENSIONES ESTIMADAS POR HABITACIÓN (SI DISPONIBLES)

**Salón**: ~25m² (6.3m × 4.0m), altura 2.7m
  - pared larga: 6.3m (windows)
  - pared corta: 4.0m (entrance)
  - pared del fondo: 4.0m

IMPORTANTE: En tu visual_narrative, referencia estas dimensiones...
```

### Phase 1 Usage

Phase 1 prompts are updated to:
1. Explain that dimensions are available in the PIR (if available)
2. Show how to use them in quantity formulas
3. Provide fallback guidance when dimensions aren't available

Example quantity_formula with dimensions:
```json
{
  "quantity": 25.2,
  "quantity_formula": "6.3m × 4.0m = 25.2m² floor",
  "unit": "m2"
}
```

### Files Modified

| File | Change |
|------|--------|
| `pipeline/steps/smart_m2.py` | Enhanced to produce wall dimensions |
| `pricing/pir_generator.py` | Accepts and integrates smart_m2_data |
| `pricing/phase_prompts_v1.py` | Phase 1 references PIR dimensions |

### Why Comparables Don't Get Dimensions

1. **Cost**: Running smart m² for every comparable adds API calls
2. **Necessity**: Comparables inform style/quality, not quantities
3. **Consistency**: Phase 1 only calculates quantities for TARGET property

The prompts say "if available" so the same code works for both target and
comparable PIRs without separate logic.

---

**Document Version:** 1.1.0  
**Next Action:** Implement Step 2 (create `multi_phase_estimator_v1.py`)
