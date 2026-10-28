"""
Google Places Client - Nearby Search Pro
=========================================

Primary POI discovery using Google Places API (New) - Nearby Search Pro tier.

Features:
- Direct lat/lng coordinates (no geocoding needed)
- Opening hours (regularOpeningHours)
- Ratings and review counts
- Primary place type

Cost: $32/1000 calls (Nearby Search Pro) - First 5,000/month FREE
See: docs/GOOGLE_PLACES_API_DECISION.md

Decision Date: 2024-12-31
Replaces: Foursquare + Google Geocoding fallback
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")

# Nearby Search Pro field mask - carefully selected for cost optimization
# These fields trigger Pro tier pricing ($32/1000)
NEARBY_SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.location",
    "places.primaryType",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",
    "places.regularOpeningHours",
])


@dataclass
class NearbyPlace:
    """A place from Google Nearby Search with full Pro data."""
    id: str
    name: str
    lat: float
    lng: float
    primary_type: str
    address: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    opening_hours: Optional[Dict[str, Any]] = None
    weekday_descriptions: Optional[List[str]] = None
    is_open_now: Optional[bool] = None
    is_open_late: bool = False  # Closes after 11 PM


@dataclass
class VerifiedPlace:
    """A place with Google-verified coordinates (legacy)."""
    name: str
    lat: float
    lng: float
    place_id: str
    formatted_address: Optional[str] = None
    original_lat: Optional[float] = None  # Foursquare's coords
    original_lng: Optional[float] = None
    distance_from_original: Optional[float] = None  # meters


class GooglePlacesClient:
    """
    Google Places API client - Primary POI discovery.
    
    Uses Places API (New) Nearby Search Pro for all POI discovery.
    No longer depends on Foursquare.
    
    Usage:
        client = GooglePlacesClient()
        
        # New: Nearby Search (recommended)
        places = await client.nearby_search(
            lat=41.3851, lng=2.1734,
            types=["restaurant", "cafe"],
            radius_m=500,
            max_results=5
        )
        for p in places:
            print(f"{p.name}: {p.rating}⭐ - {p.is_open_late and '🌙 Late Night' or ''}")
        
        # Legacy: Coordinate verification
        verified = await client.verify_place_coordinates(
            name="Mercadona",
            foursquare_lat=41.4898735,
            foursquare_lng=2.0209857
        )
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_MAPS_KEY
        if not self.api_key:
            logger.warning("⚠️ GOOGLE_MAPS_KEY not set - Places API disabled")
    
    # =========================================================================
    # NEARBY SEARCH (NEW - PRIMARY METHOD)
    # =========================================================================
    
    async def nearby_search(
        self,
        lat: float,
        lng: float,
        types: List[str],
        radius_m: int = 500,
        max_results: int = 5,
        rank_by: str = "POPULARITY",
    ) -> List[NearbyPlace]:
        """
        Search for places near a location using Google Places API (New).
        
        This is the PRIMARY method for POI discovery. Uses Pro tier for
        ratings and opening hours.
        
        Args:
            lat, lng: Center point coordinates
            types: Google place types (e.g., ["restaurant", "cafe"])
            radius_m: Search radius in meters (max 50,000)
            max_results: Max places to return (1-20)
            rank_by: "POPULARITY" or "DISTANCE"
            
        Returns:
            List of NearbyPlace with full Pro data (rating, hours, etc.)
            
        Cost: $0.032 per request (Pro tier)
        """
        if not self.api_key:
            logger.error("[GooglePlaces] No API key - cannot search")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = "https://places.googleapis.com/v1/places:searchNearby"
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": NEARBY_SEARCH_FIELD_MASK,
                }
                
                body = {
                    "includedTypes": types,
                    "maxResultCount": min(max_results, 20),
                    "rankPreference": rank_by,
                    "locationRestriction": {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lng},
                            "radius": float(min(radius_m, 50000))
                        }
                    }
                }
                
                logger.info(f"[GooglePlaces] Searching {types} within {radius_m}m of ({lat:.4f}, {lng:.4f})")
                
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    error_text = response.text[:500]
                    logger.error(f"[GooglePlaces] API error {response.status_code}: {error_text}")
                    return []
                
                data = response.json()
                places = data.get("places", [])
                
                results = []
                for p in places:
                    nearby = self._parse_nearby_place(p)
                    if nearby:
                        results.append(nearby)
                
                logger.info(f"[GooglePlaces] Found {len(results)} places")
                return results
                
        except Exception as e:
            logger.error(f"[GooglePlaces] Error in nearby_search: {e}")
            return []
    
    def _parse_nearby_place(self, data: Dict[str, Any]) -> Optional[NearbyPlace]:
        """Parse a place from Google's Nearby Search response."""
        try:
            location = data.get("location", {})
            lat = location.get("latitude")
            lng = location.get("longitude")
            
            if not lat or not lng:
                return None
            
            display_name = data.get("displayName", {})
            name = display_name.get("text", "Unknown")
            
            # Parse opening hours
            opening_hours = data.get("regularOpeningHours", {})
            weekday_descriptions = opening_hours.get("weekdayDescriptions", [])
            is_open_now = opening_hours.get("openNow")
            
            # Determine if open late
            is_open_late = self._is_open_late(opening_hours)
            
            return NearbyPlace(
                id=data.get("id", ""),
                name=name,
                lat=lat,
                lng=lng,
                primary_type=data.get("primaryType", ""),
                address=data.get("formattedAddress"),
                rating=data.get("rating"),
                review_count=data.get("userRatingCount"),
                opening_hours=opening_hours if opening_hours else None,
                weekday_descriptions=weekday_descriptions if weekday_descriptions else None,
                is_open_now=is_open_now,
                is_open_late=is_open_late,
            )
        except Exception as e:
            logger.warning(f"[GooglePlaces] Error parsing place: {e}")
            return None
    
    def _is_open_late(self, opening_hours: Dict[str, Any]) -> bool:
        """
        Determine if a place is open late (closes after 11 PM or crosses midnight).
        
        A place is "open late" if ANY day of the week it closes after 23:00
        or crosses midnight (close day != open day).
        """
        if not opening_hours:
            return False
        
        periods = opening_hours.get("periods", [])
        
        for period in periods:
            open_info = period.get("open", {})
            close_info = period.get("close", {})
            
            open_day = open_info.get("day")
            close_day = close_info.get("day")
            close_hour = close_info.get("hour", 0)
            
            # Crosses midnight (closes on different day than opens)
            if close_day is not None and open_day is not None and close_day != open_day:
                return True
            
            # Closes at or after 11 PM (23:00)
            if close_hour >= 23:
                return True
        
        return False
    
    # =========================================================================
    # LEGACY METHODS (for backward compatibility)
    # =========================================================================
    
    async def verify_place_coordinates(
        self,
        name: str,
        foursquare_lat: float,
        foursquare_lng: float,
        search_radius: int = 500,
    ) -> Optional[VerifiedPlace]:
        """
        Use Google Find Place (legacy) to verify/correct POI coordinates.
        
        Args:
            name: Place name from Foursquare (e.g., "Mercadona")
            foursquare_lat: Latitude from Foursquare
            foursquare_lng: Longitude from Foursquare
            search_radius: Search radius around Foursquare coords (meters)
            
        Returns:
            VerifiedPlace with Google's coordinates, or None if not found
        """
        if not self.api_key:
            logger.warning("[GooglePlaces] No API key - returning original coordinates")
            return VerifiedPlace(
                name=name,
                lat=foursquare_lat,
                lng=foursquare_lng,
                place_id="",
                original_lat=foursquare_lat,
                original_lng=foursquare_lng,
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use legacy Find Place API
                # Docs: https://developers.google.com/maps/documentation/places/web-service/search-find-place
                url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                
                params = {
                    "input": name,
                    "inputtype": "textquery",
                    "fields": "place_id,name,geometry,formatted_address",
                    "locationbias": f"circle:{search_radius}@{foursquare_lat},{foursquare_lng}",
                    "key": self.api_key
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"[GooglePlaces] API error: {response.status_code} - {response.text[:200]}")
                    return None
                
                data = response.json()
                
                if data.get("status") != "OK":
                    status = data.get("status", "UNKNOWN")
                    error_msg = data.get("error_message", "")
                    logger.warning(f"[GooglePlaces] Status: {status} - {error_msg}")
                    if status == "ZERO_RESULTS":
                        logger.warning(f"[GooglePlaces] No results for '{name}' near {foursquare_lat},{foursquare_lng}")
                    return None
                
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.warning(f"[GooglePlaces] No candidates for '{name}'")
                    return None
                
                place = candidates[0]
                location = place.get("geometry", {}).get("location", {})
                google_lat = location.get("lat")
                google_lng = location.get("lng")
                
                if not google_lat or not google_lng:
                    logger.warning(f"[GooglePlaces] No coordinates in response for '{name}'")
                    return None
                
                # Calculate distance from original
                distance = self._haversine_distance(
                    foursquare_lat, foursquare_lng,
                    google_lat, google_lng
                )
                
                verified = VerifiedPlace(
                    name=place.get("name", name),
                    lat=google_lat,
                    lng=google_lng,
                    place_id=place.get("place_id", ""),
                    formatted_address=place.get("formatted_address"),
                    original_lat=foursquare_lat,
                    original_lng=foursquare_lng,
                    distance_from_original=round(distance, 1)
                )
                
                logger.info(
                    f"[GooglePlaces] Verified '{name}': "
                    f"({foursquare_lat:.6f},{foursquare_lng:.6f}) → "
                    f"({google_lat:.6f},{google_lng:.6f}) "
                    f"[{distance:.0f}m difference]"
                )
                
                return verified
                
        except Exception as e:
            logger.error(f"[GooglePlaces] Error verifying '{name}': {e}")
            return None
    
    async def geocode_address(
        self,
        address: str,
        name: Optional[str] = None,
        bias_lat: Optional[float] = None,
        bias_lng: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Geocode an address to get coordinates using Google Find Place.
        
        Args:
            address: Full address string (e.g., "C. de Sant Pere Més Alt, 49, 08003 Barcelona")
            name: Optional place name to improve matching
            bias_lat, bias_lng: Optional location to bias search results
            
        Returns:
            Dict with {lat, lng, place_id, formatted_address} or None
        """
        if not self.api_key:
            logger.warning("[GooglePlaces] No API key - cannot geocode")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                
                # Combine name + address for better matching
                search_input = f"{name}, {address}" if name else address
                
                params = {
                    "input": search_input,
                    "inputtype": "textquery",
                    "fields": "place_id,name,geometry,formatted_address",
                    "key": self.api_key
                }
                
                # Add location bias if provided
                if bias_lat and bias_lng:
                    params["locationbias"] = f"circle:5000@{bias_lat},{bias_lng}"
                
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"[GooglePlaces] Geocode error: {response.status_code}")
                    return None
                
                data = response.json()
                
                if data.get("status") != "OK" or not data.get("candidates"):
                    logger.warning(f"[GooglePlaces] No geocode results for: {search_input[:50]}")
                    return None
                
                place = data["candidates"][0]
                geometry = place.get("geometry", {}).get("location", {})
                
                result = {
                    "lat": geometry.get("lat"),
                    "lng": geometry.get("lng"),
                    "place_id": place.get("place_id"),
                    "formatted_address": place.get("formatted_address"),
                    "found": True
                }
                
                logger.info(f"[GooglePlaces] Geocoded '{name or address[:30]}' → ({result['lat']}, {result['lng']})")
                return result
                
        except Exception as e:
            logger.error(f"[GooglePlaces] Geocode error: {e}")
            return None
    
    def _haversine_distance(
        self,
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """Calculate distance between two points in meters."""
        import math
        
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_building_addresses_nearby(
    lat: float,
    lng: float,
    radius_m: int = 500,
    max_results: int = 20,
) -> List[str]:
    """
    Get REAL addresses of buildings near a location.
    
    ONE API call → up to 20 addresses that EXIST in Cadastre.
    
    Cost: $0.032 per call (Pro tier)
    
    Args:
        lat, lng: Center coordinates
        radius_m: Search radius (default 500m)
        max_results: Max addresses (up to 20)
        
    Returns:
        List of formatted addresses (e.g., ["Calle Mayor, 15, Madrid", ...])
    """
    client = GooglePlacesClient()
    
    if not client.api_key:
        logger.warning("[GooglePlaces] No API key - cannot get nearby addresses")
        return []
    
    # Use diverse building types to get residential/commercial addresses
    # These are Google-supported types (see: https://developers.google.com/maps/documentation/places/web-service/supported_types)
    building_types = ["store", "restaurant", "bank", "pharmacy", "lodging"]
    
    places = await client.nearby_search(
        lat=lat,
        lng=lng,
        types=building_types,
        radius_m=radius_m,
        max_results=max_results,
        rank_by="DISTANCE",  # Get closest ones
    )
    
    # Extract unique addresses
    addresses = []
    seen = set()
    
    for place in places:
        if place.address and place.address not in seen:
            # Clean up address (remove country suffix if present)
            addr = place.address.replace(", Spain", "").replace(", España", "").strip()
            if addr and len(addr) > 10:
                addresses.append(addr)
                seen.add(place.address)
    
    logger.info(f"[GooglePlaces] Found {len(addresses)} unique addresses near ({lat:.4f}, {lng:.4f})")
    return addresses


async def verify_poi_coordinates(
    name: str,
    lat: float,
    lng: float,
) -> Tuple[float, float, Optional[str]]:
    """
    Quick function to verify POI coordinates.
    
    Returns:
        Tuple of (verified_lat, verified_lng, google_place_id)
        Falls back to original coords if verification fails
    """
    client = GooglePlacesClient()
    result = await client.verify_place_coordinates(name, lat, lng)
    
    if result:
        return result.lat, result.lng, result.place_id
    else:
        return lat, lng, None
