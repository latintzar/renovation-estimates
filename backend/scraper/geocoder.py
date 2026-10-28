"""
🌍 Photon Geocoder - Free Global Geocoding
==========================================

Uses photon.komoot.io for geocoding addresses.
Free, fast, OSM-based, no API key required.

Usage:
    from scraper.geocoder import geocode_address, reverse_geocode
    
    # Forward geocode
    result = await geocode_address("Gran Vía 42, Madrid, Spain")
    # Returns: {"lat": 40.42, "lng": -3.70, "address": {...}}
    
    # Reverse geocode  
    result = await reverse_geocode(40.42, -3.70)
    # Returns: {"city": "Madrid", "country": "Spain", ...}
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

PHOTON_API_BASE = "https://photon.komoot.io"
DEFAULT_TIMEOUT = 10.0
DEFAULT_LANGUAGE = "en"  # Force English results

# Shared HTTP client
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "Leo.casa/1.0 (property intelligence)"},
        )
    return _client


# =============================================================================
# FORWARD GEOCODING (Address → Coordinates)
# =============================================================================

async def geocode_address(
    query: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 1,
    lang: str = DEFAULT_LANGUAGE,
) -> Optional[Dict[str, Any]]:
    """
    Geocode an address string to coordinates.
    
    Args:
        query: Address string (e.g., "Gran Vía 42, Madrid, Spain")
        lat, lon: Optional center point for priority (nearby results first)
        limit: Max results (default 1)
        lang: Language for results (default "en")
    
    Returns:
        Dict with lat, lng, and structured address components, or None
    
    Example response:
        {
            "lat": 40.4200,
            "lng": -3.7025,
            "name": "Gran Vía",
            "housenumber": "42",
            "street": "Gran Vía", 
            "city": "Madrid",
            "state": "Community of Madrid",
            "country": "Spain",
            "postcode": "28013",
            "type": "street"
        }
    """
    if not query or len(query.strip()) < 3:
        return None
    
    try:
        client = await get_client()
        
        params = {
            "q": query.strip(),
            "limit": str(limit),
            "lang": lang,
        }
        
        # Add location bias if provided
        if lat is not None and lon is not None:
            params["lat"] = str(lat)
            params["lon"] = str(lon)
        
        response = await client.get(f"{PHOTON_API_BASE}/api/", params=params)
        
        if response.status_code != 200:
            logger.warning(f"Photon API error: {response.status_code}")
            return None
        
        data = response.json()
        features = data.get("features", [])
        
        if not features:
            logger.debug(f"No geocoding results for: {query}")
            return None
        
        # Parse best result
        feature = features[0]
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})
        
        coords = geometry.get("coordinates", [])
        if len(coords) < 2:
            return None
        
        result = {
            "lat": coords[1],  # GeoJSON is [lon, lat]
            "lng": coords[0],
            "name": properties.get("name"),
            "housenumber": properties.get("housenumber"),
            "street": properties.get("street"),
            "city": properties.get("city"),
            "state": properties.get("state"),
            "country": properties.get("country"),
            "postcode": properties.get("postcode"),
            "type": properties.get("osm_type") or properties.get("type"),
            "confidence": _calculate_confidence(properties, query),
        }
        
        logger.info(f"📍 Geocoded '{query[:40]}...' → ({result['lat']:.4f}, {result['lng']:.4f})")
        return result
        
    except httpx.TimeoutException:
        logger.warning(f"Photon timeout for: {query}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None


# =============================================================================
# REVERSE GEOCODING (Coordinates → Address)
# =============================================================================

async def reverse_geocode(
    lat: float,
    lon: float,
    lang: str = DEFAULT_LANGUAGE,
) -> Optional[Dict[str, Any]]:
    """
    Reverse geocode coordinates to address.
    
    Args:
        lat: Latitude
        lon: Longitude  
        lang: Language for results
    
    Returns:
        Dict with address components, or None
    
    Example response:
        {
            "name": "Gran Vía 42",
            "street": "Gran Vía",
            "housenumber": "42",
            "city": "Madrid",
            "state": "Community of Madrid",
            "country": "Spain",
            "postcode": "28013"
        }
    """
    try:
        client = await get_client()
        
        response = await client.get(
            f"{PHOTON_API_BASE}/reverse",
            params={
                "lat": str(lat),
                "lon": str(lon),
                "lang": lang,
            }
        )
        
        if response.status_code != 200:
            logger.warning(f"Photon reverse API error: {response.status_code}")
            return None
        
        data = response.json()
        features = data.get("features", [])
        
        if not features:
            return None
        
        properties = features[0].get("properties", {})
        
        result = {
            "name": properties.get("name"),
            "housenumber": properties.get("housenumber"),
            "street": properties.get("street"),
            "city": properties.get("city"),
            "state": properties.get("state"),
            "country": properties.get("country"),
            "postcode": properties.get("postcode"),
            "type": properties.get("osm_type") or properties.get("type"),
        }
        
        logger.info(f"📍 Reverse geocoded ({lat:.4f}, {lon:.4f}) → {result.get('city', 'Unknown')}")
        return result
        
    except httpx.TimeoutException:
        logger.warning(f"Photon reverse timeout for: ({lat}, {lon})")
        return None
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")
        return None


# =============================================================================
# HELPERS
# =============================================================================

def _calculate_confidence(properties: Dict, query: str) -> float:
    """Calculate confidence score (0-1) for geocoding result."""
    score = 0.5  # Base score
    
    # Boost if we have street-level precision
    if properties.get("street"):
        score += 0.2
    if properties.get("housenumber"):
        score += 0.2
    
    # Boost if city matches query
    city = properties.get("city", "").lower()
    if city and city in query.lower():
        score += 0.1
    
    return min(score, 1.0)


async def geocode_if_missing(
    data: Dict[str, Any],
    address_field: str = "address",
    city_field: str = "city",
    country_field: str = "country",
) -> Dict[str, Any]:
    """
    Geocode a property dict if lat/lng are missing.
    Modifies dict in place and returns it.
    
    Args:
        data: Property dict with address fields
        address_field: Key for street address
        city_field: Key for city
        country_field: Key for country
    
    Returns:
        Same dict with lat/lng added if found
    """
    # Skip if already has coordinates
    if data.get("lat") and data.get("lng"):
        return data
    
    # Build query from available fields (skip null/None values)
    parts = []
    
    address_val = data.get(address_field)
    city_val = data.get(city_field)
    country_val = data.get(country_field)
    
    # Filter out null, None, empty strings, and literal "null"
    if address_val and str(address_val).lower() not in ("null", "none", ""):
        parts.append(str(address_val))
    if city_val and str(city_val).lower() not in ("null", "none", ""):
        parts.append(str(city_val))
    if country_val and str(country_val).lower() not in ("null", "none", ""):
        parts.append(str(country_val))
    
    # Need at least city or address to geocode
    if len(parts) < 1:
        logger.debug("Skipping geocoding - no valid address fields")
        return data
    
    query = ", ".join(parts)
    result = await geocode_address(query)
    
    if result:
        data["lat"] = result["lat"]
        data["lng"] = result["lng"]
        
        # Fill in any missing location fields
        if not data.get("city") and result.get("city"):
            data["city"] = result["city"]
        if not data.get("region") and result.get("state"):
            data["region"] = result["state"]
        if not data.get("postal_code") and result.get("postcode"):
            data["postal_code"] = result["postcode"]
        if not data.get("country") and result.get("country"):
            data["country"] = result["country"]
    
    return data


# =============================================================================
# CLEANUP
# =============================================================================

async def close_client():
    """Close the HTTP client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import sys
    
    async def test():
        if len(sys.argv) < 2:
            print("Usage: python geocoder.py <address>")
            print("       python geocoder.py --reverse <lat> <lon>")
            return
        
        if sys.argv[1] == "--reverse" and len(sys.argv) >= 4:
            lat = float(sys.argv[2])
            lon = float(sys.argv[3])
            result = await reverse_geocode(lat, lon)
        else:
            query = " ".join(sys.argv[1:])
            result = await geocode_address(query)
        
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        await close_client()
    
    asyncio.run(test())

