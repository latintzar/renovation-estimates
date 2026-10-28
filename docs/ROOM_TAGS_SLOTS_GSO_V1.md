Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Room Tags + Slots (GSO) — V1 (Shippable)

This document defines a **V1** structure we can ship to make renovation scope + pricing **complete**, **auditable**, and **portable across regions**.

It introduces:
- **Room tags**: a canonical, multi-label description of each room cluster (kitchen/bath/etc + wet/dry/exterior + traits).
- **Slots (GSO: Global Scope Ontology)**: a finite checklist of sub-scope “buckets” per dimension that we must fill (or explicitly default) to prevent gaps.
- **Catalog adapters**: mapping from slots → allowed items in a region cost table (e.g., BCCA today; others later).

---

## Quick visual

```text
Clusters (target listing)               Strategy tier
  |                                       |
  v                                       v
Room Tags (per cluster)             Strategy Spec (as now)
  |                                       |
  +-------------------+-------------------+
                      v
              Slot Plan (per room × dimension × slot)
              - required slots from tags (deterministic)
              - slot state: DELTA vs BASELINE
              - evidence refs + assumptions
                      |
                      v
              Catalog Adapter (region-specific)
              - retrieve top-k candidates within slot
              - choose IDs (LLM constrained) or deterministic
                      |
                      v
              Quantification + Price (as V4)
```

---

## Terms (tight definitions)

- **Cluster**: a group of listing photos that represent a room-like space (`cluster_id` in DB).
- **Room tag**: canonical labels attached to a cluster (multi-label, with confidence + evidence).
- **Dimension**: current 6 buckets (`shell_preparation`, `apertures_enclosure`, `systems_services`, `surface_finishes`, `fixed_joinery_equipment`, `details_fittings`).
- **Slot (GSO slot)**: a **finite** sub-bucket inside a dimension, designed for completeness checks.
- **Slot instance**: `(listing_id, strategy, cluster_id, dimension, slot_id)`.
- **Slot state**:
  - **DELTA**: the strategy requires meaningful change vs baseline in this slot for this room.
  - **BASELINE**: hygiene-only / no meaningful upgrade delta; still may have priced baseline work or an explicit “no-op”.
- **Catalog item**: a priced line item in a region cost table (BCCA code today).
- **Catalog adapter**: mapping/logic that turns slot instances into catalog item IDs + evidence/assumptions.

---

# Canonical room types (for clustering) — V1

This is the **allowed label list** for clustering. The point is to avoid “open ended” room naming so the downstream pipeline can be deterministic.

Rules:
- A cluster gets **one primary label** from this list, plus tags.
- If multiple instances exist, append `_1`, `_2`, `_3` (e.g., `bathroom_full_2`).
- **Open-plan** / **studio** should be labeled explicitly as one cluster with combined tags (see below).

## Core room types (recommended “default allowlist”)

- `living_room`: Primary social space for seating/TV/lounge use.
- `dining_room`: Space primarily arranged around a dining table for meals.
- `kitchen`: Dedicated food-prep room with fixed cabinetry and cooking zone.
- `bedroom_primary`: Main bedroom (largest / principal sleeping room).
- `bedroom_secondary`: Standard secondary bedroom used for sleeping.
- `office`: Work-focused room with desk/study setup as primary function.
- `bathroom_full`: Full bathroom with bath/shower plus toilet and basin.
- `bathroom_en_suite`: Full bathroom directly attached to a bedroom (suite).
- `toilet_room`: WC/guest toilet with toilet and small basin, no shower/bath.
- `laundry_room`: Dedicated room for washer/dryer and laundry handling.
- `utility_room`: Service room for appliances/cleaning storage and sometimes laundry.
- `entry_hall`: Main entry/foyer area immediately inside the front door.
- `hallway`: Circulation corridor connecting rooms.
- `staircase`: Stairs and immediate stair zone.
- `balcony`: Small projecting outdoor space off a room.
- `terrace`: Larger outdoor surface intended for seating/dining.
- `garden`: Planted outdoor area with landscaping as primary surface.
- `garage_private`: Private garage box or attached garage space.
- `storage_room`: Interior storage room (despensa/trastero inside the dwelling).
- `attic_habitable`: Finished attic used as bedroom/office/lounge.
- `basement`: Below-grade level space (often moisture risk).

## Open-plan + studio (explicit combined-room labels)

