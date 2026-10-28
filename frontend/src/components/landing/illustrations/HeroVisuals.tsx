"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { Check, X, AlertTriangle, Sparkles } from "lucide-react";

// Import the actual isochrone components
import { MadridIsochroneMap, MultiClientDashboard } from "./Isochrones";

// ============================================================================
// HERO VISUAL: Madrid Isochrone (for Buyers)
// Re-export for consistency - uses Madrid map instead of Barcelona
// ============================================================================

export const HeroBuyersIsochrone = ({ className }: { className?: string }) => {
  return <MadridIsochroneMap className={className} />;
};

// ============================================================================
// HERO VISUAL: Multi-Client Dashboard (for Relocation)
// Shows multiple family isochrones in an exaggerated dashboard
// ============================================================================

export const HeroRelocationDashboard = ({ className }: { className?: string }) => {
  return <MultiClientDashboard className={className} />;
};

// ============================================================================
// HERO VISUAL: Client Profile Card (for Buyer Agents / Personal Shoppers)
// Clean card with headshot at top, clear preferences, and specific quirks
// ============================================================================

export const HeroClientProfiles = ({ className }: { className?: string }) => {
  const context = useDictionary();
  const isEs = context?.locale === 'es';

  return (
    <div className={cn("relative w-full max-w-sm mx-auto", className)} style={{ perspective: '800px' }}>
      {/* Profile card */}
      <div 
        className="bg-white rounded-2xl shadow-xl border border-stone-200 overflow-hidden"
        style={{ transform: 'rotateX(4deg) rotateY(-2deg)', transformOrigin: 'center center' }}
      >
        {/* Header with headshot centered */}
        <div className="bg-gradient-to-br from-stone-100 to-stone-50 pt-5 pb-4 px-5 text-center border-b border-stone-100">
          <img 
            src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop&crop=face" 
            alt="Sarah Parker"
            className="w-16 h-16 rounded-full object-cover ring-4 ring-white shadow-lg mx-auto mb-3"
          />
          <h3 className="font-semibold text-stone-900 text-lg">Sarah Parker</h3>
          <p className="text-stone-500 text-sm">Gràcia • €450-500k</p>
        </div>

        {/* What she cares about - clear sections */}
        <div className="p-4 space-y-4">
          
          {/* Must haves */}
          <div>
            <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Check className="w-3 h-3" />
              {isEs ? 'Imprescindible' : 'Must have'}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs text-emerald-700 font-medium">
                {isEs ? 'Luz natural' : 'Natural light'}
              </span>
              <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs text-emerald-700 font-medium">
                {isEs ? 'Terraza' : 'Terrace'}
              </span>
              <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs text-emerald-700 font-medium">
                {isEs ? 'Zona tranquila' : 'Quiet area'}
              </span>
            </div>
          </div>

          {/* Dealbreakers */}
          <div>
            <div className="text-[10px] font-bold text-rose-600 uppercase tracking-wider mb-2 flex items-center gap-1">
              <X className="w-3 h-3" />
              {isEs ? 'Descarta' : 'Dealbreaker'}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="px-2.5 py-1 bg-rose-50 border border-rose-200 rounded-full text-xs text-rose-700 font-medium">
                {isEs ? 'Planta baja' : 'Ground floor'}
              </span>
              <span className="px-2.5 py-1 bg-rose-50 border border-rose-200 rounded-full text-xs text-rose-700 font-medium">
                {isEs ? 'Sin ascensor' : 'No elevator'}
              </span>
            </div>
          </div>

          {/* Specific quirks - things Leo learned */}
          <div className="bg-blue-50/50 rounded-xl p-3 border border-blue-100">
            <div className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              {isEs ? 'Detalles que Leo aprendió' : 'Quirks Leo learned'}
            </div>
            <div className="space-y-1.5 text-xs text-stone-600">
              <div className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{isEs ? 'Trabaja desde casa — necesita un rincón para oficina' : 'Works from home — needs office nook'}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{isEs ? 'Hace yoga por las mañanas — valora suelo despejable' : 'Does morning yoga — values clearable floor'}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{isEs ? 'Odia el ruido de tráfico pero le gusta la vida de barrio' : 'Hates traffic noise but likes neighborhood life'}</span>
              </div>
            </div>
          </div>

          {/* Tolerance indicator */}
          <div className="flex items-center gap-2 text-xs text-stone-500">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span>{isEs ? 'Abierta a reforma si el hueso es bueno' : 'Open to reno if bones are good'}</span>
          </div>
        </div>
      </div>
      
      {/* Badge showing multiple clients */}
      <div className="absolute -top-2 -right-2 bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
        {isEs ? '3 clientes' : '3 clients'}
      </div>
    </div>
  );
};

// Legacy exports for backwards compatibility
export const HeroFamilyIsochrone = HeroRelocationDashboard;
export const HeroClientProfile = HeroClientProfiles;
export const HeroAssigneeProfile = HeroRelocationDashboard;
export const HeroSharedNotes = HeroClientProfiles;
