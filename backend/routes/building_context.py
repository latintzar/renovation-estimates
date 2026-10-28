"""
Building Context Route
======================

Queries OSM Overpass API for building heights in a radius.
Falls back to Overture/Athena if OSM has no data.

Used to inform Street View tour generation (e.g., skip look-up if low buildings)
"""

import os
import time
import logging
import httpx
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv

pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

router = APIRouter()

# OSM Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class BuildingContextResponse(BaseModel):
    """Response model for building context."""
    lat: float
    lng: float
    avg_building_height: Optional[float] = None
    max_building_height: Optional[float] = None
    building_count: int = 0
    has_tall_buildings: bool = False  # True if any building > 12m
    suggested_look_up: bool = True  # False if avg height < 6m
    source: str = "osm"  # osm, overture, or default


def parse_height(height_str: str) -> Optional[float]:
    """Parse OSM height string to float (handles '10m', '10 m', '10', etc.)"""
    if not height_str:
        return None
    try:
        # Remove units and whitespace
        cleaned = height_str.lower().replace('m', '').replace('ft', '').strip()
        # Handle feet conversion
        if 'ft' in height_str.lower() or "'" in height_str:
            return float(cleaned) * 0.3048
        return float(cleaned)
    except (ValueError, TypeError):
        return None


async def query_osm_buildings(lat: float, lng: float, radius_m: int = 100) -> List[dict]:
    """Query OSM Overpass API for buildings with height data."""
    # Overpass QL query for buildings with height in bbox
    # bbox format: south,west,north,east
    delta = radius_m / 111000  # Approximate degrees
    bbox = f"{lat - delta},{lng - delta},{lat + delta},{lng + delta}"
    
    query = f"""
    [out:json][timeout:15];
    (
      way["building"]["height"]({bbox});
      way["building"]["building:levels"]({bbox});
      relation["building"]["height"]({bbox});
    );
    out tags;
    """
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            OVERPASS_URL,
            data={"data": query}
        )
        response.raise_for_status()
        data = response.json()
    
    buildings = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        height = parse_height(tags.get("height"))
        
        # Estimate height from levels if no height tag
        if height is None and tags.get("building:levels"):
            try:
                levels = int(tags["building:levels"])
                height = levels * 3.0  # ~3m per floor estimate
            except (ValueError, TypeError):
                pass
        
        if height is not None:
            buildings.append({
                "id": element.get("id"),
                "height": height,
                "levels": tags.get("building:levels"),
                "name": tags.get("name")
            })
    
    return buildings


@router.get("/building-context", response_model=BuildingContextResponse)
async def get_building_context(lat: float, lng: float):
    """
    Get building context for a location using OSM data.
    
    Used to parameterize Street View tours:
    - If buildings are short (< 6m avg), skip look-up beats
    - If buildings are tall (> 12m), emphasize look-up beats
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        BuildingContextResponse with height stats and recommendations
    """
    logger.info(f"🏢 Building context request: ({lat}, {lng})")
    
    try:
        # Query OSM for buildings with height data
        buildings = await query_osm_buildings(lat, lng, radius_m=100)
        
        if not buildings:
            logger.info("   No OSM buildings with height data found")
            return BuildingContextResponse(
                lat=lat,
                lng=lng,
                avg_building_height=None,
                max_building_height=None,
                building_count=0,
                has_tall_buildings=False,
                suggested_look_up=True,  # Default to true when unknown
                source="default"
            )
        
        heights = [b["height"] for b in buildings if b["height"] is not None]
        
        if not heights:
            return BuildingContextResponse(
                lat=lat,
                lng=lng,
                avg_building_height=None,
                max_building_height=None,
                building_count=len(buildings),
                has_tall_buildings=False,
                suggested_look_up=True,
                source="osm"
            )
        
        avg_height = sum(heights) / len(heights)
        max_height = max(heights)
        
        # Determine recommendations
        has_tall = max_height > 12
        # Look up if:
        # - Unknown data (default)
        # - Average height > 6m (multi-story area)
        # - Any building > 15m (definitely look up at tall buildings)
        suggest_look_up = avg_height > 6 or max_height > 15
        
        logger.info(f"   OSM: Found {len(heights)} buildings, avg height: {avg_height:.1f}m, max: {max_height:.1f}m")
        
        return BuildingContextResponse(
            lat=lat,
            lng=lng,
            avg_building_height=round(avg_height, 1),
            max_building_height=round(max_height, 1),
            building_count=len(buildings),
            has_tall_buildings=has_tall,
            suggested_look_up=suggest_look_up,
            source="osm"
        )
        
    except httpx.TimeoutException:
        logger.warning("   OSM Overpass timeout, using defaults")
        return BuildingContextResponse(
            lat=lat,
            lng=lng,
            source="default"
        )
    except Exception as e:
        logger.error(f"   Error querying buildings: {e}")
        return BuildingContextResponse(
            lat=lat,
            lng=lng,
            source="default"
        )

