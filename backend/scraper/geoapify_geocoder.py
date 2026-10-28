"""
🌍 Geoapify Geocoder - Structured Address Geocoding
====================================================

Uses Geoapify's structured geocoding API for maximum precision.
Always returns coordinates if ANY address component is available.

Features:
- Structured address input (more accurate than free-form)
- Resolution tracking (building, street, neighborhood, city)
- Confidence scores per level
- Country bias to prevent wrong-country matches
- 3,000 requests/day FREE tier

Usage:
    from scraper.geoapify_geocoder import geocode_address, geocode_if_missing
    
    # Structured geocode
    result = await geocode_address(
        street_name="Gran Vía",
        street_number="42",
        city="Madrid",
        country="Spain"
    )
    # Returns: {"lat": 40.42, "lng": -3.70, "resolution": "building", "confidence": 0.95}
    
    # Auto-geocode missing coords in scraped data
    data = await geocode_if_missing(scraped_data)
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# TITLE → TOWN EXTRACTION  (deterministic, no LLM)
# =============================================================================

# Spanish listing titles follow patterns like:
#   "Casa en venta en Coín, Málaga"
#   "Piso en Alhaurín el Grande"
#   "Chalet adosado en venta en Fuengirola"
# We look for "en <Town>" at the end (possibly before ", Province").
# Pattern: "en [venta en] <Town>," — captures town before the comma (Province follows)
_TITLE_TOWN_RE = re.compile(
    r"\ben\s+(?:venta\s+en\s+|alquiler\s+en\s+)?([A-ZÁÉÍÓÚÑÜ][A-Za-záéíóúñü\s]+?),",
    re.UNICODE,
)

# Fallback: "en [venta en] <Town>" at end of string (no trailing comma)
_TITLE_TOWN_END_RE = re.compile(
    r"\ben\s+(?:venta\s+en\s+|alquiler\s+en\s+)?([A-ZÁÉÍÓÚÑÜ][A-Za-záéíóúñü\s]+?)\s*$",
    re.UNICODE,
)


def _extract_town_from_title(title: str) -> Optional[str]:
    """
    Extract town/municipality name from a Spanish property listing title.

    Uses regex patterns — no LLM call.  Returns None if no match.

    Examples:
        "Casa en venta en Coín, Málaga" → "Coín"
        "Piso en Alhaurín el Grande"    → "Alhaurín el Grande"
    """
    if not title:
        return None

    for pattern in (_TITLE_TOWN_RE, _TITLE_TOWN_END_RE):
        m = pattern.search(title)
        if m:
            town = m.group(1).strip()
            # Reject if it's too short (likely a preposition fragment) or a known
            # generic word that sneaks in (e.g. "venta", "alquiler", "zona")
            if len(town) < 3:
                continue
            if town.lower() in {"venta", "alquiler", "zona", "centro", "playa"}:
                continue
            logger.debug("Extracted town '%s' from title '%s'", town, title)
            return town

    return None


# =============================================================================
# CONFIGURATION
# =============================================================================

GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")
GEOAPIFY_BASE_URL = "https://api.geoapify.com/v1/geocode/search"
DEFAULT_TIMEOUT = 10.0

# Shared HTTP client
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "PuedoCasa/1.0 (property intelligence)"},
        )
    return _client


# =============================================================================
# RESOLUTION MAPPING
# =============================================================================

# Map Geoapify result_type to our resolution levels
RESOLUTION_MAP = {
    "building": "building",
    "amenity": "building",
    "street": "street",
    "suburb": "neighborhood",
    "district": "neighborhood",
    "neighbourhood": "neighborhood",
    "postcode": "postal_code",
    "city": "city",
    "town": "city",
    "village": "city",
    "county": "region",
    "state": "region",
    "country": "country",
    "unknown": "unknown",
}


def _map_resolution(result_type: str) -> str:
    """Map Geoapify result_type to our resolution levels."""
    return RESOLUTION_MAP.get(result_type, "unknown")


# =============================================================================
# STRUCTURED GEOCODING
# =============================================================================

async def geocode_address(
    street_name: Optional[str] = None,
    street_number: Optional[str] = None,
    neighborhood: Optional[str] = None,
    city: Optional[str] = None,
    postal_code: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = "Spain",
    free_form: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Geocode an address using Geoapify's structured API.
    
    Uses structured parameters when available (more accurate),
    falls back to free-form text if only that is provided.
    
    Args:
        street_name: Street name (e.g., "Gran Vía")
        street_number: House number (e.g., "42")
        neighborhood: Neighborhood/district (e.g., "Malasaña")
        city: City name (e.g., "Madrid")
        postal_code: Postal/ZIP code (e.g., "28013")
        region: State/Province (e.g., "Comunidad de Madrid")
        country: Country name (default: "Spain")
        free_form: Free-form address string (fallback)
    
    Returns:
        Dict with lat, lng, resolution, confidence, or None if not found
    """
    if not GEOAPIFY_API_KEY:
        logger.error("❌ GEOAPIFY_API_KEY not set!")
        return None
    
    # Build query parameters
    params = {
        "apiKey": GEOAPIFY_API_KEY,
        "format": "json",
        "limit": "1",
    }
    
    # Prefer structured address (more accurate)
    has_structured = any([street_name, neighborhood, city, postal_code])
    
    if has_structured:
        # Build structured query
        if street_number:
            params["housenumber"] = street_number
        if street_name:
            params["street"] = street_name
        if postal_code:
            params["postcode"] = postal_code
        if city:
            params["city"] = city
        if region:
            params["state"] = region
        if country:
            params["country"] = country
        
        # If only neighborhood (no street), use text search with type filter
        if neighborhood and not street_name:
            # Combine neighborhood + city for text search
            text_parts = [p for p in [neighborhood, city, country] if p]
            params["text"] = ", ".join(text_parts)
            params["type"] = "locality"
            # Remove structured params that don't apply
            params.pop("housenumber", None)
            params.pop("street", None)
            params.pop("postcode", None)
            params.pop("city", None)
            params.pop("state", None)
            params.pop("country", None)
        
        query_desc = f"structured: {params}"
    elif free_form:
        # Fall back to free-form text
        params["text"] = free_form
        query_desc = f"free-form: {free_form}"
    else:
        logger.debug("No address components provided for geocoding")
        return None
    
    try:
        client = await get_client()
        
        logger.debug(f"📍 Geocoding {query_desc}")
        response = await client.get(GEOAPIFY_BASE_URL, params=params)
        
        if response.status_code != 200:
            logger.warning(f"Geoapify API error: {response.status_code}")
            return None
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            logger.debug(f"No geocoding results for: {query_desc}")
            return None
        
        # Parse best result
        result = results[0]
        
        lat = result.get("lat")
        lon = result.get("lon")
        
        if not lat or not lon:
            return None
        
        # Get resolution and confidence
        result_type = result.get("result_type", "unknown")
        resolution = _map_resolution(result_type)
        
        rank = result.get("rank", {})
        confidence = rank.get("confidence", 0.5)
        confidence_building = rank.get("confidence_building_level", 0.0)
        confidence_street = rank.get("confidence_street_level", 0.0)
        confidence_city = rank.get("confidence_city_level", 0.0)
        
        # Build response
        geocoded = {
            "lat": lat,
            "lng": lon,
            "resolution": resolution,
            "result_type": result_type,
            "confidence": confidence,
            "confidence_building": confidence_building,
            "confidence_street": confidence_street,
            "confidence_city": confidence_city,
            "formatted_address": result.get("formatted"),
            "source": "geoapify",
        }
        
        # Include parsed address components (useful for validation)
        geocoded["parsed"] = {
            "street": result.get("street"),
            "housenumber": result.get("housenumber"),
            "city": result.get("city"),
            "postcode": result.get("postcode"),
            "state": result.get("state"),
            "country": result.get("country"),
            "country_code": result.get("country_code"),
        }
        
        logger.info(
            f"📍 Geocoded → ({lat:.5f}, {lon:.5f}) "
            f"[{resolution}] conf={confidence:.2f}"
        )
        
        return geocoded
        
    except httpx.TimeoutException:
        logger.warning(f"Geoapify timeout for: {query_desc}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None


# =============================================================================
# AUTO-GEOCODE FOR SCRAPED DATA
# =============================================================================

async def geocode_if_missing(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Geocode a scraped property dict if lat/lng are missing.
    
    Uses structured address fields from Gemini extraction.
    Adds resolution metadata for downstream use.
    
    Args:
        data: Scraped property dict with address fields
    
    Returns:
        Same dict with lat/lng added if found, plus:
        - coords_source: "parsed" (from HTML) or "geocoded"
        - coords_resolution: "building", "street", "neighborhood", "city"
        - coords_confidence: 0.0-1.0
    """
    # Already has coordinates from HTML parsing?
    if data.get("lat") and data.get("lng"):
        # Mark as parsed from source
        data["coords_source"] = "parsed"
        data["coords_resolution"] = "building"  # Assume building-level if from HTML
        data["coords_confidence"] = 1.0
        logger.debug(f"✅ Coords already present from HTML parsing")
        return data
    
    # Extract address components
    street_name = data.get("street_name")
    street_number = data.get("street_number")
    neighborhood = data.get("neighborhood")
    city = data.get("city")
    postal_code = data.get("postal_code")
    region = data.get("region")
    country = data.get("country", "Spain")
    
    # Also try the combined address field as fallback
    address = data.get("address")
    
    # Need at least something to geocode
    if not any([street_name, neighborhood, city, postal_code, address]):
        logger.warning("⚠️ No address components to geocode")
        data["coords_source"] = None
        data["coords_resolution"] = None
        data["coords_confidence"] = 0.0
        return data
    
    # Try structured geocoding first
    result = await geocode_address(
        street_name=street_name,
        street_number=street_number,
        neighborhood=neighborhood,
        city=city,
        postal_code=postal_code,
        region=region,
        country=country,
    )
    
    # If structured failed but we have a combined address, try free-form
    if not result and address:
        # Build free-form query
        free_form = address
        if city and city.lower() not in address.lower():
            free_form = f"{address}, {city}"
        if country and country.lower() not in free_form.lower():
            free_form = f"{free_form}, {country}"
        
        result = await geocode_address(free_form=free_form)
    
    # ── Validation: if resolution is city-level, check title for a more specific town ──
    # Spanish listing titles often contain "en [Town]" which is more specific than the
    # city field the parser extracted. If the geocoded city doesn't match the title town,
    # re-geocode using the title-extracted town.
    if result and result.get("resolution") == "city":
        title_town = _extract_town_from_title(data.get("title") or "")
        geocoded_city = (result.get("parsed", {}).get("city") or "").strip().lower()
        if title_town and geocoded_city and title_town.lower() != geocoded_city:
            logger.info(
                "Geocode mismatch: title says '%s' but geocoded to '%s' — re-geocoding with title town",
                title_town, geocoded_city,
            )
            retry = await geocode_address(city=title_town, country=country)
            if retry:
                result = retry

    if result:
        # Update data with geocoded coordinates
        data["lat"] = result["lat"]
        data["lng"] = result["lng"]
        data["coords_source"] = "geocoded"
        data["coords_resolution"] = result["resolution"]
        data["coords_confidence"] = result["confidence"]
        
        # Store full geocoding metadata for debugging
        data["geocoding_result"] = {
            "formatted_address": result.get("formatted_address"),
            "result_type": result.get("result_type"),
            "confidence_building": result.get("confidence_building"),
            "confidence_street": result.get("confidence_street"),
            "confidence_city": result.get("confidence_city"),
        }
        
        logger.info(
            f"Geocoded: {result['resolution']} level, "
            f"conf={result['confidence']:.2f}"
        )
    else:
        # Geocoding failed
        data["coords_source"] = None
        data["coords_resolution"] = None
        data["coords_confidence"] = 0.0
        logger.warning("Geocoding failed - no coordinates")
    
    return data


# =============================================================================
# HELPERS
# =============================================================================

def get_resolution_disclaimer(resolution: Optional[str]) -> Optional[str]:
    """
    Get a user-facing disclaimer based on coordinate resolution.
    
    Args:
        resolution: One of "building", "street", "neighborhood", "city", etc.
    
    Returns:
        Disclaimer string or None if no disclaimer needed
    """
    disclaimers = {
        "building": None,  # No disclaimer needed
        "street": "📍 Approximate location (street level)",
        "neighborhood": "📍 Approximate location (neighborhood center)",
        "postal_code": "📍 Approximate location (postal code area)",
        "city": "📍 Only city-level location available",
        "region": "📍 Only region-level location available",
        "country": "📍 Only country-level location available",
        "unknown": "📍 Location precision unknown",
    }
    return disclaimers.get(resolution)


def is_precise_enough_for_curation(resolution: Optional[str]) -> bool:
    """
    Check if coordinate resolution is precise enough for place curation.
    
    Building and street level are considered precise.
    Neighborhood is acceptable with disclaimer.
    City and below are too imprecise.
    
    Returns:
        True if curation should proceed, False to skip
    """
    precise_resolutions = {"building", "street", "neighborhood"}
    return resolution in precise_resolutions


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
        # Test cases
        tests = [
            # Full address
            {
                "street_name": "Gran Vía",
                "street_number": "42",
                "city": "Madrid",
                "country": "Spain",
            },
            # Street only
            {
                "street_name": "Passeig de Gràcia",
                "city": "Barcelona",
                "country": "Spain",
            },
            # Neighborhood only
            {
                "neighborhood": "Malasaña",
                "city": "Madrid",
                "country": "Spain",
            },
            # City only
            {
                "city": "Valencia",
                "country": "Spain",
            },
        ]
        
        for test in tests:
            print(f"\n{'='*60}")
            print(f"Testing: {test}")
            result = await geocode_address(**test)
            if result:
                print(f"✅ Found: ({result['lat']:.5f}, {result['lng']:.5f})")
                print(f"   Resolution: {result['resolution']}")
                print(f"   Confidence: {result['confidence']:.2f}")
                print(f"   Disclaimer: {get_resolution_disclaimer(result['resolution'])}")
            else:
                print("❌ Not found")
        
        await close_client()
    
    asyncio.run(test())

