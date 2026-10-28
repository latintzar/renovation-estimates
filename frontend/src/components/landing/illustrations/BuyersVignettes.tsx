"use client";

import React from "react";
import Image from "next/image";
import { 
  Home,
  TrendingUp,
  Wrench,
  Check,
  X,
  Euro,
  Calendar,
  ArrowRight,
  Scale
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { LANDING_IMAGES } from "./LandingImages";

// ============================================================================
// BUYERS VIGNETTES - Compact elements for "How it Works"
// ============================================================================

/**
 * Step 1: "Tell Leo your buying goals"
 * Voice orb with buyer-specific conversation
 */
export const VignetteBuyerGoals = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[220px] bg-gradient-to-b from-stone-950 to-stone-900 rounded-2xl shadow-2xl overflow-hidden", className)}>
      {/* Call header */}
      <div className="px-3 py-2 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] text-stone-400 font-medium">
            {isEs ? 'Llamada con Leo' : 'Voice call with Leo'}
          </span>
        </div>
        <span className="text-[9px] text-stone-500">3:12</span>
      </div>
      
      {/* Amorphous Voice Orb */}
      <div className="flex justify-center py-5 relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div 
            className="w-24 h-24 rounded-full opacity-30 blur-xl"
            style={{
              background: 'conic-gradient(from 0deg, #10b981, #f472b6, #fbbf24, #10b981)',
              animation: 'spin 8s linear infinite'
            }}
          />
        </div>
        
        <div 
          className="relative w-16 h-16 z-10"
          style={{
            borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%',
            background: 'conic-gradient(from 180deg at 50% 50%, #10b981 0deg, #f9a8d4 60deg, #fde68a 120deg, #10b981 180deg, #f9a8d4 240deg, #fde68a 300deg, #10b981 360deg)',
            animation: 'morphOrb 8s ease-in-out infinite, spin 12s linear infinite reverse',
            boxShadow: '0 0 40px rgba(16, 185, 129, 0.3), inset 0 0 30px rgba(255, 255, 255, 0.1)'
          }}
        >
          <div className="absolute inset-2.5 rounded-full bg-white flex items-center justify-center shadow-inner">
            <div className="flex items-center gap-[2px]">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-[3px] bg-stone-800 rounded-full"
                  style={{
                    height: '14px',
                    animation: 'waveform 0.8s ease-in-out infinite',
                    animationDelay: `${i * 0.1}s`
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Buyer-specific conversation */}
      <div className="px-3 pb-3 space-y-2">
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-emerald-400 to-pink-400 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-[8px] text-white font-bold">L</span>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl rounded-tl-none px-2.5 py-1.5 text-[10px] text-stone-300">
            {isEs ? '"¿Cuánto te apetece reformar?"' : '"What\'s your renovation appetite?"'}
          </div>
        </div>
        
        <div className="flex items-start gap-2 justify-end">
          <div className="bg-emerald-500/40 backdrop-blur rounded-xl rounded-tr-none px-2.5 py-1.5 text-[10px] text-emerald-100">
            {isEs ? '"Encantado de hacer reforma integral si el precio compensa"' : '"Happy to do a full reno if the price is right"'}
          </div>
        </div>
        
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
 * Step 2: "Get matched properties"
 * Property card with buyer-specific insights (investment angle)
 */
export const VignetteBuyerMatch = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[200px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Property image */}
      <div className="h-24 relative">
        <Image
          src={LANDING_IMAGES.propertyCardApartment}
          alt={isEs ? "Piso en Eixample" : "Eixample apartment"}
          fill
          className="object-cover"
          sizes="200px"
        />
        <div className="absolute top-2 left-2 px-2 py-0.5 bg-emerald-500 text-white text-[9px] font-bold rounded shadow-sm">
          91% {isEs ? 'encaja' : 'fit'}
        </div>
        <div className="absolute bottom-2 right-2 px-2 py-0.5 bg-amber-500 text-white text-[9px] font-bold rounded shadow-sm">
          {isEs ? 'Potencial reforma' : 'Reno potential'}
        </div>
      </div>
      
      {/* Details */}
      <div className="p-3">
        <div className="flex justify-between items-start mb-2">
          <div>
            <div className="text-xs font-semibold text-stone-900">
              {isEs ? '3 hab. Eixample' : '3-bed Eixample'}
            </div>
            <div className="text-[10px] text-stone-500">€485.000 • 95m²</div>
          </div>
        </div>
        
        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div className="bg-stone-50 rounded-lg p-1.5 text-center">
            <div className="text-[9px] text-stone-500">€/m²</div>
            <div className="text-[11px] font-bold text-stone-800">€5.105</div>
          </div>
          <div className="bg-emerald-50 rounded-lg p-1.5 text-center">
            <div className="text-[9px] text-emerald-600">{isEs ? 'vs media zona' : 'vs area avg'}</div>
            <div className="text-[11px] font-bold text-emerald-700">-8%</div>
          </div>
        </div>
        
        {/* Why it fits */}
        <div className="bg-stone-900 rounded-lg p-2">
          <div className="text-[8px] font-medium text-stone-400 mb-1">
            {isEs ? 'Por qué encaja:' : 'Why it fits:'}
          </div>
          <div className="text-[9px] text-white leading-relaxed">
            {isEs 
              ? 'Antiguo pero sólido. Año 1985, ITE OK. €60k reforma = €600k valor.'
              : 'Dated but solid. 1985 build, ITE passed. €60k reno = €600k value.'}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 3: "Viewing checklist for each serious property"
 * Exaggerated, simple checklist card - the detailed one is in the section below
 * Height matches VignetteBuyerGoals and VignetteBuyerMatch (~280px)
 */
export const VignetteBuyerChecklist = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const checklistItems = isEs ? [
    { text: 'Comprobar humedad en esquinas', checked: true },
    { text: 'Preguntar por la ITE', checked: true },
    { text: 'Probar presión del agua', checked: false },
    { text: 'Revisar orientación luz', checked: false },
  ] : [
    { text: 'Check corners for damp', checked: true },
    { text: 'Ask about ITE status', checked: true },
    { text: 'Test water pressure', checked: false },
    { text: 'Check light orientation', checked: false },
  ];
  
  return (
    <div className={cn("w-[200px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-emerald-600 px-3 py-2">
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-white" />
          <span className="text-[11px] text-white font-medium">
            {isEs ? 'Tu checklist de visita' : 'Your viewing checklist'}
          </span>
        </div>
      </div>
      
      {/* Property hint */}
      <div className="px-3 py-1.5 bg-stone-50 border-b border-stone-100">
        <div className="text-[10px] text-stone-500 text-left">
          {isEs ? 'Para: Eixample, C/ Bailèn' : 'For: Eixample, C/ Bailèn'}
        </div>
      </div>
      
      {/* Checklist items - left aligned */}
      <div className="p-3 space-y-3">
        {checklistItems.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={cn(
              "w-4 h-4 rounded border-2 flex items-center justify-center shrink-0",
              item.checked 
                ? "bg-emerald-500 border-emerald-500" 
                : "border-stone-300"
            )}>
              {item.checked && <Check className="w-3 h-3 text-white" />}
            </div>
            <span className={cn(
              "text-[11px] text-left",
              item.checked ? "text-stone-400 line-through" : "text-stone-700"
            )}>
              {item.text}
            </span>
          </div>
        ))}
      </div>
      
      {/* Progress hint */}
      <div className="px-3 pb-3 pt-1">
        <div className="flex items-center justify-between text-[9px]">
          <span className="text-stone-400">2/4 {isEs ? 'completado' : 'done'}</span>
          <span className="text-emerald-600 font-medium">50%</span>
        </div>
        <div className="h-1.5 bg-stone-100 rounded-full mt-1 overflow-hidden">
          <div className="h-full w-1/2 bg-emerald-500 rounded-full" />
        </div>
      </div>
    </div>
  );
};

/**
 * Step 3 alt: "Compare & decide"
 * Side-by-side comparison card (moved to later section)
 */
export const VignetteBuyerCompare = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[240px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-stone-900 px-3 py-2 flex items-center gap-2">
        <Scale className="w-4 h-4 text-white" />
        <span className="text-[11px] text-white font-medium">
          {isEs ? 'Comparando 2 propiedades' : 'Comparing 2 properties'}
        </span>
      </div>
      
      {/* Comparison grid */}
      <div className="p-3">
        <div className="grid grid-cols-3 gap-2 text-[9px]">
          {/* Headers */}
          <div className="text-stone-400"></div>
          <div className="text-center font-medium text-stone-700">Eixample</div>
          <div className="text-center font-medium text-stone-700">Gràcia</div>
          
          {/* Price */}
          <div className="text-stone-500 py-1">{isEs ? 'Precio' : 'Price'}</div>
          <div className="text-center py-1 font-semibold">€485k</div>
          <div className="text-center py-1 font-semibold">€520k</div>
          
          {/* Size */}
          <div className="text-stone-500 py-1">{isEs ? 'Tamaño' : 'Size'}</div>
          <div className="text-center py-1">95m²</div>
          <div className="text-center py-1">82m²</div>
          
          {/* €/m² */}
          <div className="text-stone-500 py-1">€/m²</div>
          <div className="text-center py-1 text-emerald-600 font-medium">€5.105</div>
          <div className="text-center py-1 text-amber-600 font-medium">€6.341</div>
          
          {/* Condition */}
          <div className="text-stone-500 py-1">{isEs ? 'Estado' : 'Condition'}</div>
          <div className="text-center py-1">
            <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[8px]">
              {isEs ? 'Para reformar' : 'Needs work'}
            </span>
          </div>
          <div className="text-center py-1">
            <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-[8px]">
              {isEs ? 'Para entrar' : 'Move-in'}
            </span>
          </div>
          
          {/* Match */}
          <div className="text-stone-500 py-1">{isEs ? 'Tu fit' : 'Your fit'}</div>
          <div className="text-center py-1">
            <span className="font-bold text-emerald-600">91%</span>
          </div>
          <div className="text-center py-1">
            <span className="font-bold text-stone-600">78%</span>
          </div>
        </div>
        
        {/* Leo's take */}
        <div className="mt-3 pt-3 border-t border-stone-100">
          <div className="flex items-start gap-2">
            <div className="w-5 h-5 rounded-full bg-stone-900 flex items-center justify-center shrink-0">
              <span className="text-[8px] text-white font-bold">L</span>
            </div>
            <p className="text-[9px] text-stone-600 leading-relaxed">
              {isEs 
                ? 'Eixample necesita €50-70k de reforma pero sale más barato por m² y encaja mejor con tu estilo.'
                : 'Eixample needs €50-70k reno but ends up cheaper per m² and matches your style better.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// BUYERS-SPECIFIC MOCKUPS
// ============================================================================

/**
 * Investment Analysis Card
 */
export const BuyerInvestmentCard = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden max-w-sm", className)}>
      <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-white" />
          <span className="text-white font-medium">
            {isEs ? 'Resumen de inversión' : 'Investment Snapshot'}
          </span>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Purchase breakdown */}
        <div>
          <div className="text-xs text-stone-500 mb-2">
            {isEs ? 'Inversión total' : 'Total investment'}
          </div>
          <div className="space-y-1.5">
            <div className="flex justify-between text-sm">
              <span className="text-stone-600">{isEs ? 'Precio compra' : 'Purchase price'}</span>
              <span className="font-semibold">€485.000</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-stone-600">{isEs ? 'Impuestos y gastos (~12%)' : 'Taxes & fees (~12%)'}</span>
              <span className="font-semibold">€58.200</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-stone-600">{isEs ? 'Estimación reforma' : 'Renovation estimate'}</span>
              <span className="font-semibold text-amber-600">€65.000</span>
            </div>
            <div className="flex justify-between text-sm pt-2 border-t border-stone-100">
              <span className="font-medium text-stone-900">Total</span>
              <span className="font-bold text-stone-900">€608.200</span>
            </div>
          </div>
        </div>
        
        {/* Value comparison */}
        <div className="bg-emerald-50 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-emerald-700">
              {isEs ? 'Valor estimado post-reforma' : 'Post-reno value estimate'}
            </span>
            <span className="font-bold text-emerald-700">€680.000</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-emerald-200 rounded-full overflow-hidden">
              <div className="h-full w-[89%] bg-emerald-500 rounded-full" />
            </div>
            <span className="text-xs font-semibold text-emerald-700">+12%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Renovation Appetite Slider (for profile)
 */
export const RenovationAppetiteSlider = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-white rounded-xl border border-stone-200 p-4", className)}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-stone-700">
          {isEs ? 'Ganas de reformar' : 'Renovation appetite'}
        </span>
        <span className="text-xs text-amber-600 font-medium">
          {isEs ? 'Alta' : 'High'}
        </span>
      </div>
      
      <div className="relative">
        <div className="h-2 bg-stone-100 rounded-full">
          <div className="h-full w-[75%] bg-gradient-to-r from-emerald-400 to-amber-400 rounded-full" />
        </div>
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-amber-500 rounded-full shadow"
          style={{ left: '75%', transform: 'translate(-50%, -50%)' }}
        />
      </div>
      
      <div className="flex justify-between mt-2 text-[10px] text-stone-400">
        <span>{isEs ? 'Solo para entrar' : 'Move-in ready only'}</span>
        <span>{isEs ? 'Reforma integral OK' : 'Full gut reno OK'}</span>
      </div>
    </div>
  );
};

export default {
  VignetteBuyerGoals,
  VignetteBuyerMatch,
  VignetteBuyerChecklist,
  VignetteBuyerCompare,
  BuyerInvestmentCard,
  RenovationAppetiteSlider
};

