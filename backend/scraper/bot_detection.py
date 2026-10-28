"""
🤖 BOT DETECTION & DOMAIN INTELLIGENCE
======================================

Smart system to determine when to use Scrapling vs direct fetch.

Strategy:
1. Check if domain is in "known protected" list (learned from failures)
2. If direct fetch, analyze response for bot-block signals
3. Learn from extraction failures - remember which domains need Scrapling

This avoids:
- Wasting time on protected sites (slow double-fetch)
- Wasting money on sites that work fine directly
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# DOMAIN INTELLIGENCE (Learned from experience)
# =============================================================================

# Domains we KNOW need Scrapling (updated over time)
# These get JS rendering + anti-bot bypass automatically
KNOWN_PROTECTED_DOMAINS = {
    # Major portals with strong protection
    "idealista.com",
    "idealista.pt",
    "fotocasa.es",
    "pisos.com",
    "habitaclia.com",
    "yaencontre.com",
    
    # International portals
    "rightmove.co.uk",
    "zoopla.co.uk",
    "immobilienscout24.de",
    "immowelt.de",
    "seloger.com",
    "leboncoin.fr",
    "zillow.com",
    "realtor.com",
    "redfin.com",
    
    # Franchise networks (often JS-heavy)
    "century21.es",
    "century21.com",
    "remax.es",
    "remax.com",
    "coldwellbanker.com",
    "sothebysrealty.com",
    "engelvoelkers.com",
    "lucasfox.com",
    "barnes-international.com",
}

# Domains that work fine with direct fetch (no protection)
KNOWN_SIMPLE_DOMAINS: Set[str] = set()

# File to persist learned domains
LEARNED_DOMAINS_FILE = Path(__file__).parent / ".learned_domains.json"


def load_learned_domains() -> Tuple[Set[str], Set[str]]:
    """Load domains we've learned need Scrapling."""
    protected = set(KNOWN_PROTECTED_DOMAINS)
    simple = set(KNOWN_SIMPLE_DOMAINS)
    
    if LEARNED_DOMAINS_FILE.exists():
        try:
            data = json.loads(LEARNED_DOMAINS_FILE.read_text())
            protected.update(data.get("protected", []))
            simple.update(data.get("simple", []))
        except Exception as e:
            logger.warning(f"Could not load learned domains: {e}")
    
    return protected, simple


def save_learned_domain(domain: str, needs_scrapling: bool):
    """Save a learned domain preference."""
    try:
        data = {"protected": [], "simple": []}
        if LEARNED_DOMAINS_FILE.exists():
            data = json.loads(LEARNED_DOMAINS_FILE.read_text())
        
        if needs_scrapling:
            if domain not in data["protected"]:
                data["protected"].append(domain)
                logger.info(f"📚 Learned: {domain} needs Scrapling")
        else:
            if domain not in data["simple"]:
                data["simple"].append(domain)
        
        LEARNED_DOMAINS_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning(f"Could not save learned domain: {e}")


def domain_needs_scrapling(domain: str) -> Tuple[bool, str]:
    """
    Check if a domain is known to need Scrapling.
    
    Returns: (needs_scrapling, reason)
    """
    protected, simple = load_learned_domains()
    
    # Check exact match
    if domain in protected:
        return True, "known_protected"
    
    # Check if parent domain is protected (www.century21.es → century21.es)
    parts = domain.split(".")
    for i in range(len(parts)):
        parent = ".".join(parts[i:])
        if parent in protected:
            return True, f"parent_domain:{parent}"
    
    # Check if known simple
    if domain in simple:
        return False, "known_simple"
    
    return False, "unknown"


# =============================================================================
# BOT BLOCK DETECTION (Analyze response)
# =============================================================================

# Signals that we've been bot-blocked
BOT_BLOCK_PATTERNS = [
    # Cloudflare
    r"checking your browser",
    r"cloudflare",
    r"cf-browser-verification",
    r"ray id:",
    r"please wait\.\.\.",
    r"just a moment",
    
    # Generic bot detection
    r"robot",
    r"captcha",
    r"verify you'?re (human|not a robot)",
    r"access denied",
    r"forbidden",
    r"blocked",
    r"unusual traffic",
    r"security check",
    r"bot detection",
    r"automated access",
    
    # JavaScript required
    r"javascript is required",
    r"enable javascript",
    r"javascript must be enabled",
    r"please enable js",
    
    # Login/auth walls
    r"sign in to continue",
    r"login required",
    r"please log in",
]

# Minimum content indicators (if page has real content)
CONTENT_INDICATORS = [
    r"<img[^>]+src=",  # Has images
    r"precio|price|€|\$|£",  # Has price info
    r"habitacion|bedroom|dormitor|zimmer|chambre",  # Has property terms
    r"m²|sqft|square",  # Has area info
    r"<main|<article|<section",  # Has semantic structure
]


