"""
V5 Photo Clustering (constrained canonical room types)
=====================================================

V5 differs from V0.5 clustering in one key way:
- the model MUST choose from a canonical allowlist of room types (English IDs),
  and must number multiples (_1, _2, ...).

This allows downstream slot protocols and PIR schemas to be deterministic.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pipeline.gemini_client import call_gemini, fetch_images_batch
from pricing.v5_room_types import ROOM_TYPES_V5

logger = logging.getLogger(__name__)

_COMMON_AREA_ROOM_TYPES = {
    "common_area_lobby",
    "common_area_corridor",
    "elevator_lobby",
    "stairwell_common",
}


V5_CLUSTERING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cluster_label": {"type": "string"},  # e.g., "kitchen_1", "bathroom_full_2"
                    "room_type": {"type": "string", "enum": sorted(list(ROOM_TYPES_V5.keys()))},
                    "photo_indices": {"type": "array", "items": {"type": "integer"}},
                    "confidence": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["cluster_label", "room_type", "photo_indices"],
            },
        },
        "excluded_content": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    # IMPORTANT: excluded_content is how we remove non-unit photos from renovation scope.
                    # "building_common_area" covers stairwells, lobbies, shared corridors, elevator halls, etc.
                    "type": {
                        "type": "string",
                        "enum": [
                            "building_common_area",
                            "building_exterior",
                            "street_view",
                            "views_outlook",
                            "floorplan",
                            "document",
                            "ai_generated",
                            "render",
                            "view",
                            "other",
                        ],
                    },
                    "photo_indices": {"type": "array", "items": {"type": "integer"}},
                    "reason": {"type": "string"},
                },
                "required": ["type", "photo_indices"],
            },
        },
    },
    "required": ["clusters"],
}


def build_v5_clustering_prompt(*, listing_context: str, photo_count: int) -> str:
    allowlist = [
        {
            "room_type": k,
            "definition": v.one_liner,
        }
        for k, v in ROOM_TYPES_V5.items()
        if k not in ("floorplan", "exterior_facade", "street_view")
    ]
    return f"""
You are an expert at analyzing property photos and clustering them into room groups.

IMPORTANT: This is V5 constrained clustering. You MUST use the canonical room_type allowlist below.

{listing_context}

PHOTOS:
- Photos are indexed from 0 to {photo_count - 1}
- Every photo index must appear exactly once either in a cluster or in excluded_content.

OUTPUT REQUIREMENTS:
1) Create clusters with:
   - room_type: one of the allowlist IDs
   - cluster_label: room_type + '_' + number starting at 1, e.g. 'kitchen_1', 'bathroom_full_2'
2) EXCLUDE non-unit content (preferred: put into excluded_content):
   - Building common areas (stairwells, lobby, shared corridors, elevator halls): excluded_content type='building_common_area'
   - Building exterior facade (not a private terrace/balcony): type='building_exterior'
   - Street/outside public realm: type='street_view'
   - Views/outlook shots that aren't the space itself: type='views_outlook' (or type='view')
   - Floorplans: type='floorplan'
3) If you detect a FLOORPLAN among the photos:
   - Put its photo index in excluded_content with type='floorplan'
   - USE it as a REFERENCE to improve clustering (room count, adjacency, and to sanity-check bedroom/bath/kitchen/living placement)
2) Open-plan spaces:
   - If kitchen and living/dining share one continuous space, use the open_plan_* room_type.
3) Studio:
   - If the home is a studio, use studio_main_space for the main room (bathroom separate).
4) Do NOT invent new room types.
5) Return ONLY valid JSON matching the schema.

