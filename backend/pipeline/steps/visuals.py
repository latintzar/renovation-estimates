"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗ ███████╗██████╗ ██████╗ ███████╗ ██████╗ █████╗ ████████╗███████╗  ║
║   ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝  ║
║   ██║  ██║█████╗  ██████╔╝██████╔╝█████╗  ██║     ███████║   ██║   █████╗    ║
║   ██║  ██║██╔══╝  ██╔═══╝ ██╔══██╗██╔══╝  ██║     ██╔══██║   ██║   ██╔══╝    ║
║   ██████╔╝███████╗██║     ██║  ██║███████╗╚██████╗██║  ██║   ██║   ███████╗  ║
║   ╚═════╝ ╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝  ║
║                                                                              ║
║   This module is DEPRECATED as of 2026-01-15                                 ║
║                                                                              ║
║   REPLACED BY: backend/pricing/multi_phase_estimator_v1.py                   ║
║                Phase 4 (Rendering Prompts) + Phase 5 (Image Generation)      ║
║                                                                              ║
║   WHY DEPRECATED:                                                            ║
║   - Old architecture: ONE before photo → THREE after images (tiered)         ║
║   - New architecture: MULTIPLE rooms → EACH room gets before/after pair      ║
║   - V1.0 pipeline integrates concept narrative + room-by-room rendering      ║
║                                                                              ║
║   DO NOT USE for new development. Code preserved for reference only.         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Visuals Steps (V1, V2, V3, V4) - LEGACY
=======================================

§3 Feasible Paths - Visuals phase (OLD PIPELINE)

Steps:
- V1: Defurnish (remove furniture from photos)
- V2: Select best before photo per tier
- V3: Generate rendering prompts
- V4: Render after images

Ported from:
- src/app/api/listings/[id]/photos/remove-furniture/route.ts
- src/app/api/listings/[id]/visuals/r1-select/route.ts
- src/app/api/listings/[id]/visuals/r2-prompt/route.ts
- src/app/api/listings/[id]/visuals/r3-render/route.ts
"""

import logging
import base64
import asyncio
import httpx
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


# =============================================================================
# V1: DEFURNISH (Remove Furniture from Single Before Photo)
# =============================================================================

async def run_v1_defurnish(orchestrator: "PipelineOrchestrator", listing_id: int) -> Dict[str, Any]:
    """
    V1: Remove furniture from the single before photo selected by V2.
    
    This prepares the photo for cleaner "after" renders by removing:
    - Furniture (sofas, tables, chairs, beds)
    - Decorations (art, plants, rugs)
    - Personal items (electronics, belongings)
    
    Reads: before_photo (from V2)
    Writes: defurnished_photo (updates before_photo record)
    """
    logger.info(f"🪑 V1: Removing furniture from before photo for listing {listing_id}")
    
    # Get the single before photo selected by V2
    before_photo = await orchestrator.db.get_before_photo(listing_id)
    
    if not before_photo:
        logger.warning("No before photo selected - V2 must run first")
        return {"summary": "No photo selected by V2", "processed": 0}
    
    photo_url = before_photo.get("photo_url")
    cluster_id = before_photo.get("cluster_id")
    room_name = before_photo.get("room_name", "Room")
    
    if not photo_url:
        logger.error("Before photo has no URL")
        return {"summary": "Before photo has no URL", "processed": 0}
    
    from ..gemini_client import call_gemini_image
    
    try:
        logger.info(f"  🖼️ Defurnishing {room_name} photo...")
        
        # Fetch photo as base64
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(photo_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch photo: {response.status_code}")
            
            photo_base64 = base64.b64encode(response.content).decode()
            content_type = response.headers.get("content-type", "image/jpeg")
        
        # Generate defurnished image
        prompt = """Remove all furniture, decorations, and personal items from this room.

KEEP (Structure - do not change):
- All walls, floors, ceilings
- Kitchen appliances (built-in)
- Bathroom fixtures
- Windows, doors
- Built-in closets/wardrobes
- Architectural features (moldings, columns)
- Light fixtures

REMOVE (Furniture & Items):
- All furniture (sofas, chairs, tables, beds, desks)
- Decorations (art, mirrors, plants, vases)
- Electronics (TVs, speakers, computers)
- Rugs and carpets
- Curtains/drapes
- Personal belongings
- Clutter

