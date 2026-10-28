"use client";

import React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  Train, 
  Bike, 
  Car,
  Footprints,
  Volume2, 
  Coffee, 
  Search,
  FileText,
  AlertTriangle,
  Calendar
} from "lucide-react";

/**
 * City & Access - Isochrone visualization with organic blobby shapes
 */
export const IsochroneVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full aspect-square max-w-[300px] bg-gradient-to-br from-stone-100 to-stone-200 rounded-2xl shadow-lg overflow-hidden", className)}>
      <svg viewBox="0 0 200 200" className="w-full h-full">
        {/* Street grid - warm stone tones */}
        <path d="M0,50 L200,50" stroke="#d6d3d1" strokeWidth="3" fill="none" />
        <path d="M0,100 L200,100" stroke="#c7c2bd" strokeWidth="5" fill="none" />
        <path d="M0,150 L200,150" stroke="#d6d3d1" strokeWidth="3" fill="none" />
        <path d="M50,0 L50,200" stroke="#d6d3d1" strokeWidth="3" fill="none" />
        <path d="M100,0 L100,200" stroke="#c7c2bd" strokeWidth="5" fill="none" />
        <path d="M150,0 L150,200" stroke="#d6d3d1" strokeWidth="3" fill="none" />
        
        {/* Diagonal avenues */}
        <path d="M20,0 L200,180" stroke="#ddd8d3" strokeWidth="2.5" fill="none" />
        <path d="M0,40 L160,200" stroke="#ddd8d3" strokeWidth="2.5" fill="none" />
        
        {/* Parks - emerald tones */}
        <ellipse cx="160" cy="45" rx="25" ry="20" fill="#a7f3d0" opacity="0.5" />
        <ellipse cx="35" cy="165" rx="20" ry="15" fill="#a7f3d0" opacity="0.5" />
        
        {/* Transit - outermost blob - stone/cool - translucent like hero */}
        <path 
          d="M100,15 C160,12 190,45 188,95 C186,140 165,175 120,188 C70,200 25,175 15,125 C5,75 30,30 70,18 C85,14 92,14 100,15Z"
          fill="#d6d3d1" 
          fillOpacity="0.35"
          stroke="#a8a29e"
          strokeWidth="1.5"
        />
        
        {/* Bike - middle blob - emerald - translucent like hero */}
        <path 
          d="M100,42 C150,38 175,65 178,105 C180,145 155,175 110,178 C65,180 35,155 32,110 C30,70 55,48 88,42 C94,41 97,41 100,42Z"
          fill="#6ee7b7"
          fillOpacity="0.35"
          stroke="#34d399"
          strokeWidth="1.5"
        />
        
        {/* Walking - inner blob - amber - translucent like hero */}
        <path 
          d="M100,72 C140,70 162,88 165,110 C168,135 148,158 105,160 C65,162 42,140 40,112 C38,85 60,72 90,72 C94,72 97,72 100,72Z"
          fill="#fcd34d"
          fillOpacity="0.4"
          stroke="#fbbf24"
          strokeWidth="1.5"
        />
      </svg>
      
      {/* Center point - House emoji */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-[5%] text-2xl drop-shadow-md">
        🏠
      </div>
      
      {/* Transport mode legend */}
      <div className="absolute top-3 left-3 flex flex-col gap-1.5">
        <div className="flex items-center gap-2 bg-white rounded-lg px-2.5 py-1.5 shadow-md border border-stone-200">
          <Train className="w-4 h-4 text-stone-600" />
          <span className="text-xs font-medium text-stone-700">{isEs ? 'Transp.' : 'Transit'}</span>
        </div>
        <div className="flex items-center gap-2 bg-white rounded-lg px-2.5 py-1.5 shadow-md border border-stone-200">
          <Bike className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-medium text-emerald-700">{isEs ? 'Bici' : 'Bike'}</span>
        </div>
        <div className="flex items-center gap-2 bg-white rounded-lg px-2.5 py-1.5 shadow-md border border-stone-200">
          <Footprints className="w-4 h-4 text-amber-600" />
          <span className="text-xs font-medium text-amber-700">{isEs ? 'A pie' : 'Walk'}</span>
        </div>
      </div>
      
      {/* Time label - stone dark */}
      <div className="absolute bottom-3 right-3 bg-stone-900 text-white text-sm font-bold px-4 py-2 rounded-xl shadow-lg">
        15 min
      </div>
    </div>
  );
};

