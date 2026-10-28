"use client";

import React from "react";
import Image from "next/image";
import { 
  Check, ChevronRight, MapPin, Clock, Sun, Volume2, Home, 
  Star, Heart, AlertTriangle, X, MessageCircle, Sparkles,
  Building, Users, Briefcase, School, Train, Globe
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { LANDING_IMAGES } from "./LandingImages";

// ============================================
// SHARED COMPONENTS
// ============================================

const PhoneFrameCompact = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn("relative mx-auto border-gray-800 bg-gray-800 border-[10px] rounded-[2rem] h-[520px] w-[260px] shadow-2xl", className)}>
    <div className="w-[100px] h-[14px] bg-gray-800 top-0 rounded-b-[0.8rem] left-1/2 -translate-x-1/2 absolute z-20"></div>
    <div className="h-[24px] w-[3px] bg-gray-800 absolute -right-[13px] top-[100px] rounded-r-lg"></div>
    <div className="rounded-[1.5rem] overflow-hidden w-full h-full bg-white relative z-10">
      {children}
    </div>
  </div>
);

const BrowserFrameCompact = ({ children, url, className }: { children: React.ReactNode; url: string; className?: string }) => (
  <div className={cn("relative bg-white rounded-xl shadow-[0_16px_40px_-8px_rgba(0,0,0,0.12)] border border-stone-200 overflow-hidden", className)}>
    <div className="bg-stone-100 border-b border-stone-200 h-9 flex items-center px-3 gap-2">
      <div className="flex gap-1.5">
        <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]"></div>
        <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]"></div>
        <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]"></div>
      </div>
      <div className="flex-1 ml-2">
        <div className="bg-white h-5 w-full max-w-xs rounded border border-stone-200 flex items-center justify-center text-[10px] text-stone-400">
          {url}
        </div>
      </div>
    </div>
    <div className="overflow-hidden bg-stone-50">
      {children}
    </div>
  </div>
);

// ============================================
// RENTERS MOCKUPS
// ============================================

