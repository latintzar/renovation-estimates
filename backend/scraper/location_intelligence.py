"""
🌍 GEMINI LOCATION INTELLIGENCE
===============================

AI-powered location resolution using Gemini.
Takes ALL listing data and determines the most precise location possible.

Features:
- Works for ANY country/language
- Cross-references ALL data: title, description, breadcrumbs, address fields, URL, reference
- Validates coordinates against extracted address
- Returns resolution level (res_10 to res_0) + confidence
- NO hardcoded rules - pure AI reasoning

Resolution Levels:
- res_10: Full address with street number (highest precision)
- res_9:  Street name without number
- res_8:  Neighborhood/district level
- res_7:  Zone/area level
- res_6:  City level
- res_5:  Region/province level
- res_4:  Country only
- res_0:  Unknown (no location data)

Usage:
    from scraper.location_intelligence import resolve_location
    
    result = await resolve_location(scraped_data, html=raw_html)
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", '')
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = "gemini-2.5-flash"  # Fast + accurate

_client = None

def get_client():
    """Get or create Vertex AI Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
    return _client


# =============================================================================
# RESPONSE SCHEMA
# =============================================================================

LOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        # Resolved Address Components
        "address": {
            "type": "string",
            "description": "Best formatted address string from all available data"
        },
        "street_name": {
            "type": "string",
            "description": "Street name without number (e.g., 'Gran Vía', 'Rue de Rivoli')"
        },
        "street_number": {
            "type": "string",
            "description": "Street/building number only"
        },
        "neighborhood": {
            "type": "string",
            "description": "Neighborhood, district, or barrio"
        },
        "city": {
            "type": "string",
            "description": "City name"
        },
        "region": {
            "type": "string",
            "description": "State, province, or region"
        },
        "postal_code": {
            "type": "string",
            "description": "Postal/ZIP code"
        },
        "country": {
            "type": "string",
            "description": "Country name"
        },
        
        # Coordinates
        "lat": {
            "type": "number",
            "description": "Latitude if found and validated. Null if suspicious or not found."
        },
        "lng": {
            "type": "number",
            "description": "Longitude if found and validated. Null if suspicious or not found."
        },
        "coords_validated": {
            "type": "boolean",
            "description": "True if coordinates appear legitimate and match the address context"
        },
        "coords_source": {
            "type": "string",
            "enum": ["map_embed", "json_ld", "data_attribute", "script_variable", "none"],
            "description": "Where the coordinates were found in the page"
        },
        "coords_rejection_reason": {
            "type": "string",
            "description": "If coordinates rejected, explain why (e.g., 'city center default', 'null island', 'mismatch with address')"
        },
        
        # Resolution
        "resolution": {
            "type": "string",
            "enum": ["res_10", "res_9", "res_8", "res_7", "res_6", "res_5", "res_4", "res_0"],
            "description": "Precision level: res_10=full address, res_9=street only, res_8=neighborhood, res_6=city, res_0=unknown"
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score 0.0 to 1.0"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of how location was determined and why this resolution level"
        },
    },
    "required": ["resolution", "confidence", "reasoning"]
}


# =============================================================================
# SYSTEM INSTRUCTIONS
# =============================================================================

