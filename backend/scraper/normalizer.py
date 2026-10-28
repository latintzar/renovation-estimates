"""
Scraper Normalizer
==================

Transforms raw scraped data into a canonical normalized format.
Ported from src/lib/scraper-normalizer.ts

This ensures consistent output regardless of which parser was used.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def normalize_scraped_data(raw_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
    """
    Normalize raw scraped data into canonical format.
    
    Handles various data formats from different parsers:
    - Idealista parser (server.ts port)
    - Universal AI parser (ai.ts port)
    
    Returns a consistent dict ready for ScrapedData model.
    """
    logger.info(f"📦 Normalizing scraped data for: {source_url}")
    
    # 1. Basic Info
    title = raw_data.get("title")
    description = raw_data.get("description")
    
    # 2. Price (handle various formats)
    price_eur = _normalize_price(raw_data.get("price_eur") or raw_data.get("price"))
    
    # 3. Areas (including plot for houses/villas)
    m2_built = _normalize_int(raw_data.get("m2_built") or raw_data.get("sqm"))
    m2_useful = _normalize_int(raw_data.get("m2_useful"))
    m2_plot = _normalize_int(raw_data.get("m2_plot"))
    
    areas = {
        "constructed": m2_built,
        "useful": m2_useful,
        "plot": m2_plot
    }
    
    # 4. Rooms
    bedrooms = _normalize_int(raw_data.get("bedrooms"))
    bathrooms = _normalize_int(raw_data.get("bathrooms"))
    
    # 5. Location
    address = raw_data.get("address")
    city = raw_data.get("city")
    neighborhood = raw_data.get("neighborhood")
    region = raw_data.get("region")
    country = raw_data.get("country") or "Spain"
    lat = _normalize_float(raw_data.get("lat"))
    lng = _normalize_float(raw_data.get("lng"))
    
    # 6. Property Type & Condition
    property_subtype = raw_data.get("property_subtype") or raw_data.get("property_type")
    housing_situation = raw_data.get("housing_situation")
    condition = raw_data.get("condition")
    energy_rating = raw_data.get("energy_rating")  # A-G energy certificate
    construction_year = _normalize_int(raw_data.get("construction_year"))  # Year built
    floor_level = raw_data.get("floor_level")
    floor_number = _normalize_int(raw_data.get("floor_number"))
    
    # 7. Booleans (ensure proper boolean values)
    has_elevator = _normalize_bool(raw_data.get("has_elevator"))
    is_exterior = _normalize_bool(raw_data.get("is_exterior"))
    has_terrace = _normalize_bool(raw_data.get("has_terrace"))
    has_balcony = _normalize_bool(raw_data.get("has_balcony"))
    has_pool = _normalize_bool(raw_data.get("has_pool"))
    has_garage = _normalize_bool(raw_data.get("has_garage"))
    has_garden = _normalize_bool(raw_data.get("has_garden"))
    has_storage = _normalize_bool(raw_data.get("has_storage"))
    has_air_conditioning = _normalize_bool(raw_data.get("has_air_conditioning"))
    has_wardrobes = _normalize_bool(raw_data.get("has_wardrobes"))
    is_accessible = _normalize_bool(raw_data.get("is_accessible"))
    
    # 8. Listing Type
    listing_type = raw_data.get("listing_type") or "sale"
    price_period = raw_data.get("price_period") or "total"
    
    # 9. Photos (normalize from various formats)
    image_urls = _normalize_photos(raw_data)
    
    # 10. Features & Amenities
    amenities = raw_data.get("amenities") or raw_data.get("features") or []
    additional_features = raw_data.get("additionalFeatures") or []
    
    # 11. Reference & Contact
    reference = raw_data.get("reference")
    agency = raw_data.get("agency")
    
    # Build normalized result
    result = {
        "title": title,
        "description": description,
        "price_eur": price_eur,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "areas": areas,
        "sqm": m2_built,  # Legacy compatibility
        "listing_type": listing_type,
        "price_period": price_period,
        "address": address,
        "city": city,
        "neighborhood": neighborhood,
        "region": region,
        "country": country,
        "lat": lat,
        "lng": lng,
        "property_subtype": property_subtype,
        "housing_situation": housing_situation,
        "condition": condition,
        "energy_rating": energy_rating,
        "construction_year": construction_year,
        "m2_plot": m2_plot,  # Plot area for houses (also in areas.plot)
        "floor_level": floor_level,
        "floor_number": floor_number,
        "has_elevator": has_elevator,
        "is_exterior": is_exterior,
        "has_terrace": has_terrace,
        "has_balcony": has_balcony,
        "has_pool": has_pool,
        "has_garage": has_garage,
        "has_garden": has_garden,
        "has_storage": has_storage,
        "has_air_conditioning": has_air_conditioning,
        "has_wardrobes": has_wardrobes,
        "is_accessible": is_accessible,
        "amenities": amenities,
        "additionalFeatures": additional_features,
        "image_urls": image_urls,
        "photo_urls": image_urls,
        "reference": reference,
        "agency": agency,
        "source_url": source_url,
        "scraped_at": datetime.now().isoformat(),
        "raw_metadata": {}
    }
    
    logger.info(f"✅ Normalized: {title or 'Unknown'} - {len(image_urls)} photos")
    
    return result


def _normalize_price(value: Any) -> Optional[int]:
    """Normalize price to integer."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        # Remove non-digits and convert
        clean = ''.join(c for c in value if c.isdigit())
        return int(clean) if clean else None
    return None


def _normalize_int(value: Any) -> Optional[int]:
    """Normalize to integer."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.replace(",", ".").replace(" ", "")))
        except (ValueError, TypeError):
            return None
    return None


def _normalize_float(value: Any) -> Optional[float]:
    """Normalize to float (for lat/lng)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except (ValueError, TypeError):
            return None
    return None


def _normalize_bool(value: Any) -> Optional[bool]:
    """Normalize to boolean."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "si", "sí")
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _normalize_photos(raw_data: Dict[str, Any]) -> List[str]:
    """Extract and normalize photo URLs from various formats."""
    photos: List[str] = []
    
    # Try different photo sources
    sources = [
        raw_data.get("image_urls"),
        raw_data.get("photo_urls"),
        raw_data.get("photos"),
    ]
    
    for source in sources:
        if source:
            if isinstance(source, list):
                for item in source:
                    if isinstance(item, str):
                        photos.append(item)
                    elif isinstance(item, dict):
                        # Handle {url: "...", tag: "..."} format
                        url = item.get("url") or item.get("src") or item.get("imageDataService")
                        if url:
                            photos.append(url)
            break
    
    # Deduplicate while preserving order
    seen = set()
    unique_photos = []
    for url in photos:
        if url not in seen:
            seen.add(url)
            unique_photos.append(url)
    
    return unique_photos
