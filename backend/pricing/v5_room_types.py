"""
V5 Canonical Room Types (for constrained clustering + downstream slot protocols).

This is intentionally *English* identifiers with stable names for deterministic pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


Environment = Literal["wet", "dry", "exterior"]


@dataclass(frozen=True)
class RoomTypeSpec:
    room_type: str
    one_liner: str
    environment: Environment
    # For open-plan / studio: list of component canonical room types.
    combined_types: Optional[List[str]] = None


# Core allowlist for V5 constrained clustering.
# NOTE: If you add a new room type here, also add a slot protocol mapping in `v5_slots.py`.
ROOM_TYPES_V5: Dict[str, RoomTypeSpec] = {
    # Core interior
    "living_room": RoomTypeSpec("living_room", "Primary social space for seating/TV/lounge use.", "dry"),
    "dining_room": RoomTypeSpec("dining_room", "Space primarily arranged around a dining table for meals.", "dry"),
    "kitchen": RoomTypeSpec("kitchen", "Dedicated food-prep room with fixed cabinetry and cooking zone.", "wet"),
    "bedroom_primary": RoomTypeSpec("bedroom_primary", "Main bedroom (largest/principal sleeping room).", "dry"),
    "bedroom_secondary": RoomTypeSpec("bedroom_secondary", "Secondary bedroom used for sleeping.", "dry"),
    "bedroom_single": RoomTypeSpec("bedroom_single", "Smaller bedroom typically sized for one bed.", "dry"),
    "nursery": RoomTypeSpec("nursery", "Bedroom arranged for infant/child care (crib/changing focus).", "dry"),
    "guest_bedroom": RoomTypeSpec("guest_bedroom", "Bedroom primarily intended for visitors.", "dry"),
    "office": RoomTypeSpec("office", "Work-focused room with desk/study setup.", "dry"),
    "study_nook": RoomTypeSpec("study_nook", "Small work/study area within another room (often no door).", "dry"),
    "bathroom_full": RoomTypeSpec("bathroom_full", "Full bathroom with bath/shower plus toilet and basin.", "wet"),
    "bathroom_en_suite": RoomTypeSpec("bathroom_en_suite", "Full bathroom attached to a bedroom (suite).", "wet"),
    "shower_room": RoomTypeSpec("shower_room", "Bathroom primarily centered on a shower (often compact).", "wet"),
    "toilet_room": RoomTypeSpec("toilet_room", "WC/guest toilet with toilet and small basin, no shower/bath.", "wet"),
    "powder_room": RoomTypeSpec("powder_room", "Guest WC focused on finishes/vanity, no shower/bath.", "wet"),
    "laundry_room": RoomTypeSpec("laundry_room", "Dedicated room for washer/dryer and laundry handling.", "wet"),
    "utility_room": RoomTypeSpec("utility_room", "Service room for appliances/cleaning storage; may include laundry.", "wet"),
    "entry_hall": RoomTypeSpec("entry_hall", "Main entry/foyer area immediately inside the front door.", "dry"),
    "hallway": RoomTypeSpec("hallway", "Circulation corridor connecting rooms.", "dry"),
    "landing": RoomTypeSpec("landing", "Top/bottom of stairs acting as a small circulation node.", "dry"),
    "staircase": RoomTypeSpec("staircase", "Stairs and immediate stair zone.", "dry"),
    "storage_room": RoomTypeSpec("storage_room", "Interior storage room within the dwelling.", "dry"),
    "walk_in_closet": RoomTypeSpec("walk_in_closet", "Room-sized wardrobe/dressing space for clothing storage.", "dry"),
    "closet_built_in_zone": RoomTypeSpec("closet_built_in_zone", "Built-in wardrobe wall/zone within a bedroom (not a separate room).", "dry"),
    "pantry": RoomTypeSpec("pantry", "Food storage space adjacent to kitchen.", "dry"),
    "linen_closet_zone": RoomTypeSpec("linen_closet_zone", "Storage zone for linens/towels (often near bedrooms/baths).", "dry"),
    "garage_private": RoomTypeSpec("garage_private", "Private garage space (box or attached).", "exterior"),
    "parking_space": RoomTypeSpec("parking_space", "Marked parking bay (often underground/community).", "exterior"),
    "garage_storage_zone": RoomTypeSpec("garage_storage_zone", "Garage corner primarily used for storage/workbench.", "exterior"),
    "mechanical_room": RoomTypeSpec("mechanical_room", "Dedicated plant/technical room (boiler/heat pump/manifolds).", "dry"),
    "boiler_closet": RoomTypeSpec("boiler_closet", "Small closet housing boiler/hot-water equipment.", "dry"),
    "electrical_closet": RoomTypeSpec("electrical_closet", "Closet/zone for electrical panel/distribution.", "dry"),
    "meter_cabinet": RoomTypeSpec("meter_cabinet", "Meter box zone (gas/electric/water) inside or at entry.", "dry"),
    "attic_habitable": RoomTypeSpec("attic_habitable", "Finished attic used as habitable space.", "dry"),
    "attic": RoomTypeSpec("attic", "Under-roof space with sloped ceilings (habitable or storage).", "dry"),
    "loft_mezzanine": RoomTypeSpec("loft_mezzanine", "Partial upper platform overlooking main space.", "dry"),
    "basement": RoomTypeSpec("basement", "Below-grade level space (moisture risk).", "dry"),
    "storage_basement": RoomTypeSpec("storage_basement", "Basement primarily for storage (not fully habitable finish).", "dry"),
    "wine_cellar": RoomTypeSpec("wine_cellar", "Basement space arranged for wine storage.", "dry"),
    # Outdoor
    "balcony": RoomTypeSpec("balcony", "Small projecting outdoor space off a room.", "exterior"),
    "terrace": RoomTypeSpec("terrace", "Larger outdoor surface intended for seating/dining.", "exterior"),
    "terrace_covered": RoomTypeSpec("terrace_covered", "Terrace protected by roof/overhang (partly enclosed feel).", "exterior"),
    "terrace_rooftop": RoomTypeSpec("terrace_rooftop", "Roof-level terrace/solarium (high exposure).", "exterior"),
    "patio": RoomTypeSpec("patio", "Ground-level open-to-sky outdoor courtyard space.", "exterior"),
    "courtyard_lightwell": RoomTypeSpec("courtyard_lightwell", "Small internal patio/lightwell mainly for ventilation/light.", "exterior"),
    "garden": RoomTypeSpec("garden", "Planted outdoor area with landscaping.", "exterior"),
    "outdoor_kitchen_bbq": RoomTypeSpec("outdoor_kitchen_bbq", "Exterior cooking/prep zone (built-in counter/grill focus).", "exterior"),
    "outdoor_storage": RoomTypeSpec("outdoor_storage", "Exterior storage shed/closet for bins/tools.", "exterior"),
    "gallery_laundry": RoomTypeSpec("gallery_laundry", "Enclosed/part-enclosed gallery used for laundry/utility off kitchen.", "wet"),
    "balcony_laundry": RoomTypeSpec("balcony_laundry", "Balcony used primarily for laundry drying/washer placement.", "exterior"),
    "service_terrace": RoomTypeSpec("service_terrace", "Small terrace used for utilities (boiler units, storage, laundry).", "exterior"),
    # Building / building-adjacent (usually excluded from private renovation, but may appear in photos)
    "common_area_lobby": RoomTypeSpec("common_area_lobby", "Building lobby/hall (not private dwelling interior).", "dry"),
    "common_area_corridor": RoomTypeSpec("common_area_corridor", "Shared corridor outside the unit.", "dry"),
    "elevator_lobby": RoomTypeSpec("elevator_lobby", "Shared zone around elevator.", "dry"),
    "stairwell_common": RoomTypeSpec("stairwell_common", "Shared building stairs.", "dry"),
    # Lifestyle rooms (optional)
    "home_gym": RoomTypeSpec("home_gym", "Room arranged for fitness equipment.", "dry"),
    "playroom": RoomTypeSpec("playroom", "Room arranged primarily for children’s play.", "dry"),
    "media_room": RoomTypeSpec("media_room", "Dedicated cinema/TV room with seating focus.", "dry"),
    "library": RoomTypeSpec("library", "Room dominated by shelves/reading function.", "dry"),
    # Open plan / studio (explicit combined)
    "open_plan_kitchen_living": RoomTypeSpec(
        "open_plan_kitchen_living",
        "Single continuous space combining kitchen + living (no full-height separation).",
        "dry",
        combined_types=["kitchen", "living_room"],
    ),
    "open_plan_kitchen_dining": RoomTypeSpec(
        "open_plan_kitchen_dining",
        "Single continuous space combining kitchen + dining.",
        "dry",
        combined_types=["kitchen", "dining_room"],
    ),
    "open_plan_living_dining": RoomTypeSpec(
        "open_plan_living_dining",
        "Single continuous space combining living + dining.",
        "dry",
        combined_types=["living_room", "dining_room"],
    ),
    "open_plan_kitchen_living_dining": RoomTypeSpec(
        "open_plan_kitchen_living_dining",
        "Single continuous main space combining kitchen + living + dining.",
        "dry",
        combined_types=["kitchen", "living_room", "dining_room"],
    ),
    "studio_main_space": RoomTypeSpec(
        "studio_main_space",
        "One main habitable space combining sleeping + living and often kitchenette.",
        "dry",
        combined_types=["kitchen", "living_room", "bedroom_secondary"],
    ),
    # Non-room / auxiliary
    "floorplan": RoomTypeSpec("floorplan", "Plan drawing/diagram images (not a room cluster).", "dry"),
    "exterior_facade": RoomTypeSpec("exterior_facade", "Outside building façade views (not a room).", "exterior"),
    "street_view": RoomTypeSpec("street_view", "Street/public realm view near the property.", "exterior"),
    "views_outlook": RoomTypeSpec("views_outlook", "Views from windows/terrace (not the room itself).", "exterior"),
    "unknown_room": RoomTypeSpec("unknown_room", "Interior space that can’t be confidently typed.", "dry"),
    "unknown_exterior": RoomTypeSpec("unknown_exterior", "Exterior space that can’t be confidently typed.", "exterior"),
}


def is_open_plan(room_type: str) -> bool:
    spec = ROOM_TYPES_V5.get(str(room_type))
    return bool(spec and spec.combined_types)


def combined_types_for(room_type: str) -> List[str]:
    spec = ROOM_TYPES_V5.get(str(room_type))
    if not spec or not spec.combined_types:
        return []
    return list(spec.combined_types)

