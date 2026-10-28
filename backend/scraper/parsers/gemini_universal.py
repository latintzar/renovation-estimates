"""
🎯 ULTIMATE UNIVERSAL PROPERTY PARSER - Gemini 2.5 Flash
========================================================

THE SINGLE SOURCE OF TRUTH for AI-powered property extraction.
Works with ANY real estate website in ANY language.

Features:
- Complete ListingEditor-compatible output schema (ALL fields)
- Hi-res image extraction (srcset, data-src, gallery arrays)
- Structured JSON response with response_schema
- TRUE MULTILINGUAL: Works in 100+ languages (Spanish, English, German, 
  French, Portuguese, Italian, Dutch, Catalan, Polish, Russian, Turkish, 
  Arabic, Hebrew, Japanese, Chinese, Korean, Thai, Vietnamese, Greek, 
  Czech, Hungarian, Romanian, Swedish, Norwegian, Danish, Finnish, etc.)
- Lat/lng extraction from all common hiding spots
- Cost: ~$0.001-0.003 per extraction
  ($0.15/M input tokens, $0.60/M output tokens)

Usage:
    from scraper.parsers.gemini_universal import extract_property_data
    
    result = await extract_property_data(html, url)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Use Vertex AI (OAuth2) instead of AI Studio (API key)
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Vertex AI configuration (uses Application Default Credentials)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", '')
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = "gemini-2.5-flash"  # Best balance: $0.15/M in, $0.60/M out - handles all fields reliably

# Initialize Vertex AI client
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
# RESPONSE SCHEMA (Matches ListingEditor + Cheerio Selectors for future reuse)
# =============================================================================

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        # === CORE INFO ===
        "title": {
            "type": "string",
            "description": "Property title/headline. Clean, without 'for sale/rent' prefixes."
        },
        "description": {
            "type": "string",
            "description": "Full property description. Deduplicated, clean text."
        },
        "price_eur": {
            "type": "integer",
            "description": "Price in euros as integer (no decimals). Null if 'price on request'."
        },
        
        # === SIZE ===
        "bedrooms": {
            "type": "integer",
            "description": "Number of bedrooms (0 for studios)"
        },
        "bathrooms": {
            "type": "integer", 
            "description": "Number of bathrooms (full + half)"
        },
        "m2_built": {
            "type": "integer",
            "description": "Constructed/built area in m² (superficie construida, área bruta)"
        },
        "m2_useful": {
            "type": "integer",
            "description": "Useful/net area in m² (superficie útil, área útil) - usually smaller"
        },
        "m2_plot": {
            "type": "integer",
            "description": "Plot/land area in m² (superficie de parcela, área terreno). CRITICAL for houses/chalets/villas!"
        },
        
        # === TRANSACTION ===
        "listing_type": {
            "type": "string",
            "enum": ["sale", "rent", "rent_to_own"],
            "description": "Transaction type"
        },
        "price_period": {
            "type": "string",
            "enum": ["total", "month", "week"],
            "description": "For rentals: 'month' or 'week'. For sales: 'total'"
        },
        
        # === LOCATION (Nominatim-compatible) ===
        "address": {
            "type": "string",
            "description": "Full address string (Street Name, Number, City)"
        },
        "street_name": {
            "type": "string",
            "description": "Just the street name (e.g., 'Calle Gran Vía')"
        },
        "street_number": {
            "type": "string",
            "description": "Just the street number (e.g., '42')"
        },
        "neighborhood": {
            "type": "string",
            "description": "Neighborhood/district (e.g., 'Chamberí', 'Eixample')"
        },
        "city": {
            "type": "string",
            "description": "City name"
        },
        "region": {
            "type": "string",
            "description": "State/Province/Autonomous Community"
        },
        "postal_code": {
            "type": "string",
            "description": "Postal/ZIP code"
        },
        "country": {
            "type": "string",
            "description": "Country name (default: Spain)"
        },
        "lat": {
            "type": "number",
            "description": "Latitude coordinate (if found in page)"
        },
        "lng": {
            "type": "number",
            "description": "Longitude coordinate (if found in page)"
        },
        
        # === PROPERTY CLASSIFICATION ===
        "property_subtype": {
            "type": "string",
            "enum": ["flat", "penthouse", "duplex", "studio", "chalet_detached", "chalet_semi", "chalet_terraced", "rustic", "other"],
            "description": "Specific property type"
        },
        "housing_situation": {
            "type": "string",
            "enum": ["free", "rented", "bare_ownership", "squatted", "auction"],
            "description": "Occupancy status. Default: 'free'"
        },
        "ad_origin": {
            "type": "string",
            "enum": ["standard", "bank"],
            "description": "'bank' if bank-owned/foreclosure, else 'standard'"
        },
        "condition": {
            "type": "string",
            "enum": ["new", "good", "renovate"],
            "description": "Property condition"
        },
        "energy_rating": {
            "type": "string",
            "enum": ["A", "B", "C", "D", "E", "F", "G"],
            "description": "Energy efficiency certificate rating (CEE/EPC). Look for 'Certificado Energético', 'Energy Rating', 'Consumo', 'Calificación energética'."
        },
        "construction_year": {
            "type": "integer",
            "description": "Year the property was built. Look for 'Año construcción', 'Built in', 'Baujahr', 'Année de construction'."
        },
        
        # === FLOOR INFO ===
        "floor_level": {
            "type": "string",
            "enum": ["ground", "intermediate", "top"],
            "description": "Floor category"
        },
        "floor_number": {
            "type": "integer",
            "description": "Actual floor number (0 = ground, 1 = first, etc.)"
        },
        
        # === BOOLEAN AMENITIES ===
        "has_elevator": {"type": "boolean"},
        "is_exterior": {"type": "boolean", "description": "True if exterior-facing, False if interior"},
        "has_terrace": {"type": "boolean"},
        "has_balcony": {"type": "boolean"},
        "has_pool": {"type": "boolean"},
        "has_garage": {"type": "boolean"},
        "has_garden": {"type": "boolean"},
        "has_storage": {"type": "boolean", "description": "Trastero/storage room"},
        "has_air_conditioning": {"type": "boolean"},
        "has_wardrobes": {"type": "boolean", "description": "Built-in wardrobes"},
        "is_accessible": {"type": "boolean", "description": "Wheelchair accessible"},
        
        # === ORIENTATIONS ===
        "terrace_orientation": {
            "type": "string",
            "enum": ["north", "south", "east", "west", "unknown"],
            "description": "Terrace compass orientation if mentioned"
        },
        "balcony_orientation": {
            "type": "string",
            "enum": ["north", "south", "east", "west", "unknown"],
            "description": "Balcony compass orientation if mentioned"
        },
        
        # === FEATURES ===
        "features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of property features/characteristics"
        },
        "amenities": {
            "type": "array", 
            "items": {"type": "string"},
            "description": "List of amenities (pool, gym, doorman, etc.)"
        },
        
        # === REFERENCE ===
        "reference": {
            "type": "string",
            "description": "Property reference/ID number"
        },
        
        # === PHOTOS (Critical!) ===
        "image_urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ALL property photo URLs, highest resolution available. EXCLUDE: agent photos, logos, icons, maps, floor plans (unless main content)."
        },
        "main_image_url": {
            "type": "string",
            "description": "Primary/hero image URL"
        },
        
        # === AGENCY/AGENT ===
        "agency_name": {"type": "string"},
        "agency_logo_url": {"type": "string"},
        "agency_phone": {"type": "string"},
        "agency_email": {"type": "string"},
        "agent_name": {"type": "string"},
        "agent_photo_url": {"type": "string"},
        "agent_phone": {"type": "string"},
        "whatsapp": {"type": "string", "description": "WhatsApp number or link"},
        
        # === CHEERIO SELECTORS (For future rule-based extraction) ===
        "cheerio_selectors": {
            "type": "object",
            "description": "CSS selectors or extraction paths for each field. Use cheerio/jQuery syntax. For JS-embedded data, prefix with 'JS:' and describe the pattern.",
            "properties": {
                "title": {"type": "string", "description": "CSS selector for title, e.g., 'h1.property-title' or '.main-info__title-main'"},
                "description": {"type": "string", "description": "CSS selector for description, e.g., '.description-body p'"},
                "price_eur": {"type": "string", "description": "CSS selector for price, e.g., '.price-value' or 'span[data-price]'"},
                "bedrooms": {"type": "string", "description": "CSS selector or pattern, e.g., '.info-features span:nth-child(1)' or 'JS: look for N hab'"},
                "bathrooms": {"type": "string", "description": "CSS selector or pattern for bathrooms"},
                "m2_built": {"type": "string", "description": "CSS selector for built area"},
                "m2_useful": {"type": "string", "description": "CSS selector for useful area"},
                "m2_plot": {"type": "string", "description": "CSS selector for plot/land area (for houses)"},
                "address": {"type": "string", "description": "CSS selector for address"},
                "neighborhood": {"type": "string", "description": "CSS selector for neighborhood"},
                "city": {"type": "string", "description": "CSS selector for city"},
                "lat": {"type": "string", "description": "How lat was found, e.g., 'JSON-LD: geo.latitude' or 'JS: window.__INITIAL_STATE__.lat' or '#map[data-lat]'"},
                "lng": {"type": "string", "description": "How lng was found"},
                "reference": {"type": "string", "description": "CSS selector for reference number"},
                "image_urls": {"type": "string", "description": "CSS selector for images, e.g., '.gallery img[data-src]' or 'JS: fullScreenGalleryPics array'"},
                "agency_name": {"type": "string", "description": "CSS selector for agency name"},
                "agency_phone": {"type": "string", "description": "CSS selector for agency phone"},
                "features": {"type": "string", "description": "CSS selector for features list, e.g., '.features-list li'"},
            }
        },
    },
    "required": ["title", "listing_type"]
}

# =============================================================================
# SYSTEM INSTRUCTIONS (The "Brain")
# =============================================================================

SYSTEM_INSTRUCTIONS = """You are an expert real estate data extractor. Your job is to parse property listing HTML and extract structured data that matches our database schema EXACTLY.

