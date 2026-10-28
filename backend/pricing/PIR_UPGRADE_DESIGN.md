# PIR Generation Upgrade Design Document
## Version 0.6 - Target-Relative Analysis with Rich Room Guidance

**Date**: 2026-01-15
**Author**: AI Assistant
**Status**: Design Phase

---

## Executive Summary

This document describes two major upgrades to the Property Intelligence Report (PIR) generation system:

1. **Rich Room-Specific Guidance** - Expressive, reasoning-focused instructions for analyzing spaces
2. **Target-Relative Comparable Analysis** - Comparing each comparable to the target property

These upgrades aim to:
- Improve consistency across bracket estimations
- Ensure key cost drivers (kitchens, bathrooms, windows) are never missed
- Create richer, more actionable PIRs that drive accurate scoping

---

## Upgrade 1: Rich Room-Specific Guidance

### Problem Statement

Current PIR generation gives generic instructions. This leads to inconsistent depth and missed observations that drive renovation costs.

### Solution

Add a comprehensive "Room Analysis Guide" as part of the system prompt. This guide teaches HOW to think about spaces - not rigid checklists, but reasoning frameworks.

**CRITICAL**: The clusters in each property have CUSTOM names based on what Gemini sees in the photos. The room guidance below is for INSPIRATION - to help Gemini know what kinds of things matter in different types of spaces. The guidance should enrich analysis of whatever clusters exist, not constrain it to predefined room types.

---

## Rich Room Analysis Guide

### PREAMBLE: How to Use This Guide

You're about to analyze a property with clusters that have been identified from photos. These clusters have names like "salon_comedor", "cocina", "dormitorio_1", "baño_principal", "terraza", "galería", or any number of other Spanish room names that reflect what was actually observed.

This guide exists to help you think deeply about what you're seeing. It's organized by common room functions, but YOUR job is to apply relevant thinking to WHATEVER clusters you encounter. A "galería" might function as laundry, storage, or even a small office. A "dormitorio_3" might be used as a study. A "salon_comedor" combines living and dining functions. 

Don't try to force clusters into these categories. Instead, ask yourself: "What aspects of this guidance apply to what I'm actually seeing?"

---

### KITCHENS AND COOKING SPACES

**WHY THIS MATTERS**: The kitchen is often the most expensive room to renovate, and buyers have the strongest opinions about it. A kitchen that looks "dated" will drive down perceived value even if it's functionally fine. Your job is to see past the staging and understand what's actually there - the bones, the quality, the age, the potential.

When you're looking at a kitchen, you're essentially doing archaeology. Every element tells a story about when this kitchen was created or last updated. Think about it like reading tree rings - the materials, the hardware, the layout conventions all point to an era.

For instance, if you see small ceramic tiles (maybe 10x10cm) on the walls with brown grout, that kitchen probably dates to the 1980s or early 90s. If the cabinets have visible hinges with brass or gold finish, they're pre-2000. If there's a granite countertop with a bullnose edge, you're looking at late 90s to mid-2000s. If the appliances are freestanding and mismatched brands, the kitchen evolved over time rather than being designed coherently.

Ask yourself: What story do these elements tell? When was this kitchen born, and has it been touched since?

The cabinet construction matters enormously for renovation planning. Solid wood can be refinished. MDF with good veneer can sometimes be painted. But particle board with melamine or thermofoil? That's replacement territory - you can't sand it, can't refinish it, can't save it if it's damaged. Look at the edges where doors meet frames. Look inside the cabinets. Are the shelves adjustable (modern) or fixed with visible dadoes (older)?

Think about what the countertop material tells you. Laminate is cheap to replace. Natural stone is expensive to remove (heavy) but removal is often necessary because the style dates even when the material is fine. Quartz engineered stone from the 2010s might be perfectly acceptable. The edge treatment matters too - a simple square edge reads modern, while decorative ogee or bullnose profiles scream a particular era.

Consider the layout through the lens of how people actually cook. The "work triangle" between sink, stove, and refrigerator should allow efficient movement. When cabinets block that flow, or when you have to walk around an island just to get from prep to cooking, the kitchen fails even if everything is new. A tight galley kitchen might work beautifully with smart design, while a larger kitchen with poor layout frustrates daily life.

