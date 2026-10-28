"""
V5 Slot Universe + Room Protocol Mapping.

Slots are the closed checklist that prevents “missing buckets”.
Room protocols define the fixed slot list per room type (no conditionals).
"""

from __future__ import annotations

from typing import Dict, List, Literal, Set

from pricing.v5_room_types import ROOM_TYPES_V5, combined_types_for


SlotId = str
ProtocolId = Literal["P1_DRY", "P2_KITCHEN", "P3_BATH", "P4_TOILET", "P5_ENTRY", "P6_EXTERIOR", "P7_GARDEN", "P8_LAUNDRY", "P9_GARAGE", "P10_ATTIC", "P11_BASEMENT", "P12_STAIRS"]

# Full slot universe (closed list).
SLOTS_V5: List[SlotId] = [
    # shell
    # NOTE: We intentionally do NOT model enabling-works as first-class slots
    # (protection/stripout/waste haulage/substrate prep). Those are derived later
    # in delta/decompose into work-items when implied by other scope.
    "shell.masonry_chases",
    "shell.openings_changes",
    # apertures_enclosure
    "enclosure.windows",
    "enclosure.shutters_blinds",
    "enclosure.balcony_doors",
    "enclosure.internal_doors",
    "enclosure.entrance_door",
    "enclosure.sealing_air_tightness",
    # systems_services (MEP)
    "mep.electrical_panel",
    "mep.electrical_circuits",
    "mep.sockets_switches",
    "mep.lighting_points",
    "mep.plumbing_supply",
    "mep.plumbing_drain",
    "mep.ventilation_extraction",
    "mep.hvac_distribution",
    "mep.hvac_terminals",
    "mep.heating_emitters_controls",
    "mep.hot_water_generator",
    "mep.gas_supply",
    "mep.testing_commissioning",
    # surface_finishes
    "finishes.flooring",
    "finishes.skirting",
    "finishes.wall_finish",
    "finishes.wall_tiling",
    "finishes.ceiling_finish",
    "finishes.joints_grout",
    "finishes.waterproofing",
    "finishes.thermal_insulation",
    # fixed_joinery_equipment
    "joinery.kitchen_cabinetry",
    "joinery.kitchen_worktops_splashback",
    "joinery.kitchen_appliance_integration",
    "joinery.bath_vanity_storage",
    "joinery.wardrobes_builtins",
    "joinery.laundry_storage",
    "joinery.custom_builtins",
    # details_fittings
    "details.sanitary_fixtures",
    "details.bathing_units",
    "details.taps_mixers",
    "details.screens_mirrors_accessories",
    "details.door_hardware",
    "details.electrical_trim",
    "details.intercom_entry",
]


