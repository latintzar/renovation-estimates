"""
Transitland REST API Client
===========================

Used for: Metro, Train, Bus, Tram stops (from official GTFS data)

Pricing: $200/month fixed for Professional tier (200,000 calls)
API Key: 

API Docs: https://www.transit.land/documentation/rest-api/stops
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx
from dotenv import load_dotenv
from pathlib import Path

# Load environment
backend_root = Path(__file__).parent.parent
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

TRANSITLAND_API_KEY = os.getenv("TRANSITLAND_API_KEY", "")
TRANSITLAND_BASE_URL = "https://transit.land/api/v2/rest"


class RouteType(int, Enum):
    """GTFS route types."""
    TRAM = 0
    SUBWAY = 1  # Metro
    RAIL = 2     # Train
    BUS = 3
    FERRY = 4
    CABLE_TRAM = 5
    AERIAL_LIFT = 6
    FUNICULAR = 7
    TROLLEYBUS = 11
    MONORAIL = 12


# Human-readable names
ROUTE_TYPE_NAMES = {
    0: "Tram",
    1: "Metro",
    2: "Train",
    3: "Bus",
    4: "Ferry",
    5: "Cable Tram",
    6: "Aerial Lift",
    7: "Funicular",
    11: "Trolleybus",
    12: "Monorail",
}


@dataclass
class TransitRoute:
    """Transit route/line information with geometry."""
    route_id: str
    route_short_name: str  # e.g., "L1", "S3", "45"
    route_long_name: str   # e.g., "Hospital de Bellvitge - Fondo"
    route_type: int
    route_color: Optional[str] = None  # Hex color without #
    route_text_color: Optional[str] = None
    onestop_id: Optional[str] = None
    
    # Route geometry (GeoJSON)
    geometry: Optional[Dict[str, Any]] = None  # MultiLineString
    
    # Accessibility
    continuous_pickup: Optional[int] = None
    continuous_drop_off: Optional[int] = None
    
    # Agency info
    agency_name: Optional[str] = None
    
    # Stats
    num_stops: int = 0


@dataclass
class ServiceInfo:
    """Service schedule info for a route at a stop."""
    first_departure: Optional[str] = None  # e.g., "05:30"
    last_departure: Optional[str] = None   # e.g., "23:45"
    frequency_mins: Optional[int] = None   # Average minutes between departures
    departures_per_hour: Optional[float] = None
    is_night_service: bool = False
    is_24h: bool = False


@dataclass
class TransitStop:
    """Transit stop from Transitland API."""
    stop_id: str
    name: str
    lat: float
    lng: float
    route_types: List[int]  # GTFS route types served
    route_type_names: List[str]
    distance_m: Optional[int] = None
    
    # Optional details
    parent_station: Optional[str] = None
    wheelchair_boarding: Optional[int] = None
    
    # Feed info for departures API
    feed_onestop_id: Optional[str] = None
    
    # Route information - populated by get_routes_for_stop
    routes_serving: List[TransitRoute] = None
    
    def __post_init__(self):
        if self.routes_serving is None:
            self.routes_serving = []
    
    @property
    def route_names(self) -> List[str]:
        """Get list of route short names (e.g., ['L1', 'L2', 'S3'])."""
        return [r.route_short_name for r in self.routes_serving if r.route_short_name]
    
    @property
    def is_metro(self) -> bool:
        return RouteType.SUBWAY.value in self.route_types
    
    @property
    def is_train(self) -> bool:
        return RouteType.RAIL.value in self.route_types
    
    @property
    def is_bus(self) -> bool:
        return RouteType.BUS.value in self.route_types
    
    @property
    def is_tram(self) -> bool:
        return RouteType.TRAM.value in self.route_types
    
    @property
    def primary_type(self) -> str:
        """Get the highest-priority transport type."""
        # Priority: Metro > Train > Tram > Bus
        if self.is_metro:
            return "metro"
        if self.is_train:
            return "train"
        if self.is_tram:
            return "tram"
        if self.is_bus:
            return "bus"
        return "transit"


class TransitlandClient:
    """
    Client for Transitland REST API.
    
    Usage:
        client = TransitlandClient()
        stops = await client.search_stops(lat, lng, radius=1000, route_types=[1, 2])
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TRANSITLAND_API_KEY
        if not self.api_key:
            raise ValueError(
                "❌ TRANSITLAND_API_KEY not set! "
                "Add to .env.local: TRANSITLAND_API_KEY=..."
            )
    
    async def search_stops(
        self,
        lat: float,
        lng: float,
        radius: int = 1000,
        route_types: Optional[List[int]] = None,
        limit: int = 20,
    ) -> List[TransitStop]:
        """
        Search for transit stops near a location.
        
        Args:
            lat, lng: Center coordinates
            radius: Search radius in meters (max 10,000)
            route_types: Filter by GTFS route types (0=tram, 1=metro, 2=train, 3=bus)
            limit: Max results
            
        Returns:
            List of TransitStop objects
        """
        params = {
            "lat": lat,
            "lon": lng,
            "radius": min(radius, 10000),
            "limit": limit,
            "apikey": self.api_key,
        }
        
        # Add route type filter if specified
        if route_types:
            params["served_by_route_types"] = ",".join(str(rt) for rt in route_types)
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{TRANSITLAND_BASE_URL}/stops",
                    params=params,
                )
                
                if response.status_code != 200:
                    logger.error(f"Transitland API error {response.status_code}: {response.text}")
                    raise Exception(f"Transitland API error: {response.status_code}")
                
                data = response.json()
                stops_data = data.get("stops", [])
                
                stops = []
                for item in stops_data:
                    if item is None:
                        continue
                    try:
                        stop = self._parse_stop(item, lat, lng)
                        stops.append(stop)
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse stop: {parse_error}")
                
                logger.info(f"Transitland: Found {len(stops)} stops within {radius}m")
                return stops
                
        except Exception as e:
            logger.error(f"Transitland search failed: {e}")
            raise
    
    async def search_metro_and_train(
        self,
        lat: float,
        lng: float,
        radius: int = 2000,
    ) -> Dict[str, Optional[TransitStop]]:
        """
        Search for nearest metro and train stations.
        
        Returns:
            Dict with 'metro' and 'train' keys
        """
        # Search for metro (subway) and train (rail)
        stops = await self.search_stops(
            lat, lng,
            radius=radius,
            route_types=[RouteType.SUBWAY.value, RouteType.RAIL.value],
            limit=20,
        )
        
        result = {"metro": None, "train": None}
        
        for stop in stops:
            if stop.is_metro and result["metro"] is None:
                result["metro"] = stop
            if stop.is_train and result["train"] is None:
                result["train"] = stop
            
            if result["metro"] and result["train"]:
                break
        
        return result
    
    async def search_bus_and_tram(
        self,
        lat: float,
        lng: float,
        radius: int = 500,
    ) -> Dict[str, Optional[TransitStop]]:
        """
        Search for nearest bus and tram stops.
        
        Returns:
            Dict with 'bus' and 'tram' keys
        """
        stops = await self.search_stops(
            lat, lng,
            radius=radius,
            route_types=[RouteType.BUS.value, RouteType.TRAM.value],
            limit=20,
        )
        
        result = {"bus": None, "tram": None}
        
        for stop in stops:
            if stop.is_bus and result["bus"] is None:
                result["bus"] = stop
            if stop.is_tram and result["tram"] is None:
                result["tram"] = stop
            
            if result["bus"] and result["tram"]:
                break
        
        return result
    
    async def get_all_transit(
        self,
        lat: float,
        lng: float,
        metro_radius: int = 1200,  # 15 min walk (~80m/min)
        bus_radius: int = 500,     # 6 min walk
    ) -> Dict[str, Optional[TransitStop]]:
        """
        Get nearest transit of each type using separate filtered queries.
        
        Note: Transitland doesn't return route_types_served in responses,
        so we make separate calls per transit type.
        
        Returns:
            Dict with 'metro', 'train', 'bus', 'tram' keys
        """
        result = {"metro": None, "train": None, "bus": None, "tram": None}
        
        # Search for metro/subway (type 1) and train (type 2)
        metro_train_stops = await self.search_stops(
            lat, lng,
            radius=metro_radius,
            route_types=[RouteType.SUBWAY.value, RouteType.RAIL.value],
            limit=10,
        )
        
        # Assign metro/train based on stop name heuristics or just take first ones
        for stop in metro_train_stops:
            # Force assign route types since API doesn't return them
            stop.route_types = [RouteType.SUBWAY.value]  # Assume subway for metro_train query
            if result["metro"] is None:
                result["metro"] = stop
                break
        
        # Search for bus (type 3) and tram (type 0)
        bus_tram_stops = await self.search_stops(
            lat, lng,
            radius=bus_radius,
            route_types=[RouteType.BUS.value, RouteType.TRAM.value],
            limit=10,
        )
        
        for stop in bus_tram_stops:
            stop.route_types = [RouteType.BUS.value]  # Assume bus for bus_tram query
            if result["bus"] is None:
                result["bus"] = stop
                break
        
        return result
    
    async def get_accessible_lines(
        self,
        lat: float,
        lng: float,
        walk_radius: int = 1200,  # 15 min walk at 80m/min
    ) -> Dict[str, List[Dict]]:
        """
        Get all transit LINES accessible within walk radius.
        
        For each unique line, returns the NEAREST station where you can catch it.
        
        CORRECT LOGIC (V2):
        1. Get routes in the area with their ACTUAL STOPS
        2. For each route, find stops that are ACTUALLY SERVED and within walk radius
        3. Use the nearest such stop for that route
        
        This ensures routes are only attributed to stops they actually serve,
        not stops they merely pass by geometrically.
        
        Returns:
            {
                "metro": [{"route": TransitRoute, "nearest_stop": TransitStop}, ...],
                "bus": [{"route": TransitRoute, "nearest_stop": TransitStop}, ...],
            }
        """
        # STEP 1: Get routes within walking distance with their actual stops
        routes_with_stops = await self._get_routes_with_actual_stops(
            lat, lng,
            radius=walk_radius,
            limit=100,  # Get plenty to cover all lines
        )
        
        logger.info(f"[Transit] Found {len(routes_with_stops)} routes with stop data")
        
        # STEP 2: For each route, find the nearest stop that's within walk radius
        route_to_nearest: Dict[tuple, Dict] = {}  # (short_name, type) -> {route, stop, distance}
        
        for route_data in routes_with_stops:
            route = route_data["route"]
            stops = route_data["stops"]  # Actual stops served by this route
            
            # Find the nearest stop within walk radius
            nearest_stop = None
            nearest_distance = float('inf')
            
            # Get feed info from route_data
            route_feed_id = route_data.get("feed_onestop_id", "")
            
            for stop_info in stops:
                stop_lat = stop_info.get("lat")
                stop_lng = stop_info.get("lng")
                stop_name = stop_info.get("name", "Unknown")
                stop_id = stop_info.get("stop_id", "")
                stop_feed_id = stop_info.get("feed_onestop_id") or route_feed_id
                
                if stop_lat is None or stop_lng is None:
                    continue
                
                # Calculate distance from property to this stop
                distance_m = self._haversine_distance(lat, lng, stop_lat, stop_lng)
                
                # Only consider stops within walk radius
                if distance_m <= walk_radius and distance_m < nearest_distance:
                    nearest_distance = distance_m
                    nearest_stop = TransitStop(
                        stop_id=stop_id,
                        name=stop_name,
                        lat=stop_lat,
                        lng=stop_lng,
                        route_types=[route.route_type],
                        route_type_names=[ROUTE_TYPE_NAMES.get(route.route_type, "Transit")],
                        distance_m=int(distance_m),
                        feed_onestop_id=stop_feed_id,
            )
            
            # If we found a valid stop within range, add to results
            if nearest_stop:
                # Use (short_name, route_type) to deduplicate same lines from different operators
                route_key = (route.route_short_name or route.route_id, route.route_type)
                
                # If we haven't seen this route, or this stop is closer, update
                if route_key not in route_to_nearest or nearest_distance < route_to_nearest[route_key]["distance"]:
                    route_to_nearest[route_key] = {
                        "route": route,
                        "stop": nearest_stop,
                        "distance": nearest_distance,
                    }
        
        # STEP 3: Organize by type
        result = {"metro": [], "bus": []}
        
        for data in route_to_nearest.values():
            route = data["route"]
            entry = {
                "route": route,
                "nearest_stop": data["stop"],
            }
            
            if route.route_type in [RouteType.SUBWAY.value, RouteType.RAIL.value]:
                result["metro"].append(entry)
            else:
                result["bus"].append(entry)
        
        # Sort by distance
        result["metro"].sort(key=lambda x: x["nearest_stop"].distance_m or 9999)
        result["bus"].sort(key=lambda x: x["nearest_stop"].distance_m or 9999)
        
        logger.info(f"[Transit] Accessible lines: {len(result['metro'])} metro/rail, {len(result['bus'])} bus/tram")
        
        return result
    
    async def _get_routes_with_actual_stops(
        self,
        lat: float,
        lng: float,
        radius: int = 1200,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get routes near location WITH their actual stops list.
        
        This uses include_stops=true to get the stops each route ACTUALLY serves,
        not just routes whose geometry passes nearby.
        
        Returns:
            List of {"route": TransitRoute, "stops": [{"stop_id", "name", "lat", "lng"}, ...]}
        """
        try:
            url = f"{TRANSITLAND_BASE_URL}/routes"
            params = {
                "apikey": self.api_key,
                "lat": lat,
                "lon": lng,
                "radius": min(radius, 10000),
                "include_geometry": "true",
                "include_stops": "true",  # CRITICAL: Get actual stops
                "limit": limit,
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                routes_with_stops = []
                seen_route_ids = set()  # Avoid duplicates
                
                for r in data.get("routes", []):
                    route_id = r.get("route_id", "")
                    
                    # Skip duplicates
                    if route_id in seen_route_ids:
                        continue
                    seen_route_ids.add(route_id)
                    
                    # Parse the route
                    agency = r.get("agency", {})
                    agency_name = agency.get("agency_name") if agency else None
                    
                    route = TransitRoute(
                        route_id=route_id,
                        route_short_name=r.get("route_short_name", ""),
                        route_long_name=r.get("route_long_name", ""),
                        route_type=r.get("route_type", 3),
                        route_color=r.get("route_color"),
                        route_text_color=r.get("route_text_color"),
                        onestop_id=r.get("onestop_id"),
                        geometry=r.get("geometry"),
                        continuous_pickup=r.get("continuous_pickup"),
                        continuous_drop_off=r.get("continuous_drop_off"),
                        agency_name=agency_name,
                        num_stops=len(r.get("route_stops", [])),
                    )
                    
                    # Get feed info for departures API
                    feed_version = r.get("feed_version", {})
                    feed_onestop_id = feed_version.get("feed", {}).get("onestop_id", "")
                    
                    # Extract actual stops from route_stops
                    stops = []
                    for rs in r.get("route_stops", []):
                        stop_data = rs.get("stop", {})
                        if not stop_data:
                            continue
                        
                        geometry = stop_data.get("geometry", {})
                        coords = geometry.get("coordinates", [0, 0])
                        
                        stops.append({
                            "stop_id": stop_data.get("stop_id", ""),
                            "name": stop_data.get("stop_name", "Unknown"),
                            "lat": coords[1] if len(coords) >= 2 else None,
                            "lng": coords[0] if len(coords) >= 2 else None,
                            "feed_onestop_id": feed_onestop_id,  # Include feed for departures API
                        })
                    
                    if stops:  # Only include routes with valid stops
                        routes_with_stops.append({
                            "route": route,
                            "stops": stops,
                            "feed_onestop_id": feed_onestop_id,
                        })
                
                logger.info(f"[Transit] Retrieved {len(routes_with_stops)} routes with their actual stops")
                return routes_with_stops
                
        except Exception as e:
            logger.error(f"[Transit] Failed to get routes with stops: {e}")
            return []
    
    async def get_routes_near_location(
        self,
        lat: float,
        lng: float,
        radius: int = 200,
        include_geometry: bool = True,
        route_types: Optional[List[int]] = None,
        limit: int = 10,
    ) -> List[TransitRoute]:
        """
        Get routes near a location with geometry.
        
        Args:
            lat: Latitude
            lng: Longitude
            radius: Search radius in meters (max 10000)
            include_geometry: Include route line geometry
            route_types: Filter by GTFS route types (1=metro, 3=bus, etc)
            limit: Max routes to return
            
        Returns:
            List of TransitRoute objects with geometry
        """
        try:
            url = f"{TRANSITLAND_BASE_URL}/routes"
            params = {
                "apikey": self.api_key,
                "lat": lat,
                "lon": lng,
                "radius": min(radius, 10000),
                "include_geometry": "true" if include_geometry else "false",
                "include_stops": "true",
                "limit": limit,
            }
            
            if route_types:
                params["route_types"] = ",".join(str(rt) for rt in route_types)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                routes = []
                for r in data.get("routes", []):
                    # Get agency name
                    agency = r.get("agency", {})
                    agency_name = agency.get("agency_name") if agency else None
                    
                    # Count stops
                    route_stops = r.get("route_stops", [])
                    
                    route = TransitRoute(
                        route_id=r.get("route_id", ""),
                        route_short_name=r.get("route_short_name", ""),
                        route_long_name=r.get("route_long_name", ""),
                        route_type=r.get("route_type", 3),
                        route_color=r.get("route_color"),
                        route_text_color=r.get("route_text_color"),
                        onestop_id=r.get("onestop_id"),
                        geometry=r.get("geometry"),
                        continuous_pickup=r.get("continuous_pickup"),
                        continuous_drop_off=r.get("continuous_drop_off"),
                        agency_name=agency_name,
                        num_stops=len(route_stops),
                    )
                    
                    # Avoid duplicates by route_id
                    if not any(existing.route_id == route.route_id for existing in routes):
                        routes.append(route)
                
                logger.info(f"Found {len(routes)} routes near ({lat}, {lng})")
                return routes
                
        except Exception as e:
            logger.warning(f"Failed to get routes near ({lat}, {lng}): {e}")
            return []
    
    async def enrich_stop_with_routes(self, stop: TransitStop) -> TransitStop:
        """Fetch ALL routes passing through this stop with geometry.
        
        No limits - we want to show all accessible lines.
        """
        # Use geographic search very close to the stop
        routes = await self.get_routes_near_location(
            lat=stop.lat,
            lng=stop.lng,
            radius=50,  # 50m - only routes that actually serve this stop
            include_geometry=True,
            limit=50,  # Get all routes
        )
        
        stop.routes_serving = routes
        return stop
    
    def _parse_stop(self, item: Dict, origin_lat: float, origin_lng: float) -> TransitStop:
        """Parse a Transitland API stop response."""
        geometry = item.get("geometry") or {}
        coords = geometry.get("coordinates") or [0, 0]
        
        # Get route types served (might be None or missing)
        route_types = item.get("route_types_served") or []
        route_type_names = [ROUTE_TYPE_NAMES.get(rt, f"Type {rt}") for rt in route_types]
        
        # Calculate distance
        stop_lat = coords[1]
        stop_lng = coords[0]
        distance_m = self._haversine_distance(origin_lat, origin_lng, stop_lat, stop_lng)
        
        return TransitStop(
            stop_id=item.get("stop_id", ""),
            name=item.get("stop_name", "Unknown"),
            lat=stop_lat,
            lng=stop_lng,
            route_types=route_types,
            route_type_names=route_type_names,
            distance_m=int(distance_m),
            parent_station=(item.get("parent") or {}).get("stop_name"),
            wheelchair_boarding=item.get("wheelchair_boarding"),
        )
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in meters."""
        import math
        
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def to_dict(self, stop: TransitStop) -> Dict[str, Any]:
        """Convert TransitStop to dictionary for storage."""
        return {
            "source": "transitland",
            "source_id": stop.stop_id,
            "name": stop.name,
            "lat": stop.lat,
            "lng": stop.lng,
            "category": stop.primary_type,
            "route_types": stop.route_types,
            "route_type_names": stop.route_type_names,
            "distance_m": stop.distance_m,
            "wheelchair_boarding": stop.wheelchair_boarding,
        }
    
    async def get_stop_departures(
        self,
        stop_id: str,
        feed_onestop_id: Optional[str] = None,
    ) -> Dict[str, ServiceInfo]:
        """
        Get departure schedule info for a stop from Transitland.
        
        Fetches departures for a full day and calculates:
        - First/last departure times
        - Average frequency
        - Whether it's night/24h service
        
        Args:
            stop_id: GTFS stop_id
            feed_onestop_id: Optional feed identifier for disambiguation
            
        Returns:
            Dict mapping route_id to ServiceInfo
        """
        try:
            # Build stop key - try different formats
            if feed_onestop_id:
                stop_key = f"{feed_onestop_id}:{stop_id}"
            else:
                stop_key = stop_id
            
            url = f"{TRANSITLAND_BASE_URL}/stops/{stop_key}/departures"
            params = {
                "apikey": self.api_key,
                "relative_date": "TODAY",
                "start_time": "00:00:00",
                "end_time": "23:59:59",
                "limit": 500,  # Get lots of departures
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 404:
                    logger.warning(f"[Transit] Stop {stop_key} not found for departures")
                    return {}
                
                response.raise_for_status()
                data = response.json()
                
                # Group departures by route
                route_departures: Dict[str, List[str]] = {}
                
                stops_data = data.get("stops", [])
                for stop in stops_data:
                    for departure in stop.get("departures", []):
                        trip = departure.get("trip", {})
                        route = trip.get("route", {})
                        route_id = route.get("route_id", "unknown")
                        
                        dep_time = departure.get("departure_time")
                        if dep_time:
                            if route_id not in route_departures:
                                route_departures[route_id] = []
                            route_departures[route_id].append(dep_time)
                
                # Calculate service info for each route
                service_info: Dict[str, ServiceInfo] = {}
                
                for route_id, times in route_departures.items():
                    if not times:
                        continue
                    
                    # Sort times
                    sorted_times = sorted(times)
                    first = sorted_times[0][:5]  # "HH:MM"
                    last = sorted_times[-1][:5]
                    
                    # Calculate frequency (average gap between departures)
                    frequency_mins = None
                    if len(sorted_times) >= 2:
                        gaps = []
                        for i in range(1, len(sorted_times)):
                            t1 = self._time_to_minutes(sorted_times[i-1])
                            t2 = self._time_to_minutes(sorted_times[i])
                            if t2 > t1:  # Avoid negative gaps from day wraparound
                                gaps.append(t2 - t1)
                        if gaps:
                            frequency_mins = int(sum(gaps) / len(gaps))
                    
                    # Determine service type
                    first_hour = int(first.split(":")[0])
                    last_hour = int(last.split(":")[0])
                    
                    is_night = first_hour >= 22 or first_hour < 6
                    is_24h = (last_hour >= 23 or last_hour < 1) and first_hour < 6
                    
                    service_info[route_id] = ServiceInfo(
                        first_departure=first,
                        last_departure=last,
                        frequency_mins=frequency_mins,
                        departures_per_hour=60 / frequency_mins if frequency_mins and frequency_mins > 0 else None,
                        is_night_service=is_night,
                        is_24h=is_24h,
                    )
                
                logger.info(f"[Transit] Got service info for {len(service_info)} routes at stop {stop_key}")
                return service_info
                
        except Exception as e:
            logger.warning(f"[Transit] Failed to get departures for {stop_id}: {e}")
            return {}
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM:SS to minutes since midnight."""
        parts = time_str.split(":")
        hours = int(parts[0])
        mins = int(parts[1]) if len(parts) > 1 else 0
        return hours * 60 + mins


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_nearest_transit(lat: float, lng: float) -> Dict[str, Optional[TransitStop]]:
    """Get nearest transit stops of each type."""
    client = TransitlandClient()
    return await client.get_all_transit(lat, lng)

