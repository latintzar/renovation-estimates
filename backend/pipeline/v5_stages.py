"""
V5 Pipeline Stage Registry
===========================

Single source of truth for stage ordering, job types, artifact mappings,
and per-stage version tracking.

Imported by:
- admin_routes.py     → clear-from-stage API, staleness detection
- rerun_from_stage.py → CLI clear + requeue
- v2_scheduler.py     → (reference — enqueue order matches this)

VERSION TRACKING:
Each stage has a `version` string. Bump it when you change that stage's
logic, prompt, or schema. The admin dashboard compares the version stored
in each run's config with the current version here and flags stale listings.

Convention: use ISO date + optional suffix, e.g. "2026-02-12", "2026-02-12b"
"""

from typing import Dict, List, Tuple

# ─── Stage sequence ──────────────────────────────────────────────────────────
# (stage_name, job_type, artifacts_to_delete, version)
#
# Artifact specs:
#   "ue:<key>"       → unified_estimates where package_type = <key>
#   "ue_like:<pat>"  → unified_estimates where package_type LIKE <pat>
#   "boq_v4"         → boq_line_items where dimension = 'v4'
#   "smart_m2"       → smart_m2 table rows
#   "photo_clusters" → photo_clusters table rows

V5_STAGE_SEQUENCE: List[Tuple[str, str, List[str], str]] = [
    ("snapshot",        "v5_fetch_listing_snapshot",               ["ue:v5_listing_snapshot"],                                         "2026-02-12"),
    ("comparables",     "fetch_comparables",                       ["listing_comparables", "market_stats_cache"],                      "2026-02-17"),
    ("comparables",     "v5_fetch_comparables_snapshot",           ["ue:v5_comparables"],                                              "2026-02-12"),
    ("clustering",      "v5_cluster_target_photos",                ["ue:v5_clusters", "photo_clusters"],                               "2026-02-12"),
    ("v5_room_tags",    "v5_room_tags",                            ["ue:v5_room_tags"],                                                "2026-02-12"),
    ("v5_pir",          "v5_generate_target_pir_slots",            ["ue:v5_pir_target"],                                               "2026-02-12"),
    ("v5_select",       "v5_select_median_comparable",             ["ue:v5_selected_comparable"],                                      "2026-02-12"),
    ("v5_comparables",  "v5_cluster_selected_comparable_photos",   ["ue_like:v5_selected_comparable_clusters_%"],                       "2026-02-12"),
    ("v5_comparables",  "v5_generate_selected_comparable_room_pirs", ["ue_like:v5_selected_comparable_room_pirs_%", "ue_like:v5_selected_comparable_slot_standard_%"], "2026-02-12"),
    ("v5_delta",        "v5_delta_slots_market_standard",          ["ue:v5_delta_slots_market_standard"],                              "2026-02-12b"),
    # Cross-room delta review is implemented inside the delta handler, but it is a distinct artifact.
    # Keeping it as a separate stage improves admin/reno status visibility and clear-from-stage semantics.
    ("v5_delta_review", "v5_delta_slots_market_standard",          ["ue:v5_delta_review_market_standard"],                             "2026-02-12b"),
    ("v5_decompose",    "v5_work_items_market_standard",           ["ue:v5_work_items_market_standard"],                               "2026-02-12"),
    ("v5_smart_m2",     "v5_smart_m2",                             ["smart_m2"],                                                       "2026-02-12"),
    ("v5_bcca_match",   "v5_bcca_match",                           ["ue_like:v4_bcca_matches_%"],                                      "2026-02-12"),
    ("v5_quant_plan",   "v5_quant_plan",                           ["ue_like:v4_quant_plan_%"],                                        "2026-02-12"),
    ("v5_forage",       "v5_forage",                               ["ue_like:v4_signals_%", "ue:v4_signals_shared"],                   "2026-02-12"),
    ("v5_boq_assembly", "v5_boq_assembly",                         ["boq_v4", "ue_like:v4_run_summary_%", "ue:v2_market_standard"],    "2026-02-12"),
    ("v5_finalize",     "v5_finalize",                             ["ue:v2_delta_market_standard"],                                    "2026-02-12"),
    ("v5_eli5",         "v5_eli5",                                 ["ue:v5_eli5_market_standard"],                                     "2026-02-12"),
    ("v5_negotiation",  "v5_negotiation",                          ["ue:v5_negotiation"],                                              "2026-02-15"),
    ("v5_room_images",  "v5_room_images",                          ["ue:v5_room_images_defurnish_market_standard", "ue:v5_room_images_prompt_generation_market_standard", "ue:v5_room_images_style_consistency_market_standard", "ue:v5_generated_images_market_standard"], "2026-02-12b"),
    ("v5_translations", "v5_translations",                         ["ue:v5_translations"],                                             "2026-02-15"),
]

