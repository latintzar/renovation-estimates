Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V1.0 Pipeline Prompts
## Complete Phase Prompts - Reasoning-Focused Design

**Companion to:** PIPELINE_V1_ARCHITECTURE.md

---

## Prompt Design Philosophy

### The Core Principle

These prompts are NOT instruction manuals. They're **reasoning guides**.

Traditional prompts say: "Do X, then Y, then Z, output format W."

Our prompts say: "Here's WHY this task matters. Here's what each piece of 
context tells you and WHY you have it. Here's what to think deeply about. 
Here's what to doubt and question."

The difference is profound. An instruction-following model produces 
mechanical output. A reasoning model produces thoughtful output that 
adapts to the specific situation.

---

## The Seven Principles (Applied to ALL Phases)

### 1. Explain WHY (In Extreme Detail)

Every section starts with WHY IT MATTERS, not just WHAT to do.

**Example from Phase 1:**
```
═══════════════════════════════════════════════════════════════════════════════
WHY THIS TASK MATTERS
═══════════════════════════════════════════════════════════════════════════════

This is the foundation of everything that follows. Every later phase — 
pricing, review, visualization, buyer communication — depends on the 
quality of thinking you do here.
```

**Example from Phase 4:**
```
WHY THIS MATTERS: A buyer will see "before" and "after" images side by 
side. These images are often the first thing they look at — before reading 
any text. The visual story determines whether they engage further or 
scroll past.
```

### 2. Intelligent Peer (Gemini as Colleague)

We don't talk down to the model. We treat it as a senior professional.

**Example from Phase 3:**
```
You're not a validator who stamps "approved" or "rejected." That's useless. 
You're an intelligent peer who IMPROVES the work before it goes out.

Imagine you're the senior partner at an architecture firm. A junior 
architect has prepared this estimate. Before it leaves the office with 
your firm's name on it, you're going to make it bulletproof.
```

### 3. Examples in Prose (Not Standalone Templates)

Examples are woven into explanations conversationally, never presented 
as templates with arbitrary numbers.

**Bad approach:**
```
Week 1: Site setup
Week 2-3: Demolition  
Week 4: Waterproofing
Cost range: €900-1,400/m²
```

This looks like a template to copy.

**Our approach:**
```
Don't be rigid about week numbers — every project is different based on 
size, complexity, and site conditions. But do be rigorous about dependencies.

Light renovations typically fall in the lower end of renovation costs per 
square meter. Standard full renovations are in the middle range. High-
quality renovations push higher.
```

The prose framing makes clear these are general guidance, not precise 
templates.

### 4. Questions Guide Reasoning

Instead of checklists, we use questions that prompt thinking.

**Bad approach:**
```
[ ] Check waterproofing exists
[ ] Verify cure times respected
```

**Our approach:**
```
As you read each room's items, ask: "If I were building this, what would 
I need that isn't listed here?"
```

Questions trigger reasoning. Checklists trigger ticking boxes.

### 5. Goal Before Task

Every prompt establishes role, context, and WHY IT MATTERS before diving 
into instructions.

**Example from Phase 7:**
```
You are explaining a renovation estimate to someone who is smart but has 
never renovated a property, and who is slightly skeptical of AI-generated 
content.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS TASK MATTERS
═══════════════════════════════════════════════════════════════════════════════

The detailed estimate is full of BCCA codes, technical terms, and 
construction jargon. That's necessary for contractors — but it's 
incomprehensible to a typical buyer.

Your job is to translate the estimate into plain language...
```

### 6. Reasoning Over Checklists

We guide WHAT to think about, not WHAT to check off.

**Example:**
```
**WHAT TO DOUBT AND QUESTION**

WHY THIS MATTERS: Self-doubt is how professionals catch their own mistakes. 
Before finishing, challenge yourself:

- "Have I actually looked at every room in the canonical list?"
- "Does my scope match the bracket, not exceed it?"
- "Would a contractor reading this be able to build from it?"
```

These are self-reflection prompts, not compliance checks.

### 7. No Rigid Templates

Examples are illustrative, not prescriptive.

**Example:**
```
For floor areas: length times width. But think about the actual space — 
is it rectangular or irregular? Are there built-in elements reducing the 
area?
```

This teaches the CONCEPT while acknowledging each situation differs.

---

## How Each Piece of Context Should Be Read

Every prompt now includes explicit guidance for EACH piece of context:
- **WHY YOU HAVE THIS**: Why this context was provided
- **HOW TO READ IT**: What questions to ask while reading
- **WHAT TO THINK DEEPLY ABOUT**: The non-obvious reasoning required

### Example from Phase 1:

