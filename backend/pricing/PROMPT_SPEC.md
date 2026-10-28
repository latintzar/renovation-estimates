# Prompt Specification Document

This document specifies EVERYTHING each phase needs to know. Each prompt will be written from this spec.

---

## PHILOSOPHY

**Why multi-phase?**

We split the estimation into phases because a single LLM call cannot reason deeply enough about all aspects simultaneously. Each phase focuses on one type of thinking, examines all context deeply, and produces high-quality output. Later phases then examine that output, reason about it, and build on it.

**What the prompts do:**

The prompts guide REASONING, not mechanical execution. They ask questions that force the model to think. They explain WHY context matters. They don't provide checklists to tick off - they provide reasoning frameworks.

**What the prompts don't change:**

The OUTPUT SCHEMA for each phase is fixed. The prompts make the model reason better about HOW to fill the schema, but the schema itself doesn't change. Phase 1 outputs items with scope fields. Phase 3 adds scheduling fields. Phase 5 adds pricing fields. This is immutable.

**Schema continuity:**

All phases work with the same underlying item structure. Fields are ADDED as phases progress, never removed:

```
Phase 1-2 creates: item_id, room_id, room_name, name, description, system, bcca_chapter, comparable_reference
Phase 3-4 adds:    phase_week, depends_on, duration_hours  
Phase 5 adds:      bcca_code, ffe_code, unit, quantity, quantity_formula, unit_price, line_total
Phase 6 adds:      price_multiplier, adjusted_price, adjustment_reason
```

Items flow through ALL phases. Item count can only increase (Phases 2 and 4 can add), never decrease.

---

## CONTEXT AVAILABLE TO ALL PHASES

Every phase has access to this context (passed in system instruction):

### 1. TARGET PIR (Property Intelligence Report)

The detailed analysis of the property as it exists today. Contains:

- **building_profile**: Year built, construction era, building type, floor level, total floors, energy rating
- **rooms**: Array of room analyses, each with:
  - room_id (canonical identifier from clustering)
  - room_type (cocina, dormitorio, baño, etc.)
  - condition_summary (text description of current state)
  - key_issues (array of problems identified)
- **design_profile**: 
  - dominant_style (when was this last renovated, what era does it feel like)
  - finish_quality_overall (assessment of current finish level)
  - color_palette, material_summary
- **triggers**: Array of renovation triggers identified, each with:
  - category (electrical, plumbing, structural, cosmetic, regulatory)
  - trigger (what needs attention)
  - urgency (critical, high, medium, low)
  - evidence (what in the photos showed this)

**WHY IT MATTERS:**
- Room dimensions for quantity calculations
- Condition tells you scope (cosmetic refresh vs structural intervention)
- Triggers are the REASONS items exist in the scope
- Building age affects regulatory requirements and hidden problems
- Floor level affects access logistics
- Energy rating affects what improvements might be required

### 2. BRACKET PIR (Synthesized from Comparables)

What properties at this price point look like when renovated. Contains:

- **bracket_name**: fast_sell / fair_market / out_of_market
- **design_era**: When were these typically renovated (2015-2020 modern, etc.)
- **finish_level_summary**: Text describing the expected finish quality
- **what_defines_this_bracket**: How it differs from cheaper/more expensive
- **common_materials**: 
  - flooring (what buyers expect to see)
  - walls, kitchen, bathroom materials
- **typical_features**: Array of features common in this bracket
- **price_range_min/max**: The price band this bracket represents

**WHY IT MATTERS:**
- This is the TARGET STATE - what the renovation should achieve
- Material choices should match bracket expectations
- Features should match (don't over-spec, don't under-spec)
- Understanding what defines the bracket helps make trade-off decisions

### 3. LISTING DATA

Raw data from the property listing:

- Price, area (m²), bedrooms, bathrooms
- Location/address
- Description text
- Photo URLs

**WHY IT MATTERS:**
- Area for calculating quantities
- Location for regional price adjustments
- Description may mention features not visible in photos

### 4. CANONICAL ROOM IDS

The exact room identifiers from photo clustering:

```
- room_id: "cocina" → Cocina
- room_id: "dormitorio_1" → Dormitorio Principal
- room_id: "bano_1" → Baño Principal
- room_id: "salon" → Salón-Comedor
...
```

**WHY IT MATTERS:**
- These are the ONLY valid room_ids
- Every item must belong to a canonical room or "general"
- Consistency across all phases

### 5. BCCA INDEX (~12,500 items)

Spanish construction price database. Format: `CODE|DESCRIPTION|PRICE`

Example: `09ACE00130|Alicatado azulejo 30x30 gres porcelánico rectificado...|32.00`

**WHY IT MATTERS:**
- Prices are COMPOSITE (labor + materials + overhead included)
- Base prices are Andalucía rates (need regional adjustment)
- Code structure: first 2 digits = chapter (09 = revestimientos)
- Unit is implicit in description (m², ud, ml, kg)

### 6. FFE INDEX (~200 items)

Furniture, fixtures & equipment. Format: `CODE|NAME|DESC|BUDGET_LOW|MID|HIGH|UNIT|CATEGORY`

**WHY IT MATTERS:**
- Three price tiers for different packages
- fast_sell → BUDGET_LOW
- fair_market → BUDGET_MID
- out_of_market → BUDGET_HIGH

---

## PHASE 1: SCOPE DEFINITION

### Role
**Senior Architect** - A professional with deep experience in residential renovation who understands design, materials, spatial relationships, building systems, construction sequences, and - crucially - how the gap between a property's current state and its target state translates into discrete pieces of work. The architect doesn't think in abstractions like "renovate bathroom" but in concrete actions like "remove floor tiles, remove wall tiles, remove toilet, remove vanity..."

### Context to Examine (in depth)

Phase 1 creates the scope from scratch. You have no prior phase outputs to review - you ARE the first phase. Your job is to examine the source context deeply and produce a complete bill of quantities.

---

#### EXAMINE: LISTING DATA - The Property in Context

Start with the basic listing information:

**Price and area establish the investment context.** A €400,000 apartment of 90m² in Barcelona is very different from a €150,000 apartment of 90m² in a small town. The price tells you what market you're in. The area (m²) will drive quantity calculations throughout the project - floor areas, wall areas, everything scales from this.

**Location matters for scope decisions.** Barcelona Eixample has expectations different from rural Extremadura. Urban properties often have comunidad restrictions. Historic zones may have heritage implications. The location also tells you what buyers in this market expect.

**Bedrooms and bathrooms define room count.** A 3-bed, 2-bath apartment has different scope complexity than a 1-bed, 1-bath. More rooms = more scope items. Bathrooms are particularly scope-intensive (15-25 items each for full renovation).

**The description may reveal hidden information.** Sometimes listings mention "recently updated kitchen" or "original fixtures" or "needs complete renovation". This context helps calibrate how much work is actually needed.

---

#### EXAMINE: CANONICAL ROOM IDS - Your Spatial Framework

The canonical room_ids are your containers. Every item you create must belong to one of these rooms (or to "general" for site-wide items).

Look at the list:
```
- room_id: "cocina" → Cocina
- room_id: "dormitorio_1" → Dormitorio Principal
- room_id: "dormitorio_2" → Dormitorio 2
- room_id: "bano_1" → Baño Principal
- room_id: "salon" → Salón-Comedor
- room_id: "pasillo" → Pasillo
- room_id: "terraza" → Terraza
```

This tells you exactly what rooms exist. When you create items, you MUST use these exact room_ids. Don't invent "cuarto_de_bano" if the canonical list says "bano_1". Don't create items for rooms that don't exist.

Every canonical room should have at least one item in your scope (even if minimal - maybe "pasillo" just needs painting). A room with zero items suggests you missed something or deliberately excluded it, which should be explained in reasoning_notes.

---

#### EXAMINE: TARGET PIR - The Property As It Exists Today

This is your primary source for understanding WHAT needs to change. Go through it section by section:

**building_profile - The Building Context**

- **year_built**: When was this building constructed? This tells you what you're dealing with:
  - Pre-1940: Thick masonry walls, potentially non-standard dimensions, possibly no concrete structure, likely original MEP that's long past end-of-life
  - 1940-1980: Early concrete frame, possible asbestos materials, MEP that may need replacement
  - 1980-2000: Modern construction but possibly dated finishes, MEP probably adequate
  - 2000+: Modern standards, likely just cosmetic updates needed

- **floor level and elevator**: Access affects what's practical. A penthouse with private terrace access is different from a 4th floor walkup where every material is carried by hand.

- **energy_rating**: E, F, or G ratings suggest potential regulatory triggers if significant work is done - CTE (Código Técnico de la Edificación) may require energy improvements.

**rooms - Room by Room Analysis**

This is the core. For EACH room in the PIR, examine:

- **condition_summary**: What does it say about this room's current state? "Baño original de los años 70 con azulejos en mal estado y grifería antigua" is very different from "Baño reformado hace 5 años, buen estado general". The condition drives how much work is needed.

- **key_issues**: These are specific problems identified. "Humedad en esquina", "Baldosas agrietadas", "Instalación eléctrica sin toma de tierra". Each issue potentially translates to scope items.

Read the condition descriptions carefully. They tell you:
- What MUST change (broken, failed, non-compliant)
- What SHOULD change (dated, worn, mismatched)
- What COULD stay (decent condition, acceptable for bracket)

**design_profile - Aesthetic Assessment**

- **dominant_style**: Is this property stuck in a time warp? 1985 oak and brass? 2005 Ikea minimalism? Or unrenovated original that might have character?

- **finish_quality_overall**: How does the current finish compare to what the bracket expects? If current is "low" and bracket expects "mid-high", that's a full finish transformation. If current is "mid" and bracket expects "mid", maybe it's selective updates.

- **material_summary**: What specific materials are installed? Floor type (terrazzo, parquet, ceramic, laminate), wall treatment (paint, wallpaper, tile), kitchen/bathroom finishes. This tells you what you're removing or updating.

**triggers - The Reasons for Renovation**

The PIR explicitly identifies things that REQUIRE attention:

- **Electrical triggers**: "Instalación sin toma de tierra" = full rewire needed. "Cuadro eléctrico antiguo" = panel replacement. These aren't optional in Spanish regulations.

- **Plumbing triggers**: "Tuberías de plomo" = mandatory replacement. "Bajantes en mal estado" = critical infrastructure.

- **Structural triggers**: Cracks, settlement, moisture intrusion - these are serious and affect scope.

- **Regulatory triggers**: Things that would fail an ITE inspection or don't meet current CTE. If significant work is done, these may need addressing.

Each trigger with urgency "critical" or "high" MUST appear in your scope. Triggers with "medium" or "low" are judgment calls based on bracket expectations.

---

#### EXAMINE: BRACKET PIR - The Target State

The bracket PIR tells you what the property should BECOME. It's synthesized from comparable properties that sold in this price bracket.

**design_era and finish_level_summary** 

What era of finish do comparable properties have? "Modern 2018-2022 renovation aesthetic" means clean lines, neutral colors, contemporary fixtures. "Classic updated" might mean traditional with modern conveniences. This guides your material and finish choices.

**what_defines_this_bracket**

This is explicit guidance: what separates this bracket from cheaper and more expensive? If it says "Differs from fast_sell by having quartz counters instead of laminate, wall-hung toilets instead of floor-standing, integrated appliances instead of freestanding" - those are your scope decisions made for you.

**common_materials**

Specific material expectations:
- flooring: ["porcelanato rectificado 60x60", "tarima flotante AC4"]
- walls: ["pintura lisa mate", "alicatado metro en cocina"]
- kitchen: ["encimera cuarzo", "muebles melamina blanco", "electrodomésticos integrados"]
- bathroom: ["gres porcelánico", "mueble suspendido", "mampara fija"]

When you create scope items, the materials should match these expectations. Don't spec marble in a quartz bracket. Don't spec laminate in a quartz bracket.

**typical_features**

What features do comparable properties have? Air conditioning? LED lighting? Modern windows? If the bracket has it and the target doesn't, it probably needs to be in scope.

---

#### EXAMINE: BCCA INDEX - How Work is Structured

You won't price anything yet, but understanding how the BCCA structures work helps you create items that will price cleanly later:

- **Demolition is separate from installation.** "Demoler alicatado" is one item. "Instalar alicatado" is another. Don't combine them.

- **Preparation is separate from finishing.** "Impermeabilización" is one item. "Alicatado" that goes on top is another. They're different trades, different materials, different timing.

- **Each discrete task is its own line.** The BCCA has ~12,500 items because construction is granular. When you think "paint the room", that's actually: protect surfaces, fill holes, sand, prime, first coat, second coat, clean up. Not all of these need to be separate items in your scope, but understand that "pintar habitación" is really 4-6 hours of labor covering multiple steps.

---

### Reasoning Process: Creating the Scope

For each room, you think through:

**1. What's the gap?**

Compare TARGET (current state) to BRACKET (target state). What specific changes are needed?
- TARGET: "Baño con azulejos años 80, sanitarios originales, sin mampara"
- BRACKET: "Baños con porcelánico moderno, sanitarios suspendidos, mampara fija"
- GAP: Full bathroom renovation - new tiles, new fixtures, add shower screen

**2. What does that gap break down into?**

"Full bathroom renovation" is not a scope item. Break it down:
- DEMOLITION: Remove floor tiles (1 item), remove wall tiles (1 item), remove toilet (1 item), remove vanity (1 item), remove bathtub/shower (1 item), debris disposal (1 item)
- PREPARATION: Prep floor substrate (1 item), prep wall substrate (1 item), waterproof floor (1 item), waterproof walls wet zone (1 item)
- INSTALLATION: Floor tiles (1 item), wall tiles (1 item), grout floor (1 item), grout walls (1 item), seal grout (1 item)
- FIXTURES: Install toilet (1 item), install vanity (1 item), install basin/faucet (1 item), install shower/tub (1 item), install shower screen (1 item)
- FINISHES: Install mirror (1 item), install lighting (1 item), install accessories (1 item), final connections (1 item), test fixtures (1 item)

That's ~20 items for one bathroom. This level of granularity is correct.

**3. What's realistic vs absurd?**