# Derived helpers
STAGE_NAMES_UNIQUE: List[str] = list(dict.fromkeys(s[0] for s in V5_STAGE_SEQUENCE))

# Set of all V5 job_type values — used to filter out legacy/deprecated jobs
V5_JOB_TYPES: set = {job_type for _, job_type, _, _ in V5_STAGE_SEQUENCE}

# Ordered V5 job types (deduplicated by first appearance in stage sequence).
# WHY THIS MATTERS: workers can gate execution on the direct predecessor so jobs
# run in strict order instead of relying on best-effort prerequisite checks.
V5_ORDERED_JOB_TYPES: List[str] = []
for _stage, _job_type, _artifacts, _version in V5_STAGE_SEQUENCE:
    if _job_type not in V5_ORDERED_JOB_TYPES:
        V5_ORDERED_JOB_TYPES.append(_job_type)

# Direct predecessor mapping for linear V5 execution.
V5_JOB_PREDECESSOR: Dict[str, str] = {
    V5_ORDERED_JOB_TYPES[i]: V5_ORDERED_JOB_TYPES[i - 1]
    for i in range(1, len(V5_ORDERED_JOB_TYPES))
}

def get_stage_versions() -> Dict[str, str]:
    """Current version for each stage (latest wins if stage appears multiple times)."""
    versions: Dict[str, str] = {}
    for stage, _, _, version in V5_STAGE_SEQUENCE:
        versions[stage] = version
    return versions

def get_stages_from(from_stage: str) -> List[Tuple[str, str, List[str], str]]:
    """Return all stages from `from_stage` onward (inclusive). Raises ValueError if unknown."""
    from_idx = None
    for i, (stage, _, _, _) in enumerate(V5_STAGE_SEQUENCE):
        if stage == from_stage:
            from_idx = i
            break
    if from_idx is None:
        raise ValueError(f"Unknown stage: '{from_stage}'. Valid: {', '.join(STAGE_NAMES_UNIQUE)}")
    return V5_STAGE_SEQUENCE[from_idx:]

STAGE_LABELS: Dict[str, str] = {
    "snapshot": "Snapshot",
    "comparables": "Comparables",
    "clustering": "Clustering",
    "v5_room_tags": "Room Tags",
    "v5_pir": "PIR Analysis",
    "v5_select": "Select Comparable",
    "v5_comparables": "Comparable Analysis",
    "v5_delta": "Delta Analysis",
    "v5_delta_review": "Delta Review",
    "v5_decompose": "Work Items",
    "v5_smart_m2": "Smart M²",
    "v5_bcca_match": "BCCA Matching",
    "v5_quant_plan": "Quantity Plan",
    "v5_forage": "Photo Signals",
    "v5_boq_assembly": "BOQ Assembly",
    "v5_finalize": "Finalize",
    "v5_eli5": "ELI5 Summary",
    "v5_negotiation": "Negotiation Guide",
    "v5_room_images": "Room Images",
    "v5_translations": "Translations",
    # Status-only sub-stages inside v5_room_images (derived from progress events)
    "v5_room_images_defurnish": "Photo Defurnishing",
    "v5_room_images_prompt_generation": "Prompt Generation",
    "v5_room_images_style_consistency": "Style Consistency",
    "v5_room_images_photo_generation": "Photo Generation",
}

# Ordered room-image sub-stages (status-only; no dedicated pipeline jobs).
ROOM_IMAGE_STATUS_STAGES: List[str] = [
    "v5_room_images_defurnish",
    "v5_room_images_prompt_generation",
    "v5_room_images_style_consistency",
    "v5_room_images_photo_generation",
]