ROOM TYPE ALLOWLIST (canonical):
{json.dumps(allowlist, ensure_ascii=False, indent=2)}
""".strip()


async def cluster_photos_v5(
    *,
    listing_context: str,
    photo_urls: List[str],
    property_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if not photo_urls:
        raise RuntimeError("v5 clustering: no photos provided")

    images = await fetch_images_batch(photo_urls)
    # IMPORTANT: We rely on photo index ordering matching the provided images order.
    # If any images are missing, indices become ambiguous (SDK does not label images).
    if any(img is None for img in images):
        missing = [i for i, img in enumerate(images) if img is None]
        raise RuntimeError(f"v5 clustering: image fetch failed for some photos; cannot preserve indices | missing={missing}")
    valid_images = [img for img in images if img is not None]
    if not valid_images:
        raise RuntimeError("v5 clustering: failed to fetch any images")

    prompt = build_v5_clustering_prompt(listing_context=listing_context, photo_count=len(photo_urls))
    logger.info("v5_clustering: calling gemini pro (no fallback)")
    resp = await call_gemini(
        prompt=prompt,
        images=valid_images,
        model="pro",
        temperature=0.1,
        response_schema=V5_CLUSTERING_SCHEMA,
        no_fallback=True,
        thinking_level="high",
    )
    if not resp.success:
        raise RuntimeError(f"v5 clustering: gemini failed: {resp.error}")
    try:
        out = json.loads(resp.text)
    except Exception as exc:
        raise RuntimeError(f"v5 clustering: JSON parse failed: {exc}") from exc

    raw_excluded = out.get("excluded_content") or []
    if not isinstance(raw_excluded, list):
        raw_excluded = []

    # Attach photo_urls to clusters to match the existing cluster structure expectations.
    # Keep it simple: map indices to urls for downstream PIR calls.
    excluded_out: List[Dict[str, Any]] = []
    assigned: set[int] = set()

    def _push_excluded(ex_type: str, indices: List[int], reason: str) -> None:
        clean = []
        for i in indices or []:
            if isinstance(i, int) and 0 <= i < len(photo_urls) and i not in assigned:
                clean.append(i)
                assigned.add(i)
        if not clean:
            return
        excluded_out.append(
            {
                "type": str(ex_type or "other"),
                "photo_indices": sorted(set(clean)),
                "reason": str(reason or "").strip(),
            }
        )

    # First, respect model-provided excluded_content (deduped and range-checked).
    for e in raw_excluded:
        if not isinstance(e, dict):
            continue
        et = str(e.get("type") or "other").strip() or "other"
        pis = e.get("photo_indices") or []
        rsn = str(e.get("reason") or "").strip()
        _push_excluded(et, pis if isinstance(pis, list) else [], rsn)

    clusters_out = []
    for c in out.get("clusters") or []:
        if not isinstance(c, dict):
            continue
        room_type = str(c.get("room_type") or "").strip() or "unknown_room"
        label = str(c.get("cluster_label") or "").strip() or room_type
        raw_indices = c.get("photo_indices") or []
        if not isinstance(raw_indices, list):
            raw_indices = []
        indices = []
        for i in raw_indices:
            if not (isinstance(i, int) and 0 <= i < len(photo_urls)):
                continue
            if i in assigned:
                continue
            indices.append(i)
            assigned.add(i)

        # If the model labeled non-unit spaces as clusters, move them to excluded_content.
        if room_type in _COMMON_AREA_ROOM_TYPES:
            _push_excluded("building_common_area", indices, f"Auto-excluded common area cluster: {label}")
            continue
        if room_type in ("exterior_facade",):
            _push_excluded("building_exterior", indices, f"Auto-excluded building exterior cluster: {label}")
            continue
        if room_type in ("street_view",):
            _push_excluded("street_view", indices, f"Auto-excluded street view cluster: {label}")
            continue
        if room_type in ("views_outlook",):
            _push_excluded("views_outlook", indices, f"Auto-excluded views/outlook cluster: {label}")
            continue
        if room_type in ("floorplan",):
            _push_excluded("floorplan", indices, f"Auto-excluded floorplan cluster: {label}")
            continue

        urls = [photo_urls[i] for i in indices]
        clusters_out.append(
            {
                "cluster_name": label,
                "cluster_id": label,
                "room_type": room_type,
                "photo_indices": indices,
                "photo_urls": urls,
                "confidence": c.get("confidence", 0.0),
                "description": c.get("notes") or "",
            }
        )

    # Finally, auto-exclude any missing/unassigned indices so the stage is always complete.
    missing = [i for i in range(len(photo_urls)) if i not in assigned]
    if missing:
        _push_excluded("other", missing, "Auto-excluded: unassigned by model (completeness guardrail)")

    return {
        "clusters": clusters_out,
        "excluded_content": excluded_out,
        "version": "v5",
    }

