Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC: Architecture Decision Record

> **Date**: January 2026  
> **Decision**: V0.3 Hybrid (KG Context + BCCA RAG)  
> **Status**: APPROVED

---

## The Question

**How should we provide construction knowledge to the LLM for cost estimation?**

We have two data sources:
1. **Knowledge Graph (KG)**: 683 tasks with dependency relationships (~120K tokens)
2. **BCCA Price Book**: 12,565 construction items with prices (~500K+ tokens)

---

## Options Considered

### Option A: Pure RAG (Both via Tools)

```
LLM → Tool: search_kg(query) → Tool: search_bcca(query) → Answer
```

**Pros:**
- Small context size (~10K tokens)
- Simple caching

**Cons:**
- ❌ Cannot reason about KG dependencies
- ❌ Each query is isolated
- ❌ Loses relationship traversal capability

**Verdict:** REJECTED - KG needs full visibility for dependency reasoning

---

### Option B: Pure Context (Both in System Instruction)

```
System Instruction = KG (~120K) + BCCA (~500K) + Rules
LLM reads everything → Answer
```

**Pros:**
- Single LLM call
- Full visibility

**Cons:**
- ❌ BCCA too large (500K+ tokens)
- ❌ Must filter BCCA to fit (lose items)
- ❌ Ch.18 filtering relies on prompt (unreliable)

**Verdict:** REJECTED - BCCA doesn't fit, and filtering loses accuracy

---

### Option C: Hybrid (KG Context + BCCA RAG) ✅ SELECTED

```
System Instruction = KG (~120K) + BCCA-Speak Guide (~5K) + Rules
LLM reasons with KG → Tool: search_bcca(query) → Validated Answer
```

**Pros:**
- ✅ Full KG visibility (can traverse dependencies)
- ✅ Access to ALL 12K BCCA items (not filtered)
- ✅ Ch.18 exclusion in code (100% reliable)
- ✅ Reasonable context size (~130K)
- ✅ Tool calls provide audit trail

**Cons:**
- More complex (tool calling loop)
- Multiple LLM calls per estimate

**Verdict:** APPROVED - Best of both worlds

---

## The Key Insight

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   KG = REASONING                BCCA = RETRIEVAL               │
│                                                                │
│   Must see whole graph          Just need best match           │
│   to traverse edges             from 12K items                 │
│                                                                │
│   "What work is needed?"        "What does it cost?"           │
│                                                                │
│   → CONTEXT                     → RAG TOOL                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Don't confuse reasoning problems with retrieval problems.**

---

## What's in the System Instruction (Cached)

| Component | Tokens | Purpose |
|-----------|--------|---------|
| Role + Rules | ~3K | Grounding, no hallucination |
| **Full KG YAML** | ~120K | Dependency reasoning |
| BCCA-Speak Guide | ~5K | How to search effectively |
| Quantity Formulas | ~2K | Calculate from dimensions |
| **Total** | **~130K** | 13% of 1M limit |

---

## What's in the RAG Tool (NOT in Context)

| Component | Items | Tokens (if in context) |
|-----------|-------|------------------------|
| BCCA Items | 12,565 | ~500K+ |

**Accessed via:** `search_bcca(keyword, chapter, intent)`

**Data:** Tests/inspections excluded at database load time (clean data)

---

## BCCA-Speak: Teaching the LLM to Search

The LLM doesn't have BCCA items in context, so we teach it:

1. **Chapter Index**: What each chapter covers
2. **Query Construction**: Spanish terminology
3. **Intent Keywords**: installation vs demolition
4. **Price Ranges**: Sanity check expectations

Example translations in system instruction:

| What LLM Wants | Search Query |
|----------------|--------------|
| "Install tiles" | `search_bcca("alicatado cerámico", "01", "installation")` |
| "Install toilet" | `search_bcca("inodoro porcelana", "08", "installation")` |
| "Demolish floor" | `search_bcca("levantado solado", "01", "demolition")` |

---

## Why Not SQL?

We considered teaching the LLM to write SQL:

```sql
SELECT * FROM bcca_items 
WHERE description LIKE '%alicatado%' 
AND chapter = '01'
```

**Problems:**
- LLM must know exact schema
- Syntax errors break queries
- Less forgiving than semantic search

**RAG is better:**
- Natural language input
- Hybrid BM25 + embeddings
- More robust to terminology variation

---

## Success Metrics

After implementing V0.3:

| Metric | Target | Why |
|--------|--------|-----|
| Tests in results | 0 | Excluded at load |
| All tasks have BCCA | 100% | Process grounding |
| Room attribution | <30% "General" | Context preserved |
| Reasoning chains | Every line | Explainable AI |
| Latency | <30s | Acceptable UX |

---

## CRITICAL: No Fallbacks

**V1 produces garbage** (€53 bathrooms, test items instead of work, wrong room attribution).

**We NEVER fall back to V1.** Either V0.3 succeeds with validated results OR we fail clearly with an error.

```
┌─────────────────────────────────────────────────────────────┐
│  FAIL-FAST PRINCIPLE                                        │
│                                                             │
│  V0.3 fails validation → Return CLEAR ERROR                 │
│                                                             │
│  ❌ NOT: Fall back to V1 (returns garbage)                  │
│  ❌ NOT: Return partial/invalid result                      │
│  ✅ YES: Fail clearly with actionable error                 │
│                                                             │
│  Why? Returning garbage that looks like success is          │
│  WORSE than failing. Users trust wrong numbers.             │
│  We can't debug failures we don't see.                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Order

1. **BCCA Search Tool** - BM25 + embeddings hybrid
2. **Price Validation Tool** - Sanity checks
3. **System Instruction V0.3** - KG + BCCA-speak
4. **EstimatorV3 Class** - Tool calling loop
5. **API Integration** - /estimate-v3 endpoint
6. **Testing** - Listing 12 bathroom test

---

## References

- `PETER_AGENTIC_V0.1.md` - Initial "KG as Context" concept
- `PETER_AGENTIC_V0.2_IMPLEMENTATION.md` - Pure context attempt
- `PETER_AGENTIC_V0.3_HYBRID_IMPLEMENTATION.md` - Full spec

---

*Architecture Decision Record*
*Approved: January 2026*

