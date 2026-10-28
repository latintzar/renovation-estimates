"""
Place Curation V3 - Google-Powered Curation System
==================================================

As of 2024-12-31, uses Google Places API (New) for all POI discovery.
Replaces Foursquare entirely for better data quality.

Features:
- Direct lat/lng from Google (no geocoding needed)
- Opening hours included
- Ratings and review counts
- "Open Late" detection for nightlife venues

Cost: ~$0.26/listing (first 625/month FREE)
See: docs/GOOGLE_PLACES_API_DECISION.md

Also uses:
- Transitland (Public transit: metro, bus, train)
- Overture (Parks, nature - FREE)
- Street View tile caching
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

import database
from services.curation_service import CurationService, CuratedPlaceV2
from clients.streetview_client import StreetViewClient, fetch_and_cache_panorama

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CuratedPlaceV2:
    """A curated place with all metadata."""
    slot: int
    name: str
    category: str  # e.g., "Supermarket", "metro", "bus"
    lat: float
    lng: float
    distance_m: float
    walking_min: float
    rating: Optional[float] = None
    source: str = "foursquare"  # foursquare, transitland, google
    fsq_id: Optional[str] = None
    address: Optional[str] = None
    
    # Google Places verification
    original_lat: Optional[float] = None
    original_lng: Optional[float] = None
    google_place_id: Optional[str] = None
    distance_correction_m: Optional[float] = None
    
    # Street View data
    tile_urls: Optional[Dict[str, Any]] = None
    sv_heading: Optional[float] = None
    tour_program: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for database storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class CuratedPlaceResponse(BaseModel):
    """API response model for a curated place (V3 - Google-powered)."""
    slot: int
    name: str
    category: str
    lat: float
    lng: float
    distance_m: float
    walk_mins: Optional[int] = None  # Walking time in minutes (proper calculation)
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    source: str = "google"
    google_place_id: Optional[str] = None
    # V3: Opening hours
    is_open_now: Optional[bool] = None
    is_open_late: Optional[bool] = None
    weekday_hours: Optional[List[str]] = None
    # Transit routes with per-line station info (for metro/bus slots)
    transit_routes: Optional[List[Dict[str, Any]]] = None
    transit_stop_id: Optional[str] = None
    # Legacy fields (for backward compatibility)
    fsq_id: Optional[str] = None
    address: Optional[str] = None
    original_lat: Optional[float] = None
    original_lng: Optional[float] = None
    distance_correction_m: Optional[float] = None
    tile_urls: Optional[Dict[str, Any]] = None
    sv_heading: Optional[float] = None
    tour_program: Optional[Dict[str, Any]] = None


class CurationResponse(BaseModel):
    """Response for place curation endpoint."""
    success: bool
    listing_id: int
    places: List[CuratedPlaceResponse]
    empty_slots: Dict[str, Any] = {}
    tiles_cached: int = 0
    tiles_failed: int = 0
    transit_isochrone: Optional[Dict[str, Any]] = None  # GeoJSON: 30-min transit reach
    walk_isochrone: Optional[Dict[str, Any]] = None     # GeoJSON: 15-min walk reach
    walk_2min_isochrone: Optional[Dict[str, Any]] = None  # GeoJSON: 2-min walk reach
    error: Optional[str] = None


class TourGenerationResponse(BaseModel):
    """Response for tour generation."""
    success: bool
    generated: int = 0
    failed: int = 0
    tours: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


# =============================================================================
# SLOT DEFINITIONS
# =============================================================================

SLOT_DEFINITIONS = {
    # Slot 1 = Property (handled separately)
    2: {"category": "Supermarket", "priority": 1, "source": "foursquare"},
    3: {"category": "metro", "priority": 1, "source": "transitland"},
    4: {"category": "bus", "priority": 2, "source": "transitland"},
    5: {"category": "Restaurant", "priority": 3, "source": "foursquare"},
    6: {"category": "Gym", "priority": 3, "source": "foursquare"},
    7: {"category": "School", "priority": 2, "source": "foursquare"},
    8: {"category": "Medical Center", "priority": 2, "source": "foursquare"},
    9: {"category": "Park", "priority": 3, "source": "foursquare"},
    10: {"category": "Cultural", "priority": 3, "source": "foursquare"},
}

# Category mapping for Foursquare query search
# Using text queries instead of category IDs for NEW API compatibility
FOURSQUARE_QUERY_MAP = {
    "Supermarket": "supermarket",
    "Restaurant": "restaurant",
    "Gym": "gym fitness",
    "School": "school",
    "Medical Center": "hospital medical center",
    "Park": "park",
    "Cultural": "museum gallery",
}


# =============================================================================
# CURATION LOGIC
# =============================================================================

async def _verify_coordinates_with_google(
    name: str, 
    lat: float, 
    lng: float,
    category: str,
    address: str = None,
    bias_lat: float = None,
    bias_lng: float = None,
) -> Dict[str, Any]:
    """
    Verify/geocode POI coordinates using Google Places API.
    
    If lat/lng are invalid (0 or None), geocodes from address.
    Otherwise verifies and potentially corrects coordinates.
    
    Args:
        name: Place name
        lat, lng: Foursquare coordinates (may be 0 if not provided)
        category: Place category
        address: Full address string for geocoding fallback
        bias_lat, bias_lng: Search center to bias results
    
    Returns:
        Dict with {lat, lng, google_place_id, ...}
    """
    try:
        google_client = GooglePlacesClient()
        
        # Check if we have valid coordinates from Foursquare
        has_valid_coords = lat and lng and lat != 0 and lng != 0
        
        if has_valid_coords:
            # Verify existing coordinates
            result = await google_client.verify_poi_coordinates(name, lat, lng)
        elif address:
            # No coords - geocode from address
            logger.info(f"[Curation] 📍 {name}: No coords from Foursquare, geocoding from address")
            result = await google_client.geocode_address(
                address=address,
                name=name,
                bias_lat=bias_lat,
                bias_lng=bias_lng
            )
        else:
            # No coords and no address - can't proceed
            logger.warning(f"[Curation] ⚠️ {name}: No coords or address available")
            return {"lat": lat, "lng": lng}
        
        if result and result.get("found"):
            import math
            
            new_lat = result.get("lat") or result.get("latitude")
            new_lng = result.get("lng") or result.get("longitude")
            
            if not new_lat or not new_lng:
                logger.warning(f"[Curation] ⚠️ {name}: Google returned no coords")
                return {"lat": lat, "lng": lng}
            
            # Calculate correction distance if we had original coords
            correction_m = 0
            if has_valid_coords:
                R = 6371000  # Earth radius in meters
                lat1, lat2 = math.radians(lat), math.radians(new_lat)
                dlat = lat2 - lat1
                dlng = math.radians(new_lng - lng)
                
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
                correction_m = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                logger.info(f"[Curation] ✅ {name}: Google corrected by {correction_m:.0f}m")
            else:
                logger.info(f"[Curation] ✅ {name}: Geocoded to ({new_lat:.6f}, {new_lng:.6f})")
            
            return {
                "lat": new_lat,
                "lng": new_lng,
                "original_lat": lat if has_valid_coords else None,
                "original_lng": lng if has_valid_coords else None,
                "google_place_id": result.get("place_id"),
                "distance_correction_m": round(correction_m, 1) if has_valid_coords else None
            }
        else:
            logger.info(f"[Curation] ⚠️ {name}: Google couldn't verify/geocode, using original")
            return {"lat": lat, "lng": lng}
            
    except Exception as e:
        logger.warning(f"[Curation] Google verification failed for {name}: {e}")
        return {"lat": lat, "lng": lng}


async def _fetch_foursquare_places(
    lat: float, 
    lng: float, 
    categories: List[str],
    radius: int = 1500
) -> Dict[str, List[Dict]]:
    """Fetch places from Foursquare by category using query search."""
    results = {}
    client = FoursquareClient()
    
    for category in categories:
        query = FOURSQUARE_QUERY_MAP.get(category)
        if not query:
            logger.warning(f"[Curation] No query mapping for category: {category}")
            continue
            
        try:
            # Use search_by_query for NEW API compatibility
            places = await client.search_by_query(
                lat=lat,
                lng=lng,
                query=query,
                radius=radius,
                limit=5
            )
            results[category] = places
            logger.info(f"[Curation] Foursquare {category} (query='{query}'): {len(places)} results")
        except Exception as e:
            logger.error(f"[Curation] Foursquare {category} error: {e}")
            results[category] = []
            
    return results


async def _fetch_transit_stops(
    lat: float, 
    lng: float,
    radius: int = 2000
) -> Dict[str, Any]:
    """Fetch transit stops from Transitland."""
    client = TransitlandClient()
    
    try:
        result = await client.search_metro_and_train(
            lat=lat,
            lng=lng,
            radius=radius
        )
        
        metro = result.get("metro")
        bus = result.get("bus") or result.get("train")  # Fallback to train
        
        logger.info(f"[Curation] Transit: metro={metro is not None}, bus={bus is not None}")
        
        return {"metro": metro, "bus": bus}
        
    except Exception as e:
        logger.error(f"[Curation] Transitland error: {e}")
        return {"metro": None, "bus": None}


async def _save_curated_places(
    listing_id: int, 
    places: List[CuratedPlaceV2], 
    empty_slots: Dict[str, Any]
):
    """Save curated places and empty slots to database."""
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        # Delete existing
        await client.delete(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}"}
        )
        
        # Insert new places
        saved_count = 0
        logger.info(f"[Curation] Inserting {len(places)} places...")
        for place in places:
            data = {"listing_id": listing_id, **place.to_dict()}
            # Remove None values and complex objects
            data = {k: v for k, v in data.items() if v is not None and k not in ("tour_sequence", "tour_keyframes")}
            
            logger.debug(f"[Curation] POST data for {place.name}: {list(data.keys())}")
            response = await client.post(f"{base_url}/curated_places", json=data)
            logger.info(f"[Curation] POST response: {response.status_code}")
            if response.status_code not in (200, 201):
                logger.error(f"[Curation] Insert failed for {place.name}: {response.status_code} - {response.text[:500]}")
            else:
                saved_count += 1
                logger.info(f"[Curation] ✅ Saved slot {place.slot}: {place.name}")
        
        logger.info(f"[Curation] Saved {saved_count}/{len(places)} places")
        
        # Save empty slots as area characteristics
        if empty_slots:
            listing = await database.get_listing(listing_id)
            if listing:
                scraped_data = listing.get("scraped_data", {}) or {}
                scraped_data["area_characteristics"] = {
                    "empty_slots": empty_slots,
                    "is_quiet_area": any(info.get("indicates_quietness") for info in empty_slots.values()),
                }
                
                await client.patch(
                    f"{base_url}/listings",
                    params={"id": f"eq.{listing_id}"},
                    json={"scraped_data": scraped_data}
                )
        
    except Exception as e:
        import traceback
        logger.error(f"[Curation] Save failed: {e}")
        logger.error(f"[Curation] Traceback: {traceback.format_exc()}")


async def _cache_tiles_for_curation(
    listing_id: int,
    property_lat: float,
    property_lng: float,
    places: List[CuratedPlaceV2]
) -> Dict[str, int]:
    """
    Cache Street View tiles for property and all curated places.
    """
    cached = 0
    failed = 0
    
    client = await database.get_client()
    base_url = database._get_base_url()
    
    # 1. Cache property tiles (slot 1)
    logger.info(f"[TileCache] Slot 1 (Property): fetching tiles...")
    try:
        property_tiles = await fetch_and_cache_panorama(
            lat=property_lat,
            lng=property_lng,
            listing_id=listing_id,
            slot=1,
            force_refresh=True
        )
        
        if property_tiles:
            await client.patch(
                f"{base_url}/listings",
                params={"id": f"eq.{listing_id}"},
                json={"street_view_tile_urls": property_tiles}
            )
            cached += 1
            logger.info(f"[TileCache] Slot 1 (Property): ✅ {property_tiles['tile_count']} tiles")
        else:
            failed += 1
            logger.warning(f"[TileCache] Slot 1 (Property): No Street View")
    except Exception as e:
        failed += 1
        logger.error(f"[TileCache] Slot 1 error: {e}")
    
    await asyncio.sleep(0.3)
    
    # 2. Cache tiles for each curated place
    for place in places:
        slot = place.slot
        name = place.name[:30]
        lat = place.lat
        lng = place.lng
        
        if not lat or not lng:
            logger.warning(f"[TileCache] Slot {slot} ({name}): skipping, no coords")
            continue
        
        logger.info(f"[TileCache] Slot {slot} ({name}): fetching tiles...")
        
        try:
            tile_urls = await fetch_and_cache_panorama(
                lat=float(lat),
                lng=float(lng),
                listing_id=listing_id,
                slot=slot,
                force_refresh=True
            )
            
            if tile_urls:
                await client.patch(
                    f"{base_url}/curated_places",
                    params={"listing_id": f"eq.{listing_id}", "slot": f"eq.{slot}"},
                    json={"tile_urls": tile_urls}
                )
                cached += 1
                logger.info(f"[TileCache] Slot {slot} ({name}): ✅ {tile_urls['tile_count']} tiles")
            else:
                failed += 1
                logger.warning(f"[TileCache] Slot {slot} ({name}): No Street View")
                
        except Exception as e:
            failed += 1
            logger.error(f"[TileCache] Slot {slot} error: {e}")
        
        await asyncio.sleep(0.3)
    
    return {"cached": cached, "failed": failed}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/listings/{listing_id}/curate-places", response_model=CurationResponse)
async def curate_places(listing_id: int, force_refresh: bool = False):
    """
    Curate nearby places for a listing using Google Places API.
    
    V3 Flow (Google-powered):
    1. Fetches POIs from Google Places (Nearby Search Pro)
    2. Fetches transit from Transitland
    3. Fetches nature from Overture (FREE)
    4. Caches Street View tiles
    5. Saves to database
    
    Cost: ~$0.26/listing (first 625/month FREE)
    """
    logger.info(f"[Curation] Starting V3 curation for listing {listing_id}")
    
    try:
        # Get listing
        listing = await database.get_listing(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        lat = listing.get("lat")
        lng = listing.get("lng")
        
        if not lat or not lng:
            raise HTTPException(status_code=400, detail="Listing has no coordinates")
        
        lat, lng = float(lat), float(lng)
        logger.info(f"[Curation] Using coordinates: ({lat}, {lng})")
        
        # Use the new Google-powered CurationService
        service = CurationService()
        result = await service.curate_places(lat, lng, property_heading=0)
        
        places = result.get("places", [])
        empty_slots = result.get("empty_slots", {})
        transit_isochrone = result.get("transit_isochrone")  # GeoJSON or None
        walk_isochrone = result.get("walk_isochrone")        # GeoJSON or None
        walk_2min_isochrone = result.get("walk_2min_isochrone")  # GeoJSON or None
        
        logger.info(f"[Curation] CurationService returned {len(places)} places, transit: {'✓' if transit_isochrone else '✗'}, walk15: {'✓' if walk_isochrone else '✗'}, walk2: {'✓' if walk_2min_isochrone else '✗'}")
        
        # Save places to database
        await _save_curated_places_v3(listing_id, places, empty_slots)
        
        # Cache Street View tiles (optional, can be slow)
        cache_result = {"cached": 0, "failed": 0}
        # Uncomment to enable tile caching:
        # cache_result = await _cache_tiles_for_curation(listing_id, lat, lng, places)
        
        logger.info(f"[Curation] ✅ Complete: {len(places)} places saved")
        
        # Fetch saved places from DB to ensure response matches what's stored
        saved_places = await _get_curated_places_from_db(listing_id)
        
        return CurationResponse(
            success=True,
            listing_id=listing_id,
            places=[CuratedPlaceResponse(**p) for p in saved_places],
            empty_slots=empty_slots,
            tiles_cached=cache_result["cached"],
            tiles_failed=cache_result["failed"],
            transit_isochrone=transit_isochrone,
            walk_isochrone=walk_isochrone,
            walk_2min_isochrone=walk_2min_isochrone,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[Curation] Error: {e}")
        logger.error(traceback.format_exc())
        return CurationResponse(
            success=False,
            listing_id=listing_id,
            places=[],
            error=str(e)
        )


async def _get_curated_places_from_db(listing_id: int) -> List[Dict[str, Any]]:
    """Fetch curated places from database."""
    import httpx
    import database
    
    base_url = database._get_base_url()
    headers = database._get_headers()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}", "select": "*"},
            headers=headers
        )
        data = response.json()
    
    places = []
    for row in data or []:
        places.append({
            "slot": row.get("slot"),
            "name": row.get("name"),
            "category": row.get("category"),
            "lat": row.get("lat"),
            "lng": row.get("lng"),
            "distance_m": row.get("distance_m"),
            "walk_mins": row.get("walk_mins"),  # Frontend expects walk_mins
            "rating": row.get("rating"),
            "source": row.get("source"),
            "google_place_id": row.get("google_place_id"),
            "is_open_now": row.get("is_open_now"),
            "is_open_late": row.get("is_open_late"),
            "weekday_hours": row.get("weekday_hours"),
            "rating_count": row.get("rating_count"),
            "transit_routes": row.get("transit_routes"),
            "transit_stop_id": row.get("transit_stop_id"),
        })
    
    return places


def _place_to_response(place: CuratedPlaceV2) -> Dict[str, Any]:
    """Convert CuratedPlaceV2 to response dict format."""
    walk_mins = place.walk_mins or int(round(place.distance_m / 80))
    return {
        "slot": place.slot,
        "name": place.name,
        "category": place.category,
        "lat": place.lat,
        "lng": place.lng,
        "distance_m": int(place.distance_m),
        "walking_min": walk_mins,  # Frontend expects this field name
        "rating": place.rating,
        "source": place.source,
        "google_place_id": place.google_place_id,
        # V3: New fields (for API response, even if not in DB)
        "is_open_now": place.is_open_now,
        "is_open_late": place.is_open_late,
        "weekday_hours": place.weekday_hours,
        "rating_count": place.rating_count,
        # Transit routes with geometry (for metro/bus)
        "transit_routes": place.transit_routes,
        "transit_stop_id": place.transit_stop_id,
    }


async def _save_curated_places_v3(
    listing_id: int, 
    places: List[CuratedPlaceV2], 
    empty_slots: Dict[str, Any]
):
    """Save V3 curated places to database."""
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        # Delete existing
        await client.delete(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}"}
        )
        
        # Insert new places
        saved_count = 0
        logger.info(f"[Curation] Inserting {len(places)} places...")
        
        for place in places:
            # Calculate walk_mins (distance in meters / 80 m/min)
            walk_mins = place.walk_mins or int(round(place.distance_m / 80))
            
            # Map source to valid DB values
            source_map = {
                "google": "google_maps",
                "google_maps": "google_maps",
                "overture": "overture",
                "transitland": "transitland",
                "foursquare": "foursquare",
            }
            db_source = source_map.get(place.source, "google_maps")
            
            data = {
                "listing_id": listing_id,
                "slot": place.slot,
                "name": place.name,
                "category": place.category,
                "lat": place.lat,
                "lng": place.lng,
                "distance_m": int(place.distance_m),  # integer column
                "walk_mins": int(walk_mins),  # integer column
                "rating": place.rating,
                "source": db_source,  # Must match DB constraint
                "google_place_id": place.google_place_id,
                # Transit routes with geometry (for metro/bus stops)
                "transit_routes": place.transit_routes,
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            response = await client.post(f"{base_url}/curated_places", json=data)
            
            if response.status_code not in (200, 201):
                logger.error(f"[Curation] Insert failed for {place.name}: {response.status_code} - {response.text[:200]}")
            else:
                saved_count += 1
                late_badge = "🌙" if place.is_open_late else ""
                logger.info(f"[Curation] ✅ Slot {place.slot}: {place.name} ({place.rating or 'N/A'}⭐) {late_badge}")
        
        logger.info(f"[Curation] Saved {saved_count}/{len(places)} places")
        
        # Save empty slots as area characteristics
        if empty_slots:
            listing = await database.get_listing(listing_id)
            if listing:
                scraped_data = listing.get("scraped_data", {}) or {}
                scraped_data["area_characteristics"] = {
                    "empty_slots": empty_slots,
                    "is_quiet_area": any(info.get("indicates_quietness") for info in empty_slots.values()),
                }
                
                await client.patch(
                    f"{base_url}/listings",
                    params={"id": f"eq.{listing_id}"},
                    json={"scraped_data": scraped_data}
                )
        
    except Exception as e:
        import traceback
        logger.error(f"[Curation] Save failed: {e}")
        logger.error(traceback.format_exc())


@router.get("/listings/{listing_id}/curated-places")
async def get_curated_places(listing_id: int):
    """Get curated places for a listing, including isochrones."""
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        # Fetch places
        response = await client.get(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}", "select": "*", "order": "slot.asc"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch places")
        
        places = response.json()
        
        # If we have places, also fetch isochrones for the listing
        walk_2min_isochrone = None
        walk_isochrone = None
        transit_isochrone = None
        
        if places:
            # Get listing coordinates
            listing_response = await client.get(
                f"{base_url}/listings",
                params={"id": f"eq.{listing_id}", "select": "lat,lng"}
            )
            
            if listing_response.status_code == 200:
                listings = listing_response.json()
                if listings and listings[0].get("lat") and listings[0].get("lng"):
                    lat = float(listings[0]["lat"])
                    lng = float(listings[0]["lng"])
                    
                    # Fetch isochrones in parallel (2min, 15min walk + 30min transit)
                    from clients.geoapify_isochrone import get_walking_isochrone, get_transit_isochrone
                    import asyncio
                    
                    try:
                        walk_2min_task = get_walking_isochrone(lat, lng, minutes=1)
                        walk_task = get_walking_isochrone(lat, lng, minutes=15)
                        transit_task = get_transit_isochrone(lat, lng, minutes=30)
                        
                        walk_2min_isochrone, walk_isochrone, transit_isochrone = await asyncio.gather(
                            walk_2min_task, walk_task, transit_task, return_exceptions=True
                        )
                        
                        # Handle exceptions
                        if isinstance(walk_2min_isochrone, Exception):
                            logger.warning(f"[Curation] 2-min walk isochrone fetch failed: {walk_2min_isochrone}")
                            walk_2min_isochrone = None
                        if isinstance(walk_isochrone, Exception):
                            logger.warning(f"[Curation] 15-min walk isochrone fetch failed: {walk_isochrone}")
                            walk_isochrone = None
                        if isinstance(transit_isochrone, Exception):
                            logger.warning(f"[Curation] Transit isochrone fetch failed: {transit_isochrone}")
                            transit_isochrone = None
                            
                        logger.info(f"[Curation] Fetched isochrones: walk2={'✓' if walk_2min_isochrone else '✗'}, walk15={'✓' if walk_isochrone else '✗'}, transit={'✓' if transit_isochrone else '✗'}")
                    except Exception as e:
                        logger.warning(f"[Curation] Isochrone fetch error: {e}")
        
        return {
            "places": places,
            "walk_2min_isochrone": walk_2min_isochrone,
            "walk_isochrone": walk_isochrone,
            "transit_isochrone": transit_isochrone,
        }
        
    except Exception as e:
        logger.error(f"[Curation] Get places error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transit/stop/{stop_id}/departures")
async def get_stop_departures(stop_id: str, feed: str = None):
    """
    Get real schedule/departure info for a transit stop from Transitland.
    
    Args:
        stop_id: GTFS stop ID
        feed: Optional feed onestop_id (e.g., "f-sp3e-tmb") for disambiguation
    
    Returns service info for each route at this stop:
    - first_departure: First service time (e.g., "05:30")
    - last_departure: Last service time (e.g., "23:45")
    - frequency_mins: Average minutes between departures
    - is_night_service: True if primarily night service
    - is_24h: True if 24-hour service
    """
    from clients.transitland_client import TransitlandClient
    
    try:
        client = TransitlandClient()
        service_info = await client.get_stop_departures(stop_id, feed_onestop_id=feed)
        
        # Convert dataclass to dict for JSON response
        result = {}
        for route_id, info in service_info.items():
            result[route_id] = {
                "first_departure": info.first_departure,
                "last_departure": info.last_departure,
                "frequency_mins": info.frequency_mins,
                "departures_per_hour": info.departures_per_hour,
                "is_night_service": info.is_night_service,
                "is_24h": info.is_24h,
            }
        
        return {
            "success": True,
            "stop_id": stop_id,
            "feed": feed,
            "routes": result,
        }
        
    except Exception as e:
        logger.error(f"[Transit] Departures fetch error: {e}")
        return {
            "success": False,
            "stop_id": stop_id,
            "routes": {},
            "error": str(e),
        }


# =============================================================================
# TRANSIT ISOCHRONE
# =============================================================================

@router.get("/transit/isochrone")
async def get_transit_isochrone(
    lat: float,
    lng: float,
    minutes: int = 30,
    mode: str = "transit",
):
    """
    Get a transit accessibility isochrone showing how far you can travel.
    
    Uses Geoapify Isoline API to calculate reachable area by public transport.
    
    Args:
        lat: Latitude of origin (property location)
        lng: Longitude of origin (property location)
        minutes: Travel time in minutes (default: 30)
        mode: Travel mode - "transit" (default), "walk", "drive", "bicycle", "bus"
    
    Returns:
        GeoJSON FeatureCollection with isochrone polygon
    
    Cost: ~6 credits for 30-min isochrone (3000 credits/day free)
    """
    from clients.geoapify_isochrone import get_transit_isochrone as fetch_isochrone
    
    try:
        logger.info(f"[Isochrone] Fetching {minutes}min {mode} isochrone from ({lat}, {lng})")
        
        result = await fetch_isochrone(
            lat=lat,
            lng=lng,
            minutes=minutes,
            mode=mode,
        )
        
        if not result:
            return {
                "success": False,
                "error": "Failed to generate isochrone. Check API key.",
            }
        
        # Handle async processing
        if result.get("status") == "processing":
            return {
                "success": True,
                "status": "processing",
                "id": result.get("id"),
                "message": "Isochrone is being calculated. Poll with ID to retrieve.",
            }
        
        # Return successful GeoJSON
        return {
            "success": True,
            "type": result.get("type"),
            "features": result.get("features", []),
            "metadata": {
                "lat": lat,
                "lng": lng,
                "minutes": minutes,
                "mode": mode,
            }
        }
        
    except Exception as e:
        logger.error(f"[Isochrone] Error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/transit/isochrone/{isoline_id}")
async def get_isochrone_by_id(isoline_id: str):
    """
    Retrieve a previously generated isochrone by ID.
    
    Use this to poll for async isochrones that returned status=processing.
    IDs are valid for 24 hours.
    """
    from clients.geoapify_isoline_client import get_isochrone_by_id as fetch_by_id
    
    try:
        result = await fetch_by_id(isoline_id)
        
        if not result:
            return {"success": False, "error": "Isochrone not found or expired"}
        
        if result.get("status") == "processing":
            return {"success": True, "status": "processing", "id": isoline_id}
        
        return {
            "success": True,
            "type": result.get("type"),
            "features": result.get("features", []),
        }
        
    except Exception as e:
        logger.error(f"[Isochrone] Retrieve error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# TOUR GENERATION
# =============================================================================

@router.post("/listings/{listing_id}/generate-tours", response_model=TourGenerationResponse)
async def generate_tours_for_listing(listing_id: int, force_refresh: bool = False):
    """
    Generate Gemini-powered tours for all curated places.
    """
    from services.tour_generator import TourGenerator
    
    logger.info(f"[TourGen] Starting tour generation for listing {listing_id}")
    
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        # Get listing info
        listing_response = await client.get(
            f"{base_url}/listings",
            params={"id": f"eq.{listing_id}", "select": "id,lat,lng,title,street_view_tile_urls"}
        )
        
        if listing_response.status_code != 200:
            return TourGenerationResponse(success=False, error="Failed to fetch listing")
        
        listings = listing_response.json()
        if not listings:
            return TourGenerationResponse(success=False, error="Listing not found")
        
        listing = listings[0]
        
        # Get curated places
        places_response = await client.get(
            f"{base_url}/curated_places",
            params={"listing_id": f"eq.{listing_id}", "select": "*", "order": "slot.asc"}
        )
        
        if places_response.status_code != 200:
            return TourGenerationResponse(success=False, error="Failed to fetch curated places")
        
        places = places_response.json()
        
        # Initialize services
        sv_client = StreetViewClient()
        generator = TourGenerator()
        
        generated = 0
        failed = 0
        tours = []
        
        # Generate tour for property (slot 1)
        property_lat = listing.get("lat")
        property_lng = listing.get("lng")
        property_tiles = listing.get("street_view_tile_urls")
        
        if property_lat and property_lng and property_tiles:
            if property_tiles.get("tour_program") and not force_refresh:
                logger.info(f"[TourGen] Slot 1 (Property): already has tour, skipping")
                tours.append({"slot": 1, "tour": property_tiles.get("tour_program")})
                generated += 1
            else:
                logger.info(f"[TourGen] Slot 1 (Property): generating tour...")
                try:
                    gemini_data = await sv_client.fetch_panorama_for_gemini(
                        float(property_lat), float(property_lng)
                    )
                    
                    if gemini_data:
                        tour = await generator.generate_tour(
                            panorama_image=gemini_data["image"],
                            location_type="property",
                            location_name=listing.get("title", "Property")[:50],
                            property_heading=0,
                            pano_id=gemini_data["pano_id"],
                        )
                        
                        tour_dict = generator.sequence_to_dict(tour)
                        
                        property_tiles["tour_program"] = tour_dict
                        await client.patch(
                            f"{base_url}/listings",
                            params={"id": f"eq.{listing_id}"},
                            json={"street_view_tile_urls": property_tiles}
                        )
                        
                        generated += 1
                        tours.append({"slot": 1, "tour": tour_dict})
                        logger.info(f"[TourGen] Slot 1 (Property): ✅ Generated {len(tour.actions)} actions")
                    else:
                        failed += 1
                        logger.warning(f"[TourGen] Slot 1 (Property): No panorama available")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"[TourGen] Slot 1 error: {e}")
        
        await asyncio.sleep(0.3)
        
        # Generate tours for curated places (parallel with stagger)
        async def generate_tour_for_place(place: Dict, delay: float) -> Dict:
            await asyncio.sleep(delay)
            
            slot = place.get("slot")
            name = place.get("name", "Unknown")[:30]
            lat = place.get("lat")
            lng = place.get("lng")
            tile_urls = place.get("tile_urls")
            
            if not lat or not lng or not tile_urls:
                logger.warning(f"[TourGen] Slot {slot} ({name}): skipping, no tiles")
                return {"slot": slot, "status": "skipped", "reason": "no tiles"}
            
            existing_tour = place.get("tour_program")
            if existing_tour and not force_refresh:
                logger.info(f"[TourGen] Slot {slot} ({name}): already has tour")
                return {"slot": slot, "status": "cached", "tour": existing_tour}
            
            logger.info(f"[TourGen] Slot {slot} ({name}): generating...")
            
            try:
                gemini_data = await sv_client.fetch_panorama_for_gemini(
                    float(lat), float(lng)
                )
                
                if not gemini_data:
                    return {"slot": slot, "status": "failed", "reason": "no panorama"}
                
                tour = await generator.generate_tour(
                    panorama_image=gemini_data["image"],
                    location_type=place.get("category", "place"),
                    location_name=name,
                    property_heading=place.get("sv_heading", 0),
                    pano_id=gemini_data["pano_id"],
                    distance_meters=place.get("distance_m"),
                    walking_minutes=place.get("walking_min"),
                )
                
                tour_dict = generator.sequence_to_dict(tour)
                
                place_id = place.get("id")
                if place_id:
                    await client.patch(
                        f"{base_url}/curated_places",
                        params={"id": f"eq.{place_id}"},
                        json={"tour_program": tour_dict}
                    )
                
                logger.info(f"[TourGen] Slot {slot} ({name}): ✅ Done ({len(tour.actions)} actions)")
                return {"slot": slot, "status": "generated", "tour": tour_dict}
                
            except Exception as e:
                logger.error(f"[TourGen] Slot {slot} error: {e}")
                return {"slot": slot, "status": "failed", "reason": str(e)}
        
        # Launch parallel with stagger
        tasks = [
            generate_tour_for_place(place, i * 0.2)
            for i, place in enumerate(places)
        ]
        
        logger.info(f"[TourGen] 🚀 Starting {len(tasks)} parallel tour generations")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result.get("status") == "generated":
                generated += 1
                tours.append({"slot": result["slot"], "tour": result["tour"]})
            elif result.get("status") == "cached":
                generated += 1
                tours.append({"slot": result["slot"], "tour": result["tour"]})
            else:
                failed += 1
        
        logger.info(f"[TourGen] 🎉 Complete! Generated: {generated}, Failed: {failed}")
        
        return TourGenerationResponse(
            success=True,
            generated=generated,
            failed=failed,
            tours=tours
        )
        
    except Exception as e:
        logger.error(f"[TourGen] Error: {e}")
        return TourGenerationResponse(success=False, error=str(e))

