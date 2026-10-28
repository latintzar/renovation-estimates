"""
Photo Clustering Module (V0.5)
==============================

Zero-shot clustering of property photos by room + AI image detection.
Extracted from photo_analysis.py for standalone use in V0.4.8+ pipeline.

V0.5 CHANGE: no_fallback=True
-----------------------------
Clustering quality is CRITICAL to the entire pipeline. If the Pro model
is rate-limited, we FAIL FAST rather than falling back to Flash which
produces lower-quality room assignments.

Functions:
- cluster_photos(): Main entry point for V0.4.8+ pipeline
- cluster_photos_direct(): Direct clustering without orchestrator
- get_p1_clustering_prompt(): Build the clustering prompt

Model: gemini-3-pro-preview (vision analysis) - NO FALLBACK
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple

from ..gemini_client import call_gemini, fetch_images_batch

logger = logging.getLogger(__name__)


CLUSTER_REFINEMENT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string"},
                    "room_type": {"type": "string"},
                    "photo_indices": {"type": "array", "items": {"type": "integer"}},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"},
                    "is_real": {"type": "boolean"},
                },
                "required": ["cluster_name", "room_type", "photo_indices"],
            },
        }
    },
    "required": ["clusters"],
}


# =============================================================================
# PROMPTS
# =============================================================================

def get_p1_clustering_prompt(listing_context: str, photo_count: int, property_flags: List[str] = None) -> str:
    """
    Build prompt for P1 zero-shot clustering with AI image detection.
    
    This prompt is derived from the ORIGINAL zero-shot clustering methodology
    that "worked like a dream" - preserving ALL the visual-priority instructions.
    """
    
    # Add context about property flags if known
    flag_context = ""
    if property_flags:
        if "squatted" in property_flags:
            flag_context += "\n⚠️ NOTE: This property is SQUATTED/OCCUPIED and cannot be visited. Photos may be limited or old."
        if "off_plan" in property_flags:
            flag_context += "\n⚠️ NOTE: This property is OFF-PLAN/UNDER CONSTRUCTION. Expect renders and marketing materials."
        if "renovation_renders" in property_flags:
            flag_context += "\n⚠️ NOTE: This listing may contain virtual staging or renovation renders."
    
    return f"""You are an expert at analyzing property photos, organizing them into logical room clusters,
AND detecting AI-generated/rendered images.

{listing_context}
{flag_context}

TASK: Analyze all {photo_count} photos and:
1. Classify each photo as REAL or AI-GENERATED/RENDER
2. Cluster the REAL photos into logical room groups
3. Separate AI-generated content

PHOTOS: Photos are indexed from 0 to {photo_count - 1}. Analyze each photo carefully.

═══════════════════════════════════════════════════════════════════════════════
AI/RENDER DETECTION RULES
═══════════════════════════════════════════════════════════════════════════════
Look for these telltale signs of AI-generated or rendered images:
- Perfect symmetry, impossibly clean surfaces
- Unusual lighting/shadows (too perfect or physically impossible)
- Repetitive textures (clone stamp artifacts, repeating patterns in walls/floors)
- Missing details (no light switches, outlets, door handles)
- Unnatural furniture placement or floating objects
- Inconsistent perspective or distorted proportions
- "Too good to be true" renovations with impossible finishes
- Watermarks indicating "virtual staging" or "render"

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: PRIORITIZE VISUAL CONTINUITY OF EACH PHYSICAL SPACE
═══════════════════════════════════════════════════════════════════════════════

1. SCAN ALL PHOTOS and group images that share the same SHELL:
   - Flooring (tile patterns, wood grain, carpet)
   - Wall finishes (paint color, texture, wallpaper)
   - Ceiling height
   - Fixed architectural elements (walls, doors, columns, windows)

2. USE REPEATING VISUAL PATTERNS AND TEXTURES as STRONG evidence:
   - Floor tile patterns
   - Wood grain direction
   - Rugs/carpets
   - Upholstery fabrics
   - Wall patterns/texture

