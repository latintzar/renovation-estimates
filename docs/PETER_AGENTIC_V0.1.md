Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.1: Knowledge-Augmented Reasoning Architecture

> **Date**: January 2026  
> **Author**: Peter Neyra + Claude  
> **Status**: Initial Thinking / Architecture Design

---

## The Problem We're Solving

Renovation costing pipelines fail in predictable ways:

1. **Lost Context**: Gap analysis says "renovar baño" but by BCCA matching, we've lost the room, intent, and scope
2. **Incomplete Task Discovery**: "Retile bathroom" should expand to 20+ tasks, but we only find 2
3. **Wrong Matches**: Semantic search finds items that *mention* the work, not items that *do* the work (tests vs installation)
4. **No Self-Correction**: Each phase is blind to the next; errors compound

Traditional solutions:
- **Keyword filters**: `if 'ensayo' in desc: skip` → Brittle, grows forever
- **Hardcoded rules**: `BATHROOM_TASKS = [...]` → Doesn't generalize
- **More LLM calls**: ReAct agents with 20-30 tool calls → Expensive, slow

**None of these use the architecture we built.**

---

## The Insight

We built a Knowledge Graph (KG) with 683 tasks and 2,789 edges (`requires`, `triggers`) specifically to encode renovation knowledge.

But we're using it wrong.

### Wrong: KG as Tool
```
LLM: "What tasks for bathroom?"
  → Tool call → KG query → Returns 2 tasks
LLM: "OK, price these"
  → Tool call → BCCA search → Returns wrong items
LLM: "Done" (with garbage estimate)
```

The LLM is **discovering** knowledge that the KG already contains. Each tool call is a chance to lose context.

### Right: KG as Context
```
Prompt: "Here is the COMPLETE bathroom renovation tree from the KG:
         [20+ tasks with dependencies, quantities, trades]
         
         Here is the gap analysis:
         [what the property actually needs]
         
         Here are the relevant BCCA items:
         [installation items, not tests]
         
         Produce the BoQ."

LLM: Reasons once with full picture → Correct estimate
```

The KG **augments** the LLM's reasoning. It's not a database to query; it's knowledge to reason with.

---

