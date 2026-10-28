"""
Place Curation Service V3
=========================

GOOGLE-ONLY POI DISCOVERY
-------------------------
As of 2024-12-31, we use Google Places API (New) Nearby Search Pro for all POI discovery.
This replaces Foursquare entirely.

Advantages:
- Direct lat/lng (no geocoding needed)
- Opening hours included
- Ratings and review counts
- Single API = simpler code

Cost: $0.032/request (~$0.26/listing)
First 5,000 requests/month = FREE (~625 listings)

See: docs/GOOGLE_PLACES_API_DECISION.md

Uses:
- Google Places API (New): All POI discovery
- Transitland: Metro, Train, Bus, Tram
- Overture: Parks, beaches, nature (FREE)
- Street View: Panorama tiles for Gemini analysis
"""

import logging
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from clients.google_places_client import (
    GooglePlacesClient, NearbyPlace,
)
from clients.overture_client import (
    OvertureClient, OverturePlace,
    # search_nature removed - green spaces now shown via map styling
)
from clients.transitland_client import (
    TransitlandClient, TransitStop,
    get_nearest_transit,
)
from clients.streetview_client import (
    StreetViewClient,
    fetch_and_cache_panorama,
)
from clients.geoapify_isochrone import (
    get_transit_isochrone,
    get_walking_isochrone,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ISOCHRONE HELPERS
# =============================================================================

def point_in_isochrone(lat: float, lng: float, isochrone_geojson: Dict[str, Any]) -> bool:
    """
    Check if a point (lat, lng) is inside an isochrone polygon.
    
    Uses ray-casting algorithm (no shapely dependency needed).
    
    Args:
        lat: Latitude of the point
        lng: Longitude of the point
        isochrone_geojson: GeoJSON FeatureCollection from Geoapify
    
    Returns:
        True if point is inside the isochrone polygon
    """
    if not isochrone_geojson or not isochrone_geojson.get("features"):
        return False
    
    try:
        for feature in isochrone_geojson.get("features", []):
            geometry = feature.get("geometry")
            if not geometry:
                continue
            
            geom_type = geometry.get("type")
            coords = geometry.get("coordinates", [])
            
            if geom_type == "Polygon":
                # Single polygon - check outer ring
                if _point_in_polygon(lng, lat, coords[0]):
                    return True
            elif geom_type == "MultiPolygon":
                # Multiple polygons - check each
                for polygon in coords:
                    if _point_in_polygon(lng, lat, polygon[0]):
                        return True
        
        return False
    except Exception as e:
        logger.warning(f"[Isochrone] Point-in-polygon check failed: {e}")
        return False


def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """
    Ray-casting algorithm to check if point (x, y) is inside polygon.
    
    Args:
        x: X coordinate (longitude)
        y: Y coordinate (latitude)
        polygon: List of [x, y] coordinate pairs forming the polygon ring
    
    Returns:
        True if point is inside
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside

# =============================================================================
# CONSTANTS
# =============================================================================

WALKING_SPEED_KM_PER_HOUR = 5.0
CYCLING_SPEED_KM_PER_HOUR = 15.0
DRIVING_SPEED_KM_PER_HOUR = 30.0  # Urban average

# Slot assignments
SLOT_PROPERTY = 1  # Property itself (provided by listing)
SLOT_GROCERY = 2
SLOT_METRO = 3
SLOT_BUS = 4
SLOT_LATE_NIGHT = 5
SLOT_STREET_1 = 6
SLOT_STREET_2 = 7
SLOT_HOSPITAL = 8
SLOT_GAS_STATION = 9  # Nearest gas station
SLOT_LOCAL_SPECIAL = 10


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CuratedPlaceV2:
    """Curated place with tour data and opening hours (V3 - Google-powered)."""
    slot: int
    name: str
    category: str
    category_purpose: str  # e.g., "closest_grocery", "nearest_metro"
    lat: float
    lng: float
    distance_m: int
    source: str
    
    # Quality indicators (from Google)
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    
    # Opening hours (NEW - from Google)
    is_open_now: Optional[bool] = None
    is_open_late: bool = False  # Closes after 11 PM - key for lifestyle
    weekday_hours: Optional[List[str]] = None  # ["Monday: 9 AM - 1:30 AM", ...]
    
    # Travel times
    walk_mins: Optional[int] = None
    cycle_mins: Optional[int] = None
    drive_mins: Optional[int] = None
    
    # Street View
    sv_pano_id: Optional[str] = None
    sv_lat: Optional[float] = None
    sv_lng: Optional[float] = None
    sv_heading: Optional[float] = None
    sv_available: bool = False
    
    # Google Place ID (for future lookups)
    google_place_id: Optional[str] = None
    
    # Tour (generated by Gemini)
    tour_sequence: Optional[Dict[str, Any]] = None
    tour_keyframes: Optional[List[Dict]] = None
    
    # Transit routes (for metro/bus stops)
    transit_routes: Optional[List[Dict[str, Any]]] = None
    transit_stop_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "name": self.name,
            "category": self.category,
            "category_purpose": self.category_purpose,
            "lat": self.lat,
            "lng": self.lng,
            "distance_m": self.distance_m,
            "source": self.source,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "is_open_now": self.is_open_now,
            "is_open_late": self.is_open_late,
            "weekday_hours": self.weekday_hours,
            "walk_mins": self.walk_mins,
            "cycle_mins": self.cycle_mins,
            "drive_mins": self.drive_mins,
            "sv_pano_id": self.sv_pano_id,
            "sv_lat": self.sv_lat,
            "sv_lng": self.sv_lng,
            "sv_heading": self.sv_heading,
            "sv_available": self.sv_available,
            "google_place_id": self.google_place_id,
            "tour_sequence": self.tour_sequence,
            "tour_keyframes": self.tour_keyframes,
            "transit_routes": self.transit_routes,
            "transit_stop_id": self.transit_stop_id,
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_walking_time(distance_m: int) -> int:
    """
    Calculate realistic walking time from straight-line distance.
    
    Uses:
    - Walking speed: 4.5 km/h (75 meters per minute) - realistic urban pace
    - Crow-fly factor: 1.3 - accounts for actual walking path being longer
      than straight-line distance (typical for urban street grids)
    
    Formula: walk_mins = (distance_m × crow_fly_factor) / walking_speed_m_per_min
    """
    WALKING_SPEED_M_PER_MIN = 75  # 4.5 km/h = 75 m/min
    CROW_FLY_FACTOR = 1.3  # Actual walking distance ≈ 1.3× straight-line
    
    actual_distance_m = distance_m * CROW_FLY_FACTOR
    walk_mins = actual_distance_m / WALKING_SPEED_M_PER_MIN
    
    # Round to nearest minute, minimum 1 minute
    return max(1, round(walk_mins))


def calculate_travel_times(distance_m: int) -> Dict[str, Optional[int]]:
    """Calculate travel times for different modes."""
    # Use proper walking calculation
    walk_mins = calculate_walking_time(distance_m)
    
    # Cycling at ~15 km/h with 1.2 crow-fly factor
    cycle_distance = distance_m * 1.2
    cycle_mins = int(cycle_distance / 250)  # 250 m/min = 15 km/h
    
    # Driving at ~30 km/h with 1.3 crow-fly factor (urban traffic)
    drive_distance = distance_m * 1.3
    drive_mins = int(drive_distance / 500)  # 500 m/min = 30 km/h
    
    return {
        "walk_mins": walk_mins,
        "cycle_mins": cycle_mins if walk_mins > 20 else None,
        "drive_mins": drive_mins if cycle_mins and cycle_mins > 20 else None,
    }


def calculate_heading(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> float:
    """Calculate bearing/heading from one point to another."""
    lat1 = math.radians(from_lat)
    lat2 = math.radians(to_lat)
    delta_lng = math.radians(to_lng - from_lng)
    
    x = math.sin(delta_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lng)
    
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# =============================================================================
# CURATION SERVICE
# =============================================================================

class CurationService:
    """
    Service for curating places around a listing.
    
    V3: Now uses Google Places API (New) for all POI discovery.
    No more Foursquare dependency.
    
    Usage:
        service = CurationService()
        result = await service.curate_places(lat, lng, property_heading)
        places = result["places"]
        empty_slots = result["empty_slots"]  # Indicates quietness
    """
    
    def __init__(self):
        self.google = GooglePlacesClient()
        self.transitland = TransitlandClient()
        self.streetview = StreetViewClient()
        
        # Track used categories to prevent duplicates
        self.used_categories: set = set()
        
        # Track empty slots for quietness indicator
        self.empty_slots: Dict[str, Dict[str, Any]] = {}
    
    async def curate_places(
        self,
        lat: float,
        lng: float,
        property_heading: float,  # Heading from street to property
    ) -> Dict[str, Any]:
        """
        Curate 9 places around a listing (slots 2-10).
        
        V3: Uses Google Places API (New) for all POI discovery.
        Direct coordinates + opening hours + ratings in one call.
        
        Args:
            lat, lng: Property coordinates
            property_heading: Heading from street view to property
            
        Returns:
            Dict with "places" (list) and "empty_slots" (dict for quietness indicator)
        """
        self.used_categories = set()
        self.empty_slots = {}
        places: List[CuratedPlaceV2] = []
        
        logger.info(f"[Curation] 🎬 Starting V3 curation at ({lat}, {lng}) - Google-powered")
        
        # FIRST: Fetch 15-min walk isochrone (needed to filter transit stations)
        logger.info(f"[Curation] 🗺️ Fetching 15-min walk isochrone for transit filtering...")
        walk_isochrone = await get_walking_isochrone(lat, lng, minutes=15)
        if walk_isochrone and walk_isochrone.get("features"):
            logger.info(f"[Curation] ✅ Got walk isochrone for filtering")
        else:
            logger.warning(f"[Curation] ⚠️ Walk isochrone unavailable, transit will use radius fallback")
            walk_isochrone = None
        
        # Slot 2: Grocery (Google, 10-20km car distance, rating >= 3.5, nearest)
        grocery = await self._curate_grocery(lat, lng)
        if grocery:
            places.append(grocery)
            logger.info(f"[Curation] 🛒 Slot 2: {grocery.name} ({grocery.rating}⭐)")
        else:
            self._mark_empty_slot("grocery", 2, 20000, "No supermarket within 30 min drive")
        
        # Slots 3-4: Transit (Transitland - filtered by walk isochrone)
        transit = await self._curate_transit(lat, lng, walk_isochrone=walk_isochrone)
        places.extend(transit)
        logger.info(f"[Curation] 🚇 Slots 3-4: {len(transit)} transit stops")
        if len(transit) == 0:
            self._mark_empty_slot("metro", 3, 2000, "No metro/train within 2km")
            self._mark_empty_slot("bus", 4, 500, "No bus stops within 500m")
        elif len(transit) == 1:
            found_type = transit[0].category_purpose
            if "metro" in found_type or "train" in found_type:
                self._mark_empty_slot("bus", 4, 500, "No bus stops within 500m")
            else:
                self._mark_empty_slot("metro", 3, 2000, "No metro/train within 2km")
        
        # Slot 5: Late Night (Google, 100m - detects actual late-night venues)
        late_night = await self._curate_late_night(lat, lng)
        if late_night:
            places.append(late_night)
            late_badge = "🌙" if late_night.is_open_late else ""
            logger.info(f"[Curation] 🍺 Slot 5: {late_night.name} {late_badge}")
        else:
            self._mark_empty_slot("late_night", 5, 100, "No bars/clubs within 100m - quiet residential area")
        
        # Slots 6-7: Street Activity (Google, 50m - restaurants/cafes)
        street = await self._curate_street_activity(lat, lng)
        places.extend(street)
        logger.info(f"[Curation] ☕ Slots 6-7: {len(street)} lifestyle places")
        if len(street) == 0:
            self._mark_empty_slot("street_activity", 6, 50, "No cafes/restaurants within 50m - quiet street")
        elif len(street) == 1:
            self._mark_empty_slot("street_activity_2", 7, 50, "Only 1 cafe/restaurant within 50m")
        
        # Slot 8: Hospital (Google, 2500m)
        hospital = await self._curate_hospital(lat, lng)
        if hospital:
            places.append(hospital)
            logger.info(f"[Curation] 🏥 Slot 8: {hospital.name}")
        else:
            self._mark_empty_slot("hospital", 8, 2500, "No hospital within 2.5km")
        
        # Slot 9: Gas Station (Google, 2500m - nearest)
        gas_station = await self._curate_gas_station(lat, lng)
        if gas_station:
            places.append(gas_station)
            logger.info(f"[Curation] ⛽ Slot 9: {gas_station.name}")
        else:
            self._mark_empty_slot("gas_station", 9, 2500, "No gas station within 2.5km")
        
        # Slot 10: Local Special (Google, 2000m - museums, landmarks)
        local_special = await self._curate_local_special(lat, lng)
        if local_special:
            places.append(local_special)
            logger.info(f"[Curation] 🏛️ Slot 10: {local_special.name}")
        else:
            self._mark_empty_slot("local_special", 10, 2000, "No museums/landmarks within 2km")
        
        # NO coordinate verification needed - Google gives accurate coords!
        
        # Enrich with Street View metadata
        places = await self._enrich_with_streetview(places)
        
        # Fetch remaining isochrones in parallel
        logger.info(f"[Curation] 🗺️ Fetching 2-min walk and 30-min transit isochrones...")
        import asyncio
        walk_2min_task = get_walking_isochrone(lat, lng, minutes=1)
        transit_task = get_transit_isochrone(lat, lng, minutes=30)
        
        walk_2min_isochrone, transit_isochrone = await asyncio.gather(
            walk_2min_task, transit_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(walk_2min_isochrone, Exception):
            logger.warning(f"[Curation] ⚠️ 2-min walk isochrone failed: {walk_2min_isochrone}")
            walk_2min_isochrone = None
        elif walk_2min_isochrone:
            logger.info(f"[Curation] ✅ Got 2-min walk isochrone")
            
        if isinstance(transit_isochrone, Exception):
            logger.warning(f"[Curation] ⚠️ Transit isochrone failed: {transit_isochrone}")
            transit_isochrone = None
        elif transit_isochrone:
            logger.info(f"[Curation] ✅ Got 30-min transit isochrone")
        
        logger.info(f"[Curation] ✅ Curated {len(places)} places, {len(self.empty_slots)} empty slots")
        
        return {
            "places": places,
            "empty_slots": self.empty_slots,
            "transit_isochrone": transit_isochrone,   # GeoJSON: 30-min transit reach
            "walk_isochrone": walk_isochrone,         # GeoJSON: 15-min walk reach
            "walk_2min_isochrone": walk_2min_isochrone, # GeoJSON: 2-min walk reach
        }
    
    def _mark_empty_slot(self, category: str, slot: int, radius_m: int, reason: str):
        """Mark a slot as empty (nothing found) - used for quietness indicator."""
        self.empty_slots[category] = {
            "slot": slot,
            "radius_searched_m": radius_m,
            "reason": reason,
            "indicates_quietness": category in ["late_night", "street_activity", "street_activity_2"],
        }
        logger.info(f"[Curation] ⚪ Slot {slot} empty: {reason}")
    
    async def _curate_grocery(self, lat: float, lng: float) -> Optional[CuratedPlaceV2]:
        """Curate nearest quality grocery store using Google Places.
        
        Strategy (car-friendly for rural Spain):
        1. Search 10km radius (~15 min drive)
        2. Filter for quality (rating >= 3.5)
        3. Pick the nearest one from filtered results
        4. If no quality results, expand to 20km (~30 min drive)
        5. Final fallback: any grocery regardless of rating
        """
        try:
            # First pass: 10km (~15 min drive)
            results = await self.google.nearby_search(
                lat=lat, lng=lng,
                types=["supermarket", "grocery_store"],
                radius_m=10000,  # 10km = ~15 min drive
                max_results=20,
                rank_by="DISTANCE",
            )
            
            # Filter for quality: rating >= 3.5
            quality_results = [
                p for p in results 
                if p.rating is not None and p.rating >= 3.5
            ]
            
            logger.info(f"[Curation] Grocery (10km): {len(results)} found, {len(quality_results)} with rating >= 3.5")
            
            # Pick nearest from quality results
            if quality_results:
                    return self._google_to_curated(
                    quality_results[0], lat, lng,
                        slot=SLOT_GROCERY,
                        category_purpose="closest_grocery",
                    )
            
            # Second pass: expand to 20km (~30 min drive)
            if not quality_results:
                logger.info(f"[Curation] Grocery: expanding search to 20km (~30 min drive)")
                results_extended = await self.google.nearby_search(
                    lat=lat, lng=lng,
                    types=["supermarket", "grocery_store"],
                    radius_m=20000,  # 20km = ~30 min drive
                    max_results=20,
                    rank_by="DISTANCE",
                )
                
                quality_extended = [
                    p for p in results_extended 
                    if p.rating is not None and p.rating >= 3.5
                ]
                
                logger.info(f"[Curation] Grocery (20km): {len(results_extended)} found, {len(quality_extended)} with rating >= 3.5")
                
                if quality_extended:
                    return self._google_to_curated(
                        quality_extended[0], lat, lng,
                        slot=SLOT_GROCERY,
                        category_purpose="closest_grocery",
                    )
                
                # Use extended results for final fallback
                results = results_extended if results_extended else results
            
            # Final fallback: take nearest regardless of rating
            if results:
                logger.info(f"[Curation] Grocery fallback: using nearest (rating {results[0].rating})")
                return self._google_to_curated(
                    results[0], lat, lng,
                    slot=SLOT_GROCERY,
                    category_purpose="closest_grocery",
                )
                
        except Exception as e:
            logger.error(f"[Curation] Grocery search failed: {e}")
        
        return None
    
    async def _curate_transit(
        self, 
        lat: float, 
        lng: float,
        walk_isochrone: Optional[Dict[str, Any]] = None,
    ) -> List[CuratedPlaceV2]:
        """Curate transit access showing ALL accessible lines within 15min walk isochrone.
        
        Strategy (Line-Centric with Isochrone Filtering):
        1. Find ALL stops within search radius (1500m to catch edge cases)
        2. Filter to only stations INSIDE the walk isochrone (if available)
        3. For each unique LINE, identify the nearest station that passes filter
        4. Each transit_route includes its own nearest_stop info
        5. This allows UI to show: "Line X - 5 min walk to Station Y"
        
        Args:
            lat, lng: Property coordinates
            walk_isochrone: GeoJSON FeatureCollection of 15-min walk area (for filtering)
        """
        places = []
        
        try:
            from clients.transitland_client import TransitlandClient
            transit_client = TransitlandClient()
            
            # Get all accessible lines with their nearest stations
            # Use larger radius (1500m) since isochrone will filter precisely
            accessible = await transit_client.get_accessible_lines(
                lat=lat, lng=lng,
                walk_radius=1500,  # Slightly larger, isochrone filters precisely
            )
            
            # Filter function: only keep stations inside the walk isochrone
            def filter_by_isochrone(lines: List[Dict]) -> List[Dict]:
                if not walk_isochrone:
                    # No isochrone available, use simple radius fallback (1200m)
                    logger.debug("[Transit] No isochrone, using 1200m radius fallback")
                    return [l for l in lines if (l["nearest_stop"].distance_m or 0) <= 1200]
                
                filtered = []
                for entry in lines:
                    stop = entry["nearest_stop"]
                    if point_in_isochrone(stop.lat, stop.lng, walk_isochrone):
                        filtered.append(entry)
                    else:
                        logger.debug(f"[Transit] Station '{stop.name}' filtered out (outside 15-min walk isochrone)")
                return filtered
            
            # Slot 3: Metro/Rail - filter by isochrone first
            metro_lines_raw = accessible.get("metro", [])
            metro_lines = filter_by_isochrone(metro_lines_raw)
            
            if metro_lines and "closest_metro" not in self.used_categories:
                # Use nearest metro stop as the pin location
                nearest_metro_stop = metro_lines[0]["nearest_stop"]
                
                # Build routes with per-route nearest station info AND fetch schedules
                routes_with_stations = await self._build_routes_with_stations(metro_lines, lat, lng)
                
                curated = self._transit_to_curated_v2(
                    nearest_metro_stop, lat, lng,
                    slot=SLOT_METRO,
                    category_purpose="closest_metro",
                    routes_with_stations=routes_with_stations,
                )
                places.append(curated)
                self.used_categories.add("closest_metro")
                
                route_names = [r["short_name"] or r["long_name"] for r in routes_with_stations[:5]]
                filtered_info = f" (filtered from {len(metro_lines_raw)})" if walk_isochrone else ""
                logger.info(f"[Curation] Metro: {len(routes_with_stations)} lines in isochrone{filtered_info} - {', '.join(route_names)}")
            
            # Slot 4: Bus/Tram - filter by isochrone first
            bus_lines_raw = accessible.get("bus", [])
            bus_lines = filter_by_isochrone(bus_lines_raw)
            
            if bus_lines and "closest_bus" not in self.used_categories:
                # Use nearest bus stop as the pin location
                nearest_bus_stop = bus_lines[0]["nearest_stop"]
                
                # Build routes with per-route nearest station info AND fetch schedules
                routes_with_stations = await self._build_routes_with_stations(bus_lines, lat, lng)
                
                curated = self._transit_to_curated_v2(
                    nearest_bus_stop, lat, lng,
                    slot=SLOT_BUS,
                    category_purpose="closest_bus",
                    routes_with_stations=routes_with_stations,
                )
                places.append(curated)
                self.used_categories.add("closest_bus")
                
                route_names = [r["short_name"] or r["long_name"] for r in routes_with_stations[:5]]
                filtered_info = f" (filtered from {len(bus_lines_raw)})" if walk_isochrone else ""
                logger.info(f"[Curation] Bus: {len(routes_with_stations)} lines in isochrone{filtered_info} - {', '.join(route_names)}")
                
        except Exception as e:
            logger.error(f"[Curation] Transit search failed: {e}")
        
        return places
    
    async def _build_routes_with_stations(
        self, 
        line_entries: List[Dict],
        origin_lat: float,
        origin_lng: float,
    ) -> List[Dict]:
        """Build route list with each route's nearest station info AND real schedule data.
        
        Each route entry includes:
        - Route details (name, color, geometry)
        - nearest_stop_name: Station where this line is closest
        - nearest_stop_distance_m: Distance to that station
        - nearest_stop_walk_mins: Walk time to that station
        - nearest_stop_lat/lng: Coordinates for potential per-route markers
        - Schedule info: first_departure, last_departure, frequency_mins (from Transitland)
        """
        routes_with_stations = []
        
        # Collect unique stops to fetch schedules for
        unique_stops: Dict[str, Dict] = {}  # stop_id -> {feed_onestop_id, route_ids}
        
        for entry in line_entries:
            route = entry["route"]
            stop = entry["nearest_stop"]
            stop_key = f"{stop.feed_onestop_id}:{stop.stop_id}" if stop.feed_onestop_id else stop.stop_id
            
            if stop_key not in unique_stops:
                unique_stops[stop_key] = {
                    "stop_id": stop.stop_id,
                    "feed_onestop_id": stop.feed_onestop_id,
                    "route_ids": [],
                }
            unique_stops[stop_key]["route_ids"].append(route.route_id)
        
        # Fetch schedule data for all unique stops
        schedule_data: Dict[str, Dict] = {}  # route_id -> service info
        
        logger.info(f"[Transit] Fetching schedules for {len(unique_stops)} unique stops")
        
        for stop_key, stop_info in unique_stops.items():
            try:
                logger.info(f"[Transit] Fetching schedule for stop {stop_info['stop_id']} (feed: {stop_info['feed_onestop_id']})")
                service_info = await self.transitland.get_stop_departures(
                    stop_info["stop_id"],
                    feed_onestop_id=stop_info["feed_onestop_id"],
                )
                logger.info(f"[Transit] Got {len(service_info)} routes: {list(service_info.keys())[:5]}")
                # Map service info to route_ids
                for route_id, info in service_info.items():
                    schedule_data[route_id] = {
                        "first_departure": info.first_departure,
                        "last_departure": info.last_departure,
                        "frequency_mins": info.frequency_mins,
                        "is_night_service": info.is_night_service,
                        "is_24h": info.is_24h,
                    }
                logger.info(f"[Transit] Got schedule for {len(service_info)} routes at stop {stop_key}")
            except Exception as e:
                logger.warning(f"[Transit] Failed to get schedule for {stop_key}: {e}")
        
        # Build route entries with schedule data
        for entry in line_entries:
            route = entry["route"]
            stop = entry["nearest_stop"]
            
            travel = calculate_travel_times(stop.distance_m or 0)
            
            # Get schedule data for this route if available
            sched = schedule_data.get(route.route_id, {})
            
            routes_with_stations.append({
                "route_id": route.route_id,
                "short_name": route.route_short_name,
                "long_name": route.route_long_name,
                "type": route.route_type,
                "color": route.route_color,
                "text_color": route.route_text_color,
                "onestop_id": route.onestop_id,
                "geometry": route.geometry,
                "agency_name": route.agency_name,
                "num_stops": route.num_stops,
                # Per-route nearest station info
                "nearest_stop_name": stop.name,
                "nearest_stop_distance_m": stop.distance_m or 0,
                "nearest_stop_walk_mins": travel.get("walk_mins"),
                "nearest_stop_lat": stop.lat,
                "nearest_stop_lng": stop.lng,
                "nearest_stop_id": stop.stop_id,
                # Feed info for departures API
                "feed_onestop_id": stop.feed_onestop_id,
                # Real schedule data (pre-fetched)
                "first_departure": sched.get("first_departure"),
                "last_departure": sched.get("last_departure"),
                "frequency_mins": sched.get("frequency_mins"),
                "is_night_service": sched.get("is_night_service", False),
                "is_24h": sched.get("is_24h", False),
            })
        
        # Sort by distance (nearest first)
        routes_with_stations.sort(key=lambda r: r["nearest_stop_distance_m"])
        
        return routes_with_stations
    
    def _transit_to_curated_v2(
        self,
        stop: TransitStop,
        origin_lat: float,
        origin_lng: float,
        slot: int,
        category_purpose: str,
        routes_with_stations: List[Dict],
    ) -> CuratedPlaceV2:
        """Convert Transit stop to CuratedPlaceV2 with line-centric route data."""
        # Use the nearest route's distance if station distance is None
        station_distance = stop.distance_m
        if station_distance is None and routes_with_stations:
            station_distance = routes_with_stations[0].get("nearest_stop_distance_m", 0)
        station_distance = station_distance or 0
        
        travel = calculate_travel_times(int(station_distance))
        logger.info(f"[Transit] Station {stop.name}: distance={station_distance}m → walk_mins={travel.get('walk_mins')}")
        
        return CuratedPlaceV2(
            slot=slot,
            name=stop.name,
            category=stop.primary_type,
            category_purpose=category_purpose,
            lat=stop.lat,
            lng=stop.lng,
            distance_m=int(station_distance),  # Use calculated station distance
            source="transitland",
            walk_mins=travel.get("walk_mins"),
            cycle_mins=travel.get("cycle_mins"),
            drive_mins=travel.get("drive_mins"),
            transit_routes=routes_with_stations,  # Now includes per-route station info
            transit_stop_id=stop.stop_id,
        )
    
    async def _curate_late_night(self, lat: float, lng: float) -> Optional[CuratedPlaceV2]:
        """Curate best late night venue using Google Places.
        
        Searches for bars/night clubs and uses opening hours to detect
        actual late-night venues (closes after 11 PM).
        """
        try:
            results = await self.google.nearby_search(
                lat=lat, lng=lng,
                types=["bar", "night_club", "pub"],
                radius_m=100,  # Small radius for quietness detection
                max_results=5,
                rank_by="POPULARITY",
            )
            
            # Prefer places that are actually open late
            late_places = [p for p in results if p.is_open_late]
            if late_places:
                # Sort by rating
                late_places = sorted(late_places, key=lambda p: (p.rating or 0), reverse=True)
                return self._google_to_curated(
                    late_places[0], lat, lng,
                        slot=SLOT_LATE_NIGHT,
                        category_purpose="late_night",
                    )
            
            # Fallback: any bar/club
            if results:
                return self._google_to_curated(
                    results[0], lat, lng,
                    slot=SLOT_LATE_NIGHT,
                    category_purpose="late_night",
                )
                
        except Exception as e:
            logger.error(f"[Curation] Late night search failed: {e}")
        
        return None
    
    async def _curate_street_activity(self, lat: float, lng: float) -> List[CuratedPlaceV2]:
        """Curate top 2 street activity places (cafes, restaurants) using Google Places."""
        places = []
        
        try:
            results = await self.google.nearby_search(
                lat=lat, lng=lng,
                types=["restaurant", "cafe", "coffee_shop"],
                radius_m=50,  # Small radius for quietness detection
                max_results=5,
                rank_by="POPULARITY",
            )
            
            # Sort by rating
            results = sorted(results, key=lambda p: (p.rating or 0, p.review_count or 0), reverse=True)
            
            # Take top 2 quality places
            count = 0
            for place in results:
                if count >= 2:
                    break
                if self._is_quality_google_place(place):
                    slot = SLOT_STREET_1 if count == 0 else SLOT_STREET_2
                    places.append(self._google_to_curated(
                        place, lat, lng,
                        slot=slot,
                        category_purpose="on_your_street",
                    ))
                    count += 1
            
            # Fill remaining slots with any results
            for place in results:
                if count >= 2:
                    break
                if place not in [p for p in results[:count]]:  # Not already added
                    slot = SLOT_STREET_1 if count == 0 else SLOT_STREET_2
                    places.append(self._google_to_curated(
                        place, lat, lng,
                        slot=slot,
                        category_purpose="on_your_street",
                    ))
                    count += 1
                    
        except Exception as e:
            logger.error(f"[Curation] Street activity search failed: {e}")
        
        return places
    
    async def _curate_hospital(self, lat: float, lng: float) -> Optional[CuratedPlaceV2]:
        """Curate nearest actual hospital using Google Places text search."""
        try:
            # Use text search with "hospital urgencias" to find actual hospitals, not clinics
            results = await self.google.text_search(
                query="hospital urgencias emergency",
                lat=lat, lng=lng,
                radius_m=5000,
                max_results=5,
            )
            
            # Filter for actual hospitals (not clinics, spas, massage places)
            exclude_keywords = ["massage", "masaje", "spa", "clinic", "clínica", "dental", "veterinar", "fisio", "rehab"]
            for result in results:
                name_lower = result.get("displayName", {}).get("text", "").lower()
                # Skip if name contains excluded keywords
                if any(kw in name_lower for kw in exclude_keywords):
                    continue
                # Prefer results with "hospital" in name
                if "hospital" in name_lower:
                    return self._google_to_curated(
                        result, lat, lng,
                        slot=SLOT_HOSPITAL,
                        category_purpose="closest_hospital",
                    )
            
            # Fallback to first result if no "hospital" in name
            if results:
                return self._google_to_curated(
                    results[0], lat, lng,
                    slot=SLOT_HOSPITAL,
                    category_purpose="closest_hospital",
                )
                
        except Exception as e:
            logger.error(f"[Curation] Hospital search failed: {e}")
        
        return None
    
    async def _curate_gas_station(self, lat: float, lng: float) -> Optional[CuratedPlaceV2]:
        """Curate nearest gas station using Google Places."""
        try:
            results = await self.google.nearby_search(
                lat=lat, lng=lng,
                types=["gas_station"],
                radius_m=2500,
                max_results=5,
                rank_by="DISTANCE",
            )
            
            if results:
                logger.info(f"[Curation] Gas station: found {len(results)}, picking nearest")
                return self._google_to_curated(
                    results[0], lat, lng,
                    slot=SLOT_GAS_STATION,
                    category_purpose="closest_gas_station",
                )
                
        except Exception as e:
            logger.error(f"[Curation] Gas station search failed: {e}")
        
        return None
    
    async def _curate_local_special(self, lat: float, lng: float) -> Optional[CuratedPlaceV2]:
        """Curate unique local attraction (museum, landmark, gallery) using Google Places.
        
        Uses 2000m radius for cultural attractions.
        """
        try:
            results = await self.google.nearby_search(
                lat=lat, lng=lng,
                types=["museum", "art_gallery", "tourist_attraction", "historical_landmark"],
                radius_m=2000,
                max_results=5,
                rank_by="POPULARITY",
            )
            
            # Sort by rating and review count
            results = sorted(results, key=lambda p: (p.rating or 0, p.review_count or 0), reverse=True)
            
            # Prefer quality places
            for place in results:
                if self._is_quality_google_place(place):
                    return self._google_to_curated(
                        place, lat, lng,
                        slot=SLOT_LOCAL_SPECIAL,
                        category_purpose="local_special",
                    )
            
            # Fallback: take nearest cultural attraction even without ratings
            if results:
                return self._google_to_curated(
                    results[0], lat, lng,
                    slot=SLOT_LOCAL_SPECIAL,
                    category_purpose="local_special",
                )
                
        except Exception as e:
            logger.error(f"[Curation] Local special search failed: {e}")
        
        return None
    

    # NOTE: _verify_coordinates_with_google() removed in V3
    # Google Nearby Search provides accurate coordinates directly.
    # No need for separate verification step.

    async def _enrich_with_streetview(
        self,
        places: List[CuratedPlaceV2],
    ) -> List[CuratedPlaceV2]:
        """Enrich places with Street View metadata."""
        if not places:
            return places
        
        logger.info(f"[Curation] 🗺️ Fetching Street View for {len(places)} places")
        
        for place in places:
            try:
                metadata = await self.streetview.get_panorama_metadata(place.lat, place.lng)
                
                if metadata and metadata.status == "OK":
                    place.sv_pano_id = metadata.pano_id
                    place.sv_lat = metadata.lat
                    place.sv_lng = metadata.lng
                    place.sv_heading = calculate_heading(
                        metadata.lat, metadata.lng,
                        place.lat, place.lng
                    )
                    place.sv_available = True
                else:
                    place.sv_available = False
                    
            except Exception as e:
                logger.warning(f"[Curation] Street View failed for {place.name}: {e}")
                place.sv_available = False
        
        return places
    
    def _is_quality_google_place(self, place: NearbyPlace) -> bool:
        """Check if place meets quality criteria."""
        # Rating >= 3.5 AND review_count >= 10
        if place.rating and place.rating >= 3.5:
            if place.review_count and place.review_count >= 10:
                return True
        
        # Fallback: high review count indicates established place
        if place.review_count and place.review_count >= 50:
            return True
        
        return False
    
    def _google_to_curated(
        self,
        place: NearbyPlace,
        origin_lat: float,
        origin_lng: float,
        slot: int,
        category_purpose: str,
    ) -> CuratedPlaceV2:
        """Convert Google NearbyPlace to CuratedPlaceV2."""
        # Calculate distance
        distance_m = int(haversine_distance(origin_lat, origin_lng, place.lat, place.lng))
        travel = calculate_travel_times(distance_m)
        
        # Map Google primary_type to our category
        category = self._google_type_to_category(place.primary_type)
        
        return CuratedPlaceV2(
            slot=slot,
            name=place.name,
            category=category,
            category_purpose=category_purpose,
            lat=place.lat,
            lng=place.lng,
            distance_m=distance_m,
            source="google",
            rating=place.rating,
            rating_count=place.review_count,
            is_open_now=place.is_open_now,
            is_open_late=place.is_open_late,
            weekday_hours=place.weekday_descriptions,
            walk_mins=travel.get("walk_mins"),
            cycle_mins=travel.get("cycle_mins"),
            drive_mins=travel.get("drive_mins"),
            google_place_id=place.id,
        )
    
    def _google_type_to_category(self, primary_type: str) -> str:
        """Map Google place types to our display categories."""
        TYPE_MAP = {
            # Grocery
            "supermarket": "Supermarket",
            "grocery_store": "Grocery",
            # Late Night
            "bar": "Bar",
            "night_club": "Night Club",
            "pub": "Pub",
            # Street Activity
            "restaurant": "Restaurant",
            "cafe": "Cafe",
            "coffee_shop": "Coffee Shop",
            "spanish_restaurant": "Restaurant",
            "italian_restaurant": "Restaurant",
            "mediterranean_restaurant": "Restaurant",
            "american_restaurant": "Restaurant",
            # Medical
            "hospital": "Hospital",
            "medical_clinic": "Medical",
            # Cultural
            "museum": "Museum",
            "art_gallery": "Art Gallery",
            "tourist_attraction": "Landmark",
            "historical_landmark": "Landmark",
        }
        return TYPE_MAP.get(primary_type, primary_type.replace("_", " ").title())


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def curate_places_for_listing(
    lat: float,
    lng: float,
    property_heading: float = 0,
) -> List[Dict[str, Any]]:
    """
    Curate places for a listing and return as dicts.
    
    This is the main entry point for the place curation route.
    """
    service = CurationService()
    places = await service.curate_places(lat, lng, property_heading)
    return [p.to_dict() for p in places]

