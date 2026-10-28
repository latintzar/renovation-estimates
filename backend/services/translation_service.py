"""
Translation Service
====================

Multi-language translation using deep-translator.
Supports: EN, ES, DE, FR, CA (Catalan), IT

Uses Google Translate (free, no API key needed).
"""

import logging
from typing import Optional, List, Dict
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

# Language codes mapping
SUPPORTED_LANGUAGES = {
    "en": "english",
    "es": "spanish",
    "de": "german",
    "fr": "french",
    "ca": "catalan",
    "it": "italian",
}

# Display names for UI
LANGUAGE_LABELS = {
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "ca": "Català",
    "it": "Italiano",
}


class TranslationService:
    """
    Handles text translation between supported languages.
    Uses Google Translate under the hood (free tier).
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def _get_cache_key(self, text: str, source: str, target: str) -> str:
        """Generate cache key for translation."""
        return f"{source}:{target}:{hash(text)}"
    
    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "es"  # Default source is Spanish (Gemini responds in Spanish)
    ) -> Optional[str]:
        """
        Translate a single text string.
        
        Args:
            text: Text to translate
            target_lang: Target language code (en, es, de, fr, ca, it)
            source_lang: Source language code or 'auto' for detection
            
        Returns:
            Translated text or None if failed
        """
        if not text or not text.strip():
            return text
            
        # Validate target language
        if target_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported target language: {target_lang}")
            return text
        
        # Check cache
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            
            # Cache result
            self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Return original on failure
    
    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "es"  # Default source is Spanish (Gemini responds in Spanish)
    ) -> List[str]:
        """
        Translate multiple texts efficiently.
        
        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code or 'auto'
            
        Returns:
            List of translated texts (same order)
        """
        if not texts:
            return []
            
        if target_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported target language: {target_lang}")
            return texts
        
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            
            # Filter empty strings, translate, then restore order
            results = []
            for text in texts:
                if not text or not text.strip():
                    results.append(text)
                    continue
                    
                cache_key = self._get_cache_key(text, source_lang, target_lang)
                if cache_key in self._cache:
                    results.append(self._cache[cache_key])
                else:
                    translated = translator.translate(text)
                    self._cache[cache_key] = translated
                    results.append(translated)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            return texts  # Return originals on failure
    
    def translate_dict(
        self,
        data: Dict[str, str],
        target_lang: str,
        source_lang: str = "es",  # Default source is Spanish (Gemini responds in Spanish)
        keys_to_translate: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Translate string values in a dictionary.
        
        Args:
            data: Dictionary with string values
            target_lang: Target language code
            source_lang: Source language code or 'auto'
            keys_to_translate: Optional list of specific keys to translate
            
        Returns:
            Dictionary with translated values
        """
        if not data:
            return data
            
        result = dict(data)
        
        for key, value in data.items():
            # Skip if not a string
            if not isinstance(value, str):
                continue
                
            # Skip if keys_to_translate is specified and key not in list
            if keys_to_translate and key not in keys_to_translate:
                continue
                
            translated = self.translate_text(value, target_lang, source_lang)
            if translated:
                result[key] = translated
        
        return result


# Singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create translation service singleton."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def get_supported_languages() -> Dict[str, str]:
    """Return dict of supported language codes and display names."""
    return LANGUAGE_LABELS.copy()