## The Architecture: Knowledge-Augmented Single-Pass

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   GAP ANALYSIS OUTPUT                                       │
│   "Baño: cápsula del tiempo años 70, instalación           │
│    eléctrica peligrosa, necesita plato de ducha..."        │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   KG RETRIEVAL (Deterministic, Fast, No LLM)               │
│                                                             │
│   1. Detect room types: [Baño, Cocina, ...]                │
│   2. For each room, retrieve the FULL task subtree:        │
│                                                             │
│      TASK_renovacion_integral_baño                         │
│       ├── requires: TASK_demolicion_revestimientos         │
│       │    └── triggers: TASK_gestion_escombros            │
│       ├── requires: TASK_impermeabilizacion                │
│       ├── triggers: TASK_alicatado_ceramico                │
│       │    └── requires: TASK_enfoscado                    │
│       ├── triggers: TASK_solado_antideslizante             │
│       ├── triggers: TASK_instalacion_sanitarios            │
│       │    ├── requires: TASK_fontaneria_desague           │
│       │    └── requires: TASK_fontaneria_agua              │
│       ├── triggers: TASK_griferia                          │
│       ├── triggers: TASK_mampara_ducha                     │
│       └── triggers: TASK_instalacion_electrica_baño        │
│                                                             │
│   3. Extract trades from tasks: [fontanería, albañilería]  │
│   4. Retrieve relevant BCCA items (exclude chapter 18)     │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   SINGLE LLM CALL: Full-Context Reasoning                  │
│                                                             │
│   CONTEXT BLOCK 1: Gap Analysis                            │
│   [Original room-by-room descriptions and needs]           │
│                                                             │
│   CONTEXT BLOCK 2: KG Task Trees                           │
│   [Complete subtrees for each room type]                   │
│   [Each task with: quantity_formula, trade, layer]         │
│                                                             │
│   CONTEXT BLOCK 3: BCCA Reference                          │
│   [Relevant items with prices and units]                   │
│   [Explicit note: chapter 18 = tests, don't use]           │
│                                                             │
│   CONTEXT BLOCK 4: Room Dimensions                         │
│   [From Smart M2: area, height, perimeter per room]        │
│                                                             │
│   INSTRUCTION:                                              │
│   "The KG shows EXACTLY what each room renovation needs.   │
│    Include ALL tasks from the relevant subtrees.           │
│    Match to INSTALLATION items, not tests.                 │
│    Show reasoning chain for each line item."               │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   OUTPUT: Complete BoQ with Audit Trail                    │
│                                                             │
│   {                                                         │
│     "room": "Baño",                                        │
│     "task": "Alicatado cerámico",                          │
│     "reasoning": [                                          │
│       "Gap says 'renovar acabados' for bathroom",          │
│       "KG: bathroom renovation triggers alicatado",        │
│       "KG: alicatado requires enfoscado (included)",       │
│       "Quantity: 18m² (walls) from room dimensions",       │
│       "BCCA: 01RAT00010 @ €35/m² (installation item)"      │
│     ],                                                      │
│     "bcca_code": "01RAT00010",                             │
│     "quantity": 18,                                         │
│     "unit": "m²",                                          │
│     "total": 630                                            │
│   }                                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Why This Works

### 1. Completeness is Guaranteed

The LLM can't "forget" to include tasks because the complete task tree is in the prompt. The KG tells it: "Here's what bathroom renovation means - ALL of this."

### 2. Context is Never Lost

Room attribution, intent, dimensions - everything flows together in one reasoning pass. No "telephone game" between phases.

### 3. BCCA Matching is Intent-Aware

The LLM sees both:
- The task with its intent (install sanitarios)
- The BCCA options (installation vs test items)

It can reason about matching, not just do semantic similarity.

### 4. Audit Trail is Natural

The LLM produces reasoning chains as part of its output. We don't need to bolt on logging - the explanation IS the output.

### 5. Cost is Bounded

| Approach | LLM Calls | Context Size |
|----------|-----------|--------------|
| ReAct Agent | 20-30 | Small per call |
| This Architecture | 1-2 | Large but single |

One large call is cheaper than many small calls, and more reliable.

---

## Comparison: Three Approaches

### Scenario: First attempt has issues (common case)

**Option A: Structured Pipeline**
```
Gap → [string] → Resolver → [task IDs] → BCCA → BoQ
         ↓
   Each phase only sees its input
   Context lost at every handoff
   No recovery mechanism
         ↓
   €53 for bathroom (wrong, stuck with it)
```

**Option B: Full Agentic (ReAct)**
```
Agent: "Estimate bathroom"
Tool call → KG → "Got 2 tasks"
Agent: "Seems incomplete..."
Tool call → KG → "Got 20 tasks"
Agent: "Now price them"
Tool call × 20 → BCCA → some wrong
Agent: "€650/unit is suspicious..."
Tool call → verify → retry
... 25-30 calls later ...
         ↓
   Correct estimate, but expensive and slow
```

**Option C: Knowledge-Augmented Single Pass**
```
KG retrieval: Full bathroom subtree (deterministic)
BCCA retrieval: Relevant items (deterministic)
         ↓
Single LLM call with COMPLETE context
         ↓
LLM reasons once with full picture
Can't miss tasks (they're in the prompt)
Can't match to tests (context says not to)
         ↓
   Correct estimate, fast, cheap
```

---

## The Role of Each Component

### Knowledge Graph (KG)
- **NOT**: A database to query during reasoning
- **IS**: A knowledge augmentation layer that ensures completeness

The KG answers: "If you're doing X, here's EVERYTHING that entails."

### LLM (Gemini)
- **NOT**: An agent that discovers knowledge through tool calls
- **IS**: A reasoner that synthesizes pre-loaded knowledge

The LLM answers: "Given all this knowledge, here's the correct estimate."

### BCCA Database
- **NOT**: A semantic search target
- **IS**: A reference table loaded into context

The BCCA provides: "Here are the real items with real prices to choose from."

---

## Implementation Sketch

```python
async def estimate_renovation_v1(gap_analysis: GapAnalysisResult) -> BoQ:
    """
    PETER AGENTIC V0.1: Knowledge-Augmented Single-Pass Estimation
    """
    
    # =========================================================
    # PHASE 1: Deterministic Knowledge Retrieval (No LLM)
    # =========================================================
    
    # 1a. Identify rooms from gap analysis
    rooms = extract_rooms(gap_analysis)  # ["Baño", "Cocina"]
    
    # 1b. Retrieve KG subtrees for each room type
    kg_context = ""
    for room in rooms:
        root_task = KG_ROOM_ROOTS.get(normalize(room))
        subtree = kg.expand_full_tree(root_task, max_depth=6)
        kg_context += format_subtree(room, subtree)
    
    # 1c. Extract trades from KG tasks
    trades = extract_trades(kg_context)  # ["fontanería", "albañilería"]
    
    # 1d. Retrieve relevant BCCA items (exclude tests)
    bcca_context = bcca.get_items_for_trades(
        trades, 
        exclude_chapters=['18'],  # Quality control
        exclude_keywords=['ensayo', 'prueba']
    )
    
    # 1e. Get room dimensions
    dimensions = format_dimensions(gap_analysis.room_sizes)
    
    # =========================================================
    # PHASE 2: Single LLM Call with Full Context
    # =========================================================
    
    prompt = f"""
# Renovation Estimate Task

## Gap Analysis (What the property needs)
{format_gap_analysis(gap_analysis)}

## Knowledge Graph (What each renovation type requires)
{kg_context}

## BCCA Reference (Available items for pricing)
{bcca_context}

## Room Dimensions
{dimensions}

## Instructions

You are producing a Bill of Quantities (BoQ) for this renovation.

For each room in the gap analysis:
1. Look at the KG subtree for that room type
2. Include ALL tasks from the subtree (the KG defines what's needed)
3. Calculate quantities using the room dimensions
4. Match each task to a BCCA item that INSTALLS/DOES the work (not tests)
5. Attribute each line item to the correct room

Output JSON with this structure for each line item:
{{
  "room": "room name from gap analysis",
  "task_name": "from KG",
  "task_id": "KG task ID",
  "reasoning_chain": ["step 1", "step 2", ...],
  "bcca_code": "matched BCCA code",
  "bcca_description": "what it is",
  "quantity": number,
  "unit": "m²/ud/ml",
  "unit_price": number,
  "total": number
}}

IMPORTANT:
- Chapter 18 BCCA items are TESTS, not work. Never use them.
- The KG subtree shows EVERYTHING needed - don't skip tasks.
- Each task needs a reasoning chain explaining WHY it's included.
"""
    
    response = await gemini.generate(
        prompt,
        model="gemini-2.5-pro",
        response_mime_type="application/json"
    )
    
    return parse_boq(response)
```

---

## What This Architecture Enables

### 1. Explainable AI (Built-in)
Every line item has a reasoning chain. Customers can ask "why €630 for tiling?" and get:
- "Your gap analysis mentioned renovating bathroom finishes"
- "The KG shows bathroom renovation requires alicatado"
- "Your bathroom is 4.5m² with 2.4m walls = 18m² of wall area"
- "BCCA 01RAT00010 is ceramic wall tiling at €35/m²"

### 2. Customer Feedback Loop
If customer says "that's too expensive", we can:
- Show which tasks contribute most
- Explain WHY each is included (KG dependency)
- Adjust scope (remove optional tasks)

### 3. Architect Handoff
The reasoning chain becomes the technical specification:
- Each task traced to KG definition
- Each price traced to BCCA code
- Each quantity traced to room dimensions

### 4. Continuous Improvement
When estimates are wrong:
- Check if KG subtree is complete → Add missing edges
- Check if BCCA match is correct → Improve retrieval
- Check if quantities are right → Adjust formulas

No need to add keyword filters or hardcoded rules.

---

## Open Questions for V0.2

1. **Context window limits**: What if KG subtrees + BCCA items exceed context? 
   - Solution: Smarter retrieval, only relevant items

2. **Variant selection**: KG has multiple options (e.g., plato ducha vs bañera)
   - Solution: Gap analysis should specify, or LLM chooses based on context

3. **Multi-property batching**: Can we estimate multiple properties in one call?
   - Solution: Probably not - keep it simple

4. **Validation pass**: Should we add a second LLM call to sanity-check?
   - Solution: Maybe, but the full-context approach should minimize errors

---

## Summary

**PETER AGENTIC V0.1** is not an agent that calls tools.

It's an architecture where:
- **KG** = Knowledge augmentation (completeness)
- **BCCA** = Reference augmentation (pricing)
- **LLM** = Single-pass reasoner (synthesis)
- **Context** = Everything the LLM needs in one prompt

The result: Accurate estimates with built-in explainability, at the cost of one LLM call.

---

## Next Steps

1. Implement KG retrieval layer (`retrieve_kg_context()`)
2. Implement BCCA retrieval layer (`retrieve_bcca_context()`)
3. Design the prompt template
4. Test on listing 12 (the problematic case)
5. Compare: V0.1 vs current pipeline

---

*"The best agent is no agent - just a well-informed reasoner."*

