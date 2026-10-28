"use client";

import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SectionTestimonialsProps {
  title: string;
  quotes: string[];
  cta?: string;
  className?: string;
}

export const SectionTestimonials = ({ title, quotes, cta, className }: SectionTestimonialsProps) => {
  return (
    <section id="reviews" className={cn("max-w-5xl mx-auto px-6 mb-32", className)}>
      <h2 className="font-serif text-3xl md:text-4xl text-center mb-12">{title}</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        {quotes.map((quote, i) => (
          <div 
            key={i} 
            className="bg-white p-8 rounded-2xl shadow-sm border border-stone-100 hover:shadow-md transition-shadow"
          >
            <div className="text-amber-400 text-xl mb-4">★★★★★</div>
            <p className="text-stone-700 leading-relaxed">"{quote}"</p>
          </div>
        ))}
      </div>
      
      {cta && (
        <div className="text-center mt-12">
          <Button 
            size="lg" 
            className="rounded-full px-8 py-6 text-lg bg-stone-900 hover:bg-stone-800 text-white shadow-lg shadow-stone-900/10"
          >
            {cta} <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
        </div>
      )}
    </section>
  );
};

