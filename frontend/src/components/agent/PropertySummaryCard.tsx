"use client";

import { cn } from "@/lib/utils";
import {
  MapPin,
  Home,
  Ruler,
  Calendar,
  Layers,
  Euro,
  Wrench,
  Sparkles,
} from "lucide-react";
import { MOCK_SCRAPED_PROPERTY } from "@/lib/agent/mock-data";

interface PropertySummaryCardProps {
  property?: typeof MOCK_SCRAPED_PROPERTY;
}

export function PropertySummaryCard({
  property = MOCK_SCRAPED_PROPERTY,
}: PropertySummaryCardProps) {
  const p = property;

  const formatPrice = (price: number) =>
    new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(price);

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      {/* Domain badge */}
      <div className="flex items-center gap-2 px-4 py-2 bg-green-50 border-b border-green-100">
        <div className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-xs font-medium text-green-700">
          {p.sourceDomain}
        </span>
        <span className="text-xs text-green-500 truncate flex-1">{p.sourceUrl}</span>
      </div>

      <div className="p-4 space-y-3">
        {/* Address */}
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-stone-400 mt-0.5 flex-shrink-0" />
          <span className="text-[15px] font-medium text-stone-900">
            {p.address}
          </span>
        </div>

        {/* Key Stats Grid */}
        <div className="grid grid-cols-2 gap-2.5">
          <StatRow icon={Home} label="Type" value={`${p.propertyType} · ${p.bedrooms} bed · ${p.bathrooms} bath`} />
          <StatRow icon={Ruler} label="Size" value={`Built: ${p.sqmBuilt} m² | Useful: ${p.sqmUseful} m²`} />
          <StatRow icon={Calendar} label="Year" value={`${p.yearBuilt}`} />
          <StatRow icon={Layers} label="Floor" value={p.floor} />
          <StatRow icon={Euro} label="Price" value={formatPrice(p.price)} highlight />
          <StatRow icon={Wrench} label="Condition" value={p.condition} />
        </div>

        {/* Features */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {p.features.map((feature) => (
            <span
              key={feature}
              className="text-[11px] px-2 py-0.5 rounded-full bg-stone-100 text-stone-600"
            >
              {feature}
            </span>
          ))}
        </div>

        {/* Photo/Plan counts */}
        <div className="flex items-center gap-4 pt-1 text-xs text-stone-400">
          <span>📸 {p.photoCount} photos</span>
          {p.hasFloorPlan && <span>📐 Floor plan detected</span>}
        </div>
      </div>
    </div>
  );
}

function StatRow({
  icon: Icon,
  label,
  value,
  highlight,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-3.5 h-3.5 text-stone-400 flex-shrink-0" />
      <span className="text-[11px] text-stone-400 w-12 flex-shrink-0">
        {label}
      </span>
      <span
        className={cn(
          "text-xs truncate",
          highlight ? "font-semibold text-stone-900" : "text-stone-700"
        )}
      >
        {value}
      </span>
    </div>
  );
}
