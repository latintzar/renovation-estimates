"""
🗺️ Geoapify Isochrone Client
============================

Fetches transit isochrones (reachability areas) from Geoapify API.

Features:
- Transit mode for public transport accessibility
- 30-minute isochrone by default (configurable)
- GeoJSON polygon output for map display
- Caching via isoline ID (24h validity)

Usage:
    from clients.geoapify_isochrone import get_transit_isochrone
    
    result = await get_transit_isochrone(
        lat=40.4168,
        lng=-3.7038,
        minutes=30
    )
    # Returns GeoJSON FeatureCollection with isochrone polygon
"""

import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")
GEOAPIFY_ISOLINE_URL = "https://api.geoapify.com/v1/isoline"
DEFAULT_TIMEOUT = 30.0  # Isochrones can take a while

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
# TRANSIT ISOCHRONE
# =============================================================================

async def get_transit_isochrone(
    lat: float,
    lng: float,
    minutes: int = 30,
    mode: str = "transit",
) -> Optional[Dict[str, Any]]:
    """
    Get a transit isochrone (reachable area) from Geoapify.
    
    Args:
        lat: Latitude of origin
        lng: Longitude of origin
        minutes: Travel time in minutes (default: 30)
        mode: Travel mode - "transit" for public transport, 
              "walk" for walking, "drive" for driving
    
    Returns:
        GeoJSON FeatureCollection with isochrone polygon, or None on error
        
    Response includes:
        - type: "FeatureCollection"
        - features: Array with one Feature containing:
            - type: "Feature"
            - geometry: Polygon or MultiPolygon
            - properties: lat, lon, type, mode, range, id
    """
    if not GEOAPIFY_API_KEY:
        logger.error("❌ GEOAPIFY_API_KEY not set!")
        return None
    
    # Convert minutes to seconds
    range_seconds = minutes * 60
    
    params = {
        "lat": lat,
        "lon": lng,
        "type": "time",
        "mode": mode,  # "transit" for public transport
        "range": range_seconds,
        "apiKey": GEOAPIFY_API_KEY,
    }
    
    try:
        client = await get_client()
        
        logger.info(f"🗺️ Fetching {minutes}-min {mode} isochrone from ({lat:.5f}, {lng:.5f})")
        response = await client.get(GEOAPIFY_ISOLINE_URL, params=params)
        
        # Handle async response (202)
        if response.status_code == 202:
            data = response.json()
            isoline_id = data.get("properties", {}).get("id")
            
            if isoline_id:
                logger.info(f"⏳ Isochrone calculating... ID: {isoline_id}")
                # Poll for result
                return await _poll_isochrone(isoline_id, max_attempts=10)
            else:
                logger.warning("⚠️ Got 202 but no isoline ID")
                return None
        
        if response.status_code != 200:
            logger.warning(f"Geoapify Isoline API error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        
        # Validate response
        features = data.get("features", [])
        if not features:
            logger.warning("No isochrone features returned")
            return None
        
        logger.info(f"✅ Got {mode} isochrone with {len(features)} feature(s)")
        
        return data
        
    except httpx.TimeoutException:
        logger.warning(f"Geoapify isochrone timeout for ({lat}, {lng})")
        return None
    except Exception as e:
        logger.error(f"Isochrone error: {e}")
        return None


async def _poll_isochrone(
    isoline_id: str,
    max_attempts: int = 10,
    delay_seconds: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """
    Poll for an async isochrone result.
    
    Args:
        isoline_id: The isoline ID from the 202 response
        max_attempts: Maximum polling attempts
        delay_seconds: Delay between attempts
    
    Returns:
        GeoJSON FeatureCollection or None
    """
    import asyncio
    
    if not GEOAPIFY_API_KEY:
        return None
    
    params = {
        "id": isoline_id,
        "apiKey": GEOAPIFY_API_KEY,
    }
    
    client = await get_client()
    
    for attempt in range(max_attempts):
        await asyncio.sleep(delay_seconds)
        
        try:
            response = await client.get(GEOAPIFY_ISOLINE_URL, params=params)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                
                if features:
                    logger.info(f"✅ Isochrone ready after {attempt + 1} poll(s)")
                    return data
            elif response.status_code == 202:
                # Still calculating
                logger.debug(f"⏳ Still calculating... (attempt {attempt + 1})")
                continue
            else:
                logger.warning(f"Polling error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Polling error: {e}")
            continue
    
    logger.warning(f"Isochrone polling timed out after {max_attempts} attempts")
    return None


async def get_walking_isochrone(
    lat: float,
    lng: float,
    minutes: int = 15,
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for walking isochrone.
    
    Args:
        lat: Latitude
        lng: Longitude
        minutes: Walking time (default: 15)
    
    Returns:
        GeoJSON FeatureCollection
    """
    return await get_transit_isochrone(lat, lng, minutes, mode="walk")


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
    import json
    
    async def test():
        # Test: Madrid city center
        lat, lng = 40.4168, -3.7038
        
        print(f"\n{'='*60}")
        print(f"Testing transit isochrone for ({lat}, {lng})")
        print(f"{'='*60}\n")
        
        result = await get_transit_isochrone(lat, lng, minutes=30)
        
        if result:
            print(f"✅ Got isochrone!")
            print(f"   Features: {len(result.get('features', []))}")
            
            # Print first feature geometry type
            if result.get("features"):
                geom = result["features"][0].get("geometry", {})
                print(f"   Geometry type: {geom.get('type')}")
                
                # Count coordinates (rough area indicator)
                coords = geom.get("coordinates", [])
                if coords:
                    if geom.get("type") == "Polygon":
                        print(f"   Vertices: {len(coords[0])}")
                    elif geom.get("type") == "MultiPolygon":
                        total = sum(len(poly[0]) for poly in coords)
                        print(f"   Total vertices: {total}")
            
            # Save to file for inspection
            with open("/tmp/isochrone_test.geojson", "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n   Saved to /tmp/isochrone_test.geojson")
        else:
            print("❌ Failed to get isochrone")
        
        await close_client()
    
    asyncio.run(test())

