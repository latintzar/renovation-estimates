Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## Slots by Room Type — V1 (Complete Coverage Map)

This document guarantees that **every canonical room type** we allow during clustering has a **complete fixed slot set** derived from the V1 slot universe.

Principle:
- We do not enumerate infinite variants. We enumerate **finite slots** and apply **protocols** with overrides.
- Open-plan and studio are handled via **multi-tag union** rules.

---

### Slot universe reference (IDs)

Use the slot IDs from `ROOM_TAGS_SLOTS_GSO_V1.md` Iteration 2.

---

## Slot protocols (templates)

These are reusable “room workflows” that define the **fixed slot list** we will run for a room type.

IMPORTANT:
- These slot lists are about **what we always look at** for that room type.
- A slot being present does **NOT** mean it is visible in the photos.
- The per-room PIR call must output **one sentence per slot**, and is allowed to say **"not visible"** + a conservative assumption.
- The delta step then outputs **"no change"** or a one-liner for each slot.

### Protocol P1 — Dry habitable room (bedroom/living/dining/office)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.masonry_chases`, `shell.openings_changes`, `shell.substrate_prep`
- Enclosure: `enclosure.windows`, `enclosure.shutters_blinds`, `enclosure.balcony_doors`, `enclosure.internal_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`, `mep.hvac_distribution`, `mep.hvac_terminals`, `mep.heating_emitters_controls`
- Finishes: `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
- Joinery: `joinery.wardrobes_builtins`, `joinery.custom_builtins`
- Details: `details.door_hardware`, `details.electrical_trim`

### Protocol P2 — Kitchen (wet + joinery + extraction)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.masonry_chases`, `shell.openings_changes`, `shell.substrate_prep`
- Enclosure: `enclosure.windows`, `enclosure.shutters_blinds`, `enclosure.balcony_doors`, `enclosure.internal_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`, `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.ventilation_extraction`, `mep.heating_emitters_controls`, `mep.hot_water_generator`, `mep.gas_supply`
- Finishes: `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.wall_tiling`, `finishes.ceiling_finish`, `finishes.joints_grout`, `finishes.waterproofing`
- Joinery: `joinery.kitchen_cabinetry`, `joinery.kitchen_worktops_splashback`, `joinery.kitchen_appliance_integration`
- Details: `details.taps_mixers`, `details.door_hardware`, `details.electrical_trim`

### Protocol P3 — Bathroom (full wet room)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.masonry_chases`, `shell.openings_changes`, `shell.substrate_prep`
- Enclosure: `enclosure.windows`, `enclosure.shutters_blinds`, `enclosure.internal_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`, `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.ventilation_extraction`, `mep.heating_emitters_controls`, `mep.hot_water_generator`
- Finishes: `finishes.flooring`, `finishes.wall_finish`, `finishes.wall_tiling`, `finishes.joints_grout`, `finishes.ceiling_finish`, `finishes.waterproofing`
- Joinery: `joinery.bath_vanity_storage`
- Details: `details.sanitary_fixtures`, `details.bathing_units`, `details.taps_mixers`, `details.screens_mirrors_accessories`, `details.door_hardware`, `details.electrical_trim`

### Protocol P4 — Toilet (WC only)
Same as Bathroom, except:
- `details.bathing_units` is NOT included.

### Protocol P5 — Circulation + entry (hallway/entry)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.masonry_chases`, `shell.openings_changes`, `shell.substrate_prep`
- Enclosure: `enclosure.entrance_door`, `enclosure.internal_doors`, `enclosure.windows`, `enclosure.shutters_blinds`, `enclosure.balcony_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.electrical_panel`, `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`, `mep.testing_commissioning`
- Finishes: `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
- Joinery: `joinery.wardrobes_builtins`
- Details: `details.intercom_entry`, `details.door_hardware`, `details.electrical_trim`

### Protocol P6 — Exterior hardscape (terrace/balcony/patio)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.substrate_prep`
- Enclosure: `enclosure.balcony_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.sockets_switches`, `mep.lighting_points`, `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.gas_supply`, `mep.hvac_terminals`
- Finishes: `finishes.flooring`, `finishes.wall_finish`, `finishes.waterproofing`, `finishes.thermal_insulation`
- Details: `details.electrical_trim`

