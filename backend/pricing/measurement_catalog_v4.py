"""
V4 Measurement Catalog
======================

This module defines the *canonical* list of measurement signals the system can request.

WHY THIS MATTERS:
- V4 separates “what to do” (scope + BCCA match) from “how to measure it” (signals + formula).
- The Quantification Planner must ONLY reference signals from this catalog.
- The Smart M2 Forage step must ONLY output signals requested by the planner.
- The deterministic evaluator must fail loud if a plan references an unknown signal.

Floorplan-first policy:
- If a floorplan exists, it is the primary authority for count/layout signals where applicable.
- If no floorplan exists, some signals may be provable from photos or Smart M2 primitives.
- Some signals are not reliably provable and must never be requested without an explicit default rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


UnitFamily = Literal["m2", "ml", "ud", "m3"]
ProvableFrom = Literal["floorplan", "photos", "either", "not_reliably_provable"]
PreferredSource = Literal["floorplan", "photos", "smart_m2"]


@dataclass(frozen=True)
class MeasurementSignalSpec:
    signal_id: str
    unit_family: UnitFamily
    provable_from: ProvableFrom
    preferred_sources: List[PreferredSource]
    description: str

    # If set, indicates this signal can be read deterministically from Smart M2 data,
    # without an additional forage step. The evaluator/assembler can use this to
    # pre-fill signals.
    smart_m2_path: Optional[str] = None

    # Defaulting policy:
    # - If defaultable is false, the pipeline should fail if the signal cannot be proven.
    # - If defaultable is true, a downstream deterministic default rule must exist.
    defaultable: bool = False
    default_rule_notes: Optional[str] = None


def _spec(
    *,
    signal_id: str,
    unit_family: UnitFamily,
    provable_from: ProvableFrom,
    preferred_sources: List[PreferredSource],
    description: str,
    smart_m2_path: Optional[str] = None,
    defaultable: bool = False,
    default_rule_notes: Optional[str] = None,
) -> MeasurementSignalSpec:
    if not signal_id or not isinstance(signal_id, str):
        raise ValueError("measurement_catalog_v4: signal_id is required")
    if not preferred_sources:
        raise ValueError(f"measurement_catalog_v4: preferred_sources empty | signal_id={signal_id}")
    if defaultable and not default_rule_notes:
        raise ValueError(f"measurement_catalog_v4: defaultable requires default_rule_notes | signal_id={signal_id}")
    return MeasurementSignalSpec(
        signal_id=signal_id,
        unit_family=unit_family,
        provable_from=provable_from,
        preferred_sources=preferred_sources,
        description=description,
        smart_m2_path=smart_m2_path,
        defaultable=defaultable,
        default_rule_notes=default_rule_notes,
    )


# NOTE: This is intentionally conservative and starts by mapping to existing Smart M2 primitives.
# We can expand once the V4 planner+forager is in place.
CATALOG: Dict[str, MeasurementSignalSpec] = {
    # -------------------------------------------------------------------------
    # Room geometry (usually “either”: floorplan is ideal; Smart M2 is acceptable)
    # -------------------------------------------------------------------------
    "room_floor_area_m2": _spec(
        signal_id="room_floor_area_m2",
        unit_family="m2",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Floor area of the room (plan area).",
        smart_m2_path="rooms[].estimated_m2",
    ),
    "room_ceiling_area_m2": _spec(
        signal_id="room_ceiling_area_m2",
        unit_family="m2",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Ceiling area of the room (usually equal to floor area).",
        smart_m2_path="rooms[].takeoff_primitives.ceiling_finish_m2.value",
    ),
    "room_wall_net_area_m2": _spec(
        signal_id="room_wall_net_area_m2",
        unit_family="m2",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Net wall area (gross wall area minus openings).",
        smart_m2_path="rooms[].wall_net_m2",
    ),
    "room_wall_gross_area_m2": _spec(
        signal_id="room_wall_gross_area_m2",
        unit_family="m2",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Gross wall area (before subtracting openings).",
        smart_m2_path="rooms[].wall_gross_m2",
    ),
    "room_perimeter_ml": _spec(
        signal_id="room_perimeter_ml",
        unit_family="ml",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Perimeter of the room at floor line (used for skirting/coving runs).",
        smart_m2_path="rooms[].takeoff_primitives.room_perimeter_ml.value",
    ),
    "skirting_net_ml": _spec(
        signal_id="skirting_net_ml",
        unit_family="ml",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2"],
        description="Net skirting run length (perimeter minus door/balcony door widths).",
        smart_m2_path="rooms[].takeoff_primitives.skirting_net_ml.value",
    ),
    # -------------------------------------------------------------------------
    # Openings (counts/areas) — floorplan is ideal; Smart M2/Photos acceptable.
    # -------------------------------------------------------------------------
    "openings_total_area_m2": _spec(
        signal_id="openings_total_area_m2",
        unit_family="m2",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2", "photos"],
        description="Total opening area in the room (sum of doors/windows/balcony doors).",
        smart_m2_path="rooms[].openings_total_area_m2",
    ),
    "door_count_ud": _spec(
        signal_id="door_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2", "photos"],
        description="Count of interior doors in the room.",
        smart_m2_path="rooms[].opening_aggregates.counts_by_type.door",
    ),
    "window_count_ud": _spec(
        signal_id="window_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2", "photos"],
        description="Count of windows in the room.",
        smart_m2_path="rooms[].opening_aggregates.counts_by_type.window",
    ),
    "balcony_door_count_ud": _spec(
        signal_id="balcony_door_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "smart_m2", "photos"],
        description="Count of balcony doors / terrace access openings in the room.",
        smart_m2_path="rooms[].opening_aggregates.counts_by_type.balcony_door",
    ),
    # -------------------------------------------------------------------------
    # MEP point counts — floorplan-first; photos are unreliable; defaulting discouraged.
    # -------------------------------------------------------------------------
    "light_point_count_ud": _spec(
        signal_id="light_point_count_ud",
        unit_family="ud",
        provable_from="floorplan",
        preferred_sources=["floorplan"],
        description="Count of light points in the room (plan symbols).",
        defaultable=False,
    ),
    "socket_count_ud": _spec(
        signal_id="socket_count_ud",
        unit_family="ud",
        provable_from="floorplan",
        preferred_sources=["floorplan"],
        description="Count of power sockets in the room (plan symbols).",
        defaultable=False,
    ),
    "switch_count_ud": _spec(
        signal_id="switch_count_ud",
        unit_family="ud",
        provable_from="floorplan",
        preferred_sources=["floorplan"],
        description="Count of light switches in the room (plan symbols).",
        defaultable=False,
    ),
    # -------------------------------------------------------------------------
    # Fixtures / built-ins — photos-first; floorplan may exist but not guaranteed.
    # -------------------------------------------------------------------------
    "radiator_count_ud": _spec(
        signal_id="radiator_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "photos", "smart_m2"],
        description="Count of radiators in the room.",
        smart_m2_path="rooms[].feature_aggregates.counts_by_type.radiator",
    ),
    "boiler_count_ud": _spec(
        signal_id="boiler_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "photos", "smart_m2"],
        description="Count of boilers/combination units (typically 0 or 1).",
        smart_m2_path="rooms[].feature_aggregates.counts_by_type.boiler",
    ),
    "electrical_panel_count_ud": _spec(
        signal_id="electrical_panel_count_ud",
        unit_family="ud",
        provable_from="either",
        preferred_sources=["floorplan", "photos", "smart_m2"],
        description="Count of electrical panels/consumer units (typically 0 or 1).",
        smart_m2_path="rooms[].feature_aggregates.counts_by_type.electrical_panel",
    ),
    "countertop_run_ml": _spec(
        signal_id="countertop_run_ml",
        unit_family="ml",
        provable_from="either",
        preferred_sources=["floorplan", "photos", "smart_m2"],
        description="Total linear run of countertop surfaces in the room.",
        smart_m2_path="rooms[].feature_aggregates.quantity_sums_by_type_and_unit.countertop_run.ml",
    ),
    "wardrobe_run_ml": _spec(
        signal_id="wardrobe_run_ml",
        unit_family="ml",
        provable_from="either",
        preferred_sources=["floorplan", "photos", "smart_m2"],
        description="Total linear run of built-in wardrobes in the room.",
        smart_m2_path="rooms[].feature_aggregates.quantity_sums_by_type_and_unit.wardrobe_run.ml",
    ),
}


def get_measurement_signal_spec(signal_id: str) -> MeasurementSignalSpec:
    if not signal_id or not isinstance(signal_id, str):
        raise ValueError("measurement_catalog_v4: signal_id must be a non-empty string")
    spec = CATALOG.get(signal_id)
    if not spec:
        raise KeyError(f"measurement_catalog_v4: unknown signal_id={signal_id} | known={sorted(CATALOG.keys())}")
    return spec


def list_measurement_signal_specs() -> List[MeasurementSignalSpec]:
    return [CATALOG[k] for k in sorted(CATALOG.keys())]


def validate_catalog() -> None:
    """
    Fail-loud validator for internal consistency.
    Call this in smoke tests and in any import-time validations if desired.
    """
    if not CATALOG:
        raise RuntimeError("measurement_catalog_v4: CATALOG is empty")
    for sid, spec in CATALOG.items():
        if sid != spec.signal_id:
            raise RuntimeError(f"measurement_catalog_v4: key mismatch | key={sid} spec.signal_id={spec.signal_id}")
        if spec.unit_family not in ("m2", "ml", "ud", "m3"):
            raise RuntimeError(f"measurement_catalog_v4: invalid unit_family | signal_id={sid} unit_family={spec.unit_family}")
        if not spec.description.strip():
            raise RuntimeError(f"measurement_catalog_v4: empty description | signal_id={sid}")
        if spec.defaultable and not spec.default_rule_notes:
            raise RuntimeError(f"measurement_catalog_v4: defaultable missing default_rule_notes | signal_id={sid}")


def as_public_catalog_json() -> Dict[str, Any]:
    """
    JSON-safe representation suitable for embedding in planner prompts.
    """
    validate_catalog()
    out: Dict[str, Any] = {}
    for sid, spec in CATALOG.items():
        out[sid] = {
            "unit_family": spec.unit_family,
            "provable_from": spec.provable_from,
            "preferred_sources": spec.preferred_sources,
            "description": spec.description,
            "defaultable": spec.defaultable,
            "default_rule_notes": spec.default_rule_notes,
        }
    return out