# Protocol templates (inspired by docs/SLOTS_BY_ROOM_TYPE_V1.md), but flattened:
# every room type has ONE fixed slot list (no conditional/applicable flags).
#
# IMPORTANT:
# - A slot being included does NOT mean it is visible in photos.
# - PIR/delta prompts must allow "not visible" or "no change" outcomes per slot.
# - This list is about what we ALWAYS look at for that room type.
PROTOCOLS: Dict[ProtocolId, Set[SlotId]] = {
    "P1_DRY": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.balcony_doors",
        "enclosure.internal_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.hvac_distribution",
        "mep.hvac_terminals",
        "mep.heating_emitters_controls",
        # finishes
        "finishes.flooring",
        "finishes.skirting",
        "finishes.wall_finish",
        "finishes.ceiling_finish",
        # joinery
        "joinery.wardrobes_builtins",
        "joinery.custom_builtins",
        # details
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P2_KITCHEN": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.balcony_doors",
        "enclosure.internal_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "mep.ventilation_extraction",
        "mep.heating_emitters_controls",
        "mep.hot_water_generator",
        "mep.gas_supply",
        # finishes
        "finishes.flooring",
        "finishes.skirting",
        "finishes.wall_finish",
        "finishes.wall_tiling",
        "finishes.ceiling_finish",
        "finishes.joints_grout",
        "finishes.waterproofing",
        # joinery
        "joinery.kitchen_cabinetry",
        "joinery.kitchen_worktops_splashback",
        "joinery.kitchen_appliance_integration",
        # details
        "details.taps_mixers",
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P3_BATH": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.internal_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "mep.ventilation_extraction",
        "mep.heating_emitters_controls",
        "mep.hot_water_generator",
        # finishes
        "finishes.flooring",
        "finishes.wall_finish",
        "finishes.wall_tiling",
        "finishes.joints_grout",
        "finishes.ceiling_finish",
        "finishes.waterproofing",
        # joinery
        "joinery.bath_vanity_storage",
        # details
        "details.sanitary_fixtures",
        "details.bathing_units",
        "details.taps_mixers",
        "details.screens_mirrors_accessories",
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P4_TOILET": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.internal_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "mep.ventilation_extraction",
        # finishes
        "finishes.flooring",
        "finishes.wall_finish",
        "finishes.wall_tiling",
        "finishes.joints_grout",
        "finishes.ceiling_finish",
        "finishes.waterproofing",
        # joinery
        "joinery.bath_vanity_storage",
        # details
        "details.sanitary_fixtures",
        "details.taps_mixers",
        "details.screens_mirrors_accessories",
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P5_ENTRY": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.entrance_door",
        "enclosure.internal_doors",
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.balcony_doors",
        "enclosure.sealing_air_tightness",
        # mep (includes home-level by policy)
        "mep.electrical_panel",
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.testing_commissioning",
        # finishes
        "finishes.flooring",
        "finishes.skirting",
        "finishes.wall_finish",
        "finishes.ceiling_finish",
        # joinery
        "joinery.wardrobes_builtins",
        # details
        "details.intercom_entry",
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P6_EXTERIOR": {
        # shell
        # enclosure (often adjacent, but we still want it assessed for terrace/balcony clusters)
        "enclosure.balcony_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "mep.gas_supply",
        "mep.hvac_terminals",
        # finishes
        "finishes.flooring",
        "finishes.wall_finish",
        "finishes.waterproofing",
        "finishes.thermal_insulation",
        # details
        "details.electrical_trim",
    },
    "P7_GARDEN": {
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "finishes.flooring",
        "finishes.waterproofing",
    },
    "P8_LAUNDRY": {
        # shell
        "shell.masonry_chases",
        "shell.openings_changes",
        # enclosure
        "enclosure.windows",
        "enclosure.shutters_blinds",
        "enclosure.internal_doors",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        "mep.plumbing_supply",
        "mep.plumbing_drain",
        "mep.ventilation_extraction",
        "mep.hot_water_generator",
        "mep.gas_supply",
        # finishes
        "finishes.flooring",
        "finishes.skirting",
        "finishes.wall_finish",
        "finishes.ceiling_finish",
        "finishes.waterproofing",
        # joinery
        "joinery.laundry_storage",
        # details
        "details.taps_mixers",
        "details.door_hardware",
        "details.electrical_trim",
    },
    "P9_GARAGE": {
        # shell
        # enclosure
        "enclosure.internal_doors",
        "enclosure.sealing_air_tightness",
        # mep
        "mep.electrical_circuits",
        "mep.sockets_switches",
        "mep.lighting_points",
        # finishes
        "finishes.flooring",
        "finishes.wall_finish",
        "finishes.ceiling_finish",
        # details
        "details.door_hardware",
        "details.electrical_trim",
    },
    # Expanded below as “P1_DRY + extras”
    "P10_ATTIC": set(),
    "P11_BASEMENT": set(),
    "P12_STAIRS": {
        "enclosure.internal_doors",
        "mep.lighting_points",
        "finishes.flooring",
        "finishes.skirting",
        "finishes.wall_finish",
        "finishes.ceiling_finish",
        "details.door_hardware",
        "details.electrical_trim",
    },
}


PROTOCOLS["P10_ATTIC"] = set(PROTOCOLS["P1_DRY"]) | {"finishes.thermal_insulation", "finishes.waterproofing"}
PROTOCOLS["P11_BASEMENT"] = set(PROTOCOLS["P1_DRY"]) | {"mep.ventilation_extraction", "finishes.waterproofing", "finishes.thermal_insulation"}