- `open_plan_kitchen_living`: Single continuous space combining kitchen + living (no full-height separation).
- `open_plan_kitchen_dining`: Single continuous space combining kitchen + dining.
- `open_plan_living_dining`: Single continuous space combining living + dining.
- `open_plan_kitchen_living_dining`: Single continuous main space combining kitchen + living + dining.
- `studio_main_space`: One main habitable space containing sleeping + living and often kitchenette in one open room (bathroom is separate).

## Non-room / auxiliary labels (important to avoid pollution)

- `floorplan`: Plan drawing/diagram images.
- `exterior_facade`: Outside building façade views.
- `street_view`: Street/public realm view near the property.
- `unknown_room`: Interior space that can’t be confidently typed.
- `unknown_exterior`: Exterior space that can’t be confidently typed.

### Required room tags to make this work

Each cluster must carry at least:
- `room_type` (primary label from the allowlist above)
- `environment`: `wet` | `dry` | `exterior`
- `traits[]`: may include:
  - `open_plan` (true/false)
  - `combined_types[]`: e.g., `["kitchen","living_room","dining_room"]` for open-plan clusters
  - `is_studio_main_space` (true/false)
- `confidence` (0–1)
- `evidence_refs[]` (photo refs + OPENING/FEATURE refs where available)

---

# Iteration history (5 passes, in-doc)

Each iteration is intentionally preserved so you can see how we converged.

---

## Iteration 1 — Minimal skeleton (what exists, what’s new)

### Room Tags (V1)
We need tags that are:
- **universal** (houses are houses)
- **cheap** (computed once per cluster)
- **sufficient** to drive slot applicability deterministically

**Core tags**
- `room_type`: one of:
  - `kitchen`, `bathroom`, `toilet`, `bedroom`, `living`, `dining`, `office`, `hallway`, `storage`, `dressing`, `laundry`
  - `terrace`, `garden`, `garage`, `pool`, `basement`, `attic`
  - `stairs`, `entry`, `unknown`
- `environment`: `wet` | `dry` | `exterior`
- `traits[]` (optional, multi):
  - `open_plan`, `primary`, `secondary`, `guest`, `children`
  - `has_shower`, `has_bathtub`, `has_dressing`
  - `has_window`, `interior`

**Evidence**
- `evidence_refs[]`: any of `ROOM(...)`, `OPENING(...)`, `FEATURE(...)`, or photo indices/URLs.

### Slots (V1)
Inside each dimension, define a finite set of slots that can be validated (no gaps):
- `systems_services`: sockets, switches, lighting points, panel/circuits, plumbing supply, plumbing drain, hvac terminals, testing/commissioning

### Key idea
**Dimensions reduce search space; slots enforce completeness.**

---

## Iteration 2 — The FULL Slot Universe (No Blind Spots)

This is the **comprehensive checklist** intended to cover the full renovation scope required to bring a property up to a “comparable standard”, across **all common Spanish home room types**.

Design rules for V1:
- Slots are **finite** and **named** (closed universe).
- A room does **not** have all slots; rooms get a subset via Iteration 3.
- Slots are phrased in English but map cleanly to region catalogs (BCCA now; other regions later).

### 1) `shell_preparation` (dirty works)
- `shell.protection_isolation` — protect floors/paths, dust control, masking
- `shell.stripout_demolition` — strip-out + demolition of existing elements
- `shell.waste_haulage` — bagging, transport, disposal
- `shell.masonry_chases` — channels/cuts for MEP routes
- `shell.openings_changes` — new/closed openings, widening, lintels (if needed)
- `shell.substrate_prep` — leveling, patching, skim coat, ready-for-finishes substrate

### 2) `apertures_enclosure` (openings + envelope)
- `enclosure.windows` — windows (replace/repair)
- `enclosure.shutters_blinds` — shutters/blinds/boxes where applicable
- `enclosure.balcony_doors` — exterior balcony/terrace doors
- `enclosure.internal_doors` — interior doors (swing/sliding)
- `enclosure.entrance_door` — main entrance/security door (home-level)
- `enclosure.sealing_air_tightness` — sealing/air-tightness measures (if priced separately)

