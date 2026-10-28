"""
📍 Address Resolution System
============================

Determines the most precise address available and validates coordinates.
Uses ALL listing info to cross-reference and pinpoint best address estimate.

Resolution Levels:
- res_10: Full address with street number (highest precision)
- res_9:  Street name without number
- res_8:  Neighborhood/district level
- res_7:  Zone/area level
- res_6:  City level
- res_5:  Region/province level
- res_4:  Country only
- res_0:  Unknown (no location data)

Usage:
    from scraper.address_resolver import resolve_address
    
    resolved = await resolve_address(scraped_data)
    # Returns: {
    #     "address": "Calle Gran Vía 42, Madrid",
    #     "resolution": "res_10",
    #     "confidence": 0.95,
    #     "lat": 40.4200,
    #     "lng": -3.7025,
    #     "coords_validated": True,
    #     "components": {...}
    # }
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from scraper.geocoder import geocode_address, reverse_geocode

logger = logging.getLogger(__name__)

# =============================================================================
# RESOLUTION LEVELS
# =============================================================================

@dataclass
class ResolutionLevel:
    code: str
    name: str
    precision: int  # Higher = more precise
    description: str

RESOLUTIONS = {
    "res_10": ResolutionLevel("res_10", "address", 10, "Full address with street number"),
    "res_9": ResolutionLevel("res_9", "street", 9, "Street name without number"),
    "res_8": ResolutionLevel("res_8", "neighborhood", 8, "Neighborhood/district"),
    "res_7": ResolutionLevel("res_7", "zone", 7, "Zone/area within city"),
    "res_6": ResolutionLevel("res_6", "city", 6, "City level"),
    "res_5": ResolutionLevel("res_5", "region", 5, "Region/province"),
    "res_4": ResolutionLevel("res_4", "country", 4, "Country only"),
    "res_0": ResolutionLevel("res_0", "unknown", 0, "No location data"),
}

# =============================================================================
# COORDINATE VALIDATION
# =============================================================================

# Spain bounding boxes for validation
SPAIN_BOUNDS = {
    "mainland": {"lat": (36.0, 43.8), "lng": (-9.3, 3.3)},
    "balearics": {"lat": (38.6, 40.1), "lng": (1.1, 4.4)},
    "canaries": {"lat": (27.6, 29.5), "lng": (-18.2, -13.3)},
}

# Known mock/calibration coordinates to reject
MOCK_COORDINATES = [
    (0.0, 0.0),           # Null Island
    (40.4168, -3.7038),   # Madrid center (often default)
    (41.3851, 2.1734),    # Barcelona center (often default)
    (51.5074, -0.1278),   # London (test data)
    (48.8566, 2.3522),    # Paris (test data)
]

# Tolerance for mock coordinate detection (degrees)
MOCK_TOLERANCE = 0.001


def is_in_spain(lat: float, lng: float) -> bool:
    """Check if coordinates are within Spain."""
    for region, bounds in SPAIN_BOUNDS.items():
        if (bounds["lat"][0] <= lat <= bounds["lat"][1] and
            bounds["lng"][0] <= lng <= bounds["lng"][1]):
            return True
    return False


def is_mock_coordinate(lat: float, lng: float) -> bool:
    """Check if coordinates are known mock/calibration values."""
    for mock_lat, mock_lng in MOCK_COORDINATES:
        if (abs(lat - mock_lat) < MOCK_TOLERANCE and 
            abs(lng - mock_lng) < MOCK_TOLERANCE):
            return True
    return False


def is_round_coordinate(lat: float, lng: float) -> bool:
    """Check if coordinates are suspiciously round (likely fake)."""
    # Check if they have very few decimal places
    lat_decimals = len(str(lat).split(".")[-1]) if "." in str(lat) else 0
    lng_decimals = len(str(lng).split(".")[-1]) if "." in str(lng) else 0
    
    # Less than 3 decimal places is suspiciously round (~100m precision)
    return lat_decimals < 3 or lng_decimals < 3


# =============================================================================
# ADDRESS EXTRACTION HELPERS
# =============================================================================

def extract_street_number(address: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract street name and number from address string.
    Returns: (street_name, street_number)
    """
    if not address:
        return None, None
    
    # Common Spanish patterns
    # "Calle Gran Vía 42" or "Gran Vía, 42" or "C/ Gran Vía nº 42"
    patterns = [
        r"^(.+?)\s*,?\s*(?:nº|n\.?|núm\.?|número)?\s*(\d+[\w]*)\s*$",  # Street, 42
        r"^(.+?)\s+(\d+[\w]*)\s*$",  # Street 42
        r"^(?:c/|calle|av\.?|avenida|paseo|plaza)\s*(.+?)\s*,?\s*(\d+[\w]*)\s*$",  # C/ Street 42
    ]
    
    for pattern in patterns:
        match = re.match(pattern, address.strip(), re.IGNORECASE)
        if match:
            street = match.group(1).strip()
            number = match.group(2).strip()
            # Clean up street name
            street = re.sub(r"^(?:c/|calle|av\.?|avenida|paseo|plaza)\s*", "", street, flags=re.IGNORECASE).strip()
            return street, number
    
    # No number found, return whole address as street
    street = re.sub(r"^(?:c/|calle|av\.?|avenida|paseo|plaza)\s*", "", address, flags=re.IGNORECASE).strip()
    return street, None


