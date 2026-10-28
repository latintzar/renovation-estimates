"use client";

import React from "react";
import Image from "next/image";
import { 
  Users,
  Search,
  Check,
  X,
  Eye,
  EyeOff,
  Send,
  Star,
  AlertTriangle,
  FileText,
  Building,
  Clock,
  Camera,
  Mic,
  MessageCircle,
  Briefcase,
  MapPin
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { LANDING_IMAGES } from "./LandingImages";

// ============================================================================
// BUYER AGENT VIGNETTES - For personal shoppers / buyer agents
// ============================================================================

/**
 * Step 1: "Create client profiles"
 * Client profile card with preference sliders
 */
export const VignetteClientProfile = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[200px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Client header */}
      <div className="p-3 border-b border-stone-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 font-bold text-sm">SP</div>
          <div>
            <h3 className="font-semibold text-sm text-stone-900">Sarah Parker</h3>
            <p className="text-[10px] text-stone-500">Gràcia • €450-500k</p>
          </div>
        </div>
      </div>
      
      {/* Preference sliders */}
      <div className="p-3 space-y-3">
        <div>
          <div className="flex justify-between text-[9px] mb-1">
            <span className="text-stone-500">{isEs ? 'Ubicación vs Espacio' : 'Location vs Space'}</span>
            <span className="text-stone-700 font-medium">{isEs ? 'Ubicación' : 'Location'}</span>
          </div>
          <div className="h-1.5 bg-stone-100 rounded-full">
            <div className="h-full w-[80%] bg-stone-800 rounded-full" />
          </div>
        </div>
        
        <div>
          <div className="flex justify-between text-[9px] mb-1">
            <span className="text-stone-500">{isEs ? 'Tolerancia al ruido' : 'Noise tolerance'}</span>
            <span className="text-amber-600 font-medium">{isEs ? 'Baja' : 'Low'}</span>
          </div>
          <div className="h-1.5 bg-stone-100 rounded-full">
            <div className="h-full w-[20%] bg-amber-500 rounded-full" />
          </div>
        </div>
        
        <div>
          <div className="flex justify-between text-[9px] mb-1">
            <span className="text-stone-500">{isEs ? 'Ganas de reformar' : 'Renovation appetite'}</span>
            <span className="text-stone-700 font-medium">{isEs ? 'Media' : 'Medium'}</span>
          </div>
          <div className="h-1.5 bg-stone-100 rounded-full">
            <div className="h-full w-[50%] bg-stone-600 rounded-full" />
          </div>
        </div>
        
        {/* Tags */}
        <div className="pt-2 border-t border-stone-100">
          <div className="flex flex-wrap gap-1">
            <span className="px-1.5 py-0.5 bg-stone-100 rounded text-[8px] text-stone-600">
              {isEs ? 'Necesita terraza' : 'Needs terrace'}
            </span>
            <span className="px-1.5 py-0.5 bg-stone-100 rounded text-[8px] text-stone-600">
              {isEs ? 'No planta baja' : 'No ground floor'}
            </span>
            <span className="px-1.5 py-0.5 bg-stone-100 rounded text-[8px] text-stone-600">
              {isEs ? 'Calle tranquila' : 'Quiet street'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 2: "Leo analyzes listings"
 * Property analysis with match breakdown
 */
export const VignetteListingAnalysis = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[220px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Property header */}
      <div className="h-20 relative">
        <Image
          src={LANDING_IMAGES.propertyCardApartment}
          alt="Carrer de Verdi, 45"
          fill
          className="object-cover"
          sizes="220px"
        />
        <div className="absolute top-2 left-2 bg-emerald-500 text-white px-2 py-0.5 rounded text-[10px] font-bold">
          94% {isEs ? 'Encaja' : 'Match'}
        </div>
        <div className="absolute bottom-2 left-2 right-2">
          <div className="text-[10px] text-stone-700 font-medium bg-white/80 backdrop-blur px-2 py-1 rounded">
            Carrer de Verdi, 45
          </div>
        </div>
      </div>
      
      {/* Match breakdown */}
      <div className="p-3 space-y-2">
        <div className="text-[10px] font-medium text-stone-700">
          {isEs ? 'Desglose para Sarah:' : 'Match breakdown for Sarah:'}
        </div>
        
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-stone-500">{isEs ? 'Ubicación' : 'Location'}</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-stone-100 rounded-full">
                <div className="h-full w-[95%] bg-emerald-500 rounded-full" />
              </div>
              <span className="text-[9px] font-medium text-emerald-600">95%</span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-stone-500">{isEs ? 'Nivel ruido' : 'Noise level'}</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-stone-100 rounded-full">
                <div className="h-full w-[85%] bg-emerald-500 rounded-full" />
              </div>
              <span className="text-[9px] font-medium text-emerald-600">85%</span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-stone-500">{isEs ? 'Distribución' : 'Layout'}</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-stone-100 rounded-full">
                <div className="h-full w-[70%] bg-amber-500 rounded-full" />
              </div>
              <span className="text-[9px] font-medium text-amber-600">70%</span>
            </div>
          </div>
        </div>
        
        {/* Red flags */}
        <div className="bg-amber-50 rounded-lg p-2 mt-2">
          <div className="flex items-start gap-1.5">
            <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
            <span className="text-[9px] text-amber-700">
              {isEs 
                ? 'Revisar gastos comunidad — edificio parece caro de mantener'
                : 'Check community fees — building looks expensive to maintain'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 3: "Send with personalized viewing checklist"
 * Now MUCH more visual - shows actual checklist items prominently
 */
export const VignetteShortlist = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const checklistItems = isEs ? [
    { text: "Comprobar ruido del dormitorio", icon: "🔇", done: false },
    { text: "Medir armarios (Sarah necesita mín 2m)", icon: "📏", done: false },
    { text: "Preguntar gastos comunidad reales", icon: "💰", done: false },
    { text: "Revisar orientación luz (sensible)", icon: "☀️", done: false },
    { text: "Fotografiar cocina para referencia", icon: "📸", done: false },
  ] : [
    { text: "Check bedroom noise level", icon: "🔇", done: false },
    { text: "Measure closets (Sarah needs min 2m)", icon: "📏", done: false },
    { text: "Ask real community fees", icon: "💰", done: false },
    { text: "Check light direction (sensitive)", icon: "☀️", done: false },
    { text: "Photo kitchen for reference", icon: "📸", done: false },
  ];
  
  return (
    <div className={cn("w-[220px] bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Header with client */}
      <div className="bg-emerald-600 px-3 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-[10px] font-bold">SP</div>
            <div>
              <div className="text-white text-[11px] font-medium">
                {isEs ? 'Checklist para Sarah' : "Sarah's Checklist"}
              </div>
              <div className="text-emerald-100 text-[9px]">Carrer de Verdi, 45</div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Big visual checklist */}
      <div className="p-3 space-y-2">
        {checklistItems.slice(0, 4).map((item, idx) => (
          <div 
            key={idx}
            className="flex items-center gap-2 bg-stone-50 rounded-lg px-2.5 py-2 border border-stone-100"
          >
            <span className="text-base">{item.icon}</span>
            <span className="text-[10px] text-stone-700 flex-1 leading-tight">{item.text}</span>
            <div className="w-4 h-4 rounded border-2 border-stone-300 shrink-0" />
          </div>
        ))}
        <div className="text-center text-[9px] text-stone-400">
          +1 {isEs ? 'más...' : 'more...'}
        </div>
      </div>
      
      {/* Note input bar */}
      <div className="border-t border-stone-200 px-3 py-2 bg-stone-50">
        <div className="flex items-center gap-1.5">
          <div className="flex-1 bg-white rounded-full px-3 py-1.5 border border-stone-200 text-[9px] text-stone-400">
            {isEs ? 'Añadir nota durante visita...' : 'Add note during viewing...'}
          </div>
          <button className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
            <Send className="w-3.5 h-3.5 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// AGENT-SPECIFIC MOCKUPS
// ============================================================================

/**
 * Browser Extension Mockup
 * Shows Leo overlay on Idealista-style listing - uses street view image
 */
export const BrowserExtensionMockup = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-white rounded-2xl shadow-xl border border-stone-200 overflow-hidden max-w-md", className)}>
      {/* Browser chrome */}
      <div className="bg-stone-100 px-3 py-2 flex items-center gap-2 border-b border-stone-200">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-400" />
          <div className="w-3 h-3 rounded-full bg-amber-400" />
          <div className="w-3 h-3 rounded-full bg-emerald-400" />
        </div>
        <div className="flex-1 bg-white rounded-lg px-3 py-1 text-[10px] text-stone-500 mx-2">
          idealista.com/inmueble/12345678/
        </div>
      </div>
      
      {/* Page content with Leo overlay */}
      <div className="relative">
        {/* Fake listing content */}
        <div className="p-4 bg-stone-50">
          <div className="h-32 relative rounded-lg mb-3 overflow-hidden">
            <Image
              src={LANDING_IMAGES.streetNeighborhood}
              alt={isEs ? "Piso en venta en Gràcia" : "Flat for sale in Gràcia"}
              fill
              className="object-cover"
              sizes="400px"
            />
          </div>
          <h3 className="font-semibold text-stone-800 mb-1">
            {isEs ? 'Piso en venta en Gràcia' : 'Flat for sale in Gràcia'}
          </h3>
          <p className="text-sm text-stone-600">€485.000 • 95 m² • 3 hab.</p>
        </div>
        
        {/* Leo overlay - Client fit scores */}
        <div className="absolute top-2 right-2 bg-white rounded-xl shadow-lg border border-stone-200 p-3 w-48">
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-stone-100">
            <div className="w-6 h-6 rounded-full bg-stone-900 flex items-center justify-center">
              <span className="text-[8px] text-white font-bold">L</span>
            </div>
            <span className="text-[10px] font-semibold text-stone-700">
              {isEs ? '¿Para quién encaja?' : 'Who does it fit?'}
            </span>
          </div>
          
          {/* Client fit scores with colored indicators */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 text-[8px] font-bold">SP</div>
                <span className="text-[9px] text-stone-600">Sarah P.</span>
              </div>
              <span className="text-[10px] font-bold text-emerald-600">94%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 text-[8px] font-bold">MT</div>
                <span className="text-[9px] text-stone-600">Marc T.</span>
              </div>
              <span className="text-[10px] font-bold text-amber-600">67%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-full bg-stone-100 flex items-center justify-center text-stone-500 text-[8px] font-bold">LR</div>
                <span className="text-[9px] text-stone-600">Lisa R.</span>
              </div>
              <span className="text-[10px] font-bold text-stone-400">42%</span>
            </div>
          </div>
          
          <button className="w-full mt-3 bg-stone-900 text-white text-[9px] font-medium py-1.5 rounded-lg">
            {isEs ? 'Añadir a shortlist →' : 'Add to shortlist →'}
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * Multi-Client Isochrone Map - Shows multiple clients' sweet spots
 * Key hero visual for Agents page
 */
export const MultiClientIsochroneMap = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';

  const clients = [
    { initials: "SP", name: "Sarah P.", color: "#10b981", zone: "Gràcia" },
    { initials: "MT", name: "Marc T.", color: "#f59e0b", zone: "Eixample" },
    { initials: "LR", name: "Lisa R.", color: "#8b5cf6", zone: "Sant Gervasi" },
  ];

  return (
    <div className={cn("relative w-full max-w-md mx-auto", className)}>
      {/* Map container */}
      <div className="relative aspect-[4/3] bg-stone-100 rounded-2xl overflow-hidden shadow-xl border border-stone-200">
        {/* Simplified Barcelona map background */}
        <svg viewBox="0 0 400 300" className="absolute inset-0 w-full h-full">
          {/* Background */}
          <rect width="400" height="300" fill="#f5f5f4" />
          
          {/* Street grid hint */}
          <g stroke="#e5e5e4" strokeWidth="0.5" opacity="0.6">
            <line x1="50" y1="0" x2="50" y2="300" />
            <line x1="150" y1="0" x2="150" y2="300" />
            <line x1="250" y1="0" x2="250" y2="300" />
            <line x1="350" y1="0" x2="350" y2="300" />
            <line x1="0" y1="75" x2="400" y2="75" />
            <line x1="0" y1="150" x2="400" y2="150" />
            <line x1="0" y1="225" x2="400" y2="225" />
          </g>
          
          {/* Sarah's zone (green) - Gràcia */}
          <ellipse cx="180" cy="120" rx="80" ry="60" fill="#10b981" fillOpacity="0.25" stroke="#10b981" strokeWidth="2" />
          
          {/* Marc's zone (amber) - Eixample */}
          <ellipse cx="220" cy="180" rx="90" ry="55" fill="#f59e0b" fillOpacity="0.2" stroke="#f59e0b" strokeWidth="2" />
          
          {/* Lisa's zone (purple) - Sant Gervasi */}
          <ellipse cx="130" cy="100" rx="60" ry="50" fill="#8b5cf6" fillOpacity="0.2" stroke="#8b5cf6" strokeWidth="2" />
          
          {/* Sweet spot overlap */}
          <ellipse cx="170" cy="130" rx="30" ry="25" fill="#059669" fillOpacity="0.4" stroke="#059669" strokeWidth="2" />
        </svg>
        
        {/* Client markers */}
        <div className="absolute top-[35%] left-[42%] flex items-center gap-1 bg-emerald-500 text-white px-2 py-1 rounded-full text-[10px] font-bold shadow-lg">
          SP
        </div>
        <div className="absolute top-[55%] left-[52%] flex items-center gap-1 bg-amber-500 text-white px-2 py-1 rounded-full text-[10px] font-bold shadow-lg">
          MT
        </div>
        <div className="absolute top-[28%] left-[28%] flex items-center gap-1 bg-purple-500 text-white px-2 py-1 rounded-full text-[10px] font-bold shadow-lg">
          LR
        </div>
        
        {/* Property pin in overlap */}
        <div className="absolute top-[40%] left-[40%]">
          <div className="w-6 h-6 bg-stone-900 rounded-full flex items-center justify-center shadow-lg animate-pulse">
            <MapPin className="w-4 h-4 text-white" />
          </div>
        </div>
        
        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur rounded-lg px-3 py-2 shadow-lg">
          <div className="text-[9px] font-medium text-stone-700 mb-1.5">
            {isEs ? 'Zonas de clientes' : 'Client zones'}
          </div>
          <div className="space-y-1">
            {clients.map((client, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: client.color }} />
                <span className="text-[9px] text-stone-600">{client.name}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Property match badge */}
        <div className="absolute top-3 right-3 bg-stone-900 text-white px-3 py-1.5 rounded-lg shadow-lg">
          <div className="text-[9px] text-stone-400">{isEs ? 'Este piso encaja con' : 'This listing fits'}</div>
          <div className="text-sm font-bold">2 {isEs ? 'clientes' : 'clients'}</div>
        </div>
      </div>
    </div>
  );
};

/**
 * Shared Notes Visual - Shows agent-client note collaboration
 * This is the core value prop for agents
 */
export const SharedNotesVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';

  return (
    <div className={cn("relative w-full max-w-sm mx-auto", className)}>
      <div className="bg-white rounded-2xl shadow-xl border border-stone-200 overflow-hidden">
        {/* Header */}
        <div className="bg-stone-900 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 text-xs font-bold">SP</div>
            <div>
              <div className="text-white text-sm font-medium">Sarah Parker</div>
              <div className="text-stone-400 text-[10px]">Carrer de Verdi, 45</div>
            </div>
          </div>
          <div className="bg-emerald-500 text-white text-xs font-bold px-2 py-1 rounded-full">
            94% {isEs ? 'fit' : 'fit'}
          </div>
        </div>
        
        {/* Shared notes thread */}
        <div className="p-4 space-y-3 bg-stone-50">
          {/* Agent note */}
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-stone-800 flex items-center justify-center shrink-0">
              <Briefcase className="w-3 h-3 text-white" />
            </div>
            <div className="bg-white rounded-xl rounded-tl-none px-3 py-2 shadow-sm border border-stone-100 flex-1">
              <div className="text-[10px] text-stone-400 mb-0.5">{isEs ? 'Tú' : 'You'}</div>
              <p className="text-xs text-stone-700">
                {isEs 
                  ? 'Comunidad más alta de lo esperado (€280/mes). Revisar actas.'
                  : 'Community fees higher than expected (€280/mo). Check meeting notes.'}
              </p>
            </div>
          </div>
          
          {/* Client note with photo */}
          <div className="flex gap-2 justify-end">
            <div className="bg-emerald-50 rounded-xl rounded-tr-none px-3 py-2 shadow-sm border border-emerald-100 max-w-[80%]">
              <div className="text-[10px] text-emerald-600 mb-0.5">Sarah</div>
              <p className="text-xs text-stone-700 mb-2">
                {isEs ? 'Me encantó la luz! Pero esta grieta...' : 'Loved the light! But this crack...'}
              </p>
              <div className="w-full h-16 relative rounded-lg overflow-hidden">
                <Image
                  src={LANDING_IMAGES.realityWaterStain}
                  alt={isEs ? "Foto de Sarah" : "Sarah's photo"}
                  fill
                  className="object-cover"
                  sizes="200px"
                />
              </div>
            </div>
            <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 text-[10px] font-bold shrink-0">
              SP
            </div>
          </div>
          
          {/* Agent voice note */}
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-stone-800 flex items-center justify-center shrink-0">
              <Briefcase className="w-3 h-3 text-white" />
            </div>
            <div className="bg-white rounded-xl rounded-tl-none px-3 py-2 shadow-sm border border-stone-100">
              <div className="text-[10px] text-stone-400 mb-1">{isEs ? 'Tú' : 'You'}</div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center">
                  <Mic className="w-4 h-4 text-stone-500" />
                </div>
                <div className="flex-1">
                  <div className="h-4 flex items-center gap-0.5">
                    {[3,5,8,4,6,9,5,3,7,4,6,8,3,5].map((h, i) => (
                      <div key={i} className="w-1 bg-stone-300 rounded-full" style={{ height: `${h * 2}px` }} />
                    ))}
                  </div>
                  <div className="text-[9px] text-stone-400 mt-0.5">0:23</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Input bar */}
        <div className="px-4 py-3 border-t border-stone-200 flex items-center gap-2">
          <button className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center">
            <Camera className="w-4 h-4 text-stone-500" />
          </button>
          <div className="flex-1 bg-stone-100 rounded-full px-4 py-2 text-xs text-stone-400">
            {isEs ? 'Añadir nota...' : 'Add note...'}
          </div>
          <button className="w-8 h-8 rounded-full bg-stone-900 flex items-center justify-center">
            <Mic className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * Client vs Agent View Comparison - Fixed duplicate photos
 */
export const ClientAgentViewComparison = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("grid grid-cols-2 gap-4 max-w-2xl", className)}>
      {/* Client view - Clean, simple */}
      <div className="bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden">
        <div className="bg-emerald-50 px-3 py-2 flex items-center gap-2 border-b border-emerald-100">
          <Users className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-medium text-emerald-700">
            {isEs ? 'Lo que ve Sarah' : 'What Sarah sees'}
          </span>
        </div>
        <div className="p-3">
          <div className="h-20 relative rounded-lg mb-2 overflow-hidden">
            <Image
              src={LANDING_IMAGES.realityNiceLight}
              alt={isEs ? "Piso luminoso" : "Bright apartment"}
              fill
              className="object-cover"
              sizes="300px"
            />
          </div>
          <h4 className="text-sm font-semibold text-stone-800 mb-1">
            {isEs ? 'Piso luminoso en Gràcia' : 'Bright flat in Gràcia'}
          </h4>
          <p className="text-xs text-stone-500 mb-2">€485.000 • 95 m² • 3 hab.</p>
          <div className="bg-emerald-50 rounded-lg p-2">
            <p className="text-[10px] text-emerald-700">
              {isEs 
                ? '✨ Mucha luz natural, calle tranquila, cerca de metro'
                : '✨ Great natural light, quiet street, close to metro'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Agent view - Full data */}
      <div className="bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden">
        <div className="bg-stone-800 px-3 py-2 flex items-center gap-2">
          <Eye className="w-4 h-4 text-white" />
          <span className="text-xs font-medium text-white">
            {isEs ? 'Lo que ves tú' : 'What you see'}
          </span>
        </div>
        <div className="p-3">
          <div className="h-20 relative rounded-lg mb-2 overflow-hidden">
            <Image
              src={LANDING_IMAGES.buildingFacade}
              alt="Carrer de Verdi, 45"
              fill
              className="object-cover"
              sizes="300px"
            />
          </div>
          <h4 className="text-sm font-semibold text-stone-800 mb-1">Carrer de Verdi, 45 3º 2ª</h4>
          <p className="text-xs text-stone-500 mb-2">€485.000 • €5.105/m² • ITE 2021</p>
          <div className="space-y-1 text-[9px]">
            <div className="flex items-center gap-1 text-stone-600">
              <Check className="w-3 h-3 text-emerald-500" />
              {isEs ? 'Catastro verificado • Sin cargas' : 'Cadastro verified • No liens'}
            </div>
            <div className="flex items-center gap-1 text-amber-600">
              <AlertTriangle className="w-3 h-3" />
              {isEs ? 'Comunidad: €280/mes • 45d en mercado' : 'Community: €280/mo • 45d on market'}
            </div>
            <div className="flex items-center gap-1 text-stone-600">
              <FileText className="w-3 h-3 text-stone-400" />
              {isEs ? 'Checklist: 5 puntos para Sarah' : 'Checklist: 5 items for Sarah'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Efficiency Metrics Card
 */
export const EfficiencyMetricsCard = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-white rounded-2xl shadow-lg border border-stone-200 p-4 max-w-xs", className)}>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
          <Clock className="w-4 h-4 text-emerald-600" />
        </div>
        <span className="font-medium text-stone-800">
          {isEs ? 'Tiempo ahorrado esta semana' : 'Time saved this week'}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-stone-50 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-stone-800">47</div>
          <div className="text-[10px] text-stone-500">
            {isEs ? 'Anuncios analizados' : 'Listings analyzed'}
          </div>
        </div>
        <div className="bg-emerald-50 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-emerald-600">8h</div>
          <div className="text-[10px] text-emerald-600">
            {isEs ? 'Research ahorrado' : 'Research saved'}
          </div>
        </div>
        <div className="bg-stone-50 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-stone-800">12</div>
          <div className="text-[10px] text-stone-500">
            {isEs ? 'Shortlists enviadas' : 'Shortlists sent'}
          </div>
        </div>
        <div className="bg-amber-50 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-amber-600">3</div>
          <div className="text-[10px] text-amber-600">
            {isEs ? 'Visitas reservadas' : 'Viewings booked'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default {
  VignetteClientProfile,
  VignetteListingAnalysis,
  VignetteShortlist,
  BrowserExtensionMockup,
  ClientAgentViewComparison,
  EfficiencyMetricsCard,
  MultiClientIsochroneMap,
  SharedNotesVisual
};

