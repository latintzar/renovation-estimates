import esDict from '@/dictionaries/es.json';
import enDict from '@/dictionaries/en.json';

export type Locale = 'es' | 'en';

export const locales: Locale[] = ['es', 'en'];
export const defaultLocale: Locale = 'es';

// Dictionary type based on our JSON structure
export type Dictionary = typeof esDict;

const dictionaries: Record<Locale, Dictionary> = {
  es: esDict,
  en: enDict,
};

export const getDictionary = (locale: Locale): Dictionary => {
  if (!dictionaries[locale]) {
    console.warn(`Dictionary not found for locale: ${locale}, falling back to ${defaultLocale}`);
    return dictionaries[defaultLocale];
  }
  return dictionaries[locale];
};

// Helper to get nested dictionary values
export function t(dict: Dictionary, key: string): string {
  const keys = key.split('.');
  let value: unknown = dict;
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = (value as Record<string, unknown>)[k];
    } else {
      console.warn(`Translation key not found: ${key}`);
      return key;
    }
  }
  
  if (typeof value === 'string') {
    return value;
  }
  
  console.warn(`Translation value is not a string: ${key}`);
  return key;
}
