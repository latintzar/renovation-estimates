"""
Scraper Router
==============

Routes URLs to the appropriate parser and coordinates scraping.
Uses the full schema from rules.py and normalizes output.
"""

import logging
from typing import Optional, Dict, Any

from schema import ScrapedData, ScrapeResponse, extract_domain, Areas, Agency
from scraper.fetcher import fetch_url, get_parser_type, FetchResult
from scraper.parsers.idealista import parse_idealista
from scraper.parsers.universal import parse_universal
from scraper.normalizer import normalize_scraped_data
from scraper.location_intelligence import enrich_with_location
from scraper.geoapify_geocoder import geocode_if_missing
from scraper.bot_detection import (
    should_use_scrapling,
    detect_bot_block,
    analyze_extraction_quality,
    get_fetch_strategy,
    save_learned_domain,
)
from scraper.description_formatter import format_description_markdown

logger = logging.getLogger(__name__)


async def scrape_url(url: str) -> ScrapeResponse:
    """
    Scrape a property listing URL.
    
    Smart fetch strategy:
    1. Check if domain is known to need Scrapling → use directly
    2. If unknown, try direct fetch
    3. Analyze response for bot-block signals
    4. If blocked OR extraction fails → retry with Scrapling + learn
    
    Args:
        url: The property listing URL
        
    Returns:
        ScrapeResponse with data or error
    """
    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url
    
    domain = extract_domain(url)
    parser_type = get_parser_type(url)
    
    # Get smart fetch strategy for this domain
    strategy = get_fetch_strategy(domain)
    use_scrapling = strategy["use_scrapling"]
    
    logger.info(f"🔍 Scraping: {domain} (parser: {parser_type}, scrapling: {use_scrapling}, reason: {strategy['reason']})")
    
    # Fetch HTML with smart strategy
    result: FetchResult = await fetch_url(url, use_scrapling=use_scrapling)
    
    # If direct fetch, check for bot-block signals
    if result.success and not use_scrapling and result.html:
        is_blocked, block_reason = detect_bot_block(result.html, result.status_code or 200)
        if is_blocked:
            logger.warning(f"🤖 Bot-blocked detected: {block_reason}, retrying with Scrapling...")
            result = await fetch_url(url, use_scrapling=True)
            if result.success:
                logger.info(f"✅ Scrapling retry succeeded")
    
    # Fallback to Scrapling if direct fetch failed
    if not result.success and not use_scrapling:
        logger.info(f"⚠️ Direct fetch failed ({result.error}), trying Scrapling fallback...")
        result = await fetch_url(url, use_scrapling=True)
        if result.success:
            logger.info(f"✅ Scrapling fallback succeeded")
    
    if not result.success:
        logger.error(f"❌ Fetch failed: {result.error}")
        return ScrapeResponse(
            success=False,
            error=result.error or "Failed to fetch URL",
            source_url=url,
            source_domain=domain
        )
    
    if not result.html:
        return ScrapeResponse(
            success=False,
            error="Empty HTML response",
            source_url=url,
            source_domain=domain
        )
    
    # Parse HTML with appropriate parser
    try:
        raw_data = await _parse_html(result.html, url, parser_type)
        
        # Check extraction quality
        is_good, quality_reason = analyze_extraction_quality(raw_data)
        
        # If extraction failed and we haven't tried Scrapling yet, retry
        if not is_good and not result.used_scrapling:
            logger.warning(f"⚠️ Extraction failed ({quality_reason}), retrying with Scrapling...")
            scrapling_result = await fetch_url(url, use_scrapling=True, render_js=True)
            if scrapling_result.success and scrapling_result.html:
                raw_data = await _parse_html(scrapling_result.html, url, parser_type)
                result = scrapling_result  # Update result for final_url
                
                # Learn that this domain needs Scrapling
                save_learned_domain(domain, needs_scrapling=True)
                logger.info(f"📚 Learned: {domain} needs Scrapling for good extraction")
                
                # Re-check quality after Scrapling retry
                is_good, quality_reason = analyze_extraction_quality(raw_data)
        
        # LAYER 2 DEFENSE: Reject degraded extraction even after Scrapling.
        # WHY THIS MATTERS: If Scrapling returns a "soft-blocked" page (has title
        # but no photos/coordinates), saving it creates a listing that will
        # immediately crash the pipeline. Better to fail loud here than waste
        # Casafari calls, Gemini calls, and debugging time downstream.
        if not is_good:
            logger.error(
                f"❌ Extraction quality check FAILED after all attempts | "
                f"reason={quality_reason} | domain={domain} | used_scrapling={result.used_scrapling}"
            )
            return ScrapeResponse(
                success=False,
                error=f"Extraction degraded ({quality_reason}). Site may have soft-blocked the request — try again later.",
                source_url=url,
                source_domain=domain
            )
        
        # Normalize to canonical schema
        normalized = normalize_scraped_data(raw_data, result.final_url or url)
        
        # ALWAYS geocode if coordinates are missing
        # Uses Geoapify structured geocoding for maximum accuracy
        # Tracks resolution level (building, street, neighborhood, city)
        normalized = await geocode_if_missing(normalized)
        
        # Format description into clean markdown (post-processing step)
        # Uses Gemini 2.5 Flash with temperature 0 for deterministic output
        if normalized.get("description"):
            normalized["description"] = await format_description_markdown(normalized["description"])
        
        # Convert normalized dict to ScrapedData model
        scraped_data = _dict_to_scraped_data(normalized)
        
        # Ensure we have some data
        if not scraped_data.title and not scraped_data.price_eur:
            logger.warning("⚠️ Parsed data is sparse, extraction may have issues")
        else:
            logger.info(f"✅ Scraped: {scraped_data.title} - {scraped_data.price_eur}€")
        
        return ScrapeResponse(
            success=True,
            data=scraped_data,
            source_url=result.final_url or url,
            source_domain=domain
        )
        
    except Exception as e:
        logger.error(f"❌ Parse error: {e}", exc_info=True)
        return ScrapeResponse(
            success=False,
            error=f"Failed to parse HTML: {str(e)}",
            source_url=url,
            source_domain=domain
        )


