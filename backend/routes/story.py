"""
Listing Stories API
====================

Server-side tour generation using Gemini analysis of Street View tiles.

Endpoints:
- GET /api/listings/{id}/story - Get saved story
- POST /api/listings/{id}/story/generate - Generate tours server-side
- GET /api/listings/{id}/story/exists - Check if story exists
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class ListingStory(BaseModel):
    """Complete story for a listing."""
    listing_id: int
    total_duration_ms: int
    property_program: Dict[str, Any]
    nearby_programs: List[Dict[str, Any]]
    curated_places_snapshot: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StoryResponse(BaseModel):
    """Response containing story data."""
    success: bool
    story: Optional[ListingStory] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/listings/{listing_id}/story", response_model=StoryResponse)
async def get_story(listing_id: int):
    """Get saved story for a listing."""
    logger.info(f"[Story] 📖 Getting story for listing {listing_id}")
    
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        response = await client.get(
            f"{base_url}/listing_stories",
            params={"listing_id": f"eq.{listing_id}", "select": "*"}
        )
        
        if response.status_code != 200:
            logger.error(f"[Story] DB error: {response.status_code} {response.text}")
            raise HTTPException(status_code=500, detail="Database error")
        
        stories = response.json()
        
        if not stories:
            return StoryResponse(
                success=False,
                message="No story generated yet. Click 'Generate Story' to create one."
            )
        
        story_data = stories[0]
        
        story = ListingStory(
            listing_id=story_data["listing_id"],
            total_duration_ms=story_data["total_duration_ms"],
            property_program=story_data["property_program"],
            nearby_programs=story_data.get("nearby_programs") or [],
            curated_places_snapshot=story_data.get("curated_places_snapshot"),
            created_at=story_data.get("created_at"),
            updated_at=story_data.get("updated_at")
        )
        
        logger.info(f"[Story] ✅ Found story: {story.total_duration_ms}ms, {len(story.nearby_programs)} nearby tours")
        return StoryResponse(success=True, story=story)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Story] ❌ Error getting story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listings/{listing_id}/story/generate", response_model=StoryResponse)
async def generate_story(listing_id: int):
    """
    Generate tours for a listing using Gemini analysis of Street View tiles.
    
    Process:
    1. Get listing coordinates
    2. Get curated places (must run 'Curate Places' first)
    3. For each location (property + curated places):
       - Fetch Street View tiles (32 tiles at zoom 3)
       - Stitch into panorama with grid overlay
       - Send to Gemini for analysis (tile-based prompting)
       - Execute sequence into keyframes with baked-in cinematics
    4. Save complete story to database
    """
    logger.info(f"[Story] 🎬 Generating story for listing {listing_id}")
    errors: List[str] = []
    
    # Import clients/services
    try:
        from clients.streetview_client import StreetViewClient
        from services.tour_generator import generate_tour_for_location
        from services.tour_executor import execute_tour_sequence
    except ImportError as e:
        logger.error(f"[Story] ❌ Import error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Required module not available: {e}. Check API key configuration."
        )
    
    try:
        # Get listing
        listing = await database.get_listing(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
        
        lat = listing.get("lat")
        lng = listing.get("lng")
        
        if not lat or not lng:
            raise HTTPException(status_code=400, detail="Listing has no coordinates")
        
        lat, lng = float(lat), float(lng)
        property_name = listing.get("title") or listing.get("address") or f"Listing {listing_id}"
        
        logger.info(f"[Story] Property: {property_name} at ({lat}, {lng})")
        
        # Get curated places
        client = await database.get_client()
        base_url = database._get_base_url()
        
        places_response = await client.get(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}", "select": "*", "order": "slot.asc"}
        )
        
        if places_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get curated places from database")
        
        curated_places = places_response.json()
        
        if not curated_places:
            raise HTTPException(
                status_code=400, 
                detail="No curated places found. Run 'Curate Places' first."
            )
        
        logger.info(f"[Story] Found {len(curated_places)} curated places")
        
        # Initialize Street View client
        sv_client = StreetViewClient()
        
        # Generate property tour
        logger.info(f"[Story] 🏠 Generating property tour...")
        property_program = await _generate_tour(
            sv_client=sv_client,
            lat=lat,
            lng=lng,
            location_type="property",
            location_name=property_name,
            property_heading=0,
            errors=errors,
            generate_fn=generate_tour_for_location,
            execute_fn=execute_tour_sequence,
        )
        
        if not property_program:
            errors.append("Failed to generate property tour - no Street View coverage")
        
        # Generate nearby tours
        nearby_programs = []
        
        for place in curated_places:
            place_lat = place.get("lat")
            place_lng = place.get("lng")
            place_name = place.get("name", "Unknown")
            place_type = place.get("category", "place")
            
            if not place_lat or not place_lng:
                errors.append(f"Skipped {place_name}: no coordinates")
                continue
            
            place_lat, place_lng = float(place_lat), float(place_lng)
            
            # Calculate heading from place to property
            property_heading = _calculate_heading(place_lat, place_lng, lat, lng)
            
            logger.info(f"[Story] 📍 Generating tour for {place_name} ({place_type}), heading={property_heading:.1f}°")
            
            program = await _generate_tour(
                sv_client=sv_client,
                lat=place_lat,
                lng=place_lng,
                location_type=place_type,
                location_name=place_name,
                property_heading=property_heading,
                errors=errors,
                generate_fn=generate_tour_for_location,
                execute_fn=execute_tour_sequence,
            )
            
            if program:
                nearby_programs.append({
                    "place_id": place.get("id"),
                    "slot": place.get("slot"),
                    "lat": place_lat,
                    "lng": place_lng,
                    "name": place_name,
                    "place_type": place_type,
                    "rating": place.get("rating"),
                    "rating_count": place.get("rating_count"),
                    "program": program,
                })
                logger.info(f"[Story] ✅ {place_name}: {program.get('duration_ms', 0)}ms")
            else:
                logger.warning(f"[Story] ⚠️ {place_name}: No tour generated")
        
        # Calculate total duration
        property_duration = property_program.get("duration_ms", 0) if property_program else 0
        nearby_duration = sum(np.get("program", {}).get("duration_ms", 0) for np in nearby_programs)
        total_duration = property_duration + nearby_duration
        
        logger.info(f"[Story] Total: {total_duration}ms = {property_duration}ms (property) + {nearby_duration}ms ({len(nearby_programs)} places)")
        
        # Don't save empty stories - fail loudly
        if total_duration == 0 or (not property_program and not nearby_programs):
            logger.error(f"[Story] ❌ No tours generated - not saving empty story")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate any tours. Errors: {', '.join(errors[:3])}"
            )
        
        # Save to database
        now = datetime.utcnow().isoformat()
        story_data = {
            "listing_id": listing_id,
            "total_duration_ms": total_duration,
            "property_program": property_program or {},
            "nearby_programs": nearby_programs,
            "curated_places_snapshot": curated_places,
            "updated_at": now,
        }
        
        # Upsert (update if exists, insert if not)
        existing_response = await client.get(
            f"{base_url}/listing_stories",
            params={"listing_id": f"eq.{listing_id}", "select": "id"}
        )
        existing = existing_response.json() if existing_response.status_code == 200 else []
        
        if existing:
            logger.info(f"[Story] Updating existing story")
            response = await client.patch(
                f"{base_url}/listing_stories",
                params={"listing_id": f"eq.{listing_id}"},
                json=story_data
            )
        else:
            logger.info(f"[Story] Creating new story")
            story_data["created_at"] = now
            response = await client.post(
                f"{base_url}/listing_stories",
                json=story_data
            )
        
        if response.status_code not in (200, 201):
            logger.error(f"[Story] ❌ Save failed: {response.status_code} {response.text}")
            raise HTTPException(status_code=500, detail=f"Failed to save story: {response.text}")
        
        saved_data = response.json()
        if isinstance(saved_data, list):
            saved_data = saved_data[0]
        
        story = ListingStory(
            listing_id=saved_data["listing_id"],
            total_duration_ms=saved_data["total_duration_ms"],
            property_program=saved_data["property_program"],
            nearby_programs=saved_data.get("nearby_programs") or [],
            curated_places_snapshot=saved_data.get("curated_places_snapshot"),
            created_at=saved_data.get("created_at"),
            updated_at=saved_data.get("updated_at")
        )
        
        logger.info(f"[Story] ✅ Story saved: {total_duration}ms total, {len(nearby_programs) + 1} tours")
        
        return StoryResponse(
            success=True,
            story=story,
            message=f"Generated {len(nearby_programs) + 1} tours ({total_duration}ms total)",
            errors=errors if errors else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Story] ❌ Error generating story: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}/story/exists")
async def story_exists(listing_id: int):
    """Check if a story exists for a listing."""
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        response = await client.get(
            f"{base_url}/listing_stories",
            params={
                "listing_id": f"eq.{listing_id}",
                "select": "id,created_at,total_duration_ms"
            }
        )
        
        if response.status_code != 200:
            return {"exists": False, "error": "Database error"}
        
        stories = response.json()
        
        if stories:
            return {
                "exists": True,
                "created_at": stories[0].get("created_at"),
                "total_duration_ms": stories[0].get("total_duration_ms")
            }
        else:
            return {"exists": False}
            
    except Exception as e:
        logger.error(f"[Story] Error checking existence: {e}")
        return {"exists": False, "error": str(e)}


# =============================================================================
# INTERNAL FUNCTIONS
# =============================================================================

async def _generate_tour(
    sv_client,
    lat: float,
    lng: float,
    location_type: str,
    location_name: str,
    property_heading: float,
    errors: List[str],
    generate_fn,
    execute_fn,
) -> Optional[Dict[str, Any]]:
    """Generate a tour for a single location using Gemini."""
    try:
        # Fetch panorama with grid overlay for Gemini
        panorama_data = await sv_client.fetch_panorama_for_gemini(
            lat, lng,
            poi_heading=property_heading,
        )
        
        if not panorama_data:
            errors.append(f"No Street View coverage at {location_name}")
            return None
        
        pano_id = panorama_data["pano_id"]
        image = panorama_data["image"]
        
        # Generate tour sequence with Gemini (tile-based prompting)
        sequence = await generate_fn(
            panorama_image=image,
            location_type=location_type,
            location_name=location_name,
            property_heading=property_heading,
            pano_id=pano_id,
        )
        
        # Execute sequence into keyframes with baked-in cinematics
        program = execute_fn(
            sequence=sequence,
            starting_heading=property_heading,
        )
        
        return program
        
    except Exception as e:
        errors.append(f"Tour generation failed for {location_name}: {str(e)}")
        logger.error(f"[Story] Tour failed for {location_name}: {e}", exc_info=True)
        return None


def _calculate_heading(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> float:
    """Calculate bearing from one point to another (0-360 degrees)."""
    import math
    
    lat1 = math.radians(from_lat)
    lat2 = math.radians(to_lat)
    delta_lng = math.radians(to_lng - from_lng)
    
    x = math.sin(delta_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lng)
    
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360
