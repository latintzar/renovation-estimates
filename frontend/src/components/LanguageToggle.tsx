/**
 * LanguageToggle Component
 * ========================
 * 
 * Minimal language selector with circle flag icons and text codes.
 * Supports: EN, ES, DE, FR, CA (Catalan), IT
 */

"use client";

import React from 'react';
import Image from 'next/image';
import { Loader2 } from 'lucide-react';
import { useAppStrings } from '@/hooks/AppStringsContext';
import { LANGUAGES, getCircleFlagUrl, type LanguageCode } from '@/hooks/useTranslation';

interface LanguageToggleProps {
  className?: string;
  showLabel?: boolean;
  compact?: boolean;
  currentLocale?: string;
}

export function LanguageToggle({ 
  className = '', 
  showLabel = false,
  compact = false,
}: LanguageToggleProps) {
  const { language, setLanguage, isTranslating, s } = useAppStrings();
  
  const languageCodes = Object.keys(LANGUAGES) as LanguageCode[];

  const handleLanguageChange = (newLang: LanguageCode) => {
    setLanguage(newLang);
  };

  if (compact) {
    // Ultra-compact: circle flag + text code, cycles on tap
    const currentLang = LANGUAGES[language];
    const nextIndex = (languageCodes.indexOf(language) + 1) % languageCodes.length;
    const cycleLanguage = () => handleLanguageChange(languageCodes[nextIndex]);
    
    return (
      <button
        onClick={cycleLanguage}
        disabled={isTranslating}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-full hover:bg-stone-100 transition-colors disabled:opacity-50 ${className}`}
        title={`${currentLang.label} - ${s.tapToChange}`}
        aria-label={`${s.currentLanguage}: ${currentLang.label}. ${s.tapToChange}.`}
      >
        {isTranslating ? (
          <Loader2 className="w-4 h-4 animate-spin text-[#da654d]" />
        ) : (
          <>
            <Image
              src={getCircleFlagUrl(currentLang.countryCode)}
              alt={currentLang.label}
              width={16}
              height={16}
              className="rounded-full"
              unoptimized
            />
            <span className="text-xs font-medium text-stone-600 uppercase">{language}</span>
          </>
        )}
      </button>
    );
  }

  // Full pill buttons style with circle flags
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {showLabel && (
        <div className="flex items-center gap-1.5 text-sm text-stone-500 mr-1">
          {isTranslating && <Loader2 className="w-4 h-4 animate-spin text-[#da654d]" />}
          <span className="hidden sm:inline">{s.language}</span>
        </div>
      )}
      
      <div className="flex flex-wrap gap-1 bg-stone-100 rounded-xl p-1">
        {languageCodes.map((code) => {
          const isActive = language === code;
          const { label, countryCode } = LANGUAGES[code];
          
          return (
            <button
              key={code}
              onClick={() => handleLanguageChange(code)}
              disabled={isTranslating}
              className={`
                px-2.5 py-1.5 rounded-lg text-xs font-medium uppercase
                transition-all duration-200 flex items-center gap-1.5
                disabled:opacity-50 disabled:cursor-not-allowed
                ${isActive 
                  ? 'bg-white text-stone-900 shadow-sm' 
                  : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50'
                }
              `}
              title={label}
              aria-label={`${s.switchTo} ${label}`}
              aria-pressed={isActive}
            >
              <Image
                src={getCircleFlagUrl(countryCode)}
                alt={label}
                width={14}
                height={14}
                className="rounded-full"
                unoptimized
              />
              <span>{code}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default LanguageToggle;