```
**TARGET PIR (Property Intelligence Report)**

WHY YOU HAVE THIS: This describes the property AS IT EXISTS TODAY. Without 
this, you'd be guessing what needs work. With it, you can see through the 
eyes of someone who has walked through every room and examined every surface.

HOW TO READ IT: As you read each room's description, ask yourself:
- What's the underlying condition versus the cosmetic appearance?
- Is this something that needs complete replacement, or just refreshing?
- What does the age and wear pattern tell me about what's behind the walls?
- Are there red flags that suggest hidden problems?

WHAT TO THINK DEEPLY ABOUT: If the PIR mentions "yellowed grout in the 
bathroom," don't just think "replace grout." Ask: why is it yellowed? 
Usually that means moisture has been getting behind the tiles for years, 
which means the waterproofing has probably failed, which means you can't 
just re-tile — you need to strip back and re-waterproof properly.
```

---

## What to Doubt and Question

Every phase now has an explicit "WHAT TO DOUBT AND QUESTION" section that 
triggers self-reflection:

### Phase 1 (Scope + BOQ)
```
- "Have I actually looked at every room in the canonical list?"
- "Does my scope match the bracket, not exceed it?"
- "Have I included the preparation work, not just the finish work?"
- "Are my BCCA codes real codes from the index, or did I make them up?"
- "Would a contractor reading this be able to build from it?"
```

### Phase 3 (Peer Review)
```
- "Has every room been covered, or were some forgotten?"
- "Are there preparation steps missing before finish work?"
- "Does the schedule respect chemical cure times?"
- "Is the cost per square meter reasonable for this scope?"
- "Does the energy pathway add up?"
```

### Phase 4 (Rendering Prompts)

**Critical: Every prompt must include boilerplate instructions for the image 
generation model.** The image model has no concept of "renovation" vs 
"reconstruction" — it will move walls or add windows if the prompt is ambiguous.

The boilerplate explicitly constrains:
- Camera angle: PERFECTLY identical to reference image
- Structural elements: walls, doors, windows, floors, ceilings — DO NOT MODIFY
- Surfaces/materials: these ARE what should change
- Openings: do not add, remove, or resize unless explicitly told

The key distinction is: **Change surfaces, not structures. Change what's ON 
the walls, floors, and ceilings — not WHERE they are.**

```
- "Does my prompt reflect the ACTUAL scope, not generic improvements?"
- "Have I specified materials that match the BRACKET level?"
- "Did I include the boilerplate about camera angle and structural preservation?"
- "Am I changing surfaces/materials or accidentally implying structural changes?"
- "Is my hero room choice the most dramatic transformation?"
```

### Phase 6 (Viewing Checklist)
```
- "Is each check specific to THIS property, not generic?"
- "Can a non-expert actually do this check?"
- "Have I covered the concerns raised in the TARGET PIR?"
- "Does the total fit in about twenty minutes?"
```

### Phase 7 (ELI5 Summaries)
```
- "Would a skeptical friend trust this explanation?"
- "Am I being specific or hiding behind vague words?"
- "Does this sound too polished and therefore suspicious?"
- "Have I used jargon anywhere?"
```

### Phase 8 (Architect Report)
```
- "Have I organized items correctly by BCCA chapter (trade)?"
- "Can a contractor find all their trade's work in one section?"
- "Does the timeline show dependencies, not just durations?"
- "Would an architect reviewing this find anything missing?"
```

---

## Avoiding Fixed Numbers as Examples

### The Problem

If a prompt says "Week 1: demolition, Week 2-3: MEP, €900-1,400/m²," the 
model might treat those specific numbers as correct answers rather than 
illustrative examples.

### The Solution

Describe concepts conversationally, acknowledging that specifics vary.

**Bad:**
```
**TYPICAL RENOVATION FLOW:**
- Week 1: Site setup
- Week 2-3: Demolition
- Week 4: Waterproofing
```

**Good:**
```
The renovation flows in waves: demolition clears the space, rough-in MEP 
claims it, finishes cover everything, then second-fix completes the details.

Don't be rigid about week numbers — every project is different based on 
size, complexity, and site conditions. But do be rigorous about dependencies.
```

**For costs:**

**Bad:**
```
€/m² Benchmarks:
- €600-900/m² = light renovation
- €900-1,400/m² = standard renovation
```

**Good:**
```
Light renovations typically fall in the lower end of renovation costs per 
square meter. Standard full renovations are in the middle range. High-
quality renovations push higher. Above that usually means luxury finishes 
or unusual scope.

Does the estimate fall within a reasonable range for what's being done? 
If not, why? Maybe there's a good reason — or maybe there's an error.
```

---

## Principle Compliance Checklist (for Each Phase)

| Principle | P1 | P3 | P4 | P6 | P7 | P8 |
|-----------|----|----|----|----|----|----|
| WHY THIS TASK MATTERS section | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HOW TO READ CONTEXT (with WHY) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WHAT TO THINK DEEPLY ABOUT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WHAT TO DOUBT AND QUESTION | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No fixed numbers as templates | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Questions over checklists | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Role + context before task | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

**Document Version:** 1.1.0  
**Updated:** January 2026 — Full principle compliance across all phases