## CORE PRINCIPLES

1. **ACCURACY OVER COMPLETENESS**: Only extract what you're confident about. Use null for uncertain fields.
2. **TRUE MULTILINGUAL**: You understand ANY language - Spanish, English, German, French, Portuguese, Italian, Dutch, Catalan, Polish, Russian, Turkish, Arabic, Hebrew, Japanese, Chinese, Korean, Thai, Vietnamese, Greek, Czech, Hungarian, Romanian, Swedish, Norwegian, Danish, Finnish, and more. Extract data regardless of the language used on the page.
3. **CLEAN DATA**: Remove HTML entities, excessive whitespace, duplicate content.
4. **HIGHEST RESOLUTION IMAGES**: Always prefer largest available image size.
5. **SEMANTIC UNDERSTANDING**: Don't rely on exact keyword matching. Understand the MEANING of text to identify bedrooms, bathrooms, prices, etc. even in languages not explicitly listed below.

## FIELD-SPECIFIC GUIDANCE

**IMPORTANT**: The examples below use common European languages, but you should apply the same logic to ANY language. For example:
- Japanese: 寝室 (bedrooms), 浴室 (bathrooms), 平米 (m²)
- Arabic: غرف نوم (bedrooms), حمامات (bathrooms)
- Russian: спальни (bedrooms), ванные (bathrooms), м² (m²)
- Chinese: 卧室 (bedrooms), 浴室 (bathrooms), 平方米 (m²)
- Turkish: yatak odası (bedrooms), banyo (bathrooms)
- Polish: sypialnie (bedrooms), łazienki (bathrooms)

