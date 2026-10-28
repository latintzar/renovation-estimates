"use client";

import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SectionBenefitsProps {
  title: string;
  items: string[];
  cta?: string;
  variant?: "light" | "dark";
  className?: string;
}

export const SectionBenefits = ({ 
  title, 
  items, 
  cta, 
  variant = "dark",
  className 
}: SectionBenefitsProps) => {
  const isDark = variant === "dark";
  
  return (
    <section className={cn("max-w-4xl mx-auto px-6 mb-32", className)}>
      <div className={cn(
        "rounded-3xl overflow-hidden shadow-2xl",
        isDark ? "bg-stone-900 text-white" : "bg-white text-stone-900 border border-stone-200"
      )}>
        <div className="p-8 md:p-16">
          <h2 className="font-serif text-3xl md:text-4xl mb-12 text-center">{title}</h2>
          
          <ul className="space-y-6 max-w-2xl mx-auto">
            {items.map((item, i) => (
              <li 
                key={i} 
                className={cn(
                  "flex items-start gap-4 text-lg",
                  isDark ? "text-stone-300" : "text-stone-600"
                )}
              >
                <Check className={cn(
                  "w-6 h-6 shrink-0 mt-0.5",
                  isDark ? "text-white" : "text-green-600"
                )} />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          
          {cta && (
            <div className="text-center mt-12">
              <Button 
                size="lg" 
                className={cn(
                  "rounded-full px-8 py-6 text-lg shadow-lg",
                  isDark 
                    ? "bg-white text-stone-900 hover:bg-stone-100" 
                    : "bg-stone-900 text-white hover:bg-stone-800"
                )}
              >
                {cta}
              </Button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