IMPORTANT:
- Continue the visible floor/wall pattern where items were removed
- Do NOT add anything new
- Do NOT change the room's structure
- Maintain exact camera angle and lighting
- Output a photorealistic result"""
        
        result = await call_gemini_image(
            prompt=prompt,
            image_data=photo_base64,
            image_mime_type=content_type,
        )
        
        if result.get("success") and result.get("image_data"):
            # Save defurnished data to the before_photo record
            await orchestrator.db.save_defurnished_photo(
                listing_id=listing_id,
                cluster_id=cluster_id,
                original_url=photo_url,
                defurnished_data=result["image_data"],
            )
            
            logger.info(f"  ✅ Photo defurnished successfully")
            
            return {
                "summary": "Photo defurnished successfully",
                "processed": 1,
                "room": room_name,
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"  ❌ Defurnishing failed: {error_msg}")
            return {
                "summary": f"Defurnishing failed: {error_msg}",
                "processed": 0,
                "error": error_msg,
            }
    
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return {
            "summary": f"Error: {str(e)}",
            "processed": 0,
            "error": str(e),
        }


# =============================================================================
# V2: SELECT SINGLE BEFORE PHOTO (One photo for ALL brackets)
# =============================================================================

# Response schema for V2 - single photo selection
V2_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
                    "selected_cluster_id": {
                        "type": "string",
                        "description": "The cluster_id of the selected photo"
                    },
        "room_name": {
                        "type": "string",
                        "description": "The room name"
                    },
                    "reason": {
                        "type": "string",
            "description": "Why this room is best for showing renovation potential"
                },
        "visible_elements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "What renovation elements are visible (flooring, cabinets, walls, etc.)"
        }
    },
    "required": ["selected_cluster_id", "room_name", "reason", "visible_elements"]
}


def _format_room_photos(photos: List[Dict]) -> str:
    """Format room photos for selection."""
    lines = []
    for p in photos:
        lines.append(f"- {p['cluster_id']}: {p['room_name']} ({p.get('photo_count', 1)} photos)")
    return "\n".join(lines) if lines else "No photos available"


async def run_v2_select_before(orchestrator: "PipelineOrchestrator", listing_id: int) -> Dict[str, Any]:
    """
    V2: Select ONE best before photo for ALL renovation brackets.
    
    The SAME photo is used as "before" for essential, standard, and premium renders.
    This ensures consistent comparison across brackets.
    
    Criteria:
    1. Maximum visible renovatable elements (floors, walls, cabinets, etc.)
    2. Good lighting and camera angle
    3. Room type that shows dramatic transformation (kitchen > bathroom > living)
    
    Reads: photo_clusters
    Writes: listing_before_photo
    """
    logger.info(f"📸 V2: Selecting single before photo for listing {listing_id}")
    
    # Get photo clusters
    clusters = await orchestrator.db.get_photo_clusters(listing_id)
    
    if not clusters:
        raise ValueError("No photo clusters found")
    
    # Build room photos list
    room_photos = []
    cluster_url_map = {}  # cluster_id -> first photo URL
    for c in clusters:
        urls = c.get("photo_urls", [])
        if urls:
            cluster_id = c.get("cluster_id")
            room_photos.append({
                "cluster_id": cluster_id,
                "room_name": c.get("room_name", "Unknown"),
                "photo_count": len(urls),
            })
            cluster_url_map[cluster_id] = urls[0]
    
    if not room_photos:
        return {"summary": "No photos available", "selection": None}
    
    # Build prompt for single photo selection
    prompt = f"""Select the SINGLE BEST photo to use for ALL renovation visualizations.

This ONE photo will be the "before" image for:
- Essential renovation (basic compliance)
- Standard renovation (full modernization)
- Premium renovation (high-end finishes)

CRITERIA (in order of priority):

1. VISIBLE ELEMENTS - More renovatable surfaces = better
   Best: Kitchen (cabinets + counters + floors + walls + appliances)
   Good: Bathroom (tiles + fixtures + vanity)
   OK: Living room (floors + walls)
   
2. LIGHTING - Well-lit photos show transformations clearly

3. CAMERA ANGLE - Wide angles show more of the room

4. ROOM CONDITION - Rooms needing renovation show most dramatic change

AVAILABLE PHOTOS:
{_format_room_photos(room_photos)}

