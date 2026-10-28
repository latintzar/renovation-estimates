"use client";

/**
 * PlaceCard Component
 * ===================
 * 
 * Beautiful card displaying a curated place with:
 * - Name and category
 * - Rating with stars
 * - Opening hours badge
 * - "Open Late" indicator for nightlife
 * - Walk time from property
 * 
 * Design: Glass morphism with brand accents
 */

import { useState } from "react";
import {
  Star,
  Clock,
  MapPin,
  Moon,
  Coffee,
  ShoppingCart,
  Train,
  Bus,
  Wine,
  Cross,
  TreePine,
  Landmark,
  X,
  ChevronDown,
  ChevronUp,
  Navigation,
} from "lucide-react";

// =============================================================================
// TYPES
// =============================================================================

interface PlaceCardProps {
  name: string;
  category: string;
  distance_m: number;
  walk_mins?: number;
  rating?: number | null;
  rating_count?: number | null;
  is_open_now?: boolean | null;
  is_open_late?: boolean;
  weekday_hours?: string[] | null;
  category_purpose?: string;
  onClose?: () => void;
  compact?: boolean;
}

// =============================================================================
// HELPERS
// =============================================================================

const getCategoryIcon = (category: string, purpose?: string) => {
  const lower = category.toLowerCase();
  const purposeLower = purpose?.toLowerCase() || "";
  
  if (purposeLower.includes("grocery") || lower.includes("supermarket") || lower.includes("grocery")) {
    return <ShoppingCart className="w-4 h-4" />;
  }
  if (purposeLower.includes("metro") || lower.includes("metro") || lower.includes("train")) {
    return <Train className="w-4 h-4" />;
  }
  if (purposeLower.includes("bus") || lower.includes("bus") || lower.includes("tram")) {
    return <Bus className="w-4 h-4" />;
  }
  if (purposeLower.includes("late_night") || lower.includes("bar") || lower.includes("club") || lower.includes("pub")) {
    return <Wine className="w-4 h-4" />;
  }
  if (purposeLower.includes("street") || lower.includes("restaurant") || lower.includes("cafe") || lower.includes("coffee")) {
    return <Coffee className="w-4 h-4" />;
  }
  if (purposeLower.includes("hospital") || lower.includes("hospital") || lower.includes("medical")) {
    return <Cross className="w-4 h-4" />;
  }
  if (purposeLower.includes("nature") || lower.includes("park") || lower.includes("beach") || lower.includes("forest")) {
    return <TreePine className="w-4 h-4" />;
  }
  if (purposeLower.includes("special") || lower.includes("museum") || lower.includes("landmark") || lower.includes("gallery")) {
    return <Landmark className="w-4 h-4" />;
  }
  
  return <MapPin className="w-4 h-4" />;
};

const getCategoryColor = (category: string, purpose?: string) => {
  const lower = category.toLowerCase();
  const purposeLower = purpose?.toLowerCase() || "";
  
  if (purposeLower.includes("grocery") || lower.includes("supermarket")) return "from-emerald-500 to-green-600";
  if (purposeLower.includes("metro") || lower.includes("metro")) return "from-blue-500 to-indigo-600";
  if (purposeLower.includes("bus") || lower.includes("bus")) return "from-orange-400 to-amber-500";
  if (purposeLower.includes("late_night") || lower.includes("bar")) return "from-purple-500 to-violet-600";
  if (purposeLower.includes("street") || lower.includes("cafe")) return "from-amber-500 to-orange-500";
  if (purposeLower.includes("hospital") || lower.includes("hospital")) return "from-red-500 to-rose-600";
  if (purposeLower.includes("nature") || lower.includes("park")) return "from-green-500 to-emerald-600";
  if (purposeLower.includes("special") || lower.includes("museum")) return "from-pink-500 to-rose-500";
  
  return "from-gray-500 to-slate-600";
};

const formatDistance = (meters: number): string => {
  if (meters < 1000) return `${meters}m`;
  return `${(meters / 1000).toFixed(1)}km`;
};