/**
 * Street & Building - Sophisticated map like hero style
 */
export const MapPinsVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full aspect-square max-w-[300px] bg-gradient-to-br from-stone-100 to-stone-200 rounded-2xl shadow-lg overflow-hidden", className)}>
      <svg viewBox="0 0 200 200" className="w-full h-full">
        {/* Street grid - warm stone tones */}
        <path d="M0,100 Q40,95 100,100 Q160,105 200,100" stroke="#e7e5e4" strokeWidth="14" fill="none" strokeLinecap="round" />
        <path d="M100,0 Q95,40 100,100 Q105,160 100,200" stroke="#e7e5e4" strokeWidth="14" fill="none" strokeLinecap="round" />
        
        {/* Secondary streets */}
        <path d="M20,50 Q60,55 100,50" stroke="#f5f5f4" strokeWidth="6" fill="none" strokeLinecap="round" />
        <path d="M100,150 Q140,148 180,155" stroke="#f5f5f4" strokeWidth="6" fill="none" strokeLinecap="round" />
        
        {/* Building blocks - warm stone */}
        <rect x="15" y="15" width="55" height="55" fill="#d6d3d1" rx="8" opacity="0.6" />
        <rect x="130" y="15" width="55" height="55" fill="#d6d3d1" rx="8" opacity="0.6" />
        <rect x="15" y="130" width="55" height="55" fill="#d6d3d1" rx="8" opacity="0.6" />
        <rect x="130" y="130" width="55" height="55" fill="#d6d3d1" rx="8" opacity="0.6" />
        
        {/* Property pin - center - amber */}
        <g transform="translate(100, 100)">
          <ellipse cx="0" cy="12" rx="8" ry="4" fill="rgba(0,0,0,0.15)" />
          <path d="M0,-22 C10,-22 18,-14 18,-4 C18,8 0,22 0,22 C0,22 -18,8 -18,-4 C-18,-14 -10,-22 0,-22Z" fill="#f59e0b" />
          <circle cx="0" cy="-4" r="6" fill="white" />
        </g>
      </svg>
      
      {/* POI badges - unified colors: stone, emerald, amber */}
      <div className="absolute top-[14%] left-[22%] flex flex-col items-center">
        <div className="w-8 h-8 bg-stone-700 rounded-full flex items-center justify-center shadow-lg border-2 border-white">
          <Volume2 className="w-4 h-4 text-white" />
        </div>
        <span className="mt-1 text-xs bg-white px-2 py-0.5 rounded-lg shadow-md font-medium text-stone-700 border border-stone-200">Bar</span>
      </div>
      
      <div className="absolute top-[20%] right-[12%] flex flex-col items-center">
        <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg border-2 border-white">
          <Coffee className="w-4 h-4 text-white" />
        </div>
        <span className="mt-1 text-xs bg-white px-2 py-0.5 rounded-lg shadow-md font-medium text-emerald-700 border border-stone-200">Café</span>
      </div>
      
      <div className="absolute bottom-[18%] left-[12%] flex flex-col items-center">
        <div className="w-8 h-8 bg-stone-600 rounded-full flex items-center justify-center shadow-lg border-2 border-white">
          <Train className="w-4 h-4 text-white" />
        </div>
        <span className="mt-1 text-xs bg-white px-2 py-0.5 rounded-lg shadow-md font-medium text-stone-700 border border-stone-200">Metro</span>
      </div>
      
      {/* Noise indicator - amber accent */}
      <div className="absolute top-3 right-3 bg-amber-50 border border-amber-300 rounded-xl px-3 py-1.5 text-xs font-medium text-amber-700 flex items-center gap-1.5 shadow-md">
        <Volume2 className="w-4 h-4" /> {isEs ? 'Moderado' : 'Moderate'}
      </div>
    </div>
  );
};

/**
 * Look & Feel - AI analysis with React bounding boxes
 * Annotations fade in one by one on scroll and persist
 */