What's NOT there is often as important as what IS. No dishwasher? The plumbing and electrical for one may not exist. No exhaust hood, or just a recirculating one with a dirty filter? Expect grease buildup you can't see. No under-cabinet lighting? The counter is probably shadowed and hard to work on.

For each kitchen space, ask yourself:
- What era does this represent, and does that era feel dated to today's buyer?
- Could this kitchen be refreshed (paint, hardware, fixtures) or does it need gutting?
- What's the quality level of what's here - is it builder-grade, mid-range, or premium?
- What critical elements are missing that a buyer would expect?
- If I opened these cabinets, what would I find? Particle board? Plywood? Solid wood?

---

### BATHROOMS AND WET ROOMS

**WHY THIS MATTERS**: Bathrooms are the second most expensive renovation, and they have a hidden enemy: water. What looks fine on the surface might be concealing years of moisture damage. Your job is to see what's visible, but also to think about what might be hiding.

When you look at a bathroom, start with the age indicators. Toilet shape is a quick tell - elongated bowls are modern, round bowls are older. Wall-hung toilets are premium and recent. Floor-mounted with exposed bolts and a round bowl? That's probably original to a 1970s or 80s building. The same logic applies to vanities: pedestal sinks are classic (or dated, depending on context), vessel sinks on furniture pieces were very 2005-2015, floating wall-mounted vanities are current.

Tile tells a story too. Small mosaic tiles can hide curves and imperfections - installers use them on surfaces that aren't perfectly flat. Large format tiles (60x60cm or bigger) require flat substrates and skilled installation - their presence suggests more recent, quality work. The ubiquitous 15x15cm or 20x20cm tiles in neutral colors often indicate 1990s-2000s renovations.

Now think about what water does over time. Where tile meets tub or shower, look at the caulk line. Is it intact and clean, or is it pulling away, discolored, or showing black spots? That black isn't just ugly - it's mold, and it means water has been getting behind. Once water gets behind tile, it can rot the substrate, whether that's cement board (better) or drywall (much worse).

Look at the ceiling above the shower area. Peeling paint? That's moisture. The bathroom either has no exhaust fan, or the fan isn't working, or nobody uses it. Either way, moisture has been accumulating for years. What you see on the ceiling is the warning sign - what you don't see is the potential damage in walls and subfloor.

The floor near the toilet deserves special attention. Press with your foot if you can. Does it feel solid, or is there any give? Toilets develop slow leaks at the wax ring that connects them to the drain. This water seeps into subfloor over years. By the time you feel softness, there might be significant rot underneath.

For each bathroom, ask yourself:
- What's the age of these fixtures and finishes? Do they cohere or represent different eras?
- Where would water have been attacking this room over the years? What's the evidence?
- Is this a cosmetic refresh situation (new paint, fixtures, accessories) or a gut job?
- What's behind those tiles? Is there likely to be cement board (good) or just drywall (problem)?
- If I removed that toilet, what would I find underneath?

---

### BEDROOMS AND SLEEPING SPACES

**WHY THIS MATTERS**: Bedrooms seem simple, but they're where people spend a third of their lives. Buyers care deeply about light, closet space, and whether the room feels restful or cramped. Small differences in these factors significantly impact perceived value.

Start with light. What direction do the windows face? A south-facing bedroom gets warm afternoon sun - great for some, oppressive for others. A north-facing room is cooler and more even, but might feel gloomy in winter. An interior bedroom with no exterior wall is a permanent limitation - no amount of renovation creates natural light where there's no window.

Closet situation is often the deal-breaker. Modern buyers expect substantial closet space. If you see a tiny reach-in closet with a single rod, that's a problem. If there's no closet at all (common in older European apartments), the room loses functionality unless built-in wardrobes are added. Walk-in closets are aspirational; even a modest one elevates a bedroom from "room" to "suite."

The ceiling matters more than people think. Standard 2.5m height feels normal. Drop below 2.4m and the room starts feeling oppressive. Go above 2.8m and suddenly the space feels grand, even if the floor area is modest. In older buildings, you sometimes find bedrooms with dropped ceilings hiding utilities - there might be height to recover.