// Phone mockup showing Leo chat + property cards
export const RentersPhoneMockup = () => {
  const properties = [
    { 
      title: "2-bed in Gràcia", 
      price: "€1,350/mo", 
      tags: ["Bright", "Quiet street", "10 min to work"],
      match: 94
    },
    { 
      title: "Sunny studio, Born", 
      price: "€1,100/mo", 
      tags: ["Natural light", "Near market"],
      match: 87
    },
  ];

  return (
    <PhoneFrameCompact>
      <div className="flex flex-col h-full bg-stone-50">
        {/* Chat Header */}
        <div className="bg-white border-b border-stone-100 px-4 pt-8 pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-stone-900 flex items-center justify-center">
              <span className="text-white text-sm font-bold">L</span>
            </div>
            <div>
              <div className="font-semibold text-stone-900 text-sm">Leo</div>
              <div className="text-xs text-green-600">Active now</div>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Leo's message */}
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-stone-900 flex items-center justify-center flex-shrink-0">
              <span className="text-white text-[10px] font-bold">L</span>
            </div>
            <div className="bg-white rounded-2xl rounded-tl-sm px-3 py-2 shadow-sm border border-stone-100 max-w-[85%]">
              <p className="text-sm text-stone-700">
                Good morning! I found 3 places that match your "quiet + bright" priority. Here are my top picks:
              </p>
            </div>
          </div>

          {/* Property Cards */}
          {properties.map((property, idx) => (
            <div key={idx} className="ml-8">
              <div className="bg-white rounded-xl border border-stone-200 overflow-hidden shadow-sm">
                {/* Property Image */}
                <div className="h-24 relative">
                  <Image
                    src={LANDING_IMAGES.propertyCardApartment}
                    alt={property.title}
                    fill
                    className="object-cover"
                    sizes="200px"
                  />
                  <div className="absolute top-2 right-2">
                    <Badge className="bg-green-500/90 text-white text-[10px] border-none">
                      {property.match}% match
                    </Badge>
                  </div>
                  {/* Mini Map */}
                  <div className="absolute bottom-2 left-2 w-12 h-12 bg-white/90 rounded-lg border border-stone-200 flex items-center justify-center">
                    <MapPin className="w-4 h-4 text-stone-500" />
                  </div>
                </div>
                
                {/* Property Info */}
                <div className="p-3">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-semibold text-stone-900 text-sm">{property.title}</div>
                    <div className="text-sm font-bold text-stone-900">{property.price}</div>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {property.tags.map((tag, tagIdx) => (
                      <span key={tagIdx} className="inline-flex items-center gap-1 px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full text-[10px]">
                        {tag === "Bright" && <Sun className="w-2.5 h-2.5" />}
                        {tag === "Quiet street" && <Volume2 className="w-2.5 h-2.5" />}
                        {tag === "Natural light" && <Sun className="w-2.5 h-2.5" />}
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </PhoneFrameCompact>
  );
};

// Viewing feedback mockup (before/after style)
export const RentersFeedbackMockup = () => {
  const feedbackTags = [
    { text: "Too dark", selected: true, negative: true },
    { text: "Loved the street", selected: true, negative: false },
    { text: "Living room too small", selected: true, negative: true },
    { text: "Nice neighbours", selected: false, negative: false },
  ];

  return (
    <div className="flex gap-4 items-start max-w-2xl mx-auto">
      {/* Left: Property Card */}
      <div className="flex-1 bg-white rounded-xl border border-stone-200 overflow-hidden shadow-sm">
        <div className="h-32 relative">
          <Image
            src={LANDING_IMAGES.propertyCardApartment}
            alt="Carrer de Verdi, 45"
            fill
            className="object-cover"
            sizes="300px"
          />
          <Badge className="absolute top-3 left-3 bg-blue-500/90 text-white border-none text-xs">
            View booked
          </Badge>
        </div>
        <div className="p-4">
          <div className="font-semibold text-stone-900 mb-1">Carrer de Verdi, 45</div>
          <div className="text-sm text-stone-500 flex items-center gap-1">
            <MapPin className="w-3 h-3" /> Gràcia • €1,400/mo
          </div>
        </div>
      </div>

      {/* Arrow */}
      <div className="flex items-center justify-center pt-16">
        <ChevronRight className="w-6 h-6 text-stone-400" />
      </div>

      {/* Right: Feedback Card */}
      <div className="flex-1 space-y-3">
        <div className="bg-white rounded-xl border border-stone-200 p-4 shadow-sm">
          <div className="text-sm font-semibold text-stone-900 mb-3 flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-stone-500" />
            Your notes from this visit
          </div>
          <div className="flex flex-wrap gap-2">
            {feedbackTags.map((tag, idx) => (
              <span 
                key={idx} 
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                  tag.selected 
                    ? tag.negative 
                      ? "bg-red-100 text-red-700 border border-red-200" 
                      : "bg-green-100 text-green-700 border border-green-200"
                    : "bg-stone-100 text-stone-500 border border-stone-200"
                )}
              >
                {tag.text}
              </span>
            ))}
          </div>
        </div>

        {/* Next Suggestions Strip */}
        <div className="bg-stone-900 rounded-xl p-3 text-white">
          <div className="text-xs text-stone-400 mb-2 flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> Leo adjusts...
          </div>
          <div className="text-sm">
            Next batch will prioritise <span className="font-semibold">south-facing</span> + <span className="font-semibold">larger living spaces</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// BUYERS MOCKUPS
// ============================================

// Enhanced checklist mockup with note-taking capabilities
export const BuyersChecklistMockup = () => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const checklistItems = isEs ? [
    { text: "Comprobar ruido en dormitorio", checked: true, note: "Todo tranquilo, calle interior" },
    { text: "Preguntar por gastos de comunidad", checked: true, note: "€280/mes — más de lo esperado", hasPhoto: true },
    { text: "Buscar humedad en las esquinas", checked: false },
    { text: "Probar presión del agua", checked: false },
  ] : [
    { text: "Check noise in bedroom", checked: true, note: "All quiet, interior street" },
    { text: "Ask about community fees", checked: true, note: "€280/mo — higher than expected", hasPhoto: true },
    { text: "Look for humidity in corners", checked: false },
    { text: "Test water pressure", checked: false },
  ];

  return (
    <div className="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-lg max-w-md mx-auto">
      {/* Phone-style header */}
      <div className="bg-stone-900 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center">
            <span className="text-white text-xs font-bold">L</span>
          </div>
          <div>
            <div className="text-white text-sm font-medium">{isEs ? 'Checklist de visita' : 'Viewing Checklist'}</div>
            <div className="text-stone-400 text-[10px]">Carrer de Bailèn, 124</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-emerald-400 font-medium">2/4</span>
          <div className="w-12 h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div className="w-1/2 h-full bg-emerald-400 rounded-full" />
          </div>
        </div>
      </div>

      {/* Checklist items with notes */}
      <div className="p-4 space-y-3">
          {checklistItems.map((item, idx) => (
          <div key={idx} className="space-y-2">
            <div 
              className={cn(
                "flex items-center gap-3 p-3 rounded-xl border transition-all",
                item.checked 
                  ? "bg-emerald-50 border-emerald-200" 
                  : "bg-white border-stone-200"
              )}
            >
              <div className={cn(
                "w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0",
                item.checked ? "bg-emerald-500 border-emerald-500" : "border-stone-300"
              )}>
                {item.checked && <Check className="w-3 h-3 text-white" />}
              </div>
              <span className={cn(
                "text-sm flex-1",
                item.checked ? "text-emerald-800" : "text-stone-700"
              )}>
                {item.text}
              </span>
            </div>
            
            {/* Note attached to checked item */}
            {item.checked && item.note && (
              <div className="ml-8 flex gap-2">
                <div className="flex-1 bg-stone-50 rounded-lg p-2.5 border border-stone-100">
                  <div className="flex items-start gap-2">
                    <MessageCircle className="w-3.5 h-3.5 text-stone-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-stone-600">{item.note}</p>
                  </div>
                </div>
                {item.hasPhoto && (
                  <div className="w-10 h-10 rounded-lg bg-stone-200 relative overflow-hidden shrink-0">
                    <Image
                      src={LANDING_IMAGES.realityWaterStain}
                      alt={isEs ? "Foto de la visita" : "Viewing photo"}
                      fill
                      className="object-cover"
                      sizes="40px"
                    />
                  </div>
                )}
              </div>
            )}
            </div>
          ))}
      </div>

      {/* Note-taking bar at bottom */}
      <div className="border-t border-stone-200 p-3 bg-stone-50">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-white rounded-full px-4 py-2 border border-stone-200 flex items-center gap-2">
            <input
              type="text"
              placeholder={isEs ? "Añadir nota..." : "Add a note..."}
              className="flex-1 text-sm text-stone-700 placeholder:text-stone-400 outline-none bg-transparent"
              readOnly
            />
          </div>
          {/* Action buttons */}
          <button className="w-9 h-9 rounded-full bg-white border border-stone-200 flex items-center justify-center hover:bg-stone-50 transition-colors">
            <svg className="w-4 h-4 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button className="w-9 h-9 rounded-full bg-emerald-500 flex items-center justify-center hover:bg-emerald-600 transition-colors">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/>
            </svg>
          </button>
        </div>
        <div className="flex justify-center gap-4 mt-2 text-[10px] text-stone-400">
          <span>📝 {isEs ? 'Texto' : 'Text'}</span>
          <span>📷 {isEs ? 'Foto' : 'Photo'}</span>
          <span>🎤 {isEs ? 'Voz' : 'Voice'}</span>
        </div>
      </div>
    </div>
  );
};

// Enhanced comparison mockup with notes and photos - improved design
export const BuyersComparisonMockup = () => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const contenders = [
    { 
      address: "Bailèn 124", 
      area: "Eixample",
      price: "€485k",
      verdict: isEs ? "Favorito" : "Favorite", 
      status: "green",
      note: isEs ? "Mucha luz, calle tranquila" : "Great light, quiet street",
      image: LANDING_IMAGES.realityNiceLight
    },
    { 
      address: "Aragó 89", 
      area: "Gràcia",
      price: "€520k",
      verdict: isEs ? "Quizás" : "Maybe", 
      status: "amber",
      note: isEs ? "Buen tamaño pero ruidoso" : "Good size but noisy",
      image: LANDING_IMAGES.interiorApartment
    },
    { 
      address: "València 201", 
      area: "Sant Antoni",
      price: "€495k",
      verdict: isEs ? "Descartado" : "Rejected", 
      status: "stone",
      note: isEs ? "Humedad en el baño" : "Humidity in bathroom",
      image: LANDING_IMAGES.propertyCardApartment
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-stone-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-stone-900 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span className="text-white text-sm font-medium">
            {isEs ? 'Comparar visitas' : 'Compare viewings'}
          </span>
        </div>
        <span className="text-[10px] text-stone-400">
          {isEs ? '3 propiedades vistas' : '3 properties viewed'}
        </span>
      </div>
      
      {/* Comparison cards - horizontal layout with images */}
      <div className="p-4 space-y-3">
        {contenders.map((property, idx) => (
          <div 
            key={idx}
            className={cn(
              "rounded-xl border overflow-hidden transition-all",
              property.status === "green" && "bg-emerald-50/50 border-emerald-200",
              property.status === "amber" && "bg-amber-50/50 border-amber-200",
              property.status === "stone" && "bg-stone-50 border-stone-200"
            )}
          >
            <div className="flex">
              {/* Property image */}
              <div className="w-20 h-20 relative shrink-0">
                <Image
                  src={property.image}
                  alt={property.address}
                  fill
                  className="object-cover"
                  sizes="80px"
                />
                {/* Status badge overlay */}
                <div className={cn(
                  "absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[9px] font-bold",
                  property.status === "green" && "bg-emerald-500 text-white",
                  property.status === "amber" && "bg-amber-500 text-white",
                  property.status === "stone" && "bg-stone-400 text-white"
                )}>
                  {property.verdict}
                </div>
              </div>
              
              {/* Property info */}
              <div className="flex-1 p-3 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div>
                    <div className="text-sm font-semibold text-stone-900 truncate">{property.address}</div>
                    <div className="text-[10px] text-stone-400">{property.area}</div>
                  </div>
                  <span className="text-xs font-medium text-stone-700 whitespace-nowrap">{property.price}</span>
                </div>
                
                {/* Note */}
                <div className="flex items-start gap-1.5 text-[11px] text-stone-600 mt-2">
                  <MessageCircle className="w-3 h-3 text-stone-400 mt-0.5 shrink-0" />
                  <span className="line-clamp-2">{property.note}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Leo's insight */}
      <div className="border-t border-stone-200 px-4 py-3 bg-gradient-to-r from-stone-50 to-stone-100">
        <div className="flex items-start gap-2">
          <div className="w-6 h-6 rounded-full bg-stone-900 flex items-center justify-center shrink-0">
            <span className="text-[9px] text-white font-bold">L</span>
          </div>
          <div className="text-xs text-stone-600">
            <span className="font-medium text-stone-800">{isEs ? 'Leo aprende:' : 'Leo learns:'}</span>{' '}
            {isEs 
              ? 'Sigues rechazando pisos ruidosos. Próximos filtros: solo calles interiores.'
              : 'You keep rejecting noisy places. Next filters: interior streets only.'}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// BUYER AGENTS MOCKUPS
// ============================================

// Browser with extension overlay
export const BuyerAgentsExtensionMockup = () => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const listings = [
    { title: isEs ? "3 hab. Eixample" : "3-bed Eixample", price: "€520k", fit: 92, fitLabel: isEs ? "Encaja bien" : "Strong match" },
    { title: isEs ? "2 hab. Gràcia" : "2-bed Gràcia", price: "€385k", fit: 82, fitLabel: "82% fit" },
    { title: "Ático Born", price: "€780k", fit: 65, fitLabel: "65% fit" },
    { title: isEs ? "4 hab. Sant Gervasi" : "4-bed Sant Gervasi", price: "€890k", fit: 78, fitLabel: "78% fit" },
  ];

  return (
    <BrowserFrameCompact url="viviendas.ejemplo.com/barcelona" className="max-w-4xl mx-auto">
      <div className="flex">
        {/* Main listing grid */}
        <div className="flex-1 p-4">
          <div className="grid grid-cols-2 gap-3">
            {listings.map((listing, idx) => (
              <div key={idx} className="bg-white rounded-lg border border-stone-200 overflow-hidden shadow-sm">
                <div className="h-20 relative">
                  <Image
                    src={idx % 2 === 0 ? LANDING_IMAGES.interiorApartment : LANDING_IMAGES.propertyCardApartment}
                    alt={listing.title}
                    fill
                    className="object-cover"
                    sizes="150px"
                  />
                  <Badge 
                    className={cn(
                      "absolute top-2 right-2 text-[10px] border-none",
                      listing.fit >= 90 ? "bg-green-500 text-white" :
                      listing.fit >= 80 ? "bg-blue-500 text-white" :
                      "bg-stone-500 text-white"
                    )}
                  >
                    {listing.fitLabel}
                  </Badge>
                </div>
                <div className="p-2">
                  <div className="text-xs font-medium text-stone-900">{listing.title}</div>
                  <div className="text-xs text-stone-500">{listing.price}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Leo Extension Panel */}
        <div className="w-48 bg-white border-l border-stone-200 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-6 h-6 rounded bg-stone-900 flex items-center justify-center">
              <span className="text-white text-xs font-bold">L</span>
            </div>
            <span className="text-xs font-semibold text-stone-900">
              {isEs ? 'Enviar a Leo' : 'Send to Leo'}
            </span>
          </div>

          {/* Client Dropdown */}
          <div className="mb-4">
            <label className="text-[10px] text-stone-500 mb-1 block">
              {isEs ? 'Cliente' : 'Client'}
            </label>
            <div className="flex items-center justify-between bg-stone-100 rounded-lg px-3 py-2 text-sm">
              <span className="text-stone-900 font-medium">Marta P.</span>
              <ChevronRight className="w-4 h-4 text-stone-400 rotate-90" />
            </div>
          </div>

          {/* Selected count */}
          <div className="text-xs text-stone-500 mb-3">
            {isEs ? '2 propiedades seleccionadas' : '2 properties selected'}
          </div>

          {/* Send Button */}
          <Button className="w-full bg-stone-900 text-white text-xs h-9">
            {isEs ? 'Enviar a Leo' : 'Send to Leo'}
          </Button>
        </div>
      </div>
    </BrowserFrameCompact>
  );
};

// Client vs Agent view comparison
export const BuyerAgentsViewsMockup = () => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const clientItems = isEs ? [
    "Comprobar ruido",
    "Preguntar por gastos",
    "Revisar almacenaje",
  ] : [
    "Check noise levels",
    "Ask about fees",
    "Look at storage",
  ];

  const agentItems = isEs ? [
    "Comprobar ruido en dormitorio",
    "Preguntar por comunidad (€150/mes indicado)",
    "Revisar almacenaje + medir armarios",
    "Verificar ITE (edificio 1975)",
    "Nota: Marta mencionó sensibilidad a la luz",
  ] : [
    "Check noise levels in bedroom",
    "Ask about community fees (€150/mo claimed)",
    "Look at storage + measure closets",
    "Verify ITE certificate (1975 build)",
    "Note: Marta mentioned light sensitivity",
  ];

  return (
    <div className="flex gap-4 max-w-3xl mx-auto">
      {/* Client View */}
      <div className="flex-1 bg-white rounded-xl border border-stone-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
            <span className="text-amber-700 text-sm font-bold">M</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-stone-900">
              {isEs ? 'Checklist para Marta' : 'Checklist for Marta'}
            </div>
            <div className="text-xs text-stone-500">
              {isEs ? 'Vista simple' : 'Simple view'}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          {clientItems.map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 p-2 bg-stone-50 rounded-lg">
              <div className="w-4 h-4 rounded border-2 border-stone-300" />
              <span className="text-sm text-stone-700">{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Agent View */}
      <div className="flex-1 bg-white rounded-xl border border-stone-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <Briefcase className="w-4 h-4 text-blue-700" />
          </div>
          <div>
            <div className="text-sm font-semibold text-stone-900">
              {isEs ? 'Vista agente' : 'Agent view'}
            </div>
            <div className="text-xs text-stone-500">
              {isEs ? 'Contexto completo' : 'Full context'}
            </div>
          </div>
        </div>

        <div className="space-y-2 mb-4">
          {agentItems.slice(0, 3).map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 p-2 bg-stone-50 rounded-lg">
              <div className="w-4 h-4 rounded border-2 border-stone-300" />
              <span className="text-xs text-stone-700">{item}</span>
            </div>
          ))}
        </div>

        {/* Analysis Notes */}
        <div className="bg-amber-50 border border-amber-100 rounded-lg p-3">
          <div className="text-[10px] font-bold text-amber-800 uppercase tracking-wider mb-1">
            {isEs ? 'Notas de análisis' : 'Analysis notes'}
          </div>
          <div className="text-xs text-amber-700 space-y-1">
            <p>• {agentItems[3]}</p>
            <p>• {agentItems[4]}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// RELOCATION MOCKUPS
// ============================================

// Housing brief document
export const RelocationBriefMockup = () => {
  const sections = [
    { icon: Building, title: "Work & School", value: "Tech hub, International school" },
    { icon: Train, title: "Commute", value: "Max 30 min, prefer metro" },
    { icon: Home, title: "Budget", value: "€2,000-2,500/mo" },
    { icon: MapPin, title: "Preferred areas", value: "Sarriá, Pedralbes, Les Corts" },
    { icon: AlertTriangle, title: "Sensitivities", value: "No stairs (elderly parent)" },
  ];

  const assignees = [
    { name: "Ana", city: "Madrid", status: "Searching", color: "bg-blue-100 text-blue-700" },
    { name: "Lucas", city: "Barcelona", status: "Shortlist", color: "bg-amber-100 text-amber-700" },
    { name: "Priya", city: "Lisbon", status: "Settled", color: "bg-green-100 text-green-700" },
  ];

  return (
    <div className="flex gap-6 max-w-4xl mx-auto">
      {/* Housing Brief Card */}
      <div className="flex-1 bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
        <div className="bg-stone-900 text-white px-5 py-4">
          <div className="flex items-center gap-3 mb-2">
            <Globe className="w-5 h-5" />
            <span className="text-sm font-semibold">Housing Brief</span>
          </div>
          <div className="text-lg font-bold">Berlin → Family of 3</div>
        </div>

        <div className="p-4 space-y-3">
          {sections.map((section, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-stone-50 rounded-lg">
              <div className="w-8 h-8 rounded-lg bg-white border border-stone-200 flex items-center justify-center flex-shrink-0">
                <section.icon className="w-4 h-4 text-stone-600" />
              </div>
              <div>
                <div className="text-xs font-semibold text-stone-900">{section.title}</div>
                <div className="text-xs text-stone-600">{section.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Assignee List */}
      <div className="w-56 bg-white rounded-xl border border-stone-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-4 h-4 text-stone-500" />
          <span className="text-sm font-semibold text-stone-900">Active assignees</span>
        </div>

        <div className="space-y-3">
          {assignees.map((assignee, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-stone-50 rounded-lg">
              <div>
                <div className="text-sm font-medium text-stone-900">{assignee.name}</div>
                <div className="text-xs text-stone-500">{assignee.city}</div>
              </div>
              <Badge className={cn("text-[10px] border-none", assignee.color)}>
                {assignee.status}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Map with recommended areas - using real image
export const RelocationMapMockup = () => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4 shadow-sm max-w-md mx-auto">
      <div className="text-sm font-semibold text-stone-900 mb-3 flex items-center gap-2">
        <MapPin className="w-4 h-4 text-stone-500" />
        {isEs ? 'Zonas que Leo recomienda' : 'Areas Leo recommends'}
      </div>
      
      {/* Map with real city image */}
      <div className="relative h-48 rounded-lg overflow-hidden">
        <Image
          src={LANDING_IMAGES.citySkyline}
          alt={isEs ? "Zonas recomendadas en Barcelona" : "Recommended areas in Barcelona"}
          fill
          className="object-cover"
          sizes="400px"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />

        {/* Area highlights overlaid on image */}
        <div className="absolute top-8 left-8 w-16 h-16 rounded-full bg-emerald-500/30 border-2 border-emerald-400 flex items-center justify-center backdrop-blur-sm">
          <MapPin className="w-4 h-4 text-white" />
        </div>
        <div className="absolute top-16 right-12 w-14 h-14 rounded-full bg-emerald-500/30 border-2 border-emerald-400 flex items-center justify-center backdrop-blur-sm">
          <MapPin className="w-4 h-4 text-white" />
        </div>
        <div className="absolute bottom-12 left-1/3 w-12 h-12 rounded-full bg-amber-500/30 border-2 border-amber-400 flex items-center justify-center backdrop-blur-sm">
          <MapPin className="w-3 h-3 text-white" />
        </div>

        {/* Legend */}
        <div className="absolute bottom-3 right-3 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 text-[10px] space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500/30 border border-emerald-500"></div>
            <span className="text-stone-700">{isEs ? 'Mejor opción' : 'Best match'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500/30 border border-amber-500"></div>
            <span className="text-stone-700">{isEs ? 'A considerar' : 'Consider'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};


