Select ONE photo that will work best for showing renovation potential across all brackets.
List ALL visible renovatable elements in that photo."""

    from ..gemini_client import call_gemini_json
    
    logger.info(f"  📷 Selecting single best photo from {len(room_photos)} options...")
    
    result = await call_gemini_json(
        prompt=prompt,
        model="flash",
        temperature=0.3,
        response_schema=V2_RESPONSE_SCHEMA,
    )
    
    if not result or "selected_cluster_id" not in result:
        raise ValueError(f"V2 Gemini call failed or invalid response: {result}")
    
    cluster_id = result.get("selected_cluster_id")
    room_name = result.get("room_name", "")
    reason = result.get("reason", "")
    visible_elements = result.get("visible_elements", [])
    
    photo_url = cluster_url_map.get(cluster_id)
    if not photo_url:
        # Fallback to first available
        cluster_id = list(cluster_url_map.keys())[0]
        photo_url = cluster_url_map[cluster_id]
        logger.warning(f"  ⚠️ Selected cluster not found, using fallback: {cluster_id}")
    
    # Save single before photo
    await orchestrator.db.save_before_photo(
        listing_id=listing_id,
        cluster_id=cluster_id,
        photo_url=photo_url,
        room_name=room_name,
        selection_reason=reason,
        visible_elements=visible_elements,
    )
    
    logger.info(f"  ✅ Selected: {room_name} ({cluster_id})")
    logger.info(f"  📋 Visible elements: {', '.join(visible_elements)}")
    
    return {
        "summary": f"Selected before photo: {room_name}",
        "selection": {
            "cluster_id": cluster_id,
            "room_name": room_name,
            "visible_elements": visible_elements,
        },
    }


# =============================================================================
# V3: GENERATE RENDERING PROMPTS (For all 3 brackets)
# =============================================================================

# Strict constraints that apply to ALL renders - NO structural changes
STRICT_RENDER_CONSTRAINTS = """
CRITICAL CONSTRAINTS - THE STRUCTURE MUST NOT CHANGE:

✅ YOU CAN CHANGE (Visual Finishes Only):
- Wall paint colors and wallpaper
- Floor materials, colors, patterns
- Ceiling paint and light fixtures
- Cabinet styles and colors (SAME positions)
- Countertop materials
- Tile patterns and colors
- Appliance appearances (SAME positions)
- Fixture styles (taps, handles, outlets)
- Window frame color (SAME size/position)
- Door style and color (SAME position)

❌ YOU CANNOT CHANGE (Structure is LOCKED):
- Wall positions (no knocking down walls)
- Door positions or count (no new doors, no removing doors)
- Window positions or sizes (no new windows)
- Room shape or dimensions
- Ceiling height
- Kitchen layout / plumbing locations
- Bathroom layout / plumbing locations
- Add any new structural elements
- Add furniture

The camera angle, perspective, and room geometry
MUST be IDENTICAL to the input image.

