
import {appFetch as fetch} from '@/lib/app-path';
/**
 * useTranslation Hook
 * ====================
 * 
 * React hook for multi-language translation support.
 * Uses the backend translation API powered by deep-translator.
 * 
 * Supports: EN, ES, DE, FR, CA (Catalan), IT
 */

import { useState, useCallback, useEffect } from 'react';

// API URL - uses Next.js API routes that proxy to backend
const API_URL = '';

// Supported language codes
export type LanguageCode = 'en' | 'es' | 'de' | 'fr' | 'ca' | 'it';

// Language display info with country codes for circle-flags
export const LANGUAGES: Record<LanguageCode, { label: string; flag: string; countryCode: string }> = {
  en: { label: 'English', flag: '🇬🇧', countryCode: 'gb' },
  es: { label: 'Español', flag: '🇪🇸', countryCode: 'es' },
  de: { label: 'Deutsch', flag: '🇩🇪', countryCode: 'de' },
  fr: { label: 'Français', flag: '🇫🇷', countryCode: 'fr' },
  ca: { label: 'Català', flag: '🏴', countryCode: 'es-ct' }, // Catalonia
  it: { label: 'Italiano', flag: '🇮🇹', countryCode: 'it' },
};

// Circle-flags CDN URL
export const getCircleFlagUrl = (countryCode: string) => 
  `${process.env.NEXT_PUBLIC_BASE_PATH||''}/flags/${countryCode}.svg`;

// Local storage key
const STORAGE_KEY = 'puedo_casa_language';

// Source language for all content (Spanish - Gemini responds in Spanish)
const SOURCE_LANGUAGE = 'es';

interface TranslationCache {
  [key: string]: string;
}

interface UseTranslationReturn {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  translateText: (text: string) => Promise<string>;
  translateBatch: (texts: string[]) => Promise<string[]>;
  translateListing: (data: ListingTranslateData) => Promise<ListingTranslateData>;
  isTranslating: boolean;
  isSourceLanguage: boolean;
  languages: typeof LANGUAGES;
  t: (text: string) => Promise<string>; // Shorthand for translateText
}

interface ListingTranslateData {
  title?: string;
  description?: string;
  summary?: string;
  reasons?: string[];
}

// Global cache to persist across hook instances
const globalCache: TranslationCache = {};

/**
 * Preload pre-computed translations into the global cache.
 * Call this from the listing page when the language changes — if pre-computed
 * translations exist (from the V5 pipeline), they'll be instantly available
 * via translateText/translateBatch without any API calls.
 *
 * @param listingId  The listing to fetch translations for
 * @param lang       Target language code
 * @returns          Number of translations loaded (0 if none available)
 */
export async function preloadTranslations(listingId: number, lang: LanguageCode): Promise<number> {
  if (lang === 'es') return 0; // Source language — nothing to preload

  try {
    const resp = await fetch(`/api/listings/${listingId}/translations?lang=${lang}`, { cache: "no-store" });
    const json = await resp.json();
    if (!json?.hasTranslations || !json?.translations) return 0;

    const translations = json.translations as Record<string, string>;
    let count = 0;
    for (const [sourceText, translatedText] of Object.entries(translations)) {
      if (sourceText && translatedText) {
        globalCache[getCacheKey(sourceText, lang)] = translatedText;
        count++;
      }
    }
    return count;
  } catch {
    return 0;
  }
}

function getCacheKey(text: string, targetLang: string): string {
  return `${targetLang}:${text}`;
}

