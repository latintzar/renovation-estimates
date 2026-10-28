"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";

interface Step {
  number: number;
  title: string;
  description: string;
  detail?: string;
  bullets?: string[];
  secondBullets?: string[];
  leoCaptures?: string[];
  extensionFeatures?: string[];
  leoActions?: string[];
  briefCaptures?: string[];
  sources?: string[];
  assigneeActions?: string[];
}

interface SectionHowItWorksProps {
  title: string;
  steps: Step[];
  className?: string;
}

export const SectionHowItWorks = ({ title, steps, className }: SectionHowItWorksProps) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <section id="how-it-works" className={cn("max-w-4xl mx-auto px-6 mb-32", className)}>
      <h2 className="font-serif text-3xl md:text-4xl text-center mb-16">{title}</h2>
      
      <div className="space-y-16">
        {steps.map((step, index) => (
          <div 
            key={step.number} 
            className={cn(
              "relative pl-16 md:pl-20",
              index !== steps.length - 1 && "pb-16 border-l-2 border-stone-100 ml-6"
            )}
          >
            {/* Step Number */}
            <div className="absolute left-0 -translate-x-1/2 w-12 h-12 rounded-full bg-stone-900 text-white flex items-center justify-center font-serif text-xl">
              {step.number}
            </div>
            
            {/* Content */}
            <div className="pt-1">
              <h3 className="font-serif text-2xl mb-4">{step.title}</h3>
              <p className="text-stone-600 leading-relaxed mb-4">{step.description}</p>
              
              {/* Various bullet point types */}
              {step.bullets && step.bullets.length > 0 && (
                <ul className="space-y-2 mb-4">
                  {step.bullets.map((bullet, i) => (
                    <li key={i} className="flex items-start gap-3 text-stone-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                      <span dangerouslySetInnerHTML={{ __html: bullet.replace(/\*\*(.*?)\*\*/g, '<strong class="text-stone-900">$1</strong>') }} />
                    </li>
                  ))}
                </ul>
              )}
              
              {step.leoCaptures && step.leoCaptures.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-stone-500 mb-2">
                    {isEs ? 'Leo captura:' : 'Leo captures:'}
                  </p>
                  <ul className="space-y-2">
                    {step.leoCaptures.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-stone-600">
                        <Check className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {step.extensionFeatures && step.extensionFeatures.length > 0 && (
                <div className="mb-4 bg-stone-50 rounded-xl p-4 border border-stone-100">
                  <p className="text-sm font-medium text-stone-700 mb-3">
                    {isEs ? 'Con la extensión Enviar a Leo, puedes:' : 'With the Send to Leo extension, you:'}
                  </p>
                  <ul className="space-y-2">
                    {step.extensionFeatures.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                        <span dangerouslySetInnerHTML={{ __html: item.replace(/\*\*(.*?)\*\*/g, '<strong class="text-stone-900">$1</strong>') }} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {step.leoActions && step.leoActions.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-stone-500 mb-2">
                    {isEs ? 'Leo entonces:' : 'Leo then:'}
                  </p>
                  <ul className="space-y-2">
                    {step.leoActions.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-stone-600">
                        <Check className="w-4 h-4 text-stone-400 mt-0.5 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {step.briefCaptures && step.briefCaptures.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-stone-500 mb-2">
                    {isEs ? 'Obtienes un brief estructurado que captura:' : 'You get a structured brief that captures:'}
                  </p>
                  <ul className="space-y-2">
                    {step.briefCaptures.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-stone-600">
                        <Check className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {step.sources && step.sources.length > 0 && (
                <ul className="space-y-2 mb-4 pl-4">
                  {step.sources.map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-stone-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
              
              {step.secondBullets && step.secondBullets.length > 0 && (
                <ul className="space-y-2 mb-4 ml-4 border-l-2 border-stone-100 pl-4">
                  {step.secondBullets.map((bullet, i) => (
                    <li key={i} className="flex items-start gap-3 text-stone-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-2 shrink-0"></span>
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              )}
              
              {step.assigneeActions && step.assigneeActions.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-stone-500 mb-2">They can:</p>
                  <ul className="space-y-2">
                    {step.assigneeActions.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-stone-600">
                        <span className="w-1.5 h-1.5 rounded-full bg-stone-400 mt-2 shrink-0"></span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {step.detail && (
                <p className="text-stone-500 italic text-sm">{step.detail}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

