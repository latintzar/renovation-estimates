"use client";

import React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  Pause,
  Play,
  ArrowRight,
  Mic,
  Camera
} from "lucide-react";

// Image paths
const LIFE_IMAGES = {
  firstPlace: "/images/landing/life-first-place.webp",
  flatmates: "/images/landing/life-flatmates.webp",
  movingIn: "/images/landing/life-moving-in.webp",
  family: "/images/landing/life-family.webp",
} as const;

/**
 * Editorial-style life stages layout
 * Asymmetric grid with better visual hierarchy
 */
export const LifeStagesCinematic = ({ className }: { className?: string }) => {
  const { locale, dictionary } = useDictionary();
  const isEs = locale === 'es';
  const t = dictionary.renters.movingProfile;
  
  return (
    <div className={cn("w-full", className)}>
      {/* Editorial asymmetric grid */}
      <div className="grid grid-cols-12 gap-3 mb-6">
        {/* Left column - Pause mockup + First place (large) */}
        <div className="col-span-12 md:col-span-5 space-y-3">
          {/* Pause mockup - Hinge style paused state - ABOVE the image */}
          <div className="bg-stone-800/80 backdrop-blur rounded-xl p-5 text-center">
            {/* Illustration - paused Leo */}
            <div className="w-16 h-16 mx-auto mb-3 relative">
              <div className="absolute inset-0 bg-amber-500/10 rounded-full" />
              <div className="absolute inset-2 bg-amber-500/20 rounded-full flex items-center justify-center">
                <div className="flex gap-1">
                  <div className="w-1.5 h-6 bg-amber-400 rounded-full" />
                  <div className="w-1.5 h-6 bg-amber-400 rounded-full" />
                </div>
              </div>
            </div>
            
            {/* Headline */}
            <div className="text-white text-sm font-medium mb-1">
              {t.pauseTitle}
            </div>
            
            {/* Explanation */}
            <p className="text-stone-400 text-xs mb-4">
              {t.pauseDescription}
            </p>
            
            {/* Button */}
            <button className="bg-white text-stone-900 text-xs font-medium py-2 px-6 rounded-full hover:bg-stone-100 transition-colors">
              {t.resumeButton}
            </button>
          </div>
          
          {/* First place - hero size */}
          <div className="relative aspect-[4/5] rounded-2xl overflow-hidden group">
            <Image
              src={LIFE_IMAGES.firstPlace}
              alt={isEs ? "Primer piso" : "First apartment"}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-105"
              sizes="(max-width: 768px) 100vw, 40vw"
            />
          </div>
        </div>

        {/* Right column - 2x2 grid + Reactivate */}
        <div className="col-span-12 md:col-span-7 space-y-3">
          {/* Top row - Flatmates (wide) */}
          <div className="relative aspect-[16/9] rounded-2xl overflow-hidden group">
            <Image
              src={LIFE_IMAGES.flatmates}
              alt={isEs ? "Vivir con compañeros" : "Living with flatmates"}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-105"
              sizes="(max-width: 768px) 100vw, 60vw"
            />
          </div>

          {/* Bottom row - Together + Family side by side */}
          <div className="grid grid-cols-2 gap-3">
            <div className="relative aspect-[4/5] rounded-2xl overflow-hidden group">
              <Image
                src={LIFE_IMAGES.movingIn}
                alt={isEs ? "Mudándose juntos" : "Moving in together"}
                fill
                className="object-cover transition-transform duration-500 group-hover:scale-105"
                sizes="(max-width: 768px) 50vw, 30vw"
              />
            </div>

            <div className="relative aspect-[4/5] rounded-2xl overflow-hidden group">
              <Image
                src={LIFE_IMAGES.family}
                alt={isEs ? "Familia creciendo" : "Growing family"}
                fill
                className="object-cover transition-transform duration-500 group-hover:scale-105"
                sizes="(max-width: 768px) 50vw, 30vw"
              />
            </div>
          </div>

          {/* Reactivate mockup - conversational */}
          <div className="bg-gradient-to-r from-emerald-900/60 to-stone-800/60 backdrop-blur rounded-xl p-4">
            {/* Header */}
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                <Play className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex-1">
                <div className="text-white text-sm font-medium">
                  {isEs ? '¡Bienvenido de vuelta!' : 'Welcome back!'}
                </div>
                <div className="text-emerald-300/60 text-xs">
                  {isEs ? 'Antes de empezar — una pregunta rápida' : 'Before we start — quick question'}
                </div>
              </div>
            </div>
            
            {/* Leo's question */}
            <div className="bg-stone-900/60 rounded-xl p-3 mb-3">
              <div className="text-white/90 text-sm mb-1">
                {isEs ? '¿Qué tal el de Gràcia?' : 'How was the Gràcia place?'}
              </div>
              <div className="text-stone-400 text-xs">
                {isEs ? '¿Algo que Leo debería saber para la próxima?' : 'Anything Leo should know for next time?'}
              </div>
            </div>
            
            {/* Answer input - WhatsApp style */}
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-stone-800 rounded-full px-4 py-2 flex items-center gap-2">
                <input 
                  type="text" 
                  placeholder={isEs ? "Cuéntale a Leo..." : "Tell Leo..."} 
                  className="flex-1 bg-transparent text-white text-sm placeholder:text-stone-500 outline-none"
                  readOnly
                />
                <button className="w-7 h-7 rounded-full bg-stone-700 hover:bg-stone-600 flex items-center justify-center transition-colors">
                  <Camera className="w-3.5 h-3.5 text-stone-400" />
                </button>
              </div>
              <button className="w-9 h-9 rounded-full bg-emerald-600 hover:bg-emerald-500 flex items-center justify-center transition-colors shrink-0">
                <Mic className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom caption */}
      <p className="text-center text-stone-400 text-sm">
        {isEs 
          ? 'Distintas personas. Distintas etapas. Un Leo que aprende de todos.' 
          : 'Different people. Different chapters. One Leo that learns from everyone.'}
      </p>
    </div>
  );
};

/**
 * Compact horizontal timeline with images (alternative layout)
 */
export const LifeStagesHorizontal = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const stages = [
    { image: LIFE_IMAGES.firstPlace, year: "'22", label: isEs ? "Estudio" : "Studio" },
    { image: LIFE_IMAGES.flatmates, year: "'23", label: isEs ? "Compartido" : "Shared" },
    { image: LIFE_IMAGES.movingIn, year: "'25", label: isEs ? "Juntos" : "Together" },
    { image: LIFE_IMAGES.family, year: "'28", label: isEs ? "Familia" : "Family" },
  ];

  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <div className="flex items-center gap-2 min-w-max px-4">
        {stages.map((stage, index) => (
          <React.Fragment key={stage.year}>
            <div className="relative w-20 h-28 rounded-lg overflow-hidden shrink-0">
              <Image
                src={stage.image}
                alt={stage.label}
                fill
                className="object-cover"
                sizes="80px"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
              <div className="absolute bottom-2 left-2 right-2 text-center">
                <div className="text-white/60 text-[8px] font-mono">{stage.year}</div>
                <div className="text-white text-[10px] font-medium">{stage.label}</div>
              </div>
            </div>
            {index < stages.length - 1 && (
              <ArrowRight className="w-4 h-4 text-stone-500 shrink-0" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

// Keep old exports for backwards compatibility
export const LifeStagesTimeline = LifeStagesCinematic;
export const LifeStagesCompact = LifeStagesHorizontal;
export const LifeStagesFilmstrip = LifeStagesCinematic;