OUTPUT: Photorealistic image showing ONLY finish changes."""


# Bracket-specific styling
BRACKET_STYLES = {
    "essential": {
        "name": "Basic Compliance",
        "description": "Minimal changes for safety and habitability",
        "materials": ["standard paint", "basic tiles", "functional fixtures"],
        "colors": ["white", "light gray", "neutral"],
        "quality": "basic/functional",
    },
    "standard": {
        "name": "Modern Standard",
        "description": "Full modernization to 'very good' condition",
        "materials": ["porcelain tiles", "quality laminate", "modern cabinets", "quartz counters"],
        "colors": ["white", "warm gray", "light wood tones"],
        "quality": "mid-range/modern",
    },
    "premium": {
        "name": "Premium Finish",
        "description": "High-end materials and designer aesthetic",
        "materials": ["large format porcelain", "hardwood", "custom cabinets", "marble/dekton"],
        "colors": ["designer palette", "accent colors", "premium finishes"],
        "quality": "high-end/luxury",
    },
}


async def run_v3_prompts(orchestrator: "PipelineOrchestrator", listing_id: int) -> Dict[str, Any]:
    """
    V3: Generate rendering prompts for all 3 brackets.
    
    Creates ONE prompt per bracket (essential, standard, premium).
    All prompts reference the SAME before photo.
    
    Reads: before_photo, detected_conditions
    Writes: render_prompts (3 rows)
    """
    logger.info(f"📝 V3: Generating render prompts for listing {listing_id}")
    
    # Get the single before photo
    before_photo = await orchestrator.db.get_before_photo(listing_id)
    if not before_photo:
        raise ValueError("No before photo found - run V2 first")
    
    room_name = before_photo.get("room_name", "Main Room")
    visible_elements = before_photo.get("visible_elements", [])
    
    # Get detected conditions (what needs fixing)
    conditions = await orchestrator.db.get_detected_conditions(listing_id)
    
    results = []
    
    for bracket in ["essential", "standard", "premium"]:
        logger.info(f"  📝 Generating prompt for {bracket} bracket...")
        
        style = BRACKET_STYLES[bracket]
        
        # Build bracket-specific prompt
        prompt = _build_bracket_render_prompt(
            bracket=bracket,
            room_name=room_name,
            visible_elements=visible_elements,
            style=style,
            conditions=conditions,
        )
        
        # Save render prompt
        await orchestrator.db.save_render_prompt(
            listing_id=listing_id,
            tier=bracket,  # Using "tier" column for bracket
            render_prompt=prompt,
            style_keywords=style["materials"],
            model_used="built-in",
        )
        
        results.append({
            "bracket": bracket,
            "prompt_length": len(prompt),
        })
        
        logger.info(f"  ✅ {bracket}: Prompt generated ({len(prompt)} chars)")
    
    logger.info(f"✅ V3: Generated prompts for {len(results)} brackets")
    
    return {
        "summary": f"Generated render prompts for {len(results)} brackets",
        "prompts": results,
    }


def _build_bracket_render_prompt(
    bracket: str,
    room_name: str,
    visible_elements: List[str],
    style: Dict,
    conditions: List[Dict],
) -> str:
    """Build the full render prompt for a bracket."""
    
    # What to change based on visible elements
    changes = []
    
    if "walls" in visible_elements or "wall" in visible_elements:
        if bracket == "essential":
            changes.append("- Repaint walls in clean white")
        elif bracket == "standard":
            changes.append("- Repaint walls in warm white/light gray")
        else:
            changes.append("- Designer paint finish, consider accent wall")
    
    if "flooring" in visible_elements or "floor" in visible_elements:
        if bracket == "essential":
            changes.append("- Clean existing flooring or basic laminate")
        elif bracket == "standard":
            changes.append("- Quality wood-look laminate or porcelain tile")
        else:
            changes.append("- Large format porcelain or real hardwood")
    
    if "cabinets" in visible_elements or "kitchen" in room_name.lower():
        if bracket == "essential":
            changes.append("- Repaint cabinet fronts, new handles")
        elif bracket == "standard":
            changes.append("- Modern white/gray cabinets with soft-close")
        else:
            changes.append("- Custom handleless cabinets, integrated appliances")
    
    if "counters" in visible_elements or "countertop" in visible_elements:
        if bracket == "essential":
            changes.append("- Basic laminate countertop")
        elif bracket == "standard":
            changes.append("- Quartz or engineered stone countertop")
        else:
            changes.append("- Marble, Dekton, or premium stone countertop")
    
    if "fixtures" in visible_elements or "bathroom" in room_name.lower():
        if bracket == "essential":
            changes.append("- Functional chrome fixtures")
        elif bracket == "standard":
            changes.append("- Modern chrome fixtures, rain shower")
        else:
            changes.append("- Designer brushed gold/black fixtures")
    
    if "tiles" in visible_elements or "tile" in visible_elements:
        if bracket == "essential":
            changes.append("- Basic white tiles where needed")
        elif bracket == "standard":
            changes.append("- Modern subway or large format tiles")
        else:
            changes.append("- Designer patterned or textured tiles")
    
    if "lighting" in visible_elements or "lights" in visible_elements:
        if bracket == "essential":
            changes.append("- Basic ceiling light fixture")
        elif bracket == "standard":
            changes.append("- Recessed LED lighting")
        else:
            changes.append("- Statement pendant lights, integrated LED strips")
    
    # Add any visible elements not covered
    for elem in visible_elements:
        elem_lower = elem.lower()
        if not any(elem_lower in c.lower() for c in changes):
            if bracket == "essential":
                changes.append(f"- Clean/repair {elem}")
            elif bracket == "standard":
                changes.append(f"- Modernize {elem}")
            else:
                changes.append(f"- Premium upgrade to {elem}")
    
    changes_text = "\n".join(changes) if changes else "- General modernization of visible finishes"
    
    return f"""Transform this {room_name} photo to show {style['name']} renovation.

