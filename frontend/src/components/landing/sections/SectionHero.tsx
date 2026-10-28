"use client";

import { ArrowRight, Play } from "lucide-react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { VoiceWaveform } from "../phone-mockups";
import { IsochroneMap, MadridIsochroneMap, MultiClientDashboard } from "../illustrations/Isochrones";

// Lazy load hero visuals to avoid circular dependencies during build
const HeroClientProfiles = dynamic(() => import("../illustrations/HeroVisuals").then(mod => ({ default: mod.HeroClientProfiles })), { ssr: false });

type HeroVisual = 'isochrone' | 'madridIsochrone' | 'multiClientDashboard' | 'clientProfiles' | 'waveform' | 'none';

interface SectionHeroProps {
  eyebrow: string;
  headline: string;
  subcopy: string;
  primaryCta: string;
  secondaryCta?: string;
  proLink?: string;
  onProLinkClick?: () => void;
  showWaveform?: boolean;
  showIsochrone?: boolean;
  heroVisual?: HeroVisual;
}

export const SectionHero = ({
  eyebrow,
  headline,
  subcopy,
  primaryCta,
  secondaryCta,
  proLink,
  onProLinkClick,
  showWaveform = true,
  showIsochrone = false,
  heroVisual,
}: SectionHeroProps) => {
  // Determine which visual to show
  // New heroVisual prop takes precedence, otherwise fall back to legacy props
  const visual: HeroVisual = heroVisual 
    ? heroVisual 
    : showIsochrone 
      ? 'isochrone' 
      : showWaveform 
        ? 'waveform' 
        : 'none';

  return (
    <section className="max-w-4xl mx-auto px-6 text-center mb-24 md:mb-32">
      {/* Eyebrow */}
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-stone-100 text-xs font-medium text-stone-600 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <span className="w-2 h-2 rounded-full bg-green-500"></span>
        {eyebrow}
      </div>
      
      {/* Headline */}
      <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[1.15] md:leading-[1.15] tracking-tight mb-8 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
        {headline}
      </h1>
      
      {/* Hero Visual - based on heroVisual prop */}
      {visual === 'isochrone' && (
        <div className="mb-10 animate-in fade-in zoom-in-95 duration-1000 delay-100">
          <IsochroneMap className="max-w-sm mx-auto" />
        </div>
      )}
      
      {visual === 'madridIsochrone' && (
        <div className="mb-10 animate-in fade-in zoom-in-95 duration-1000 delay-100">
          <MadridIsochroneMap className="max-w-sm mx-auto" />
        </div>
      )}
      
      {visual === 'multiClientDashboard' && (
        <div className="mb-10 animate-in fade-in zoom-in-95 duration-1000 delay-100">
          <MultiClientDashboard />
        </div>
      )}
      
      {visual === 'clientProfiles' && (
        <div className="mb-10 animate-in fade-in zoom-in-95 duration-1000 delay-100">
          <HeroClientProfiles />
        </div>
      )}
      
      {visual === 'waveform' && (
        <div className="mb-8 flex justify-center animate-in fade-in slide-in-from-bottom-8 duration-700 delay-150">
          <VoiceWaveform />
        </div>
      )}

      {/* Subcopy */}
      <p className="text-lg md:text-xl text-stone-600 leading-relaxed max-w-2xl mx-auto mb-10 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
        {subcopy}
      </p>
      
      {/* CTAs */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-10 duration-700 delay-300">
        <Button 
          size="lg" 
          className="rounded-full px-8 py-6 text-lg bg-stone-900 hover:bg-stone-800 text-white w-full sm:w-auto shadow-lg shadow-stone-900/10"
        >
          {primaryCta} <ArrowRight className="ml-2 w-5 h-5" />
        </Button>
        
        {secondaryCta && (
          <Button 
            variant="outline" 
            size="lg" 
            className="rounded-full px-6 py-6 text-lg border-stone-200 hover:bg-stone-50 w-full sm:w-auto"
          >
            {secondaryCta}
          </Button>
        )}
      </div>
      
      {/* Pro Link */}
      {proLink && (
        <button 
          onClick={onProLinkClick}
          className="mt-8 text-sm text-stone-500 hover:text-stone-900 transition-colors cursor-pointer animate-in fade-in duration-700 delay-500"
        >
          {proLink}
        </button>
      )}
    </section>
  );
};