### Protocol P7 — Garden (softscape)
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`
- MEP: `mep.lighting_points`, `mep.plumbing_supply`, `mep.plumbing_drain`
- Finishes: `finishes.flooring`, `finishes.waterproofing`

### Protocol P8 — Laundry / utility
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.masonry_chases`, `shell.openings_changes`, `shell.substrate_prep`
- Enclosure: `enclosure.windows`, `enclosure.shutters_blinds`, `enclosure.internal_doors`
- MEP: `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`, `mep.plumbing_supply`, `mep.plumbing_drain`, `mep.ventilation_extraction`, `mep.hot_water_generator`, `mep.gas_supply`
- Finishes: `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`, `finishes.waterproofing`
- Joinery: `joinery.laundry_storage`
- Details: `details.taps_mixers`, `details.door_hardware`, `details.electrical_trim`

### Protocol P9 — Garage / storage
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.substrate_prep`
- Enclosure: `enclosure.internal_doors`, `enclosure.sealing_air_tightness`
- MEP: `mep.electrical_circuits`, `mep.sockets_switches`, `mep.lighting_points`
- Finishes: `finishes.flooring`, `finishes.wall_finish`, `finishes.ceiling_finish`
- Details: `details.door_hardware`, `details.electrical_trim`

### Protocol P10 — Attic (habitable)
Protocol P1 (dry habitable) PLUS:
- `finishes.thermal_insulation`, `finishes.waterproofing`

### Protocol P11 — Basement (habitable or semi-habitable)
Protocol P1 (dry habitable) PLUS:
- `mep.ventilation_extraction`, `finishes.waterproofing`, `finishes.thermal_insulation`

### Protocol P12 — Stairs
Slots (always):
- Shell: `shell.protection_isolation`, `shell.stripout_demolition`, `shell.waste_haulage`, `shell.substrate_prep`
- Enclosure: `enclosure.internal_doors`
- MEP: `mep.lighting_points`
- Finishes: `finishes.flooring`, `finishes.skirting`, `finishes.wall_finish`, `finishes.ceiling_finish`
- Details: `details.door_hardware`, `details.electrical_trim`

---

## Room type → protocol mapping (complete list)

Each canonical room type below maps to a protocol and overrides. This ensures **full slot coverage** for every allowed cluster label.

### Core interior
- `living_room` → P1
- `dining_room` → P1
- `kitchen` → P2
- `bedroom_primary` → P1
- `bedroom_secondary` → P1
- `office` → P1
- `storage_room` → P9 (storage variant)

### Bathrooms / wet
- `bathroom_full` → P3
- `bathroom_en_suite` → P3
- `toilet_room` → P4

### Service
- `laundry_room` → P8
- `utility_room` → P8

### Circulation
- `entry_hall` → P5 (preferred host for home-level slots)
- `hallway` → P5
- `staircase` → P12

### Outdoor
- `balcony` → P6
- `terrace` → P6
- `garden` → P7

### Vehicles / storage
- `garage_private` → P9

### Special volumes
- `attic_habitable` → P10
- `basement` → P11

### Open plan / studio (multi-tag union)
Open-plan clusters must also carry `combined_types[]` and are evaluated as **union** of protocols:
- `open_plan_kitchen_living` → union(P2 kitchen, P1 living)
- `open_plan_kitchen_dining` → union(P2 kitchen, P1 dining)
- `open_plan_living_dining` → union(P1 living, P1 dining)
- `open_plan_kitchen_living_dining` → union(P2 kitchen, P1 living, P1 dining)
- `studio_main_space` → union(P2 kitchen, P1 living, P1 bedroom_secondary) by default

### Non-room / auxiliary
- `floorplan` → excluded from renovation scope (no slots)
- `exterior_facade` → excluded from room slots (may inform enclosure evidence)
- `street_view` → excluded
- `unknown_room` → fallback to P1 (dry habitable) with conservative assumptions
- `unknown_exterior` → fallback to P6 (exterior hardscape) with conservative assumptions