LOCATION_SYSTEM_PROMPT = """You are a Location Intelligence Agent. Your job is to determine the MOST PRECISE location possible for a property listing by analyzing ALL available data.

## YOUR MISSION

Given listing data (title, description, address fields, URL, reference number, coordinates, etc.), determine:
1. The best formatted address possible
2. Whether any coordinates found are legitimate
3. The resolution level (how precise the location is)
4. Your confidence in the result

## RESOLUTION LEVELS

- **res_10**: Full address with street number (e.g., "123 Main Street, Apt 4B, Brooklyn, NY")
  - You have: street name + number + city
  - Confidence: High if multiple sources agree

- **res_9**: Street name only, no number (e.g., "Main Street, Brooklyn, NY")
  - You have: street name + city, but no specific number
  - Common when privacy-hiding exact address

- **res_8**: Neighborhood/district level (e.g., "Williamsburg, Brooklyn, NY")
  - You have: neighborhood + city
  - Street not specified or too vague

- **res_7**: Zone/area within city (e.g., "North Brooklyn, NY")
  - Vague area reference, not a specific neighborhood

- **res_6**: City level only (e.g., "Brooklyn, NY")
  - Only city is known, no sub-city detail

- **res_5**: Region/province only (e.g., "New York State")
  - Only region known

- **res_4**: Country only
  - Only country is determinable

- **res_0**: Unknown
  - Cannot determine any location

## COORDINATE VALIDATION (CRITICAL!)

Coordinates found in listings are OFTEN wrong. You MUST validate them intelligently:

### SUSPICIOUS coordinates to investigate:
1. **Famous landmark coordinates**: Exact coords of Puerta del Sol, Times Square, Eiffel Tower, etc.
2. **Null Island**: (0, 0) or very close to it
3. **Very round numbers**: Like (40.0, -3.0) with 1-2 decimal places only
4. **Country/region center**: Geographic center points
5. **Mismatch**: Coords in different city/country than address mentions

### BUT WAIT - The property COULD actually be in the city center!

**DO NOT auto-reject city center coords if:**
1. The listing SAYS it's in the center: "Centro", "Downtown", "City Center", "Casco Antiguo", "Old Town"
2. The neighborhood mentioned IS central: "Sol", "Gran Vía", "Soho", "Marais", "Mitte"
3. Description mentions central location: "heart of the city", "walking distance to everything"
4. The coordinates have GOOD PRECISION (4+ decimals) and aren't exactly on a landmark

### Decision logic:
```
IF coords are near famous landmark:
  IF listing mentions central location OR neighborhood is central:
    → ACCEPT with note "Central location corroborated by listing data"
  ELSE IF coords are EXACTLY on landmark (< 50m):
    → REJECT as "Likely default - no central location mentioned in listing"
  ELSE:
    → ACCEPT with lower confidence
```

### ACCEPT coordinates if:
1. They match the general area mentioned in the listing
2. They have good precision (4+ decimal places)
3. Multiple location hints corroborate the area
4. For central locations: the listing explicitly mentions being central

## DATA SOURCES TO CROSS-REFERENCE

1. **Title**: Often contains location ("Apartment in Tribeca", "Piso en Chamberí")
2. **Description**: May mention neighborhood, landmarks, metro stations
3. **Address field**: Explicit address if provided
4. **URL**: Often contains location slugs ("/brooklyn/", "/madrid/")
5. **Reference number**: Sometimes contains postal codes
6. **Breadcrumbs**: Navigation path often shows location hierarchy
7. **Map coordinates**: lat/lng from map embeds (validate carefully!)
8. **Agency location**: Sometimes indicates property's general area
9. **Nearby amenities mentioned**: "5 min from X metro", "near Central Park"

## OUTPUT RULES

1. **Err on the side of caution**: If unsure between res_8 and res_6, choose res_6
2. **Explain your reasoning**: Always explain WHY you chose this resolution
3. **Reject suspicious coordinates**: Better to have no coords than wrong ones
4. **Use null, not empty string**: For missing values, use null
5. **Country is required**: If you can determine ANY location, determine the country
6. **Confidence reflects uncertainty**: Multiple agreeing sources = high confidence

## EXAMPLES

### Example 1: High precision
Data: title="Piso en Calle Serrano 45, Salamanca, Madrid", address="Calle Serrano 45, 4º Izq", city="Madrid"
→ resolution: "res_10", address: "Calle Serrano 45, Salamanca, Madrid", confidence: 0.95

### Example 2: Street without number
Data: title="Apartment on 5th Avenue, NYC", description="Beautiful views of Central Park"
→ resolution: "res_9" (no specific number), address: "5th Avenue, New York, NY", confidence: 0.8

### Example 3: Neighborhood only (common!)
Data: title="Piso en venta en Chamberí", city="Madrid", no street in any field
→ resolution: "res_8", neighborhood: "Chamberí", city: "Madrid", confidence: 0.85

### Example 4: Suspicious coordinates - REJECTED
Data: lat=40.4168, lng=-3.7038, city="Madrid", neighborhood="Chamberí"
→ coords_validated: false, coords_rejection_reason: "Coords at Puerta del Sol but listing says Chamberí (different area)"

### Example 5: City center coords - ACCEPTED (listing confirms central location!)
Data: lat=40.4170, lng=-3.7035, neighborhood="Sol", description="En pleno centro de Madrid, junto a la Puerta del Sol"
→ coords_validated: true, reasoning: "Central location explicitly mentioned, neighborhood is Sol"

### Example 6: Near city center with good precision - ACCEPTED
Data: lat=40.4195, lng=-3.7012, neighborhood="Centro", description="Piso reformado en el corazón de Madrid"
→ coords_validated: true, reasoning: "Good precision (4 decimals), listing confirms central Madrid location"

REMEMBER: Your job is to extract the MAXIMUM location precision available while being INTELLIGENT about coordinate validity. 
- Don't blindly reject city center coords - check if the listing confirms central location
- Don't blindly accept any coords - verify they match the mentioned area
- Better to say res_8 with high confidence than res_10 with low confidence.
"""


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def resolve_location(
    data: Dict[str, Any],
    html: Optional[str] = None,
    max_html_chars: int = 15000,
) -> Dict[str, Any]:
    """
    Use Gemini to determine the most precise location from ALL available data.
    
    Args:
        data: Scraped listing data (all fields)
        html: Optional raw HTML for additional context (truncated)
        max_html_chars: Max HTML chars to include
    
    Returns:
        Dict with resolved location:
        - address, street_name, street_number, neighborhood, city, region, postal_code, country
        - lat, lng, coords_validated, coords_source
        - resolution, confidence, reasoning
    """
    logger.info("🌍 Gemini Location Intelligence analyzing...")
    
    # Build context for Gemini
    context_parts = []
    
    # 1. All extracted data fields
    description = data.get("description") or ""
    relevant_fields = {
        "title": data.get("title"),
        "description": description[:1000] if description else None,  # First 1000 chars
        "address": data.get("address"),
        "street_name": data.get("street_name"),
        "street_number": data.get("street_number"),
        "neighborhood": data.get("neighborhood"),
        "city": data.get("city"),
        "region": data.get("region"),
        "postal_code": data.get("postal_code"),
        "country": data.get("country"),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "reference": data.get("reference"),
        "source_url": data.get("source_url"),
    }
    
    # Remove None values for cleaner prompt
    relevant_fields = {k: v for k, v in relevant_fields.items() if v is not None}
    
    context_parts.append("## EXTRACTED DATA\n```json\n" + json.dumps(relevant_fields, indent=2, ensure_ascii=False) + "\n```")
    
    # 2. Include truncated HTML if provided (for breadcrumbs, hidden data, etc.)
    if html and len(html) > 100:
        # Focus on likely location-containing sections
        html_excerpt = html[:max_html_chars]
        context_parts.append(f"\n## RAW HTML (first {max_html_chars} chars)\n```html\n{html_excerpt}\n```")
    
    prompt = "\n".join(context_parts) + "\n\n## TASK\nAnalyze ALL the data above and determine the most precise location possible. Validate any coordinates found. Return the resolved location with your confidence level."
    
    try:
        client = get_client()
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=LOCATION_SYSTEM_PROMPT,
                temperature=0.1,  # Low temp for accuracy
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=LOCATION_SCHEMA,
            ),
        )
        
        if not response.text:
            logger.error("❌ Gemini returned empty response for location")
            return _empty_result("Gemini returned empty response")
        
        result = json.loads(response.text)
        
        # Log result
        logger.info(f"   📍 Resolution: {result.get('resolution')} | Confidence: {result.get('confidence', 0):.2f}")
        logger.info(f"   📍 Address: {result.get('address', 'None')}")
        if result.get('coords_validated'):
            logger.info(f"   📍 Coords: ({result.get('lat')}, {result.get('lng')}) ✓")
        elif result.get('coords_rejection_reason'):
            logger.info(f"   📍 Coords rejected: {result.get('coords_rejection_reason')}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error in location response: {e}")
        return _empty_result(f"JSON parse error: {e}")
    except Exception as e:
        logger.error(f"❌ Location intelligence error: {e}")
        return _empty_result(str(e))


