# Phase Prompt Requirements - What Each Phase Needs to Know

This document defines what information each phase needs. The prompts should communicate this to an intelligent reasoning model - not dumb it down, not over-explain, just give it the information it needs to do the job.

---

## PHASE 1: SCOPE DEFINITION

### Goal
Create the complete scope of work that transforms property from TARGET state to BRACKET state.

### What it needs to know

**Context:**
- TARGET PIR: Current property condition (from photos + listing data)
- BRACKET PIR: What properties at this price point look like (synthesized from comparables)
- CANONICAL ROOM IDS: The exact room identifiers from photo clustering (must use these)
- BCCA INDEX: Spanish construction price book for chapter classification

**Task Understanding:**
- Output becomes a contractor's work order - each item is a discrete task they'll price and execute
- Granularity: each physical action is its own item (don't consolidate "bathroom renovation" into one item)
- Every demolition needs corresponding installation
- Every installation needs preparation (waterproofing before tiles, primer before paint)
- Hardware, accessories, finishing steps are separate items

**Example of Proper Granularity:**
```
Bathroom full renovation = ~15-25 items:
- Remove floor tiles, Remove wall tiles, Remove toilet, Remove vanity, Remove mirror
- Remove lighting, Disconnect plumbing
- Prep substrate (floor), Prep substrate (walls)
- Waterproof floor, Waterproof walls (wet zone)
- Install floor tiles, Install wall tiles
- Grout floor, Grout walls, Seal grout
- Install toilet, Install vanity, Install sink+faucet, Install mirror
- Install lighting, Install ventilation
- Final plumbing connections, Test fixtures
```

**Output Schema:**
- items[]: array of scope items with item_id, room_id, name, description, system, bcca_chapter
- rooms_coverage: summary of coverage per room

---

## PHASE 2: SCOPE VERIFICATION

### Goal
Review Phase 1 output and add any missing items to ensure completeness.

### What it needs to know

**Rules:**
- Can ADD items, cannot REMOVE items
- Item IDs continue from Phase 1's max (if Phase 1 ended at ITEM_087, start at ITEM_088)

**What to verify:**
1. Every canonical room_id has at least one item
2. Every demolition has corresponding installation
3. Every surface installation has proper prep (waterproofing, primer)
4. Finishing items included (grout, sealant, hardware, cover plates)
5. Site logistics (protection, debris removal, cleanup)
6. Required certifications (boletines for electrical, gas)

**Output Schema:**
- items_to_add[]: new items to add
- verification_notes: what was checked
- all_rooms_covered: boolean

---

## PHASE 3: SCHEDULING

### Goal
Fill scheduling fields for ALL items: phase_week, depends_on, duration_hours

### What it needs to know

**Physical constraints:**
- Waterproofing: 48h cure before tiling
- Plaster: 2 weeks dry before painting
- Rough-in (electrical, plumbing): BEFORE closing walls
- Cabinets: BEFORE countertops
- Countertops: BEFORE appliance fit-out

**Typical sequence:**
- Week 1: Site setup, protection, demolition start
- Week 2-3: Demolition complete, rough-in (MEP)
- Week 4-5: Carpentry, structural, waterproofing
- Week 6-7: Finishes (tile, plaster, paint)
- Week 8-9: Second fix (fixtures, appliances)
- Week 10: Final finishes, cleanup, handover

**Rules:**
- MUST return ALL items from input (cannot lose any)
- Count input items, count output items, must match

**Output Schema:**
- items[]: all items with scheduling fields filled
- phase_breakdown: summary by week

---

## PHASE 4: LOGISTICS CHECK

### Goal
Review scheduled BOQ, add missing logistics items, fix sequencing issues.

### What it needs to know

**Logistics to verify:**
- Floor/surface protection
- Dust barriers if needed
- Skip hire for debris
- Scaffolding if high work
- Permits (building, comunidad)
- Inspections (pre-cover electrical, plumbing pressure test)
- Interim cleanup
- Final deep clean

**Rules:**
- Can ADD items, cannot REMOVE items
- New items must have scheduling fields filled
- Can flag sequencing issues and propose fixes

**Output Schema:**
- items_to_add[]: new logistics items
- sequencing_fixes[]: {item_id, old_week, new_week, reason}
- permits_needed, inspections_needed

---

## PHASE 5: PRICING

### Goal
Fill pricing fields for ALL items by reading from BCCA/FFE index in context.

### What it needs to know

**BCCA Index format:**
```
CODE|DESCRIPTION|PRICE
09ACE00130|Alicatado azulejo 30x30 gres porcel...|32.00
```
- Prices are in EUR, include labor + materials + overhead
- Unit is implicit in description (m2, ud, ml)

**FFE Index format:**
```
CODE|NAME|DESC|BUDGET_LOW|BUDGET_MID|BUDGET_HIGH|UNIT|CATEGORY
FFE_BATH_ENC_001|Mampara Ducha|...|150|220|300|ud|BATHROOM_FFE
```
- Use BUDGET_LOW for fast_sell, BUDGET_MID for fair_market, BUDGET_HIGH for out_of_market

**Task:**
1. Find matching code in index for each item
2. Read unit_price from index (don't invent prices)
3. Estimate quantity from TARGET PIR dimensions
4. Calculate line_total = quantity × unit_price

**Rules:**
- MUST price ALL items (no nulls)
- If no exact match, find closest and note adaptation

**Output Schema:**
- items[]: all items with bcca_code, unit, quantity, quantity_formula, unit_price, line_total
- subtotals_by_system, total_before_adjustments

---

## PHASE 6: ADJUSTMENTS

### Goal
Apply regional and complexity adjustments to all items.

### What it needs to know

**BCCA base:** Andalucía pricing. Adjustments needed for other regions.

**Regional multipliers:**
- Barcelona centro: +15-20%
- Madrid centro: +10-15%
- Valencia: +0-5%
- Other capitals: variable

**Access factors:**
- No lift + high floor: +5-10%
- Narrow street: +5%
- Restricted work hours: +10%

**Building factors:**
- Heritage listed: +15-20%
- Pre-1900: +10-15%

**Task:**
For each item: adjusted_price = line_total × price_multiplier

**Output Schema:**
- items[]: all items with price_multiplier, adjusted_price, adjustment_reason
- total_after_adjustments
- iva_rate (0.21), iva_amount, final_total_with_iva

---

## PHASES 7-9: VALIDATION

Validation phases checking timeline feasibility, energy compliance, and overall sanity.
These don't modify items, they verify the estimate makes sense.

---

## PHASE 10: RENDERING PROMPTS

Generate AI image transformation prompts for each room based on scope.
Uses bracket PIR for finish guidance.

---

## PHASE 11: VIEWING GUIDE

Generate 20-minute property viewing checklist.
Three modes: sensory, inspection, questions for agent.

---

## PRINCIPLES FOR PROMPT WRITING

1. **Treat it as intelligent** - It's a flagship reasoning model. Give it the information, it will figure out what to do.

2. **Be comprehensive** - Don't leave out details thinking "it'll figure it out." Include everything relevant.

3. **Don't be negative** - No "don't do X" or "avoid Y." State what you want, not what you don't want.

4. **Show examples** - One good example is worth 100 words of explanation.

5. **Be specific about output** - It needs to know exactly what schema to produce.

6. **Trust the context** - The PIRs, indexes, and previous outputs are in context. Reference them, don't repeat them.
