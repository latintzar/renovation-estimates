"""
Spanish Cadastre Client (Python port)
=====================================

Queries the Spanish Catastro (Cadastre) API to get official building data:
- Year built (Antigüedad)
- Surface area
- Property use

Also provides smart year estimation with fallback chain:
- Listing data → Cadastre API → Conservative estimate

API Docs: https://www.catastro.meh.es/ws/Webservices_Libres.pdf
"""

import re
import logging
import ssl
import httpx
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Cadastre API endpoints
BASE_URL_COORDS = 'http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx'
BASE_URL_CALLEJERO = 'http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx'

# Nominatim for geocoding
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'


@dataclass
class CadastreResult:
    """Result from cadastre lookup."""
    ref_cat: str
    year_built: Optional[int]
    surface_m2: Optional[int]
    usage: Optional[str]
    address: Optional[str]
    source: str = "cadastre"  # "cadastre" or "visual_estimate"


async def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """
    Geocode an address to lat/lng using Nominatim.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    'q': address,
                    'format': 'json',
                    'limit': 1
                },
                headers={'User-Agent': 'PuedoCasa/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return {
                        'lat': float(data[0]['lat']),
                        'lng': float(data[0]['lon'])
                    }
    except Exception as e:
        logger.warning(f"Geocoding failed for {address}: {e}")
    
    return None


async def reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, str]]:
    """
    Reverse geocode coordinates to get structured address using Nominatim.
    
    Returns dict with: road, house_number, city, province, postcode
    This is DYNAMIC - no hardcoded province mappings needed.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers={'User-Agent': 'PuedoCasa/1.0'})
            
            if response.status_code == 200:
                data = response.json()
                addr = data.get('address', {})
                
                return {
                    'road': addr.get('road', ''),
                    'house_number': addr.get('house_number', ''),
                    'suburb': addr.get('suburb', addr.get('quarter', '')),
                    'city': addr.get('city', addr.get('town', addr.get('municipality', ''))),
                    'province': addr.get('province', addr.get('state', '')),
                    'postcode': addr.get('postcode', ''),
                    'display_name': data.get('display_name', ''),
                }
    except Exception as e:
        logger.warning(f"Reverse geocoding failed for {lat}, {lng}: {e}")
    
    return None


async def lookup_via_street_search(
    street_name: str,
    city: str,
    province: str,
) -> Optional[CadastreResult]:
    """
    Use Cadastre's ConsultaVia to find a street, then sample building years.
    
    This is the DYNAMIC approach - no hardcoded mappings needed.
    The Cadastre API itself validates province/municipality names.
    """
    # Normalize names for Cadastre API (uppercase, no accents)
    street_clean = _normalize_spanish(street_name.upper())
    city_clean = _normalize_spanish(city.upper())
    province_clean = _normalize_spanish(province.upper())
    
    logger.info(f"  → Street search: {street_clean} in {city_clean}, {province_clean}")
    
    # Step 1: Find the street in Cadastre
    url = f"{BASE_URL_CALLEJERO}/ConsultaVia?Provincia={province_clean}&Municipio={city_clean}&TipoVia=&NombreVia={street_clean}"
    xml = await _fetch_xml(url)
    
    if not xml or '<cuerr>1</cuerr>' in xml:
        logger.warning(f"  → Street not found in Cadastre")
        return None
    
    # Check if street was found
    if '<cuca>0</cuca>' in xml:
        logger.warning(f"  → No matches for street '{street_clean}'")
        return None
    
    logger.info(f"  → Street found in Cadastre, sampling until 20 valid years...")
    
    # Step 2: Sample addresses on this street until we have 20 valid years
    import asyncio
    years = []
    MIN_SAMPLES = 20
    # Extended range of building numbers to try (odd then even, common in Spain)
    sample_numbers = list(range(1, 301, 2)) + list(range(2, 302, 2))
    
    for num in sample_numbers:
        if len(years) >= MIN_SAMPLES:
            break
        try:
            result = await lookup_by_address(
                province=province_clean,
                municipality=city_clean,
                street_type="CL",  # Most common
                street_name=street_clean,
                number=str(num)
            )
            if result and result.year_built and 1800 < result.year_built < 2030:
                years.append(result.year_built)
            
            await asyncio.sleep(0.15)  # Be nice to the API
        except Exception:
            continue
    
    if len(years) >= MIN_SAMPLES:
        # Use MEDIAN not average (more robust to outliers)
        median_year = _calculate_median(years)
        logger.info(f"  ✅ Street sampling: {len(years)} samples, MEDIAN year: {median_year} (range: {min(years)}-{max(years)})")
        return CadastreResult(
            ref_cat="STREET_SAMPLE",
            year_built=median_year,
            surface_m2=None,
            usage=None,
            address=f"{street_name}, {city}",
            source="street_sampling"
        )
    elif years:
        logger.warning(f"  ⚠️ Only {len(years)} samples (need {MIN_SAMPLES}), falling back to neighborhood")
    
    return None


