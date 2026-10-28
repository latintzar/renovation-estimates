'use client';

import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  X,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileText,
  Home,
  ArrowDown,
  Shield,
} from 'lucide-react';
import BeforeAfterSlider from './BeforeAfterSlider';
import { OfficialBudgetReport } from './OfficialBudgetReport';
import { NegotiationModal } from './NegotiationModal';
import { useAppStrings } from '@/hooks/AppStringsContext';

// =============================================================================
// TYPES
// =============================================================================

interface EnergyCompliance {
  current_rating?: string;
  target_rating?: string;
  improvement_letters?: number;
  measures?: string[];
}

interface ComparableFeatures {
  floor?: string;
  view?: string;
  views?: string[];
  direction?: string;
  directions?: string[];
  orientation?: string;
  characteristics?: string[];
  elevator?: boolean;
  balcony?: boolean;
  terrace?: boolean;
  parking?: boolean;
  pool?: boolean;
  storage?: boolean;
  air_conditioning?: boolean;
  heating?: string;
}

interface Comparable {
  id: number;
  casafari_property_id: number;
  sale_price: number;
  price_per_sqm: number;
  total_area: number | null;
  living_area: number | null;
  plot_area: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  condition: string | null;
  distance_km: number;
  address: string | null;
  property_url: string;
  photo_urls: string[];
  // Additional characteristics
  energy_rating?: string | null;
  construction_year?: number | null;
  features?: ComparableFeatures;
  comp_role?: 'reference' | 'above' | 'below';
}

interface Pricing {
  pem?: number;
  overhead_13pct?: number;
  profit_6pct?: number;
  iva_21pct?: number;
  total_with_iva?: number;
}

// ELI5 Summary — the buyer-friendly room breakdown
interface ELI5Package {
  name: string;
  cost: number;
}

interface ELI5Room {
  room_id: string;
  room_name: string;
  estimated_m2?: number;     // Smart M² estimated floor area
  tagline: string;           // "Modern galley with quartz island"
  key_changes: string[];     // ["🪵 Oak flooring", "💡 Recessed lighting"]
  cost: number;
  weeks?: string;
  packages?: ELI5Package[];  // Grouped buyer-friendly packages from LLM
}

interface ELI5Summary {
  concept: {
    vision_statement?: string;
    intro_before?: string;
    intro_after?: string;
    design_style: string;
    key_upgrades: string[];
    value_story: string;
  };
  property_summary: {
    address: string;
    total_cost: number;
    total_weeks: number;
  };
  rooms: ELI5Room[];
  general_items?: {
    tagline: string;
    key_items: string[];
    cost: number;
  };
  timeline: {
    total_weeks: number;
    summary: string;
  };
}

interface RenovationAnalysis {
  bracket: 'fair_market';
  target_price: number;
  asking_price: number;
  gap: number;
  renovation_cost: number;
  pem_subtotal: number;
  line_items_count: number;
  scope_of_work: {
    total_items: number;
    categories: any[];
    pricing?: Pricing;
  };
  total_investment: number;
  potential_margin: number;
  estimated_weeks_min: number;
  estimated_weeks_max: number;
  before_image: string | null;
  after_image: string | null;
  comparables: Comparable[];
  energy_compliance?: EnergyCompliance;
  cost_breakdown?: Record<string, number>;
  line_items?: Array<{
    item_id: string;
    room_id?: string;
    room_name?: string;
    description: string;
    quantity: number;
    unit: string;
    unit_price: number;
    line_total: number;
    bcca_code?: string;
  }>;
  room_images?: Array<{
    room_id: string;
    room_name: string;
    before_image: string;
    after_image: string;
    key_changes: string[];
    is_hero: boolean;
  }>;
  eli5_summary?: ELI5Summary;
  reference_comparable_id?: number;
  reference_sold_price?: number;
}

interface BracketAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: RenovationAnalysis;
  listingId: number;
  address?: string;
  hideEli5Numbers?: boolean;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
};

// Single strategy: always "Valor de mercado"

// =============================================================================
// SHARE POPUP
// =============================================================================

interface SharePopupProps {
  isOpen: boolean;
  onClose: () => void;
  onShareLink: () => void;
  onArchitectView: () => void;
  onOfficialBudget: () => void;
}