def detect_bot_block(html: str, status_code: int = 200) -> Tuple[bool, str]:
    """
    Analyze HTML response to detect if we've been bot-blocked.
    
    Returns: (is_blocked, reason)
    """
    if not html:
        return True, "empty_response"
    
    html_lower = html.lower()
    html_len = len(html)
    
    # 1. Very short response is suspicious
    if html_len < 2000:
        # Could be a redirect page or block page
        for pattern in BOT_BLOCK_PATTERNS:
            if re.search(pattern, html_lower):
                return True, f"short_page_with_block_signal:{pattern[:20]}"
        
        # Short but no block signals - might be legitimate thin page
        if html_len < 500:
            return True, "very_short_response"
    
    # 2. Check for explicit block patterns
    for pattern in BOT_BLOCK_PATTERNS:
        if re.search(pattern, html_lower):
            # Found block signal - but check if it's just mentioned in content
            # (e.g., "our robot vacuum" shouldn't trigger)
            matches = re.findall(pattern, html_lower)
            if len(matches) > 2:  # Multiple occurrences = likely block page
                return True, f"block_pattern:{pattern[:20]}"
    
    # 3. Check for content indicators
    content_score = 0
    for pattern in CONTENT_INDICATORS:
        if re.search(pattern, html_lower):
            content_score += 1
    
    # If very little real content found in a long page, might be JS-only
    if html_len > 10000 and content_score < 2:
        # Large HTML but no property content = probably needs JS rendering
        return True, "no_content_in_large_page"
    
    # 4. Check for SPA indicators (needs JS rendering)
    spa_indicators = [
        r'<div id="(root|app|__next)">\s*</div>',  # Empty React/Next/Vue root
        r'window\.__INITIAL_STATE__\s*=',  # SSR data (good sign actually)
        r'<noscript>.*javascript.*</noscript>',
    ]
    
    for pattern in spa_indicators:
        if re.search(pattern, html_lower):
            if content_score < 2:  # SPA without rendered content
                return True, "spa_not_rendered"
    
    return False, "content_ok"


def analyze_extraction_quality(data: dict) -> Tuple[bool, str]:
    """
    Analyze if extraction was successful enough.
    
    Returns: (is_good, reason)
    """
    # Must have at least title OR price
    has_title = bool(data.get("title") and data.get("title") != "HTML_UNPARSEABLE")
    has_price = bool(data.get("price_eur") or data.get("price"))
    
    if not has_title and not has_price:
        return False, "no_title_or_price"
    
    # Check for error indicators
    if data.get("title") == "HTML_UNPARSEABLE":
        return False, "unparseable_html"
    
    if data.get("error"):
        return False, f"extraction_error:{data.get('error')[:50]}"
    
    # Check for minimum images (most listings have photos)
    images = data.get("image_urls") or data.get("photo_urls") or []

    # Some parsers (e.g. Idealista) emit `photos: [{url, tag}, ...]` in the raw
    # extraction dict before normalization. Treat those as images too.
    if not images:
        raw_photos = data.get("photos") or []
        if isinstance(raw_photos, list):
            extracted_urls = []
            for p in raw_photos:
                if isinstance(p, str):
                    if p:
                        extracted_urls.append(p)
                    continue
                if not isinstance(p, dict):
                    continue
                url = p.get("url") or p.get("imageDataService") or p.get("src")
                if url:
                    extracted_urls.append(url)
            images = extracted_urls
    if len(images) == 0 and has_title:
        # Has title but no images - might be partial extraction
        return False, "no_images"
    
    return True, "extraction_ok"


# =============================================================================
# MAIN DECISION FUNCTION
# =============================================================================

def should_use_scrapling(
    domain: str,
    html: Optional[str] = None,
    extraction_data: Optional[dict] = None,
    status_code: int = 200,
) -> Tuple[bool, str]:
    """
    Smart decision: should we use Scrapling for this request?
    
    Call BEFORE fetch: just pass domain
    Call AFTER failed direct fetch: pass html and/or extraction_data
    
    Returns: (use_scrapling, reason)
    """
    # 1. Check if domain is known
    known, reason = domain_needs_scrapling(domain)
    if known:
        return True, reason
    
    # 2. If we have HTML, analyze it
    if html:
        blocked, block_reason = detect_bot_block(html, status_code)
        if blocked:
            # Learn this domain needs Scrapling
            save_learned_domain(domain, needs_scrapling=True)
            return True, f"detected:{block_reason}"
    
    # 3. If we have extraction data, check quality
    if extraction_data:
        good, quality_reason = analyze_extraction_quality(extraction_data)
        if not good:
            # Learn this domain needs Scrapling
            save_learned_domain(domain, needs_scrapling=True)
            return True, f"extraction_failed:{quality_reason}"
    
    return False, "direct_fetch_ok"


# =============================================================================
# UTILITY
# =============================================================================

def get_fetch_strategy(domain: str) -> dict:
    """
    Get the recommended fetch strategy for a domain.
    
    Returns config dict for fetcher.
    """
    needs_scrapling, reason = domain_needs_scrapling(domain)
    
    return {
        "use_scrapling": needs_scrapling,
        "reason": reason,
        "render_js": needs_scrapling,  # If Scrapling, also render JS
        "retry_with_scrapling": not needs_scrapling,  # If direct, allow fallback
    }