const RatingStars = ({ rating }: { rating: number }) => {
  const fullStars = Math.floor(rating);
  const hasHalf = rating % 1 >= 0.5;
  
  return (
    <div className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className={`w-3 h-3 ${
            i < fullStars
              ? "text-yellow-400 fill-yellow-400"
              : i === fullStars && hasHalf
              ? "text-yellow-400 fill-yellow-400/50"
              : "text-gray-400"
          }`}
        />
      ))}
      <span className="ml-1 text-xs font-medium text-white/90">{rating.toFixed(1)}</span>
    </div>
  );
};

// =============================================================================
// COMPONENT
// =============================================================================

export default function PlaceCard({
  name,
  category,
  distance_m,
  walk_mins,
  rating,
  rating_count,
  is_open_now,
  is_open_late,
  weekday_hours,
  category_purpose,
  onClose,
  compact = false,
}: PlaceCardProps) {
  const [showHours, setShowHours] = useState(false);
  
  const colorGradient = getCategoryColor(category, category_purpose);
  const icon = getCategoryIcon(category, category_purpose);
  
  if (compact) {
    return (
      <div className="bg-gray-900/95 backdrop-blur-md rounded-xl border border-white/10 p-3 shadow-xl min-w-[200px]">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg bg-gradient-to-br ${colorGradient}`}>
              {icon}
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm truncate max-w-[140px]">{name}</h3>
              <p className="text-xs text-white/60">{category}</p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-white/40 hover:text-white/80 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/10">
          <div className="flex items-center gap-1 text-white/60">
            <Navigation className="w-3 h-3" />
            <span className="text-xs">{formatDistance(distance_m)}</span>
            {walk_mins && <span className="text-xs">• {walk_mins} min walk</span>}
          </div>
          {rating && <RatingStars rating={rating} />}
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-gray-900/95 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden shadow-2xl min-w-[280px] max-w-[320px]">
      {/* Header with gradient */}
      <div className={`bg-gradient-to-r ${colorGradient} p-4`}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
              {icon}
            </div>
            <div>
              <h3 className="font-bold text-white text-lg leading-tight">{name}</h3>
              <p className="text-sm text-white/80">{category}</p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Rating */}
        {rating && (
          <div className="flex items-center justify-between">
            <RatingStars rating={rating} />
            {rating_count && (
              <span className="text-xs text-white/50">({rating_count.toLocaleString()} reviews)</span>
            )}
          </div>
        )}
        
        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          {/* Open Now badge */}
          {is_open_now !== null && is_open_now !== undefined && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                is_open_now
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-red-500/20 text-red-400 border border-red-500/30"
              }`}
            >
              <Clock className="w-3 h-3" />
              {is_open_now ? "Open Now" : "Closed"}
            </span>
          )}
          
          {/* Open Late badge */}
          {is_open_late && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30">
              <Moon className="w-3 h-3" />
              Open Late
            </span>
          )}
        </div>
        
        {/* Distance and walk time */}
        <div className="flex items-center gap-4 text-white/70">
          <div className="flex items-center gap-1">
            <Navigation className="w-4 h-4" />
            <span className="text-sm font-medium">{formatDistance(distance_m)}</span>
          </div>
          {walk_mins && (
            <div className="flex items-center gap-1">
              <span className="text-sm">{walk_mins} min walk</span>
            </div>
          )}
        </div>
        
        {/* Opening hours (expandable) */}
        {weekday_hours && weekday_hours.length > 0 && (
          <div className="pt-2 border-t border-white/10">
            <button
              onClick={() => setShowHours(!showHours)}
              className="flex items-center justify-between w-full text-white/60 hover:text-white/80 transition-colors"
            >
              <span className="text-xs font-medium flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Hours
              </span>
              {showHours ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
            
            {showHours && (
              <div className="mt-2 space-y-1">
                {weekday_hours.map((hours, i) => (
                  <p key={i} className="text-xs text-white/50">
                    {hours}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// EXPORT COMPACT VERSION
// =============================================================================

export function PlaceCardCompact(props: PlaceCardProps) {
  return <PlaceCard {...props} compact />;
}