Look at what the walls tell you. Cracks above door frames often indicate settling - usually cosmetic, but worth noting. Water stains on ceiling or walls near windows point to leaks. Discoloration around windows suggests condensation problems - typically from single-pane glass and poor insulation.

For each bedroom space, ask yourself:
- How does light enter this room throughout the day? Is it sufficient or deficient?
- What's the closet story? Does it meet modern expectations, or is it a problem to solve?
- Is this a primary bedroom (needs ensuite potential, generous closet) or secondary (more flexible)?
- What's the ceiling situation? Height, condition, hidden potential?
- If this bedroom is interior (no windows), how has that been addressed, if at all?

---

### LIVING ROOMS AND COMMON SPACES

**WHY THIS MATTERS**: The living room is the first space buyers emotionally react to. It sets the tone for the entire property. Your analysis here shapes whether the property feels like a "wow" or a "meh" - regardless of actual square meters.

Think about the living room as the property's face. What's the first impression when you enter? Is there a clear focal point - a view, a fireplace, a feature wall? Or does the eye wander without landing anywhere? Spaces without clear focal points feel confused, even when they're generously sized.

Light quality in living rooms is crucial. How many windows? What orientations? How deep does natural light penetrate into the room? A north-facing living room in Spain needs careful color choices and good artificial lighting to avoid feeling cold. A south-facing room with large windows might need solutions for glare and heat gain.

Consider how the space flows. Open floor plans are the expectation today. If walls separate living from dining from kitchen, modern buyers immediately think about what comes down. When you see separate rooms, ask yourself: which walls might be load-bearing versus partition? A structural column is a hint that serious architecture happened; a simple partition wall might be easy to remove.

Look for evidence of architectural character. Original moldings, terrazzo floors, ceiling details, built-in features - these add value when maintained, and their absence in an older building suggests previous "modernization" that stripped character. Sometimes the best renovation is restoration, not renewal.

The floor tells you a lot. Original terrazzo in good condition is an asset - buyers who love mid-century character will pay for it. Laminate flooring installed over who-knows-what suggests budget updates. Carpet hides both sins and treasures - what's underneath might be beautiful hardwood or cold concrete.

For each living space, ask yourself:
- What's the emotional impact when you first see this space? What drives that reaction?
- Where's the natural focal point, and does the furniture arrangement (if visible) respect it?
- How does light behave here throughout the day? What does orientation tell you?
- Is this space already open-plan, or are there walls that buyers would want removed?
- What character elements exist, and have previous owners added to or stripped away that character?

---

### TERRACES, BALCONIES, AND OUTDOOR SPACES

**WHY THIS MATTERS**: Outdoor space has become extremely valuable, especially post-pandemic. Even a small balcony dramatically increases appeal. But outdoor spaces also have unique problems - exposure to weather means degradation that doesn't happen inside.

First, assess the size and usability. Can you actually sit out here, or is it just standing room? A balcony where two chairs fit is dramatically more valuable than one where you can only lean on the railing. Depth matters more than width for usability.

The floor surface deserves careful examination. Look for cracks - in balconies, cracks can indicate structural issues or waterproofing failures. White powdery deposits (efflorescence) mean water is moving through the concrete. Staining below railings often indicates rust from the reinforcing steel inside the concrete - a serious structural concern.

Railings are both safety and aesthetic. Are they original (often beautiful iron or forged steel) or replacement (often cheaper aluminum)? Do they meet current height requirements (typically 1.1m minimum)? Loose or wobbly railings are both safety hazards and red flags for deferred maintenance.

Privacy and views matter enormously. A beautiful view makes any outdoor space premium. But a balcony overlooking neighbors' windows or backing onto air shafts has limited appeal regardless of size. What can you see, and what can see you?

Sun exposure determines useability. West-facing in Spain means brutal afternoon sun in summer - almost unusable without shade. North-facing might be too cold much of the year. East gets pleasant morning sun. South is the sweet spot for most buyers, though it still might need an awning.