const SharePopup: React.FC<SharePopupProps> = ({
  isOpen,
  onClose,
  onShareLink,
  onArchitectView,
  onOfficialBudget,
}) => {
  const { s } = useAppStrings();
  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-12 w-64 bg-white rounded-lg shadow-lg border z-50">
      <div className="p-2">
        <button
          onClick={onShareLink}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
        >
          <Copy className="w-4 h-4" />
          {s.copyLink}
        </button>
        <button
          onClick={onArchitectView}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
        >
          <FileText className="w-4 h-4" />
          {s.techReport}
        </button>
        <button
          onClick={onOfficialBudget}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded border-t border-gray-100 mt-1 pt-2"
        >
          <FileText className="w-4 h-4 text-blue-600" />
          <div className="text-left">
            <span className="font-medium text-blue-600">{s.officialBudget}</span>
            <p className="text-xs text-gray-400">{s.ecoFormat}</p>
          </div>
        </button>
      </div>
      <button
        onClick={onClose}
        className="w-full px-3 py-2 text-sm text-gray-500 border-t hover:bg-gray-50"
      >
        {s.cancel}
      </button>
    </div>
  );
};

// =============================================================================
// ROOM IMAGES CAROUSEL
// =============================================================================

interface RoomImage {
  room_id: string;
  room_name: string;
  before_image: string;
  after_image: string;
  key_changes: string[];
  is_hero: boolean;
}

