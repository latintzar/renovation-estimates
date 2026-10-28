"use client";

import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  Camera,
  MapPin as MapPinIcon,
  FileText,
  Package,
  Users,
  Wrench,
  AlertTriangle,
} from "lucide-react";

export function CompletionSummary() {
  const items = [
    { icon: Camera, label: "30 photos organized across 8 rooms", done: true },
    { icon: MapPinIcon, label: "Floor plan analyzed — all rooms linked", done: true },
    { icon: FileText, label: "8 documents processed and categorized", done: true },
    { icon: Package, label: "18-item equipment inventory", done: true },
    { icon: Users, label: "3 trusted contacts profiled", done: true },
    { icon: Wrench, label: "Kitchen renovation history (2022)", done: true },
    { icon: AlertTriangle, label: "Known issues logged (humidity, electrical)", done: true },
  ];

  const missing = [
    "Better scan of Cédula de Habitabilidad",
    "Utility contract details (electricity kW)",
    "Building insurance renewal status",
  ];

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-emerald-50 to-teal-50 border-b border-emerald-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-stone-900">
              Property Dossier Complete
            </h3>
            <p className="text-[11px] text-stone-500">
              Calle Mayor 15, 3º Izq, Madrid
            </p>
          </div>
        </div>
      </div>

      {/* Property Quick Info */}
      <div className="px-4 py-3 border-b border-stone-100 bg-stone-50/50">
        <div className="flex items-center gap-6 text-xs text-stone-600">
          <span>🏠 Apartment · 3 bed · 2 bath · 75 m²</span>
          <span>🏗️ 1965 · 3rd floor</span>
          <span className="font-medium">💰 €185,000</span>
        </div>
      </div>

      {/* Completed Items */}
      <div className="p-4 space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-emerald-50 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
              </div>
              <span className="text-sm text-stone-700">{item.label}</span>
            </div>
          );
        })}
      </div>

      {/* Missing Items */}
      <div className="px-4 py-3 bg-amber-50/50 border-t border-amber-100">
        <p className="text-[11px] text-amber-600 font-medium uppercase tracking-wider mb-2">
          Could still use (optional)
        </p>
        {missing.map((item) => (
          <div key={item} className="flex items-center gap-2 py-0.5">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span className="text-xs text-amber-700">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