For each outdoor space, ask yourself:
- Is this usable as actual living space, or is it decorative only?
- What's the condition of the waterproofing and structure? Any warning signs?
- What's the privacy situation? The view? The sun exposure?
- Could improvements (flooring, railings, shade) significantly increase value?
- When was this space last properly maintained or renovated?

---

### CORRIDORS, HALLWAYS, AND CIRCULATION

**WHY THIS MATTERS**: Corridors are often treated as throwaway space, but they're what you experience every single day. Dark, cramped hallways make even nice apartments feel oppressive. Good circulation makes a smaller home feel larger.

The biggest question with corridors is whether they're necessary. Long hallways are "dead space" - they add square meters that don't contribute to living. When you see a long corridor, ask: could this be reconfigured to give that space to adjacent rooms instead?

Light in corridors is almost always a problem. Few have windows; most rely entirely on artificial light. Dark corridors feel institutional, even hostile. Solutions include: glass doors or transoms to borrow light from rooms, light paint colors, adequate artificial lighting, and mirrors to bounce what light exists.

Corridors often hide the electrical panel, utility connections, and other infrastructure. This constrains certain renovations - you can't necessarily eliminate the corridor if it provides access to these critical systems.

Width matters for daily life. Can two people pass comfortably? Can you carry furniture through? European hallways are often surprisingly narrow by modern standards.

For each circulation space, ask yourself:
- Is this corridor necessary, or could the space be reclaimed for adjacent rooms?
- How dark is it, and what are the options for bringing in light?
- What infrastructure does this corridor provide access to?
- Does the corridor feel generous or cramped?

---

### UTILITY ROOMS, LAUNDRY, AND SERVICE SPACES

**WHY THIS MATTERS**: These are the unglamorous workhorses of daily life. Buyers rarely get excited about utility rooms, but they notice when there's no sensible place for the washing machine.

The Spanish "galería" deserves special attention. These semi-outdoor spaces (often enclosed glass-and-aluminum lean-tos) traditionally house laundry and storage. They're neither inside nor outside, which creates both opportunities and problems. Ventilation is usually good (great for laundry), but thermal comfort is poor, and they're often neglected.

