"use client";

import { cn } from "@/lib/utils";

interface SectionCalloutProps {
  content: string;
  variant?: "default" | "highlight";
  className?: string;
}

export const SectionCallout = ({ 
  content, 
  variant = "default",
  className 
}: SectionCalloutProps) => {
  return (
    <section className={cn("max-w-3xl mx-auto px-6 mb-24", className)}>
      <div className={cn(
        "rounded-2xl p-6 md:p-8 text-center",
        variant === "highlight" 
          ? "bg-stone-900 text-white" 
          : "bg-stone-50 border border-stone-100"
      )}>
        <p className={cn(
          "text-lg md:text-xl leading-relaxed italic",
          variant === "highlight" ? "text-stone-200" : "text-stone-600"
        )}>
          {content}
        </p>
      </div>
    </section>
  );
};