async def _parse_html(html: str, url: str, parser_type: str) -> Dict[str, Any]:
    """
    Parse HTML with the appropriate parser.
    Returns raw dict ready for normalization.
    """
    if parser_type == "idealista":
        return await parse_idealista(html, url)
    else:
        # Use universal AI parser for everything else
        return await parse_universal(html, url)


def _dict_to_scraped_data(data: Dict[str, Any]) -> ScrapedData:
    """Convert normalized dict to ScrapedData pydantic model."""
    
    # Handle areas
    areas = None
    if data.get("areas"):
        areas = Areas(
            constructed=data["areas"].get("constructed"),
            useful=data["areas"].get("useful")
        )
    
    # Handle agency
    agency = None
    if data.get("agency"):
        agency = Agency(**data["agency"])
    
    # Get photo URLs from various sources
    photo_urls = data.get("photo_urls") or []
    image_urls = data.get("image_urls") or photo_urls
    
    return ScrapedData(
        title=data.get("title"),
        description=data.get("description"),
        price_eur=data.get("price_eur"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        areas=areas,
        m2_built=data.get("areas", {}).get("constructed"),
        m2_useful=data.get("areas", {}).get("useful"),
        sqm=data.get("areas", {}).get("constructed"),  # Legacy compatibility
        listing_type=data.get("listing_type"),
        price_period=data.get("price_period"),
        address=data.get("address"),
        street_name=data.get("street_name"),
        street_number=data.get("street_number"),
        city=data.get("city"),
        neighborhood=data.get("neighborhood"),
        region=data.get("region"),
        postal_code=data.get("postal_code"),
        country=data.get("country", "Spain"),
        lat=data.get("lat"),
        lng=data.get("lng"),
        autocomplete_query=data.get("autocomplete_query"),
        # Address Resolution
        address_resolution=data.get("address_resolution"),
        address_confidence=data.get("address_confidence"),
        coords_validated=data.get("coords_validated"),
        coords_source=data.get("coords_source"),
        # Coordinate Resolution (from geocoding)
        coords_resolution=data.get("coords_resolution"),
        coords_confidence=data.get("coords_confidence"),
        # Property Classification
        property_type=data.get("property_subtype"),  # Map to property_type for compatibility
        property_subtype=data.get("property_subtype"),
        housing_situation=data.get("housing_situation"),
        ad_origin=data.get("ad_origin"),
        condition=data.get("condition"),
        floor_level=data.get("floor_level"),
        floor_number=data.get("floor_number"),
        has_elevator=data.get("has_elevator"),
        is_exterior=data.get("is_exterior"),
        has_terrace=data.get("has_terrace"),
        has_balcony=data.get("has_balcony"),
        has_pool=data.get("has_pool"),
        has_garage=data.get("has_garage"),
        has_garden=data.get("has_garden"),
        has_storage=data.get("has_storage"),
        has_air_conditioning=data.get("has_air_conditioning"),
        has_wardrobes=data.get("has_wardrobes"),
        is_accessible=data.get("is_accessible"),
        balcony_orientation=data.get("balcony_orientation"),
        terrace_orientation=data.get("terrace_orientation"),
        features=data.get("amenities") or [],
        amenities=data.get("amenities") or [],
        additionalFeatures=data.get("additionalFeatures") or [],
        roomsAndAmenities=data.get("roomsAndAmenities"),
        image_urls=image_urls,
        photo_urls=photo_urls,
        reference=data.get("reference"),
        source_url=data.get("source_url"),
        scraped_at=data.get("scraped_at"),
        agency=agency,
        raw_metadata=data.get("raw_metadata") or {}
    )


async def scrape_preview(url: str) -> ScrapeResponse:
    """
    Quick scrape for preview (no Scrapling, faster).
    Used for immediate feedback while user types URL.
    """
    if not url.startswith("http"):
        url = "https://" + url
    
    domain = extract_domain(url)
    parser_type = get_parser_type(url)
    
    # Quick fetch without Scrapling
    result = await fetch_url(url, use_scrapling=False, timeout=15)
    
    if not result.success or not result.html:
        # Return minimal response for preview
        return ScrapeResponse(
            success=False,
            error=result.error or "Could not fetch",
            source_url=url,
            source_domain=domain
        )
    
    # Parse and normalize
    raw_data = await _parse_html(result.html, url, parser_type)
    normalized = normalize_scraped_data(raw_data, url)
    
    # Geocode if missing (same as full scrape)
    normalized = await geocode_if_missing(normalized)
    
    # Format description into clean markdown
    if normalized.get("description"):
        normalized["description"] = await format_description_markdown(normalized["description"])
    
    scraped_data = _dict_to_scraped_data(normalized)
    
    return ScrapeResponse(
        success=True,
        data=scraped_data,
        source_url=url,
        source_domain=domain
    )