For laundry specifically, what matters is: space for washer AND dryer (increasingly expected), proper ventilation for a vented dryer (or recognition that heat-pump dryers don't need venting), adequate electrical capacity, floor drainage in case of leaks, and a work surface for folding.

These spaces can often be converted to other uses if laundry can be relocated. A galería could become a home office. A utility room might become a second bathroom. Think about flexibility.

For each utility/service space, ask yourself:
- What function does this serve now, and is that the best use?
- If it's for laundry, is it properly equipped (drainage, ventilation, capacity)?
- Could this space be converted to something more valuable?
- What's the condition - has it been neglected compared to "showcase" rooms?

---

### FACADE AND BUILDING CONTEXT

**WHY THIS MATTERS**: An individual owner typically can't change the exterior, but the building's condition directly impacts the apartment's value and future costs. Your analysis of the facade and common areas tells buyers what they're buying into.

Building age and architectural style set expectations. A 1920s Eixample building has different character (and different problems) than a 1970s concrete block in the suburbs. Original features on a historic facade are assets; deterioration is a liability that the community must address collectively.

Look at the common areas as indicators of community health. Well-maintained entrance, clean stairwell, functioning lift - these suggest an engaged community that invests in the building. Peeling paint, broken tiles, flickering lights suggest deferred maintenance and possibly upcoming special assessments.

Windows visible from outside tell you about community coordination. If every apartment has different windows - some original, some aluminum, some PVC, different colors - you're seeing a community that either can't agree on standards or hasn't needed to. If windows are uniform, either the building is original and unrenovated, or a coordinated replacement happened.

For building context, ask yourself:
- What's the building's architectural character, and how has it been maintained?
- What do common areas suggest about community management and investment?
- Are there visible signs of deferred maintenance that suggest future costs?
- How does this building compare to others on the street or in the neighborhood?

---

## Upgrade 2: Target-Relative Comparable Analysis

### Problem Statement

Currently, each comparable PIR is generated in isolation. The model describes what it sees, but doesn't explicitly compare to what the TARGET property has or needs.

This leads to:
- Generic descriptions that don't highlight renovation-relevant differences
- Bracket PIRs that describe an "average" rather than "what target needs to match"
- Inconsistent scoping because the model doesn't carry target context across calls

### The Core Insight

When you're estimating a renovation, what matters isn't "what nice kitchens look like in abstract" - it's "what my specific kitchen needs to compete with the kitchens that sold at this price point."

The comparable analysis should always be grounded in the target. Not "this comparable has quartz countertops" but "this comparable has quartz countertops while the target has laminate - that's a specific gap."

### Solution

Modify comparable PIR generation to:
1. **Include target property photos** alongside comparable photos
2. **Frame all analysis comparatively** - what does the comparable have that target lacks?
3. **Identify specific gaps** that represent renovation scope

Then modify bracket PIR synthesis to:
1. **Reference the target property** throughout
2. **Phrase synthesis in terms of what target needs** - not what bracket "looks like"
3. **Aggregate gaps** from individual comparable analyses

### How This Changes the Analysis

**Current approach**: "The kitchen has push-open cabinets, quartz counters, and integrated appliances."

**New approach**: "Looking at this comparable's kitchen against the target: where the target has visible-hinge melamine cabinets, this comparable has push-open lacquered fronts. Where the target has granite counters with bullnose edge, this comparable has thin-profile quartz with waterfall edge. The target's freestanding appliances contrast with this comparable's fully integrated, panel-covered units. This represents a complete kitchen transformation, not just updates."

### Implementation Approach

#### Comparable PIR Generation

**Current flow:**
```
Input: Comparable photos + Comparable listing data
Output: PIR describing the comparable
```

**New flow:**
```
Input: TARGET photos + Comparable photos + Both listing data
Output: PIR describing comparable RELATIVE TO target
```

The system prompt (cached) contains:
- Rich room analysis guidance (from above)
- Instructions for comparative analysis
- Role as renovation consultant comparing properties

The user prompt (per-call) contains:
- Target photos (labeled "TARGET PROPERTY")
- Comparable photos (labeled "COMPARABLE PROPERTY")
- Listing data for both
- Specific instruction to analyze gaps

#### Bracket PIR Synthesis

**Current approach**: Synthesize what properties at this price point look like.

**New approach**: Synthesize what the TARGET needs to reach this price point.

The bracket synthesis prompt changes from:
- "Describe what kitchens look like in this bracket" 

To:
- "Based on the comparable PIRs (which already describe gaps from target), synthesize what the target kitchen needs to match this bracket"

This is more prescriptive and actionable because it's grounded in a specific starting point (the target's current state).

### Photo Handling

| PIR Type | Target Photos | Comparable Photos | Cached? |
|----------|---------------|-------------------|---------|
| Target PIR | ✅ Required | N/A | System prompt only |
| Comparable PIR | ✅ NEW (for comparison) | ✅ Required | System + Target photos |
| Bracket PIR | ❌ None | ❌ None | N/A (text only) |

**Caching strategy**: The system prompt + target photos can be cached across ALL comparable PIR calls for a given target property. This means the cost of including target photos is amortized across 8+ comparable calls.

---

## Implementation Plan

### Phase 1: Rich Room Guidance
1. Create `ROOM_ANALYSIS_GUIDE` constant with all room-type guidance
2. Add to system prompt for Target PIR generation
3. Test with target PIR to verify richer output
4. Commit and push

### Phase 2: Target-Relative Comparable PIRs
1. Modify `generate_comparable_pir()` to accept target photos and data
2. Update prompt for comparative analysis
3. Test with single comparable
4. Commit and push

### Phase 3: Relative Bracket PIR Synthesis
1. Update bracket synthesis prompt for gap-focused language
2. Test full pipeline
3. Verify cost ordering is correct
4. Commit and push

---

## Success Criteria

1. **Richer PIRs**: Each space analysis shows deep reasoning, not just surface observation
2. **Consistent scoping**: All brackets include appropriate kitchen/bathroom/major-system work
3. **Correct cost ordering**: fast_sell < fair_market < out_of_market
4. **Actionable gaps**: Bracket PIRs clearly state what target needs, not abstract ideals
5. **Cluster flexibility**: Guidance enhances analysis of whatever clusters exist, not just predefined room types
