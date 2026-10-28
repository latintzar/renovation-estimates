"use client";

import Image from "next/image";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  SectionHero, 
  SectionChecklist, 
  SectionTestimonials,
  SectionBenefits,
  SectionCTA,
  HowItWorks,
} from "./sections";
import { 
  BuyersChecklistMockup, 
  BuyersComparisonMockup, 
  VignetteBuyerGoals,
  VignetteBuyerMatch,
  VignetteBuyerChecklist,
  RenovationTiersMockup,
  LANDING_IMAGES,
} from "./illustrations";

interface BuyersContentProps {
  onProLinkClick: () => void;
}

export const BuyersContent = ({ onProLinkClick }: BuyersContentProps) => {
  const { dictionary: t, locale } = useDictionary();
  const content = t.buyers;
  
  return (
    <div className="animate-in fade-in duration-500">
      {/* Hero - Madrid isochrone map (different city from renters for variety) */}
      <SectionHero
        eyebrow={content.hero.eyebrow}
        headline={content.hero.headline}
        subcopy={content.hero.subcopy}
        primaryCta={content.hero.primaryCta}
        secondaryCta={content.hero.secondaryCta}
        proLink={t.shared.proLink}
        onProLinkClick={onProLinkClick}
        heroVisual="madridIsochrone"
      />

      {/* How It Works - alternating layout matching Renters */}
      <HowItWorks
        title={content.howItWorks.title}
        subtitle={locale === 'es' ? 'Del presupuesto a las llaves, Leo te guía en tu compra' : 'From budget to keys, Leo guides your buying journey'}
        steps={content.howItWorks.steps}
        vignettes={[
          <VignetteBuyerGoals key="goals" />,
          <VignetteBuyerMatch key="match" />,
          <VignetteBuyerChecklist key="checklist" />
        ]}
      />

      {/* What Leo Looks Into - with visuals */}
      <SectionChecklist
        title={content.whatLeoLooksInto.title}
        categories={content.whatLeoLooksInto.categories}
        callout={content.whatLeoLooksInto.callout}
        showVisuals={true}
      />

      {/* Viewing Checklist - Combined with mockup */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="text-center mb-10">
          <h2 className="font-serif text-3xl md:text-4xl text-stone-900 mb-3">{content.viewingChecklist.title}</h2>
          <p className="text-stone-600 leading-relaxed max-w-2xl mx-auto">{content.viewingChecklist.description}</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 items-start">
          {/* Left: The mockup - now enhanced with note-taking */}
        <BuyersChecklistMockup />

          {/* Right: What makes it special */}
          <div className="space-y-6">
            {/* What's in the checklist */}
            <div className="bg-white rounded-2xl p-6 border border-stone-100 shadow-sm">
              <h3 className="font-medium text-stone-900 mb-4">
                {locale === 'es' ? 'Qué incluye cada checklist' : 'What each checklist covers'}
              </h3>
              <ul className="space-y-2">
            {content.viewingChecklist.bullets.map((item, i) => (
              <li 
                key={i} 
                    className="flex items-start gap-3 text-stone-600 text-sm"
                dangerouslySetInnerHTML={{ 
                      __html: `<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0"></span><span>${item.replace(/\*\*(.*?)\*\*/g, '<strong class="text-stone-800">$1</strong>')}</span>` 
                }}
              />
            ))}
          </ul>
            </div>
            
            {/* What it reflects */}
            <div className="bg-stone-50 rounded-2xl p-6 border border-stone-100">
              <h4 className="text-sm font-medium text-stone-700 mb-3">
                {locale === 'es' ? 'Personalizado según:' : 'Personalized based on:'}
              </h4>
              <ul className="space-y-2">
            {content.viewingChecklist.reflects.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-stone-600 text-sm">
                    <Check className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
            </div>
            
            {/* Note-taking highlight */}
            <div className="bg-gradient-to-br from-emerald-50 to-stone-50 rounded-2xl p-6 border border-emerald-100">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">📝📷🎤</span>
                <h4 className="font-medium text-stone-900">
                  {locale === 'es' ? 'Añade notas durante la visita' : 'Add notes during viewings'}
                </h4>
              </div>
              <p className="text-sm text-stone-600">
                {locale === 'es' 
                  ? 'Texto, fotos o notas de voz — todo queda guardado con cada propiedad para comparar después.'
                  : 'Text, photos, or voice notes — everything saved with each property to compare later.'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* After Viewing + Comparison (merged) */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="text-center mb-10">
          <h2 className="font-serif text-3xl md:text-4xl text-stone-900 mb-3">{content.afterViewing.title}</h2>
          <p className="text-stone-600 max-w-2xl mx-auto">{content.afterViewing.detail}</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 items-start">
          {/* Left: Comparison mockup with notes */}
          <BuyersComparisonMockup />
          
          {/* Right: How Leo helps after viewing */}
          <div className="space-y-6">
            {/* What you can do */}
            <div className="bg-white rounded-2xl p-6 border border-stone-100 shadow-sm">
            <h3 className="font-medium text-stone-900 mb-4">{content.afterViewing.description}</h3>
            <ul className="space-y-2">
              {content.afterViewing.bullets.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          
            {/* What Leo does */}
          <div className="bg-stone-900 text-white rounded-2xl p-6">
              <h3 className="font-medium mb-4 flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
                  <span className="text-[10px] font-bold">L</span>
                </div>
                {locale === 'es' ? 'Luego Leo:' : 'Leo then:'}
              </h3>
            <ul className="space-y-2">
              {content.afterViewing.leoActions.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-stone-300 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        </div>
      </section>

      {/* Renovation Help */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="text-center mb-10">
          <h2 className="font-serif text-3xl md:text-4xl mb-4">{content.renovationHelp.title}</h2>
          <p className="text-stone-600 leading-relaxed max-w-2xl mx-auto">{content.renovationHelp.description}</p>
        </div>
        
        {/* Interactive mockup preview - includes tier tabs */}
        <div className="mb-10">
          <RenovationTiersMockup />
        </div>
        
        {/* Additional info */}
        <div className="bg-gradient-to-br from-stone-50 to-stone-100 rounded-3xl p-8 border border-stone-200">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Renovation paths */}
            <div>
              <h3 className="font-medium text-stone-900 mb-4">
                {locale === 'es' ? 'Opciones que Leo puede explorar:' : 'Paths Leo can explore:'}
              </h3>
              <div className="space-y-3">
            {content.renovationHelp.paths.map((path, i) => (
                  <div key={i} className="flex items-start gap-3 bg-white rounded-xl p-3 border border-stone-100 shadow-sm">
                    <div className="w-6 h-6 rounded-full bg-stone-900 text-white flex items-center justify-center text-xs font-bold shrink-0">
                  {i + 1}
                </div>
                <p className="text-stone-700 text-sm">{path}</p>
              </div>
            ))}
              </div>
          </div>
          
            {/* What Leo provides */}
            <div>
              <h3 className="font-medium text-stone-900 mb-4">
                {locale === 'es' ? 'Para cada opción, Leo esboza:' : 'For each path, Leo sketches:'}
              </h3>
          <ul className="space-y-2 mb-6">
            {content.renovationHelp.leoSketches.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                    <Check className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
            <p className="text-amber-800 text-sm italic">{content.renovationHelp.callout}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Your Future Home Visual */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-6">
          <div className="col-span-2 md:col-span-3 aspect-[16/10] relative overflow-hidden rounded-2xl shadow-lg">
            <Image
              src={LANDING_IMAGES.interiorApartment}
              alt="Bright Spanish apartment interior with natural light"
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 60vw"
            />
          </div>
          <div className="col-span-2 md:col-span-2 aspect-[4/3] md:aspect-[3/4] relative overflow-hidden rounded-2xl shadow-lg">
            <Image
              src={LANDING_IMAGES.buildingFacade}
              alt="Traditional Spanish apartment building facade"
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 40vw"
            />
          </div>
        </div>
        <p className="text-center text-stone-500 italic mt-6 text-sm">
          {locale === 'es' ? 'Encuentra una casa que encaje con tu vida, no solo con tu presupuesto' : 'Find a home that fits your life, not just your budget'}
        </p>
      </section>

      {/* Who This Is For */}
      <SectionBenefits
        title={content.whoThisIsFor.title}
        items={content.whoThisIsFor.items}
        variant="light"
      />

      {/* Testimonials */}
      <SectionTestimonials
        title={content.testimonials.title}
        quotes={content.testimonials.quotes}
      />

      {/* Final CTA */}
      <SectionCTA
        title={content.finalCta.title}
        description={content.finalCta.description}
        buttonText={content.finalCta.buttonText}
      />
    </div>
  );
};
