"""
Lean MVP Pydantic Schemas
=========================

Request/response models for the API.
Matches database schema and frontend types.
Aligned with ListingEditor full schema.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class PipelineStatus(str, Enum):
    SCRAPED = "scraped"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class TierName(str, Enum):
    COSMETIC = "cosmetic"
    SYSTEMS = "systems"
    STRUCTURE = "structure"


class ListingType(str, Enum):
    SALE = "sale"
    RENT = "rent"
    RENT_TO_OWN = "rent_to_own"


class PricePeriod(str, Enum):
    TOTAL = "total"
    MONTH = "month"


class Condition(str, Enum):
    NEW = "new"
    GOOD = "good"
    RENOVATE = "renovate"


class FloorLevel(str, Enum):
    GROUND = "ground"
    INTERMEDIATE = "intermediate"
    TOP = "top"


class PropertySubtype(str, Enum):
    FLAT = "flat"
    PENTHOUSE = "penthouse"
    DUPLEX = "duplex"
    STUDIO = "studio"
    CHALET_DETACHED = "chalet_detached"
    CHALET_SEMI = "chalet_semi"
    CHALET_TERRACED = "chalet_terraced"
    RUSTIC = "rustic"


class HousingSituation(str, Enum):
    FREE = "free"
    RENTED = "rented"
    BARE_OWNERSHIP = "bare_ownership"
    SQUATTED = "squatted"
    AUCTION = "auction"


class AdOrigin(str, Enum):
    STANDARD = "standard"
    BANK = "bank"


# =============================================================================
# NESTED MODELS
# =============================================================================

class Areas(BaseModel):
    """Area measurements for a property."""
    constructed: Optional[int] = None  # m2_built / área bruta
    useful: Optional[int] = None       # m2_useful / área útil
    plot: Optional[int] = None         # m2_plot / área terreno (CRITICAL for houses!)


class Agency(BaseModel):
    """Real estate agency information (full schema)."""
    name: Optional[str] = None
    logo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    agent_name: Optional[str] = None
    agent_photo_url: Optional[str] = None
    agent_phone: Optional[str] = None
    whatsapp: Optional[str] = None


class Location(BaseModel):
    """Location information for a listing."""
    address: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    region: Optional[str] = None
    country: str = "Spain"
    lat: Optional[float] = None
    lng: Optional[float] = None


# =============================================================================
# SCRAPED DATA (FULL SCHEMA - Matches ListingEditor)
# =============================================================================

class ScrapedData(BaseModel):
    """
    Full schema data extracted from property listing.
    This matches the ListingEditor schema exactly.
    """
    # Core Info
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Numbers
    price_eur: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    
    # Areas
    areas: Optional[Areas] = None
    m2_built: Optional[int] = None   # Alias for areas.constructed (área bruta)
    m2_useful: Optional[int] = None  # Alias for areas.useful (área útil)
    m2_plot: Optional[int] = None    # Alias for areas.plot (área terreno - CRITICAL for houses!)
    sqm: Optional[int] = None  # Legacy alias
    
    # Transaction
    listing_type: Optional[str] = None  # 'sale' | 'rent' | 'rent_to_own'
    price_period: Optional[str] = None  # 'total' | 'month'
    
    # Location
    address: Optional[str] = None
    street_name: Optional[str] = None
    street_number: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Spain"
    lat: Optional[float] = None
    lng: Optional[float] = None
    autocomplete_query: Optional[str] = None
    
    # Address Resolution (res_10 = precise address, res_8 = neighborhood, res_0 = unknown)
    address_resolution: Optional[str] = None  # 'res_10', 'res_9', 'res_8', 'res_6', 'res_0'
    address_confidence: Optional[float] = None  # 0.0 to 1.0
    coords_validated: Optional[bool] = None  # True if coordinates verified against address
    coords_source: Optional[str] = None  # 'parsed' (from HTML), 'geocoded', or None
    
    # Coordinate Resolution (from Geoapify geocoding)
    coords_resolution: Optional[str] = None  # 'building', 'street', 'neighborhood', 'city', etc.
    coords_confidence: Optional[float] = None  # 0.0 to 1.0 from geocoder
    
    # Property Classification
    property_type: Optional[str] = None  # Legacy
    property_subtype: Optional[str] = None  # 'flat', 'penthouse', 'duplex', etc.
    housing_situation: Optional[str] = None  # 'free', 'rented', 'bare_ownership', etc.
    ad_origin: Optional[str] = None  # 'standard', 'bank'
    condition: Optional[str] = None  # 'new', 'good', 'renovate'
    energy_rating: Optional[str] = None  # 'A', 'B', 'C', 'D', 'E', 'F', 'G' - Energy certificate
    construction_year: Optional[int] = None  # Year built (from listing or cadastre)
    
    # Floor Info
    floor_level: Optional[str] = None  # 'ground', 'intermediate', 'top'
    floor_number: Optional[int] = None
    
    # Boolean Amenities
    has_elevator: Optional[bool] = None
    is_exterior: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garage: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_storage: Optional[bool] = None
    has_air_conditioning: Optional[bool] = None
    has_wardrobes: Optional[bool] = None
    is_accessible: Optional[bool] = None
    
    # Orientations
    balcony_orientation: Optional[str] = None
    terrace_orientation: Optional[str] = None
    
    # Features & Amenities
    features: List[str] = Field(default_factory=list)  # Legacy
    amenities: List[str] = Field(default_factory=list)
    additionalFeatures: List[str] = Field(default_factory=list)
    roomsAndAmenities: Optional[str] = None
    
    # Photos
    image_urls: List[str] = Field(default_factory=list)
    photo_urls: List[str] = Field(default_factory=list)  # Alias
    
    # Reference & Source
    reference: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: Optional[str] = None
    
    # Agency
    agency: Optional[Agency] = None
    
    # Raw metadata for debugging
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# LISTING (Full Database Schema)
# =============================================================================

class ListingBase(BaseModel):
    """Base listing fields matching full schema."""
    source_url: str
    source_domain: Optional[str] = None
    
    # Core Info
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Numbers
    price_eur: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    
    # Areas
    m2_built: Optional[int] = None
    m2_useful: Optional[int] = None
    m2_plot: Optional[int] = None  # Plot/land area (for houses)
    sqm: Optional[int] = None  # Legacy compatibility
    
    # Transaction
    listing_type: Optional[str] = None
    price_period: Optional[str] = None
    
    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    region: Optional[str] = None
    country: str = "Spain"
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Property Classification
    property_type: Optional[str] = None  # Legacy
    property_subtype: Optional[str] = None
    housing_situation: Optional[str] = None
    ad_origin: Optional[str] = None
    condition: Optional[str] = None
    
    # Floor Info
    floor_level: Optional[str] = None
    floor_number: Optional[int] = None
    
    # Boolean Amenities
    has_elevator: Optional[bool] = None
    is_exterior: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garage: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_storage: Optional[bool] = None
    has_air_conditioning: Optional[bool] = None
    has_wardrobes: Optional[bool] = None
    is_accessible: Optional[bool] = None
    
    # Features
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    
    # Reference
    reference: Optional[str] = None


class ListingCreate(ListingBase):
    """Data for creating a new listing."""
    scraped_data: Optional[Dict[str, Any]] = None
    image_urls: List[str] = Field(default_factory=list)
    agency: Optional[Dict[str, Any]] = None


class ListingUpdate(BaseModel):
    """Data for updating a listing (all optional)."""
    title: Optional[str] = None
    description: Optional[str] = None
    price_eur: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    m2_built: Optional[int] = None
    m2_useful: Optional[int] = None
    m2_plot: Optional[int] = None  # Plot/land area (for houses)
    sqm: Optional[int] = None
    listing_type: Optional[str] = None
    price_period: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    region: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    property_type: Optional[str] = None
    property_subtype: Optional[str] = None
    housing_situation: Optional[str] = None
    ad_origin: Optional[str] = None
    condition: Optional[str] = None
    floor_level: Optional[str] = None
    floor_number: Optional[int] = None
    has_elevator: Optional[bool] = None
    is_exterior: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garage: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_storage: Optional[bool] = None
    has_air_conditioning: Optional[bool] = None
    has_wardrobes: Optional[bool] = None
    is_accessible: Optional[bool] = None
    features: Optional[List[str]] = None
    reference: Optional[str] = None


class Listing(ListingBase):
    """Full listing with database fields."""
    id: int
    user_id: Optional[str] = None
    scraped_data: Optional[Dict[str, Any]] = None
    agency: Optional[Dict[str, Any]] = None
    pipeline_status: PipelineStatus = PipelineStatus.SCRAPED
    pipeline_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ListingWithPhotos(Listing):
    """Listing with photo URLs."""
    photos: List[str] = Field(default_factory=list)


# =============================================================================
# PHOTO
# =============================================================================

class ListingPhoto(BaseModel):
    """Photo attached to a listing."""
    id: int
    listing_id: int
    url: str
    storage_path: Optional[str] = None
    display_order: int = 0
    is_primary: bool = False
    room_type: Optional[str] = None
    cluster_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# API REQUESTS
# =============================================================================

class ScrapeRequest(BaseModel):
    """Request to scrape a URL."""
    url: str


# =============================================================================
# API RESPONSES
# =============================================================================

class ScrapeResponse(BaseModel):
    """Response from scraping."""
    success: bool
    data: Optional[ScrapedData] = None
    error: Optional[str] = None
    source_url: str
    source_domain: str


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ListingsResponse(BaseModel):
    """Response with multiple listings."""
    success: bool
    data: List[ListingWithPhotos]
    total: int


class ListingResponse(BaseModel):
    """Response with single listing."""
    success: bool
    data: Optional[ListingWithPhotos] = None
    error: Optional[str] = None


# =============================================================================
# DOMAIN DETECTION
# =============================================================================

class DomainConfig(BaseModel):
    """Configuration for a known domain."""
    name: str
    color: str
    bg_color: str
    text_color: str


KNOWN_DOMAINS: Dict[str, DomainConfig] = {
    "idealista.com": DomainConfig(
        name="Idealista", 
        color="#00b140", 
        bg_color="bg-green-50", 
        text_color="text-green-700"
    ),
    "fotocasa.es": DomainConfig(
        name="Fotocasa", 
        color="#ff6b35", 
        bg_color="bg-orange-50", 
        text_color="text-orange-700"
    ),
    "habitaclia.com": DomainConfig(
        name="Habitaclia", 
        color="#ff6900", 
        bg_color="bg-orange-50", 
        text_color="text-orange-700"
    ),
    "pisos.com": DomainConfig(
        name="Pisos.com", 
        color="#0066cc", 
        bg_color="bg-blue-50", 
        text_color="text-blue-700"
    ),
    "lucasfox.com": DomainConfig(
        name="Lucas Fox", 
        color="#1a1a1a", 
        bg_color="bg-stone-100", 
        text_color="text-stone-700"
    ),
    "engelvoelkers.com": DomainConfig(
        name="Engel & Völkers", 
        color="#c4122e", 
        bg_color="bg-red-50", 
        text_color="text-red-700"
    ),
    "kyero.com": DomainConfig(
        name="Kyero", 
        color="#005eb8", 
        bg_color="bg-blue-50", 
        text_color="text-blue-700"
    ),
    "rightmove.co.uk": DomainConfig(
        name="Rightmove", 
        color="#00deb6", 
        bg_color="bg-teal-50", 
        text_color="text-teal-700"
    ),
    "immobilienscout24.de": DomainConfig(
        name="ImmoScout24", 
        color="#ff6600", 
        bg_color="bg-orange-50", 
        text_color="text-orange-700"
    ),
}


def get_domain_config(url: str) -> Optional[DomainConfig]:
    """Get config for a known domain."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        for domain, config in KNOWN_DOMAINS.items():
            if domain in hostname:
                return config
        return None
    except Exception:
        return None


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        return hostname.replace("www.", "")
    except Exception:
        return "unknown"