### 3) `systems_services` (MEP)
- `mep.electrical_panel` — main panel (home-level)
- `mep.electrical_circuits` — circuits + rewiring where needed
- `mep.sockets_switches` — sockets + switches/controls
- `mep.lighting_points` — light points
- `mep.plumbing_supply` — water supply lines
- `mep.plumbing_drain` — drain lines
- `mep.ventilation_extraction` — extraction/ventilation (kitchen/baths)
- `mep.hvac_distribution` — ducts/pipes distribution where applicable
- `mep.hvac_terminals` — terminals (grilles/diffusers/splits)
- `mep.heating_emitters_controls` — radiators/towel rails/thermostats where applicable
- `mep.hot_water_generator` — boiler/heat pump/hot water unit where applicable
- `mep.gas_supply` — gas supply modifications where applicable
- `mep.testing_commissioning` — testing/commissioning

### 4) `surface_finishes` (finishes)
- `finishes.flooring` — main floor finish
- `finishes.skirting` — skirting/baseboard trim
- `finishes.wall_finish` — paint/wall finish
- `finishes.wall_tiling` — wall tiling (wet rooms / splashbacks)
- `finishes.ceiling_finish` — ceilings (false ceiling/plaster/paint)
- `finishes.joints_grout` — joints/grout/finish sealing between tiles
- `finishes.waterproofing` — waterproofing membranes/tanking
- `finishes.thermal_insulation` — insulation upgrades where applicable

### 5) `fixed_joinery_equipment` (built-ins)
- `joinery.kitchen_cabinetry` — kitchen base/wall/tall cabinets
- `joinery.kitchen_worktops_splashback` — countertops + splashback joinery component
- `joinery.kitchen_appliance_integration` — columns, integration, appliance housing
- `joinery.bath_vanity_storage` — vanity + storage
- `joinery.wardrobes_builtins` — wardrobes/built-ins
- `joinery.laundry_storage` — laundry/utility storage
- `joinery.custom_builtins` — custom shelves/niches/bookcases where applicable

### 6) `details_fittings` (fixtures + hardware)
- `details.sanitary_fixtures` — toilets/sinks/bidet (room-level fixtures)
- `details.bathing_units` — shower tray / bathtub
- `details.taps_mixers` — faucets/shower sets
- `details.screens_mirrors_accessories` — screens/mirrors/accessories
- `details.door_hardware` — handles/hinges/stops/locks for internal doors
- `details.electrical_trim` — faceplates/trim
- `details.intercom_entry` — entry intercom (home-level)

---

## Iteration 3 — Room-by-room Slot Coverage (Explicit per-room requirements)

Slots are **global**, but every listing is priced **room-by-room** (cluster-by-cluster). This section defines the **required slot set per room type**.

Legend:
- **Required**: must exist for that room type in V1.
- **Conditional**: required only if relevant evidence exists (feature/opening) or if strategy tier demands it.
- **Not applicable**: should not be included unless special evidence overrides.

### Core room types (most homes)

#### Kitchen
Required:
- `shell.protection_isolation`, `shell.stripout_demolition` (if delta), `shell.waste_haulage`, `shell.masonry_chases` (if delta), `shell.substrate_prep`
- `mep.sockets_switches`, `mep.lighting_points`, `mep.ventilation_extraction`
- `mep.plumbing_supply`, `mep.plumbing_drain`
- `finishes.flooring`, `finishes.wall_finish`, `finishes.ceiling_finish`
- `finishes.wall_tiling` (conditional: splashback/full height policy), `finishes.joints_grout` (if tiling), `finishes.waterproofing` (conditional policy)
- `joinery.kitchen_cabinetry`, `joinery.kitchen_worktops_splashback`, `joinery.kitchen_appliance_integration` (conditional)
- `details.taps_mixers` (sink), `details.electrical_trim`
Conditional:
- `enclosure.windows` / `enclosure.shutters_blinds` / `enclosure.balcony_doors` (if openings exist)
- `mep.gas_supply`, `mep.hot_water_generator` (if gas/boiler located here)

#### Bathroom / Toilet
Required:
- `shell.protection_isolation`, `shell.stripout_demolition` (if delta), `shell.waste_haulage`, `shell.masonry_chases` (if delta), `shell.substrate_prep`
- `mep.sockets_switches` (safety spec), `mep.lighting_points`, `mep.ventilation_extraction`
- `mep.plumbing_supply`, `mep.plumbing_drain`
- `finishes.flooring`, `finishes.wall_tiling`, `finishes.joints_grout`, `finishes.ceiling_finish`, `finishes.waterproofing`
- `joinery.bath_vanity_storage`
- `details.sanitary_fixtures`, `details.taps_mixers`, `details.screens_mirrors_accessories`, `details.bathing_units` (bathroom)
Conditional:
- `mep.heating_emitters_controls` (towel rail/radiator), `mep.hot_water_generator` (if unit located here)
- `enclosure.windows` / `enclosure.shutters_blinds` (if openings exist)