def normalize_city_name(name: str) -> str:
    """Normalize city name for comparison."""
    if not name:
        return ""
    return re.sub(r"[^a-záéíóúüñ]", "", name.lower())


def cities_match(city1: str, city2: str) -> bool:
    """Check if two city names refer to the same city."""
    if not city1 or not city2:
        return False
    return normalize_city_name(city1) == normalize_city_name(city2)


# =============================================================================
# ADDRESS SOURCES
# =============================================================================

def extract_all_location_hints(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract ALL location hints from the listing data.
    Looks at title, description, breadcrumbs, address fields, etc.
    """
    hints = {
        "addresses": [],
        "streets": [],
        "neighborhoods": [],
        "cities": [],
        "regions": [],
        "postal_codes": [],
    }
    
    # 1. Direct fields
    if data.get("address"):
        hints["addresses"].append(data["address"])
    if data.get("street_name"):
        hints["streets"].append(data["street_name"])
    if data.get("neighborhood"):
        hints["neighborhoods"].append(data["neighborhood"])
    if data.get("city"):
        hints["cities"].append(data["city"])
    if data.get("region"):
        hints["regions"].append(data["region"])
    if data.get("postal_code"):
        hints["postal_codes"].append(str(data["postal_code"]))
    
    # 2. Title often contains location
    title = data.get("title", "")
    if title:
        # Look for "en [Location]" pattern (Spanish)
        en_match = re.search(r"\ben\s+(.+?)(?:\s*[-,]|$)", title, re.IGNORECASE)
        if en_match:
            hints["neighborhoods"].append(en_match.group(1).strip())
        
        # Look for "in [Location]" pattern (English)
        in_match = re.search(r"\bin\s+(.+?)(?:\s*[-,]|$)", title, re.IGNORECASE)
        if in_match:
            hints["neighborhoods"].append(in_match.group(1).strip())
    
    # 3. URL often contains location slugs
    url = data.get("source_url", "")
    if url:
        # /madrid/ or /barcelona/ etc.
        city_match = re.search(r"/([a-z-]+)(?:/|$)", url.lower())
        if city_match:
            city_slug = city_match.group(1).replace("-", " ").title()
            if len(city_slug) > 2:
                hints["cities"].append(city_slug)
    
    # 4. Reference number sometimes contains postal code
    ref = data.get("reference", "")
    if ref:
        postal_match = re.search(r"\b(\d{5})\b", ref)
        if postal_match:
            hints["postal_codes"].append(postal_match.group(1))
    
    # 5. Description may contain address info
    description = data.get("description", "")[:500]  # First 500 chars
    if description:
        # Look for postal codes
        for match in re.finditer(r"\b(\d{5})\b", description):
            hints["postal_codes"].append(match.group(1))
    
    # Deduplicate and clean
    for key in hints:
        hints[key] = list(set(h.strip() for h in hints[key] if h and h.strip()))
    
    return hints


# =============================================================================
# COORDINATE VALIDATION
# =============================================================================

async def validate_coordinates(
    lat: float,
    lng: float,
    expected_city: Optional[str] = None,
    expected_neighborhood: Optional[str] = None,
) -> Tuple[bool, str, float]:
    """
    Validate that coordinates are legitimate and match expected location.
    
    Returns: (is_valid, reason, confidence)
    """
    # 1. Basic sanity checks
    if not lat or not lng:
        return False, "missing_coordinates", 0.0
    
    if is_mock_coordinate(lat, lng):
        return False, "mock_coordinate", 0.0
    
    if is_round_coordinate(lat, lng):
        logger.warning(f"Suspiciously round coordinates: ({lat}, {lng})")
        # Don't reject, but lower confidence
        confidence_penalty = 0.3
    else:
        confidence_penalty = 0.0
    
    # 2. Check if in Spain (or expected country)
    if not is_in_spain(lat, lng):
        # Could be international property, don't reject but flag
        logger.info(f"Coordinates outside Spain: ({lat}, {lng})")
    
    # 3. Reverse geocode to verify
    try:
        reverse = await reverse_geocode(lat, lng)
        if not reverse:
            return True, "could_not_verify", 0.5 - confidence_penalty
        
        # Check if reverse geocoded city matches expected
        reverse_city = reverse.get("city", "")
        
        if expected_city:
            if cities_match(reverse_city, expected_city):
                return True, "city_verified", 0.9 - confidence_penalty
            else:
                logger.warning(f"City mismatch: expected '{expected_city}', got '{reverse_city}'")
                return False, f"city_mismatch:{reverse_city}", 0.2
        
        # Check neighborhood if city not available
        if expected_neighborhood and reverse.get("name"):
            if expected_neighborhood.lower() in reverse.get("name", "").lower():
                return True, "neighborhood_verified", 0.85 - confidence_penalty
        
        # Can't verify but not obviously wrong
        return True, "unverified", 0.6 - confidence_penalty
        
    except Exception as e:
        logger.warning(f"Coordinate validation error: {e}")
        return True, "validation_error", 0.5 - confidence_penalty


# =============================================================================
# MAIN RESOLVER
# =============================================================================

async def resolve_address(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve the most precise address possible from listing data.
    
    Uses ALL available info to determine best address estimate
    and validates coordinates against that address.
    
    Args:
        data: Scraped listing data
        
    Returns:
        Dict with resolved address info:
        - address: Best formatted address string
        - resolution: "res_10" to "res_0"
        - confidence: 0.0 to 1.0
        - lat, lng: Validated coordinates (or None)
        - coords_validated: Whether coordinates were verified
        - coords_source: "scraped", "geocoded", or None
        - components: {street_name, street_number, neighborhood, city, region, postal_code, country}
    """
    logger.info("📍 Resolving address...")
    
    # Extract all location hints from the data
    hints = extract_all_location_hints(data)
    
    # Initialize result
    result = {
        "address": None,
        "resolution": "res_0",
        "confidence": 0.0,
        "lat": None,
        "lng": None,
        "coords_validated": False,
        "coords_source": None,
        "components": {
            "street_name": None,
            "street_number": None,
            "neighborhood": None,
            "city": None,
            "region": None,
            "postal_code": None,
            "country": data.get("country", "Spain"),
        }
    }
    
    # Determine resolution level based on available data
    has_address = bool(hints["addresses"])
    has_street = bool(hints["streets"])
    has_neighborhood = bool(hints["neighborhoods"])
    has_city = bool(hints["cities"])
    has_region = bool(hints["regions"])
    has_postal = bool(hints["postal_codes"])
    
    # Try to extract street number from address
    street_name, street_number = None, None
    if has_address:
        street_name, street_number = extract_street_number(hints["addresses"][0])
    elif has_street:
        street_name = hints["streets"][0]
    
    # Determine resolution
    if street_name and street_number:
        result["resolution"] = "res_10"
        result["confidence"] = 0.9
        result["components"]["street_name"] = street_name
        result["components"]["street_number"] = street_number
    elif street_name:
        result["resolution"] = "res_9"
        result["confidence"] = 0.8
        result["components"]["street_name"] = street_name
    elif has_neighborhood:
        result["resolution"] = "res_8"
        result["confidence"] = 0.7
        result["components"]["neighborhood"] = hints["neighborhoods"][0]
    elif has_city:
        result["resolution"] = "res_6"
        result["confidence"] = 0.5
    elif has_region:
        result["resolution"] = "res_5"
        result["confidence"] = 0.3
    else:
        result["resolution"] = "res_0"
        result["confidence"] = 0.0
        logger.warning("❌ No address data found")
        return result
    
    # Fill in components
    if has_neighborhood:
        result["components"]["neighborhood"] = hints["neighborhoods"][0]
    if has_city:
        result["components"]["city"] = hints["cities"][0]
    if has_region:
        result["components"]["region"] = hints["regions"][0]
    if has_postal:
        result["components"]["postal_code"] = hints["postal_codes"][0]
    
    # Build formatted address string
    address_parts = []
    if result["components"]["street_name"]:
        if result["components"]["street_number"]:
            address_parts.append(f"{result['components']['street_name']} {result['components']['street_number']}")
        else:
            address_parts.append(result["components"]["street_name"])
    if result["components"]["neighborhood"]:
        address_parts.append(result["components"]["neighborhood"])
    if result["components"]["city"]:
        address_parts.append(result["components"]["city"])
    if result["components"]["region"]:
        address_parts.append(result["components"]["region"])
    
    result["address"] = ", ".join(address_parts) if address_parts else None
    
    # Handle coordinates
    scraped_lat = data.get("lat")
    scraped_lng = data.get("lng")
    
    if scraped_lat and scraped_lng:
        # Validate scraped coordinates
        is_valid, reason, coord_confidence = await validate_coordinates(
            scraped_lat,
            scraped_lng,
            expected_city=result["components"]["city"],
            expected_neighborhood=result["components"]["neighborhood"],
        )
        
        if is_valid:
            result["lat"] = scraped_lat
            result["lng"] = scraped_lng
            result["coords_validated"] = "verified" in reason
            result["coords_source"] = "scraped"
            # Adjust confidence based on coordinate validation
            result["confidence"] = min(result["confidence"], result["confidence"] * (0.5 + coord_confidence * 0.5))
            logger.info(f"   ✅ Coordinates validated: {reason}")
        else:
            logger.warning(f"   ❌ Coordinates rejected: {reason}")
            # Try to geocode instead
            scraped_lat, scraped_lng = None, None
    
    # Geocode if no valid coordinates and we have at least city-level data
    if (not result["lat"] or not result["lng"]) and result["resolution"] in ["res_10", "res_9", "res_8", "res_6"]:
        logger.info("   🌍 Geocoding address...")
        geocode_result = await geocode_address(result["address"])
        
        if geocode_result:
            # Validate geocoded coordinates
            is_valid, reason, coord_confidence = await validate_coordinates(
                geocode_result["lat"],
                geocode_result["lng"],
                expected_city=result["components"]["city"],
            )
            
            if is_valid:
                result["lat"] = geocode_result["lat"]
                result["lng"] = geocode_result["lng"]
                result["coords_validated"] = True
                result["coords_source"] = "geocoded"
                
                # Geocoded coordinates are generally neighborhood-center level
                # Downgrade resolution if we used geocoding (not as precise)
                if result["resolution"] == "res_10":
                    result["resolution"] = "res_9"  # Can't trust exact location from geocoding
                    result["confidence"] *= 0.9
                
                logger.info(f"   📍 Geocoded to: ({result['lat']:.4f}, {result['lng']:.4f})")
    
    # Final logging
    logger.info(f"   📍 Resolution: {result['resolution']} ({RESOLUTIONS[result['resolution']].description})")
    logger.info(f"   📍 Address: {result['address']}")
    logger.info(f"   📍 Confidence: {result['confidence']:.2f}")
    
    return result


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

async def enrich_with_address(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich scraped data with resolved address information.
    Adds resolution, confidence, and validated coordinates.
    
    Modifies dict in place and returns it.
    """
    resolved = await resolve_address(data)
    
    # Update data with resolved address
    if resolved["address"]:
        data["address"] = resolved["address"]
    
    data["address_resolution"] = resolved["resolution"]
    data["address_confidence"] = resolved["confidence"]
    
    if resolved["lat"] and resolved["lng"]:
        data["lat"] = resolved["lat"]
        data["lng"] = resolved["lng"]
        data["coords_validated"] = resolved["coords_validated"]
        data["coords_source"] = resolved["coords_source"]
    
    # Update individual components if we found better data
    components = resolved["components"]
    if components["street_name"] and not data.get("street_name"):
        data["street_name"] = components["street_name"]
    if components["street_number"] and not data.get("street_number"):
        data["street_number"] = components["street_number"]
    if components["neighborhood"] and not data.get("neighborhood"):
        data["neighborhood"] = components["neighborhood"]
    if components["city"] and not data.get("city"):
        data["city"] = components["city"]
    if components["region"] and not data.get("region"):
        data["region"] = components["region"]
    if components["postal_code"] and not data.get("postal_code"):
        data["postal_code"] = components["postal_code"]
    
    return data


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import json
    
    async def test():
        # Test with sample data
        test_data = {
            "title": "Piso en venta en Chamberí, Madrid",
            "address": "Calle de Sagasta 15",
            "city": "Madrid",
            "lat": 40.4290,
            "lng": -3.6970,
        }
        
        result = await resolve_address(test_data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())