Some things can't or shouldn't be changed:
- Load-bearing walls: Can't remove without structural engineer and significant cost
- Facade windows: Comunidad often controls exterior appearance
- Riser locations: Moving a bathroom 5m means moving all plumbing
- Ceiling height: Fixed by building structure

Be practical. Match the bracket expectations without gold-plating.

**4. What are the dependencies?**

Even though Phase 3 does scheduling, thinking about execution order helps you not miss items:
- You can't tile before waterproofing cures (so both items must exist)
- You can't install countertop before cabinets (so both items must exist)
- You can't paint before walls are plastered (so both items must exist)

**5. What goes in reasoning_notes?**

Document your thinking:
- Uncertainties: "Unclear if waterproofing behind existing tiles has failed - scoped full replacement to be safe"
- Trade-offs: "Could open kitchen to salon but comparable properties mostly have separate kitchens - kept existing layout"
- Opportunities not taken: "Building has potential for terrace extension but not typical for this bracket"
- Assumptions: "Assumed electrical rough-in needed based on PIR trigger; actual extent to be confirmed on site"

These notes help later phases understand your intent.

---

### Output

- **items**: Array of scope items. Each item has:
  - item_id: Sequential identifier (ITEM_001, ITEM_002, ...)
  - room_id: From canonical list or "general"
  - room_name: Human-readable name in Spanish
  - name: Task name in Spanish ("Demoler alicatado suelo")
  - description: Detailed description in Spanish
  - system: One of (demolition, plumbing, electrical, finishes, hvac, carpentry, ffe, logistics)
  - bcca_chapter: BCCA chapter code ("01" for demolition, "09" for finishes, etc.)
  - comparable_reference: What in BRACKET PIR drove this item

- **rooms_coverage**: Array confirming every canonical room has items:
  ```
  [{"room_id": "cocina", "item_count": 18}, {"room_id": "bano_1", "item_count": 22}, ...]
  ```

- **reasoning_notes**: Array of strings with your thinking, trade-offs, uncertainties

- **total_items**: Integer count of all items

---

### Hygiene Rules

- **SPANISH TEXT**: All name, description, reasoning_notes content in Spanish
- **CANONICAL ROOM_IDS ONLY**: Use exactly the room_ids from the canonical list. Don't invent new ones. Use "general" for site-wide items (permits, protection, final clean).
- **LEAVE NULL FIELDS NULL**: Scheduling fields (phase_week, depends_on, duration_hours) = null. Pricing fields (bcca_code, unit, quantity, unit_price, line_total) = null. Adjustment fields (price_multiplier, adjusted_price, adjustment_reason) = null. Phase 1 only fills scope fields.
- **EVERY ROOM COVERED**: Check your output - every canonical room should have at least one item. If a room genuinely needs no work, note that in reasoning_notes.
- **GRANULAR ITEMS**: Don't create single items like "Renovar baño completo" or "Reforma cocina integral". Break everything down to discrete tasks.

---

## PHASE 2: SCOPE VERIFICATION

### Role
**Senior Project Manager** - A professional who has managed hundreds of renovation projects and has learned the hard way what happens when scopes are incomplete. They've been on sites where the contractor says "this wasn't in scope" and a change order appears. They've seen projects stall because a critical prep step was missing. They read scopes the way a contractor would - looking for gaps, missing steps, incomplete sequences. The PM is the last line of defense before this scope becomes a contract.

### Context to Examine (in depth)

Phase 2 has everything Phase 1 had PLUS Phase 1's output and reasoning. Your job is to verify completeness.

---

#### EXAMINE: PHASE 1 OUTPUT - The Proposed Scope

This is your primary focus. Go through Phase 1's scope item by item:

**Count and distribution.**

How many total items? How many per room? A full bathroom renovation typically has 15-25 items. A full kitchen might have 20-30. If you see a bathroom with 5 items, something is probably missing.

Look at the rooms_coverage from Phase 1. Any rooms with suspiciously few items? Any canonical rooms with zero items?

**For each room, trace the work sequence.**

Take bano_1 as an example. Find all items with room_id: "bano_1" and read through them:

1. Is there demolition? (Remove tiles, remove fixtures)
2. Is there debris disposal?
3. Is there substrate preparation?
4. Is there waterproofing? (Critical for bathrooms - this is THE most commonly missed item)
5. Is there installation? (New tiles, new fixtures)
6. Is there finishing? (Grout, sealant, hardware)
7. Is there testing? (Plumbing pressure test, leak check)

If you find demolition but no debris disposal - gap.
If you find tiles but no waterproofing - gap.
If you find fixtures but no connections/testing - gap.

**Check for the "hidden steps."**

Experienced PMs know what architects sometimes forget:

- **Waterproofing before tiles in wet areas.** Not just bathrooms - also kitchen splash zones, laundry areas. The membrane needs 24-48h cure before tiles. If Phase 1 has tiles but no waterproofing, add it.

- **Surface prep before paint.** Fill holes, sand, prime, then paint. Often collapsed into one item but should exist somehow. If Phase 1 just says "paint room" with no prep, at minimum verify that's intentional (maybe it's just a touch-up job).

- **First-fix and second-fix for MEP.** Electrical rough-in happens before walls close; electrical finish (sockets, switches, lights) happens after painting. If Phase 1 has "instalar enchufes" but no "cableado eléctrico", there's a gap.

- **Hardware with doors.** A door is useless without hinges, handle, striker plate, stops. Either these are explicit items or clearly bundled into the door item.

- **Connections and testing.** New toilet needs connection to waste and water. New sink needs trap and connections. These should be tested (run water, check for leaks) before handover.

---

#### EXAMINE: PHASE 1 REASONING_NOTES

The architect's notes are crucial context:

**What uncertainties did they flag?**

If Phase 1 noted "Unclear if waterproofing behind existing tiles has failed - scoped full replacement to be safe", that tells you the scope is conservative in that area. Good.

If Phase 1 noted "Assumed existing electrical adequate - no rewire scoped", check if that's consistent with TARGET PIR triggers. If PIR flagged electrical issues, the assumption might be wrong.

**What trade-offs did they make?**

If Phase 1 noted "Could open kitchen to salon but kept existing layout per bracket norms", that's a deliberate decision. Don't add items that contradict it.

**What did they defer?**

If Phase 1 noted "Terrace has potential for enclosure but not typical for bracket - not scoped", that's intentional. But check if the terrace at least has basic scope (maybe just clean and repaint).

---

#### EXAMINE: TARGET PIR - Revisit for Completeness

Go back to TARGET PIR with fresh eyes:

**Are all triggers addressed?**

The PIR lists triggers with urgency ratings. Every "critical" and "high" trigger should have corresponding scope items. Cross-check:

- PIR says "instalación eléctrica sin toma de tierra" (critical) → Is there a rewire in scope?
- PIR says "humedades en baño" (high) → Is there waterproofing in scope?
- PIR says "ventanas con filtración" (medium) → Are window repairs in scope?

If a trigger isn't addressed and should be, add items.

**Are room conditions matched by scope?**

For each room in TARGET PIR, does the condition_summary align with what Phase 1 scoped?

- PIR says kitchen is "completamente original, necesita reforma integral" → Kitchen scope should be comprehensive (25+ items)
- PIR says bedroom_2 is "buen estado, solo necesita pintura" → Bedroom_2 scope should be minimal (maybe just painting)

If there's a mismatch, investigate. Maybe Phase 1 missed something. Maybe the PIR description is misleading. Note your findings.

---

#### EXAMINE: BRACKET PIR - Verify Target is Achievable

Go back to BRACKET PIR:

**Does the scope achieve the bracket standard?**

The scope from Phase 1 should, when executed, result in a property that matches BRACKET PIR expectations. Quick check:

- BRACKET expects "porcelanato rectificado" → Is there porcelain tile in scope (not just "tile")?
- BRACKET expects "sanitarios suspendidos" → Are wall-hung fixtures in scope (not just "new toilet")?
- BRACKET expects "cocina con electrodomésticos integrados" → Is there integrated appliance installation in scope?

Phase 1 should have gotten this right, but verify.

---

### Verification Questions

Don't follow a checklist mechanically. Instead, go through each room and ASK YOURSELF these questions. Let your reasoning flow naturally.

**For each bathroom in the scope:**

Look at all the items for this bathroom. Now ask yourself:

- If tiles are being removed, where does the debris go? Is there a debris removal item? If not, who clears the rubble before new work starts?

- If new tiles are being installed in wet areas, where is the waterproofing? This is critical - tiles without membrane will fail within years. Where is the item for waterproofing the floor? The walls in the shower zone? If I can't find it, I need to add it.

- The waterproofing needs to cure before tiles go on top. Does the architect know this? Did they create items for both, or did they assume waterproofing was included in tiling? If they combined them, that might be okay for pricing but we need to make sure it's explicit.

- After tiles are installed, where is the grouting? The sealing? These are separate steps. If I just see "install tiles" with no grout, the contractor will ask "does this include grout or not?"

- The fixtures (toilet, vanity, shower) - are they being installed or just "included"? Is there an item for actually connecting them? Testing for leaks?

- What about the small things - the mirror, the towel rail, the toilet roll holder? These are often forgotten but buyers notice.

**For the kitchen:**

- If cabinets are being replaced, where is the demolition of the old ones? Who removes them?

- Cabinets go in, then counter on top, then appliances fit into the counter. Are these in the right order? Are they all present?

- The sink needs plumbing. The dishwasher needs plumbing AND electrical. The oven needs electrical (and gas if gas). The hob needs gas connection if gas, or high-amp electrical if induction. The extractor needs electrical and probably ducting. Are ALL these connections in scope, or did the architect assume "install appliance" includes connection?

- What about the backsplash behind the counter? Is there tile work? Is it explicit?

**For every room being painted:**

- What's the starting condition? If it's existing painted walls, just paint might be fine. But if it's new plaster, or walls with damage, there needs to be prep. Is prep mentioned or assumed?

