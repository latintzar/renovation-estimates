"""
Foursquare Places API Client (V2 - New API)
============================================

Used for: Grocery, Lifestyle, Hospital, Late Night, Local Special
NOT for: Parks, beaches, nature → Use Overture (FREE)

API Version: June 2025 (places-api.foursquare.com)
Auth: Service Key (Bearer token)
Headers: X-Places-Api-Version: 2025-06-17

Pricing:
- Pro tier: $15 per 1,000 calls
- Premium tier: $18.75 per 1,000 calls (for rating/stats fields)
- Free tier: 10,000 calls/month

Category Reference: https://docs.foursquare.com/data-products/docs/categories
- Use "Places Open Source & Pro/Premium Flat File" table
- Categories are BSON ObjectIds (24 char hex strings)

API Docs: https://docs.foursquare.com/developer/reference/place-search
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

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

FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")
# NEW Foursquare Places API (June 2025)
FOURSQUARE_BASE_URL = "https://places-api.foursquare.com/places"

# Category IDs for Foursquare API
# Reference: https://docs.foursquare.com/data-products/docs/categories
# =============================================================================
# FOURSQUARE CATEGORY IDS - Places Open Source & Pro/Premium API
# Reference: https://developer.foursquare.com/docs/categories
# =============================================================================

CATEGORY_IDS = {
    # ---------------------------------------------------------------------
    # GROCERY (Food and Beverage Retail)
    # ---------------------------------------------------------------------
    "grocery": "4bf58dd8d48988d118951735",        # Grocery Store
    "supermarket": "52f2ab2ebcbc57f1066b8b46",    # Supermarket
    "convenience": "4d954b0ea243a5684a65b473",    # Convenience Store
    
    # ---------------------------------------------------------------------
    # LATE NIGHT (Dining and Drinking > Bar)
    # ---------------------------------------------------------------------
    "bar": "4bf58dd8d48988d116941735",            # Bar (parent)
    "nightclub": "4bf58dd8d48988d11f941735",      # Night Club (Arts & Entertainment)
    "pub": "4bf58dd8d48988d11b941735",            # Pub
    "cocktail_bar": "4bf58dd8d48988d11e941735",   # Cocktail Bar
    "wine_bar": "4bf58dd8d48988d123941735",       # Wine Bar
    "beer_bar": "56aa371ce4b08b9a8d57356c",       # Beer Bar
    "lounge": "4bf58dd8d48988d121941735",         # Lounge
    "dive_bar": "4bf58dd8d48988d118941735",       # Dive Bar
    "sports_bar": "4bf58dd8d48988d11d941735",     # Sports Bar
    "whisky_bar": "4bf58dd8d48988d122941735",     # Whisky Bar
    
    # ---------------------------------------------------------------------
    # LIFESTYLE / STREET ACTIVITY (Dining and Drinking)
    # ---------------------------------------------------------------------
    "cafe": "4bf58dd8d48988d16d941735",           # Café
    "coffee_shop": "4bf58dd8d48988d1e0931735",    # Coffee Shop
    "restaurant": "4d4b7105d754a06374d81259",     # Restaurant (parent)
    "bakery": "4bf58dd8d48988d16a941735",         # Bakery
    "breakfast": "4bf58dd8d48988d143941735",      # Breakfast Spot
    "dessert": "4bf58dd8d48988d1d0941735",        # Dessert Shop
    "ice_cream": "4bf58dd8d48988d1c9941735",      # Ice Cream Parlor
    
    # ---------------------------------------------------------------------
    # FITNESS (Sports and Recreation > Gym and Studio)
    # ---------------------------------------------------------------------
    "gym": "4bf58dd8d48988d176941735",            # Gym
    "gym_studio": "4bf58dd8d48988d175941735",     # Gym and Studio (parent)
    "yoga": "4bf58dd8d48988d102941735",           # Yoga Studio
    "pilates": "5744ccdfe4b0c0459246b4b2",        # Pilates Studio
    "boxing": "52f2ab2ebcbc57f1066b8b47",         # Boxing Gym
    "climbing": "503289d391d4c4b30a586d6a",       # Climbing Gym
    
    # ---------------------------------------------------------------------
    # ESSENTIAL SERVICES (Health and Medicine)
    # ---------------------------------------------------------------------
    "hospital": "4bf58dd8d48988d196941735",       # Hospital
    "pharmacy": "4bf58dd8d48988d10f951735",       # Pharmacy
    "medical_center": "4bf58dd8d48988d104941735", # Medical Center
    "urgent_care": "56aa371be4b08b9a8d573526",    # Urgent Care Center
    "emergency_room": "4bf58dd8d48988d194941735", # Emergency Room
    "dentist": "4bf58dd8d48988d178941735",        # Dentist
    "doctor": "4bf58dd8d48988d177941735",         # Doctor's Office
    
    # ---------------------------------------------------------------------
    # LOCAL SPECIAL (Arts and Entertainment / Landmarks)
    # ---------------------------------------------------------------------
    "museum": "4bf58dd8d48988d181941735",         # Museum (parent)
    "art_museum": "4bf58dd8d48988d18f941735",     # Art Museum
    "history_museum": "4bf58dd8d48988d190941735", # History Museum
    "science_museum": "4bf58dd8d48988d191941735", # Science Museum
    "art_gallery": "4bf58dd8d48988d1e2931735",    # Art Gallery
    "theater": "4bf58dd8d48988d137941735",        # Theater
    "concert_hall": "5032792091d4c4b30a586d5c",   # Concert Hall
    "performing_arts": "4bf58dd8d48988d1f2931735",# Performing Arts Venue
    "historic_site": "4deefb944765f83613cdba6e",  # Historic and Protected Site
    "monument": "4bf58dd8d48988d12d941735",       # Monument
    "castle": "50aaa49e4b90af0d42d5de11",         # Castle
    "palace": "52e81612bcbc57f1066b7a14",         # Palace
    "bookstore": "4bf58dd8d48988d114951735",      # Bookstore
    
    # ---------------------------------------------------------------------
    # LANDMARKS (Landmarks and Outdoors) - NOTE: Parks use Overture!
    # ---------------------------------------------------------------------
    "plaza": "4bf58dd8d48988d164941735",          # Plaza
    "scenic_lookout": "4bf58dd8d48988d165941735", # Scenic Lookout
    "bridge": "4bf58dd8d48988d1df941735",         # Bridge
    "lighthouse": "4bf58dd8d48988d15d941735",     # Lighthouse
    "theater": "4bf58dd8d48988d137941735",  # Theater
    "bookstore": "4bf58dd8d48988d114951735",  # Bookstore
    "market": "4bf58dd8d48988d1fa941735",  # Farmers Market
    "food_market": "4bf58dd8d48988d1f7941735",  # Food Court
}

# Composite category groups - New BSON IDs (June 2025 API)
# =============================================================================
# CATEGORY GROUPS - For Slot-Based Curation
# =============================================================================

CATEGORY_GROUPS = {
    # Slot 2: GROCERY - Nearest supermarket/grocery
    "grocery": [
        "4bf58dd8d48988d118951735",  # Grocery Store
        "52f2ab2ebcbc57f1066b8b46",  # Supermarket
    ],
    
    # Slot 5: LATE NIGHT - Bars, clubs, nightlife (100m radius)
    "late_night": [
        "4bf58dd8d48988d116941735",  # Bar (parent)
        "4bf58dd8d48988d11f941735",  # Night Club
        "4bf58dd8d48988d11b941735",  # Pub
        "4bf58dd8d48988d11e941735",  # Cocktail Bar
        "4bf58dd8d48988d123941735",  # Wine Bar
        "56aa371ce4b08b9a8d57356c",  # Beer Bar
        "4bf58dd8d48988d121941735",  # Lounge
    ],
    
    # Slots 6-7: STREET ACTIVITY - Cafes, restaurants (50m radius)
    "lifestyle": [
        "4bf58dd8d48988d16d941735",  # Café
        "4bf58dd8d48988d1e0931735",  # Coffee Shop
        "4d4b7105d754a06374d81259",  # Restaurant (parent)
        "4bf58dd8d48988d16a941735",  # Bakery
        "4bf58dd8d48988d143941735",  # Breakfast Spot
    ],
    
    # Slot 8: HOSPITAL - Medical emergency access
    "hospital": [
        "4bf58dd8d48988d196941735",  # Hospital
        "4bf58dd8d48988d104941735",  # Medical Center
        "4bf58dd8d48988d194941735",  # Emergency Room
    ],
    
    # FITNESS - Gyms and studios (optional slot)
    "fitness": [
        "4bf58dd8d48988d175941735",  # Gym and Studio (parent)
        "4bf58dd8d48988d176941735",  # Gym
        "4bf58dd8d48988d102941735",  # Yoga Studio
    ],
    
    # Slot 10: LOCAL SPECIAL - Cultural landmarks (2km radius)
    # Museums, theaters, historic sites - things that make the area unique
    "local_special": [
        "4bf58dd8d48988d181941735",  # Museum (parent)
        "4bf58dd8d48988d18f941735",  # Art Museum
        "4bf58dd8d48988d190941735",  # History Museum
        "4bf58dd8d48988d1e2931735",  # Art Gallery
        "4bf58dd8d48988d137941735",  # Theater
        "5032792091d4c4b30a586d5c",  # Concert Hall
        "4bf58dd8d48988d1f2931735",  # Performing Arts Venue
        "4deefb944765f83613cdba6e",  # Historic and Protected Site
        "4bf58dd8d48988d12d941735",  # Monument
        "50aaa49e4b90af0d42d5de11",  # Castle
        "52e81612bcbc57f1066b7a14",  # Palace
    ],
    
    # NOTE: GREEN SPACE (Slot 9) uses OVERTURE (FREE!)
    # Parks, beaches, forests, lakes → Use overture_client.search_nature()
}


@dataclass
class FoursquarePlace:
    """Place result from Foursquare API."""
    fsq_id: str
    name: str
    lat: float
    lng: float
    category: str
    category_id: str
    distance_m: int
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    price_level: Optional[int] = None
    address: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    photos: List[str] = None
    hours_popular: Optional[List[Dict]] = None
    
    def __post_init__(self):
        if self.photos is None:
            self.photos = []


class FoursquareClient:
    """
    Client for Foursquare Places API.
    
    Usage:
        client = FoursquareClient()
        places = await client.search_places(lat, lng, categories=['grocery'], radius=1000)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or FOURSQUARE_API_KEY
        if not self.api_key:
            raise ValueError(
                "❌ FOURSQUARE_API_KEY not set! "
                "Add to .env.local: FOURSQUARE_API_KEY=fsq3..."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",  # Service Key with Bearer
            "Accept": "application/json",
            "X-Places-Api-Version": "2025-06-17",  # Required version header
        }
    
    async def search_places(
        self,
        lat: float,
        lng: float,
        categories: List[str],
        radius: int = 1000,
        limit: int = 10,
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None,
        sort: str = "DISTANCE",  # DISTANCE, RATING, RELEVANCE, POPULARITY
    ) -> List[FoursquarePlace]:
        """
        Search for places near a location.
        
        Args:
            lat, lng: Center coordinates
            categories: List of category names (e.g., ['grocery', 'cafe'])
            radius: Search radius in meters (max 100,000)
            limit: Max results (max 50)
            min_rating: Minimum rating filter (applied post-fetch)
            min_reviews: Minimum review count filter (applied post-fetch)
            sort: Sort order
            
        Returns:
            List of FoursquarePlace objects
        """
        # Convert category names to IDs
        category_ids = []
        for cat in categories:
            if cat in CATEGORY_GROUPS:
                category_ids.extend(CATEGORY_GROUPS[cat])
            elif cat in CATEGORY_IDS:
                category_ids.append(CATEGORY_IDS[cat])
            else:
                logger.warning(f"Unknown Foursquare category: {cat}")
        
        if not category_ids:
            logger.error(f"No valid category IDs for: {categories}")
            return []
        
        params = {
            "ll": f"{lat},{lng}",
            "radius": min(radius, 100000),
            "fsq_category_ids": ",".join(category_ids),
            "limit": min(limit, 50),
            "sort": sort,
            # Don't specify fields - use default Pro fields (should include lat/lng per docs)
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{FOURSQUARE_BASE_URL}/search",
                    headers=self.headers,
                    params=params,
                )
                
                if response.status_code != 200:
                    logger.error(f"Foursquare API error {response.status_code}: {response.text}")
                    raise Exception(f"Foursquare API error: {response.status_code}")
                
                data = response.json()
                results = data.get("results", [])
                
                places = []
                for item in results:
                    place = self._parse_place(item)
                    
                    # Apply quality filters
                    if min_rating and (place.rating is None or place.rating < min_rating):
                        continue
                    if min_reviews and (place.rating_count is None or place.rating_count < min_reviews):
                        continue
                    
                    places.append(place)
                
                logger.info(f"Foursquare: Found {len(places)} places for {categories} within {radius}m")
                return places
                
        except Exception as e:
            logger.error(f"Foursquare search failed: {e}")
            raise
    
    async def get_place_details(self, fsq_id: str) -> Optional[FoursquarePlace]:
        """Get detailed information about a specific place."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{FOURSQUARE_BASE_URL}/{fsq_id}",
                    headers=self.headers,
                    # No params needed - default Pro fields returned
                )
                
                if response.status_code != 200:
                    logger.error(f"Foursquare details error: {response.status_code}")
                    return None
                
                data = response.json()
                return self._parse_place(data, distance=0)
                
        except Exception as e:
            logger.error(f"Foursquare get_place_details failed: {e}")
            return None
    
    def _parse_place(self, item: Dict, distance: Optional[int] = None) -> FoursquarePlace:
        """Parse a Foursquare API response item into FoursquarePlace."""
        # NEW API (June 2025) returns latitude/longitude directly
        lat = item.get("latitude", 0)
        lng = item.get("longitude", 0)
        categories = item.get("categories", [{}])
        primary_cat = categories[0] if categories else {}
        location = item.get("location", {})
        stats = item.get("stats", {})
        
        # Extract photos
        photos = []
        for photo in item.get("photos", []):
            prefix = photo.get("prefix", "")
            suffix = photo.get("suffix", "")
            if prefix and suffix:
                photos.append(f"{prefix}original{suffix}")
        
        return FoursquarePlace(
            fsq_id=item.get("fsq_place_id", item.get("fsq_id", "")),  # NEW API uses fsq_place_id
            name=item.get("name", "Unknown"),
            lat=lat,
            lng=lng,
            category=primary_cat.get("name", ""),
            category_id=primary_cat.get("id", ""),
            distance_m=distance if distance is not None else item.get("distance", 0),
            rating=item.get("rating"),
            rating_count=stats.get("total_ratings"),
            price_level=item.get("price"),
            address=location.get("formatted_address"),
            website=item.get("website"),
            phone=item.get("tel"),
            photos=photos,
            hours_popular=item.get("hours_popular"),
        )
    
    def to_dict(self, place: FoursquarePlace) -> Dict[str, Any]:
        """Convert FoursquarePlace to dictionary for storage."""
        return {
            "source": "foursquare",
            "source_id": place.fsq_id,
            "name": place.name,
            "lat": place.lat,
            "lng": place.lng,
            "category": place.category,
            "category_id": place.category_id,
            "distance_m": place.distance_m,
            "rating": place.rating,
            "rating_count": place.rating_count,
            "price_level": place.price_level,
            "address": place.address,
            "website": place.website,
            "phone": place.phone,
            "photos": place.photos,
        }
    
    async def search_by_query(
        self,
        lat: float,
        lng: float,
        query: str,
        radius: int = 1000,
        limit: int = 10,
    ) -> List[FoursquarePlace]:
        """
        Search for places using a text query instead of category IDs.
        
        This is more reliable with the new Foursquare API since old BSON category
        IDs don't always work with the new endpoints.
        
        Args:
            lat, lng: Center coordinates
            query: Text to search for (e.g., 'park', 'museum')
            radius: Search radius in meters
            limit: Max results
            
        Returns:
            List of FoursquarePlace objects
        """
        params = {
            "ll": f"{lat},{lng}",
            "radius": min(radius, 100000),
            "query": query,
            "limit": min(limit, 50),
            "sort": "DISTANCE",
            # Don't specify fields - use default Pro fields
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{FOURSQUARE_BASE_URL}/search",
                    headers=self.headers,
                    params=params,
                )
                
                if response.status_code != 200:
                    logger.error(f"Foursquare query search error {response.status_code}: {response.text[:200]}")
                    return []
                
                data = response.json()
                results = data.get("results", [])
                
                places = []
                for item in results:
                    place = self._parse_place(item)
                    places.append(place)
                
                logger.info(f"[Foursquare] Query '{query}' found {len(places)} places")
                return places
                
        except Exception as e:
            logger.error(f"Foursquare search_by_query failed: {e}")
            return []
    
    async def search_by_query_cultural(
        self,
        lat: float,
        lng: float,
        query: str,
        radius: int = 2000,
        limit: int = 5,
    ) -> List[FoursquarePlace]:
        """
        Search for cultural/special places using a text query.
        
        Filters to only include museums, galleries, historic sites, landmarks.
        """
        params = {
            "ll": f"{lat},{lng}",
            "radius": min(radius, 100000),
            "query": query,
            "limit": min(limit, 50),
            "sort": "DISTANCE",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{FOURSQUARE_BASE_URL}/search",
                    headers=self.headers,
                    params=params,
                )
                
                if response.status_code != 200:
                    logger.error(f"Foursquare cultural search error {response.status_code}: {response.text[:200]}")
                    return []
                
                data = response.json()
                results = data.get("results", [])
                
                places = []
                cultural_categories = ['museum', 'gallery', 'theater', 'historic', 'landmark', 'monument', 'cultural', 'art']
                
                for item in results:
                    place = self._parse_place(item)
                    cat_name = place.category.lower() if place.category else ""
                    # Filter to only cultural places
                    if any(term in cat_name for term in cultural_categories):
                        places.append(place)
                
                logger.info(f"[Foursquare] Cultural query '{query}' found {len(places)} places")
                return places
                
        except Exception as e:
            logger.error(f"Foursquare search_by_query_cultural failed: {e}")
            return []


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def search_grocery(lat: float, lng: float, radius: int = 1250) -> List[FoursquarePlace]:
    """Search for grocery stores near a location."""
    client = FoursquareClient()
    return await client.search_places(
        lat, lng,
        categories=["grocery"],
        radius=radius,
        limit=5,
        sort="DISTANCE",
    )


async def search_late_night(lat: float, lng: float, radius: int = 100) -> List[FoursquarePlace]:
    """Search for late night venues (bars, clubs) near a location."""
    client = FoursquareClient()
    return await client.search_places(
        lat, lng,
        categories=["late_night"],
        radius=radius,
        limit=10,
        min_rating=3.0,
        sort="POPULARITY",
    )


async def search_lifestyle(lat: float, lng: float, radius: int = 50) -> List[FoursquarePlace]:
    """Search for lifestyle places (cafes, restaurants) near a location."""
    client = FoursquareClient()
    return await client.search_places(
        lat, lng,
        categories=["lifestyle"],
        radius=radius,
        limit=10,
        min_rating=3.0,
        min_reviews=10,
        sort="POPULARITY",
    )


async def search_hospital(lat: float, lng: float, radius: int = 2500) -> List[FoursquarePlace]:
    """Search for hospitals near a location."""
    client = FoursquareClient()
    return await client.search_places(
        lat, lng,
        categories=["hospital"],
        radius=radius,
        limit=3,
        sort="DISTANCE",
    )


# NOTE: search_green_space REMOVED - Use Overture (FREE!) instead
# from clients.overture_client import search_parks


async def search_local_special(lat: float, lng: float, radius: int = 2000) -> List[FoursquarePlace]:
    """Search for unique local places (museums, galleries, landmarks) near a location.
    
    Uses multiple queries to find cultural attractions.
    """
    client = FoursquareClient()
    all_results = []
    seen_ids = set()
    
    # Search for multiple types of cultural places
    queries = ["museum", "gallery", "landmark", "historic"]
    
    for query in queries:
        results = await client.search_by_query_cultural(lat, lng, query=query, radius=radius, limit=5)
        for place in results:
            if place.fsq_id not in seen_ids:
                seen_ids.add(place.fsq_id)
                all_results.append(place)
    
    # Sort by distance and return top results
    all_results.sort(key=lambda p: p.distance_m)
    return all_results[:5]

