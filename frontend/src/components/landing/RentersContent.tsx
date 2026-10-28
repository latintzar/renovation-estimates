"use client";

import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  SectionHero, 
  SectionChecklist, 
  SectionBenefits,
  SectionCTA,
  RentersHowItWorks
} from "./sections";
import { 
  ListingVsRealityMockup, 
  LifeStagesTimeline,
} from "./illustrations";

interface RentersContentProps {
  onProLinkClick: () => void;
}

export const RentersContent = ({ onProLinkClick }: RentersContentProps) => {
  const { dictionary: t } = useDictionary();
  const content = t.renters;
  
  return (
    <div className="animate-in fade-in duration-500">
      {/* Hero with Isochrone Map */}
      <SectionHero
        eyebrow={content.hero.eyebrow}
        headline={content.hero.headline}
        subcopy={content.hero.subcopy}
        primaryCta={content.hero.primaryCta}
        secondaryCta={content.hero.secondaryCta}
        proLink={t.shared.proLink}
        onProLinkClick={onProLinkClick}
        showWaveform={false}
        showIsochrone={true}
      />

      {/* How It Works - with integrated compact vignettes */}
      <RentersHowItWorks />

      {/* What Leo Checks */}
      <SectionChecklist
        title={content.whatLeoChecks.title}
        categories={content.whatLeoChecks.categories}
        callout={content.whatLeoChecks.callout}
      />

      {/* Viewing Day - Listing vs Reality */}
      <section className="max-w-4xl mx-auto px-6 mb-32">
        <div className="text-center mb-12">
          <h2 className="font-serif text-3xl md:text-4xl mb-4">{content.viewingDay.title}</h2>
          <p className="text-stone-600 leading-relaxed max-w-2xl mx-auto">
            {content.viewingDay.description}
          </p>
        </div>
        
        {/* The "gotcha" mockup - beautiful listing vs reality */}
        <ListingVsRealityMockup />
        
        <p className="text-center text-stone-500 italic mt-8 text-sm">
          {content.viewingDay.detail}
        </p>
      </section>

      {/* Moving Profile - Visual-driven section */}
      <section className="max-w-5xl mx-auto px-6 mb-32">
        <div className="bg-stone-900 text-white rounded-3xl p-8 md:p-12 shadow-2xl">
          {/* Simple headline */}
          <h2 className="font-serif text-3xl md:text-4xl mb-3 text-center">
            {content.movingProfile.title}
          </h2>
          <p className="text-stone-400 text-center mb-10 max-w-xl mx-auto">
            {content.movingProfile.callout}
          </p>
          
          {/* Life stages - images tell the story */}
          <LifeStagesTimeline />
        </div>
      </section>

      {/* Who This Is For */}
      <SectionBenefits
        title={content.whoThisIsFor.title}
        items={content.whoThisIsFor.items}
        variant="light"
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
