"""
Image Cache Module
==================

V0.4.8 - Comparable Image Storage

Downloads comparable images from external URLs and stores them in Supabase Storage.
All pipeline steps that need comparable images use these cached URLs.

ARCHITECTURE:
- Images downloaded once when comparables are loaded
- Stored in Supabase Storage: comparable-images/{comp_id}/{hash}.{ext}
- Cached URLs stored in database: comparable_image_cache table
- Pipeline steps use cached URLs (same datacenter, no rate limits)

USAGE:
    cache = get_image_cache()
    
    # Cache images for a comparable
    cached_urls = await cache.cache_comparable_images(comp_id=95, photo_urls=[...])
    
    # Get cached URLs
    cached_urls = await cache.get_cached_urls(comp_id=95)
"""

import asyncio
import hashlib
import logging
import os
from typing import Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

CACHE_BUCKET = "comparable-images"
MIN_IMAGES_FOR_PIR = 10
DOWNLOAD_TIMEOUT = 60
UPLOAD_TIMEOUT = 60
MAX_RETRIES = 3
BATCH_SIZE = 5
BATCH_DELAY = 0.5


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ImageCacheError(Exception):
    """Image caching failed."""
    pass


class InsufficientImagesError(ImageCacheError):
    """Not enough images were cached."""
    def __init__(self, comp_id: int, cached: int, required: int):
        super().__init__(f"Comparable {comp_id}: {cached}/{required} images cached")


# =============================================================================
# IMAGE CACHE
# =============================================================================