def _calculate_median(values: list) -> int:
    """Calculate median of a list of integers."""
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) // 2


async def _fetch_xml(url: str) -> Optional[str]:
    """Fetch XML from Cadastre API with SSL workaround."""
    try:
        # Create client with SSL verification disabled (Cadastre has issues)
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
    except Exception as e:
        logger.error(f"Cadastre API fetch failed: {e}")
    return None


def _extract_between(xml: str, start_tag: str, end_tag: str) -> Optional[str]:
    """Simple XML value extraction without parsing."""
    pattern = f"<{start_tag}>(.*?)</{end_tag}>"
    match = re.search(pattern, xml, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


async def get_refcat_from_coordinates(lat: float, lng: float) -> Optional[str]:
    """
    Get Cadastre reference from coordinates.
    Returns 14-20 char reference.
    """
    params = f"SRS=EPSG:4326&Coordenada_X={lng}&Coordenada_Y={lat}"
    url = f"{BASE_URL_COORDS}/Consulta_RCCOOR?{params}"
    
    xml = await _fetch_xml(url)
    if not xml:
        return None
    
    # Check for error
    if '<err>' in xml.lower() and '<desc>' in xml.lower():
        err = _extract_between(xml, 'desc', 'desc')
        if err:
            logger.warning(f"Cadastre error: {err}")
            return None
    
    # Extract reference components
    pc1 = _extract_between(xml, 'pc1', 'pc1')
    pc2 = _extract_between(xml, 'pc2', 'pc2')
    car = _extract_between(xml, 'car', 'car') or ''
    cc = _extract_between(xml, 'cc', 'cc') or ''
    
    if pc1 and pc2:
        return pc1 + pc2 + car + cc
    
    return None


async def get_unit_details(ref_cat: str) -> Optional[CadastreResult]:
    """
    Get details for a cadastre reference.
    Returns year built, surface, usage.
    """
    params = f"RC={ref_cat}&Provincia=&Municipio="
    url = f"{BASE_URL_CALLEJERO}/Consulta_DNPRC?{params}"
    
    xml = await _fetch_xml(url)
    if not xml:
        return None
    
    # Check for error
    if '<err>' in xml.lower():
        return None
    
    # Extract data from <bico><bi><debi> structure
    year_str = _extract_between(xml, 'ant', 'ant')
    surface_str = _extract_between(xml, 'sfc', 'sfc')
    usage = _extract_between(xml, 'luso', 'luso')
    address = _extract_between(xml, 'ldt', 'ldt')  # Full address
    
    year = int(year_str) if year_str and year_str.isdigit() else None
    surface = int(surface_str) if surface_str and surface_str.isdigit() else None
    
    # Validate year (must be reasonable)
    if year and (year < 1000 or year > 2030):
        year = None
    
    return CadastreResult(
        ref_cat=ref_cat,
        year_built=year,
        surface_m2=surface,
        usage=usage,
        address=address,
        source="cadastre"
    )


def is_specific_address(address: str) -> bool:
    """
    Check if address is specific (has street number).
    
    Specific: "Carrer de la Penya, 23, Rubí" → True
    Street only: "Avenida Maragatos, Benavente" → False
    Neighborhood: "Vila de Gràcia, Barcelona" → False
    """
    return classify_address(address) == "specific"


def has_street_info(address: str) -> bool:
    """
    Check if address has at least street-level info (can sample the street).
    
    Returns True for both 'specific' and 'street_only' addresses.
    """
    addr_type = classify_address(address)
    return addr_type in ("specific", "street_only")


async def get_province_from_gemini(city: str) -> Optional[str]:
    """
    Use Gemini flash-lite to resolve city → province.
    Quick and cheap lookup.
    """
    from .gemini_client import call_gemini
    
    prompt = f"""What Spanish province is "{city}" in? Reply with ONLY the province name in uppercase."""

    try:
        response = await call_gemini(
            prompt=prompt,
            model="flash-lite",
            temperature=0,
            max_tokens=50,
            use_spanish=False,
        )
        
        if response.success and response.text:
            province = response.text.strip().upper()
            province = province.replace(".", "").replace(",", "").strip()
            for old, new in [("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U")]:
                province = province.replace(old, new)
            
            if 2 < len(province) < 30:
                logger.info(f"  🤖 Province from Gemini: {province}")
                return province
                
    except Exception as e:
        logger.warning(f"Gemini province lookup failed: {e}")
    
    return None


# Common street type mappings
STREET_TYPES = {
    "carrer": "CL", "calle": "CL", "c/": "CL", "c.": "CL",
    "avinguda": "AV", "avenida": "AV", "av.": "AV", "av": "AV",
    "plaça": "PZ", "plaza": "PZ", "pl.": "PZ",
    "passeig": "PS", "paseo": "PS",
    "rambla": "RB", "travessera": "TR", "travesera": "TR",
    "carretera": "CR", "camí": "CM", "camino": "CM",
    "ronda": "RD", "via": "VI",
}

# Common province mappings (quick lookup)
PROVINCE_MAP = {
    "barcelona": "BARCELONA", "rubí": "BARCELONA", "rubi": "BARCELONA",
    "terrassa": "BARCELONA", "sabadell": "BARCELONA", "badalona": "BARCELONA",
    "madrid": "MADRID", "alcalá": "MADRID", "móstoles": "MADRID",
    "valencia": "VALENCIA", "alicante": "ALICANTE",
    "sevilla": "SEVILLA", "málaga": "MALAGA", "malaga": "MALAGA",
    "granada": "GRANADA", "córdoba": "CORDOBA",
    "bilbao": "VIZCAYA", "san sebastián": "GUIPUZCOA",
    "zaragoza": "ZARAGOZA", "palma": "BALEARES",
    "benavente": "ZAMORA", "zamora": "ZAMORA",
}


def _parse_address_sync(address: str) -> Dict[str, str]:
    """
    Synchronous address parsing (no API calls).
    
    Handles Spanish address formats:
    - "Av. Maragatos, 72, 49600 Benavente, Zamora"  → municipality=BENAVENTE, province=ZAMORA
    - "Carrer de la Penya, 23, Rubí, Spain" → municipality=RUBÍ, province=BARCELONA
    """
    address = address.replace(", Spain", "").replace(",Spain", "").replace(", España", "").strip()
    
    parts = [p.strip() for p in address.split(",")]
    
    result = {
        "province": "",
        "municipality": "",
        "street_type": "CL",
        "street_name": "",
        "number": ""
    }
    
    # Try to identify parts from the END (province is usually last)
    # Format: Street, Number, [PostCode] City, Province
    
    # Check last part - it could be province OR city OR both (like "Barcelona")
    if len(parts) >= 2:
        last_part = parts[-1].strip().lower()
        
        # First check if it's a PROVINCE name (like "Zamora", "Barcelona")
        is_province_name = last_part in [p.lower() for p in PROVINCE_MAP.values()]
        
        if is_province_name:
            # It's a province - find and set it
            for city_key, prov in PROVINCE_MAP.items():
                if prov.lower() == last_part:
                    result["province"] = prov
                    # IMPORTANT: If province == city name (like Barcelona, Madrid, Valencia),
                    # also set municipality to the same value
                    if city_key == last_part:
                        result["municipality"] = _normalize_spanish(parts[-1].strip().upper())
                    parts = parts[:-1]  # Remove province from parts
                    break
        else:
            # It might be a city name (like "Benavente" → province ZAMORA)
            for city_key, prov in PROVINCE_MAP.items():
                if city_key == last_part:
                    # It's a city! Set both province AND municipality
                    result["province"] = prov
                    result["municipality"] = _normalize_spanish(parts[-1].strip().upper())
                    break
    
    # Look for municipality (usually right before province or has postal code)
    for i, part in enumerate(parts):
        part_lower = part.lower().strip()
        
        # Check for postal code + city pattern (e.g., "49600 Benavente")
        postal_match = re.match(r'^\d{5}\s+(.+)$', part.strip())
        if postal_match:
            city_name = postal_match.group(1)
            result["municipality"] = _normalize_spanish(city_name.upper())
            # Try to find province for this city
            if not result["province"]:
                for city_key, prov in PROVINCE_MAP.items():
                    if city_key in city_name.lower():
                        result["province"] = prov
                        break
            continue
        
        # Check if it's a known city (not a street part)
        is_street_part = any(st in part_lower for st in STREET_TYPES.keys())
        if not is_street_part:
            for city_key, prov in PROVINCE_MAP.items():
                if city_key in part_lower and city_key != prov.lower():
                    # It's a city, not a province
                    if not result["municipality"]:
                        result["municipality"] = _normalize_spanish(part.upper())
                    if not result["province"]:
                        result["province"] = prov
                    break
        
        # Check for street number (standalone digit)
        if part.strip().isdigit():
            result["number"] = part.strip()
            continue
        
        # Handle complex numbers like "5 - E"
        num_complex_match = re.match(r'^(\d+)\s*[-]?\s*\w?$', part.strip())
        if num_complex_match:
            result["number"] = num_complex_match.group(1)
            continue
        
        # Check for street type
        for st_name, st_code in STREET_TYPES.items():
            if part_lower.startswith(st_name) or part_lower.startswith(f"{st_name}."):
                result["street_type"] = st_code
                # Extract street name after the type
                street = re.sub(f'^{st_name}\\.?\\s*', '', part, flags=re.IGNORECASE)
                street = re.sub(r'^(de la |del |de |la |el |las |los )', '', street, flags=re.IGNORECASE)
                
                # Check for embedded number
                num_match = re.search(r',?\s*(\d+)(\s*[-]\s*\w)?$', street)
                if num_match:
                    result["number"] = num_match.group(1)
                    street = street[:num_match.start()].strip().rstrip(",")
                
                result["street_name"] = _normalize_spanish(street.upper())
                break
    
    return result


def _normalize_spanish(text: str) -> str:
    """Normalize Spanish/Catalan text for Cadastre API (remove accents)."""
    # Handle both uppercase and lowercase, including Catalan accents
    replacements = [
        # Uppercase Spanish
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("Ñ", "N"), ("Ü", "U"),
        # Lowercase Spanish
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ñ", "n"), ("ü", "u"),
        # Catalan grave accents (À, È, Ò)
        ("À", "A"), ("È", "E"), ("Ò", "O"),
        ("à", "a"), ("è", "e"), ("ò", "o"),
        # Catalan L·L (ela geminada)
        ("L·L", "LL"), ("l·l", "ll"),
        # Catalan Ç
        ("Ç", "C"), ("ç", "c"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


async def parse_spanish_address(address: str) -> Optional[Dict[str, str]]:
    """
    Parse Spanish address into components for Cadastre API.
    Uses Gemini flash-lite to resolve unknown cities → provinces.
    
    Input: "Carrer de la Penya, 23, Rubí, Spain"
    Output: {province, municipality, street_type, street_name, number}
    """
    result = _parse_address_sync(address)
    
    # If we have municipality but no province, ask Gemini
    if result["municipality"] and not result["province"]:
        logger.info(f"  → Unknown city '{result['municipality']}', asking Gemini...")
        province = await get_province_from_gemini(result["municipality"])
        if province:
            result["province"] = province
    
    # Valid if we have street + municipality + province
    if result["street_name"] and result["municipality"] and result["province"]:
        return result
    
    # Also valid if we have at least street + municipality (can try sampling)
    if result["street_name"] and result["municipality"]:
        return result
    
    return None


async def lookup_by_address(province: str, municipality: str, street_type: str, 
                            street_name: str, number: str) -> Optional[CadastreResult]:
    """
    Query Cadastre API by address components.
    """
    params = (
        f"Provincia={province}&Municipio={municipality}&"
        f"Sigla={street_type}&Calle={street_name}&Numero={number}&"
        f"Bloque=&Escalera=&Planta=&Puerta="
    )
    url = f"{BASE_URL_CALLEJERO}/Consulta_DNPLOC?{params}"
    
    xml = await _fetch_xml(url)
    if not xml:
        return None
    
    # Check for error
    if '<err>' in xml.lower():
        err = _extract_between(xml, 'des', 'des')
        if err:
            logger.warning(f"Cadastre error: {err}")
        return None
    
    # Extract data
    year_str = _extract_between(xml, 'ant', 'ant')
    surface_str = _extract_between(xml, 'sfc', 'sfc')
    usage = _extract_between(xml, 'luso', 'luso')
    full_address = _extract_between(xml, 'ldt', 'ldt')
    
    # Get reference
    pc1 = _extract_between(xml, 'pc1', 'pc1') or ''
    pc2 = _extract_between(xml, 'pc2', 'pc2') or ''
    car = _extract_between(xml, 'car', 'car') or ''
    cc1 = _extract_between(xml, 'cc1', 'cc1') or ''
    cc2 = _extract_between(xml, 'cc2', 'cc2') or ''
    ref_cat = pc1 + pc2 + car + cc1 + cc2
    
    year = int(year_str) if year_str and year_str.isdigit() else None
    surface = int(surface_str) if surface_str and surface_str.isdigit() else None
    
    # Validate year
    if year and (year < 1000 or year > 2030):
        year = None
    
    if not year and not surface:
        return None
    
    return CadastreResult(
        ref_cat=ref_cat,
        year_built=year,
        surface_m2=surface,
        usage=usage,
        address=full_address,
        source="cadastre"
    )


async def lookup_year_from_cadastre(
    address: str, 
    city: str = None,
    lat: float = None,
    lng: float = None
) -> Optional[CadastreResult]:
    """
    Main entry point: Look up building year from Cadastre.
    
    Strategy (DYNAMIC - no hardcoded province mappings):
    1. IF we have lat/lng → Try direct coordinate lookup
    2. IF coordinates fail → Use reverse geocoding to get province/city
    3. Use Cadastre street search API (fully dynamic)
    4. Sample addresses on the street
    
    Returns CadastreResult or None.
    """
    logger.info(f"🏛️ Cadastre lookup for: {address}")
    
    # STRATEGY 1: Use coordinates if available (direct parcel lookup)
    if lat and lng:
        logger.info(f"  → Using coordinates: {lat:.6f}, {lng:.6f}")
        ref_cat = await get_refcat_from_coordinates(lat, lng)
        if ref_cat:
            details = await get_unit_details(ref_cat)
            if details and details.year_built:
                logger.info(f"  ✅ Year from coordinates: {details.year_built}")
                return details
        logger.info(f"  → Coordinates didn't match cadastre parcel")
        
        # STRATEGY 2: Use reverse geocoding to get province/city DYNAMICALLY
        logger.info(f"  → Trying reverse geocoding...")
        geo = await reverse_geocode(lat, lng)
        if geo and geo.get('city') and geo.get('province'):
            logger.info(f"  → Reverse geocoded to: {geo.get('city')}, {geo.get('province')}")
            
            # Extract street name from original address
            addr_type = classify_address(address)
            if addr_type in ("specific", "street_only"):
                # Parse street from address
                parsed = await parse_spanish_address(address)
                street_name = parsed.get("street_name") if parsed else None
                
                if not street_name:
                    # Try to extract from address directly
                    for part in address.split(","):
                        part = part.strip().lower()
                        if any(st in part for st in STREET_TYPES.keys()):
                            street_name = part
                            break
                
                if street_name:
                    # Use dynamic street search
                    result = await lookup_via_street_search(
                        street_name=street_name,
                        city=geo['city'],
                        province=geo['province'],
                    )
                    if result:
                        return result
    
    addr_type = classify_address(address)
    logger.info(f"  → Address type: {addr_type}")
    
    # Parse address components (async - may call Gemini for province)
    parsed = await parse_spanish_address(address)
    
    if addr_type == "specific" and parsed:
        # SPECIFIC: Direct lookup
        logger.info(f"  → Direct lookup: {parsed['street_type']} {parsed['street_name']} {parsed['number']}")
        
        result = await lookup_by_address(
            province=parsed["province"],
            municipality=parsed["municipality"],
            street_type=parsed["street_type"],
            street_name=parsed["street_name"],
            number=parsed["number"]
        )
        
        if result and result.year_built:
            logger.info(f"  ✅ Year Built: {result.year_built} (exact address)")
            return result
    
    elif addr_type == "street_only" and parsed:
        # STREET_ONLY: Sample addresses on this street
        logger.info(f"  → Street sampling: {parsed['street_type']} {parsed['street_name']}")
        
        avg_year = await sample_street_years(
            province=parsed["province"],
            municipality=parsed["municipality"],
            street_type=parsed["street_type"],
            street_name=parsed["street_name"]
        )
        
        if avg_year:
            return CadastreResult(
                ref_cat="SAMPLED",
                year_built=avg_year,
                surface_m2=None,
                usage=None,
                address=address,
                source="street_sampling"
            )
        
        # Street doesn't exist - fall back to neighborhood sampling
        logger.info(f"  → Street not found, falling back to neighborhood sampling...")
        neighborhood = parsed["municipality"]  # Use city as neighborhood
        avg_year = await sample_neighborhood_years(
            neighborhood=neighborhood,
            city=parsed["municipality"],
            province=parsed["province"],
            lat=lat,
            lng=lng
        )
        
        if avg_year:
            return CadastreResult(
                ref_cat="SAMPLED",
                year_built=avg_year,
                surface_m2=None,
                usage=None,
                address=address,
                source="neighborhood_sampling"
            )
    
    elif addr_type == "neighborhood_only":
        # NEIGHBORHOOD_ONLY: Use Google Places + Cadastre sampling
        # Extract neighborhood and city
        parts = [p.strip() for p in address.split(",")]
        neighborhood = parts[0] if parts else address
        detected_city = city or (parts[1] if len(parts) > 1 else "")
        
        # Try to detect province (ask Gemini if unknown)
        province = None
        for city_name, prov in PROVINCE_MAP.items():
            if city_name in address.lower() or (detected_city and city_name in detected_city.lower()):
                province = prov
                break
        
        if not province and detected_city:
            province = await get_province_from_gemini(detected_city)
        
        province = province or "BARCELONA"  # Last resort default
        
        logger.info(f"  → Neighborhood sampling: {neighborhood} in {detected_city} ({province})")
        
        avg_year = await sample_neighborhood_years(
            neighborhood=neighborhood,
            city=detected_city,
            province=province,
            lat=lat,   # Pass coordinates for Google Places
            lng=lng
        )
        
        if avg_year:
            return CadastreResult(
                ref_cat="SAMPLED",
                year_built=avg_year,
                surface_m2=None,
                usage=None,
                address=address,
                source="neighborhood_sampling"
            )
    
    # Fallback: Try coordinate-based lookup
    logger.info(f"  → Trying coordinate fallback...")
    coords = await geocode_address(address)
    if coords:
        ref_cat = await get_refcat_from_coordinates(coords['lat'], coords['lng'])
        if ref_cat:
            details = await get_unit_details(ref_cat)
            if details and details.year_built:
                logger.info(f"  ✅ Year Built: {details.year_built} (via coords)")
                return details
    
    logger.warning(f"  → Could not determine year from Cadastre")
    return None


# =============================================================================
# STREET/NEIGHBORHOOD SAMPLING
# =============================================================================

async def sample_street_years(
    province: str,
    municipality: str, 
    street_type: str,
    street_name: str,
    min_samples: int = 20
) -> Optional[int]:
    """
    Sample multiple addresses on a street to estimate MEDIAN building year.
    Used when we have street name but no specific number.
    
    Keeps sampling until we have min_samples (default 20).
    Returns median year or None.
    """
    import asyncio
    years = []
    # Extended range: odd numbers then even numbers (common in Spain)
    sample_numbers = list(range(1, 301, 2)) + list(range(2, 302, 2))
    
    logger.info(f"  📊 Sampling addresses on {street_type} {street_name} until {min_samples} valid years...")
    
    for num in sample_numbers:
        if len(years) >= min_samples:
            break
        try:
            result = await lookup_by_address(
                province=province,
                municipality=municipality,
                street_type=street_type,
                street_name=street_name,
                number=str(num)
            )
            if result and result.year_built and 1800 < result.year_built < 2030:
                years.append(result.year_built)
                
            await asyncio.sleep(0.15)  # Be nice to the API
            
        except Exception as e:
            continue
    
    if len(years) >= min_samples:
        median = _calculate_median(years)
        logger.info(f"  ✅ Street sampling: {len(years)} valid samples, MEDIAN year: {median} (range: {min(years)}-{max(years)})")
        return median
    elif years:
        logger.warning(f"  ⚠️ Only {len(years)} samples (need {min_samples})")
    
    return None


async def generate_neighborhood_addresses(neighborhood: str, city: str) -> list:
    """
    Use Gemini to generate real addresses in a neighborhood.
    """
    from .gemini_client import call_gemini
    
    prompt = f"""Generate 20 REAL street addresses in the neighborhood "{neighborhood}" of {city}, Spain.

These must be actual existing streets with typical building numbers.
Focus on residential areas.

Return JSON only:
{{"addresses": ["Calle Example 15", "Carrer Example 22", ...]}}

Just the street name and number, no city/neighborhood suffix needed."""

    try:
        response = await call_gemini(
            prompt=prompt,
            model="flash",  # gemini-3-flash-preview
            temperature=0.4,
            max_tokens=2000,
        )
        
        if response.success and response.text:
            import json
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text.strip())
            addresses = data.get("addresses", [])
            logger.info(f"  🤖 Gemini generated {len(addresses)} addresses for {neighborhood}")
            return addresses[:20]
            
    except Exception as e:
        logger.error(f"Failed to generate neighborhood addresses: {e}")
    
    return []


async def sample_neighborhood_years(
    neighborhood: str, 
    city: str, 
    province: str,
    lat: float = None,
    lng: float = None,
    min_samples: int = 20  # Need 20 samples for reliable MEDIAN
) -> Optional[int]:
    """
    Sample buildings across a neighborhood to estimate MEDIAN building year.
    Used when we only have neighborhood-level location.
    
    Strategy:
    1. IF lat/lng available → Google Places (multiple calls) → Get place coordinates
    2. Query Cadastre BY COORDINATES (more reliable than address)
    3. Return MEDIAN only if we have >= min_samples (20)
    
    Cost:
    - Google Places: ~$0.032 per API call
    - Cadastre: FREE
    """
    logger.info(f"  📊 Sampling neighborhood: {neighborhood}, {city}...")
    
    years = []
    
    # STRATEGY 1: Google Places → Coordinates → Cadastre
    if lat and lng:
        logger.info(f"  → Using Google Places (coordinates method)...")
        try:
            from clients.google_places_client import GooglePlacesClient
            client = GooglePlacesClient()
            
            # ONE API call gets up to 20 places with coordinates
            places = await client.nearby_search(
                lat=lat, 
                lng=lng, 
                types=["store", "restaurant", "bank", "pharmacy", "lodging"],
                radius_m=500,
                max_results=20,
                rank_by="DISTANCE"
            )
            
            if places:
                logger.info(f"  ✅ Google Places returned {len(places)} places")
                
                # Query Cadastre by COORDINATES (much more reliable)
                for place in places:
                    try:
                        refcat = await get_refcat_from_coordinates(place.lat, place.lng)
                        if refcat:
                            details = await get_unit_details(refcat)
                            # Filter suspicious years (but 1900 can be valid for old towns!)
                            if details and details.year_built and 1850 < details.year_built < 2030:
                                years.append(details.year_built)
                                logger.debug(f"    {place.name}: {details.year_built}")
                        
                        # Small delay to be nice to Cadastre API
                        import asyncio
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        continue
                        
        except Exception as e:
            logger.warning(f"  → Google Places coordinate method failed: {e}")
    
    # STRATEGY 2: Gemini fallback (address-based - less reliable)
    if len(years) < min_samples:
        logger.info(f"  → Trying Gemini-generated addresses...")
        addresses = await generate_neighborhood_addresses(neighborhood, city)
        
        for addr in addresses:
            parsed = await parse_spanish_address(f"{addr}, {city}")
            if not parsed:
                continue
            
            parsed["province"] = province
            parsed["municipality"] = _normalize_spanish(city.upper())
            
            try:
                result = await lookup_by_address(
                    province=parsed["province"],
                    municipality=parsed["municipality"],
                    street_type=parsed["street_type"],
                    street_name=parsed["street_name"],
                    number=parsed["number"]
                )
                
                if result and result.year_built and 1850 < result.year_built < 2030:
                    years.append(result.year_built)
                    logger.debug(f"    ↳ {addr[:40]}: {result.year_built}")
                
                import asyncio
                await asyncio.sleep(0.3)
                
            except Exception as e:
                continue
    
    # MINIMUM SAMPLE THRESHOLD - use MEDIAN
    if len(years) >= min_samples:
        median = _calculate_median(years)
        logger.info(f"  ✅ Neighborhood sampling: {len(years)} valid samples, MEDIAN year: {median} (range: {min(years)}-{max(years)})")
        return median
    elif years:
        logger.warning(f"  ⚠️ Only {len(years)} samples (need {min_samples}). Not reliable enough.")
    else:
        logger.warning(f"  → No valid years found in {neighborhood}")
    
    return None


def classify_address(address: str) -> str:
    """
    Classify address type:
    - 'specific': Has street + number (e.g., "Carrer Penya, 23, Rubí")
    - 'street_only': Has street but no number (e.g., "Avenida Maragatos, Benavente")
    - 'neighborhood_only': Just area name (e.g., "Vila de Gràcia, Barcelona")
    """
    if not address:
        return "unknown"
    
    # Check for street number
    has_number = bool(re.search(r'[,\s](\d{1,4})[,\s]', address))
    has_numbered_suffix = bool(re.search(r'(nº|n\.|número|num)\s*\d+', address, re.IGNORECASE))
    
    if has_number or has_numbered_suffix:
        return "specific"
    
    # Check for street type words (indicates street-level but no number)
    street_keywords = [
        "calle", "carrer", "avenida", "avinguda", "paseo", "passeig",
        "plaza", "plaça", "rambla", "travesera", "travessera", "ronda",
        "camino", "camí", "carretera", "via", "c/", "av.", "pl."
    ]
    
    addr_lower = address.lower()
    has_street = any(kw in addr_lower for kw in street_keywords)
    
    if has_street:
        return "street_only"
    
    return "neighborhood_only"


# =============================================================================
# VISUAL YEAR ESTIMATION
# =============================================================================

async def estimate_year_from_photos(
    images: list,
    gemini_client_func,
    model: str = "pro"
) -> Optional[int]:
    """
    Estimate construction year from photos using Gemini.
    Used when cadastre lookup fails or address is not specific.
    
    Returns estimated year or None.
    """
    prompt = """Analiza estas fotos de una vivienda en España y estima el AÑO DE CONSTRUCCIÓN.

Busca indicadores de época:
- Materiales de fachada (ladrillo visto, revoco, piedra)
- Estilo de ventanas (aluminio plateado = 70s-80s, PVC = post-2000)
- Carpintería interior (sapelly = 70s-80s, roble = 90s, lacado = 2000s)
- Suelos (terrazo = 60s-80s, gres = 90s, porcelánico = 2000s)
- Azulejos (patrones = 70s-80s, colores neutros = 90s+)
- Instalaciones eléctricas visibles
- Estilo arquitectónico general

Responde SOLO con un JSON:
{
  "year_estimate": 1975,
  "confidence": "high/medium/low",
  "indicators": ["indicador 1", "indicador 2", "indicador 3"]
}"""

    try:
        response = await gemini_client_func(
            prompt=prompt,
            images=images[:6],
            model=model,
            temperature=0.2,
            max_tokens=1000,
        )
        
        if response.success and response.text:
            import json
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text.strip())
            year = data.get("year_estimate")
            
            if year and 1900 < year < 2030:
                logger.info(f"  📷 Visual estimate: {year} ({data.get('confidence', '?')} confidence)")
                logger.info(f"     Indicators: {data.get('indicators', [])[:3]}")
                return year
                
    except Exception as e:
        logger.error(f"Visual year estimation failed: {e}")
    
    return None


# =============================================================================
# SMART YEAR ESTIMATION (V0.4.8)
# =============================================================================

def get_year_from_listing(listing_data: Dict[str, Any]) -> Optional[int]:
    """
    Try to get year built from listing data (sync, no API calls).
    
    Checks (in order):
    1. Top-level year_built field (from DB or previous estimation)
    2. scraped_data.year_built / construction_year / ano_construccion
    3. Features containing "construido"
    
    Returns validated year (1800-2030) or None.
    """
    year = None
    
    # 1. Check top-level year_built first (already in DB)
    top_level_year = listing_data.get("year_built")
    if top_level_year:
        try:
            y = int(top_level_year)
            if 1800 < y < 2030:
                logger.info(f"  → Year from listing DB: {y}")
                return y
        except (ValueError, TypeError):
            pass
    
    # 2. Check scraped_data fields
    scraped = listing_data.get("scraped_data", {})
    if isinstance(scraped, dict):
        year = scraped.get("year_built") or scraped.get("construction_year") or scraped.get("ano_construccion")
        
        # 3. Check features for "construido en YYYY"
        if not year:
            features = scraped.get("features", [])
            if isinstance(features, list):
                for feat in features:
                    if isinstance(feat, str) and "construido" in feat.lower():
                        match = re.search(r'(\d{4})', feat)
                        if match:
                            year = int(match.group(1))
                            break
    
    if year:
        try:
            y = int(year)
            if 1800 < y < 2030:
                logger.info(f"  → Year from scraped_data: {y}")
                return y
        except (ValueError, TypeError):
            pass
    
    return None


async def smart_year_estimation(listing_data: Dict[str, Any]) -> Tuple[int, str]:
    """
    Smart year estimation with fallback chain:
    1. From listing data (fastest)
    2. From Cadastre API (prioritizes coordinates):
       - Coordinates → direct lookup (most reliable)
       - Specific address → exact lookup
       - Street-only → sample street, then neighborhood
       - Neighborhood-only → generate addresses with Gemini, sample
    3. Fallback to conservative estimate
    
    Returns: (year, source)
    
    Sources:
    - "listing": Year found in listing data
    - "cadastre": Direct cadastre lookup
    - "street_sampling": Average of buildings on same street
    - "neighborhood_sampling": Average of buildings in neighborhood
    - "estimate": Conservative fallback (1975)
    """
    # 1. Try listing data first (no API calls)
    year = get_year_from_listing(listing_data)
    if year:
        logger.info(f"📅 Year from listing: {year}")
        return year, "listing"
    
    # 2. Try Cadastre (prioritize coordinates if available)
    address = listing_data.get("address", "")
    city = listing_data.get("city", "")
    lat = listing_data.get("lat")
    lng = listing_data.get("lng")
    
    if address or (lat and lng):
        if lat and lng:
            logger.info(f"📍 Have coordinates: {lat:.6f}, {lng:.6f}")
        if address:
            addr_type = classify_address(address)
            logger.info(f"📍 Address type: {addr_type}")
        
        try:
            result = await lookup_year_from_cadastre(
                address=address, 
                city=city,
                lat=lat,
                lng=lng
            )
            if result and result.year_built:
                source = result.source
                logger.info(f"🏛️ Year from {source}: {result.year_built}")
                return result.year_built, source
        except Exception as e:
            logger.warning(f"Cadastre lookup failed: {e}")
    
    # 3. Fallback
    logger.warning("⚠️ Could not determine year, using conservative estimate: 1975")
    return 1975, "estimate"