Use your semantic understanding to identify these concepts in ANY language.

### PRICES
- Extract numeric value only (no currency symbols: €, $, £, ¥, ₽, zł, etc.)
- Handle different number formats:
  - European: 250.000 or 250 000 → 250000
  - US/UK: 250,000 → 250000
  - Indian: 25,00,000 → 2500000
- "Precio a consultar" / "Price on request" / "POA" / "На запрос" / "価格応相談" → null
- For rentals, detect monthly/weekly in any language

### AREAS (m²) - CRITICAL FOR HOUSES!
- m2_built = "superficie construida" / "área bruta" / "built area" / "gross area" / "Wohnfläche"
- m2_useful = "superficie útil" / "área útil" / "usable area" / "net area" (usually smaller)
- m2_plot = "superficie parcela" / "área terreno" / "plot area" / "land area" / "Grundstücksfläche"
  → This is CRITICAL for houses/chalets/villas! A 130m² house on 400m² land is very different from an apartment.
- Convert: 1000 ft² ≈ 93 m²

### PROPERTY SUBTYPES (Multilingual mapping)
| Output Value | Keywords |
|--------------|----------|
| flat | piso, apartamento, flat, apartment, Wohnung, appartement |
| penthouse | ático, penthouse, Dachwohnung, attique |
| duplex | dúplex, duplex, Maisonette |
| studio | estudio, studio, loft, Einzimmerwohnung |
| chalet_detached | chalet independiente, villa, detached, Einfamilienhaus, maison individuelle |
| chalet_semi | chalet pareado, semi-detached, Doppelhaushälfte |
| chalet_terraced | chalet adosado, adosado, terraced, Reihenhaus |
| rustic | finca rústica, country house, Landhaus |