class ImageCache:
    """Manages caching of comparable images in Supabase Storage."""
    
    def __init__(self):
        self._supabase_url: Optional[str] = None
        self._supabase_key: Optional[str] = None
        self._db_client = None
        self._db_base_url: Optional[str] = None
    
    def _get_credentials(self) -> Tuple[str, str]:
        """Get Supabase credentials.
        
        IMPORTANT:
        - Use SERVICE ROLE for Storage writes.
        - Avoid legacy env names to prevent silent 400s.
        """
        if self._supabase_url and self._supabase_key:
            return self._supabase_url, self._supabase_key
        
        url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")  # legacy
            or os.getenv("SUPABASE_ANON_KEY")
        )
        
        if not url or not key:
            raise ImageCacheError("Supabase credentials not configured")
        
        self._supabase_url = url
        self._supabase_key = key
        return url, key
    
    async def _get_db(self):
        """Get database client."""
        if self._db_client is None:
            from database import get_client, _get_base_url
            self._db_client = await get_client()
            self._db_base_url = _get_base_url()
        return self._db_client, self._db_base_url
    
    async def cache_comparable_images(
        self,
        comp_id: int,
        photo_urls: List[str],
        force_refresh: bool = False
    ) -> List[str]:
        """
        Cache images for a comparable in Supabase Storage.
        
        Returns list of Supabase Storage URLs.
        """
        if not photo_urls:
            raise ImageCacheError(f"No photo URLs for comparable {comp_id}")
        
        # Check existing cache
        if not force_refresh:
            existing = await self._load_from_db(comp_id)
            if existing and len(existing) >= MIN_IMAGES_FOR_PIR:
                logger.info(f"  ✓ Using {len(existing)} cached images for comp {comp_id}")
                return existing
        
        logger.info(f"  → Caching {len(photo_urls)} images for comp {comp_id}...")
        
        # Download and upload in batches
        cached_urls: List[str] = []
        
        for batch_start in range(0, len(photo_urls), BATCH_SIZE):
            batch = photo_urls[batch_start:batch_start + BATCH_SIZE]
            tasks = [
                self._cache_single(comp_id, url, batch_start + i)
                for i, url in enumerate(batch)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, str) and result:
                    cached_urls.append(result)
            
            if batch_start + BATCH_SIZE < len(photo_urls):
                await asyncio.sleep(BATCH_DELAY)
        
        # Save to database
        if cached_urls:
            await self._save_to_db(comp_id, cached_urls)
        
        logger.info(f"  ✓ Cached {len(cached_urls)}/{len(photo_urls)} images for comp {comp_id}")
        
        return cached_urls
    
    async def get_cached_urls(self, comp_id: int) -> List[str]:
        """Get cached image URLs for a comparable."""
        return await self._load_from_db(comp_id)
    
    async def validate_comparable(self, comp_id: int, min_images: int = MIN_IMAGES_FOR_PIR) -> bool:
        """Check if comparable has enough cached images."""
        cached = await self._load_from_db(comp_id)
        return len(cached) >= min_images
    
    async def _cache_single(self, comp_id: int, url: str, index: int) -> Optional[str]:
        """Download and upload a single image."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        ext = self._get_extension(url)
        filename = f"{comp_id}/{url_hash}_{index}.{ext}"
        
        # Download
        data, content_type = await self._download(url)
        if not data:
            return None
        
        # Upload
        return await self._upload(filename, data, content_type)
    
    async def _download(self, url: str) -> Tuple[Optional[bytes], str]:
        """Download image with retries."""
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
                    response = await client.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; PuedoCasa/1.0)",
                            "Accept": "image/*"
                        }
                    )
                    
                    if response.status_code == 200:
                        return response.content, response.headers.get("content-type", "image/jpeg")
                    
                    if response.status_code in (403, 404, 410):
                        return None, ""
                    
            except httpx.TimeoutException:
                pass
            except Exception:
                pass
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 * (attempt + 1))
        
        return None, ""
    
    async def _upload(self, filename: str, data: bytes, content_type: str) -> Optional[str]:
        """Upload image to Supabase Storage (fail loud in logs, return None on failure)."""
        url, key = self._get_credentials()
        mime = self._normalize_mime(content_type)
        
        try:
            async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
                response = await client.post(
                    f"{url}/storage/v1/object/{CACHE_BUCKET}/{filename}",
                    content=data,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": mime,
                        "x-upsert": "true"
                    }
                )
                
                if response.status_code in (200, 201):
                    return f"{url}/storage/v1/object/public/{CACHE_BUCKET}/{filename}"
                
                # Log failures (previously swallowed, leading to lots of confusing 400s)
                logger.warning(
                    f"  ⚠️ Storage upload failed: {response.status_code} | bucket={CACHE_BUCKET} | path={filename} | body={response.text[:300]}"
                )
        except Exception:
            logger.exception(f"  ⚠️ Storage upload exception | bucket={CACHE_BUCKET} | path={filename}")
        
        return None
    
    async def _load_from_db(self, comp_id: int) -> List[str]:
        """Load cached URLs from database."""
        try:
            client, base_url = await self._get_db()
            response = await client.get(
                f"{base_url}/comparable_image_cache",
                params={"comparable_id": f"eq.{comp_id}", "select": "cached_urls"}
            )
            if response.status_code == 200:
                rows = response.json()
                if rows and rows[0].get("cached_urls"):
                    return rows[0]["cached_urls"]
        except Exception:
            pass
        return []
    
    async def _save_to_db(self, comp_id: int, cached_urls: List[str]):
        """Save cached URLs to database."""
        try:
            client, base_url = await self._get_db()
            await client.delete(f"{base_url}/comparable_image_cache", params={"comparable_id": f"eq.{comp_id}"})
            await client.post(f"{base_url}/comparable_image_cache", json={
                "comparable_id": comp_id,
                "cached_urls": cached_urls,
                "image_count": len(cached_urls)
            })
        except Exception:
            pass
    
    @staticmethod
    def _get_extension(url: str) -> str:
        url_lower = url.lower()
        if ".png" in url_lower:
            return "png"
        if ".webp" in url_lower:
            return "webp"
        if ".gif" in url_lower:
            return "gif"
        return "jpg"
    
    @staticmethod
    def _normalize_mime(content_type: str) -> str:
        ct = content_type.lower()
        if "png" in ct:
            return "image/png"
        if "webp" in ct:
            return "image/webp"
        if "gif" in ct:
            return "image/gif"
        return "image/jpeg"


# =============================================================================
# SINGLETON
# =============================================================================

_cache: Optional[ImageCache] = None


def get_image_cache() -> ImageCache:
    """Get singleton ImageCache instance."""
    global _cache
    if _cache is None:
        _cache = ImageCache()
    return _cache