- Paint goes: ceiling first (drips don't matter), then walls, then woodwork (frames, skirting, doors). Are these broken out or lumped together?

**For electrical work:**

- Is there first-fix (the cabling inside walls) separate from second-fix (the visible sockets and switches)? In a full renovation, these happen weeks apart - first-fix before walls close, second-fix after painting.

- If there's significant electrical work, who does the boletín? Is the certification item in scope?

**Across the whole scope:**

- On day one of the project, workers arrive. Is the floor protected before demolition starts? If not, they'll damage it.

- All this demolition creates debris. A LOT of debris. Where does it go? Is there skip hire? Is it scheduled before demo starts?

- At the end, before handover, the place needs cleaning. Not just sweeping - proper deep clean of construction dust. Is it in scope?

Go through each room this way. When you find something missing, add it. When you verify something is present, note that in verification_notes so later phases know you checked.

---

### Output

- **items_to_add**: Array of new items that are missing. Each item has the same schema as Phase 1:
  - item_id: Continue from Phase 1's max (if Phase 1 ended at ITEM_065, start at ITEM_066)
  - room_id, room_name, name, description, system, bcca_chapter, comparable_reference
  - Leave scheduling and pricing fields null
  
  If the scope is complete, this is an empty array.

- **verification_notes**: Array of strings documenting what you checked:
  ```
  [
    "Verificado secuencia de baño_1: demolición → impermeabilización → alicatado → instalaciones. Completo.",
    "Añadido impermeabilización en cocina zona fregadero - faltaba en Phase 1.",
    "Verificado todos los triggers del PIR tienen items correspondientes.",
    ...
  ]
  ```

- **rooms_needing_items**: Array of room_ids where you added items: ["cocina", "pasillo"]

- **all_rooms_covered**: Boolean - true if every canonical room has at least one item (including any you added)

---

### Hygiene Rules

- **CAN ADD, CANNOT REMOVE OR MODIFY**: You can add items that are missing. You cannot remove or change existing Phase 1 items. If Phase 1 made an error, note it in verification_notes but don't delete their items.

- **CONTINUE ITEM_ID SEQUENCE**: If Phase 1's highest item_id was ITEM_065, your new items start at ITEM_066, ITEM_067, etc.

- **NEW ITEMS USE SAME SCHEMA**: Everything you add has the same fields as Phase 1 items. Leave scheduling and pricing fields null.

- **SPANISH TEXT**: All names, descriptions, verification_notes in Spanish.

- **VERIFICATION_NOTES ARE THOROUGH**: Document what you checked, not just what you added. "Verificado baños: secuencia completa" is useful even if you added nothing.

---

## PHASE 3: SCHEDULING

### Role
**Construction Director** - A professional who has run dozens of residential renovation projects and understands the physical reality of how work sequences. They know that you can't tile before waterproofing cures, you can't paint before plaster dries, you can't have two trades working in the same small bathroom at the same time. They think in weeks and dependencies, not abstractions.

### Context to Examine (in depth)

Phase 3 takes the complete scope from Phases 1-2 and figures out WHEN each item happens. To do this well, you need to understand not just the items but WHY they exist and HOW they relate to each other.

---

#### EXAMINE: TARGET PIR - The Physical Property

Go back to TARGET PIR and think about the physical constraints of this specific property:

**Room sizes affect parallel work capacity.** A 4m² bathroom means one worker at a time. A 30m² open-plan kitchen-living means multiple trades can work simultaneously. Look at the room descriptions and think about how many people can physically work there at once.

**Floor level and access affect material flow.** A 4th floor walkup means every delivery is slow. Tiles, cement, fixtures - everything comes up by hand. Debris - everything goes down by hand. This affects scheduling - you might want to concentrate material-heavy phases (tiling, finishing) after all demolition debris is cleared, so you're not carrying new materials up past workers carrying debris down.

**Building systems state affects sequence.** If the TARGET PIR flagged "electrical installation original, no earth, needs full rewire", that first-fix electrical work is substantial - not just adding a few points but running all new circuits from the consumer unit. That takes time and needs to happen early, before walls are closed.

**Layout affects workflow.** Spanish apartments often have that central hallway (pasillo) connecting all rooms. During renovation, this hallway is the circulation route for workers and materials. Work that blocks the hallway (floor demolition, floor finishing) affects access to other rooms. Sometimes you do rooms sequentially (finish bedroom 1 before starting bedroom 2) rather than all at once, to maintain access.

---

#### EXAMINE: BRACKET PIR - The Target State

Go back to BRACKET PIR and understand what influences scheduling:

**Finish quality implies drying/curing times.** Higher-end finishes often need more preparation and curing. Quality paint jobs need proper priming and multiple coats with drying between. Quality tile work needs proper waterproofing cure. The bracket's quality expectations affect your timeline.

**Material choices have lead times.** If the bracket implies custom or special-order materials (large-format tiles, specific appliances), those might need ordering in advance. The scheduling should account for this - demolition might start while materials are being ordered.

---

#### EXAMINE: PHASE 1 OUTPUT AND REASONING

Go back to Phase 1's scope and reasoning_notes:

**The items tell you what work exists.** Read through ALL items. Group them mentally:
- All demolition items (these go early)
- All first-fix MEP items (electrical rough-in, plumbing repositioning)
- All preparation items (waterproofing, substrate prep, priming)
- All finish items (tiling, plastering, painting)
- All second-fix items (fixture installation, hardware, final connections)
- All logistics items (protection, cleanup)

Each group has a natural position in the timeline.

**The reasoning_notes reveal complexity.** If Phase 1 noted "uncertain about extent of waterproofing" or "may need to open walls to assess electrical", build buffer time into the schedule. The architect's uncertainties become your contingency.

**The comparable_reference shows the target.** If items reference "comparable bathrooms have wall-hung toilets", that's modern concealed-cistern installation - more complex first-fix (the frame goes in before walls close) than a standard floor-standing toilet.

**Item relationships suggest dependencies.** Items in the same room often have implied sequence. "Demoler alicatado suelo baño" (demo floor tiles) logically precedes "Impermeabilización suelo baño" (waterproof floor) which precedes "Alicatado suelo baño" (new floor tiles). Make these dependencies explicit.

---

#### EXAMINE: PHASE 2 OUTPUT AND REASONING

Go back to Phase 2's additions:

**What did the PM add?** Phase 2 typically adds:
- Preparation items the architect missed (waterproofing, priming)
- Finishing items (grouting, sealing, hardware)
- Testing and certification items (boletín eléctrico)
- Logistics items (protection, cleanup)

These additions need scheduling too. Prep items go before their corresponding installation. Finishing items go after main installation. Testing goes near the end. Cleanup is last.

**The verification_notes show what was checked.** If PM wrote "added waterproofing for all wet areas - needs 48h cure before tiling", you now have explicit cure time requirements to build into the schedule.

**The total item count grew.** Phase 1 might have had 60 items, Phase 2 added 15 (now 75). You're scheduling all 75. Don't lose any.

---

### Reasoning Process: Physical Constraints

Now think through the physical reality of renovation work:

**The immutable sequence of trades:**

1. **Demolition comes first.** You can't build new until old is removed. Demo is noisy, dusty, heavy - do it early and clear it out.

2. **First-fix MEP follows demo.** Once walls and floors are open, electricians run cables, plumbers run pipes, HVAC runs ducts. This MUST happen before walls close.

3. **Structural/carpentry overlaps.** Door frames, window frames, any stud walls - these define the spaces that finishes will cover.

4. **Waterproofing before wet finishes.** Any area getting tiles in a wet zone (bathroom, kitchen splash) needs waterproofing membrane. And that membrane needs 24-48 hours to cure before tiles go on top.

5. **Wet trades in sequence.** Tiling, then plastering, then painting. Each needs the previous to be done and sometimes dry. Plaster on new construction needs 2-3 weeks before painting. Paint needs coats with drying between.

6. **Second-fix after finishes.** Once walls are painted and floors are tiled, you install the toilets, mount the lights, fit the switches, hang the doors.

7. **Final clean and handover.** The last thing, after all trades are done.

**Physical constraints that create dependencies:**

- **Waterproofing cure**: 24-48h before tiling. Non-negotiable - tiles laid on uncured membrane will fail.
- **Plaster dry time**: 2-3 weeks for new plaster before painting. Less critical for old walls just getting repainted.
- **First-fix before close**: Electrical cables, plumbing pipes must be in before plasterboard/finishing covers them.
- **Cabinets before counters**: Kitchen and bathroom cabinets are the base. Countertops sit on them. Appliances fit into them.
- **High work before floor finish**: If you need scaffolding for ceilings, do that before you've laid the nice new floor.

**Trade coordination constraints:**

You can't have a tiler and a painter working in a 4m² bathroom at the same time. In small spaces, trades work sequentially. In larger spaces, they can overlap (electrician in bedroom 1 while tiler in bathroom).

---

### Scheduling Principles

The following PRINCIPLES govern how work sequences in ANY renovation. Apply these to the specific scope:

**PRINCIPLE A: Protection Before Everything**

Before any work starts, the property must be protected. Floor protection, dust barriers, door covers - these come FIRST. Demolition creates debris and dust that damages unprotected surfaces. The earliest scheduled items must always be protection and mobilization.

**PRINCIPLE B: Demolition Before Installation**

You can't install new things until old things are removed. In any area where existing elements are being replaced, demolition items must precede installation items. This seems obvious, but it has implications: debris must be cleared before new materials arrive, or they'll be stored in rubble.

**PRINCIPLE C: First-Fix Before Walls Close**

Electrical cables, plumbing pipes, HVAC ducts - anything that runs INSIDE walls must be installed BEFORE those walls are finished. Once plasterboard is up or plaster is applied, you can't run cables behind it (without ripping it down). First-fix MEP must happen when walls are "open" - after demolition, before finishing.

**PRINCIPLE D: Waterproofing Needs Cure Time**

Waterproofing membranes are critical in wet areas (bathrooms, kitchen splash zones). They need 24-48 hours minimum to cure before tiles can be laid on top. A schedule that has tiling the same day or next day after waterproofing is physically wrong - those tiles will fail.

**PRINCIPLE E: Wet Trades Before Dry**

"Wet" trades (plaster, screed, waterproofing) introduce moisture that must dry before "dry" trades (paint, flooring) can proceed:
- Fresh plaster needs 2-3 weeks to dry before painting
- Screed needs similar time before floor finishes
- The schedule must allow for drying - you can't compress this

**PRINCIPLE F: High Work Before Floor Finishes**

Work requiring scaffolding or ladders (ceilings, high walls, cornices) should happen BEFORE new floors are installed. Scaffolding feet scratch and dent new flooring. If ceiling work is scheduled after floor installation, the floors need heavy protection.

**PRINCIPLE G: Finishes Before Second-Fix**

Paint the walls BEFORE you mount the switches and sockets. Install floor tiles BEFORE you set the toilet. Second-fix (visible electrical, plumbing fixtures, hardware) comes after surfaces are finished. This avoids having to mask around fixtures and touch up.

**PRINCIPLE H: Cleanup Is Last**

Deep cleaning is the final item. Construction dust is incredibly fine and coats everything. Clean only after ALL trades are complete, not in between.

**HOW THESE COMBINE:**

These principles combine to create a natural flow: Protection → Demo → First-Fix → Framing → Waterproofing/Prep → Wet Finishes (tile, plaster) → [DRYING TIME] → Dry Finishes (paint) → Second-Fix → Final Finishes → Cleanup → Handover.

The SPECIFIC weeks depend on the scope size and complexity. A small bathroom-only renovation might be 3-4 weeks. A full apartment gut might be 10-14 weeks. Apply the principles to the actual items to determine the actual schedule.

**TYPICAL DURATIONS (for calibration):**
- Protection/mobilization: 1-2 days
- Bathroom demolition: 2-3 days per bathroom
- Electrical first-fix: 3-5 days for full apartment
- Waterproofing + cure: 3-4 days
- Tiling: 5-8m² per day per tiler (adjust for wall vs floor, tile size)
- Painting: 1 coat per day per room (with drying between)
- Kitchen installation: 3-5 days for cabinets + counters + appliances

Use these to sanity-check duration_hours, but let the PRINCIPLES drive the sequence.

---

### Output

- **items**: ALL items from Phase 2 with scheduling fields added:
  - phase_week: Which week (1, 2, 3, etc.)
  - depends_on: Array of item_ids that must complete before this item can start
  - duration_hours: Estimated labor hours for this item
- **total_weeks**: The overall project duration
- **critical_path**: Array of item_ids that determine the total duration (if any of these slips, the project slips)
- **phase_breakdown**: Object mapping week to array of item_ids {"week_1": ["ITEM_001", "ITEM_002"...], "week_2": [...]}

---

### Hygiene Rules

- **NO ITEM LOSS**: The input has X items (from Phases 1+2 combined). Your output must have exactly X items. Every item_id from input must appear in output with scheduling fields filled.
- **KEEP ALL EXISTING FIELDS**: Each item already has scope fields (item_id, room_id, name, description, system, bcca_chapter, comparable_reference). Keep all of these exactly as they are. Add the scheduling fields.
- **ALL ITEMS GET SCHEDULED**: Every single item needs phase_week (integer), depends_on (array, can be empty), and duration_hours (number). No nulls.
- **REASONABLE DURATIONS**: Think about what's realistic. Demolishing a bathroom floor might be 4-6 hours. Tiling that same floor might be 8-10 hours. Painting a bedroom might be 6-8 hours. Don't just put "1" for everything.
- **SENSIBLE DEPENDENCIES**: depends_on should list items that MUST complete before this one can START. Don't make everything depend on everything. Identify the real physical dependencies.

---

## PHASE 4: LOGISTICS CHECK

### Role
**Site Manager** - A professional who has been on job sites when things go wrong. They know what happens when you start demo without floor protection (goodbye existing floors in circulation areas). They know what happens when there's no skip (debris piles up, workers can't move, productivity crashes). They know about the permits you need before you start and the inspections you need before you close walls. The Site Manager catches what office-bound architects and schedulers miss.

### Context to Examine (in depth)

Phase 4 reviews the complete scheduled scope and asks: "Can we actually execute this on a real job site?" You need to examine all prior context to understand the practical realities.

---

#### EXAMINE: TARGET PIR - Site Conditions

Go back to TARGET PIR and think about the physical site:

**Access and logistics.**

- **Floor level and elevator**: A 4th floor walkup changes everything. Materials go up slowly. Debris comes down slowly. Workers tire faster. There needs to be explicit time allocated for vertical transport. If there's a building elevator, is it usable for construction? Some comunidades forbid using the elevator for construction materials.

- **Building entrance and hallways**: How do you get materials from street to apartment? Narrow doorways might limit what can be delivered assembled. Long hallways need protection. Stairs need protection if used for material transport.

- **Neighboring units**: Is the building occupied? Neighbors above, below, adjacent? This affects noise constraints, dust management, work hours.

**Room access during works.**

- **Single entrance apartments**: If there's only one door, all circulation goes through it. Work in the entrance area affects access to everywhere else.

- **Bathroom count**: If there's only one bathroom and it's being fully renovated, where do workers use facilities during the project? This seems minor but matters on real sites.

---

#### EXAMINE: LISTING DATA - Location Context

Go back to LISTING DATA for location information:

**Street and parking.**

- **Where does the skip go?** Spanish cities often have narrow streets, limited parking. A skip (contenedor) needs space. Is there street parking that can be used? Do you need a permit from the Ayuntamiento?

- **Material deliveries.** Where does the delivery truck stop? If it's double-parking, deliveries need to be quick. Some areas have restricted delivery hours.

- **Heritage zone restrictions.** Historic centers sometimes have rules about construction visible from the street, work hours, noise levels.

---

#### EXAMINE: PHASE 1 OUTPUT - Scope Implications

Go back to Phase 1's scope and think about logistics implications:

**Demolition scope implies waste management.**

Count the demolition items. Full bathroom demo? Full kitchen demo? All floors? That's a LOT of debris - tiles, cement, old fixtures, packaging from new materials. A typical full apartment renovation generates 2-4 container loads of debris. Is skip hire in the scope? Is interim debris removal (so debris doesn't accumulate for weeks)?

**MEP work implies inspections.**

If there's electrical work (rewire, new circuits, significant modifications), Spanish regulations require a boletín eléctrico - a certificate from a licensed electrician. This isn't optional. Is it in the scope?

If there's gas work (boiler, hobs, gas lines), you need a certified gas installer and certificate.

If there's HVAC with refrigerant (splits), you need F-gas certification.

Are these inspection/certification items in the scope? If not, add them.

**Structural work implies permits.**

Look at Phase 1 for any structural items - removing walls, new openings, structural reinforcement. These require:
- Building permit from Ayuntamiento (licencia de obra mayor)
- Often a technical project signed by an architect
- Sometimes comunidad approval

Is permit application in the scope? Is it scheduled BEFORE work starts?

---

#### EXAMINE: PHASE 2 OUTPUT - What PM Added

Go back to Phase 2's additions:

**What logistics did PM already catch?**

Phase 2 often adds items like floor protection, debris removal, testing. Review what's there. Don't duplicate, but also check for gaps.

**What's the total item count now?**

Phase 1 + Phase 2 = total scope items. You're reviewing ALL of them for logistics completeness.

---

#### EXAMINE: PHASE 3 OUTPUT - The Schedule

Go back to Phase 3's scheduled items:

**Does the schedule respect dependencies?**

For each item with a depends_on field:
- Is every dependency scheduled in an EARLIER week than this item?
- If an item depends on something scheduled in the SAME or LATER week, that's a sequencing error.