export const ImageRecognitionVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  const containerRef = React.useRef<HTMLDivElement>(null);
  
  // Track which annotations have been revealed (persist once shown)
  const [revealed, setRevealed] = React.useState({
    image: false,
    eastFacing: false,
    ceiling: false,
    floorArea: false,
    lightQuality: false,
  });
  
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Stagger the reveals - once triggered, they persist
            setRevealed((prev) => {
              if (prev.image) return prev; // Already triggered
              return { ...prev, image: true };
            });
            
            // Stagger annotations after image
            setTimeout(() => {
              setRevealed((prev) => ({ ...prev, eastFacing: true }));
            }, 400);
            
            setTimeout(() => {
              setRevealed((prev) => ({ ...prev, ceiling: true }));
            }, 700);
            
            setTimeout(() => {
              setRevealed((prev) => ({ ...prev, floorArea: true }));
            }, 1000);
            
            setTimeout(() => {
              setRevealed((prev) => ({ ...prev, lightQuality: true }));
            }, 1300);
          }
        });
      },
      { threshold: 0.4 } // Trigger when 40% visible
    );
    
    observer.observe(container);
    return () => observer.disconnect();
  }, []);
  
  return (
    <div 
      ref={containerRef}
      className={cn("relative w-full aspect-[16/9] max-w-[380px] rounded-2xl overflow-hidden shadow-xl border border-stone-200", className)}
    >
      {/* Base image */}
      <Image
        src="/images/landing/checklist-look-feel.webp"
        alt={isEs ? "Análisis IA de luz y espacio" : "AI light and space analysis"}
        fill
        className={cn(
          "object-cover transition-opacity duration-500",
          revealed.image ? "opacity-100" : "opacity-0"
        )}
        sizes="380px"
      />
      
      {/* React bounding boxes overlay */}
      <div className="absolute inset-0">
        {/* Emerald box - Natural light / East facing */}
        <div 
          className={cn(
            "absolute border-[2px] border-emerald-400 bg-emerald-400/10 transition-all duration-500",
            revealed.eastFacing ? "opacity-100 scale-100" : "opacity-0 scale-95"
          )}
          style={{ 
            left: '15%', 
            top: '8%', 
            width: '15%', 
            height: '78%',
            borderRadius: '4px'
          }}
        >
          {/* East facing label - to the right of the green box */}
          <div className={cn(
            "absolute top-2 -right-2 translate-x-full bg-emerald-500 text-white text-[11px] px-2.5 py-1.5 rounded-xl font-medium shadow-lg leading-tight whitespace-nowrap transition-all duration-500 delay-100",
            revealed.eastFacing ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"
          )}>
            <div className="font-semibold">{isEs ? 'Orientación este' : 'East facing'}</div>
            <div className="text-emerald-200 text-[9px]">{isEs ? 'Sol de mañana' : 'Morning sun'}</div>
          </div>
        </div>
        
        {/* Amber measurement arrow - Floor to ceiling height */}
        <div 
          className={cn(
            "absolute flex flex-col items-center transition-all duration-500",
            revealed.ceiling ? "opacity-100" : "opacity-0"
          )}
          style={{ 
            right: '8%', 
            top: '8%', 
            height: '78%'
          }}
        >
          {/* Top arrow */}
          <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[6px] border-b-amber-400" />
          {/* Vertical line */}
          <div className="w-[2px] flex-1 bg-amber-400" />
          {/* Bottom arrow */}
          <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[6px] border-t-amber-400" />
        </div>
        {/* Ceiling label - TOP RIGHT */}
        <div className={cn(
          "absolute top-3 right-[14%] bg-amber-400 text-amber-900 text-[11px] px-2.5 py-1.5 rounded-xl font-semibold shadow-lg leading-tight transition-all duration-500 delay-100",
          revealed.ceiling ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"
        )}>
          <div>3,2m</div>
          <div className="text-amber-700 text-[9px] font-medium">{isEs ? 'Techos altos' : 'High ceiling'}</div>
        </div>
        
        {/* Blue/indigo trapezoid - Floor area in perspective */}
        <svg 
          className={cn(
            "absolute inset-0 w-full h-full transition-opacity duration-500",
            revealed.floorArea ? "opacity-100" : "opacity-0"
          )}
          viewBox="0 0 100 100" 
          preserveAspectRatio="none"
        >
          <path 
            d="M0,100 L34,66 L67,66 L97,100 Z" 
            fill="rgba(99, 102, 241, 0.3)" 
            stroke="#818cf8" 
            strokeWidth="0.8" 
            strokeDasharray="2,1"
          />
        </svg>
        {/* Floor area label - BOTTOM LEFT */}
        <div className={cn(
          "absolute bottom-3 left-3 bg-indigo-500 text-white text-[11px] px-2.5 py-1.5 rounded-xl font-semibold shadow-lg leading-tight transition-all duration-500 delay-100",
          revealed.floorArea ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
        )}>
          <div>~28m²</div>
          <div className="text-indigo-200 text-[9px] font-medium">{isEs ? 'Salón' : 'Living area'}</div>
        </div>
        
        {/* Light quality label - BOTTOM RIGHT */}
        <div className={cn(
          "absolute bottom-3 right-3 bg-stone-900/90 backdrop-blur-sm text-white text-[11px] px-2.5 py-1.5 rounded-xl font-medium shadow-lg transition-all duration-500",
          revealed.lightQuality ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
        )}>
          {isEs ? 'Luz:' : 'Light:'} <span className="text-emerald-400 font-semibold">{isEs ? 'Excelente' : 'Excellent'}</span>
        </div>
      </div>
    </div>
  );
};

