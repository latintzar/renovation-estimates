"use client";

import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SectionCTAProps {
  title: string;
  description?: string;
  buttonText: string;
  className?: string;
}

export const SectionCTA = ({ title, description, buttonText, className }: SectionCTAProps) => {
  return (
    <section className={cn("max-w-3xl mx-auto px-6 text-center mb-32", className)}>
      <h2 className="font-serif text-4xl md:text-5xl mb-8">{title}</h2>
      
      {description && (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-stone-100 inline-block mb-10">
          <p className="text-xl text-stone-600 italic">{description}</p>
        </div>
      )}
      
      <div className="block">
        <Button 
          size="lg" 
          className="rounded-full px-10 py-8 text-xl bg-stone-900 text-white hover:bg-stone-800 shadow-xl shadow-stone-900/10"
        >
          {buttonText} <ArrowRight className="ml-2 w-6 h-6" />
        </Button>
      </div>
    </section>
  );
};