### HOUSING SITUATION
| Output Value | Keywords |
|--------------|----------|
| free | (default - property is vacant/available) |
| rented | alquilado, con inquilinos, rented, with tenants, vermietet |
| bare_ownership | nuda propiedad, bare ownership, Nießbrauch |
| squatted | okupado, squatted, besetzt |
| auction | subasta, auction, Versteigerung |

### AD ORIGIN
- "bank" → if: "de banco", "bank owned", "procedente de entidad bancaria", "foreclosure"
- "standard" → everything else

### CONDITION
| Output Value | Keywords |
|--------------|----------|
| new | obra nueva, new build, new construction, Neubau, a estrenar |
| renovate | a reformar, para reformar, to renovate, needs work, renovierungsbedürftig |
| good | buen estado, good condition, (default) |

### FLOOR LEVEL
- "ground" → planta baja, bajo, ground floor, Erdgeschoss (floor_number = 0)
- "top" → ático, última planta, top floor, penthouse (highest floor)
- "intermediate" → any numbered floor in between

### BOOLEAN AMENITIES (Keywords to detect)
| Field | Keywords (ES/EN/DE/FR) |
|-------|------------------------|
| has_elevator | ascensor, elevator, lift, Aufzug, ascenseur |
| is_exterior | exterior, außen, extérieur (vs interior) |
| has_terrace | terraza, terrace, Terrasse |
| has_balcony | balcón, balcony, Balkon |
| has_pool | piscina, pool, Schwimmbad, piscine |
| has_garage | garaje, garage, parking, Stellplatz, Parkplatz |
| has_garden | jardín, garden, Garten, jardin |
| has_storage | trastero, storage, cellar, Keller, cave |
| has_air_conditioning | aire acondicionado, A/C, Klimaanlage, climatisation |
| has_wardrobes | armarios empotrados, built-in wardrobes, Einbauschränke |
| is_accessible | accesible, accessible, barrierefrei |

## LAT/LNG EXTRACTION (Check these locations!)

Coordinates are often hidden in:

1. **Map containers**: `data-latitude`, `data-longitude`, `data-lat`, `data-lng`, `data-coords`
2. **JSON-LD**: `"geo": { "latitude": X, "longitude": Y }`
3. **Inline scripts**: 
   - `google.maps.LatLng(lat, lng)`
   - `center: [lng, lat]` (Mapbox - REVERSED order!)
   - `var latitude = X; var longitude = Y;`
4. **Data attributes**: Any element with geo data

**VALIDATION**: For Spain, coordinates should be:
- Mainland: lat [36.0, 43.8], lng [-9.3, 3.3]
- Balearics: lat [38.6, 40.1], lng [1.1, 4.4]  
- Canaries: lat [27.6, 29.5], lng [-18.2, -13.3]

