"""
🔍 URL Validator - Gemini 2.5 Flash Lite
========================================

Quick validation to check if a URL is a property listing.
Cost: ~$0.075/M input tokens. Fast: ~200-500ms.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", '')
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = "gemini-2.5-flash-lite"

_client = None

def get_client():
    """Get or create Vertex AI client."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
    return _client


# =============================================================================
# SCHEMA & PROMPT
# =============================================================================

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_property_listing": {
            "type": "boolean",
        },
        "reason": {
            "type": "string",
        }
    },
    "required": ["is_property_listing", "reason"]
}

SYSTEM_PROMPT = """You validate URLs for a property search app.

A property listing is a webpage showing a SINGLE property (apartment, house, flat, villa, land, etc.) for sale or rent. It can be from any country in the world.

Return true if the URL points to a single property listing page.
Return false for anything else: search results, homepages, news, e-commerce, tech sites, etc."""


# =============================================================================
# VALIDATION
# =============================================================================

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: str
    detected_type: str
    rejection_reason: Optional[str] = None
    error: Optional[str] = None


async def validate_listing_url(url: str, html_snippet: str = "") -> ValidationResult:
    """Validate if URL is a property listing using Flash Lite."""
    logger.info(f"🔍 Validating: {url[:60]}...")
    
    try:
        client = get_client()
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=f"Is this a property listing URL?\n\n{url}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,
                max_output_tokens=100,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        
        if not response.text:
            logger.warning("Empty response")
            return ValidationResult(is_valid=True, confidence="low", detected_type="unknown", error="Empty response")
        
        data = json.loads(response.text)
        is_valid = data.get("is_property_listing", False)
        reason = data.get("reason", "")
        
        if is_valid:
            logger.info(f"   ✅ Valid: {reason}")
        else:
            logger.info(f"   ❌ Rejected: {reason}")
        
        return ValidationResult(
            is_valid=is_valid,
            confidence="high",
            detected_type="single_listing" if is_valid else "other",
            rejection_reason=None if is_valid else reason,
        )
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return ValidationResult(is_valid=True, confidence="low", detected_type="unknown", error=str(e))