#### Bedroom
Required:
- `shell.protection_isolation`, `shell.stripout_demolition` (if delta), `shell.waste_haulage` (if delta), `shell.substrate_prep`
- `mep.sockets_switches`, `mep.lighting_points`
- `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
- `details.electrical_trim`
Conditional:
- `joinery.wardrobes_builtins` (if wardrobes/built-ins exist or tier requires)
- `enclosure.windows` / `enclosure.shutters_blinds` (if openings exist)
- `mep.hvac_terminals` / `mep.hvac_distribution` / `mep.heating_emitters_controls` (if system present)

#### Living / Dining
Required:
- `shell.protection_isolation`, `shell.stripout_demolition` (if delta), `shell.waste_haulage` (if delta), `shell.substrate_prep`
- `mep.sockets_switches`, `mep.lighting_points`
- `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
- `details.electrical_trim`
Conditional:
- `joinery.custom_builtins`
- `enclosure.windows` / `enclosure.shutters_blinds` / `enclosure.balcony_doors` (if openings exist)
- `mep.hvac_terminals` / `mep.hvac_distribution` / `mep.heating_emitters_controls` (if system present)

#### Hallway / Corridor / Entry
Required:
- `shell.protection_isolation`, `shell.stripout_demolition` (if delta), `shell.waste_haulage` (if delta), `shell.substrate_prep`
- `mep.sockets_switches`, `mep.lighting_points`, `details.electrical_trim`
- `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
Home-level required here (unless another “technical” room is designated):
- `mep.electrical_panel`
- `enclosure.entrance_door`
- `details.intercom_entry`
Conditional:
- `joinery.wardrobes_builtins` (coat closet)

### Exterior room types

#### Balcony / Terrace
Required:
- `shell.protection_isolation` (site protection), `shell.stripout_demolition` (if delta), `shell.waste_haulage` (if delta)
- `finishes.flooring` (exterior-rated), `finishes.wall_finish` (if walls), `finishes.waterproofing`
Conditional:
- `enclosure.balcony_doors` (belongs to adjacent interior room but can be attributed here)
- `mep.lighting_points` (if evidence), `mep.sockets_switches` (if evidence)
- `mep.plumbing_supply` / `mep.plumbing_drain` (if outdoor tap/drain evidence)

#### Garden
Required (only if garden is in scope of reno; otherwise baseline no-op):
- `finishes.flooring` (paths/paving), `mep.lighting_points` (if evidence)
Conditional:
- `mep.plumbing_supply` (irrigation/tap), `mep.plumbing_drain` (drainage)

### Special room types (Spain common variants)

#### Laundry / Utility
Required:
- `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.ventilation_extraction`
- `mep.sockets_switches`, `mep.lighting_points`, `details.electrical_trim`
- `finishes.flooring`, `finishes.wall_finish`, `finishes.ceiling_finish`
- `joinery.laundry_storage` (conditional by tier)

#### Garage / Storage
Required:
- `mep.lighting_points`
Conditional:
- `mep.sockets_switches` (if evidence), `finishes.flooring`, `finishes.wall_finish`, `finishes.ceiling_finish`

#### Attic
Required (in addition to bedroom-like baseline):
- `finishes.thermal_insulation`
Conditional:
- `enclosure.windows` (skylights/roof windows), `finishes.waterproofing` (roof adjacency)

#### Basement
Required (in addition to generic interior baseline):
- `finishes.waterproofing` (tanking) if moisture risk evidence
- `mep.ventilation_extraction`
Conditional:
- `finishes.thermal_insulation`

#### Stairs
Required:
- `finishes.flooring` (treads/risers) and `details.screens_mirrors_accessories` (if balustrade/handrail is in-scope)
Conditional:
- `mep.lighting_points` (step lighting)

### “Decide the slots?” step (cost control)
V1: do **not** ask the LLM which slots apply.
- Compute room tags once.
- Apply this room-by-room slot requirement list deterministically, with feature/opening conditionals.

### Open-plan and studio rule (mandatory for “no blind spots”)

If a cluster has `traits.combined_types[]`:
- Required slots for that cluster = **union** of required slots for each component room type.
- Dedupe by slot_id (no double counting).
- Kitchen components always bring in: `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.ventilation_extraction`, and kitchen joinery slots.

If a cluster is `studio_main_space`:
- Treat it as `combined_types=["living_room","bedroom_secondary","kitchen"]` unless evidence says otherwise.

### Home-level slots (one-per-home) and where they live

Some slots are inherently home-level (should appear exactly once per home):
- `mep.electrical_panel`
- `enclosure.entrance_door`
- `details.intercom_entry`

Host-room policy (deterministic):
1) Prefer `entry_hall_*` cluster if present
2) Else `hallway_*`
3) Else `living_room_*` (or open-plan main space)
4) Else `kitchen_*`

---

## Iteration 4 — Slot state: DELTA vs BASELINE (and reuse across tiers)

For each slot instance, we store:
- `slot_state`: `DELTA` or `BASELINE`
- `slot_intent_summary`: short phrase (not full prose)
- `evidence_refs[]`
- `assumptions[]` (only if needed)

### Reuse policy across tiers
Strategy tiers are ordered: `conservative` → `market_standard` → `top_of_market`.

**BASELINE reuse**
- If a slot is `BASELINE` at a higher tier, reuse the baseline definition from the nearest lower tier **unless**:
  - higher tier explicitly tightens hygiene standards (rare; define as policy)

**DELTA monotonicity**
- If `DELTA` at conservative, it stays `DELTA` at higher tiers (but may become “stronger” delta).
- If `BASELINE` at conservative, it can become `DELTA` at higher tiers.

---

## Iteration 5 — “Ship it”: exact V1 data contracts + how catalog mapping works

### V1 RoomTags schema (what we persist)

Per listing, store:
- `room_tags_v1.rooms[]`:
  - `room_id` (cluster_id)
  - `room_type` (canonical)
  - `environment` (`wet|dry|exterior`)
  - `traits[]`
  - `confidence` (0–1)
  - `evidence_refs[]`
  - `notes` (optional)

### V1 SlotPlan schema (what we persist)

Per listing × strategy:
- `slot_plan_v1.strategy_name`
- `slot_plan_v1.rooms[]`:
  - `room_id`
  - `room_tags_ref` (pointer to room_tags_v1)
  - `dimensions[]`:
    - `dimension`
    - `slots[]`:
      - `slot_id`
      - `required` (bool)
      - `slot_state` (`DELTA|BASELINE`)
      - `intent_summary` (short)
      - `evidence_refs[]`
      - `assumptions[]`

### Catalog adapter (V1)

We support multiple region catalogs by separating:
- **GSO slots** (stable)
- **catalog** (variable)

Per region:
- `slot_id → allowed_catalog_families/items`
- retrieval index over catalog items (embeddings)

Runtime mapping for a slot instance:
1) Build a small query text: `intent_summary + evidence snippet keywords + dimension + slot_id`
2) Retrieve top-k catalog items **filtered by allowed set for slot**
3) Choose final item(s):
   - deterministic rules where possible
   - else LLM constrained to pick from top-k IDs
4) Persist:
   - chosen item IDs
   - evidence/assumption flags

### Why this ships (V1 constraints)
- **Completeness is testable**: all `required=true` slots must be mapped or defaulted.
- **Costs remain bounded**: slot applicability is deterministic; mapping uses small top-k contexts.
- **Portability is real**: only the slot→catalog mapping changes per region.

---

## Notes on the existing KG (how it fits, without blocking V1)

You already have a renovation KG of canonical tasks + requires/triggers. In V1:
- Use it **inside a slot** as an optional expander (ensure prerequisite coverage), not as the primary completeness mechanism.
- Completeness is guaranteed by slots; KG helps with “within-slot completeness” and sequencing.

---

## Open questions (explicitly tracked for V1)

- **Do we price BASELINE as a real cost or a true no-op?**
  - V1 recommendation: baseline can still produce priced items (e.g. repaint, minor electrical swaps) but must be explicit.
- **Do we treat `internal_doors` as `apertures_enclosure` always?**
  - V1 recommendation: yes; stop letting “door work” vanish into generic carpintería.
- **What’s the smallest viable slot set?**
  - V1 above is intentionally compact; if we want fewer calls, we reduce *items per slot*, not remove slots.

