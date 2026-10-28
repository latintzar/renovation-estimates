"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  VignetteLeoAsks, 
  VignettePropertyMatch, 
  VignetteFeedbackLoop 
} from "../illustrations/CompactVignettes";

interface RentersHowItWorksProps {
  className?: string;
}

// Helper component to render bullet points
const BulletList = ({ items, className }: { items?: string[]; className?: string }) => {
  if (!items || items.length === 0) return null;
  return (
    <ul className={cn("list-disc list-inside text-stone-600 space-y-1 ml-1", className)}>
      {items.map((item, idx) => (
        <li key={idx} className="text-sm">{item}</li>
      ))}
    </ul>
  );
};

export const RentersHowItWorks = ({ className }: RentersHowItWorksProps) => {
  const { dictionary: t } = useDictionary();
  const content = t.renters.howItWorks;
  
  return (
    <section id="how-it-works" className={cn("max-w-5xl mx-auto px-6 mb-32", className)}>
      <h2 className="font-serif text-3xl md:text-4xl text-center mb-16">
        {content.title}
      </h2>
      
      <div className="space-y-20">
        {/* Step 1 - Leo asks, vignette on right */}
        <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12">
          <div className="flex-1 order-2 md:order-1">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-full bg-stone-900 text-white flex items-center justify-center font-serif text-lg shrink-0">
                1
              </div>
              <div>
                <h3 className="font-serif text-xl md:text-2xl mb-2">{content.steps[0].title}</h3>
                <p className="text-stone-600 leading-relaxed mb-1">{content.steps[0].description}</p>
                <BulletList items={content.steps[0].bullets} className="mb-3" />
                <p className="text-stone-500 italic text-sm">{content.steps[0].detail}</p>
              </div>
            </div>
          </div>
          <div className="order-1 md:order-2 shrink-0">
            <VignetteLeoAsks />
          </div>
        </div>
        
        {/* Step 2 - Property match, vignette on left */}
        <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12">
          <div className="shrink-0">
            <VignettePropertyMatch />
          </div>
          <div className="flex-1">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-full bg-stone-900 text-white flex items-center justify-center font-serif text-lg shrink-0">
                2
              </div>
              <div>
                <h3 className="font-serif text-xl md:text-2xl mb-2">{content.steps[1].title}</h3>
                <p className="text-stone-600 leading-relaxed mb-1">{content.steps[1].description}</p>
                <p className="text-stone-600 leading-relaxed mb-1">{content.steps[1].detail}</p>
                <BulletList items={content.steps[1].bullets} className="mb-3" />
              </div>
            </div>
          </div>
        </div>
        
        {/* Step 3 - Feedback loop, vignette on right */}
        <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12">
          <div className="flex-1 order-2 md:order-1">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-full bg-stone-900 text-white flex items-center justify-center font-serif text-lg shrink-0">
                3
              </div>
              <div>
                <h3 className="font-serif text-xl md:text-2xl mb-2">{content.steps[2].title}</h3>
                <p className="text-stone-600 leading-relaxed mb-1">{content.steps[2].description}</p>
                <BulletList items={content.steps[2].bullets} className="mb-3" />
                <p className="text-stone-500 italic text-sm">{content.steps[2].detail}</p>
              </div>
            </div>
          </div>
          <div className="order-1 md:order-2 shrink-0">
            <VignetteFeedbackLoop />
          </div>
        </div>
      </div>
    </section>
  );
};

export default RentersHowItWorks;