/**
 * Age & Structure - Top to bottom research flow
 */
export const InvestigationVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("flex flex-col gap-2.5 w-full max-w-[300px]", className)}>
      {/* 1. Listing data - what we start with */}
      <div className="bg-white rounded-2xl shadow-md border border-stone-200 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-stone-400" />
            <span className="text-xs text-stone-500 font-medium">{isEs ? 'Del anuncio' : 'From listing'}</span>
          </div>
          <div className="flex gap-3 text-sm">
            <span><span className="text-stone-500">4ª</span> <span className="text-amber-600 font-bold">{isEs ? 'sin asc.' : 'no lift'}</span></span>
            <span><span className="text-stone-500">Cert:</span> <span className="text-amber-600 font-bold">E</span></span>
          </div>
        </div>
      </div>
      
      {/* 2. Cadastro lookup */}
      <div className="bg-amber-50 rounded-2xl shadow-md border border-amber-200 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-amber-600" />
            <span className="text-xs text-amber-700 font-semibold">Catastro</span>
          </div>
          <div className="text-right">
            <span className="text-sm font-bold text-stone-800">1965</span>
            <span className="text-xs text-stone-500 ml-1.5">{isEs ? 'construcción' : 'built'}</span>
          </div>
        </div>
      </div>
      
      {/* 3. 2-barrel search - typical problems */}
      <div className="bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden">
        <div className="h-8 bg-stone-900 flex items-center px-3">
          <Search className="w-3.5 h-3.5 text-stone-400 mr-2" />
          <span className="text-xs text-white font-medium">{isEs ? 'Eixample 1960s — problemas típicos' : 'Eixample 1960s — typical issues'}</span>
        </div>
        <div className="p-3 space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span className="text-xs text-stone-700">{isEs ? 'Aluminosis en estructura' : 'Aluminosis in structure'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span className="text-xs text-stone-700">{isEs ? 'Instalación eléctrica antigua' : 'Old electrical wiring'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span className="text-xs text-stone-700">{isEs ? 'Tuberías de plomo' : 'Lead pipes'}</span>
          </div>
        </div>
      </div>
      
      {/* 4. Hidden vices - what to watch for */}
      <div className="bg-stone-900 rounded-2xl shadow-xl p-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span className="text-sm font-bold text-white">{isEs ? 'Vicios ocultos a revisar' : 'Hidden vices to check'}</span>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs text-stone-300">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
            <span>{isEs ? 'Humedades en fachada norte' : 'Damp on north facade'}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-stone-300">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
            <span>{isEs ? 'Bajantes comunitarios antiguos' : 'Old communal pipes'}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-stone-300">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
            <span>{isEs ? 'Ruido de patio interior' : 'Inner courtyard noise'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Combined export for use in SectionChecklist
 */
export const ChecklistVisuals = {
  cityAccess: IsochroneVisual,
  streetBuilding: MapPinsVisual,
  lookFeel: ImageRecognitionVisual,
  ageStructure: InvestigationVisual,
};
