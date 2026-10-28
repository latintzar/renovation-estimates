"""
Idealista Parser - Full Schema Extraction
Uses cheerio-style parsing with BeautifulSoup
Ported from src/lib/extraction/adapters/server.ts
"""

import re
import json
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import logging

from scraper.rules import PARSING_RULES, Parsers

logger = logging.getLogger(__name__)


def parse_idealista_html(html_content: str) -> Dict[str, Any]:
    """
    Parse Idealista HTML and extract full property data.
    Uses the shared rules from rules.py for consistent extraction.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    rules = PARSING_RULES["idealista"]
    
    # Helper to find text from selectors
    def get_text(selectors: List[str]) -> Optional[str]:
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text()
        return None
    
    # 1. Basic Info
    title_raw = get_text(rules["title"]["selectors"])
    location_raw = get_text(rules["location"]["selectors"])
    
    title_clean = Parsers.clean_text(title_raw)
    location_clean = Parsers.clean_text(location_raw)
    
    # Use Shared Cleaning Logic
    specific_part = Parsers.clean_address(title_clean)
    address = f"{specific_part}, {location_clean}" if location_clean else specific_part
    title = f"{title_clean.replace('en venta ', '').strip()}, {location_clean}" if location_clean else title_clean
    # Idealista location format: "Town, Comarca, Province" — town is [0], province is [-1].
    # We want the municipality (town), not the province.
    city = location_clean.split(",")[0].strip() if location_clean else ""
    price = Parsers.clean_price(get_text(rules["price"]["selectors"]))
    description = Parsers.clean_text(get_text(rules["description"]["selectors"]))
    
    # 2. Features & Stats
    features: List[str] = []
    for li in soup.select(".details-property_features li"):
        features.append(Parsers.clean_text(li.get_text()))
    
    # Combine text for Regex scanning
    header_el = soup.select_one(".info-features, .main-info__features")
    header_features = Parsers.clean_text(header_el.get_text() if header_el else "")
    all_stats_text = (header_features + " " + " ".join(features)).replace("  ", " ")
    
    # Apply Shared Regexes
    bedrooms = 0
    bathrooms = 0
    m2_built = 0
    m2_useful = 0
    floor_number = 0
    
    stats = rules["stats"]
    
    bed_match = re.search(stats["bedrooms"], all_stats_text, re.IGNORECASE)
    if bed_match:
        bedrooms = int(bed_match.group(1))
    
    bath_match = re.search(stats["bathrooms"], all_stats_text, re.IGNORECASE)
    if bath_match:
        bathrooms = int(bath_match.group(1))
    
    area_match = re.search(stats["m2_built"], all_stats_text, re.IGNORECASE)
    if area_match:
        m2_built = int(float(area_match.group(1).replace(".", "")))
    
    useful_match = re.search(stats["m2_useful"], all_stats_text, re.IGNORECASE)
    if useful_match:
        m2_useful = int(float(useful_match.group(1).replace(".", "")))
    
    floor_match = re.search(stats["floor_number"], all_stats_text, re.IGNORECASE)
    if floor_match:
        floor_number = int(floor_match.group(1) or floor_match.group(2) or 0)
    
    # Plot area (for houses/villas)
    m2_plot = 0
    plot_match = re.search(stats["m2_plot"], all_stats_text, re.IGNORECASE)
    if plot_match:
        m2_plot = int(float(plot_match.group(1).replace(".", "")))
    
    # Energy rating (A-G)
    energy_rating: Optional[str] = None
    energy_match = re.search(stats["energy_rating"], all_stats_text, re.IGNORECASE)
    if energy_match:
        energy_rating = energy_match.group(1).upper()
    
    # Construction year
    construction_year: Optional[int] = None
    year_match = re.search(stats["construction_year"], all_stats_text, re.IGNORECASE)
    if year_match:
        year_val = int(year_match.group(1))
        if 1800 <= year_val <= 2030:  # Sanity check
            construction_year = year_val
    
    # Apply Shared Booleans & Enums
    extra_data: Dict[str, Any] = {}
    lower_features = all_stats_text.lower()
    
    for key, keywords in rules["booleans"].items():
        if any(k in lower_features for k in keywords):
            extra_data[key] = True
    
    for key, options in rules["enums"].items():
        for opt in options:
            if any(k in lower_features for k in opt["keywords"]):
                extra_data[key] = opt["value"]
                break
    
    # 3. Contact (Using Rules)
    phone = Parsers.clean_text(get_text(rules["phone"]["selectors"]))
    reference_raw = Parsers.clean_text(get_text(rules["reference"]["selectors"]))
    reference = re.sub(r"ref\.?|referencia|:|reference", "", reference_raw, flags=re.IGNORECASE).strip()
    
    # Agency (Special logic for scripts)
    agency = None
    agency_branding = soup.select_one("#agency-branding")
    if agency_branding:
        img_el = agency_branding.select_one("img.agency-video__logo")
        if img_el:
            agency = {
                "name": img_el.get("alt", "").strip() or None,
                "logo_url": img_el.get("data-ondemand-img") or img_el.get("src") or None
            }
    
    # 4. Coordinates (Server-Side Strategy)
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Strategy 1: map container data attributes
    map_container = soup.select_one("#ideMapDetail, #main-map")
    if map_container:
        raw_lat = map_container.get("data-latitude")
        raw_lng = map_container.get("data-longitude")
        if raw_lat and raw_lng:
            try:
                lat = float(raw_lat)
                lng = float(raw_lng)
                logger.info(f"📍 Coords from map container data attributes: {lat}, {lng}")
            except (ValueError, TypeError):
                pass
    
    if not lat:
        for script in soup.find_all("script"):
            script_text = script.string or ""
            # Strategy 2a: explicit latitude/longitude keys
            if "latitude" in script_text and "longitude" in script_text:
                lat_match = re.search(r'["\']?latitude["\']?\s*:\s*"?([-0-9.]+)"?', script_text)
                lng_match = re.search(r'["\']?longitude["\']?\s*:\s*"?([-0-9.]+)"?', script_text)
                if lat_match and lng_match:
                    try:
                        lat = float(lat_match.group(1))
                        lng = float(lng_match.group(1))
                        logger.info(f"📍 Coords from script latitude/longitude keys: {lat}, {lng}")
                        break
                    except (ValueError, TypeError):
                        pass

    # Strategy 2b: Google Maps static map URL with center= parameter
    # Idealista embeds a static map URL in the multimediaCarrousel JSON:
    #   "map":{"src":"https://maps.googleapis.com/maps/api/staticmap?...&center=36.66295910%2C-4.75590770&..."}
    # The %2C is a URL-encoded comma separating lat,lng.
    if not lat:
        _GMAPS_CENTER_RE = re.compile(
            r'maps\.googleapis\.com/maps/api/staticmap\?[^"]*?center=([-0-9.]+)%2C([-0-9.]+)',
            re.IGNORECASE,
        )
        match = _GMAPS_CENTER_RE.search(html_content)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                logger.info(f"📍 Coords from Google Maps static map URL: {lat}, {lng}")
            except (ValueError, TypeError):
                lat = None
                lng = None
    
    # 5. Photos (Robust Extraction)
    photos: List[Dict[str, str]] = []
    
    for line in html_content.split("\n"):
        if "fullScreenGalleryPics" in line:
            try:
                start_index = line.index("[")
                bracket_count = 0
                end_index = start_index
                
                for i in range(start_index, len(line)):
                    if line[i] == "[":
                        bracket_count += 1
                    if line[i] == "]":
                        bracket_count -= 1
                    if bracket_count == 0:
                        end_index = i
                        break
                
                array_string = line[start_index:end_index + 1]
                # Convert JavaScript object to JSON
                json_string = re.sub(r'([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:', r'\1"\2":', array_string)
                json_string = re.sub(r':\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*([,}])', r': "\1"\2', json_string)
                
                gallery_array = json.loads(json_string)
                if isinstance(gallery_array, list):
                    for idx, p in enumerate(gallery_array):
                        url = p.get("imageDataService") or p.get("url") or p.get("src")
                        if url:
                            photos.append({
                                "url": url,
                                "tag": p.get("tag") or f"photo_{idx}"
                            })
            except Exception as e:
                logger.warning(f"Error parsing fullScreenGalleryPics: {e}")
            break
    
    # 6. Listing Type Detection
    listing_type = "sale"  # Default
    price_period = "total"
    
    url_and_title = (title_clean + " " + (description or "")).lower()
    rent_keywords = ["alquiler", "rent", "louer", "miete", "lloguer"]
    
    if any(k in url_and_title for k in rent_keywords):
        listing_type = "rent"
        price_period = "month"
    
    # Build result
    result = {
        "title": title or None,
        "price_eur": price or None,
        "city": city or None,
        "address": address or None,
        "description": description or None,
        "amenities": features if features else None,
        "additionalFeatures": features if features else None,
        "bedrooms": bedrooms or None,
        "bathrooms": bathrooms or None,
        "m2_built": m2_built or None,
        "m2_useful": m2_useful or None,
        "m2_plot": m2_plot or None,  # Plot/land area for houses
        "energy_rating": energy_rating,  # A-G energy certificate
        "construction_year": construction_year,  # Year built
        "floor_number": floor_number or None,
        "lat": lat,
        "lng": lng,
        "reference": reference or None,
        "agency": {**agency, "phone": phone} if agency else None,
        "photos": photos if photos else None,
        "contact": {"phone": phone, "reference": reference},
        "listing_type": listing_type,
        "price_period": price_period,
        **extra_data
    }
    
    # Remove None values
    return {k: v for k, v in result.items() if v is not None}


async def parse_idealista(html: str, url: str) -> Dict[str, Any]:
    """
    Main entry point for Idealista parsing.
    Returns full schema data ready for normalization.
    """
    logger.info(f"🏠 Parsing Idealista listing: {url}")
    
    result = parse_idealista_html(html)
    result["source_url"] = url
    
    logger.info(f"✅ Extracted: {result.get('title', 'Unknown')} - {result.get('price_eur', 0)}€")
    
    return result