def _empty_result(reason: str) -> Dict[str, Any]:
    """Return empty result on error."""
    return {
        "address": None,
        "street_name": None,
        "street_number": None,
        "neighborhood": None,
        "city": None,
        "region": None,
        "postal_code": None,
        "country": None,
        "lat": None,
        "lng": None,
        "coords_validated": False,
        "coords_source": "none",
        "resolution": "res_0",
        "confidence": 0.0,
        "reasoning": f"Error: {reason}",
    }


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

async def enrich_with_location(
    data: Dict[str, Any],
    html: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich scraped data with AI-resolved location.
    Modifies dict in place and returns it.
    
    Args:
        data: Scraped listing data
        html: Optional raw HTML for additional context
    
    Returns:
        Same dict with enriched location fields
    """
    resolved = await resolve_location(data, html=html)
    
    # Update data with resolved location (only if we got something)
    if resolved.get("resolution") != "res_0":
        # Address components (only update if resolved has value)
        if resolved.get("address"):
            data["address"] = resolved["address"]
        if resolved.get("street_name"):
            data["street_name"] = resolved["street_name"]
        if resolved.get("street_number"):
            data["street_number"] = resolved["street_number"]
        if resolved.get("neighborhood"):
            data["neighborhood"] = resolved["neighborhood"]
        if resolved.get("city"):
            data["city"] = resolved["city"]
        if resolved.get("region"):
            data["region"] = resolved["region"]
        if resolved.get("postal_code"):
            data["postal_code"] = resolved["postal_code"]
        if resolved.get("country"):
            data["country"] = resolved["country"]
        
        # Coordinates (only if validated)
        if resolved.get("coords_validated") and resolved.get("lat") and resolved.get("lng"):
            data["lat"] = resolved["lat"]
            data["lng"] = resolved["lng"]
            data["coords_validated"] = True
            data["coords_source"] = resolved.get("coords_source")
        elif not resolved.get("coords_validated"):
            # Clear potentially bad coordinates
            data["lat"] = None
            data["lng"] = None
            data["coords_validated"] = False
            data["coords_source"] = None
    
    # Always set resolution info
    data["address_resolution"] = resolved.get("resolution", "res_0")
    data["address_confidence"] = resolved.get("confidence", 0.0)
    
    return data


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_data = {
            "title": "Beautiful apartment in Williamsburg, Brooklyn",
            "description": "2BR/1BA in the heart of Williamsburg. Walking distance to Bedford Ave L train.",
            "city": "New York",
            "lat": 40.7128,  # This is lower Manhattan - suspicious!
            "lng": -74.0060,
            "source_url": "https://example.com/brooklyn/williamsburg/listing-123",
        }
        
        result = await resolve_location(test_data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())

