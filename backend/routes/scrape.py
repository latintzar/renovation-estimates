"""
Scraping Routes
===============

API endpoints for scraping property listings.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from schema import ScrapeRequest, ScrapeResponse
from scraper.router import scrape_url, scrape_preview
from scraper.parsers.url_validator import validate_listing_url

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# VALIDATION SCHEMAS
# =============================================================================

class ValidateRequest(BaseModel):
    """Request for URL validation."""
    url: str

class ValidateResponse(BaseModel):
    """Response from URL validation."""
    success: bool
    is_valid: bool
    confidence: str
    detected_type: str
    rejection_reason: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# VALIDATION ENDPOINT
# =============================================================================

@router.post("/scrape/validate", response_model=ValidateResponse)
async def validate_url(request: ValidateRequest) -> ValidateResponse:
    """
    Quick validation to check if a URL is a property listing.
    
    Uses Gemini 2.5 Flash Lite for super fast, cheap classification.
    Call this BEFORE the full scrape to reject non-listing URLs early.
    
    Returns:
        ValidateResponse with is_valid and rejection_reason if rejected
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    logger.info(f"Validate request: {request.url[:80]}...")
    
    try:
        result = await validate_listing_url(request.url)
        
        return ValidateResponse(
            success=True,
            is_valid=result.is_valid,
            confidence=result.confidence,
            detected_type=result.detected_type,
            rejection_reason=result.rejection_reason,
            error=result.error,
        )
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        # On error, allow through (don't block legitimate requests)
        return ValidateResponse(
            success=False,
            is_valid=True,  # Allow through
            confidence="low",
            detected_type="unknown",
            error=str(e),
        )


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_listing(request: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape a property listing URL.
    
    Supports:
    - Idealista (idealista.com/es, idealista.pt)
    - Any other property listing site (universal parser)
    
    Returns:
        ScrapeResponse with extracted data or error
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    logger.info(f"Scrape request: {request.url[:80]}...")
    
    try:
        result = await scrape_url(request.url)
        
        if not result.success:
            logger.warning(f"Scrape failed: {result.error}")
        else:
            logger.info(f"Scrape success: {result.data.title if result.data else 'No title'}")
        
        return result
        
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape/preview", response_model=ScrapeResponse)
async def preview_listing(request: ScrapeRequest) -> ScrapeResponse:
    """
    Quick scrape for preview (faster, no premium features).
    
    Use this for real-time feedback while user is entering URL.
    Falls back faster but may miss some data on protected sites.
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        return await scrape_preview(request.url)
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scrape/test")
async def test_scrape():
    """
    Test endpoint to verify scraper is working.
    """
    # Test with a known good URL
    test_url = "https://www.idealista.com/inmueble/106041682/"
    
    try:
        result = await scrape_preview(test_url)
        return {
            "status": "ok",
            "test_url": test_url,
            "success": result.success,
            "title": result.data.title if result.data else None,
            "error": result.error
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