3. CONTINUOUS SPACE RULE:
   - Treat a continuous open-plan area (no solid walls/doors, same flooring and walls) as ONE physical space
   - Even if furniture or usage zones change (seating, dining, work corner)
   - Do NOT create separate clusters only because the furniture changes
   - Only split spaces when there is CLEAR physical separation (different room, different flooring, a wall or doorway, clearly different finishes)

4. CORNER/SUB-ZONE HANDLING:
   - If photo shows only a corner or sub-zone (sitting area, reading corner, desk)
   - But the shell and fixed elements clearly match another cluster
   - Treat it as part of that room's cluster instead of creating a micro-cluster

5. FOREGROUND PRIORITY:
   - For each photo, focus on the primary interior space in the FOREGROUND
   - Background views or distant exterior scenery should NOT change the room/space classification

6. AMBIGUITY RESOLUTION:
   - When a photo could belong to more than one cluster
   - Assign it to the cluster whose other photos have the CLOSEST visual match in the shell (flooring, walls, structure)

7. OVER-MERGE PREVENTION:
   - Only merge photos into the same cluster when the physical space is CLEARLY the same (continuous shell and no separating wall/door)
   - Do NOT merge separate bedrooms, bathrooms, or clearly distinct rooms even if they share similar decor

8. FLOORPLAN HANDLING:
   - If a floorplan image is present, USE IT to understand room layout, adjacencies, and orientations
   - It helps you identify: which rooms connect, which walls are exterior vs interior, approximate room sizes
   - The floorplan itself MUST stay in "excluded_content" as type "floorplan" (don't cluster it)
   - If the floorplan conflicts with the photos, FOLLOW THE PHOTOS (photos are ground truth)

═══════════════════════════════════════════════════════════════════════════════
NAMING AND EXCLUSIONS
═══════════════════════════════════════════════════════════════════════════════

CLUSTER NAMES: Use descriptive names in Spanish (e.g., "Salón", "Cocina", "Dormitorio Principal", "Baño", "Terraza")

Create SEPARATE clusters for different rooms even if similar (e.g., "Dormitorio 1" vs "Dormitorio 2")
- In open-plan spaces, furniture-based zones can be merged when they share a continuous shell
- Small sub-zones inside a room should NOT become their own cluster
- Only treat infrastructure-heavy service zones (cooking, bathing, laundry with fixed cabinets/appliances/sinks) as separate clusters when clearly visible

OUTDOOR SPACES: Separate clusters for "Terraza", "Jardín", "Balcón", etc.

EXCLUDED CONTENT (put in excluded_content array):
- type: "view" — Photos that MAINLY show external views (landscapes, sea, city, sky) with little or no interior content. NOT grouped with interior rooms or terraces.
- type: "floorplan" — Floorplan images (can be used as hints but must be excluded)
- type: "document" — Certificates, documents
- type: "ai_generated" — AI-generated or virtually staged images
- type: "render" — Architectural renders, 3D visualizations

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON)
═══════════════════════════════════════════════════════════════════════════════
{{
  "clusters": [
    {{
      "cluster_name": "Salón",
      "photo_indices": [0, 1, 2],
      "room_type": "living_room",
      "description": "Main living room with modern furniture",
      "confidence": 0.95,
      "is_real": true
    }}
  ],
  "excluded_content": [
    {{
      "type": "view",
      "photo_indices": [15],
      "reason": "External marina view without property content"
    }},
    {{
      "type": "ai_generated",
      "photo_indices": [8, 9],
      "reason": "Virtual staging - perfect furniture, no electrical outlets visible, unnatural lighting"
    }}
  ],
  "ai_image_summary": {{
    "total_ai_images": 2,
    "ai_image_types": ["virtual_staging"],
    "warning": "This listing contains 2 virtually staged images showing potential renovation outcomes. The actual property condition may differ significantly."
  }},
  "reasoning": "Brief explanation of clustering decisions"
}}