const RoomImagesCarousel: React.FC<{
  roomImages: RoomImage[];
  fallbackBefore: string | null;
  fallbackAfter: string | null;
  bracketLabel: string;
}> = ({ roomImages, fallbackBefore, fallbackAfter, bracketLabel }) => {
  const { s, translateText, isSourceLanguage } = useAppStrings();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [translatedRoomNames, setTranslatedRoomNames] = useState<Record<string, string>>({});
  
  // Use room_images if available, otherwise fall back to single hero image
  const images = roomImages.length > 0 
    ? roomImages 
    : fallbackBefore && fallbackAfter 
      ? [{ room_id: 'hero', room_name: s.mainRoom, before_image: fallbackBefore, after_image: fallbackAfter, key_changes: [], is_hero: true }]
      : [];
  
  // Translate room names when language changes
  useEffect(() => {
    if (isSourceLanguage || images.length === 0) { setTranslatedRoomNames({}); return; }
    const doIt = async () => {
      const map: Record<string, string> = {};
      for (const img of images) {
        if (img.room_name) map[img.room_name] = await translateText(img.room_name);
      }
      setTranslatedRoomNames(map);
    };
    doIt();
  }, [images.length, isSourceLanguage, translateText]);

  if (images.length === 0) return null;
  
  const current = images[currentIndex];
  const displayRoomName = translatedRoomNames[current.room_name] || current.room_name;
  
  const goNext = () => setCurrentIndex((i) => (i + 1) % images.length);
  const goPrev = () => setCurrentIndex((i) => (i - 1 + images.length) % images.length);
  
  return (
    <div className="mb-2">
      {/* Before/After Slider with navigation overlay */}
      <div className="relative isolate h-[400px] rounded-2xl overflow-hidden">
        <BeforeAfterSlider
          beforeImage={current.before_image}
          afterImage={current.after_image}
          beforeLabel={s.beforeUpper}
          afterLabel={s.afterUpper}
          className="h-full w-full"
          hideSlideHint={images.length > 1}
        />
        
        {/* Room name overlay at top center */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30">
          <div className="bg-black/60 backdrop-blur-sm text-white px-4 py-2 rounded-full text-center">
            <span className="font-medium">{displayRoomName}</span>
          </div>
        </div>
        
        {/* Navigation buttons - only show if multiple rooms */}
        {images.length > 1 && (
          <>
            <button
              onClick={goPrev}
              className="absolute left-3 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-black/40 backdrop-blur-sm text-white flex items-center justify-center hover:bg-black/60 transition-colors"
              aria-label={s.prevRoom}
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
            <button
              onClick={goNext}
              className="absolute right-3 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-black/40 backdrop-blur-sm text-white flex items-center justify-center hover:bg-black/60 transition-colors"
              aria-label={s.nextRoom}
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          </>
        )}
        
        {/* Desliza hint + dot indicators — stacked at bottom */}
        {images.length > 1 && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center gap-1.5">
            <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] px-2.5 py-0.5 rounded-full animate-pulse">
              {s.slideHint}
            </span>
            <div className="flex gap-2">
              {images.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentIndex(idx)}
                  className={`w-2 h-2 rounded-full transition-all ${
                    idx === currentIndex
                      ? 'bg-white w-6'
                      : 'bg-white/50 hover:bg-white/70'
                  }`}
                  aria-label={`${s.goToRoom} ${idx + 1}`}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// HERO METRICS SECTION - Matches Landing Page Style
// =============================================================================

// Format as compact (e.g., €45k)
const formatCompact = (value: number): string => {
  const absValue = Math.abs(value);
  if (absValue >= 1000000) {
    return `€${(value / 1000000).toFixed(1)}M`;
  } else if (absValue >= 1000) {
    return `€${Math.round(value / 1000)}k`;
  }
  return `€${Math.round(value)}`;
};

// Keep only the energy letter (A-G), even if backend sends text like "G (estimado)".
const normalizeEnergyRating = (rating?: string | null): string | null => {
  if (!rating) return null;
  const m = String(rating).toUpperCase().match(/[A-G]/);
  return m ? m[0] : null;
};

// Get energy rating color
const getEnergyColor = (rating: string): string => {
  const colors: Record<string, string> = {
    'A': 'bg-green-600', 'B': 'bg-green-500', 'C': 'bg-lime-500',
    'D': 'bg-yellow-500', 'E': 'bg-orange-500', 'F': 'bg-orange-600', 'G': 'bg-red-500'
  };
  return colors[rating.toUpperCase()] || 'bg-stone-400';
};

const HeroMetricsSection: React.FC<{
  renovationCost: number;
  valueIncrease: number;
  totalWeeks: string;
  currentEnergy?: string;
  targetEnergy?: string;
  hideValueAndTime?: boolean;
}> = ({ renovationCost, valueIncrease, totalWeeks, currentEnergy, targetEnergy, hideValueAndTime }) => {
  const { s } = useAppStrings();
  const netProfit = valueIncrease - renovationCost;
  const isNetPositive = netProfit >= 0;
  const currentEnergyLetter = normalizeEnergyRating(currentEnergy);
  const targetEnergyLetter = normalizeEnergyRating(targetEnergy);

  return (
    <div className="space-y-3 mb-6">
      {hideValueAndTime ? (
        /* Contractor view: show only renovation cost, clean and centered */
        <div className="py-5 bg-white rounded-xl border border-stone-100 shadow-sm text-center">
          <p className="text-3xl font-bold text-stone-800">{formatCompact(renovationCost)}</p>
          <p className="text-xs text-stone-400 mt-1">{s.investment}</p>
        </div>
      ) : (
        /* Full buyer view: Investment → Value */
        <div className="flex items-center justify-center gap-6 py-4 bg-white rounded-xl border border-stone-100 shadow-sm">
          <div className="text-center">
            <p className="text-2xl font-bold text-stone-800">{formatCompact(renovationCost)}</p>
            <p className="text-xs text-stone-400">{s.investment}</p>
          </div>
          <ArrowRight className="w-5 h-5 text-amber-500" />
          <div className="text-center">
            <p className={`text-2xl font-bold ${isNetPositive ? 'text-emerald-500' : 'text-red-500'}`}>
              {valueIncrease >= 0 ? '+' : ''}{formatCompact(valueIncrease)}
            </p>
            <p className="text-xs text-stone-400">{s.valueAdded}</p>
            {!isNetPositive && (
              <p className="text-[10px] font-medium text-red-400 mt-1">
                neto -{formatCompact(Math.abs(netProfit))}
              </p>
            )}
          </div>
        </div>
      )}
      
      {/* Time — hidden in contractor view */}
      {!hideValueAndTime && (
        <div className="flex items-center justify-between py-3 px-4 bg-white rounded-xl border border-stone-100 shadow-sm">
          <p className="text-sm text-stone-600">{s.workDuration}</p>
          <p className="text-lg font-bold text-stone-800">{totalWeeks}</p>
        </div>
      )}
      
      {/* Energy */}
      {currentEnergyLetter && targetEnergyLetter && (
        <div className="flex items-center justify-between py-3 px-4 bg-white rounded-xl border border-stone-100 shadow-sm">
          <p className="text-sm text-stone-600">{s.energyCert}</p>
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-md ${getEnergyColor(currentEnergyLetter)} flex items-center justify-center`}>
              <span className="text-white text-xs font-bold">{currentEnergyLetter}</span>
            </div>
            <ArrowRight className="w-4 h-4 text-stone-400" />
            <div className={`w-7 h-7 rounded-md ${getEnergyColor(targetEnergyLetter)} flex items-center justify-center`}>
              <span className="text-white text-xs font-bold">{targetEnergyLetter}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


// =============================================================================
// ELI5 ROOM TABLE - Layman-friendly room breakdown with costs & time per item
// =============================================================================

// Helper to format labor hours to readable time
const formatTime = (hours: number): string => {
  if (hours < 1) return `${Math.round(hours * 60)}min`;
  if (hours < 8) return `${hours.toFixed(1)}h`;
  const days = hours / 8;
  if (days < 5) return `${days.toFixed(1)} días`;
  const weeks = days / 5;
  return `${weeks.toFixed(1)} sem`;
};

// Simplify technical BOQ descriptions to layman terms
const simplifyDescription = (desc: string): string => {
  // Common simplifications
  const simplifications: [RegExp, string][] = [
    [/demolici[oó]n.*suelo/i, 'Quitar suelo antiguo'],
    [/demolici[oó]n.*alicatado/i, 'Quitar azulejos'],
    [/aplicaci[oó]n.*pintura|pintura.*pl[aá]stica/i, 'Pintar paredes'],
    [/solado.*cer[aá]mico|baldosa/i, 'Suelo nuevo'],
    [/alicatado/i, 'Azulejos nuevos'],
    [/instalaci[oó]n.*el[eé]ctrica/i, 'Instalación eléctrica'],
    [/punto.*luz/i, 'Puntos de luz'],
    [/mecanismo.*el[eé]ctrico/i, 'Enchufes/interruptores'],
    [/radiador/i, 'Radiador nuevo'],
    [/sanitario|inodoro/i, 'Sanitarios'],
    [/grifo|griferí/i, 'Grifería nueva'],
    [/carpinter[ií]a.*interior/i, 'Puertas interiores'],
    [/ventana/i, 'Ventanas'],
    [/armario.*empotrado/i, 'Armario empotrado'],
    [/encimera/i, 'Encimera nueva'],
    [/mueble.*cocina/i, 'Muebles de cocina'],
    [/tarima|parquet/i, 'Suelo de madera'],
  ];
  
  for (const [pattern, simple] of simplifications) {
    if (pattern.test(desc)) return simple;
  }
  
  // Truncate long descriptions
  if (desc.length > 40) {
    return desc.substring(0, 37) + '...';
  }
  return desc;
};

const ELI5RoomTable: React.FC<{ eli5: ELI5Summary; hideNumbers?: boolean }> = ({ eli5, hideNumbers }) => {
  const { s, translateText, isSourceLanguage } = useAppStrings();
  const eurFmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
  // Translate dynamic ELI5 content (intro_before, intro_after, room names, taglines)
  const [tr, setTr] = useState<Record<string, string>>({});
  useEffect(() => {
    if (isSourceLanguage) { setTr({}); return; }
    const texts: string[] = [];
    if (eli5.concept.intro_before) texts.push(eli5.concept.intro_before);
    if (eli5.concept.intro_after) texts.push(eli5.concept.intro_after);
    if (eli5.timeline?.summary) texts.push(eli5.timeline.summary);
    for (const r of eli5.rooms) {
      if (r.room_name) texts.push(r.room_name);
      if (r.tagline) texts.push(r.tagline);
      for (const kc of r.key_changes || []) { if (kc) texts.push(kc); }
      for (const pkg of (r as any).packages || []) { if (pkg?.name) texts.push(pkg.name); }
    }
    if (eli5.general_items?.key_items) {
      for (const ki of eli5.general_items.key_items) { if (ki) texts.push(ki); }
    }
    if (texts.length === 0) return;
    const doIt = async () => {
      const map: Record<string, string> = {};
      for (const t of texts) { map[t] = await translateText(t); }
      setTr(map);
    };
    doIt();
  }, [eli5, isSourceLanguage, translateText]);
  const t = (text: string) => tr[text] || text;
  const round100 = (n: number) => Math.round(n / 100) * 100;
  const hasBeforeAfter = eli5.concept.intro_before && eli5.concept.intro_after;
  const hasConceptIntro = eli5.concept.vision_statement || eli5.concept.design_style || eli5.concept.value_story;
  const shouldHideNumbers = !!hideNumbers;
  // Sort rooms most expensive first
  const sortedRooms = [...eli5.rooms].sort((a, b) => b.cost - a.cost);

  return (
    <div className="mb-6">
      {/* Before → After intro */}
      {hasBeforeAfter ? (
        <div className="rounded-xl mb-4 border border-stone-200 overflow-hidden">
          {/* Before */}
          <div className="bg-stone-50 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400 mb-1">{s.now}</p>
            <p className="text-stone-700 text-[15px] leading-relaxed">{t(eli5.concept.intro_before!)}</p>
          </div>
          {/* Arrow */}
          <div className="flex justify-center -my-2.5 relative z-10">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center shadow-sm">
              <ArrowDown className="w-4 h-4 text-white" />
            </div>
          </div>
          {/* After */}
          <div className="bg-emerald-50 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 mb-1">{s.afterReno}</p>
            <p className="text-emerald-900 text-[15px] leading-relaxed">{t(eli5.concept.intro_after!)}</p>
          </div>
        </div>
      ) : hasConceptIntro ? (
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 mb-4 border border-amber-100">
          {eli5.concept.design_style && (
            <p className="font-semibold text-amber-900 mb-1">{eli5.concept.design_style}</p>
          )}
          {eli5.concept.vision_statement && (
            <p className="text-gray-700 text-[15px] leading-relaxed">{eli5.concept.vision_statement}</p>
          )}
          {eli5.concept.value_story && (
            <p className="text-sm text-amber-700 mt-2 font-medium">{eli5.concept.value_story}</p>
          )}
        </div>
      ) : eli5.timeline?.summary ? (
        <div className="rounded-xl p-4 mb-4 bg-gray-50 border border-gray-200">
          <p className="text-gray-700 text-[15px] leading-relaxed">{t(eli5.timeline.summary)}</p>
        </div>
      ) : null}

      {/* Room-by-room breakdown */}
      <h4 className="text-lg font-semibold mb-3 text-gray-900">
        {s.roomBreakdown}
      </h4>

      <div className="space-y-3">
        {sortedRooms.map((room) => (
          <div key={room.room_id} className="bg-white border rounded-lg overflow-hidden">
            {/* Room header: name + cost */}
            <div className="bg-gray-50 px-3 py-2 border-b">
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-800">{t(room.room_name)}</span>
                {!shouldHideNumbers && (
                  <span className="text-sm font-semibold text-gray-900">{eurFmt.format(round100(room.cost))}</span>
                )}
              </div>
              {/* Tagline sentence */}
              <p className="text-xs text-gray-500 mt-0.5">{t(room.tagline)}</p>
            </div>

            {/* 2-5 buyer-friendly packages */}
            {room.packages && room.packages.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {room.packages.map((pkg, i) => (
                  <div key={i} className="px-3 py-2 flex items-center justify-between text-sm">
                    <span className="text-gray-700">{t(pkg.name)}</span>
                    {!shouldHideNumbers && (
                      <span className="font-medium text-gray-900">{eurFmt.format(round100(pkg.cost))}</span>
                    )}
                  </div>
                ))}
              </div>
            ) : room.key_changes && room.key_changes.length > 0 ? (
              <div className="px-3 py-2 flex flex-wrap gap-1">
                {room.key_changes.map((change, i) => (
                  <span key={i} className="text-xs px-2 py-1 bg-gray-50 text-gray-700 rounded-full">{t(change)}</span>
                ))}
              </div>
            ) : null}
          </div>
        ))}

        {/* General items if present */}
        {eli5.general_items && (
          <div className="bg-gray-50 border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-800">🔧 {eli5.general_items.tagline}</span>
              {!shouldHideNumbers && (
                <span className="text-sm font-semibold text-gray-900">{eurFmt.format(eli5.general_items.cost)}</span>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {eli5.general_items.key_items.map((item, i) => (
                <span key={i} className="text-xs px-2 py-1 bg-white text-gray-700 rounded-full">{t(item)}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Timeline removed — hero metrics already show duration */}
    </div>
  );
};


// =============================================================================
// FULLSCREEN COMPARABLE VIEWER
// =============================================================================
// (ComparablesCarousel and FullscreenImageCarousel removed — comparables have
// their own dedicated tab now; see ComparablesTab.tsx)
// =============================================================================

// =============================================================================
// MAIN MODAL COMPONENT
// =============================================================================

export const BracketAnalysisModal: React.FC<BracketAnalysisModalProps> = ({
  isOpen,
  onClose,
  analysis,
  listingId,
  address,
  hideEli5Numbers,
}) => {
  const { s } = useAppStrings();
  const [showOfficialBudgetModal, setShowOfficialBudgetModal] = useState(false);
  const [showNegotiationModal, setShowNegotiationModal] = useState(false);

  if (!analysis) return null;

  const bracketLabel = s.fairMarket;

  return (
    <>
    {/* Official Budget Report (overlay) */}
    <OfficialBudgetReport
      isOpen={showOfficialBudgetModal}
      onClose={() => setShowOfficialBudgetModal(false)}
      analysis={analysis}
      listingId={listingId}
      address={address}
    />
    {/* Negotiation Modal (overlay) */}
    <NegotiationModal
      isOpen={showNegotiationModal}
      onClose={() => setShowNegotiationModal(false)}
      listingId={listingId}
    />
    
    <div>
      {/* ROOM IMAGES CAROUSEL */}
      <RoomImagesCarousel 
        roomImages={analysis.room_images || []}
        fallbackBefore={analysis.before_image}
        fallbackAfter={analysis.after_image}
        bracketLabel={bracketLabel}
      />

      {/* HERO METRICS */}
      {(() => {
        const refComparable = analysis.comparables?.find(c => c?.comp_role === 'reference');
        const refComparablePrice = Number(
          (analysis.reference_sold_price ?? refComparable?.sale_price ?? analysis.target_price ?? 0) as any
        );
        const asking = Number((analysis.asking_price ?? 0) as any);
        const valueIncrease = refComparablePrice - asking;
        return (
      <HeroMetricsSection
        renovationCost={analysis.renovation_cost}
        valueIncrease={valueIncrease}
        totalWeeks={`${analysis.estimated_weeks_min}-${analysis.estimated_weeks_max} ${s.weeks}`}
        currentEnergy={analysis.energy_compliance?.current_rating}
        targetEnergy={analysis.energy_compliance?.target_rating}
        hideValueAndTime={!!hideEli5Numbers}
      />
        );
      })()}

      {/* Negotiation CTA — hidden in contractor view */}
      {!hideEli5Numbers && (
        <button
          type="button"
          onClick={() => setShowNegotiationModal(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-3.5 mb-6 bg-stone-900 text-white text-sm font-medium rounded-xl hover:bg-stone-800 active:scale-[0.98] transition-all"
          aria-label={s.negotiatePrice}
          tabIndex={0}
        >
          <Shield className="w-4 h-4" />
          <span>{s.negotiatePrice}</span>
          <ChevronRight className="w-4 h-4 opacity-60" />
        </button>
      )}

      {/* ELI5 ROOM TABLE — the V5 buyer-friendly room breakdown */}
      {analysis.eli5_summary && (
        <ELI5RoomTable
          eli5={analysis.eli5_summary}
          hideNumbers={!!hideEli5Numbers}
        />
      )}

      {/* No ELI5 yet → pipeline likely incomplete */}
      {!analysis.eli5_summary && (
        <div className="mb-6 p-4 bg-stone-50 rounded-xl border border-stone-200 text-center">
          <p className="text-stone-500 text-sm">
            {s.eli5Pending}
          </p>
        </div>
      )}

      {/* Comparables moved to dedicated tab — no longer shown here */}
    </div>
    </>
  );
};

export default BracketAnalysisModal;

