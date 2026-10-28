"use client";

import { Check, Users, ClipboardList, Eye, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  SectionHero, 
  SectionBenefits,
  SectionCTA,
  HowItWorks,
} from "./sections";
import {
  BuyerAgentsExtensionMockup,
  AgentWorkspaceImage,
  VignetteClientProfile,
  VignetteListingAnalysis,
  VignetteShortlist,
  ClientAgentViewComparison,
  EfficiencyMetricsCard,
  ClientPortalMockup,
  VoiceAgentIntakeMockup,
  LANDING_IMAGES,
} from "./illustrations";

export const BuyerAgentsContent = () => {
  const { dictionary: t, locale } = useDictionary();
  const content = t.agents;
  
  return (
    <div className="animate-in fade-in duration-500">
      {/* Hero - Client profiles showing multiple buyer clients */}
      <SectionHero
        eyebrow={content.hero.eyebrow}
        headline={content.hero.headline}
        subcopy={content.hero.subcopy}
        primaryCta={content.hero.primaryCta}
        secondaryCta={content.hero.secondaryCta}
        heroVisual="clientProfiles"
      />

      {/* How It Works - alternating layout matching Renters */}
      <HowItWorks
        title={content.howItWorks.title}
        subtitle={locale === 'es' ? 'Del onboarding del cliente a la oferta firmada, Leo se encarga de la investigación' : 'From client onboarding to signed offer, Leo handles the research'}
        steps={content.howItWorks.steps}
        vignettes={[
          <VignetteClientProfile key="profile" />,
          <VignetteListingAnalysis key="analysis" />,
          <VignetteShortlist key="shortlist" />
        ]}
      />

      {/* Efficiency Metrics */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1 text-center md:text-left">
            <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-4">
              {locale === 'es' ? 'Trabaja más inteligente, no más duro' : 'Work smarter, not harder'}
            </h3>
            <p className="text-stone-500 max-w-md">
              {locale === 'es' 
                ? 'Leo se encarga de la investigación que consume tiempo para que puedas concentrarte en lo que importa: construir relaciones y cerrar tratos.' 
                : 'Leo handles time-consuming research so you can focus on what matters: building relationships and closing deals.'}
            </p>
          </div>
          <EfficiencyMetricsCard />
        </div>
      </section>

      {/* Client Portal - Send properties to clients with full context */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-8">
          <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-2">
            {locale === 'es' ? 'Envía anuncios con contexto completo' : 'Send listings with full context'}
          </h3>
          <p className="text-stone-500 max-w-2xl mx-auto">
            {locale === 'es' 
              ? 'Portal de cliente con tu marca: perfil, propiedades seleccionadas, notas de visita, y opciones de reforma. Los clientes pueden dar like, comentar y comparar.' 
              : 'Branded client portal: profile, curated properties, visit notes, and renovation options. Clients can like, comment, and compare.'}
          </p>
        </div>
        <ClientPortalMockup />
      </section>
      
      {/* Voice Agent for Client Intake */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-4">
              {locale === 'es' ? 'Onboarding de clientes con tu marca' : 'Client onboarding with your brand'}
            </h3>
            <p className="text-stone-600 leading-relaxed mb-6">
              {locale === 'es' 
                ? 'Comparte un enlace de Leo con tu marca. El cliente habla con Leo sobre lo que busca, y tú recibes un perfil estructurado listo para trabajar.' 
                : 'Share a Leo link with your branding. The client talks to Leo about what they want, and you receive a structured profile ready to work with.'}
            </p>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Tu logo y colores en la interfaz' : 'Your logo and colors in the interface'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Conversación de voz natural con Leo' : 'Natural voice conversation with Leo'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Perfil estructurado automático' : 'Automatic structured profile'}</span>
              </li>
              <li className="flex items-start gap-3 text-stone-600">
                <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                <span>{locale === 'es' ? 'Enlace único por cliente' : 'Unique link per client'}</span>
              </li>
            </ul>
            <Button variant="outline" className="rounded-full border-stone-200 hover:bg-stone-50">
              {locale === 'es' ? 'Ver demo del intake' : 'See intake demo'}
            </Button>
          </div>
          <VoiceAgentIntakeMockup />
        </div>
      </section>

      {/* Client Profile */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="w-12 h-12 rounded-2xl bg-stone-100 flex items-center justify-center mb-6">
              <Users className="w-6 h-6 text-stone-900" />
            </div>
            <h2 className="font-serif text-3xl mb-6">{content.clientProfile.title}</h2>
            <p className="text-stone-600 leading-relaxed mb-6">{content.clientProfile.description}</p>
            
            <ul className="space-y-3 mb-6">
              {content.clientProfile.items.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600">
                  <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <p className="text-stone-500 text-sm mb-4">
              {locale === 'es' ? 'El perfil se mantiene con ellos:' : 'The profile stays with them:'}
            </p>
            <ul className="space-y-2 mb-6 pl-4">
              {content.clientProfile.persistence.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <p className="text-stone-500 italic text-sm mb-6">{content.clientProfile.detail}</p>
            
            <Button variant="outline" className="rounded-full border-stone-200 hover:bg-stone-50">
              {content.clientProfile.cta}
            </Button>
          </div>
          
          {/* Mock Profile Card */}
          <div className="bg-white rounded-2xl shadow-lg border border-stone-200 p-6">
            <div className="flex items-center gap-4 mb-6 pb-6 border-b border-stone-100">
              <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 font-bold text-xl">SP</div>
              <div>
                <h3 className="font-bold text-xl text-stone-900">Sara Pérez</h3>
                <p className="text-stone-500">{locale === 'es' ? 'Gràcia • €450k-500k' : 'Gràcia • €450k-500k'}</p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-stone-500 text-sm">{locale === 'es' ? 'Ubicación vs Espacio' : 'Location vs Space'}</span>
                <div className="flex gap-1">
                  {[1,2,3,4,5].map(i => (
                    <div key={i} className={`w-4 h-4 rounded ${i <= 4 ? 'bg-stone-900' : 'bg-stone-200'}`}></div>
                  ))}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-stone-500 text-sm">{locale === 'es' ? 'Tolerancia al ruido' : 'Noise Tolerance'}</span>
                <div className="flex gap-1">
                  {[1,2,3,4,5].map(i => (
                    <div key={i} className={`w-4 h-4 rounded ${i <= 1 ? 'bg-stone-900' : 'bg-stone-200'}`}></div>
                  ))}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-stone-500 text-sm">{locale === 'es' ? 'Apetito renovación' : 'Renovation Appetite'}</span>
                <div className="flex gap-1">
                  {[1,2,3,4,5].map(i => (
                    <div key={i} className={`w-4 h-4 rounded ${i <= 3 ? 'bg-stone-900' : 'bg-stone-200'}`}></div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="mt-6 pt-6 border-t border-stone-100">
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 bg-stone-100 rounded-full text-xs text-stone-600">{locale === 'es' ? 'Necesita terraza' : 'Needs terrace'}</span>
                <span className="px-3 py-1 bg-stone-100 rounded-full text-xs text-stone-600">{locale === 'es' ? 'No planta baja' : 'No ground floor'}</span>
                <span className="px-3 py-1 bg-stone-100 rounded-full text-xs text-stone-600">{locale === 'es' ? 'Calle tranquila' : 'Quiet street'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Property Analysis */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Mock Analysis Card */}
          <div className="bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden order-2 md:order-1">
            <div className="h-40 relative">
              <Image
                src={LANDING_IMAGES.interiorApartment}
                alt="Carrer de Verdi, 45"
                fill
                className="object-cover"
                sizes="400px"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
              <div className="absolute top-4 left-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                94% {locale === 'es' ? 'Match' : 'Match'}
              </div>
            </div>
            <div className="p-6">
              <h3 className="font-bold text-lg mb-2">Carrer de Verdi, 45</h3>
              <p className="text-stone-500 text-sm mb-4">
                {locale === 'es' 
                  ? 'Gran match en luz y distribución, más débil en zona' 
                  : 'Great match on light and layout, weaker on area'}
              </p>
              
              <div className="flex flex-wrap gap-2 mb-4">
                <span className="px-3 py-1 bg-green-50 border border-green-200 text-green-700 rounded-full text-xs">
                  {locale === 'es' ? 'Tranquilo' : 'Quiet'}
                </span>
                <span className="px-3 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded-full text-xs">
                  {locale === 'es' ? 'Potencial reforma' : 'Renovation potential'}
                </span>
                <span className="px-3 py-1 bg-stone-50 border border-stone-200 text-stone-600 rounded-full text-xs">
                  {locale === 'es' ? 'Construido 1985' : 'Built 1985'}
                </span>
              </div>
              
              <div className="bg-stone-50 rounded-lg p-3">
                <p className="text-xs text-stone-500 font-medium mb-2">
                  {locale === 'es' ? 'A verificar:' : 'To verify:'}
                </p>
                <ul className="text-xs text-stone-600 space-y-1">
                  <li>• {locale === 'es' ? 'Revisar estado ITE con agente' : 'Check ITE status with agent'}</li>
                  <li>• {locale === 'es' ? 'Confirmar gastos comunidad' : 'Confirm community fees'}</li>
                  <li>• {locale === 'es' ? 'Visitar tarde para evaluar ruido' : 'Visit afternoon for noise check'}</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div className="order-1 md:order-2">
            <div className="w-12 h-12 rounded-2xl bg-stone-100 flex items-center justify-center mb-6">
              <ClipboardList className="w-6 h-6 text-stone-900" />
            </div>
            <h2 className="font-serif text-3xl mb-6">{content.propertyAnalysis.title}</h2>
            <p className="text-stone-600 leading-relaxed mb-6">{content.propertyAnalysis.description}</p>
            
            <ul className="space-y-3 mb-6">
              {content.propertyAnalysis.items.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600">
                  <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <p className="text-stone-500 text-sm mb-4">
              {locale === 'es' ? 'Esto facilita:' : 'This makes it easier to:'}
            </p>
            <ul className="space-y-2 mb-6 pl-4">
              {content.propertyAnalysis.benefits.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            
            <Button className="rounded-full bg-stone-900 text-white hover:bg-stone-800">
              {content.propertyAnalysis.cta}
            </Button>
          </div>
        </div>
      </section>

      {/* Viewing Day */}
      <section className="max-w-4xl mx-auto px-6 mb-32">
        <div className="text-center mb-12">
          <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mx-auto mb-6">
            <Eye className="w-8 h-8 text-stone-900" />
          </div>
          <h2 className="font-serif text-3xl md:text-4xl mb-4">{content.viewingDay.title}</h2>
          <p className="text-stone-600 leading-relaxed max-w-2xl mx-auto">{content.viewingDay.description}</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-stone-50 rounded-2xl p-6 border border-stone-100">
            <h3 className="font-medium text-stone-900 mb-4">
              {locale === 'es' ? 'El cliente ve:' : 'Client sees:'}
            </h3>
            <ul className="space-y-2">
              {content.viewingDay.clientSees.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          
          <div className="bg-stone-900 text-white rounded-2xl p-6">
            <h3 className="font-medium mb-4">
              {locale === 'es' ? 'Tú ves:' : 'You see:'}
            </h3>
            <ul className="space-y-2">
              {content.viewingDay.agentSees.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-stone-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-white mt-2 shrink-0"></span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        
        <p className="text-center text-stone-500 italic mt-8">{content.viewingDay.detail}</p>
      </section>

      {/* Client vs Agent Views Mockup */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="text-center mb-8">
          <h3 className="font-serif text-2xl md:text-3xl text-stone-900 mb-2">
            {locale === 'es' ? 'Dos capas: simple para clientes, contexto completo para ti' : 'Two layers: simple for clients, full context for you'}
          </h3>
          <p className="text-stone-500">
            {locale === 'es' ? 'Controla lo que ven tus clientes — mantén las notas de due diligence privadas' : 'Control what your clients see — keep due diligence notes private'}
          </p>
        </div>
        <div className="flex justify-center">
          <ClientAgentViewComparison />
        </div>
      </section>

      {/* Workspace Visual */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <AgentWorkspaceImage className="w-full" />
        <p className="text-center text-stone-500 italic mt-4 text-sm">
          {locale === 'es' 
            ? 'Trabaja más inteligente, no más duro — Leo se encarga de la investigación' 
            : 'Work smarter, not harder — Leo handles the research'}
        </p>
      </section>

      {/* Renovation Layer */}
      <section className="max-w-4xl mx-auto px-6 mb-32">
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-3xl p-8 md:p-12 border border-amber-100">
          <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center mb-6 shadow-sm">
            <Layers className="w-6 h-6 text-stone-900" />
          </div>
          <h2 className="font-serif text-2xl md:text-3xl mb-4">{content.renovationLayer.title}</h2>
          <p className="text-stone-600 leading-relaxed mb-6">{content.renovationLayer.description}</p>
          
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-white rounded-xl p-4 shadow-sm">
              {content.renovationLayer.paths.map((path, i) => (
                <div key={i} className="flex items-start gap-3 py-2 text-stone-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 shrink-0"></span>
                  <span>{path}</span>
                </div>
              ))}
            </div>
            
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <p className="text-stone-500 text-sm mb-3">
                {locale === 'es' ? 'Con cada esquema, Leo provee:' : 'With each scheme, Leo provides:'}
              </p>
              {content.renovationLayer.leoProvides.map((item, i) => (
                <div key={i} className="flex items-start gap-3 py-1 text-stone-600">
                  <Check className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>
          
          <p className="text-stone-500 text-sm mb-4">
            {locale === 'es' ? 'Tú sigues siendo quien:' : 'You remain the one who:'}
          </p>
          <ul className="space-y-2 pl-4">
            {content.renovationLayer.agentRole.map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
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
