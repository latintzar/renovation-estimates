"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// ============ TRANSLATIONS ============

export type Language = 'es' | 'en';

export const translations = {
  es: {
    // Navigation
    nav: {
      speakWithLeo: "Habla con Leo",
      properties: "Propiedades",
      profile: "Mi Perfil",
      settings: "Configuración",
      signOut: "Cerrar sesión",
    },
    
    // Dashboard
    dashboard: {
      title: "Mis Propiedades",
      subtitle: "Leo ha encontrado {count} propiedades nuevas para ti",
      recommended: "Recomendadas",
      saved: "Guardados",
      viewed: "Visitados",
      notes: "Notas",
      viewAll: "Ver todas",
      noSaved: "Aún no has guardado ninguna propiedad",
      noSavedDescription: "Guarda las propiedades que te interesen para verlas aquí",
      explore: "Explorar propiedades",
    },
    
    // Profile
    profile: {
      title: "Mi Perfil",
      subtitle: "Así es como Leo entiende tu búsqueda",
      leoUnderstands: "Leo te entiende así",
      tellLeo: "Cuéntale a Leo lo que buscas",
      tellLeoDescription: "Después de tu conversación, Leo mostrará aquí un resumen de tus necesidades",
      whatILookFor: "Lo que busco",
      budget: "Presupuesto",
      bedrooms: "Habitaciones",
      preferredAreas: "Zonas preferidas",
      workLocation: "Lugar de trabajo",
      maxCommute: "Commute máximo",
      minutes: "minutos",
      notDefined: "No definido",
      additionalNotes: "Notas adicionales",
      wantToChange: "¿Hay algo que quieras cambiar?",
      tellLeoUpdate: "Cuéntaselo a Leo y actualizará tu perfil",
    },
    
    // Settings
    settings: {
      title: "Configuración",
      subtitle: "Personaliza tu experiencia en Leo.casa",
      language: "Idioma",
      languageDescription: "Elige el idioma de la aplicación y de Leo",
      spanish: "Español",
      spanishDescription: "Leo hablará contigo en español",
      english: "English",
      englishDescription: "Leo will speak with you in English",
      notifications: "Notificaciones",
      privacy: "Privacidad",
      comingSoon: "Próximamente",
      saving: "Guardando...",
      saved: "Guardado",
    },
    
    // Speak with Leo
    speakWithLeo: {
      titleOnboarding: "Conoce a Leo",
      subtitleOnboarding: "Cuéntame sobre tu vida y lo que buscas. En 2-3 minutos sabré exactamente qué tipo de casa necesitas.",
      titleFollowup: "Habla con Leo",
      subtitleFollowup: "¿Hay algo que quieras actualizar sobre tu búsqueda? Cuéntame cualquier cambio.",
      preferChat: "Prefiero escribir",
      chatWith: "Chat con Leo",
      voice: "Voz",
      write: "Escribir",
      connecting: "Conectando...",
      leoSpeaking: "Leo está hablando",
      listening: "Te escucho...",
      readyToTalk: "Listo",
      tellMe: "Cuéntame lo que buscas",
      pressToStart: "Pulsa para empezar",
      startConversation: "Hablar con Leo",
      finish: "Finalizar llamada",
      analyzing: "Guardando perfil...",
      typeHere: "Escribe aquí...",
      profileUpdated: "Perfil actualizado",
      leoKnows: "Leo ha guardado los cambios.",
      goToProperties: "Ver propiedades",
      suggestions: ["Estoy buscando piso para mí", "Somos familia con niños", "Busco algo tranquilo"],
      suggestionsFollowup: ["Mi presupuesto ha cambiado", "Busco otra zona", "Necesito más habitaciones"],
    },
    
    // Property
    property: {
      fitScore: "Tu Fit Score",
      compatibility: "compatibilidad",
      save: "Guardar",
      saved: "Guardado",
      original: "Original",
      wantToSee: "Quiero verlo",
      alreadyVisited: "Ya la visité",
      visited: "Visitada",
      myNotes: "Mis notas",
      notesAboutProperty: "Apuntes sobre esta propiedad",
      writeNote: "Escribe una nota...",
      photo: "Foto",
      voice: "Voz",
      add: "Añadir",
      adding: "Añadiendo...",
      noNotes: "Aún no tienes notas",
      back: "Volver",
      beds: "hab.",
      baths: "baño",
      perMonth: "/mes",
    },
    
    // Common
    common: {
      loading: "Cargando...",
      error: "Error",
      retry: "Reintentar",
      cancel: "Cancelar",
      confirm: "Confirmar",
      delete: "Eliminar",
      edit: "Editar",
      save: "Guardar",
      close: "Cerrar",
    },
  },
  
  en: {
    // Navigation
    nav: {
      speakWithLeo: "Speak with Leo",
      properties: "Properties",
      profile: "My Profile",
      settings: "Settings",
      signOut: "Sign out",
    },
    
    // Dashboard
    dashboard: {
      title: "My Properties",
      subtitle: "Leo has found {count} new properties for you",
      recommended: "Recommended",
      saved: "Saved",
      viewed: "Viewed",
      notes: "Notes",
      viewAll: "View all",
      noSaved: "You haven't saved any properties yet",
      noSavedDescription: "Save properties you're interested in to see them here",
      explore: "Explore properties",
    },
    
    // Profile
    profile: {
      title: "My Profile",
      subtitle: "This is how Leo understands your search",
      leoUnderstands: "Leo understands you like this",
      tellLeo: "Tell Leo what you're looking for",
      tellLeoDescription: "After your conversation, Leo will show a summary of your needs here",
      whatILookFor: "What I'm looking for",
      budget: "Budget",
      bedrooms: "Bedrooms",
      preferredAreas: "Preferred areas",
      workLocation: "Work location",
      maxCommute: "Max commute",
      minutes: "minutes",
      notDefined: "Not defined",
      additionalNotes: "Additional notes",
      wantToChange: "Want to change something?",
      tellLeoUpdate: "Tell Leo and he'll update your profile",
    },
    
    // Settings
    settings: {
      title: "Settings",
      subtitle: "Customize your Leo.casa experience",
      language: "Language",
      languageDescription: "Choose the app and Leo's language",
      spanish: "Español",
      spanishDescription: "Leo hablará contigo en español",
      english: "English",
      englishDescription: "Leo will speak with you in English",
      notifications: "Notifications",
      privacy: "Privacy",
      comingSoon: "Coming soon",
      saving: "Saving...",
      saved: "Saved",
    },
    
    // Speak with Leo
    speakWithLeo: {
      titleOnboarding: "Meet Leo",
      subtitleOnboarding: "Tell me about your life and what you're looking for. In 2-3 minutes I'll know exactly what kind of home you need.",
      titleFollowup: "Speak with Leo",
      subtitleFollowup: "Anything you want to update about your search? Tell me any changes.",
      preferChat: "I prefer to type",
      chatWith: "Chat with Leo",
      voice: "Voice",
      write: "Type",
      connecting: "Connecting...",
      leoSpeaking: "Leo is speaking",
      listening: "I'm listening...",
      readyToTalk: "Ready",
      tellMe: "Tell me what you're looking for",
      pressToStart: "Press to start",
      startConversation: "Speak with Leo",
      finish: "End call",
      analyzing: "Saving profile...",
      typeHere: "Type here...",
      profileUpdated: "Profile updated",
      leoKnows: "Leo saved your changes.",
      goToProperties: "See properties",
      suggestions: ["I'm looking for an apartment", "We're a family with kids", "Looking for something quiet"],
      suggestionsFollowup: ["My budget changed", "Looking for another area", "Need more bedrooms"],
    },
    
    // Property
    property: {
      fitScore: "Your Fit Score",
      compatibility: "compatibility",
      save: "Save",
      saved: "Saved",
      original: "Original",
      wantToSee: "I want to see it",
      alreadyVisited: "Already visited",
      visited: "Visited",
      myNotes: "My notes",
      notesAboutProperty: "Notes about this property",
      writeNote: "Write a note...",
      photo: "Photo",
      voice: "Voice",
      add: "Add",
      adding: "Adding...",
      noNotes: "No notes yet",
      back: "Back",
      beds: "beds",
      baths: "bath",
      perMonth: "/month",
    },
    
    // Common
    common: {
      loading: "Loading...",
      error: "Error",
      retry: "Retry",
      cancel: "Cancel",
      confirm: "Confirm",
      delete: "Delete",
      edit: "Edit",
      save: "Save",
      close: "Close",
    },
  },
} as const;

// Create a more generic type that allows for any string values in the translation objects
type DeepStringify<T> = T extends string ? string : { [K in keyof T]: DeepStringify<T[K]> };
export type Translations = DeepStringify<typeof translations.es>;

export function getTranslations(lang: Language): Translations {
  return translations[lang] || translations.es;
}

// ============ CONTEXT ============

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => Promise<void>;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

interface LanguageProviderProps {
  children: ReactNode;
  initialLanguage?: Language;
}

export function LanguageProvider({ children, initialLanguage = 'es' }: LanguageProviderProps) {
  const [language, setLanguageState] = useState<Language>(initialLanguage);
  const [t, setT] = useState<Translations>(getTranslations(initialLanguage));

  // Update translations when language changes
  useEffect(() => {
    setT(getTranslations(language));
  }, [language]);

  // Set language and persist to backend
  const setLanguage = useCallback(async (newLang: Language) => {
    setLanguageState(newLang);
    
    // Persist to backend
    try {
      await fetch('/api/user/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLang }),
      });
    } catch (error) {
      console.error('Failed to save language preference:', error);
    }
  }, []);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

// Hook for components that only need translations (read-only)
export function useTranslations() {
  const { t } = useLanguage();
  return t;
}

