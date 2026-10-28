"""
Translation API Routes
=======================

Endpoints for multi-language translation.
Supports: EN, ES, DE, FR, CA (Catalan), IT
"""

import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.translation_service import (
    get_translation_service,
    get_supported_languages,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class TranslateTextRequest(BaseModel):
    """Request to translate a single text."""
    text: str
    target_lang: str
    source_lang: str = "auto"


class TranslateTextResponse(BaseModel):
    """Response with translated text."""
    original: str
    translated: str
    target_lang: str
    source_lang: str


class TranslateBatchRequest(BaseModel):
    """Request to translate multiple texts."""
    texts: List[str]
    target_lang: str
    source_lang: str = "auto"


class TranslateBatchResponse(BaseModel):
    """Response with translated texts."""
    translations: List[str]
    target_lang: str
    source_lang: str
    count: int


class TranslateListingRequest(BaseModel):
    """Request to translate listing-specific fields."""
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    reasons: Optional[List[str]] = None
    target_lang: str
    source_lang: str = "auto"


class TranslateListingResponse(BaseModel):
    """Response with translated listing fields."""
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    reasons: Optional[List[str]] = None
    target_lang: str


class SupportedLanguagesResponse(BaseModel):
    """List of supported languages."""
    languages: Dict[str, str]


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/translate/languages", response_model=SupportedLanguagesResponse)
async def list_languages():
    """
    Get list of supported languages.
    
    Returns language codes and display names:
    - en: English
    - es: Español
    - de: Deutsch
    - fr: Français
    - ca: Català
    - it: Italiano
    """
    return SupportedLanguagesResponse(languages=get_supported_languages())


@router.post("/translate/text", response_model=TranslateTextResponse)
async def translate_text(request: TranslateTextRequest):
    """
    Translate a single text string.
    
    Example:
    ```
    POST /api/translate/text
    {
        "text": "Esta casa tiene tres habitaciones",
        "target_lang": "en"
    }
    ```
    """
    if request.target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {request.target_lang}. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    
    service = get_translation_service()
    translated = service.translate_text(
        text=request.text,
        target_lang=request.target_lang,
        source_lang=request.source_lang
    )
    
    return TranslateTextResponse(
        original=request.text,
        translated=translated or request.text,
        target_lang=request.target_lang,
        source_lang=request.source_lang
    )


@router.post("/translate/batch", response_model=TranslateBatchResponse)
async def translate_batch(request: TranslateBatchRequest):
    """
    Translate multiple texts at once.
    
    More efficient for translating many strings.
    
    Example:
    ```
    POST /api/translate/batch
    {
        "texts": ["Cocina moderna", "Baño reformado", "Terraza exterior"],
        "target_lang": "en"
    }
    ```
    """
    if request.target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {request.target_lang}"
        )
    
    if len(request.texts) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 texts per batch"
        )
    
    service = get_translation_service()
    translations = service.translate_batch(
        texts=request.texts,
        target_lang=request.target_lang,
        source_lang=request.source_lang
    )
    
    return TranslateBatchResponse(
        translations=translations,
        target_lang=request.target_lang,
        source_lang=request.source_lang,
        count=len(translations)
    )


@router.post("/translate/listing", response_model=TranslateListingResponse)
async def translate_listing(request: TranslateListingRequest):
    """
    Translate listing-specific fields (title, description, summary, reasons).
    
    Optimized for property listing content.
    
    Example:
    ```
    POST /api/translate/listing
    {
        "title": "Piso reformado en el centro",
        "description": "Amplio piso de 3 habitaciones...",
        "summary": "Propiedad en buen estado general",
        "reasons": ["Cocina moderna", "Buena iluminación"],
        "target_lang": "en"
    }
    ```
    """
    if request.target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {request.target_lang}"
        )
    
    service = get_translation_service()
    
    # Translate each field
    translated_title = None
    translated_description = None
    translated_summary = None
    translated_reasons = None
    
    if request.title:
        translated_title = service.translate_text(
            request.title, request.target_lang, request.source_lang
        )
    
    if request.description:
        translated_description = service.translate_text(
            request.description, request.target_lang, request.source_lang
        )
    
    if request.summary:
        translated_summary = service.translate_text(
            request.summary, request.target_lang, request.source_lang
        )
    
    if request.reasons:
        translated_reasons = service.translate_batch(
            request.reasons, request.target_lang, request.source_lang
        )
    
    return TranslateListingResponse(
        title=translated_title,
        description=translated_description,
        summary=translated_summary,
        reasons=translated_reasons,
        target_lang=request.target_lang
    )

