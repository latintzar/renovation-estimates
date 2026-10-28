"""
Casafari API Client
===================

Client for Casafari real estate data API.
Used for: Comparable properties, market statistics, price estimates.

API Docs: https://api.casafari.com/docs
Auth: Token-based authentication via Authorization header

Endpoints Used:
- POST /v1/comparables/search - Get comparable properties
- GET /v1/references/types - Get property types
- GET /v1/references/conditions - Get property conditions
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv
from pathlib import Path

# Load environment
backend_root = Path(__file__).parent.parent
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CASAFARI_API_TOKEN = os.getenv("CASAFARI_API_TOKEN")
CASAFARI_BASE_URL = "https://api.casafari.com/v1"

# Property type mapping: Our types → Casafari types (list, primary first)
# Sources: scraper enum (gemini_universal.py) + Idealista types + common Spanish terms
#
# WHY LISTS: Casafari `comparables_types` accepts an array. Sending related
# types dramatically increases the comparable pool — a "chalet_terraced"
# (adosado) should match townhouses, row-houses, and generic houses.
#
# Casafari type groups for reference:
#   apartment: apartment, duplex, studio, penthouse, dachgeschosswohnung,
#              erdgeschosswohnung, etagenwohnung
#   house:     villa, einfamilienhaus, chalet, reihenhaus, country_house,
#              house, family_house, reihenendhaus, bungalow, zweifamilienhaus,
#              landwirtschaftliche_betriebe, palace, country_estate,
#              reihenmittelhaus, townhouse
PROPERTY_TYPE_MAP: dict[str, list[str]] = {
    # ── Apartments ────────────────────────────────────────────────────
    "apartment":  ["apartment", "etagenwohnung"],
    "piso":       ["apartment", "etagenwohnung"],
    "flat":       ["apartment", "etagenwohnung"],                    # scraper enum
    "studio":     ["studio", "apartment"],
    "estudio":    ["studio", "apartment"],
    "duplex":     ["duplex", "apartment"],
    "penthouse":  ["penthouse", "dachgeschosswohnung", "apartment"],
    "atico":      ["penthouse", "dachgeschosswohnung", "apartment"],

    # ── Houses — broad matching for comparable coverage ───────────────
    "house":              ["house", "family_house", "einfamilienhaus", "chalet", "villa"],
    "casa":               ["house", "family_house", "einfamilienhaus", "chalet", "villa"],
    "chalet":             ["chalet", "villa", "house", "einfamilienhaus", "family_house"],
    "chalet_detached":    ["chalet", "villa", "einfamilienhaus", "house", "family_house"],        # scraper enum
    "chalet_semi_detached": ["chalet", "reihenendhaus", "townhouse", "house", "family_house"],
    "chalet_semi":        ["chalet", "reihenendhaus", "townhouse", "house", "family_house"],      # scraper enum
    "chalet_terraced":    ["townhouse", "reihenhaus", "reihenmittelhaus", "reihenendhaus",        # scraper enum (adosado)
                           "house", "family_house"],
    "chalet detached":    ["chalet", "villa", "einfamilienhaus", "house", "family_house"],
    "villa":              ["villa", "chalet", "house", "einfamilienhaus", "family_house"],
    "townhouse":          ["townhouse", "reihenhaus", "reihenmittelhaus", "reihenendhaus",
                           "house", "family_house"],
    "adosado":            ["townhouse", "reihenhaus", "reihenmittelhaus", "reihenendhaus",
                           "house", "family_house"],
    "country_house":      ["country_house", "country_estate", "house", "family_house"],
    "rustic":             ["country_house", "country_estate", "house", "family_house"],            # scraper enum
    "finca":              ["country_estate", "country_house", "house"],
    "unifamiliar":        ["house", "family_house", "einfamilienhaus", "chalet"],
    "casa unifamiliar":   ["house", "family_house", "einfamilienhaus", "chalet"],
    "bungalow":           ["bungalow", "house", "family_house", "chalet"],

    # ── Other ─────────────────────────────────────────────────────────
    "plot":       ["plot", "urban_plot", "rural_plot"],
    "terreno":    ["plot", "urban_plot", "rural_plot"],
    "garage":     ["garage", "parking"],
    "parking":    ["parking", "garage"],
    "other":      ["house", "family_house", "apartment"],             # scraper enum fallback
}

# All Casafari types that belong to the "house" group — used for feature logic
HOUSE_TYPES = frozenset([
    "house", "villa", "chalet", "townhouse", "country_house", "country_estate",
    "bungalow", "family_house", "einfamilienhaus", "reihenhaus", "reihenendhaus",
    "reihenmittelhaus", "zweifamilienhaus", "palace",
])

# Condition sent to Casafari — ALWAYS "very-good".
#
# WHY THIS MATTERS: We're looking for renovation comparables. Casafari's
# condition filter is strict — "new" excludes most of the market and returns
# near-zero results, "used" excludes recently renovated properties. "very-good"
# gives us the broadest, most useful set of comps that represent the AFTER
# state of a renovated property. Never change this.
CASAFARI_CONDITION = "very-good"

# Energy rating scale — best to worst
ENERGY_RATING_SCALE = ["A+", "A", "B", "C", "D", "E", "F", "G", "H"]


def energy_ratings_above(target_rating: Optional[str]) -> Optional[List[str]]:
    """
    Return all energy ratings that are at least one level better than the target.
    If target is G, returns [A+, A, B, C, D, E, F].
    If target is unknown or not in scale, returns None (no filter).

    WHY THIS MATTERS: We want comparables that represent the AFTER state —
    a renovated property should have a better energy rating than the current
    unrenovated target.
    """
    if not target_rating:
        return None
    target_upper = target_rating.strip().upper()
    if target_upper not in ENERGY_RATING_SCALE:
        return None
    idx = ENERGY_RATING_SCALE.index(target_upper)
    if idx == 0:
        # Target is already A+ — can't go higher, return A+ itself
        return ["A+"]
    # Everything from the top down to one level above the target
    above = ENERGY_RATING_SCALE[:idx]
    # Also include Unknown so we don't accidentally exclude comps without ratings
    return above + ["Unknown"]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComparableProperty:
    """A comparable property from Casafari."""
    property_id: int
    price_bucket: str  # always 'comparable' (no bucketing)
    sale_price: int
    price_per_sqm: int
    total_area: Optional[int]      # Built area (m2_built)
    living_area: Optional[int]     # Useful area (m2_useful)
    plot_area: Optional[int]       # Plot/land area (m2_plot) - CRITICAL for houses!
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    condition: Optional[str]
    construction_year: Optional[int]
    energy_rating: Optional[str]
    distance_km: float
    address: Optional[str]
    property_url: str
    photo_urls: List[str]
    photo_urls_full: List[str]
    photo_urls_thumbnails: List[str]
    coordinates: Dict[str, float]
    features: Dict[str, Any]
    property_type: Optional[str] = None


@dataclass
class MarketStats:
    """Market statistics from Casafari."""
    average_price: int
    average_price_per_sqm: int
    average_days_on_market: int
    sold_last_6_months: int
    fast_sell_price: int
    fair_market_price: int
    out_of_market_price: int
    casafari_link: str


@dataclass
class ComparablesResult:
    """Full result from comparables search."""
    market_stats: MarketStats
    comparables: List[ComparableProperty]
    raw_response: Dict[str, Any]


# =============================================================================
# GEMINI RADIUS ADVISOR — for rural/low-density areas
# =============================================================================

_RADIUS_ADVISOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommended_radius_km": {
            "type": "number",
            "description": "Recommended search radius in kilometers (min 3, max 50)",
        },
        "reasoning": {
            "type": "string",
            "description": "One-sentence explanation of why this radius was chosen",
        },
    },
    "required": ["recommended_radius_km", "reasoning"],
}


async def _gemini_suggest_radius(
    *,
    latitude: float,
    longitude: float,
    property_type: str,
    bedrooms: Optional[int],
    current_radius_km: float,
) -> Optional[float]:
    """
    Ask Gemini Pro to suggest a search radius when Casafari found 0 results.

    WHY THIS EXISTS: Rural areas (villages, small towns) have no comparable
    properties within 1-2km. A professional appraiser would know to search
    15-20km to reach the nearest active property market. Gemini has the same
    geographic knowledge — it knows that Asón-Agüera (pop. 1,500) needs a
    wider net than central Madrid.

    Returns the suggested radius in km, or None on failure.
    """
    try:
        from pipeline.gemini_client import call_gemini_json

        prompt = (
            f"You are a senior real estate appraiser in Europe. "
            f"I searched for comparable {property_type} properties "
            f"({bedrooms or '?'} bedrooms, condition: very-good) within "
            f"{current_radius_km}km of coordinates ({latitude}, {longitude}) "
            f"and found ZERO results.\n\n"
            f"Based on your knowledge of this location — the nearest towns, "
            f"population density, and active property markets — what search "
            f"radius (in km) should I use to find at least 5-10 comparable "
            f"very-good condition properties for sale?\n\n"
            f"Consider: What are the nearest towns with an active real estate "
            f"market? How far away are they? The radius must be between 3 and "
            f"50 km. Pick the smallest radius likely to yield results — don't "
            f"overshoot."
        )

        resp = await call_gemini_json(
            prompt=prompt,
            model="pro",
            temperature=0.2,
            response_schema=_RADIUS_ADVISOR_SCHEMA,
        )

        if not resp.success:
            logger.warning(f"Gemini radius advisor failed: {resp.error}")
            return None

        import json
        result = json.loads(resp.text)
        radius = float(result.get("recommended_radius_km", 0))
        reasoning = result.get("reasoning", "")
        logger.info(f"🧠 Gemini radius advisor: {radius}km — {reasoning}")

        if radius < 3.0:
            radius = 3.0
        if radius > 50.0:
            radius = 50.0
        return radius

    except Exception:
        logger.exception("Gemini radius advisor error")
        return None


# =============================================================================
# CLIENT CLASS
# =============================================================================

class CasafariClient:
    """Client for Casafari API."""
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or CASAFARI_API_TOKEN
        if not self.api_token:
            logger.warning(
                "❌ CASAFARI_API_TOKEN not set! "
                "Add to .env.local: CASAFARI_API_TOKEN=..."
            )
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }
    
    async def search_comparables(
        self,
        latitude: float,
        longitude: float,
        property_type: str = "apartment",
        operation: str = "sale",
        bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        total_area: Optional[int] = None,
        plot_area: Optional[int] = None,  # CRITICAL for houses!
        distance_km: float = 1.0,
        count: int = 50,
        energy_ratings: Optional[List[str]] = None,  # Filter by energy cert
        # LISTING FEATURES - for matching true comparables
        has_elevator: Optional[bool] = None,
        has_terrace: Optional[bool] = None,
        has_balcony: Optional[bool] = None,
        has_pool: Optional[bool] = None,
        has_garage: Optional[bool] = None,
        has_garden: Optional[bool] = None,
        has_storage: Optional[bool] = None,
        has_parking: Optional[bool] = None,
        floor_level: Optional[str] = None,  # 'ground', 'intermediate', 'top'
        floor_number: Optional[int] = None,  # Exact floor number (1-250)
        is_exterior: Optional[bool] = None,  # Exterior vs interior orientation
    ) -> ComparablesResult:
        """
        Search for comparable properties near a location.
        
        CRITICAL: condition is ALWAYS "very-good". Do NOT add a condition
        parameter here — see CASAFARI_CONDITION constant.
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            property_type: Our property type (mapped to Casafari)
            operation: "sale" or "rent"
            bedrooms: Number of bedrooms (optional)
            bathrooms: Number of bathrooms (optional)
            total_area: Total built m² (optional)
            plot_area: Plot/land m² (optional) - CRITICAL for houses!
            distance_km: Search radius in km (default: 1km)
            count: Max number of comparables (default: 50, API max)
            has_elevator: Listing has elevator (for apartments)
            has_terrace: Listing has terrace
            has_balcony: Listing has balcony
            has_pool: Listing has swimming pool
            has_garage: Listing has garage
            floor_level: Listing floor level
            
        Returns:
            ComparablesResult with market stats and all valid comparables
        """
        if not self.api_token:
            raise ValueError("CASAFARI_API_TOKEN not configured")
        
        # Map property type → list of Casafari types
        casafari_types = PROPERTY_TYPE_MAP.get(
            property_type.lower() if property_type else "apartment",
            ["apartment"],
        )
        
        # Build request payload (correct structure per API docs)
        # condition is ALWAYS "very-good" — see CASAFARI_CONDITION comment above.
        payload = {
            "comparables_count": count,
            "operation": operation,
            "comparables_types": casafari_types,
            "condition": CASAFARI_CONDITION,
            "location_boundary": {
                "circle": {
                    "target_point": {
                        "coordinates": {
                            "latitude": latitude,
                            "longitude": longitude
                        }
                    },
                    "distance": distance_km
                }
            }
        }
        
        # =================================================================
        # HARD FILTERS — define what makes a true comparable
        # =================================================================
        # WHY bedrooms only (no total_area): Dropping area gives us the
        # neighborhood "vibe" — what very-good places sell for per m² —
        # instead of hunting for exact-size clones (which returns ~9 results).
        # We do our own price/m² math downstream: median comp €/m² × listing
        # area = renovated value. This is MORE accurate because price/m² is
        # remarkably consistent across sizes in a neighborhood.
        if bedrooms is not None:
            payload["bedrooms"] = bedrooms
        if plot_area is not None:
            payload["plot_area"] = plot_area
        
        # =================================================================
        # FLOOR CATEGORY — ground floor is a different market
        # =================================================================
        # WHY: Ground floors are cheaper (less light, less privacy, noise).
        # A ground-floor comp is NOT comparable to a 4th-floor flat.
        # We only distinguish ground vs. not-ground — that's the real
        # market split. Middle vs. top doesn't change the calculus enough
        # to justify killing result counts.
        is_house = bool(set(casafari_types) & HOUSE_TYPES)
        
        if is_house:
            payload["floors"] = ["no_floor", "ground"]
        elif floor_number is not None and floor_number >= 1:
            if floor_number <= 1:
                payload["floors"] = ["ground"]
            else:
                payload["floors"] = ["middle", "top"]
        elif floor_level:
            if floor_level.lower() == "ground":
                payload["floors"] = ["ground"]
            else:
                # intermediate, top, etc. — all "not ground"
                payload["floors"] = ["middle", "top"]
        
        # =================================================================
        # ELEVATOR — category-defining for upper floors
        # =================================================================
        # WHY: A 4th floor walk-up is a fundamentally different product
        # than a 4th floor with lift. This isn't a preference — it defines
        # the market segment. A walk-up buyer is not the same buyer as a
        # lift-building buyer.
        # Only applies to upper floors (ground floor doesn't need a lift).
        must_have = []
        is_upper_floor = (
            (floor_number is not None and floor_number >= 2)
            or (floor_level and floor_level.lower() in ("intermediate", "top"))
        )
        if not is_house and is_upper_floor and has_elevator is True:
            must_have.append("elevator")
        
        # =================================================================
        # SOFT PREFERENCES — features the listing HAS
        # =================================================================
        # WHY nice_to_have (not must_have): Casafari ranks by these but
        # won't filter them out, so we get the full pool.
        # WHY only features the listing HAS: If the listing has NO balcony
        # and we mention balcony, Casafari will prefer comps WITH balconies
        # which are more expensive → upward price skew.
        nice_to_have = []
        
        if has_terrace is True:
            nice_to_have.append("terrace")
        if has_balcony is True:
            nice_to_have.append("balcony")
        if has_pool is True:
            nice_to_have.append("swimming_pool")
        if has_garage is True:
            nice_to_have.append("garage")
        if has_garden is True:
            nice_to_have.append("garden")
        if has_storage is True:
            nice_to_have.append("storage")
        if has_parking is True:
            nice_to_have.append("parking")
        
        characteristics = {}
        if must_have:
            characteristics["must_have"] = must_have
        if nice_to_have:
            characteristics["nice_to_have"] = nice_to_have
        if characteristics:
            payload["characteristics"] = characteristics
        
        # NOTE: bathrooms, orientation, and energy_ratings are intentionally
        # NOT sent. They killed result counts without meaningfully improving
        # comparable quality (Madrid 2km: 50 → 9 with all filters on).
        
        async def fetch_for_radius(distance_km_for_request: float) -> Dict[str, Any]:
            payload["location_boundary"]["circle"]["distance"] = distance_km_for_request

            logger.info(
                f"🏠 Casafari search: {casafari_types} @ ({latitude}, {longitude}), "
                f"{distance_km_for_request}km radius"
            )
            floor_info = payload.get("floors", "any")
            logger.info(
                f"   📊 Hard filters: {bedrooms}bd, {total_area}m² built, "
                f"{plot_area}m² plot | floors={floor_info} | condition={CASAFARI_CONDITION}"
            )
            logger.info(f"   🔒 Must have: {must_have}")
            logger.info(f"   🏷️ Nice to have: {nice_to_have}")
            logger.debug(f"Payload: {payload}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{CASAFARI_BASE_URL}/comparables/search",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code == 401:
                    raise ValueError("Casafari authentication failed - check API token")
                if response.status_code == 403:
                    raise ValueError("Casafari access forbidden - check permissions")

                response.raise_for_status()
                return response.json()

        radius_used_km = float(distance_km)
        data = await fetch_for_radius(radius_used_km)
        first_pass_count = len(data.get("results", []))

        # Auto-expand radius for dense city markets (Spain): 1km → 2km when too few comps.
        if radius_used_km <= 1.0 and first_pass_count <= 5:
            logger.info(
                f"🔁 Casafari low sample at {radius_used_km}km "
                f"({first_pass_count} comps) → retrying at 2.0km"
            )
            radius_used_km = 2.0
            data = await fetch_for_radius(radius_used_km)

        # Gemini Pro radius advisor: if 2km still returned 0, ask Gemini
        # what radius makes sense for this location. Rural villages need
        # 10-20km to find comps; cities never reach this code path.
        second_pass_count = len(data.get("results", []))
        if second_pass_count == 0 and radius_used_km >= 2.0:
            gemini_radius = await _gemini_suggest_radius(
                latitude=latitude,
                longitude=longitude,
                property_type=property_type,
                bedrooms=bedrooms,
                current_radius_km=radius_used_km,
            )
            if gemini_radius and gemini_radius > radius_used_km:
                logger.info(
                    f"🧠 Gemini suggested radius={gemini_radius}km for "
                    f"({latitude}, {longitude}) — retrying Casafari"
                )
                radius_used_km = gemini_radius
                data = await fetch_for_radius(radius_used_km)

        logger.info(
            f"✅ Casafari returned {len(data.get('results', []))} comparables "
            f"(radius_used_km={radius_used_km})"
        )
        
        # Parse market stats
        # CRITICAL: Casafari returns null (not missing key) for statistics/estimated_prices
        # when 0 comparables are found. dict.get("key", {}) returns None when key exists
        # with value None, so we must use `or {}` to handle this.
        stats = data.get("statistics") or {}
        prices = data.get("estimated_prices") or {}
        
        market_stats = MarketStats(
            average_price=stats.get("average_price", 0),
            average_price_per_sqm=stats.get("average_price_per_sqm", 0),
            average_days_on_market=stats.get("average_time_on_the_market", 0),
            sold_last_6_months=stats.get("sold_or_rented_in_last_six_months", 0),
            fast_sell_price=prices.get("fast_sell_price", 0),
            fair_market_price=prices.get("fair_market_price", 0),
            out_of_market_price=prices.get("out_of_market_price", 0),
            casafari_link=data.get("casafari_link", "")
        )
        
        # Parse ALL comparables — keep every valid one, sorted by distance.
        # NO bucketing. We paid for them; use them all.
        comparables = self._parse_all_comparables(data.get("results", []))
        
        return ComparablesResult(
            market_stats=market_stats,
            comparables=comparables,
            raw_response=data
        )
    
    def _parse_all_comparables(
        self,
        results: List[Dict],
    ) -> List[ComparableProperty]:
        """
        Parse all Casafari results into ComparableProperty objects.
        
        - Drops new-builds (skew renovation pricing)
        - Drops zero-price entries
        - Keeps EVERYTHING else, sorted closest-first
        
        No bucketing, no artificial limits. We paid for these comps —
        use them all for the most accurate pricing.
        """
        comparables: List[ComparableProperty] = []
        skipped_new = 0
        skipped_no_price = 0
        
        for prop in results:
            # Drop new-builds — they skew renovation pricing completely
            prop_condition = (prop.get("condition") or "").lower().strip()
            if prop_condition == "new":
                skipped_new += 1
                continue

            price = prop.get("sale_price") or prop.get("rent_price") or 0
            if price <= 0:
                skipped_no_price += 1
                continue
            
            photos_full = prop.get("pictures", []) or []
            photos_thumbnails = prop.get("thumbnails", []) or []
            photos = photos_thumbnails or photos_full
            coords = prop.get("coordinates", {})
            features = prop.get("features", {})
            
            comparables.append(ComparableProperty(
                property_id=prop.get("property_id", 0),
                price_bucket="comparable",
                sale_price=price,
                price_per_sqm=prop.get("sale_price_per_sqm") or prop.get("rent_price_per_sqm") or 0,
                total_area=prop.get("total_area"),
                living_area=prop.get("living_area"),
                plot_area=prop.get("plot_area"),
                bedrooms=prop.get("bedrooms"),
                bathrooms=prop.get("bathrooms"),
                condition=prop.get("condition"),
                construction_year=prop.get("construction_year"),
                energy_rating=prop.get("energy_rating"),
                distance_km=prop.get("distance", 0),
                address=prop.get("address"),
                property_url=prop.get("property_url", ""),
                photo_urls=photos,
                photo_urls_full=photos_full,
                photo_urls_thumbnails=photos_thumbnails,
                coordinates=coords,
                features=features,
                property_type=prop.get("type")
            ))
        
        # Sort by distance — closest first
        comparables.sort(key=lambda c: c.distance_km)
        
        if skipped_new:
            logger.info(f"🚫 Dropped {skipped_new} new-build comps")
        if skipped_no_price:
            logger.info(f"🚫 Dropped {skipped_no_price} zero-price comps")
        logger.info(
            f"📊 Keeping ALL {len(comparables)} valid comps, sorted by distance"
        )
        
        return comparables
    
    async def get_property_types(self) -> List[Dict]:
        """Get available property types from Casafari."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CASAFARI_BASE_URL}/references/types",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("types", [])
    
    async def get_conditions(self) -> List[str]:
        """Get available property conditions from Casafari."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CASAFARI_BASE_URL}/references/conditions",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("conditions", [])


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

async def search_comparables(
    latitude: float,
    longitude: float,
    property_type: str = "apartment",
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    total_area: Optional[int] = None,
    plot_area: Optional[int] = None,  # CRITICAL for houses!
    distance_km: float = 1.0,
    energy_ratings: Optional[List[str]] = None,
    # LISTING FEATURES - pass these for TRUE comparables!
    has_elevator: Optional[bool] = None,
    has_terrace: Optional[bool] = None,
    has_balcony: Optional[bool] = None,
    has_pool: Optional[bool] = None,
    has_garage: Optional[bool] = None,
    has_garden: Optional[bool] = None,
    has_storage: Optional[bool] = None,
    has_parking: Optional[bool] = None,
    floor_level: Optional[str] = None,
    floor_number: Optional[int] = None,
    is_exterior: Optional[bool] = None,
) -> ComparablesResult:
    """
    Convenience function to search comparables.
    
    Condition is ALWAYS "very-good" (hardcoded). Do NOT add a condition param.
    Default radius is 1km — auto-expands to 2km if fewer than 5 comps found.
    """
    client = CasafariClient()
    return await client.search_comparables(
        latitude=latitude,
        longitude=longitude,
        property_type=property_type,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        total_area=total_area,
        plot_area=plot_area,
        distance_km=distance_km,
        energy_ratings=energy_ratings,
        has_elevator=has_elevator,
        has_terrace=has_terrace,
        has_balcony=has_balcony,
        has_pool=has_pool,
        has_garage=has_garage,
        has_garden=has_garden,
        has_storage=has_storage,
        has_parking=has_parking,
        floor_level=floor_level,
        floor_number=floor_number,
        is_exterior=is_exterior,
    )


# =============================================================================
# 2-CALL STRATEGY FOR FULL PHOTOS
# =============================================================================

async def fetch_comparables_with_full_photos(
    latitude: float,
    longitude: float,
    property_type: str = "apartment",
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    total_area: Optional[int] = None,
    plot_area: Optional[int] = None,
    distance_km: float = 1.0,
    count: int = 50,
    energy_ratings: Optional[List[str]] = None,
    # All listing features for TRUE comparables
    has_elevator: Optional[bool] = None,
    has_terrace: Optional[bool] = None,
    has_balcony: Optional[bool] = None,
    has_pool: Optional[bool] = None,
    has_garage: Optional[bool] = None,
    has_garden: Optional[bool] = None,
    has_storage: Optional[bool] = None,
    has_parking: Optional[bool] = None,
    floor_level: Optional[str] = None,
    floor_number: Optional[int] = None,
    is_exterior: Optional[bool] = None,
) -> ComparablesResult:
    """
    Fetch comparables with FULL-SIZE photos.

    Casafari now returns `pictures[]` (full-res) directly in the comparables response.
    We only use the comparables response and never call the listings API.

    /v1/comparables/search
        → Returns property info + pictures[] per comparable
        → We use pictures[] when present, otherwise keep thumbnails[]
    
    Returns:
        ComparablesResult with full-size photos in each comparable's photo_urls
    """
    client = CasafariClient()
    
    if not client.api_token:
        raise ValueError("CASAFARI_API_TOKEN not configured")
    
    # CALL 1: Standard comparables search with ALL filters
    logger.info("📞 CALL 1: Fetching comparables...")
    result = await client.search_comparables(
        latitude=latitude,
        longitude=longitude,
        property_type=property_type,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        total_area=total_area,
        plot_area=plot_area,
        distance_km=distance_km,
        count=count,
        energy_ratings=energy_ratings,
        # All listing features
        has_elevator=has_elevator,
        has_terrace=has_terrace,
        has_balcony=has_balcony,
        has_pool=has_pool,
        has_garage=has_garage,
        has_garden=has_garden,
        has_storage=has_storage,
        has_parking=has_parking,
        floor_level=floor_level,
        floor_number=floor_number,
        is_exterior=is_exterior,
    )
    
    raw_results = result.raw_response.get("results", [])
    property_full_photos = {}  # Map property_id -> pictures[]
    
    for prop in raw_results:
        property_id = prop.get("property_id")
        pictures = prop.get("pictures") or []
        if property_id and pictures:
            property_full_photos[property_id] = pictures
    
    if property_full_photos:
        logger.info(f"✅ Comparables response includes full photos | listings={len(property_full_photos)}")
        for comp in result.comparables:
            full_photos = property_full_photos.get(comp.property_id)
            if full_photos:
                comp.photo_urls_full = full_photos
        return result
    
    logger.warning("⚠️ Comparables response missing pictures[] - using thumbnails")
    return result


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print(f"CASAFARI_API_TOKEN: {'✓ Set' if CASAFARI_API_TOKEN else '✗ Not set'}")
        
        if not CASAFARI_API_TOKEN:
            print("Add CASAFARI_API_TOKEN to .env.local")
            return
        
        # Test with Barcelona coordinates
        result = await search_comparables(
            latitude=41.3851,
            longitude=2.1734,
            property_type="apartment",
            bedrooms=3,
            distance_km=1.0
        )
        
        print(f"\n📊 Market Stats:")
        print(f"  Average price: €{result.market_stats.average_price:,}")
        print(f"  Average €/m²: €{result.market_stats.average_price_per_sqm:,}")
        print(f"  Days on market: {result.market_stats.average_days_on_market}")
        print(f"\n💰 Price Estimates:")
        print(f"  Fast sell: €{result.market_stats.fast_sell_price:,}")
        print(f"  Fair market: €{result.market_stats.fair_market_price:,}")
        print(f"  Out of market: €{result.market_stats.out_of_market_price:,}")
        print(f"\n🏠 Comparables ({len(result.comparables)}):")
        for comp in result.comparables:
            print(f"  €{comp.sale_price:,} - {comp.total_area}m² - {comp.distance_km:.1f}km - {comp.condition}")
    
    asyncio.run(test())