For items with cure/dry time requirements:
- Is there enough gap between waterproofing and subsequent tiling? (Minimum 48h)
- Is there enough gap between new plaster and painting? (Minimum 2-3 weeks for new plaster; just repainting existing walls doesn't need this)

If you find sequencing errors, note them in sequencing_fixes.

**Are logistics items in the right position?**

Find the protection items (floor covers, dust barriers). These should be scheduled BEFORE any other work - they must be the earliest scheduled items.

Find the skip hire / debris removal items. These should be scheduled BEFORE demolition starts.

Find the final clean item. This should be scheduled AFTER all other work - it must be the latest scheduled item (or among the latest).

**Are cure times respected?**

Look for tight sequences. If waterproofing is scheduled and tiling is scheduled in the immediately following days, is there at least 48h gap? Standard is 48h minimum but many professionals prefer 72h to be safe. Flag any sequences that seem tight.

---

### Logistics Questions

Think through the practical reality of executing this project. Ask yourself these questions:

**Before any work starts:**

- On the very first day, workers arrive with tools. They're about to start demolition. Is the existing flooring in the hallway protected? If not, by the end of day one, the parquet in the pasillo will be scratched and damaged from debris being dragged through. Where is the floor protection item? When is it scheduled - it needs to be literally the first thing that happens.

- Are there dust barriers if neighbors are adjacent or above/below? Renovation dust gets EVERYWHERE. If this is an occupied building, dust control matters.

**Waste management:**

- Look at the demolition scope. Bathroom tiles, kitchen cabinets, maybe flooring throughout. That's a LOT of material. In my experience, a full apartment gut generates 3-4 skip loads. Where is the skip hire? Is it scheduled before demolition starts, so there's somewhere to put the debris from day one?

- If the skip goes on a public street, you need a permit from the Ayuntamiento. Is that in scope? Does the schedule allow time to obtain it before the skip arrives?

- If demolition is phased (bathrooms first, then kitchen later), debris builds up. Is there interim debris removal, or does rubble pile up for weeks?

**Access and equipment:**

- What's the ceiling height? Standard 2.5m is fine with a ladder. But if there are 3m+ ceilings, or any high work (cornices, high cabinets, ceiling work), you might need scaffolding or a tower. Is it in scope?

- If there's any exterior work or high facade access, where's the scaffolding? Who arranges it?

**Permits - this is where projects get stuck:**

- Is there any structural work (removing walls, new openings, reinforcement)? If yes, you need a licencia de obra mayor from the Ayuntamiento. This takes weeks to obtain. Is permit application in scope? Is it scheduled BEFORE construction starts?

- Does the comunidad need to approve? Work that makes noise, affects common areas, or involves the facade usually needs comunidad approval. Where is it?

**Inspections and certifications:**

- If there's significant electrical work, Spanish regulations require a boletín eléctrico - a certificate from a licensed electrician that the installation meets code. This isn't optional. Is it in scope?

- If the gas installation is touched (boiler, hob, gas lines), you need a certificado de instalación de gas. Is it in scope?

- If HVAC systems with refrigerant (split AC) are installed, you need F-gas certification. Is it in scope?

- If the electrical panel is being replaced, there might need to be temporary power during the changeover. Is that considered?

**At the end:**

- Before handover, everything needs to be cleaned. Not just swept - properly cleaned. Construction dust is incredibly fine and coats everything. Is professional deep cleaning in scope?

- Is there a snagging walk-through scheduled? Time for punch list items to be fixed?

- Documentation handover - the owner should receive all certificates (boletines), appliance manuals, warranties. Is that explicit?

**Now check the schedule:**

Look at Phase 3's output. Is anything impossible?

- Is any item scheduled BEFORE its dependencies? Look for the depends_on fields. If item A depends on item B, A must be in a later or same week as B, not earlier.

- Is tiling scheduled immediately after waterproofing? The membrane needs 48h minimum to cure. If waterproofing is Friday and tiling is Monday, that's barely enough. If they're the same day, that's wrong.

- Is painting scheduled soon after new plastering? Fresh plaster needs 2-3 weeks to dry before paint adheres properly. Check the gap between plastering items and painting items - if there's only one week between them, that's not enough for new plaster (but might be fine for just repainting existing walls - check what the item actually describes).

When you find issues, either add missing items or note sequencing problems in sequencing_fixes.

---

### Output

- **items_to_add**: New logistics items that are missing. Each needs:
  - item_id: Continue from Phase 2's max (if Phase 2 ended at ITEM_077, start at ITEM_078)
  - room_id: Usually "general" for logistics items
  - room_name: "General / Obra"
  - name: Spanish name
  - description: Spanish description
  - system: "logistics"
  - bcca_chapter: Usually "01" (actuaciones previas) or "16" (seguridad)
  - comparable_reference: Can be null or brief note
  - phase_week: MUST be filled (these are scheduled items)
  - depends_on: Relevant dependencies
  - duration_hours: Estimated time
  
- **sequencing_fixes**: Array of corrections if Phase 3 made errors:
  ```
  [
    {"item_id": "ITEM_045", "old_week": 5, "new_week": 6, "reason": "Necesita 48h mínimo para curado de impermeabilización"},
    ...
  ]
  ```
  
- **permits_needed**: Array of required permits based on scope
- **inspections_needed**: Array of required inspections based on scope
- **verification_complete**: Boolean - true if logistics review is complete

---

### Hygiene Rules

- **CAN ADD, CANNOT REMOVE**: You can add logistics items that are missing. You cannot remove or modify existing items from Phases 1-3.
- **NEW ITEMS ARE COMPLETE**: Any item you add must have ALL fields including scheduling (phase_week, depends_on, duration_hours). Don't add unscheduled items.
- **CONTINUE ITEM_ID SEQUENCE**: If previous phases ended at ITEM_077, your new items are ITEM_078, ITEM_079, etc.
- **SPANISH TEXT**: All names and descriptions in Spanish.
- **SEQUENCING FIXES ARE SEPARATE**: If you're correcting a scheduling error from Phase 3, put it in sequencing_fixes, not in items_to_add. Don't create duplicate items.

---

## PHASE 5: PRICING

### Role
**Quantity Surveyor** - A senior professional who measures work, understands construction pricing, and knows that accurate estimates require understanding not just WHAT is being done but WHY it was specified and HOW it will be executed.

### Context to Examine (in depth)

Phase 5 has the richest context of any phase so far. You need to examine ALL of it because pricing requires understanding the complete picture - the property, the target state, WHY each item exists, HOW it will be executed, and WHERE to find the right price.

---

#### EXAMINE: TARGET PIR

Go back to the TARGET PIR and look at it through the lens of a quantity surveyor:

**Room dimensions are your quantity source.** The PIR describes each room. Look for:
- Floor areas (for flooring, tiling, waterproofing)
- Wall perimeters and heights (for painting, wall tiling - remember to subtract window/door openings)
- Ceiling areas (usually same as floor, but check for unusual shapes)
- Linear measurements (for skirting, coving, trim)

When the PIR says "baño_1: approximately 2.1m × 2.0m", that 4.2m² is what you'll use for floor tile quantity. But also think - wall tiling usually goes up 2.1m height in wet areas, so a 2.1m × 2.0m bathroom has roughly (2.1 + 2.0 + 2.1 + 2.0) × 2.1 = 17.2m² of potential wall area, minus the door (~1.6m²) = ~15.6m² of wall tile if fully tiled.

**Condition affects complexity, complexity affects price selection.** If the PIR flagged "substrate in poor condition" or "evidence of previous water damage", the scope items for preparation work might need a more robust (and expensive) BCCA code than standard prep.

**Building characteristics affect code selection.** A pre-1940 building often has thicker walls, non-standard openings, irregular floors. When pricing items in such buildings, you might need to select BCCA codes that account for additional labor (like "regularización de superficies" before tiling).

---

#### EXAMINE: BRACKET PIR

Go back to the BRACKET PIR and understand what it means for pricing:

**Material quality tier drives BCCA code selection.** The bracket PIR tells you what buyers at this price point expect. If it says "porcelanato rectificado 60x60 en zonas comunes", you're looking for BCCA codes for rectified porcelain, not basic ceramic. If it says "encimera de cuarzo", you're pricing quartz countertops, not laminate.

The BCCA has MANY variants of similar items at different price points:
- 09ACE00110 might be basic 30x30 ceramic at €24/m²
- 09ACE00130 might be 30x30 porcelain rectified at €32/m²
- 09ACE00150 might be 60x60 large format at €45/m²

The bracket PIR tells you WHICH tier is appropriate. Don't under-spec (buyer will sense "cheap") and don't over-spec (you're wasting money beyond what the bracket expects).

**The "what_defines_this_bracket" field is key.** It explicitly tells you how this bracket differs from cheaper and more expensive. Use this to guide material selection throughout.

---

#### EXAMINE: PHASE 1 OUTPUT AND REASONING

Go back to Phase 1's scope items and reasoning_notes:

**Understand WHY each item was created.** The architect didn't just list "alicatado suelo baño" randomly - they saw something in the TARGET PIR (cracked tiles, dated finish, waterproofing failure evidence) and something in the BRACKET PIR (expectation of modern porcelain) that drove this item. Understanding the WHY helps you:
- Select the right BCCA code variant
- Estimate quantity more accurately (is it a small repair or full replacement?)
- Price preparation work appropriately

**Read the reasoning_notes carefully.** The architect might have written:
- "Uncertain about waterproofing extent in baño_1 - PIR shows some staining but unclear if membrane has failed. Scoped full waterproofing to be safe."
- "Kitchen layout seems functional, only updating finishes not configuration"
- "Considered opening kitchen to salon but bracket comps mostly have separate kitchen"

These notes tell you the INTENT behind the scope. When pricing waterproofing for baño_1, you now know the architect was conservative - price accordingly. When pricing kitchen, you know it's finishes only, not structural changes.

**The comparable_reference field explains the target.** Each item has a note about what in the BRACKET PIR drove it. "Comparable kitchens have quartz countertops" tells you exactly what quality level to price.

---

#### EXAMINE: PHASE 2 OUTPUT AND REASONING

Go back to Phase 2's additions and verification_notes:

**What did the PM catch that the architect missed?** If Phase 2 added waterproofing that Phase 1 forgot, that tells you the PM was concerned about completeness in wet areas - make sure you price the waterproofing robustly.

**The verification_notes show what was checked.** If the PM wrote "verified all tile installations have waterproofing prep", you know the sequence is intentional. Price both the waterproofing AND the tiles.

**Item count grew.** If Phase 1 had 65 items and Phase 2 added 12 (now 77), those 12 additions are usually logistics, prep, and finishing items. They're often smaller value but essential - don't skip pricing them.

---

#### EXAMINE: PHASE 3 OUTPUT AND REASONING

Go back to Phase 3's scheduled items:

**Duration estimates inform quantity/complexity.** If the scheduler allocated 16 hours for tiling a bathroom, that's roughly 2 days for one tiler. Reverse-engineering: if standard tiling is about 5-8m² per day, that suggests the bathroom is around 10-16m² of tile work (floor + walls). This is a sanity check on your quantity estimate.

**Dependencies reveal sequences that affect pricing.** If waterproofing depends on demolition and tiling depends on waterproofing with a gap for curing, you're pricing a standard sequence. But if the scheduler noted "complex sequence due to phased access", there might be additional costs.

**The critical_path items are often the most expensive.** Items that determine the timeline are usually substantial work - full bathroom renovations, kitchen fit-outs, etc. Make sure you price these carefully.

---

#### EXAMINE: PHASE 4 OUTPUT AND REASONING

Go back to Phase 4's logistics additions:

**Site logistics affect overall cost.** If Phase 4 added scaffolding, skip hire, floor protection - these are real costs that the BCCA covers. Find the appropriate codes.

**Permits and inspections are costs.** Boletín eléctrico isn't free - there's the inspection fee and the electrician's time to prepare documentation. Price these.

**Sequencing fixes reveal complexity.** If Phase 4 had to adjust the schedule due to sequencing issues, that suggests a complex project with potential for coordination problems. This context helps you understand the overall scope complexity.

---

#### EXAMINE: BCCA INDEX

Now, with full understanding of the project, examine the BCCA index:

**Structure of the index.** Format is CODE|DESCRIPTION|PRICE. The code's first two digits indicate the chapter:
- 01: Actuaciones previas (preliminaries, demolition)
- 02-04: Earthworks, foundations (rarely used in apartment renovation)
- 05: Estructuras (structural)
- 06: Fachadas (facades)
- 07: Particiones (partitions, internal walls)
- 08: Cubiertas (roofing)
- 09: Revestimientos y trasdosados (finishes - this is the big one for renovation)
- 10: Carpintería (joinery, doors, windows)
- 11-13: MEP (installations)
- 14-16: Urbanización, seguridad (site works, safety)

**Prices are COMPOSITE.** When you see €32/m² for tiling, that includes:
- Labor (the tiler's time)
- Materials (tiles, adhesive, grout, sealant)
- Small tools and consumables
- Contractor overhead and profit

Do NOT break these down. Use them as-is. The BCCA is a professional pricing database used across Spain.

**Prices are ANDALUCÍA baseline.** Andalucía has lower labor costs than Barcelona or Madrid. Phase 6 will apply regional adjustments, so use the base prices here without modification.

**Search strategically.** For "alicatado suelo cocina", search for "alicatado" and "azulejo" and "solado". Read multiple options and select the one that matches the BRACKET PIR quality expectations.

---

#### EXAMINE: FFE INDEX

For furniture, fixtures, and equipment not in BCCA:

**Three-tier pricing.** FFE has BUDGET_LOW, BUDGET_MID, BUDGET_HIGH. Select based on package type:
- fast_sell package → BUDGET_LOW
- fair_market package → BUDGET_MID  
- out_of_market package → BUDGET_HIGH

**When to use FFE vs BCCA.** Use FFE for:
- Appliances (fridge, oven, dishwasher, washer)
- Sanitary ware if not in BCCA (specific vanity units, designer fixtures)
- Furniture if included in scope (wardrobes, kitchen cabinets as units)

BCCA covers most installation work, but FFE covers the actual items when they're specified as loose furniture/equipment.

---

### Reasoning Process

For each item in the scope, you think through:

1. **What is this item actually?** Read the name, description, and comparable_reference. Understand what work is being done and to what standard.

2. **Why was it specified?** Go back to Phase 1 reasoning if needed. What in the TARGET PIR triggered this? What in the BRACKET PIR defined the quality level?

3. **What are the dimensions?** Go to TARGET PIR for the relevant room. Calculate the quantity - floor area, wall area, linear meters, unit count. Show your formula.

4. **What BCCA/FFE code matches?** Search the index. Consider the quality tier from BRACKET PIR. Select the appropriate code.

5. **Read the price.** Extract it from the index. Don't invent prices.

6. **Calculate line_total.** quantity × unit_price. Simple multiplication.

7. **Sanity check.** Does this line_total feel reasonable for this work? A small bathroom floor tile at €130 feels right. A small bathroom floor tile at €1300 suggests a calculation error.

---

### Output

- **items**: ALL items from Phase 4 with pricing fields added:
  - bcca_code: The code from BCCA index (e.g., "09ACE00130")
  - ffe_code: The code from FFE index if applicable (null otherwise)
  - unit: The unit (m², ud, ml, kg, etc.)
  - quantity: The calculated quantity (number)
  - quantity_formula: String showing calculation ("2.1m × 2.0m = 4.2m²")
  - unit_price: The price from index (number with 2 decimals)
  - line_total: quantity × unit_price (calculated number)
- **subtotals_by_system**: Object with sum per system {"demolition": 2340.00, "finishes": 12500.00, ...}
- **total_before_adjustments**: Sum of all line_total values
- **pricing_notes**: Array of strings noting any adaptations, estimates, or observations

---

### Hygiene Rules

- **NO ITEM LOSS**: Count items in input. Your output must have exactly that many items. Every item_id from input appears in output.
- **NO NULL PRICES**: Every single item must have unit_price (number) and line_total (number). Never null. If you can't find exact match in index, find closest and note in pricing_notes.
- **KEEP ALL EXISTING FIELDS**: You're adding pricing fields to items that already have scope fields (from Phase 1-2) and scheduling fields (from Phase 3-4). Keep everything.
- **PRICES ARE NUMBERS**: unit_price: 32.00 not "32.00". line_total: 134.40 not "134.40".
- **ALL TEXT IN SPANISH**: quantity_formula, pricing_notes - write in Spanish.

---

## PHASE 6: REGIONAL ADJUSTMENTS

### Role
**Senior Cost Consultant** - A professional who has worked across Spain and understands that identical work costs very different amounts depending on WHERE it happens and WHAT building it happens in. The BCCA prices are accurate for Andalucía in a normal building with good access. But this property might be in Barcelona, on the 4th floor with no elevator, in a pre-war building with heritage restrictions. The Cost Consultant knows how to adjust.

### Context to Examine (in depth)

Phase 6 is the final pricing phase. You have the complete priced BOQ from Phase 5. Now you need to examine ALL prior context to understand what adjustments are needed.

---

#### EXAMINE: LISTING DATA - Where Is This Property?

Go to the LISTING DATA and find the location information:

**The city determines the regional baseline adjustment.**

Spanish construction labor costs vary dramatically by city. The BCCA is based on Andalucía, which has among the lowest labor costs. Other regions are more expensive:

- **Barcelona city center**: +15-20%. Barcelona has the highest construction labor costs in Spain. Strong demand, limited supply of skilled trades, high cost of living. A tiler in Barcelona earns significantly more than a tiler in Sevilla.

- **Madrid city center**: +10-15%. The capital has high demand but more competition than Barcelona. Still a meaningful premium over Andalucía.

- **Valencia city**: +0-5%. Growing market but still relatively affordable. Close to BCCA baseline.

- **Málaga, Sevilla, Granada**: +0%. These are BCCA baseline territory - Andalucía.

- **Balearic Islands**: +10-15%. Everything ships by ferry. Logistics costs are higher. Skilled trades are in short supply.

- **Canary Islands**: +10-15%. Even more remote. Similar dynamics to Balearics.

- **Smaller cities, rural areas**: -5% to +5%. Depends on local market conditions.

**The specific neighborhood matters too.** "Barcelona" is a city of 1.6 million. A project in Eixample is different from a project in a new development in Sant Cugat. Historic center? Narrow medieval streets? Tourist zone with restricted work hours? Note these.

---

#### EXAMINE: TARGET PIR - Building Characteristics

Go back to TARGET PIR and examine the building_profile section:

**Floor level and elevator status.**

Every material, every tool, every piece of debris must get into and out of the property. In a building with an elevator, this is straightforward. But in a 4th floor walkup:
- Bags of cement (25kg each) carried up by hand
- Floor tiles (heavy boxes) carried up by hand
- Old tiles and debris (very heavy) carried down by hand
- Large items (vanity units, shower screens) awkward on stairs
- Workers expend more energy, work slower, need more breaks

This is real cost: +5-10% depending on floor. A 5th floor walkup might be +10%. A 2nd floor walkup might be +5%. Ground floor or building with good elevator: +0%.

**Building age and construction type.**

Pre-1940 buildings in Spain often have:
- Non-standard dimensions (walls not square, floors not level)
- Thick masonry walls that are hard to chase for cables
- No concrete structure (load-bearing masonry throughout)
- Potential for surprises when you open walls (hidden pipes, old wiring, structural issues)
- Heritage implications (even if not formally listed, comunidad or city may have opinions)

This adds uncertainty and labor: +10% or more for pre-1940.

Buildings from 1940-1980 often have:
- Early concrete frame construction (sometimes with quality issues)
- Asbestos-containing materials possible (requires specialist removal)
- Old but standardized dimensions

Add +5% for potential complications.

Buildings from 1980+ are usually:
- Modern construction standards
- Standardized dimensions
- Easier to work on

No age-related adjustment needed.

**Heritage or protection status.**

If the building is:
- BIC (Bien de Interés Cultural) - formally protected: +15-20%. Strict rules, specialist trades, heritage-approved materials, extensive documentation.
- On a local heritage catalog: +10-15%. Less strict but still restrictions.
- In a historic zone: +5-10%. May have facade or exterior restrictions.

Look at the TARGET PIR and listing data for any mention of "protegido", "catalogado", "histórico", "patrimonio".

---

#### EXAMINE: LISTING DATA - Access Context

Look for clues about site access:

**Street characteristics.**

Narrow street with limited parking? That means:
- Skip placement far from entrance (longer debris carries)
- Material deliveries need coordination (can't just leave a pallet)
- Possible double-parking fees for delivery trucks

Add +5% for access difficulties.

**Noise and work hour restrictions.**

Some buildings have strict comunidad rules about work hours. Some neighborhoods have tourist-related noise restrictions. If workers can only be loud from 9am-2pm and 4pm-7pm (typical Spanish pattern), that compresses productive time.

Add +5-10% for significant restrictions.

---

#### EXAMINE: PHASE 5 OUTPUT - The Priced BOQ

Go back to Phase 5's output and look at:

**Total before adjustments.** This is your base that you're adjusting. A €30,000 project with +15% adjustment adds €4,500. Make sure the adjustment factors make sense for the magnitude.

**Distribution of costs.** If the project is heavily weighted toward finishes (which are labor-intensive), regional adjustments matter more. If it's heavily weighted toward materials/FFE (which ship at standard prices), the labor adjustment matters less.

**Phase 5's pricing_notes.** Did the QS note any unusual pricing? Any adaptations? These might warrant an extra adjustment for uncertainty.

---

#### EXAMINE: ALL PRIOR PHASE REASONING

**Phase 1 reasoning_notes**: Did the architect note building complexity? Heritage concerns? Access issues?

**Phase 2 verification_notes**: Did the PM note any logistical challenges?

**Phase 3 scheduling**: How many total weeks? A longer project has more coordination overhead. 10 weeks is standard; 14+ weeks suggests complexity that might warrant a small adjustment.

**Phase 4 logistics items**: What permits and inspections were identified? Complex permitting (heritage, structural) adds cost beyond just the permit fee.

---

### Reasoning Process

The Cost Consultant synthesizes all factors:

1. **Identify regional factor.** Where is this property? What's the city-level adjustment? Barcelona centro = +15-18%. Madrid centro = +12%. Valencia = +3%. Sevilla = +0%.

2. **Identify access factors.** Floor level? Elevator? Narrow street? Work hour restrictions? Each adds a percentage.

3. **Identify building factors.** Building age? Heritage status? Construction type? Each adds a percentage.

4. **Combine factors.** You can multiply (1.15 × 1.08 × 1.10 = 1.36) or you can add a weighted combination. Either way, document your reasoning.

5. **Apply to each item.** The multiplier applies to line_total. adjusted_price = line_total × price_multiplier.

6. **Calculate final total.** Sum all adjusted_price values. Add IVA (21%).

---

### Typical Adjustment Examples

**Example 1: Barcelona Eixample, 3rd floor no lift, 1920s building**
- Regional: +17% (Barcelona centro)
- Access: +7% (3rd floor walkup)
- Building: +12% (pre-1940 construction)
- Combined: roughly 1.40 multiplier
- A €35,000 base estimate becomes €49,000 before IVA

**Example 2: Valencia centro, 1st floor with lift, 2005 building**
- Regional: +3% (Valencia)
- Access: +0% (good lift access)
- Building: +0% (modern construction)
- Combined: 1.03 multiplier
- A €35,000 base estimate becomes €36,050 before IVA

**Example 3: Sevilla historic center, ground floor, 1890 building, heritage listed**
- Regional: +0% (Andalucía = BCCA baseline)
- Access: +0% (ground floor)
- Building: +18% (pre-1900 + heritage)
- Combined: 1.18 multiplier
- A €35,000 base estimate becomes €41,300 before IVA

---

### Output

- **items**: ALL items from Phase 5 with adjustment fields added:
  - price_multiplier: The combined adjustment multiplier (e.g., 1.35)
  - adjusted_price: line_total × price_multiplier (calculated number)
  - adjustment_reason: Brief explanation in Spanish ("Barcelona centro +17%, sin ascensor 3ª planta +7%, edificio pre-1940 +12%")
- **adjustments_applied**: Array of objects explaining each factor:
  ```
  [
    {"factor": "regional", "percentage": 17, "reason": "Barcelona centro - costes laborales más altos de España"},
    {"factor": "access", "percentage": 7, "reason": "3ª planta sin ascensor - transporte manual de materiales"},
    {"factor": "building", "percentage": 12, "reason": "Edificio pre-1940 - dimensiones no estándar, posibles complicaciones"}
  ]
  ```
- **total_after_adjustments**: Sum of all adjusted_price values
- **iva_rate**: 0.21 (21% Spanish IVA for renovation work)
- **iva_amount**: total_after_adjustments × 0.21
- **final_total_with_iva**: total_after_adjustments + iva_amount (this is the contract price)

---

### Hygiene Rules

- **NO ITEM LOSS**: Count items in input (from Phase 5). Your output must have exactly that many items.
- **NO NULL ADJUSTMENTS**: Every item must have price_multiplier (number) and adjusted_price (number).
- **SAME MULTIPLIER IS FINE**: The adjustments are property-level, so all items typically get the same multiplier. That's correct - you're not adjusting individual items differently.
- **KEEP ALL EXISTING FIELDS**: Each item already has scope fields (Phase 1-2), scheduling fields (Phase 3-4), and pricing fields (Phase 5). You're adding adjustment fields while keeping everything else.
- **NUMBERS NOT STRINGS**: price_multiplier: 1.35 not "1.35". adjusted_price: 1890.00 not "1890.00".
- **SPANISH TEXT**: adjustment_reason and all notes in Spanish.

---

## PHASE 7: TIMELINE VALIDATION

### Role
**Construction Consultant** - An independent reviewer who looks at a schedule with fresh eyes after six phases of work. They've seen projects fail because someone scheduled tiling the day after waterproofing (membrane needs 48h cure) or painting right after new plaster (needs 2-3 weeks to dry). They catch the errors that seem obvious in hindsight but slip through when you're deep in the details. The Construction Consultant doesn't just check individual items - they look at the schedule as a living system where each piece affects others.

### Context to Examine (in depth)

Phase 7 has access to the richest context yet - six phases of accumulated work. Your job is to validate that the schedule from Phase 3 (with Phase 4's fixes applied) is physically executable. To do this well, you need to understand not just WHAT is scheduled but WHY it was scheduled that way.

---

#### EXAMINE: PHASE 3 OUTPUT - The Complete Schedule

This is your primary input. Phase 3 took all scope items and assigned each one a `phase_week`, `depends_on`, and `duration_hours`.

**What it contains:**
- Every item has `phase_week` (integer) - which week it's scheduled
- Every item has `depends_on` (array of item_ids) - what must complete before it starts
- Every item has `duration_hours` - how long the work takes
- `total_weeks` - the overall project duration
- `critical_path` - items that determine the total duration

**WHY IT MATTERS for timeline validation:**

The schedule is a promise. It says "if you start on Monday of week 1, you'll be done in N weeks." But schedules can be physically impossible - you can't tile on uncured waterproofing, you can't paint on wet plaster, you can't install sockets before cables are run. Your job is to find the impossible promises.

For each item in the schedule, you need to understand: when is it scheduled? what does it depend on? what depends on IT? Is the timing physically achievable?

---

#### EXAMINE: PHASE 4 OUTPUT - Sequencing Fixes Already Applied

Phase 4 reviewed logistics and may have flagged sequencing issues.

**What it contains:**
- `sequencing_fixes` - array of corrections Phase 4 identified
- `items_to_add` - any logistics items that were missing
- `verification_complete` - whether logistics review is done

**WHY IT MATTERS for timeline validation:**

Don't re-flag issues that Phase 4 already caught. If Phase 4 said "move ITEM_045 from week 5 to week 6 because waterproofing needs cure time", check if that fix was applied to the schedule you're validating. If the fix is in sequencing_fixes but the schedule still shows ITEM_045 in week 5, that's a problem - the fix wasn't applied.

Read through the sequencing_fixes array. For each fix, verify the item is now in the corrected week. If fixes are pending, note which ones still need to be applied.

---

#### EXAMINE: PHASES 1-2 REASONING_NOTES - Scope Complexity Indicators

Go back to what the Architect and PM wrote about the scope.

**What to look for:**
- Uncertainties: "unclear extent of electrical work", "may need to open walls"
- Complexity flags: "pre-1940 building with non-standard dimensions"
- Assumptions: "assumed existing substrate is sound"

**WHY IT MATTERS for timeline validation:**

Uncertainties in the scope translate to risks in the schedule. If Phase 1 noted "uncertain about waterproofing extent - scoped full replacement to be safe", the waterproofing items may take longer than estimated. If Phase 2 noted "added buffer items for unexpected MEP complications", those buffers should be in the schedule.

Items flagged as uncertain need more generous scheduling. If Phase 1 expressed doubt about electrical complexity and the schedule shows electrical work compressed into a single week, that's a risk worth flagging.

---

#### EXAMINE: PHASE 5-6 OUTPUTS - What's Being Built

The priced items tell you the actual quantities of work.

**What to look for:**
- Large quantities (50m² of tiling = many days of work)
- High-value items (likely complex installation)
- System breakdowns (how much electrical vs plumbing vs finishes)

**WHY IT MATTERS for timeline validation:**

Quantities validate durations. If there's 80m² of floor tiling and the schedule shows 8 hours, that's wrong - 80m² at ~5m²/day means at least 16 days, not 1 day. Use the quantities from Phase 5 to sanity-check the duration_hours from Phase 3.

Look at the subtotals_by_system from Phase 5. A project that's 40% finishes will have heavy tiling/painting weeks. A project that's 30% MEP will have substantial electrical/plumbing phases. Does the schedule reflect the weight of each system?

---

#### EXAMINE: TARGET PIR - Physical Property Constraints

Go back to the property analysis for constraints that affect scheduling.

**What to look for:**
- Floor level and access (affects material delivery timing)
- Room layout (rooms only accessible through other rooms)
- Number of bathrooms (if only one, can't demo it on day one)
- Building age (older buildings often reveal surprises)
- Ceiling heights (affects scaffold/access time)

**WHY IT MATTERS for timeline validation:**

Property-specific constraints create scheduling risks. If there's only one bathroom and it's being fully renovated, workers need facilities somewhere - the schedule can't have total bathroom demolition on day one. If the property is a 4th-floor walkup, material deliveries take longer - the schedule needs to account for this.

Think about physical reality: workers arrive, they need to move through the space, they need facilities, they need to get materials in and debris out. Does the schedule allow for this?

---

#### EXAMINE: LISTING DATA - Project Scale Context

Basic property data helps calibrate timeline expectations.

**What to look for:**
- Total area (m²) - larger properties take longer
- Room count - more rooms means more parallel work possible
- Location - access constraints, work hour restrictions

**WHY IT MATTERS for timeline validation:**

A 120m² apartment takes longer than a 60m² apartment, even with proportionally similar scope. More area means more material movement, more setup time, more cleanup time. The schedule should reflect property scale.

---

### Reasoning Questions

Don't follow a checklist mechanically. Instead, reason through the schedule using these PRINCIPLES:

**PRINCIPLE 1: Cure Times Are Physical Laws**

Certain materials MUST cure before dependent work can proceed:
- Waterproofing membrane: 24-48 hours minimum before tiles
- New plaster: 2-3 weeks before painting
- Concrete/screed: 28 days for full cure (though often walked on earlier)
- Grout: 24 hours before heavy traffic/sealing
- Silicone sealant: 24 hours before water exposure

For each item that involves curing:
- Find the item in the schedule
- Find the items that depend on it (directly or logically)
- Calculate the gap between them
- Is there enough time? If waterproofing is Thursday afternoon and tiling is Friday morning, that's NOT 48 hours.

**PRINCIPLE 2: Dependencies Must Be Respected**

Every item has `depends_on` - a list of items that must complete first.

For each item with dependencies:
- Is every dependency scheduled in an EARLIER week (or same week but clearly before)?
- If an item depends on something scheduled in a LATER week, that's impossible

For the dependency chain as a whole:
- Follow the critical path - does it make physical sense?
- Are there circular dependencies (A depends on B depends on A)?

**PRINCIPLE 3: Trades Must Follow Physical Sequence**

Certain work MUST happen in order:
- Demolition before installation in the same area
- First-fix MEP (cables, pipes in walls) before walls are closed
- Rough before finish
- Wet trades (plaster, screed) need drying before dry trades (paint, flooring)
- High work (ceilings, high walls) before floor finishes (so scaffolding doesn't damage new floors)

For each room:
- Find all items in that room
- Do they follow a sensible sequence? Demo → prep → install → finish?
- Are there any inversions (finishing scheduled before prep)?

**PRINCIPLE 4: Buffer for Complexity**

Complex or uncertain work needs schedule buffer.

For items flagged as uncertain in Phase 1-2:
- Is there buffer time after them?
- If electrical work is "uncertain extent", is there a contingency day?

For the schedule as a whole:
- Is there any buffer at the end for snagging?
- Is there any buffer in the middle for unexpected issues?
- A schedule with zero buffer is unrealistic

**PRINCIPLE 5: Parallel Work Must Be Physically Possible**

Multiple items scheduled in the same week implies parallel work.

For each week:
- How many items are scheduled?
- Can they physically happen simultaneously?
- In a 4m² bathroom, only one trade can work at a time - if 5 items are scheduled, they're sequential within the week, not parallel

For rooms that are access routes:
- If the hallway floor is being done, can workers access other rooms?
- If the only entrance is blocked, nothing else can happen

---

### Output

- **timeline_valid**: Boolean - is the schedule physically executable without modification?

- **critical_issues**: Array of problems that MUST be fixed before execution:
  ```
  [
    {
      "items": ["ITEM_045", "ITEM_052"], 
      "issue": "Descripción del problema en español",
      "principle_violated": "cure_time|dependency|trade_sequence|buffer|parallel",
      "fix": "Propuesta de corrección"
    }
  ]
  ```

- **warnings**: Array of concerns that aren't fatal but should be noted (tight timing, minimal buffer, complexity risks)

- **total_weeks**: Confirmed total duration after reviewing

- **feasibility_assessment**: Brief text assessment of the schedule's executability in Spanish

- **validation_notes**: Array of strings documenting your reasoning - what you checked, what concerns you found, what looks solid

---

### Hygiene Rules

- **DON'T MODIFY ITEMS**: This phase validates, it doesn't change the items. Flag issues in critical_issues with specific fix recommendations.
- **BE SPECIFIC**: Don't say "sequencing issue" - say which items, which principle is violated, and what the fix should be.
- **REFERENCE ITEM_IDS**: Always use specific item_ids when flagging issues so fixes can be targeted.
- **SPANISH TEXT**: All issue descriptions, fixes, and validation_notes in Spanish.
- **NO ANECDOTAL WEEKS**: Don't assume "week 1" or "week 10" - reason about the schedule as it actually is.

---

## PHASE 8: ENERGY COMPLIANCE

### Role
**Energy Consultant** - A professional who understands Spanish energy regulations (CTE DB-HE - Código Técnico de la Edificación, Documento Básico de Ahorro de Energía) and knows when renovations trigger compliance requirements. Not every renovation needs energy upgrades, but significant works often do - and missing this can mean failed inspections, certificates that can't be issued, or retrofit costs later. The Energy Consultant also understands that beyond compliance, energy performance increasingly affects commercial viability - buyers care about ratings and running costs.

### Context to Examine (in depth)

Phase 8 has access to seven phases of accumulated work plus all source context. Your job is to assess whether the scope meets regulatory requirements AND whether it achieves the energy performance the market expects.

---

#### EXAMINE: TARGET PIR - Current Energy State

Go to the TARGET PIR and examine everything related to energy.

**What to look for in building_profile:**
- `energy_rating`: The current CEE (Certificado de Eficiencia Energética). E, F, G are poor. D is mediocre. C and above are decent.
- `year_built`: Pre-2006 buildings were built before the CTE existed. They often have no insulation, single glazing, inefficient systems. Post-2006 buildings should have some energy features.
- Building type: Apartments in blocks share walls (less envelope exposure). Chalets have more envelope (more heat loss).
- Floor level: Top floors lose heat through the roof. Ground floors may have uninsulated slab.

**What to look for in systems mentioned:**
- Heating: What type? Old boiler, electric radiators, nothing? What age?
- Cooling: AC present? What type? Split systems, central?
- Hot water: Connected to heating? Separate water heater? Solar thermal?
- Windows: Single glazing, double glazing, age, material (aluminum without thermal break, PVC with thermal break)?

**WHY IT MATTERS for energy compliance:**

The current state is your baseline. A property that's already D-rated with modern windows is very different from an F-rated property with single glazing. The gap between current state and CTE requirements determines what's mandatory. The gap between current state and bracket expectations determines what's commercially sensible.

If the PIR flagged "instalación de calefacción original de 1975" or "ventanas de aluminio sin rotura de puente térmico", these are energy triggers that may need addressing.

---

#### EXAMINE: PHASE 1 SCOPE - Envelope Interventions

Go through all items from Phase 1 and find everything that touches the building envelope.

**What counts as envelope:**
- Windows and doors to exterior
- Exterior walls (facade)
- Roof/ceiling to unheated space
- Floor to unheated space (garage, crawl space)
- Any element that separates heated interior from unheated exterior

**What to count:**
- How many windows are being replaced vs total windows?
- Is any facade work being done?
- Is any roof/ceiling insulation being added?
- Is any floor insulation being added?

**WHY IT MATTERS for energy compliance:**

The CTE has a "25% threshold" principle. If you're replacing/renovating more than 25% of a particular envelope element, you may need to bring ALL of that element type up to current CTE U-value requirements. So if you're replacing 3 of 8 windows (37.5%), all 3 new windows must meet current CTE standards for that climate zone.

For each envelope item, ask: Does this push us over a threshold? What's the cumulative percentage of this envelope type being touched?

---

#### EXAMINE: PHASE 1 REASONING_NOTES - Design Decisions About Energy

Go back to what the Architect wrote about energy-related decisions.

**What to look for:**
- Explicit decisions: "Kept existing windows per comunidad restrictions"
- Trade-offs noted: "Could upgrade to triple glazing but bracket only expects double"
- Assumptions: "Assumed existing heating adequate"
- Deferred items: "Energy improvements not in scope - cosmetic focus"

**WHY IT MATTERS for energy compliance:**

Understanding WHY certain energy decisions were made helps you assess if they were correct. If the architect kept existing single-glazed windows because the comunidad controls the facade, that's a valid constraint but you should note it affects energy performance. If the architect didn't include heating upgrade and the bracket expects modern heating, that's a potential gap.

---

#### EXAMINE: PHASE 5-6 OUTPUTS - Energy Systems Being Changed

Look at the priced BOQ for any energy-related items.

**What to look for:**
- Heating items: New boiler, radiators, underfloor heating, heat pump
- Cooling items: AC installation, split systems
- Hot water items: New water heater, solar thermal
- Window items: New windows with specifications
- Insulation items: Any wall, floor, or ceiling insulation

**WHY IT MATTERS for energy compliance:**

New systems must meet current efficiency standards. A new gas boiler must be condensing type (>92% efficiency). New windows must meet U-value requirements for the climate zone. New AC must meet EER/SEER requirements. Check that the items in scope will actually achieve compliance - not just "new boiler" but "condensing boiler meeting current regs".

---

#### EXAMINE: PHASE 7 OUTPUT - Timeline Implications

Phase 7 validated the schedule. Look for any energy-related flags.

**What to look for:**
- Were any energy items flagged for scheduling issues?
- Is there coordination needed between energy systems and other work?

**WHY IT MATTERS for energy compliance:**

Some energy work has coordination requirements. Underfloor heating must be installed before floor finishes. Boiler replacement may need gas certification before use. If Phase 7 flagged issues with energy item scheduling, those affect feasibility.

---

#### EXAMINE: BRACKET PIR - Market Energy Expectations

Go to the BRACKET PIR and understand what the market expects.

**What to look for:**
- `typical_features`: Does the bracket mention AC, efficient heating, modern windows?
- `common_materials`: Do window specs mention double glazing, thermal break?
- `what_defines_this_bracket`: Are energy features a differentiator?

**WHY IT MATTERS for energy compliance:**

Beyond legal compliance, there's commercial compliance - meeting what the market expects. If the bracket shows comparable properties have AC and efficient heating, a property without these will underperform. Even if not legally required, missing expected energy features is a commercial gap.

---

#### EXAMINE: LISTING DATA - Climate Zone Context

Check the location for climate implications.

**What to look for:**
- City/region: Spain has different CTE climate zones (A-E for winter, 1-4 for summer)
- Coastal vs inland: Coastal is milder, inland has more extreme temperatures
- Altitude: Higher altitude means colder winters

**WHY IT MATTERS for energy compliance:**

CTE U-value requirements vary by climate zone. Windows in Sevilla (zone B4) have different requirements than windows in Madrid (zone D3). Heating is more critical in northern zones, cooling more critical in southern zones. Your compliance assessment must consider the actual climate zone.

---

### Reasoning Questions

Don't apply thresholds mechanically. Reason through energy compliance using these PRINCIPLES:

**PRINCIPLE 1: Thresholds Trigger Requirements**

Spanish energy regulations have threshold rules:
- >25% of envelope element being renovated → may trigger upgrade requirements for that element
- Major renovation (cost exceeding certain % of building value) → may trigger broader energy requirements
- Change of use → triggers full compliance
- New systems → must meet current efficiency standards regardless of threshold

For each envelope element type (windows, facade, roof, floor):
- What percentage is being touched?
- If >25%, are the new elements CTE-compliant?
- If <25%, no legal requirement but consider commercial impact

**PRINCIPLE 2: New Systems Must Meet Current Standards**

Any NEW energy system must meet current efficiency requirements:
- Gas boilers: Must be condensing type (ErP Directive compliant)
- Heat pumps: Must meet SCOP/SEER requirements
- AC: Must meet EER requirements
- Windows: Must meet U-value for climate zone
- Insulation: Must meet R-value requirements

For each new system in scope:
- Is it specified to meet current standards?
- If just "new boiler" without specs, is it clear it will be condensing?

**PRINCIPLE 3: Commercial Expectations May Exceed Legal Requirements**

What's legally required may be less than what the market expects.

For the property:
- What's the current rating? Would improving it add value?
- What does the bracket expect? Does the scope deliver that?
- Are there easy wins being missed? (Adding AC where bracket expects it)

**PRINCIPLE 4: Energy Rating Projection**

Try to estimate the impact of the scope on energy rating:
- Starting rating from TARGET PIR
- New windows typically improve rating by 0.5-1 letter
- Efficient heating can improve by 0.5-1 letter
- Insulation can improve by 1+ letter
- Combined improvements can move from F to C

Is the projected rating appropriate for the bracket?

---

### Output

- **energy_compliant**: Boolean - does the scope meet regulatory requirements for this scope of work?

- **current_rating**: The property's current energy rating from TARGET PIR (e.g., "E", "F", or "Unknown")

- **projected_rating**: Estimated rating after renovation (e.g., "D" or "C-D range")

- **regulatory_requirements**: Array of CTE requirements triggered by this scope:
  ```
  [
    {
      "requirement": "Descripción del requisito en español",
      "trigger": "What in the scope triggered this",
      "status": "met|unmet|unclear",
      "notes": "Explanation"
    }
  ]
  ```

- **recommendations**: Array of energy improvements that would add value even if not legally required:
  ```
  [
    {
      "recommendation": "Descripción en español",
      "rationale": "Why this would add value",
      "estimated_impact": "Effect on rating or running costs"
    }
  ]
  ```

- **compliance_notes**: Array of strings documenting your reasoning - what you assessed, what thresholds you calculated, what you concluded

---

### Hygiene Rules

- **DON'T ADD ITEMS**: This phase assesses compliance, it doesn't modify scope. If improvements are needed, flag them in recommendations.
- **BE PRACTICAL**: Not every property needs to become A-rated. Assess what's required and what's commercially sensible for the bracket.
- **SPANISH TEXT**: All requirements, recommendations, and compliance_notes in Spanish.
- **REFERENCE SPECIFIC ITEMS**: When discussing scope items, reference their item_ids.
- **CITE CLIMATE ZONE**: Make clear what climate zone assumptions you're using.

---

## PHASE 9: SANITY CHECK

### Role
**Senior Estimator / Commercial Director** - Someone who has seen thousands of estimates and knows immediately when something looks "off". They don't check every line item - they look at the big picture. Is the total reasonable? Is the cost per m² in the right ballpark? Are there any obvious red flags? The Senior Estimator has pattern recognition from years of experience - they know what a "normal" renovation looks like and can spot anomalies instantly.

### Context to Examine (in depth)

Phase 9 has the richest context of any phase - eight phases of accumulated work. Your job is to step back from the details and ask: does this estimate make sense as a whole? You're the last line of defense before this estimate is presented.

---

#### EXAMINE: PHASE 6 OUTPUT - The Final Priced BOQ

This is your primary input - the complete estimate with all adjustments applied.

**What to look for:**
- `final_total_with_iva`: The bottom-line number
- `total_after_adjustments`: The pre-IVA total
- `adjustments_applied`: What regional/building factors were applied
- `items`: The complete list with all fields filled
- Count of items: How many discrete items are there?

**WHY IT MATTERS for sanity check:**

The total is what the client sees. If it's wildly wrong - too high, too low, missing major items - this is your last chance to catch it. A renovation estimate that's 50% off reality damages credibility and trust.

Count the items. A full apartment renovation typically has 60-100+ items. If you see 20 items for "complete renovation", something is probably missing. If you see 200 items, maybe there's duplication.

---

#### EXAMINE: PHASE 5 OUTPUT - System Breakdowns

Phase 5 calculated subtotals by system before adjustments were applied.

**What to look for:**
- `subtotals_by_system`: Breakdown by demolition, plumbing, electrical, finishes, hvac, carpentry, ffe, logistics
- Relative proportions of each system
- Any system that seems outsized or undersized

**WHY IT MATTERS for sanity check:**

Proportions reveal problems. In a typical renovation:
- Demolition should be 5-10% of total - it's necessary but not the bulk of cost
- Finishes (tiling, painting, flooring) should be 30-40% - this is where most visible work happens
- Kitchen/bathroom fixtures: 20-30% - these are expensive rooms
- MEP (electrical, plumbing, HVAC): 15-25% - essential infrastructure
- Logistics: 5-10% - protection, skip hire, cleanup

If demolition is 30%, something is probably wrong. If MEP is 2% but the scope includes full rewire, something is probably wrong.

---

#### EXAMINE: ALL PRIOR PHASE REASONING_NOTES - The Story of This Estimate

Go back through the reasoning from all prior phases.

**Phase 1 reasoning_notes**: What was the architect's intent? What trade-offs did they make? What were they uncertain about?

**Phase 2 verification_notes**: What did the PM catch? What was added? What was confirmed?

**Phase 3-4 notes**: Were there scheduling or logistics complexities?

**Phase 5 pricing_notes**: Were there any items that were hard to price? Any adaptations?

**Phase 6 adjustment_notes**: Why were certain multipliers applied?

**Phase 7 validation_notes**: Were there timeline concerns?

**Phase 8 compliance_notes**: Were there energy compliance issues?

**WHY IT MATTERS for sanity check:**

The reasoning trail tells you where confidence is high and where it's low. If Phase 1 noted "uncertain about electrical extent" and Phase 5 noted "used generic code for electrical - exact spec unclear", that's a confidence gap. If every phase noted "straightforward scope, standard finishes", confidence should be high.

---

#### EXAMINE: TARGET PIR - What This Property Actually Is

Go back to the property analysis.

**What to look for:**
- Property condition overall: How much work does it actually need?
- Room count and types: Does scope cover all rooms?
- Triggers identified: Are all high/critical triggers addressed in scope?
- Building age and complexity: Does the estimate reflect complexity?

**WHY IT MATTERS for sanity check:**

The estimate should match the property. A property described as "needs complete renovation" should have a substantial estimate. A property described as "cosmetic refresh only" should have a lighter estimate. If the PIR screams "major work needed" but the estimate is €300/m², there's a mismatch.

---

#### EXAMINE: BRACKET PIR - What The Market Expects

Go to the BRACKET PIR for market context.

**What to look for:**
- What finish level defines this bracket?
- What features are expected?
- What's the competitive landscape?

**WHY IT MATTERS for sanity check:**

The estimate should deliver what the bracket expects. If the bracket is "fair_market" with modern finishes, the estimate should fund that level. If the bracket expects quartz countertops but the estimate has laminate, there's a gap.

---

#### EXAMINE: LISTING DATA - Property Economics

Basic property data for economic context.

**What to look for:**
- `area`: Total m² for cost/m² calculation
- `price`: Property purchase price for renovation ratio
- `location`: Regional context

**WHY IT MATTERS for sanity check:**

Cost per m² is the universal sanity metric. It lets you compare this estimate to market norms regardless of property size. Renovation cost as % of property price tells you if the investment makes sense.

---

### Reasoning Questions

Don't apply benchmarks mechanically. Reason through the estimate using these PRINCIPLES:

**PRINCIPLE 1: Cost Per m² Should Match Scope Intensity**

Calculate: final_total_with_iva ÷ area_m²

Benchmark ranges for Spanish residential renovation:
- Light refresh (paint, minor updates): €200-400/m²
- Medium renovation (kitchen, bathroom, finishes): €600-900/m²
- Full gut renovation (everything): €900-1,200/m²
- High-end / complex: €1,200-1,800/m²

For the property:
- What's the calculated €/m²?
- What scope intensity does the PIR and Phase 1 scope suggest?
- Do they match?

If the scope description says "full renovation" but cost is €300/m², either the scope isn't really "full" or it's underpriced. If the scope says "cosmetic refresh" but cost is €1,000/m², either it's more than cosmetic or it's overpriced.

**PRINCIPLE 2: System Proportions Should Make Sense**

For each system in subtotals_by_system:
- What percentage of total is it?
- Does that percentage match the scope?

If finishes are 60% of total and MEP is 5%, ask: is this really a finish-heavy scope with minimal electrical/plumbing? Or is MEP underpriced?

If demolition is 25% of total, ask: is there really that much demolition? Or are items being double-counted or overpriced?

**PRINCIPLE 3: Item Distribution Should Be Even**

Look at the range of item values.

For each item:
- Is any single item more than 15-20% of total? That's unusual unless it's something like a complete kitchen fit-out.
- Are there many items at exactly round numbers (€1,000, €5,000)? That suggests estimates rather than calculated prices.
- Are there many items at suspiciously precise numbers (€1,247.83)? That might be spurious precision.

For the collection as a whole:
- Is there a sensible distribution from small items (€50-200) through medium (€500-2000) to large (€3000+)?
- Or is everything clustered in one range?

**PRINCIPLE 4: Renovation vs Property Value Should Be Rational**

Calculate: final_total_with_iva ÷ property_price × 100

For most properties:
- 10-20%: Normal renovation investment
- 20-35%: Substantial renovation
- 35-50%: Major transformation
- >50%: Unusual - needs justification (maybe a total ruin being rescued?)

If renovation is 75% of property value, is that intentional? Does the scope justify it?

**PRINCIPLE 5: Confidence Reflects Uncertainty**

Think about where uncertainty exists:

- Phase 1 had uncertainties about scope → Lower confidence
- Phase 5 had to adapt many prices → Lower confidence
- All phases noted straightforward work → Higher confidence
- Property is pre-1940 with unknown hidden conditions → Lower confidence

What's your overall confidence in this estimate?

---

### Output

- **sanity_check_passed**: Boolean - is this estimate reasonable enough to present?

- **total_cost**: The final total with IVA (copy from Phase 6)

- **cost_per_sqm**: Calculated €/m²

- **cost_per_sqm_assessment**: One of "low", "typical", "high", "very_high" with explanation in Spanish

- **scope_intensity**: One of "light_refresh", "medium_renovation", "full_gut", "high_end" based on your assessment

- **proportion_check**: Object with assessment of system proportions:
  ```
  {
    "assessment": "balanced|imbalanced",
    "notes": "Explicación en español",
    "outliers": ["system_name if any are unusual"]
  }
  ```

- **red_flags**: Array of concerns found:
  ```
  [
    {
      "flag": "Descripción del problema",
      "severity": "high|medium|low",
      "recommendation": "Qué hacer al respecto"
    }
  ]
  ```

- **confidence_score**: Integer 0-100 representing confidence in the estimate

- **recommendations**: Array of suggestions for improvement or review

- **sanity_notes**: Array of strings documenting your reasoning - what you checked, what looked normal, what raised questions

---

### Hygiene Rules

- **DON'T MODIFY**: This is a review, not a correction phase. Flag issues, don't fix them.
- **BE HONEST**: If something looks wrong, flag it clearly. A false-positive is better than a missed problem.
- **GIVE CONTEXT**: Don't say "cost seems high" - say "€1,400/m² is high for a medium renovation in Valencia - typical would be €700-900/m²"
- **SPANISH TEXT**: All assessments, notes, and explanations in Spanish.
- **JUSTIFY CONFIDENCE**: If confidence_score is below 70, explain why in sanity_notes.

---

## PHASE 10: RENDERING PROMPTS

### Role
**Visual Designer / Art Director** - Someone who can translate renovation scope into visual transformation prompts. They understand what an AI image generator needs to create compelling before/after visualizations. They know that "renovate bathroom" isn't a useful prompt - you need specific visual directions that describe colors, materials, textures, lighting, and mood. The Visual Designer bridges the technical scope (what's being done) with the visual outcome (what it will look like).

### Context to Examine (in depth)

Phase 10 has access to nine phases of accumulated work plus all source context. Your job is to translate the scope into visual transformation prompts that an AI image generator can use to create realistic before/after renderings.

---

#### EXAMINE: TARGET PIR - Visual State of Each Room

Go to the TARGET PIR and examine each room's current visual state.

**What to look for in each room:**
- Floor: What material? What color? What condition? (terrazzo, ceramic tile, parquet, laminate)
- Walls: What treatment? What color? Any patterns? (paint, wallpaper, tile, exposed brick)
- Fixtures: What style? What era? What material? (brass, chrome, white porcelain, wood)
- Lighting: What type? What fixtures? Natural light direction?
- Overall feel: What era does this room feel like? 1970s? 1990s? 2010s?

**WHY IT MATTERS for rendering prompts:**

The "before" state is what we're transforming. If you don't understand exactly what's there now, you can't describe the transformation. The PIR should give you the visual vocabulary - "brown terrazzo floor", "cream wall tiles with decorative border", "original brass fixtures". These specific descriptions become the "from" in your transformation prompt.

---

#### EXAMINE: BRACKET PIR - Target Visual Aesthetic

Go to the BRACKET PIR and understand the target visual style.

**What to look for:**
- `design_era`: What era defines this bracket? "Modern 2018-2022" suggests contemporary minimalism. "Classic updated" suggests traditional with modern conveniences.
- `common_materials`: What specific materials do comparable properties have? Porcelain tile, quartz counters, floating vanities - these become your "to" specifications.
- `typical_features`: What visual elements define success? LED lighting, frameless glass, integrated appliances.
- `what_defines_this_bracket`: How does it differ from cheaper? This tells you what visual upgrades matter.

**WHY IT MATTERS for rendering prompts:**

The "after" state comes from the bracket. You're not inventing a look - you're visualizing what properties at this price point look like when renovated. The bracket PIR gives you the visual target.

---

#### EXAMINE: PHASE 1 SCOPE - What's Actually Changing

Go through the Phase 1 items and understand exactly what visual changes are in scope.

**What to look for:**
- For each room, list the items that affect visual appearance
- Distinguish between visible changes (new tiles, new paint) and invisible changes (rewiring, new pipes)
- Note what is NOT changing - elements that should stay the same in the "after"

**WHY IT MATTERS for rendering prompts:**

The rendering must match the scope. If the scope doesn't include new bedroom flooring, the "after" render should show the existing bedroom floor. If the scope includes painting but not new tiles in a bathroom, the walls should be freshly painted but the same tiles should be visible.

This is critical - an "after" render that shows changes not in scope creates false expectations.

---

#### EXAMINE: PHASE 1 REASONING_NOTES - Design Intent

Go back to what the Architect wrote about design decisions.

**What to look for:**
- Style notes: "Going for Scandinavian minimal" or "Maintaining classic character"
- Color decisions: "Light and bright throughout" or "Warm neutral palette"
- Trade-offs: "Kept original terrazzo as a feature" or "Budget focused on kitchen"
- Feature priorities: "Bathroom is the hero room" or "Open kitchen as focal point"

**WHY IT MATTERS for rendering prompts:**

The architect had a vision. Your rendering prompts should reflect that vision. If Phase 1 noted "maintaining original character while updating functionality", your prompts should show modernized spaces that still feel connected to the original.

---

#### EXAMINE: PHASE 5-6 OUTPUTS - Material Specifications

Look at the priced items for specific material details.

**What to look for:**
- Tile specifications: Size, finish (matt/gloss), color, brand if mentioned
- Paint colors: Any specific colors or just "white"?
- Fixture details: What specific items were priced?
- Kitchen/bathroom specifics: Cabinet style, countertop material

**WHY IT MATTERS for rendering prompts:**

Phase 5 may have specific material references that inform visuals. If the priced item says "porcelanato rectificado 60x60 gris claro", that's more specific than just "new tiles". Use the specificity from pricing to inform your visual descriptions.

---

#### EXAMINE: PHASE 9 OUTPUT - Overall Assessment

Check Phase 9's sanity assessment for context.

**What to look for:**
- `scope_intensity`: Light refresh? Full gut? This affects how dramatic transformations should be.
- Any red flags about scope completeness

**WHY IT MATTERS for rendering prompts:**

If this is a "light refresh", transformations should be subtle - fresh paint, new fixtures, same layout. If it's a "full gut", transformations should be dramatic - everything new. The rendering intensity should match the scope intensity.

---

### Reasoning Questions

Don't create prompts mechanically. Reason through the visual transformation using these PRINCIPLES:

**PRINCIPLE 1: Before → After Must Match Scope**

For each room:
- What elements are being changed according to the scope?
- What elements are staying the same?
- List the specific transformations: "old → new" for each element

Don't invent changes. If the scope doesn't include new windows, the windows should look the same in before and after (maybe cleaner, but same style).

**PRINCIPLE 2: Describe Visually, Not Technically**

Rendering prompts are for image generation. Describe what things LOOK like:
- BAD: "Install 60x60 porcelain tile"
- GOOD: "Large format light grey tiles with subtle texture, minimal grout lines, matt finish"

Think about: color, texture, sheen, pattern, scale, light reflection. These are what an image generator needs.

**PRINCIPLE 3: Maintain Spatial Consistency**

The "after" should be recognizably the same space as the "before":
- Same room dimensions
- Same window positions
- Same door locations
- Same basic layout (unless scope changes it)

Only change what the scope changes. A viewer should be able to match "before" and "after" as the same room.

**PRINCIPLE 4: Mood Transformation Matters**

Beyond individual elements, describe the overall mood shift:
- "Dated and tired → Fresh and contemporary"
- "Dark and cramped → Light and spacious"
- "Cold and institutional → Warm and inviting"

This helps the image generator understand the emotional transformation, not just the material changes.

**PRINCIPLE 5: Identify the Hero Room**

Which room has the most dramatic transformation? This becomes the "hero" image for marketing:
- Usually kitchen or bathroom (highest visual impact)
- Should be a room with significant scope items
- Should showcase the bracket's defining features

---

### Output

- **room_prompts**: Array of transformation prompts, one per room with visual changes. For each room:
  - `room_id`: The canonical room_id
  - `room_name`: Human-readable name in Spanish
  - `current_description`: Visual description of the room as it is now (in English for image generator)
  - `transformation_prompt`: Detailed prompt describing the visual transformation (in English for image generator)
  - `key_changes`: Array of the main visual elements being changed
  - `unchanged_elements`: Array of elements that should remain the same

- **hero_room_id**: The room_id of the most visually dramatic transformation

- **overall_style**: Brief description of the target aesthetic across all rooms (e.g., "Contemporary Scandinavian with warm wood accents and clean lines")

- **color_palette**: Array of main colors across the renovation (e.g., ["white", "light grey", "warm oak", "chrome accents"])

- **design_notes**: Array of strings documenting your visual reasoning - why certain transformations, what aesthetic choices, how it connects to the bracket

---

### Hygiene Rules

- **MATCH THE SCOPE**: Only describe changes that are actually in the scope. Verify each transformation against Phase 1 items.
- **BE VISUAL**: Describe appearance, not technical specs. Colors, textures, finishes, light, mood.
- **BE SPECIFIC**: "Modern bathroom" is too vague. "White large-format tiles, floating oak vanity, frameless glass shower, black hardware" is specific.
- **ENGLISH PROMPTS**: current_description and transformation_prompt in English (for image generators). room_name and design_notes in Spanish.
- **EVERY CANONICAL ROOM**: Generate prompts for every canonical room that has scope items with visual impact.

---

## PHASE 11: VIEWING GUIDE

### Role
**Property Advisor** - Someone helping a buyer prepare for a property viewing. They translate the ten phases of technical analysis into practical viewing guidance that a non-expert buyer can follow in a real visit. They know that a viewing is precious time - you only get one first impression, agents are watching, and you need to gather critical information efficiently. The Property Advisor creates a customized checklist that reflects THIS property's specific issues and THIS renovation's specific assumptions.

### Context to Examine (in depth)

Phase 11 has access to all ten prior phases of work. Your job is to translate this technical depth into practical viewing actions. The viewing guide should help a buyer verify the assumptions behind the renovation estimate.

---

#### EXAMINE: TARGET PIR - Known Issues and Triggers

Go to the TARGET PIR and examine every trigger and issue identified.

**What to look for:**
- All triggers with their urgency levels (critical, high, medium, low)
- Evidence cited for each trigger
- Room-specific issues in condition_summary
- Building profile issues (age, systems, structure)

**WHY IT MATTERS for viewing guide:**

Each trigger represents something the analysis identified that needs attention. The buyer should verify these triggers exist and assess their severity in person. A photo might show "possible damp in corner" but the buyer can smell damp, feel soft plaster, see the actual extent.

For each trigger:
- What should the buyer look for to verify it exists?
- What would make it better or worse than the analysis suggests?
- What questions should they ask about it?

---

#### EXAMINE: PHASE 1-2 SCOPE - What's Being Renovated

Go through the scope items and understand what the renovation assumes.

**What to look for:**
- Items that assume certain existing conditions ("repaint existing plaster" assumes plaster is sound)
- Items that were explicitly excluded (anything NOT in scope needs to be checked)
- Items flagged as uncertain in reasoning_notes

**WHY IT MATTERS for viewing guide:**

The scope is based on photos and analysis. It may have assumed things that aren't true. If the scope assumes walls are in good condition but they're actually crumbling, the estimate is wrong. The buyer needs to verify the assumptions.

For each major scope item:
- What condition does it assume?
- What should the buyer check to verify that assumption?
- What would change the scope if found to be different?

---

#### EXAMINE: PHASE 1-2 REASONING_NOTES - Uncertainties and Assumptions

Go back to what the Architect and PM wrote about uncertainties.

**What to look for:**
- "Unclear if..." statements
- "Assumed..." statements
- "May need to open walls to verify..."
- Anything flagged as uncertain or to-be-confirmed

**WHY IT MATTERS for viewing guide:**

Uncertainties in the scope are verification priorities for the viewing. If Phase 1 noted "uncertain about waterproofing condition behind tiles", the buyer should pay extra attention to signs of water damage in that area.

---

#### EXAMINE: PHASE 7-8 OUTPUTS - Validation Concerns

Check what the validation phases flagged.

**What to look for:**
- Phase 7: Any timeline concerns that relate to property access or complexity
- Phase 8: Energy compliance issues, current rating, improvement recommendations

**WHY IT MATTERS for viewing guide:**

If Phase 7 flagged "single bathroom creates access constraint", the buyer should note how this affects practical renovation. If Phase 8 noted "current rating E, window upgrades recommended", the buyer should pay attention to window condition.

---

#### EXAMINE: PHASE 9 OUTPUT - Confidence and Flags

Check the sanity check results.

**What to look for:**
- confidence_score: Is this a high-confidence estimate or uncertain?
- red_flags: What concerns were raised?
- sanity_notes: What reasoning led to the assessment?

**WHY IT MATTERS for viewing guide:**

Low confidence means more verification needed. Red flags become viewing priorities. If Phase 9 noted "MEP proportion unusually low - verify extent of electrical work needed", the buyer should check electrical carefully.

---

#### EXAMINE: LISTING DATA - What to Verify Against Listing

Check the original listing data.

**What to look for:**
- Listed area (m²) - does the property feel that size?
- Room count - are all rooms accessible?
- Features mentioned - terrace, storage, parking, balcony
- Location claims - floor level, views, orientation

**WHY IT MATTERS for viewing guide:**

Listings sometimes exaggerate or omit. The buyer should verify the basics match reality.

---

### Reasoning Questions

Don't create a generic viewing checklist. Reason through THIS property's specific needs using these PRINCIPLES:

**PRINCIPLE 1: Every Trigger Becomes a Verification Point**

For each trigger in the TARGET PIR:
- What sensory check can verify it? (sight, smell, touch, sound)
- What question should be asked about it?
- What would change the renovation plan if it's worse than thought?

High-urgency triggers are high-priority verifications. Critical triggers are must-verify items.

**PRINCIPLE 2: Every Assumption Becomes a Check**

For each major assumption in the scope:
- How can the buyer verify it's true?
- What signs would indicate it's false?

If scope assumes "existing flooring in good condition to remain", the buyer should check that flooring carefully.

**PRINCIPLE 3: Sensory → Inspection → Questions**

Structure the viewing in three modes:

Mode 1 - Sensory (first impressions):
- What do you sense when you enter? Smell, light, sound, feel
- Building context: Common areas, neighbors, lift, street

Mode 2 - Inspection (room by room):
- For each canonical room, what specific checks apply?
- These should be driven by the triggers and scope for that room

Mode 3 - Questions (for the agent):
- Spanish property-specific questions (comunidad, ITE, derramas, cédula)
- Questions arising from the PIR triggers
- Questions about building history and neighbors

**PRINCIPLE 4: Prioritize by Impact**

Not everything can be checked in a 20-30 minute viewing. Prioritize:
- HIGH: Things that would significantly change the renovation estimate
- MEDIUM: Things that would moderately affect scope or cost
- LOW: Nice to know but not critical

A critical structural issue is HIGH priority. Paint color preference is LOW priority.

**PRINCIPLE 5: Photo Documentation**

The buyer should photograph things they can't remember or need to review:
- Every trigger mentioned in PIR
- Any condition they're uncertain about
- Systems (electrical panel, boiler, windows)
- Views and light at that time of day

---

### Output

- **address**: Property address (from LISTING DATA)

- **total_duration_minutes**: Suggested viewing duration based on property complexity

- **mode1_sensory**: Array of first-impression checks:
  ```
  [
    {
      "id": "S1",
      "action": "Action in Spanish",
      "detail": "What to notice/check",
      "why": "Why this matters for this property"
    }
  ]
  ```
  These should be property-specific, derived from PIR triggers and building context.

- **mode2_inspect**: Array of room-by-room inspections. For EACH canonical room:
  ```
  [
    {
      "room_id": "canonical_id",
      "room_name": "Spanish name",
      "checks": ["Check 1 in Spanish", "Check 2 in Spanish", ...],
      "priority_items": ["Highest priority checks for this room"],
      "photos_to_take": ["What to photograph in this room"]
    }
  ]
  ```
  Checks should be derived from that room's triggers and scope items.

- **mode3_ask**: Array of questions for the agent:
  ```
  [
    {
      "id": "Q1",
      "question": "Question in Spanish",
      "context": "Why this question matters in English",
      "relates_to": "Which trigger or concern this addresses"
    }
  ]
  ```

- **key_verification_points**: Array of the most critical things to verify, derived from PIR triggers and scope assumptions

- **photo_checklist**: Array of what to photograph, with reason for each

- **guide_notes**: Array of strings documenting your reasoning - why certain checks are prioritized, what the viewing should focus on

---

### Hygiene Rules

- **PROPERTY-SPECIFIC**: Every check should relate to something in the PIR, scope, or analysis. No generic advice.
- **PRACTICAL DURATION**: The guide must fit in a real viewing (20-30 minutes). Prioritize ruthlessly.
- **NON-TECHNICAL LANGUAGE**: Explain in terms a non-expert buyer understands. Not "check the DPC" but "look for damp marks at the base of walls".
- **SPANISH CONTEXT**: Questions in Spanish using correct terms (comunidad, derrama, ITE, cédula de habitabilidad).
- **ACTIONABLE**: Each check should tell the buyer exactly what to DO and what to LOOK FOR.

---

## PROMPT WRITING PRINCIPLES

1. **Ask questions, don't give checklists.**
   
   BAD: "[ ] Check for waterproofing before tiles"
   
   GOOD: "If tiles are being installed in wet areas, where is the waterproofing? Look for it. If you can't find it, that's a gap - the tiles will fail without it."
   
   Questions force reasoning. Checklists encourage mechanical ticking.

2. **Explain WHY context matters for THIS task.**
   
   BAD: "The TARGET PIR contains room dimensions."
   
   GOOD: "The TARGET PIR tells you room dimensions - when you see bano_1 is 2.1m × 2.0m, that 4.2m² becomes your floor tile quantity. But also think - if you're tiling walls up to 2.1m around a 6.2m perimeter, that's another 13m² of wall tile minus the door opening..."

3. **Make reasoning iterative.**
   
   The model should examine its own output. "Look at the items you have for this bathroom. Now ask yourself: if I were a contractor reading this, would I know exactly what to do? Or would I call you with questions?"
   
   This is like editing your own work - review, find gaps, improve.

4. **Each phase examines ALL prior context and reasoning.**
   
   Phase 5 doesn't just see "items from Phase 4" - it sees WHY Phase 1 created each item (the reasoning_notes), WHAT Phase 2 verified, HOW Phase 3 scheduled them. This cumulative understanding makes better decisions.

5. **Examples flow within explanations, not as separate blocks.**
   
   BAD: 
   ```
   EXAMPLE:
   Item: Alicatado suelo baño
   Step 1: Find BCCA code
   Step 2: Read price
   ```
   
   GOOD: "...so when you're pricing that bathroom floor tile, you're looking at the PIR to see the room is 2.1×2.0m, searching the BCCA for 'alicatado porcelánico' which might give you 09ACE00130 at €32/m², and computing 4.2 × 32 = €134..."

6. **Separate reasoning guidance from output specification.**
   
   The reasoning sections are expansive, question-based, flowing.
   The output sections are precise, schema-defined, no ambiguity.
   
   Don't let reasoning instructions muddy the output format. Keep "what to think about" separate from "what to output".

7. **Trust the model's intelligence.**
   
   It's a flagship reasoning model. Give it understanding and it figures out execution. Give it recipes and it follows them mechanically, missing edge cases.
   
   Talk to it like a smart colleague who needs context, not like a junior who needs step-by-step instructions.