Return ONLY valid JSON, no markdown formatting."""


def _attach_photo_urls(
    clusters: List[Dict[str, Any]],
    photo_urls: List[str],
    *,
    total_count: int,
) -> List[Dict[str, Any]]:
    seen: set[int] = set()
    out: List[Dict[str, Any]] = []
    for cluster in clusters:
        indices = []
        for idx in cluster.get("photo_indices", []):
            if not isinstance(idx, int) or idx < 0 or idx >= total_count:
                continue
            if idx in seen:
                continue
            seen.add(idx)
            indices.append(idx)
        if not indices:
            continue
        cluster["photo_indices"] = indices
        cluster["photo_urls"] = [photo_urls[i] for i in indices]
        cluster["cluster_id"] = _normalize_cluster_id(cluster.get("cluster_name", "unknown"))
        out.append(cluster)

    missing = [idx for idx in range(total_count) if idx not in seen]
    if missing:
        out.append(
            {
                "cluster_name": "Sin asignar",
                "room_type": "unknown",
                "photo_indices": missing,
                "photo_urls": [photo_urls[i] for i in missing],
                "cluster_id": _normalize_cluster_id("sin_asignar"),
                "description": "Fotos sin cluster asignado",
                "confidence": 0.5,
                "is_real": True,
            }
        )
    return out


async def refine_clusters(
    *,
    photo_urls: List[str],
    listing_context: str,
    initial_clusters: List[Dict[str, Any]],
    excluded_content: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Refine initial clusters: reassign outliers, split/merge, rename.
    NEVER drop photos. Missing indices are reattached after refinement.
    """
    if not photo_urls:
        raise RuntimeError("refine_clusters: no photos provided")

    images = await fetch_images_batch(photo_urls)
    valid_indices = [idx for idx, img in enumerate(images) if img is not None]
    valid_images = [img for img in images if img is not None]
    if not valid_images:
        raise RuntimeError("refine_clusters: failed to fetch any images")

    orig_to_valid = {orig: i for i, orig in enumerate(valid_indices)}
    valid_clusters = []
    for cluster in initial_clusters:
        indices = []
        for idx in cluster.get("photo_indices", []):
            if idx in orig_to_valid:
                indices.append(orig_to_valid[idx])
        if indices:
            valid_clusters.append(
                {
                    "cluster_name": cluster.get("cluster_name", "unknown"),
                    "room_type": cluster.get("room_type", "unknown"),
                    "photo_indices": indices,
                    "description": cluster.get("description", ""),
                    "confidence": cluster.get("confidence", 0.8),
                    "is_real": cluster.get("is_real", True),
                }
            )

    prompt = f"""You are reviewing a first-pass clustering of property photos.
WHY THIS MATTERS for this task: The downstream BOQ depends on reliable room groupings.
If a single outlier image sits in the wrong cluster, the entire room narrative
and cost inference can be skewed. Your job is to fix those errors and improve
cluster naming without dropping any photos.

{listing_context}

You are given initial clusters and all images. Improve the clustering:
- If there is an "ugly duckling" in a cluster, move it to the right cluster.
- If a cluster contains multiple rooms, split it into separate clusters.
- If two clusters are really the same room, merge them.
- Rename clusters to clearer Spanish room names when needed.
- NEVER remove photos. Every photo must appear exactly once across clusters.

For each cluster, ask yourself: does every photo share the same physical shell
and fixed elements, or is one image clearly from a different room?

Return JSON with the refined clusters only.
"""

    prompt += "\nINITIAL CLUSTERS (indices refer to provided images):\n"
    for cluster in valid_clusters:
        prompt += f"- {cluster['cluster_name']} ({cluster.get('room_type', 'unknown')}): {cluster['photo_indices']}\n"

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=8000,
        images=valid_images,
        response_schema=CLUSTER_REFINEMENT_SCHEMA,
        use_spanish=True,
    )

    if not response.success or not response.text:
        raise RuntimeError(f"refine_clusters: Gemini call failed: {response.error}")

    try:
        refined = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"refine_clusters: JSON parse failed: {exc}") from exc

    clusters = refined.get("clusters", [])
    mapped_clusters: List[Dict[str, Any]] = []
    for cluster in clusters:
        mapped = []
        for idx in cluster.get("photo_indices", []):
            if not isinstance(idx, int) or idx < 0 or idx >= len(valid_indices):
                continue
            mapped.append(valid_indices[idx])
        if mapped:
            cluster["photo_indices"] = mapped
            mapped_clusters.append(cluster)

    # Preserve floorplans explicitly as a dedicated cluster so they don't get shoved into "Sin asignar"
    # and lost. This also enables downstream floorplan-first quantification when available.
    excluded_content = excluded_content or []
    floorplan_indices: List[int] = []
    for exc in excluded_content:
        if not isinstance(exc, dict):
            continue
        if str(exc.get("type") or "").strip().lower() != "floorplan":
            continue
        for idx in exc.get("photo_indices", []) or []:
            if isinstance(idx, int):
                floorplan_indices.append(idx)
    floorplan_indices = sorted(set([i for i in floorplan_indices if 0 <= i < len(photo_urls)]))
    if floorplan_indices:
        mapped_clusters.append(
            {
                "cluster_name": "Plano",
                "room_type": "floorplan",
                "photo_indices": floorplan_indices,
                "description": "Floorplan / plano (excluded from room clustering; used as quantification evidence when present)",
                "confidence": 1.0,
                "is_real": True,
            }
        )

    return _attach_photo_urls(mapped_clusters, photo_urls, total_count=len(photo_urls))