# Room type → protocol mapping (complete for all allowlisted room types we care about).
ROOM_TYPE_TO_PROTOCOL: Dict[str, ProtocolId] = {
    "living_room": "P1_DRY",
    "dining_room": "P1_DRY",
    "kitchen": "P2_KITCHEN",
    "bedroom_primary": "P1_DRY",
    "bedroom_secondary": "P1_DRY",
    "bedroom_single": "P1_DRY",
    "nursery": "P1_DRY",
    "guest_bedroom": "P1_DRY",
    "office": "P1_DRY",
    "study_nook": "P1_DRY",
    "bathroom_full": "P3_BATH",
    "bathroom_en_suite": "P3_BATH",
    "shower_room": "P3_BATH",
    "toilet_room": "P4_TOILET",
    "powder_room": "P4_TOILET",
    "laundry_room": "P8_LAUNDRY",
    "utility_room": "P8_LAUNDRY",
    "entry_hall": "P5_ENTRY",
    "hallway": "P5_ENTRY",
    "landing": "P5_ENTRY",
    "staircase": "P12_STAIRS",
    "balcony": "P6_EXTERIOR",
    "terrace": "P6_EXTERIOR",
    "terrace_covered": "P6_EXTERIOR",
    "terrace_rooftop": "P6_EXTERIOR",
    "patio": "P6_EXTERIOR",
    "courtyard_lightwell": "P6_EXTERIOR",
    "garden": "P7_GARDEN",
    "outdoor_kitchen_bbq": "P6_EXTERIOR",
    "outdoor_storage": "P6_EXTERIOR",
    "gallery_laundry": "P8_LAUNDRY",
    "balcony_laundry": "P6_EXTERIOR",
    "service_terrace": "P6_EXTERIOR",
    "garage_private": "P9_GARAGE",
    "parking_space": "P9_GARAGE",
    "garage_storage_zone": "P9_GARAGE",
    "storage_room": "P9_GARAGE",
    "attic_habitable": "P10_ATTIC",
    "attic": "P10_ATTIC",
    "loft_mezzanine": "P1_DRY",
    "basement": "P11_BASEMENT",
    "storage_basement": "P11_BASEMENT",
    "wine_cellar": "P11_BASEMENT",
    "walk_in_closet": "P1_DRY",
    "closet_built_in_zone": "P1_DRY",
    "pantry": "P1_DRY",
    "linen_closet_zone": "P1_DRY",
    "mechanical_room": "P8_LAUNDRY",
    "boiler_closet": "P8_LAUNDRY",
    "electrical_closet": "P5_ENTRY",
    "meter_cabinet": "P5_ENTRY",
    "home_gym": "P1_DRY",
    "playroom": "P1_DRY",
    "media_room": "P1_DRY",
    "library": "P1_DRY",
    "common_area_lobby": "P6_EXTERIOR",
    "common_area_corridor": "P6_EXTERIOR",
    "elevator_lobby": "P6_EXTERIOR",
    "stairwell_common": "P6_EXTERIOR",
    "unknown_room": "P1_DRY",
    "unknown_exterior": "P6_EXTERIOR",
    # Non-room: excluded from renovation slotting
    "floorplan": "P1_DRY",
    "exterior_facade": "P6_EXTERIOR",
    "street_view": "P6_EXTERIOR",
    "views_outlook": "P6_EXTERIOR",
}


HOME_LEVEL_SLOTS: Set[SlotId] = {
    "mep.electrical_panel",
    "enclosure.entrance_door",
    "details.intercom_entry",
}


def protocol_for_room_type(room_type: str) -> ProtocolId:
    rt = str(room_type or "").strip()
    if rt in ROOM_TYPE_TO_PROTOCOL:
        return ROOM_TYPE_TO_PROTOCOL[rt]
    # Fallback by environment if possible
    spec = ROOM_TYPES_V5.get(rt)
    if spec and spec.environment == "exterior":
        return "P6_EXTERIOR"
    return "P1_DRY"

def slot_ids_for_room_type(room_type: str) -> List[SlotId]:
    """
    Fixed slot list per room type (no conditionals).

    - For open-plan types, returns the union of component room types (deduped).
    - Ordering is stable: we preserve the global slot-universe order `SLOTS_V5`.
    """
    rt = str(room_type or "").strip()
    combined = combined_types_for(rt)
    slot_set: Set[SlotId] = set()
    if combined:
        for sub_rt in combined:
            slot_set |= set(slot_ids_for_room_type(sub_rt))
    else:
        pid = protocol_for_room_type(rt)
        slot_set = set(PROTOCOLS.get(pid) or set())

    # Preserve stable ordering (helps prompts + diffs).
    return [sid for sid in SLOTS_V5 if sid in slot_set]


# Back-compat name used by earlier code. In the simplified system, all slots in the
# per-room list are treated as "required" for PIR/delta completeness checks.
def required_slot_ids(room_type: str) -> List[SlotId]:
    return slot_ids_for_room_type(room_type)


# Retained for backward compatibility with any imports; always empty in the simplified system.
def conditional_slot_ids(room_type: str) -> List[SlotId]:
    _ = room_type
    return []

