"use client";

import { Check, FileText, Users, TrendingUp, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  SectionHero, 
  SectionBenefits,
  SectionCTA,
  HowItWorks,
} from "./sections";
import { 
  RelocationBriefMockup, 
  RelocationMapMockup, 
  CitySkylineImage,
  VignetteBriefForm,
  VignetteCityAnalysis,
  VignetteDashboard,
  FamilyOverlapVisual,
  ClientPortalMockup,
  VoiceAgentIntakeMockup,
} from "./illustrations";

export const RelocationContent = () => {
  const { dictionary: t, locale } = useDictionary();
  const content = t.relocation;
  
  return (
    <div className="animate-in fade-in duration-500">
      {/* Hero - Multi-client dashboard showing multiple family relocations */}
      <SectionHero
        eyebrow={content.hero.eyebrow}
        headline={content.hero.headline}
        subcopy={content.hero.subcopy}
        primaryCta={content.hero.primaryCta}
        secondaryCta={content.hero.secondaryCta}
        heroVisual="multiClientDashboard"
      />

      {/* How It Works - alternating layout matching Renters */}
      <HowItWorks
        title={content.howItWorks.title}
        subtitle={locale === 'es' ? 'Estandariza tu workflow de reubicación del brief al contrato firmado' : 'Standardise your relocation workflow from brief to signed lease'}
        steps={content.howItWorks.steps}
        vignettes={[
          <VignetteBriefForm key="brief" />,
          <VignetteCityAnalysis key="city" />,
          <VignetteDashboard key="dashboard" />
        ]}
      />

      {/* Family Overlap Visual */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="text-center mb-8">
          <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-2">
            {content.familyOverlap.title}
          </h3>
          <p className="text-stone-500">
            {content.familyOverlap.description}
          </p>
        </div>
        <div className="flex justify-center">
          <FamilyOverlapVisual />
        </div>
      </section>

      {/* Housing Brief + Assignees Mockup */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-8">
          <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-2">
            {locale === 'es' ? 'Briefs estructurados + muchas mudanzas' : 'Structured briefs + many moves'}
          </h3>
          <p className="text-stone-500">
            {locale === 'es' ? 'Sigue a los asignados entre ciudades con perfiles de vivienda estandarizados' : 'Track assignees across cities with standardised housing profiles'}
          </p>
        </div>
        <RelocationBriefMockup />
      </section>

      {/* Housing Brief */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="w-12 h-12 rounded-2xl bg-stone-100 flex items-center justify-center mb-6">
              <FileText className="w-6 h-6 text-stone-900" />
            </div>
            <h2 className="font-serif text-3xl mb-6">{content.housingBrief.title}</h2>
            <p className="text-stone-600 leading-relaxed mb-6">{content.housingBrief.description}</p>
            
            <ul className="space-y-3 mb-6">
              {content.housingBrief.items.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600">
                  <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <p className="text-stone-500 text-sm mb-4">
              {locale === 'es' ? 'Este brief:' : 'This brief:'}
            </p>
            <ul className="space-y-2 mb-6 pl-4">
              {content.housingBrief.briefFeatures.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <Button variant="outline" className="rounded-full border-stone-200 hover:bg-stone-50">
              {content.housingBrief.cta}
            </Button>
          </div>
          
          {/* Mock Housing Brief Card */}
          <div className="bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden">
            <div className="bg-stone-900 text-white p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold">PM</div>
                <div>
                  <h3 className="font-bold">Pablo Martínez</h3>
                  <p className="text-stone-300 text-xs">{locale === 'es' ? 'Ingeniero Senior • Mudanza desde Austin' : 'Senior Engineer • Moving from Austin'}</p>
                </div>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-start gap-3">
                <Globe className="w-5 h-5 text-stone-400 shrink-0" />
                <div>
                  <p className="text-xs text-stone-500 mb-1">{locale === 'es' ? 'Ubicación de la oficina' : 'Office Location'}</p>
                  <p className="text-stone-900 font-medium">@22 District, Barcelona</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <Users className="w-5 h-5 text-stone-400 shrink-0" />
                <div>
                  <p className="text-xs text-stone-500 mb-1">{locale === 'es' ? 'Familia' : 'Family'}</p>
                  <p className="text-stone-900 font-medium">{locale === 'es' ? 'Pareja + 2 hijos (5, 8)' : 'Partner + 2 children (5, 8)'}</p>
                </div>
              </div>
              
              <div className="border-t border-stone-100 pt-4">
                <p className="text-xs text-stone-500 mb-2">{locale === 'es' ? 'Requisitos clave' : 'Key Requirements'}</p>
                <div className="flex flex-wrap gap-2">
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">{locale === 'es' ? 'Acceso colegio internacional' : 'International school access'}</span>
                  <span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs">{locale === 'es' ? '3+ habitaciones' : '3+ bedrooms'}</span>
                  <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-xs">{locale === 'es' ? 'Máx 30min commute' : 'Max 30min commute'}</span>
                </div>
              </div>
              
              <div className="border-t border-stone-100 pt-4">
                <p className="text-xs text-stone-500 mb-2">{locale === 'es' ? 'Sensibilidades' : 'Sensitivities'}</p>
                <div className="flex flex-wrap gap-2">
                  <span className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs">{locale === 'es' ? 'Sin escaleras (movilidad pareja)' : 'No stairs (partner mobility)'}</span>
                  <span className="px-2 py-1 bg-stone-100 text-stone-600 rounded text-xs">{locale === 'es' ? 'Tardes tranquilas' : 'Quiet evenings'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Voice Agent for Assignee Intake */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <VoiceAgentIntakeMockup />
          <div>
            <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-4">
              {locale === 'es' ? 'Onboarding de asignados con tu marca' : 'Assignee onboarding with your brand'}
            </h3>
            <p className="text-stone-600 leading-relaxed mb-6">
              {locale === 'es' 
                ? 'Envía un enlace de Leo con tu marca a cada asignado. Ellos hablan con Leo sobre sus necesidades de vivienda, y tú recibes un brief estructurado listo para trabajar.' 
                : 'Send a Leo link with your branding to each assignee. They talk to Leo about their housing needs, and you receive a structured brief ready to work with.'}
            </p>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Tu logo y colores en la interfaz' : 'Your logo and colors in the interface'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Conversación de voz natural en múltiples idiomas' : 'Natural voice conversation in multiple languages'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Brief de vivienda estructurado automático' : 'Automatic structured housing brief'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Integración con tu CRM' : 'Integration with your CRM'}</span>
              </li>
            </ul>
            <Button variant="outline" className="rounded-full border-stone-200 hover:bg-stone-50">
              {locale === 'es' ? 'Ver demo del intake' : 'See intake demo'}
            </Button>
          </div>
        </div>
      </section>

      {/* Local Network */}
      <section className="max-w-4xl mx-auto px-6 mb-32">
        <div className="bg-stone-900 text-white rounded-3xl p-8 md:p-12 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center mb-6">
            <Users className="w-6 h-6 text-white" />
          </div>
          <h2 className="font-serif text-3xl mb-6">{content.localNetwork.title}</h2>
          <p className="text-stone-300 leading-relaxed mb-6">{content.localNetwork.description}</p>
          
          <ul className="space-y-2 mb-6">
            {content.localNetwork.attachments.map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-stone-300">
                <Check className="w-5 h-5 text-green-400 mt-0.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          
          <p className="text-white font-medium mb-4">
            {locale === 'es' ? 'Esto permite a tus partners:' : 'This lets your partners:'}
          </p>
          <ul className="space-y-2 mb-6">
            {content.localNetwork.partnerBenefits.map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-stone-300">
                <span className="w-1.5 h-1.5 rounded-full bg-white mt-2 shrink-0"></span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          
          <p className="text-stone-400 italic text-sm">{content.localNetwork.detail}</p>
        </div>
      </section>

      {/* Map Mockup */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <RelocationMapMockup />
      </section>

      {/* City Skyline Visual */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="relative rounded-3xl overflow-hidden">
          <CitySkylineImage />
          <div className="absolute inset-0 bg-gradient-to-t from-stone-900/60 via-transparent to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
            <p className="text-xl md:text-2xl font-serif text-center">
              {locale === 'es' ? 'Cada mudanza es un nuevo comienzo — Leo lo hace más suave' : 'Every move is a new beginning — Leo makes it smoother'}
            </p>
          </div>
        </div>
      </section>

      {/* Feedback Loop */}
      <section className="max-w-4xl mx-auto px-6 mb-32">
        <div className="text-center mb-12">
          <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mx-auto mb-6">
            <TrendingUp className="w-8 h-8 text-stone-900" />
          </div>
          <h2 className="font-serif text-3xl md:text-4xl mb-4">{content.feedbackLoop.title}</h2>
          <p className="text-stone-600 leading-relaxed max-w-2xl mx-auto">{content.feedbackLoop.description}</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-stone-50 rounded-2xl p-6 border border-stone-100">
            <ul className="space-y-2">
              {content.feedbackLoop.actions.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <p className="text-stone-500 text-sm mt-4 italic">{content.feedbackLoop.leoRecords}</p>
          </div>
          
          <div className="bg-green-50 rounded-2xl p-6 border border-green-100">
            <p className="text-green-800 font-medium mb-4">
              {locale === 'es' ? 'Eso te permite:' : 'That allows you to:'}
            </p>
            <ul className="space-y-2">
              {content.feedbackLoop.benefits.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-green-700">
                  <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Why Use */}
      <SectionBenefits
        title={content.whyUse.title}
        items={content.whyUse.items}
        cta={content.whyUse.cta}
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
