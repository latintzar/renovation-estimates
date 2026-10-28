"use client";

import { createContext, useContext } from "react";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n";

interface DictionaryContextType {
  dictionary: Dictionary;
  locale: Locale;
}

const DictionaryContext = createContext<DictionaryContextType | null>(null);

export function DictionaryProvider({
  children,
  dictionary,
  locale,
}: {
  children: React.ReactNode;
  dictionary: Dictionary;
  locale: Locale;
}) {
  return (
    <DictionaryContext.Provider value={{ dictionary, locale }}>
      {children}
    </DictionaryContext.Provider>
  );
}

export function useDictionary() {
  const context = useContext(DictionaryContext);
  if (!context) {
    throw new Error("useDictionary must be used within a DictionaryProvider");
  }
  return context;
}

