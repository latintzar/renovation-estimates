"""
Description Formatter
=====================

Post-processing step to clean up property descriptions into nice markdown.
Uses Gemini 2.5 Flash with temperature 0 for deterministic formatting.

This runs AFTER both idealista and universal parsers, cleaning up the raw text
into clean, readable markdown without changing what it says.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def format_description_markdown(description: Optional[str]) -> Optional[str]:
    """
    Format a property description into clean markdown.
    
    - Preserves ALL original content (no additions, no removals)
    - Adds proper paragraphs, bullet points, and structure
    - Cleans up messy spacing and formatting
    - Uses temperature 0 for deterministic output
    
    Args:
        description: Raw description text from scraper
        
    Returns:
        Formatted markdown string, or original if formatting fails
    """
    if not description or len(description.strip()) < 20:
        return description
    
    try:
        # Import here to avoid circular imports
        from pipeline.gemini_client import call_gemini
        
        prompt = f"""Format this property listing description into clean, readable markdown.

RULES:
1. DO NOT change, add, or remove ANY content - preserve everything exactly as written
2. DO NOT translate - keep the original language
3. DO NOT add opinions, summaries, or interpretations
4. DO organize into logical paragraphs and sections
5. Use bullet points (•) for lists of features/amenities
6. Use **bold** for emphasis on key details like rooms, sizes, locations
7. Clean up messy spacing, line breaks, and formatting
8. Remove redundant whitespace but keep paragraph breaks meaningful
9. If there are ALL CAPS sections, convert to normal Title Case
10. Output ONLY the formatted description, nothing else

DESCRIPTION TO FORMAT:
{description}

FORMATTED MARKDOWN:"""

        response = await call_gemini(
            prompt=prompt,
            model="flash",  # gemini-2.5-flash for speed
            temperature=0,  # Deterministic output
            max_tokens=4096,
            use_spanish=False,  # Don't force Spanish - preserve original language
        )
        
        if response.success and response.text:
            formatted = response.text.strip()
            
            # Basic validation - shouldn't be drastically different in length
            original_len = len(description)
            formatted_len = len(formatted)
            
            # Allow up to 50% change in length (formatting can add/remove whitespace)
            if 0.5 < (formatted_len / original_len) < 1.5:
                logger.info(f"✨ Description formatted: {original_len} → {formatted_len} chars")
                return formatted
            else:
                logger.warning(f"⚠️ Formatted description length suspicious: {original_len} → {formatted_len}, using original")
                return description
        else:
            logger.warning(f"⚠️ Description formatting failed: {response.error}")
            return description
            
    except Exception as e:
        logger.error(f"❌ Description formatting error: {e}")
        return description