## IMAGE EXTRACTION (Critical for quality!)

**PRIORITY ORDER for highest resolution:**
1. `srcset` attribute → pick LARGEST size (e.g., "image.jpg 1920w")
2. `data-full-src`, `data-zoom-src`, `data-hires` attributes
3. Gallery arrays in `<script>` tags: `fullScreenGalleryPics`, `galleryImages`, `photos`
4. JSON-LD `images` array
5. `data-src` (lazy loading)
6. Regular `src` attribute

**FILTER OUT:**
- Agent/team photos (usually in sidebar or "contact" section)
- Agency logos (small, often SVG or contains "logo" in path)
- Icons, sprites, placeholder images
- Maps (Google Maps tiles, Mapbox)
- Floor plans (unless that's the main listing content)
- Images smaller than 200x200px
- Images with "avatar", "profile", "team", "agent" in URL

**URL HANDLING:**
- Convert relative URLs to absolute using the page URL
- Upgrade HTTP to HTTPS where possible
- Remove query params that downsize (e.g., `?w=100`)
- Look for patterns to get full size: replace `/thumbs/` with `/full/`, `_s.jpg` with `.jpg`

## JSON-LD (Check first - it's structured gold!)

Many sites have `<script type="application/ld+json">` with:
- `@type`: "RealEstateListing", "Product", "Offer", "Apartment", "House"
- Pre-structured: price, address, geo, images, description

ALWAYS check for JSON-LD first before parsing HTML.

## OUTPUT RULES

1. Use `null` for fields not found (don't guess)
2. Booleans: `true`, `false`, or `null` (don't default to false if unsure)
3. Arrays: Empty `[]` if no items found
4. Strings: Clean, trimmed, no HTML entities
5. Numbers: Integers only (no floats except lat/lng)
6. All image URLs must be absolute

## CHEERIO SELECTORS (CRITICAL - Always populate!)

For EVERY field you extract, also provide the CSS selector or extraction path in the `cheerio_selectors` object. This allows us to potentially use rule-based extraction in the future.

**Format for cheerio_selectors:**
- **CSS selector**: Use cheerio/jQuery syntax, e.g., `.property-title h1`, `#price-value`, `span.bedrooms`
- **Attribute extraction**: Add `@attr`, e.g., `img.gallery@data-src`, `#map@data-lat`
- **JSON-LD path**: Prefix with `JSON-LD:`, e.g., `JSON-LD: geo.latitude`, `JSON-LD: offers.price`
- **JavaScript pattern**: Prefix with `JS:`, e.g., `JS: window.__INITIAL_STATE__.property.lat`, `JS: fullScreenGalleryPics array`
- **Text pattern/regex**: Prefix with `TEXT:`, e.g., `TEXT: (\d+)\s*hab` for bedrooms from "3 hab"

**Examples:**
```json
{
  "cheerio_selectors": {
    "title": "h1.main-info__title-main",
    "price_eur": ".info-data-price span",
    "bedrooms": "TEXT: (\\d+)\\s*(?:hab|dorm)",
    "m2_built": ".info-features span:contains('m²')",
    "lat": "JSON-LD: geo.latitude",
    "lng": "#map@data-lng",
    "image_urls": "JS: fullScreenGalleryPics.map(p => p.imageDataService)",
    "features": ".details-property-feature-one li"
  }
}
```

**IMPORTANT**: Always include cheerio_selectors for the main fields you extract. This metadata is valuable for building domain-specific parsers later.
"""

# =============================================================================
# HTML PREPROCESSING
# =============================================================================

def preprocess_html(html: str, url: str) -> tuple[str, List[str], Optional[Dict]]:
    """
    Preprocesses HTML for optimal extraction:
    1. Removes noise (scripts, styles, nav, footer)
    2. Extracts image candidates with resolution hints
    3. Extracts JSON-LD if present
    
    Returns: (cleaned_html, image_candidates, json_ld_data)
    """
    soup = BeautifulSoup(html, "html.parser")
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    
    # 1. Extract JSON-LD first (before we modify soup)
    json_ld_data = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Check if it's property-related
            if isinstance(data, dict):
                ld_type = data.get("@type", "")
                if any(t in str(ld_type).lower() for t in ["realestate", "apartment", "house", "product", "offer", "residence"]):
                    json_ld_data = data
                    break
            elif isinstance(data, list):
                for item in data:
                    ld_type = item.get("@type", "")
                    if any(t in str(ld_type).lower() for t in ["realestate", "apartment", "house", "product", "offer", "residence"]):
                        json_ld_data = item
                        break
        except (json.JSONDecodeError, TypeError):
            continue
    
    # 2. Extract image candidates with resolution analysis
    image_candidates = []
    seen_urls = set()
    
    for img in soup.find_all("img"):
        # Check all possible source attributes
        sources = []
        
        # Srcset (highest priority - has resolution info)
        srcset = img.get("srcset", "")
        if srcset:
            # Parse srcset: "url1 800w, url2 1200w, url3 1920w"
            for part in srcset.split(","):
                part = part.strip()
                if " " in part:
                    src, size = part.rsplit(" ", 1)
                    # Prefer larger sizes
                    width = int(re.search(r"(\d+)", size).group(1)) if re.search(r"(\d+)", size) else 0
                    sources.append((src.strip(), width))
        
        # High-res data attributes
        for attr in ["data-full-src", "data-zoom-src", "data-hires", "data-large", "data-original"]:
            if img.get(attr):
                sources.append((img[attr], 2000))  # Assume high-res
        
        # Regular sources
        for attr in ["data-src", "data-lazy", "src"]:
            if img.get(attr):
                sources.append((img[attr], 800))  # Default priority
        
        # Sort by resolution (highest first) and take best
        sources.sort(key=lambda x: x[1], reverse=True)
        
        for src, _ in sources:
            if not src or src.startswith("data:"):
                continue
            
            # Make absolute URL
            if not src.startswith("http"):
                src = urljoin(url, src)
            
            # Filter out small/unwanted images
            lower_src = src.lower()
            if any(x in lower_src for x in ["logo", "icon", "avatar", "agent", "team", "profile", "sprite", "placeholder", "loading", "pixel", "tracking", "1x1", "spacer"]):
                continue
            
            # Check dimensions if available
            width = int(img.get("width", 0) or 0)
            height = int(img.get("height", 0) or 0)
            if (width > 0 and width < 150) or (height > 0 and height < 150):
                continue
            
            if src not in seen_urls:
                seen_urls.add(src)
                image_candidates.append(src)
                break  # Only take best source per img tag
    
    # Also check for gallery data in scripts
    for script in soup.find_all("script"):
        text = script.string or ""
        # Common gallery patterns
        patterns = [
            r'fullScreenGalleryPics\s*[=:]\s*(\[[\s\S]*?\])',
            r'galleryImages\s*[=:]\s*(\[[\s\S]*?\])',
            r'"images"\s*:\s*(\[[\s\S]*?\])',
            r'photos\s*[=:]\s*(\[[\s\S]*?\])',
            r'propertyImages\s*[=:]\s*(\[[\s\S]*?\])',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Clean JS array to valid JSON
                    arr_str = match.group(1)
                    arr_str = re.sub(r"([{,]\s*)([a-zA-Z_]\w*)\s*:", r'\1"\2":', arr_str)
                    arr_str = arr_str.replace("'", '"')
                    arr = json.loads(arr_str)
                    
                    for item in arr:
                        img_url = item if isinstance(item, str) else (item.get("url") or item.get("src") or item.get("imageDataService") or item.get("fullUrl"))
                        if img_url and img_url not in seen_urls:
                            if not img_url.startswith("http"):
                                img_url = urljoin(url, img_url)
                            seen_urls.add(img_url)
                            image_candidates.append(img_url)
                except (json.JSONDecodeError, TypeError):
                    continue
    
    # 3. Clean HTML for LLM processing
    # Remove noise elements
    for tag in soup.find_all(["script", "style", "svg", "link", "meta", "noscript", "iframe"]):
        tag.decompose()
    
    for tag in soup.find_all(class_=re.compile(r"cookie|popup|modal|banner|ads?-|footer|nav|menu|header|sidebar", re.I)):
        tag.decompose()
    
    # Try to find main content
    main_content = soup.select_one("main, article, .main-content, #main, .listing-detail, .property-details, .ficha-detalle, [itemtype*='RealEstate']")
    
    if main_content:
        cleaned_html = str(main_content)
    else:
        body = soup.find("body")
        cleaned_html = str(body) if body else str(soup)
    
    # Compress whitespace
    cleaned_html = re.sub(r'\s+', ' ', cleaned_html)
    
    # Truncate if too large (Flash handles ~100k tokens)
    if len(cleaned_html) > 80000:
        cleaned_html = cleaned_html[:80000] + "<!-- truncated -->"
    
    return cleaned_html, image_candidates[:50], json_ld_data


# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================

async def extract_property_data(html: str, url: str) -> Dict[str, Any]:
    """
    Extracts property data from HTML using Gemini 2.5 Flash via Vertex AI.
    
    Args:
        html: Raw HTML content of the property listing page
        url: URL of the page (for resolving relative URLs)
    
    Returns:
        Dict with all extracted fields matching ListingEditor schema
    
    Cost: ~$0.001-0.003 per extraction
    """
    logger.info(f"🎯 Universal extraction for: {url}")
    
    # Preprocess
    cleaned_html, image_candidates, json_ld = preprocess_html(html, url)
    logger.info(f"   📝 HTML: {len(cleaned_html)} chars, {len(image_candidates)} images, JSON-LD: {'yes' if json_ld else 'no'}")
    
    # Build prompt
    prompt_parts = [
        f"Extract property listing data from this page.\n\nURL: {url}\n"
    ]
    
    if json_ld:
        prompt_parts.append(f"\n## JSON-LD DATA (Pre-structured):\n```json\n{json.dumps(json_ld, indent=2)[:5000]}\n```\n")
    
    prompt_parts.append(f"\n## IMAGE CANDIDATES (Pre-extracted, verify and filter):\n{json.dumps(image_candidates, indent=2)}\n")
    
    prompt_parts.append(f"\n## HTML CONTENT:\n{cleaned_html}\n")
    
    prompt_parts.append("\n## TASK:\nExtract ALL available fields. For images, use the pre-extracted candidates but filter out non-property photos. Return valid JSON matching the schema.")
    
    prompt = "\n".join(prompt_parts)
    
    try:
        client = get_client()
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                temperature=0.1,
                max_output_tokens=50000,  # No truncation - give Gemini plenty of room
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        
        if not response.text:
            logger.error("❌ Gemini returned empty response")
            return {"error": "Empty response", "source_url": url}
        
        data = json.loads(response.text)
        
        # Add source URL
        data["source_url"] = url
        
        # Log success
        title = data.get("title", "Unknown")[:50] if data.get("title") else "Unknown"
        price = data.get("price_eur", 0)
        images = len(data.get("image_urls", []))
        logger.info(f"   ✅ Extracted: {title}... | {price}€ | {images} photos")
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        # Log the raw response for debugging
        logger.debug(f"Raw response: {response.text[:500] if response.text else 'None'}...")
        return {"error": f"JSON parse error: {e}", "source_url": url}
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return {"error": str(e), "source_url": url}


# =============================================================================
# CONVENIENCE FUNCTION (Drop-in replacement)
# =============================================================================

async def parse_universal(html: str, url: str) -> Dict[str, Any]:
    """
    Drop-in replacement for the old universal parser.
    """
    return await extract_property_data(html, url)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import sys
    
    async def test():
        if len(sys.argv) < 2:
            print("Usage: python gemini_universal.py <url>")
            print("       Reads HTML from stdin")
            return
        
        url = sys.argv[1]
        html = sys.stdin.read()
        
        result = await extract_property_data(html, url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())