export function useTranslation(): UseTranslationReturn {
  // Start with default Spanish - sync with localStorage in useEffect to avoid hydration mismatch
  const [language, setLanguageState] = useState<LanguageCode>('es');
  const [isTranslating, setIsTranslating] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);

  // Always start in Spanish (source language).
  // The user can switch manually; we persist their choice for future sessions
  // but we do NOT auto-restore it — every fresh page load starts in Spanish
  // because the source data is Spanish and we want instant first render.
  useEffect(() => {
    setIsHydrated(true);
  }, []);

  // Persist language choice
  const setLanguage = useCallback((lang: LanguageCode) => {
    console.log('[useTranslation] Setting language to:', lang);
    setLanguageState(lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }, []);

  // Check if we're using the source language (no translation needed)
  const isSourceLanguage = language === SOURCE_LANGUAGE;

  // Translate single text
  const translateText = useCallback(async (
    text: string
  ): Promise<string> => {
    if (!text || !text.trim()) return text;
    
    // If target is Spanish (source language), no translation needed
    if (language === SOURCE_LANGUAGE) {
      return text;
    }
    
    // Check cache
    const cacheKey = getCacheKey(text, language);
    if (globalCache[cacheKey]) {
      return globalCache[cacheKey];
    }
    
    setIsTranslating(true);
    try {
      const response = await fetch(`${API_URL}/api/translate/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          target_lang: language,
          source_lang: SOURCE_LANGUAGE,
        }),
      });
      
      if (!response.ok) {
        console.warn('Translation API error:', response.status);
        return text;
      }
      
      const data = await response.json();
      const translated = data.translated || text;
      
      // Cache result
      globalCache[cacheKey] = translated;
      
      return translated;
    } catch (error) {
      console.error('Translation error:', error);
      return text;
    } finally {
      setIsTranslating(false);
    }
  }, [language]);

  // Translate batch of texts
  const translateBatch = useCallback(async (
    texts: string[]
  ): Promise<string[]> => {
    if (!texts.length) return [];
    
    // If target is Spanish (source), return as-is
    if (language === SOURCE_LANGUAGE) {
      return texts;
    }
    
    // Check what's cached vs what needs translation
    const results: string[] = [];
    const toTranslate: { index: number; text: string }[] = [];
    
    texts.forEach((text, index) => {
      const cacheKey = getCacheKey(text, language);
      if (globalCache[cacheKey]) {
        results[index] = globalCache[cacheKey];
      } else if (text && text.trim()) {
        toTranslate.push({ index, text });
      } else {
        results[index] = text;
      }
    });
    
    // If all cached, return
    if (toTranslate.length === 0) {
      return results;
    }
    
    setIsTranslating(true);
    try {
      const response = await fetch(`${API_URL}/api/translate/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texts: toTranslate.map(t => t.text),
          target_lang: language,
          source_lang: SOURCE_LANGUAGE,
        }),
      });
      
      if (!response.ok) {
        console.warn('Batch translation API error:', response.status);
        // Fill in originals for failed translations
        toTranslate.forEach(({ index, text }) => {
          results[index] = text;
        });
        return results;
      }
      
      const data = await response.json();
      const translations = data.translations || [];
      
      // Map back to original positions and cache
      toTranslate.forEach(({ index, text }, i) => {
        const translated = translations[i] || text;
        results[index] = translated;
        globalCache[getCacheKey(text, language)] = translated;
      });
      
      return results;
    } catch (error) {
      console.error('Batch translation error:', error);
      // Return originals on error
      toTranslate.forEach(({ index, text }) => {
        results[index] = text;
      });
      return results;
    } finally {
      setIsTranslating(false);
    }
  }, [language]);

  // Translate listing-specific fields.
  // WHY cache-first: preloadTranslations seeds the global cache from the pipeline.
  // If all fields are cached, we skip the API call entirely → instant switch.
  const translateListing = useCallback(async (
    data: ListingTranslateData
  ): Promise<ListingTranslateData> => {
    // If target is Spanish (source), return as-is
    if (language === SOURCE_LANGUAGE) {
      return data;
    }

    // ── Check global cache for every field first ──
    const cachedTitle = data.title ? globalCache[getCacheKey(data.title, language)] : undefined;
    const cachedDesc = data.description ? globalCache[getCacheKey(data.description, language)] : undefined;
    const cachedSummary = data.summary ? globalCache[getCacheKey(data.summary, language)] : undefined;
    const cachedReasons = data.reasons?.map(r => globalCache[getCacheKey(r, language)]);
    const allReasonsCached = !data.reasons || cachedReasons?.every(Boolean);

    const titleOk = !data.title || cachedTitle;
    const descOk = !data.description || cachedDesc;
    const summaryOk = !data.summary || cachedSummary;

    if (titleOk && descOk && summaryOk && allReasonsCached) {
      // Everything is in cache — return instantly, no API call
      console.log('[useTranslation] All fields served from cache — instant switch');
      return {
        title: cachedTitle || data.title,
        description: cachedDesc || data.description,
        summary: cachedSummary || data.summary,
        reasons: cachedReasons as string[] || data.reasons,
      };
    }
    
    // ── Fallback: call the translation API for uncached fields ──
    setIsTranslating(true);
    try {
      const response = await fetch(`${API_URL}/api/translate/listing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: cachedTitle ? undefined : data.title,
          description: cachedDesc ? undefined : data.description,
          summary: cachedSummary ? undefined : data.summary,
          reasons: allReasonsCached ? undefined : data.reasons,
          target_lang: language,
          source_lang: SOURCE_LANGUAGE,
        }),
      });
      
      if (!response.ok) {
        console.warn('Listing translation API error:', response.status);
        return data;
      }
      
      const result = await response.json();
      
      // Cache individual translations
      if (data.title && result.title) {
        globalCache[getCacheKey(data.title, language)] = result.title;
      }
      if (data.description && result.description) {
        globalCache[getCacheKey(data.description, language)] = result.description;
      }
      if (data.summary && result.summary) {
        globalCache[getCacheKey(data.summary, language)] = result.summary;
      }
      if (data.reasons && result.reasons) {
        data.reasons.forEach((reason: string, i: number) => {
          if (result.reasons[i]) {
            globalCache[getCacheKey(reason, language)] = result.reasons[i];
          }
        });
      }
      
      return {
        title: cachedTitle || result.title || data.title,
        description: cachedDesc || result.description || data.description,
        summary: cachedSummary || result.summary || data.summary,
        reasons: allReasonsCached ? (cachedReasons as string[]) : (result.reasons || data.reasons),
      };
    } catch (error) {
      console.error('Listing translation error:', error);
      return data;
    } finally {
      setIsTranslating(false);
    }
  }, [language]);

  return {
    language,
    setLanguage,
    translateText,
    translateBatch,
    translateListing,
    isTranslating,
    isSourceLanguage,
    languages: LANGUAGES,
    t: translateText, // Shorthand alias
  };
}

export default useTranslation;

