"""
GLA Pipeline Stage Registry
==========================

GLA (General Listing Analysis) is a lighter, no-comparables pipeline intended to:
- build a listing snapshot
- cluster photos and tag rooms
- run target PIR slots
- compute Smart M2 dimensions
- produce Leo's "opinion" narratives per room (what should/could be done)

This file is the single source of truth for:
- stage ordering
- job type ordering (deduped)
- predecessor graph (linear chain)
- per-stage version tracking

WHY THIS MATTERS:
The worker gates each job on its direct predecessor so the pipeline executes in a
strict, deterministic order, and the admin dashboard can detect stale runs by
comparing stored versions against current versions here.

Convention: use ISO date + optional suffix, e.g. "2026-02-15", "2026-02-15b"
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# ─── Stage sequence ──────────────────────────────────────────────────────────
# (stage_name, job_type, artifacts_to_delete, version)
#
# Artifact specs (shared with V5 conventions):
#   "ue:<key>"       → unified_estimates where package_type = <key>
#   "ue_like:<pat>"  → unified_estimates where package_type LIKE <pat>
#   "smart_m2"       → smart_m2 table rows
#   "photo_clusters" → photo_clusters table rows

GLA_STAGE_SEQUENCE: List[Tuple[str, str, List[str], str]] = [
    ("snapshot",   "gla_fetch_listing_snapshot",          ["ue:v5_listing_snapshot"],  "2026-02-15"),
    ("clustering", "gla_cluster_target_photos",           ["ue:v5_clusters", "photo_clusters"], "2026-02-15"),
    ("room_tags",  "gla_room_tags",                       ["ue:v5_room_tags"],         "2026-02-15"),
    ("pir",        "gla_generate_target_pir_slots",       ["ue:v5_pir_target"],         "2026-02-15"),
    ("smart_m2",   "gla_smart_m2",                        ["smart_m2"],                 "2026-02-15"),
    ("opinion",    "gla_opinion",                         ["ue:gla_opinion"],           "2026-02-15"),
]

# Ordered GLA job types (deduplicated by first appearance in stage sequence).
GLA_ORDERED_JOB_TYPES: List[str] = []
for _stage, _job_type, _artifacts, _version in GLA_STAGE_SEQUENCE:
    if _job_type not in GLA_ORDERED_JOB_TYPES:
        GLA_ORDERED_JOB_TYPES.append(_job_type)

# Direct predecessor mapping for linear GLA execution.
GLA_JOB_PREDECESSOR: Dict[str, str] = {
    GLA_ORDERED_JOB_TYPES[i]: GLA_ORDERED_JOB_TYPES[i - 1]
    for i in range(1, len(GLA_ORDERED_JOB_TYPES))
}

STAGE_LABELS: Dict[str, str] = {
    "snapshot": "Snapshot",
    "clustering": "Clustering",
    "room_tags": "Room Tags",
    "pir": "PIR Analysis",
    "smart_m2": "Smart M²",
    "opinion": "Leo Opinion",
}


def get_gla_stage_versions() -> Dict[str, str]:
    """Current version for each stage (latest wins if stage appears multiple times)."""
    versions: Dict[str, str] = {}
    for stage, _job_type, _artifacts, version in GLA_STAGE_SEQUENCE:
        versions[stage] = version
    return versions