BRACKET: {bracket.upper()}
STYLE: {style['description']}

CHANGES TO APPLY:
{changes_text}

MATERIALS & COLORS:
- Quality level: {style['quality']}
- Materials: {', '.join(style['materials'])}
- Color palette: {', '.join(style['colors'])}

{STRICT_RENDER_CONSTRAINTS}

Create a photorealistic result showing ONLY the finish changes listed above.
The room's structure (walls, doors, windows) must remain EXACTLY as in the original."""


# =============================================================================
# V4: RENDER AFTER IMAGES (3 brackets from 1 before photo)
# =============================================================================

async def run_v4_render(orchestrator: "PipelineOrchestrator", listing_id: int) -> Dict[str, Any]:
    """
    V4: Generate after-images for all 3 brackets.
    
    Uses the SINGLE before photo with 3 different prompts (essential, standard, premium).
    Applies STRICT constraints - NO structural changes allowed.
    
    Reads: before_photo (single), render_prompts (3), defurnished_photo (optional)
    Writes: after_photos (3)
    """
    logger.info(f"🎨 V4: Rendering after-images for listing {listing_id}")
    
    # Get single before photo
    before_photo = await orchestrator.db.get_before_photo(listing_id)
    if not before_photo:
        raise ValueError("No before photo found - run V2 first")
    
    # Get render prompts (one per bracket)
    render_prompts = await orchestrator.db.get_render_prompts(listing_id)
    if not render_prompts:
        raise ValueError("No render prompts found - run V3 first")
    
    # Check for defurnished version
    defurnished = await orchestrator.db.get_defurnished_photo(listing_id)
    
    # Build prompt map
    prompt_map = {p.get("tier"): p.get("prompt", "") for p in render_prompts}
    
    # Get before image data
    photo_url = before_photo.get("photo_url")
    
    if defurnished and defurnished.get("defurnished_data"):
        # Use defurnished version
        photo_base64 = defurnished["defurnished_data"]
        content_type = "image/jpeg"
        logger.info("  📷 Using defurnished photo as base")
    else:
        # Fetch original
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(photo_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch photo: {response.status_code}")
            photo_base64 = base64.b64encode(response.content).decode()
            content_type = response.headers.get("content-type", "image/jpeg")
        logger.info("  📷 Using original photo as base")
    
    # Render each bracket
    results = []
    errors = []
    
    from ..gemini_client import call_gemini_image
    
    for bracket in ["essential", "standard", "premium"]:
        render_prompt = prompt_map.get(bracket, "")
        
        if not render_prompt:
            logger.warning(f"  ⚠️ No render prompt for {bracket} bracket")
            continue
        
        try:
            logger.info(f"  🖼️ Rendering {bracket} bracket...")
            
            # Full prompt with strict constraints
            full_prompt = f"""{render_prompt}

FINAL REMINDER - STRUCTURE IS LOCKED:
- Same walls, same doors, same windows
- Same room shape, same camera angle
- ONLY change surface finishes
- Photorealistic output"""
            
            result = await call_gemini_image(
                prompt=full_prompt,
                image_data=photo_base64,
                image_mime_type=content_type,
            )
            
            if result.get("success") and result.get("image_data"):
                # Save to database
                after_data_url = f"data:image/jpeg;base64,{result['image_data']}"
                
                await orchestrator.db.save_after_photo(
                    listing_id=listing_id,
                    tier=bracket,  # Using "tier" column for bracket
                    cluster_id=before_photo.get("cluster_id"),
                    before_url=photo_url,
                    after_url=after_data_url,
                )
                
                results.append({
                    "bracket": bracket,
                    "status": "success",
                })
                
                logger.info(f"  ✅ {bracket} bracket rendered")
            else:
                errors.append({
                    "bracket": bracket,
                    "error": result.get("error", "Unknown error"),
                })
                logger.error(f"  ❌ {bracket}: {result.get('error')}")
        
        except Exception as e:
            errors.append({
                "bracket": bracket,
                "error": str(e),
            })
            logger.error(f"  ❌ {bracket}: {e}")
    
    logger.info(f"✅ V4: Rendered {len(results)} after-images, {len(errors)} errors")
    
    return {
        "summary": f"Rendered {len(results)} after-images",
        "rendered": len(results),
        "errors": len(errors),
        "results": results,
    }

