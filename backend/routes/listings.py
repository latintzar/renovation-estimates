"""
Listings Routes
===============

API endpoints for managing property listings.
Photos are stored as URLs - they'll be fetched via Scrapfly when needed for Gemini.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from schema import (
    ListingCreate, 
    ListingUpdate, 
    ListingWithPhotos,
    ListingsResponse,
    ListingResponse,
    ApiResponse,
    extract_domain
)
import database

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/listings", response_model=ListingsResponse)
async def get_listings(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: Optional[str] = None
):
    """
    Get all listings with photos.
    
    Args:
        limit: Max items to return (1-100)
        offset: Pagination offset
        user_id: Filter by user (optional)
    """
    try:
        listings = await database.get_listings(limit=limit, offset=offset, user_id=user_id)
        total = await database.count_listings(user_id=user_id)
        
        return ListingsResponse(
            success=True,
            data=listings,
            total=total
        )
    except Exception as e:
        logger.error(f"Get listings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int):
    """
    Get a single listing by ID.
    """
    try:
        listing = await database.get_listing_with_photos(listing_id)
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        return ListingResponse(
            success=True,
            data=listing
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listings", response_model=ListingResponse)
async def create_listing(data: ListingCreate):
    """
    Create a new listing.
    
    This is called after scraping, when user confirms the data.
    Photos are stored as URLs - fetched via Scrapfly when needed for Gemini calls.
    """
    try:
        # Ensure domain is set
        if not data.source_domain and data.source_url:
            data.source_domain = extract_domain(data.source_url)
        
        # Convert to dict for database
        listing_data = data.model_dump()
        
        # Create listing (database.create_listing handles photos)
        listing = await database.create_listing(listing_data)
        
        # Get with photos
        listing_with_photos = await database.get_listing_with_photos(listing["id"])
        
        logger.info(f"Created listing {listing['id']}: {listing.get('title', 'Untitled')}")
        
        return ListingResponse(
            success=True,
            data=listing_with_photos
        )
    except Exception as e:
        logger.error(f"Create listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(listing_id: int, data: ListingUpdate):
    """
    Update an existing listing.
    """
    try:
        # Check exists
        existing = await database.get_listing(listing_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Update
        update_data = data.model_dump(exclude_unset=True)
        updated = await database.update_listing(listing_id, update_data)
        
        # Get with photos
        listing_with_photos = await database.get_listing_with_photos(listing_id)
        
        logger.info(f"Updated listing {listing_id}")
        
        return ListingResponse(
            success=True,
            data=listing_with_photos
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/listings/{listing_id}", response_model=ApiResponse)
async def delete_listing(listing_id: int):
    """
    Delete a listing.
    """
    try:
        deleted = await database.delete_listing(listing_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        logger.info(f"Deleted listing {listing_id}")
        
        return ApiResponse(
            success=True,
            message=f"Listing {listing_id} deleted"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}/photos")
async def get_listing_photos(listing_id: int):
    """
    Get photos for a listing.
    """
    try:
        photos = await database.get_listing_photos(listing_id)
        
        return {
            "success": True,
            "data": photos
        }
    except Exception as e:
        logger.error(f"Get photos error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}/due-diligence")
async def get_due_diligence(listing_id: int):
    """
    Get Section 2 enhanced research data for the UI.
    
    Returns comprehensive research across 7 categories (used for Renovation Difficulty):
    1. Building Health & Structural Risk
    2. Environmental & Natural Hazards
    3. Legal & Urban Planning Status
    4. Neighborhood & Social Safety
    5. Running Costs & Ongoing Fees
    6. Infrastructure & Connectivity
    7. Market Position & Investment Context
    """
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        
        response = await client.get(
            f"{base_url}/due_diligence_research",
            params={"listing_id": f"eq.{listing_id}", "select": "*"},
            headers=database._get_headers()
        )
        
        if response.status_code != 200:
            logger.error(f"Supabase error: {response.text}")
            return {"listing_id": listing_id, "has_data": False}
        
        rows = response.json()
        if not rows:
            return {"listing_id": listing_id, "has_data": False}
        
        data = rows[0]
        
        # Parse JSONB fields if needed
        categories = data.get("categories", [])
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except json.JSONDecodeError:
                categories = []
        
        all_sources = data.get("all_sources", [])
        if isinstance(all_sources, str):
            try:
                all_sources = json.loads(all_sources)
            except json.JSONDecodeError:
                all_sources = []
        
        property_context = data.get("property_context", {})
        if isinstance(property_context, str):
            try:
                property_context = json.loads(property_context)
            except json.JSONDecodeError:
                property_context = {}
        
        return {
            "listing_id": listing_id,
            "has_data": True,
            "overall_risk_score": data.get("overall_risk_score"),
            "overall_risk_level": data.get("overall_risk_level"),
            "categories": categories,
            "all_sources": all_sources,
            "total_queries": data.get("total_queries"),
            "total_sources": data.get("total_sources"),
            "property_context": property_context,
            "model_used": data.get("model_used"),
            "created_at": data.get("created_at"),
        }
    except Exception as e:
        logger.error(f"Get due diligence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

