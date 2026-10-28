"use client";

import { cn } from "@/lib/utils";
import { 
  IsochroneVisual, 
  MapPinsVisual, 
  ImageRecognitionVisual, 
  InvestigationVisual 
} from "../illustrations/ChecklistVisuals";

interface Category {
  name: string;
  items: string[];
}

interface SectionChecklistProps {
  title: string;
  categories: Category[];
  callout?: string;
  className?: string;
  showVisuals?: boolean;
}

// Map category names (both ES and EN) to their visual components
const visualComponents: Record<string, React.ComponentType<{ className?: string }>> = {
  // English names
  "City & access": IsochroneVisual,
  "Street & building": MapPinsVisual,
  "Look & feel": ImageRecognitionVisual,
  "Age & structure": InvestigationVisual,
  // Spanish names
  "Ciudad y acceso": IsochroneVisual,
  "Calle y edificio": MapPinsVisual,
  "Luz y espacio": ImageRecognitionVisual,
  "Edad y estructura": InvestigationVisual,
  // Additional variations
  "The building and its history": InvestigationVisual,
  "El edificio y su historia": InvestigationVisual,
  "The flat itself": ImageRecognitionVisual,
  "El piso en sí": ImageRecognitionVisual,
  "The surroundings": MapPinsVisual,
  "El entorno": MapPinsVisual,
  "Your plans": IsochroneVisual,
  "Tus planes": IsochroneVisual,
};

export const SectionChecklist = ({ title, categories, callout, className, showVisuals = true }: SectionChecklistProps) => {
  const colors = [
    { bg: "bg-blue-50", border: "border-blue-100", dot: "bg-blue-400" },
    { bg: "bg-amber-50", border: "border-amber-100", dot: "bg-amber-400" },
    { bg: "bg-green-50", border: "border-green-100", dot: "bg-green-400" },
    { bg: "bg-purple-50", border: "border-purple-100", dot: "bg-purple-400" },
  ];

  return (
    <section className={cn("max-w-5xl mx-auto px-6 mb-32", className)}>
      <h2 className="font-serif text-3xl md:text-4xl text-center mb-12">{title}</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        {categories.map((category, index) => {
          const color = colors[index % colors.length];
          const VisualComponent = showVisuals ? visualComponents[category.name] : null;
          
          return (
            <div 
              key={category.name}
              className={cn(
                "rounded-2xl p-6 border",
                color.bg,
                color.border
              )}
            >
              {/* Visual mockup - shown above text on larger screens */}
              {VisualComponent && (
                <div className="flex justify-center mb-5">
                  <VisualComponent />
                </div>
              )}
              
              {/* Text content */}
              <div>
                <h3 className="font-serif text-lg mb-3 text-stone-900">{category.name}</h3>
              <ul className="space-y-2">
                {category.items.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-stone-600 text-sm">
                    <span className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", color.dot)}></span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              </div>
            </div>
          );
        })}
      </div>
      
      {callout && (
        <div className="mt-10 bg-white rounded-2xl p-6 border border-stone-200 shadow-sm text-center">
          <p className="text-stone-600 italic">{callout}</p>
        </div>
      )}
    </section>
  );
};