# =============================================================================
# CLUSTERING FUNCTIONS
# =============================================================================

async def cluster_photos(
    photo_urls: List[str],
    listing_context: str = "",
    property_flags: List[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for V0.4.8 pipeline.
    
    Zero-shot clustering of photos by room + AI image detection.
    Same logic as cluster_photos_direct but with standardized return format.
    
    Args:
        photo_urls: List of photo URLs to cluster
        listing_context: Context string about the property
        property_flags: Property flags like "squatted", "off_plan"
    
    Returns:
        {
            "clusters": [...],
            "excluded_content": [...],
            "ai_image_summary": {...},
            "ai_image_count": int,
            "reasoning": str
        }
    
    Raises:
        RuntimeError: If clustering fails (NO FALLBACKS - fail loud and fast)
    """
    if not photo_urls:
        raise RuntimeError("No photos provided for clustering")
    
    logger.info(f"📸 CLUSTERING | {len(photo_urls)} photos")
    
    # Fetch images as base64
    logger.info(f"  → Fetching images...")
    images = await fetch_images_batch(photo_urls)
    
    # Filter out failed fetches, track valid indices
    valid_images = []
    valid_indices = []
    for i, img in enumerate(images):
        if img:
            valid_images.append(img)
            valid_indices.append(i)
    
    if not valid_images:
        raise RuntimeError("Failed to fetch any images for clustering")
    
    logger.info(f"  → Successfully fetched {len(valid_images)}/{len(photo_urls)} images")
    
    # Build prompt
    prompt = get_p1_clustering_prompt(listing_context, len(valid_images), property_flags)
    
    # Call Gemini with images + THINKING LEVEL HIGH for extended reasoning
    # This matches the original zero-shot methodology that "worked like a dream"
    # V0.5: no_fallback=True - FAIL if Pro unavailable (don't use weaker models)
    logger.info(f"  → Calling Gemini Pro for clustering (thinkingLevel: HIGH, no_fallback: True)...")
    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.7,
        max_tokens=16000,
        images=valid_images,
        thinking_level="HIGH",  # CRITICAL: Extended reasoning for visual analysis
        no_fallback=True,  # V0.5: FAIL if Pro unavailable - clustering quality is critical
    )
    
    if not response.success or not response.text:
        raise RuntimeError(f"Clustering Gemini call failed: {response.error}")
    
    # Parse response
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        result = json.loads(text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse clustering response: {e}")
        logger.error(f"Response text (first 500 chars): {response.text[:500]}")
        raise RuntimeError(f"Failed to parse clustering result: {e}")
    
    clusters = result.get("clusters", [])
    excluded_content = result.get("excluded_content", [])
    ai_image_summary = result.get("ai_image_summary", {})
    
    # Map photo indices back to URLs (original indices)
    for cluster in clusters:
        indices = [valid_indices[i] for i in cluster.get("photo_indices", []) if i < len(valid_indices)]
        cluster["photo_indices"] = indices
        cluster["photo_urls"] = [photo_urls[i] for i in indices]
        # Create a clean cluster_id
        cluster["cluster_id"] = _normalize_cluster_id(cluster.get("cluster_name", "unknown"))

    # Map excluded_content indices back to original indices (critical for floorplan preservation).
    mapped_excluded: List[Dict[str, Any]] = []
    for exc in excluded_content or []:
        if not isinstance(exc, dict):
            continue
        mapped = dict(exc)
        mapped_indices: List[int] = []
        for i in exc.get("photo_indices", []) or []:
            if isinstance(i, int) and i < len(valid_indices):
                mapped_indices.append(valid_indices[i])
        mapped["photo_indices"] = mapped_indices
        mapped_excluded.append(mapped)
    excluded_content = mapped_excluded

    # Preserve floorplans as an explicit cluster so they are not reassigned into "Sin asignar".
    floorplan_indices: List[int] = []
    for exc in excluded_content:
        if str(exc.get("type") or "").strip().lower() != "floorplan":
            continue
        for idx in exc.get("photo_indices", []) or []:
            if isinstance(idx, int):
                floorplan_indices.append(idx)
    floorplan_indices = sorted(set([i for i in floorplan_indices if 0 <= i < len(photo_urls)]))
    if floorplan_indices:
        clusters.append(
            {
                "cluster_name": "Plano",
                "room_type": "floorplan",
                "photo_indices": floorplan_indices,
                "photo_urls": [photo_urls[i] for i in floorplan_indices],
                "description": "Floorplan / plano (excluded from room clustering; used as quantification evidence when present)",
                "confidence": 1.0,
                "is_real": True,
                "cluster_id": _normalize_cluster_id("plano"),
            }
        )
    
    # Count AI-generated images
    ai_image_count = sum(
        len(exc.get("photo_indices", []))
        for exc in excluded_content
        if exc.get("type") in ("ai_generated", "render")
    )
    
    logger.info(f"  ✓ Created {len(clusters)} clusters")
    logger.info(f"  ✓ Detected {ai_image_count} AI-generated images")
    
    return {
        "clusters": _attach_photo_urls(clusters, photo_urls, total_count=len(photo_urls)),
        "excluded_content": excluded_content,
        "ai_image_summary": ai_image_summary,
        "ai_image_count": ai_image_count,
        "reasoning": result.get("reasoning", "")
    }


# V0.5: cluster_photos_direct REMOVED - use cluster_photos() directly
# Legacy code should import from photo_analysis.py if needed


def _normalize_cluster_id(name: str) -> str:
    """Normalize cluster name to a clean ID."""
    if not name:
        return "unknown"
    
    # Lowercase and replace spaces
    cluster_id = name.lower().replace(" ", "_")
    
    # Remove Spanish accents
    for old, new in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        cluster_id = cluster_id.replace(old, new)
    
    return cluster_id


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_room_types_from_clusters(clusters: List[Dict[str, Any]]) -> List[str]:
    """Extract unique room types from clusters."""
    room_types = set()
    for cluster in clusters:
        room_type = cluster.get("room_type", "unknown")
        if room_type and room_type != "unknown":
            room_types.add(room_type)
    return list(room_types)


def get_cluster_photo_urls(clusters: List[Dict[str, Any]], cluster_name: str) -> List[str]:
    """Get photo URLs for a specific cluster by name."""
    for cluster in clusters:
        if cluster.get("cluster_name") == cluster_name or cluster.get("cluster_id") == cluster_name:
            return cluster.get("photo_urls", [])
    return []


def get_cluster_by_room_type(clusters: List[Dict[str, Any]], room_type: str) -> Optional[Dict[str, Any]]:
    """Get first cluster matching a room type."""
    for cluster in clusters:
        if cluster.get("room_type") == room_type:
            return cluster
    return None

