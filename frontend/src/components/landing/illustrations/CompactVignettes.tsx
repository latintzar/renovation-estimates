"use client";

import React from "react";
import Image from "next/image";
import { 
  MessageCircle, 
  MapPin, 
  Sun, 
  Volume2, 
  Clock, 
  Heart, 
  X as XIcon,
  ThumbsUp,
  ThumbsDown,
  Camera,
  Sparkles,
  ChevronRight,
  Check,
  AlertTriangle,
  Home,
  Train,
  Coffee,
  Send
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LANDING_IMAGES } from "./LandingImages";
import { useDictionary } from "@/contexts/DictionaryContext";

// ============================================================================
// RENTERS VIGNETTES - Compact 150px elements for "How it Works"
// ============================================================================

/**
 * Step 1: "Tell Leo how you live"
 * ElevenLabs-style amorphous voice orb with animated waveform
 */
export const VignetteLeoAsks = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[220px] bg-gradient-to-b from-stone-950 to-stone-900 rounded-2xl shadow-2xl overflow-hidden", className)}>
      {/* Call header */}
      <div className="px-3 py-2 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[10px] text-stone-400 font-medium">
            {isEs ? 'Llamada con Leo' : 'Voice call with Leo'}
          </span>
        </div>
        <span className="text-[9px] text-stone-500">2:34</span>
      </div>
      
      {/* Amorphous Voice Orb - ElevenLabs style */}
      <div className="flex justify-center py-6 relative">
        {/* Outer glow */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div 
            className="w-28 h-28 rounded-full opacity-30 blur-xl"
            style={{
              background: 'conic-gradient(from 0deg, #10b981, #f472b6, #fbbf24, #10b981)',
              animation: 'spin 8s linear infinite'
            }}
          />
        </div>
        
        {/* Main amorphous orb */}
        <div 
          className="relative w-20 h-20 z-10"
          style={{
            borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%',
            background: 'conic-gradient(from 180deg at 50% 50%, #10b981 0deg, #f9a8d4 60deg, #fde68a 120deg, #10b981 180deg, #f9a8d4 240deg, #fde68a 300deg, #10b981 360deg)',
            animation: 'morphOrb 8s ease-in-out infinite, spin 12s linear infinite reverse',
            boxShadow: '0 0 40px rgba(16, 185, 129, 0.3), inset 0 0 30px rgba(255, 255, 255, 0.1)'
          }}
        >
          {/* Inner white circle with waveform */}
          <div className="absolute inset-3 rounded-full bg-white flex items-center justify-center shadow-inner">
            {/* Animated waveform bars */}
            <div className="flex items-center gap-[2px]">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-[3px] bg-stone-800 rounded-full"
                  style={{
                    height: '16px',
                    animation: 'waveform 0.8s ease-in-out infinite',
                    animationDelay: `${i * 0.1}s`
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Transcribed conversation */}
      <div className="px-3 pb-3 space-y-2">
        {/* Leo's question (transcribed) */}
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-emerald-400 to-pink-400 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-[8px] text-white font-bold">L</span>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl rounded-tl-none px-2.5 py-1.5 text-[10px] text-stone-300">
            {isEs ? '"¿Dónde trabajas?"' : '"Where do you work?"'}
          </div>
        </div>
        
        {/* User's response (transcribed) */}
        <div className="flex items-start gap-2 justify-end">
          <div className="bg-emerald-500/40 backdrop-blur rounded-xl rounded-tr-none px-2.5 py-1.5 text-[10px] text-emerald-100">
            {isEs ? '"Cerca de Diagonal, unos 20 min en metro"' : '"Near Diagonal, takes me like 20 min by metro"'}
          </div>
        </div>
        
        {/* Leo thinking */}
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-emerald-400 to-pink-400 flex items-center justify-center shrink-0">
            <span className="text-[8px] text-white font-bold">L</span>
          </div>
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 2: "Get rentals worth seeing"
 * Property card with match explanation - now with real image
 */
export const VignettePropertyMatch = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[180px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Real apartment image */}
      <div className="h-20 relative">
        <Image
          src={LANDING_IMAGES.propertyCardApartment}
          alt={isEs ? "Piso bonito en Gràcia" : "Beautiful apartment in Gràcia"}
          fill
          className="object-cover"
          sizes="180px"
        />
        <div className="absolute top-2 left-2 px-1.5 py-0.5 bg-emerald-500 text-white text-[9px] font-bold rounded shadow-sm">
          94% {isEs ? 'encaja' : 'fit'}
        </div>
        <div className="absolute bottom-2 right-2 flex gap-1">
          <span className="px-1.5 py-0.5 bg-white/90 backdrop-blur rounded text-[7px] text-stone-600 shadow-sm">
            <Sun className="w-2 h-2 inline mr-0.5" />{isEs ? 'Luminoso' : 'Bright'}
          </span>
        </div>
      </div>
      
      {/* Details */}
      <div className="p-2.5">
        <div className="flex justify-between items-start mb-1.5">
          <div>
            <div className="text-[11px] font-semibold text-stone-900">
              {isEs ? '2 hab. en Gràcia' : '2-bed in Gràcia'}
            </div>
            <div className="text-[9px] text-stone-500">€1.200/mes • 65m²</div>
          </div>
        </div>
        
        {/* Why it fits */}
        <div className="bg-emerald-50 rounded-lg p-2 border border-emerald-100">
          <div className="text-[8px] font-medium text-emerald-700 mb-1">
            {isEs ? 'Por qué encaja:' : 'Why it fits:'}
          </div>
          <div className="text-[8px] text-emerald-600 leading-relaxed">
            {isEs ? '12 min al trabajo, calle tranquila, techos altos' : '12 min to work, quiet street, high ceilings'}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 3: "View, react, refine"
 * Casual text-to-friend style - like what a 30yo would actually send
 */
export const VignetteFeedbackLoop = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[200px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* iMessage-style header */}
      <div className="bg-stone-100 px-3 py-1.5 flex items-center gap-2">
        <div className="w-5 h-5 rounded-full bg-stone-900 flex items-center justify-center">
          <span className="text-[8px] text-white font-bold">L</span>
        </div>
        <span className="text-[10px] font-medium text-stone-700">Leo</span>
        <span className="text-[8px] text-stone-400 ml-auto">{isEs ? 'ahora' : 'now'}</span>
      </div>
      
      {/* Casual message thread */}
      <div className="p-2.5 space-y-2 bg-stone-50">
        {/* Leo asks */}
        <div className="bg-white rounded-lg rounded-tl-none px-2.5 py-1.5 text-[10px] text-stone-700 shadow-sm border border-stone-100 max-w-[85%]">
          {isEs ? '¿Qué tal el de Gràcia?' : 'How was the Gràcia place?'}
        </div>
        
        {/* User's casual response - like texting a friend */}
        <div className="flex justify-end">
          <div className="bg-blue-500 text-white rounded-lg rounded-tr-none px-2.5 py-1.5 text-[10px] max-w-[85%]">
            {isEs ? 'la verdad bastante bien pero la calle era muy ruidosa 😩' : 'honestly pretty nice but the street was loud af 😩'}
          </div>
        </div>
        
        <div className="flex justify-end">
          <div className="bg-blue-500 text-white rounded-lg rounded-tr-none px-2.5 py-1.5 text-[10px] max-w-[85%]">
            {isEs ? 'pero la luz me encantó ✨' : 'loved the light tho ✨'}
          </div>
        </div>
        
        {/* Leo learns */}
        <div className="bg-white rounded-lg rounded-tl-none px-2.5 py-1.5 text-[10px] text-stone-700 shadow-sm border border-stone-100 max-w-[85%]">
          <span className="text-stone-400">{isEs ? 'Entendido—' : 'Got it—'}</span>
          {isEs ? 'priorizando calles más tranquilas 🤫' : 'prioritizing quieter streets 🤫'}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// LISTING VS REALITY - The "gotcha" mockup
// ============================================================================

/**
 * Beautiful listing vs reality photos contrast
 * Shows staged listing photo vs actual viewing photos - now with real generated images
 */
export const ListingVsRealityMockup = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("max-w-2xl mx-auto", className)}>
      <div className="grid md:grid-cols-2 gap-6">
        {/* Listing Photo - Beautiful staged photo */}
        <div className="relative">
          <div className="absolute -top-3 left-4 px-3 py-1 bg-stone-900 text-white text-xs font-medium rounded-full shadow-lg z-10">
            {isEs ? 'Foto del anuncio' : 'Listing photo'}
          </div>
          <div className="aspect-[4/3] rounded-2xl overflow-hidden border border-stone-200 shadow-lg relative">
            <Image
              src={LANDING_IMAGES.listingStagedBeautiful}
              alt={isEs ? "Foto del anuncio con home staging" : "Beautiful staged listing photo"}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 50vw"
            />
            {/* Overlay with listing info */}
            <div className="absolute bottom-4 left-4 right-4">
              <div className="bg-white/90 backdrop-blur rounded-xl p-3 shadow-lg">
                <div className="text-xs text-stone-500 mb-1">
                  {isEs ? 'Piso luminoso exterior' : 'Bright corner apartment'}
              </div>
                <div className="text-sm font-medium text-stone-900">
                  {isEs ? 'Luz natural todo el día ✨' : 'Natural light all day ✨'}
            </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Reality Photos - Your viewing */}
        <div className="relative">
          <div className="absolute -top-3 left-4 px-3 py-1 bg-amber-500 text-white text-xs font-medium rounded-full shadow-lg z-10">
            {isEs ? 'Tus fotos de la visita' : 'Your viewing photos'}
          </div>
          <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-stone-100 border border-stone-200 shadow-lg relative">
            {/* Grid of real reality photos */}
            <div className="grid grid-cols-2 gap-1 p-1 h-full">
              {/* Dark corner */}
              <div className="relative rounded-lg overflow-hidden">
                <Image
                  src={LANDING_IMAGES.realityDarkCorner}
                  alt={isEs ? "Esquina oscura" : "Dark corner reality"}
                  fill
                  className="object-cover"
                  sizes="25vw"
                />
                <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-red-500/90 text-white text-[8px] font-medium rounded">
                  {isEs ? 'Esquina oscura' : 'Dark corner'}
                </div>
              </div>
              
              {/* Water stain */}
              <div className="relative rounded-lg overflow-hidden">
                <Image
                  src={LANDING_IMAGES.realityWaterStain}
                  alt={isEs ? "Mancha de humedad" : "Water stain on ceiling"}
                  fill
                  className="object-cover"
                  sizes="25vw"
                />
                <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-amber-500/90 text-white text-[8px] font-medium rounded">
                  {isEs ? '¿Humedad?' : 'Water stain?'}
                </div>
              </div>
              
              {/* Street view */}
              <div className="relative rounded-lg overflow-hidden">
                <Image
                  src={LANDING_IMAGES.realityStreetView}
                  alt={isEs ? "Vista a la calle" : "View of busy street"}
                  fill
                  className="object-cover"
                  sizes="25vw"
                />
                <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-stone-700/90 text-white text-[8px] font-medium rounded">
                  {isEs ? 'Vista calle' : 'Street view'}
                </div>
              </div>
              
              {/* Nice light */}
              <div className="relative rounded-lg overflow-hidden">
                <Image
                  src={LANDING_IMAGES.realityNiceLight}
                  alt={isEs ? "Buena luz por la mañana" : "Nice morning light"}
                  fill
                  className="object-cover"
                  sizes="25vw"
                />
                <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-green-500/90 text-white text-[8px] font-medium rounded">
                  {isEs ? 'Buena luz AM' : 'Nice light AM'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Leo's insight */}
      <div className="mt-6 bg-stone-900 text-white rounded-2xl p-4 flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0">
          <Sparkles className="w-4 h-4" />
        </div>
        <div>
          <div className="text-sm font-medium mb-1">{isEs ? 'Leo notó:' : 'Leo noticed:'}</div>
          <p className="text-sm text-stone-300 leading-relaxed">
            {isEs 
              ? 'El anuncio usó gran angular y sacó las fotos por la mañana. Tus fotos captaron la esquina norte y un posible problema de humedad. La próxima vez, marcaré los edificios de esta calle.'
              : "The listing used a wide-angle lens and shot in morning light. Your photos caught the north-facing corner and a possible damp issue. Next time, I'll flag buildings on this street."}
          </p>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// SMALL REUSABLE ELEMENTS
// ============================================================================

/**
 * Tiny property card (~100px)
 */
export const TinyPropertyCard = ({ 
  title = "2 hab. Gràcia",
  price = "€1.200",
  match = 94,
  className
}: { 
  title?: string;
  price?: string;
  match?: number;
  className?: string;
}) => {
  return (
    <div className={cn("w-[100px] bg-white rounded-lg shadow-md border border-stone-200 overflow-hidden", className)}>
      <div className="h-12 bg-gradient-to-br from-stone-200 to-stone-300 relative">
        <div className="absolute top-1 left-1 px-1 py-0.5 bg-emerald-500 text-white text-[7px] font-bold rounded">
          {match}%
        </div>
      </div>
      <div className="p-1.5">
        <div className="text-[9px] font-semibold text-stone-900 truncate">{title}</div>
        <div className="text-[8px] text-stone-500">{price}</div>
      </div>
    </div>
  );
};

/**
 * Leo "checks" badge
 */
export const LeoChecksBadge = ({ 
  text = "ITE OK",
  type = "success"
}: { 
  text: string;
  type?: "success" | "warning" | "neutral";
}) => {
  const colors = {
    success: "bg-green-100 text-green-700 border-green-200",
    warning: "bg-amber-100 text-amber-700 border-amber-200",
    neutral: "bg-stone-100 text-stone-600 border-stone-200"
  };
  
  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-medium", colors[type])}>
      {type === "success" && <Check className="w-2.5 h-2.5" />}
      {type === "warning" && <AlertTriangle className="w-2.5 h-2.5" />}
      {text}
    </span>
  );
};

/**
 * Vignette showing what Leo checks
 */
export const VignetteLeoChecks = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[160px] bg-white rounded-xl shadow-lg border border-stone-200 p-3", className)}>
      <div className="text-[10px] font-medium text-stone-900 mb-2 flex items-center gap-1.5">
        <Sparkles className="w-3 h-3 text-amber-500" />
        {isEs ? 'Leo comprobó:' : 'Leo checked:'}
      </div>
      <div className="space-y-1.5">
        <LeoChecksBadge text={isEs ? "Edificio: 1985" : "Building: 1985"} type="success" />
        <LeoChecksBadge text={isEs ? "Sin aluminosis" : "No aluminosis"} type="success" />
        <LeoChecksBadge text={isEs ? "Zona con mucho Airbnb" : "High Airbnb area"} type="warning" />
      </div>
    </div>
  );
};

// All components are exported above with `export const`
