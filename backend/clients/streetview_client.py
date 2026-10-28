"""
Street View Client - Tile Fetching and Caching
==============================================

Handles:
- Fetching Street View metadata (pano_id, location)
- Fetching tiles at Zoom 3 (8x4 grid = 32 tiles)
- Caching tiles to Supabase Storage
- Creating stitched panorama for Gemini analysis
"""

import os
import io
import asyncio
import logging
import httpx
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

import database

logger = logging.getLogger(__name__)

# Google Street View API config
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
STREETVIEW_METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
STREETVIEW_TILE_URL = "https://tile.googleapis.com/v1/streetview/tiles"

# Tile config: Zoom 3 = 8x4 tiles = 32 tiles per location
TILE_ZOOM = 3
TILES_X = 8
TILES_Y = 4
TILE_SIZE = 512

# Supabase storage bucket
STORAGE_BUCKET = "streetview"


class StreetViewClient:
    """Client for fetching and caching Street View data."""
    
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        if not self.api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set!")
    
    async def get_metadata(self, lat: float, lng: float, radius: int = 50) -> Optional[Dict[str, Any]]:
        """Get Street View metadata for a location."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    STREETVIEW_METADATA_URL,
                    params={
                        "location": f"{lat},{lng}",
                        "radius": radius,
                        "key": self.api_key
                    },
                    timeout=10.0
                )
                
                data = response.json()
                
                if data.get("status") == "OK":
                    return {
                        "pano_id": data.get("pano_id"),
                        "lat": data.get("location", {}).get("lat"),
                        "lng": data.get("location", {}).get("lng"),
                        "date": data.get("date"),
                        "copyright": data.get("copyright"),
                    }
                else:
                    logger.warning(f"Street View not found at {lat},{lng}: {data.get('status')}")
                    return None
                
            except Exception as e:
                logger.error(f"Street View metadata error: {e}")
                return None
    
    async def _get_session_token(self) -> str:
        """Get a session token for tile requests."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://tile.googleapis.com/v1/createSession",
                    params={"key": self.api_key},
                    json={
                        "mapType": "streetview",
                        "language": "en",
                        "region": "US"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json().get("session", "")
                else:
                    logger.error(f"Session token error: {response.status_code}")
                    return ""
                    
            except Exception as e:
                logger.error(f"Session token error: {e}")
                return ""
    
    async def fetch_all_tiles(self, pano_id: str) -> Dict[str, bytes]:
        """Fetch all tiles for a panorama (Zoom 3 = 8x4 = 32 tiles)."""
        tiles = {}
        session = await self._get_session_token()
        
        if not session:
            logger.error("Failed to get session token")
            return tiles
        
        async with httpx.AsyncClient() as client:
            for y in range(TILES_Y):
                for x in range(TILES_X):
                    url = f"{STREETVIEW_TILE_URL}/{TILE_ZOOM}/{x}/{y}"
                    try:
                        response = await client.get(
                            url,
                            params={
                                "session": session,
                                "key": self.api_key,
                                "panoId": pano_id
                            },
                            timeout=15.0
                        )
                        
                        if response.status_code == 200:
                            tiles[f"{x}_{y}"] = response.content
                        else:
                            logger.warning(f"Tile {x},{y} failed: {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"Tile {x},{y} error: {e}")
        
        logger.info(f"Fetched {len(tiles)}/{TILES_X * TILES_Y} tiles for {pano_id}")
        return tiles
    
    async def cache_tiles_to_supabase(
        self,
        listing_id: int,
        slot: int,
        pano_id: str,
        tiles: Dict[str, bytes]
    ) -> Dict[str, str]:
        """Upload tiles to Supabase Storage and return URLs."""
        tile_urls = {}
        
        for tile_key, tile_data in tiles.items():
            path = f"{listing_id}/{slot}/{tile_key}.jpg"
            
            try:
                # Upload to Supabase storage
                result = await database.upload_to_storage(
                    bucket=STORAGE_BUCKET,
                    path=path,
                    data=tile_data,
                    content_type="image/jpeg"
                )
                
                if result:
                    tile_urls[tile_key] = result
                    
            except Exception as e:
                logger.error(f"Failed to cache tile {path}: {e}")
        
        logger.info(f"Cached {len(tile_urls)}/{len(tiles)} tiles to Supabase")
        return tile_urls
    
    async def fetch_and_cache_panorama(
        self,
        listing_id: int,
        slot: int,
        lat: float,
        lng: float,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Full workflow: get metadata, fetch tiles, cache to Supabase.
        Returns tile_urls dict ready for storage in DB.
        """
        # Get metadata first
        metadata = await self.get_metadata(lat, lng)
        if not metadata:
            logger.warning(f"No Street View at {lat},{lng}")
            return None
        
        pano_id = metadata["pano_id"]
        logger.info(f"[SV] Found pano {pano_id} for slot {slot}")
        
        # Check if already cached (unless force_refresh)
        if not force_refresh:
            existing = await database.get_cached_tiles(listing_id, slot)
            if existing and existing.get("pano_id") == pano_id:
                logger.info(f"[SV] Using cached tiles for slot {slot}")
                return existing
        
        # Fetch all tiles
        tiles = await self.fetch_all_tiles(pano_id)
        if not tiles:
            logger.error(f"[SV] Failed to fetch tiles for {pano_id}")
            return None
        
        # Cache to Supabase
        tile_urls = await self.cache_tiles_to_supabase(
            listing_id=listing_id,
            slot=slot,
            pano_id=pano_id,
            tiles=tiles
        )
        
        if not tile_urls:
            logger.error(f"[SV] Failed to cache tiles for {pano_id}")
            return None
        
        # Return complete tile_urls object
        result = {
            "pano_id": pano_id,
            "lat": metadata["lat"],
            "lng": metadata["lng"],
            "date": metadata.get("date"),
            "tile_urls": tile_urls,
            "zoom": TILE_ZOOM,
            "tiles_x": TILES_X,
            "tiles_y": TILES_Y
        }
        
        logger.info(f"[SV] ✅ Cached {len(tile_urls)} tiles for slot {slot}")
        return result
    
    async def stitch_panorama(self, tiles: Dict[str, bytes]) -> Optional[bytes]:
        """Stitch tiles into a single panorama image for Gemini analysis."""
        try:
            # Create full panorama canvas
            pano_width = TILES_X * TILE_SIZE
            pano_height = TILES_Y * TILE_SIZE
            panorama = Image.new("RGB", (pano_width, pano_height))
            
            for tile_key, tile_data in tiles.items():
                x, y = map(int, tile_key.split("_"))
                tile_img = Image.open(io.BytesIO(tile_data))
                panorama.paste(tile_img, (x * TILE_SIZE, y * TILE_SIZE))
            
            # Convert to bytes
            output = io.BytesIO()
            panorama.save(output, format="JPEG", quality=85)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Stitch error: {e}")
            return None
    
    async def get_panorama_for_gemini(
        self,
        listing_id: int,
        slot: int,
        lat: float,
        lng: float
    ) -> Optional[Tuple[bytes, str]]:
        """
        Get panorama image bytes + pano_id for Gemini analysis.
        Returns (image_bytes, pano_id) or None.
        """
        # Fetch and cache first
        result = await self.fetch_and_cache_panorama(listing_id, slot, lat, lng)
        if not result:
            return None
        
        pano_id = result["pano_id"]
        
        # Fetch tiles again (from cache next time) for stitching
        tiles = await self.fetch_all_tiles(pano_id)
        if not tiles:
            return None
        
        # Stitch
        panorama_bytes = await self.stitch_panorama(tiles)
        if not panorama_bytes:
            return None
        
        return (panorama_bytes, pano_id)


# Standalone function for backwards compatibility
async def fetch_and_cache_panorama(
    listing_id: int,
    slot: int,
    lat: float,
    lng: float,
    force_refresh: bool = False
) -> Optional[Dict[str, Any]]:
    """Standalone wrapper for StreetViewClient.fetch_and_cache_panorama."""
    client = StreetViewClient()
    return await client.fetch_and_cache_panorama(
        listing_id=listing_id,
        slot=slot,
        lat=lat,
        lng=lng,
        force_refresh=force_refresh
    )
