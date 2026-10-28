"""
Universal AI Scraper - Gemini-powered extraction for any property site

This is now a thin wrapper around gemini_universal.py which contains
the ultimate extraction logic with:
- Complete ListingEditor-compatible schema
- Response schema for structured output
- Hi-res image extraction
- Multilingual support (ES, EN, DE, FR, PT, IT, NL, CA)

For direct access to the new implementation:
    from scraper.parsers.gemini_universal import extract_property_data
"""

import logging
from typing import Any, Dict

# Import the new implementation
from scraper.parsers.gemini_universal import extract_property_data, parse_universal as _parse_universal

logger = logging.getLogger(__name__)


async def extract_universal_data(html: str, url: str) -> Dict[str, Any]:
    """
    DEPRECATED: Use extract_property_data from gemini_universal instead.
    This wrapper exists for backwards compatibility.
    """
    logger.info(f"🤖 Universal AI extraction for: {url} (using gemini_universal)")
    return await extract_property_data(html, url)


async def parse_universal(html: str, url: str) -> Dict[str, Any]:
    """
    Main entry point for universal AI parsing.
    Returns full schema data ready for normalization.
    """
    return await _parse_universal(html, url)

