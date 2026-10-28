"use client";

import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SectionFeatureCardProps {
  title: string;
  description: string;
  items: string[];
  detail?: string;
  cta?: string;
  className?: string;
}

export const SectionFeatureCard = ({ 
  title, 
  description, 
  items, 
  detail,
  cta,
  className 
}: SectionFeatureCardProps) => {
  return (
    <section className={cn("max-w-4xl mx-auto px-6 mb-24", className)}>
      <div className="bg-white rounded-3xl p-8 md:p-12 shadow-sm border border-stone-100">
        <h2 className="font-serif text-2xl md:text-3xl mb-4">{title}</h2>
        <p className="text-stone-600 leading-relaxed mb-6">{description}</p>
        
        <ul className="space-y-3 mb-6">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-3 text-stone-600">
              <Check className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
              <span dangerouslySetInnerHTML={{ 
                __html: item.replace(/\*\*(.*?)\*\*/g, '<strong class="text-stone-900">$1</strong>') 
              }} />
            </li>
          ))}
        </ul>
        
        {detail && (
          <p className="text-stone-500 text-sm italic mb-6">{detail}</p>
        )}
        
        {cta && (
          <Button 
            variant="outline"
            className="rounded-full border-stone-200 hover:bg-stone-50"
          >
            {cta}
          </Button>
        )}
      </div>
    </section>
  );
};

