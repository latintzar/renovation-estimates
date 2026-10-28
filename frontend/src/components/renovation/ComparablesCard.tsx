'use client';

import {appFetch as fetch} from '@/lib/app-path';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { 
  Scale, 
  Home,
  CheckCircle,
  Loader2,
  Image as ImageIcon,
} from 'lucide-react';
import { BracketAnalysisModal } from './BracketAnalysisModal';
import { useAppStrings } from '@/hooks/AppStringsContext';

// =============================================================================
// IN-MEMORY RENOVATION CACHE
// =============================================================================
// Stores fetched renovation data per listing so that switching tabs is instant.
// Cache is invalidated when we trigger or complete a pipeline run.

interface RenoCacheEntry {
  state: CardState;
  renovationOptions: RenovationOption[];
  bracketsData: BracketsData | null;
  hasCoordinates: boolean;
  timestamp: number;
}

const renoCache = new Map<string, RenoCacheEntry>();

/** Clear cache for a listing (call after pipeline trigger or completion). */
export const invalidateRenoCache = (listingId: number | string) => {
  renoCache.delete(String(listingId));
};

/** Max age before background revalidation (5 minutes). */
const CACHE_MAX_AGE_MS = 5 * 60 * 1000;

// =============================================================================
// TYPES
// =============================================================================

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
  similarity_score?: number;
}

interface PriceBrackets {
  fast_sell: number | null;
  fair_market: number | null;
  premium: number | null;
  count: number;
  comparables: Comparable[];
}

interface BracketsData {
  asking_price: number;
  casafari: PriceBrackets;
  filtered: PriceBrackets;
  filter_tolerance: number;
}

interface RenovationOption {
  bracket: 'fair_market';
  strategy_name?: string;
  target_price: number;
  asking_price: number;
  gap: number;
  renovation_cost: number;
  pem_subtotal: number;
  line_items_count: number;
  scope_of_work: { total_items: number; categories: any[] };
  total_investment: number;
  potential_margin: number;
  estimated_weeks_min: number;
  estimated_weeks_max: number;
  before_image: string;
  after_image: string;
  comparables: Comparable[];
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
    category?: string;
    subcategory?: string;
  }>;
  property_area?: number;
  price_basis?: string;
  confidence_score?: number;
  sanity_check_passed?: boolean;
  risk_flags?: Array<string | { flag: string; severity?: string; mitigation?: string }>;
  room_images?: Array<{
    room_id: string;
    room_name: string;
    before_image: string;
    after_image: string;
    key_changes: string[];
    is_hero: boolean;
  }>;
  delta_scopes?: any;
  dimension_totals?: Record<string, number>;
  eli5_summary?: any;
  architect_report?: any;
  reference_comparable_id?: number;
  reference_sold_price?: number;
  energy_compliance?: Record<string, any>;
}

type CardState = 'initial' | 'loading' | 'renovation_options';

interface ComparablesCardProps {
  listingId: number;
  onBack?: () => void;
  isContractorView?: boolean;
  onDataReady?: (data: { eli5Summary: any | null; address: string | null }) => void;
  /**
   * Render the real UI with hardcoded data (no fetch/polling).
   * WHY: used by marketing pages that want the exact listing UI look, but
   * deterministic and offline.
   */
  mock?: {
    state: CardState;
    renovationOptions: RenovationOption[];
    bracketsData?: BracketsData | null;
    hasCoordinates?: boolean;
  };
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

const formatPrice = (price: number | null | undefined) => {
  if (!price) return '—';
  return `€${price.toLocaleString()}`;
};

// Single strategy: "market_standard" is the only package type we produce.

const buildRenovationOptionsFromV048 = ({
  packages,
  strategySelection,
  askingPrice,
  targetPrices,
  listing,
}: {
  packages: any[];
  listing?: any;
  strategySelection: any;
  askingPrice: number;
  targetPrices: { fast_sell: number; fair_market: number; out_of_market: number };
}): RenovationOption[] => {
  // Market-standard only (product decision).
  // WHY: We don't want to show or use other strategies like "conservative" or "top_of_market".
  const pkgs = Array.isArray(packages) ? packages : [];
  const marketStandardPkg = pkgs.find((pkg: any) => {
    const raw = String(pkg?.package_type || pkg?.strategy_name || pkg?.bracket || '').trim();
    return raw === 'market_standard';
  });

  if (!marketStandardPkg) return [];

  const pkg = marketStandardPkg;
  const asking = Number(askingPrice || 0);
  const referenceComparable = Array.isArray(pkg?.comparables)
    ? pkg.comparables.find((c: any) => c?.comp_role === 'reference')
    : null;
  const referenceSoldPrice = Number(
    pkg?.reference_sold_price ??
    referenceComparable?.sale_price ??
    targetPrices.fair_market ??
    0
  );
  const targetPrice = referenceSoldPrice;
  const renovationCost = Number(pkg?.total_cost || pkg?.renovation_cost || 0);
  const itemCount = Number(pkg?.line_items_count || (Array.isArray(pkg?.line_items) ? pkg.line_items.length : 0) || 0);
  const durationWeeks = Number(pkg?.duration_weeks || 10);

  return [{
    bracket: 'fair_market' as const,
    strategy_name: 'market_standard',
    target_price: targetPrice,
    asking_price: asking,
    gap: targetPrice - asking,
    renovation_cost: renovationCost,
    pem_subtotal: 0,
    line_items_count: itemCount,
    scope_of_work: { total_items: itemCount, categories: [] },
    total_investment: asking + renovationCost,
    potential_margin: targetPrice - asking,
    estimated_weeks_min: durationWeeks,
    estimated_weeks_max: durationWeeks + 2,
    before_image: pkg?.before_image || '',
    after_image: pkg?.after_image || '',
    comparables: pkg?.comparables || [],
    eli5_summary: pkg?.eli5_summary,
    architect_report: pkg?.architect_report,
    delta_scopes: pkg?.delta_scopes,
    dimension_totals: pkg?.dimension_totals,
    cost_breakdown: pkg?.cost_breakdown || {},
    price_basis:pkg?.price_basis,
    property_area:Number(listing?.m2_built||listing?.sqm||0)||undefined,
    confidence_score: pkg?.confidence_score || 0.8,
    sanity_check_passed: pkg?.sanity_check_passed ?? true,
    risk_flags: pkg?.risk_flags || [],
    line_items: pkg?.line_items || [],
    energy_compliance: pkg?.energy_compliance || {},
    room_images: pkg?.room_images || [],
    reference_comparable_id: pkg?.reference_comparable_id,
    reference_sold_price: referenceSoldPrice || undefined,
  }];
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

const MiniListingCard: React.FC<{ comp: Comparable }> = ({ comp }) => {
  const { s: strings } = useAppStrings();
  const [imageError, setImageError] = useState(false);
  const mainPhoto = comp.photo_urls?.[0];

  return (
    <div className="flex-shrink-0 w-40 border rounded-lg overflow-hidden bg-white hover:shadow-md transition-shadow">
      {/* Photo */}
      <div className="relative h-24 bg-gray-100">
        {mainPhoto && !imageError ? (
          <img 
            src={mainPhoto} 
            alt={comp.address || 'Propiedad'} 
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <Home className="w-6 h-6" />
          </div>
        )}
        {/* Distance badge */}
        <div className="absolute top-1 right-1 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded">
          {comp.distance_km.toFixed(1)}km
        </div>
      </div>
      
      {/* Info */}
      <div className="p-2">
        <p className="font-semibold text-sm text-gray-900">{formatPrice(comp.sale_price)}</p>
        <p className="text-xs text-gray-500">{comp.total_area}m²</p>
        {comp.plot_area && (
          <p className="text-xs text-gray-400">{comp.plot_area}m² {strings.plotArea}</p>
        )}
        {comp.photo_urls && comp.photo_urls.length > 1 && (
          <p className="text-xs text-stone-400 mt-0.5">{comp.photo_urls.length} fotos</p>
        )}
      </div>
    </div>
  );
};

// Format price in compact K format (€38K)
const formatCompactPrice = (price: number): string => {
  const absPrice = Math.abs(price);
  if (absPrice >= 1000) {
    return `€${Math.round(absPrice / 1000)}K`;
  }
  return `€${Math.round(absPrice)}`;
};

const RenovationOptionCard: React.FC<{
  option: RenovationOption;
  isExpanded: boolean;
  onToggle: () => void;
  onBack: () => void;
  listingId: number;
  isContractorView?: boolean;
  autoOpen?: boolean;
}> = ({ option, isExpanded, onToggle, onBack, listingId, isContractorView, autoOpen = false }) => {
  const { s: strings } = useAppStrings();
  const [showModal, setShowModal] = useState(autoOpen);
  const { renovation_cost, potential_margin,
          after_image, estimated_weeks_min, estimated_weeks_max } = option;
  
  // Calculate average weeks for display
  const avgWeeks = Math.round((estimated_weeks_min + estimated_weeks_max) / 2);
  
  // Card View - matches landing page mockup design
  return (
    <>
      <button 
        onClick={() => setShowModal(true)}
        className="w-full text-left rounded-2xl mb-4 bg-white overflow-hidden shadow-sm hover:shadow-md transition-all border border-stone-100"
      >
        <div className="flex">
          {/* Left: After Image */}
          <div className="w-[55%] aspect-[4/3]">
            {after_image ? (
              <img 
                src={after_image} 
                className="w-full h-full object-cover" 
                alt={strings.previewAlt} 
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-stone-100 to-stone-200 flex items-center justify-center">
                <ImageIcon className="w-12 h-12 text-stone-300" />
              </div>
            )}
          </div>
          
          {/* Right: Stats */}
          <div className="flex-1 flex flex-col justify-center px-4 py-4 space-y-3">
            {/* Inversión (Investment) */}
            <div className="text-center">
              <p className="text-stone-400 text-xs font-medium tracking-wide">Inversión</p>
              <p className="text-2xl font-bold text-stone-900">{formatCompactPrice(renovation_cost)}</p>
            </div>
            
            {/* Valor + (Value Added) — hidden in contractor view */}
            {!isContractorView && (() => {
              const netProfit = potential_margin - renovation_cost;
              const isNetPositive = netProfit >= 0;
              return (
                <div className="text-center">
                  <p className="text-stone-400 text-xs font-medium tracking-wide">Valor +</p>
                  <p className={`text-xl font-bold ${isNetPositive ? 'text-emerald-600' : 'text-red-500'}`}>
                    {potential_margin >= 0 ? '+' : ''}{formatCompactPrice(potential_margin)}
                  </p>
                  {!isNetPositive && (
                    <p className="text-[10px] font-medium text-red-400 mt-0.5">
                      neto -{formatCompactPrice(netProfit)}
                    </p>
                  )}
                </div>
              );
            })()}
            
            {/* Plazo (Timeline) — hidden in contractor view */}
            {!isContractorView && (
              <div className="text-center">
                <p className="text-stone-400 text-xs font-medium tracking-wide">Plazo</p>
                <p className="text-xl font-bold text-stone-900">{avgWeeks} sem</p>
              </div>
            )}
          </div>
        </div>
      </button>
      
      {/* Full-screen Modal */}
      <BracketAnalysisModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        analysis={option}
        listingId={listingId}
        hideEli5Numbers={!!isContractorView}
      />
    </>
  );
};

// =============================================================================
// PIPELINE PROGRESS — Vercel-style live animation
// =============================================================================

// V5 stages in execution order (used for the vertical timeline)
const V5_STAGE_ORDER = [
  'snapshot', 'comparables', 'clustering', 'v5_room_tags', 'v5_pir',
  'v5_select', 'v5_comparables', 'v5_delta', 'v5_delta_review', 'v5_decompose',
  'v5_smart_m2', 'v5_bcca_match', 'v5_quant_plan', 'v5_forage', 'v5_boq_assembly',
  'v5_finalize', 'v5_eli5',
  'v5_room_images_defurnish', 'v5_room_images_prompt_generation',
  'v5_room_images_style_consistency', 'v5_room_images_photo_generation',
  'v5_negotiation', 'v5_translations',
];

// Rotating patience messages — cycle through these while waiting
const PATIENCE_MESSAGES = [
  'Esto suele tardar entre 2 y 4 minutos...',
  'Cada foto se analiza individualmente por IA...',
  'Estamos comparando con propiedades vendidas reales...',
  'Los precios se calculan con la base de datos BCCA oficial...',
  'Mejor tomarse un café mientras tanto...',
  'Cada habitación se inspecciona por separado...',
  'Detectando hasta el más mínimo detalle...',
  'La precisión requiere paciencia...',
  'Verificando doble cada partida de obra...',
  'Casi listo... o puede que no, pero estamos en ello...',
];

const PipelineProgress: React.FC<{
  pipelineStatus: string;
  currentStage: string | null;
  completedStages: number | null;
  totalStages: number | null;
  stages: any[] | null;
  stageLabels: Record<string, string>;
  stageSubtitles: Record<string, string>;
  strings: any;
}> = ({ pipelineStatus, currentStage, completedStages, totalStages, stages, stageLabels, stageSubtitles, strings }) => {
  // Rotating patience message
  const [patienceIdx, setPatienceIdx] = useState(0);
  const [patienceFading, setPatienceFading] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setPatienceFading(true);
      setTimeout(() => {
        setPatienceIdx(i => (i + 1) % PATIENCE_MESSAGES.length);
        setPatienceFading(false);
      }, 300);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Elapsed time counter
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const fmtElapsed = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s.toString().padStart(2, '0')}s` : `${s}s`;
  };

  const progress = completedStages && totalStages ? completedStages / totalStages : 0;

  // Build stage status map from the stages array
  const stageStatusMap = useMemo(() => {
    const map: Record<string, 'done' | 'running' | 'pending'> = {};
    if (stages) {
      for (const s of stages) {
        const name = s.stage || s.name;
        if (!name) continue;
        const succeeded = Number(s.succeeded ?? s.succeeded_jobs ?? 0);
        const inProgress = Number(s.in_progress ?? s.in_progress_jobs ?? 0);
        const queued = Number(s.queued ?? s.queued_jobs ?? 0);
        if (succeeded > 0 && inProgress === 0 && queued === 0) {
          map[name] = 'done';
        } else if (inProgress > 0) {
          map[name] = 'running';
        } else if (queued > 0) {
          map[name] = 'pending';
        } else {
          map[name] = 'pending';
        }
      }
    }

    // Infer from currentStage if stages array is empty.
    if (!stages && currentStage) {
      const idx = V5_STAGE_ORDER.indexOf(currentStage);
      V5_STAGE_ORDER.forEach((s, i) => {
        if (i < idx) map[s] = 'done';
        else if (i === idx) map[s] = 'running';
        else map[s] = 'pending';
      });
    }
    return map;
  }, [stages, currentStage]);

  // Determine which stages to show (only the ones we know about)
  const visibleStages = V5_STAGE_ORDER.filter(s => stageLabels[s]);

  if (pipelineStatus === 'queued') {
    return (
      <div className="py-12 flex flex-col items-center text-center px-4">
        <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mb-4">
          <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
        </div>
        <p className="text-base font-semibold text-stone-800 mb-1">{strings.queued}</p>
        <p className="text-sm text-stone-500 max-w-xs">
          Hay otra propiedad en análisis ahora mismo. La tuya es la siguiente.
        </p>
      </div>
    );
  }

  return (
    <div className="py-6 px-4">
      {/* ── Header: progress bar + elapsed timer ── */}
      <div className="mb-6">
        {/* Top row: label + elapsed */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-stone-800">
            {currentStage
              ? (stageLabels[currentStage] || strings.inProgress)
              : strings.starting}
          </span>
          <span className="text-xs font-mono text-stone-400 tabular-nums">
            {fmtElapsed(elapsed)}
          </span>
        </div>

        {/* Progress bar with shimmer effect */}
        <div className="relative h-2 bg-stone-100 rounded-full overflow-hidden">
          {/* Filled portion */}
          <div
            className="absolute inset-y-0 left-0 bg-stone-800 rounded-full animate-progress-glow"
            style={{
              width: `${Math.min(100, Math.max(3, progress * 100))}%`,
              transition: 'width 1.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
          {/* Shimmer overlay on the progress bar */}
          <div
            className="absolute inset-y-0 left-0 animate-shimmer-sweep rounded-full"
            style={{
              width: `${Math.min(100, Math.max(3, progress * 100))}%`,
              transition: 'width 1.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
        </div>

        {/* Progress counter */}
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[11px] text-stone-400">
            {completedStages !== null && totalStages !== null
              ? `${completedStages} de ${totalStages} etapas`
              : 'Iniciando...'}
          </span>
          {completedStages !== null && totalStages !== null && (
            <span className="text-[11px] text-stone-400 tabular-nums">
              {Math.round(progress * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* ── Vertical Stage Timeline ── */}
      <div className="relative ml-1">
        {visibleStages.map((stageName, i) => {
          const status = stageStatusMap[stageName] || 'pending';
          const isLast = i === visibleStages.length - 1;

          return (
            <div
              key={stageName}
              className="flex items-start gap-3 animate-step-enter"
              style={{ animationDelay: `${i * 30}ms` }}
            >
              {/* Timeline line + dot */}
              <div className="flex flex-col items-center shrink-0 w-5">
                {/* Dot */}
                <div className="relative">
                  {status === 'done' && (
                    <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                      <CheckCircle className="w-3.5 h-3.5 text-white" />
                    </div>
                  )}
                  {status === 'running' && (
                    <div className="relative">
                      <div className="w-5 h-5 rounded-full bg-stone-800 flex items-center justify-center animate-pulse-ring">
                        <div className="w-2 h-2 rounded-full bg-white" />
                      </div>
                    </div>
                  )}
                  {status === 'pending' && (
                    <div className="w-5 h-5 rounded-full border-2 border-stone-200 bg-white" />
                  )}
                </div>
                {/* Connector line */}
                {!isLast && (
                  <div className={`w-0.5 flex-1 min-h-[20px] ${
                    status === 'done' ? 'bg-emerald-300' :
                    status === 'running' ? 'bg-gradient-to-b from-stone-800 to-stone-200' :
                    'bg-stone-200'
                  }`} />
                )}
              </div>

              {/* Stage content */}
              <div className={`pb-4 flex-1 min-w-0 ${status === 'pending' ? 'opacity-40' : ''}`}>
                <p className={`text-sm leading-tight ${
                  status === 'running' ? 'font-semibold text-stone-900' :
                  status === 'done' ? 'font-medium text-stone-600' :
                  'text-stone-400'
                }`}>
                  {stageLabels[stageName]}
                </p>
                {/* Show subtitle only for the active stage */}
                {status === 'running' && (
                  <p className="text-xs text-stone-500 mt-0.5 animate-text-fade-in">
                    {stageSubtitles[stageName] || '...'}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Rotating patience message ── */}
      <div className="mt-4 pt-4 border-t border-stone-100 text-center">
        <p
          className={`text-xs text-stone-400 italic transition-opacity duration-300 ${
            patienceFading ? 'opacity-0' : 'opacity-100'
          }`}
        >
          {PATIENCE_MESSAGES[patienceIdx]}
        </p>
      </div>
    </div>
  );
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export const ComparablesCard: React.FC<ComparablesCardProps> = ({ listingId, onBack, isContractorView, onDataReady, mock }) => {
  const initialMock = mock && mock.state !== 'loading' ? mock : null;

  // START IN LOADING STATE - never show buttons while checking for existing data
  const [state, setState] = useState<CardState>(initialMock?.state ?? 'loading');
  const [bracketsData, setBracketsData] = useState<BracketsData | null>(initialMock?.bracketsData ?? null);
  const [renovationOptions, setRenovationOptions] = useState<RenovationOption[]>(initialMock?.renovationOptions ?? []);
  const [expandedBracket, setExpandedBracket] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasCoordinates, setHasCoordinates] = useState(initialMock?.hasCoordinates ?? true);
  const [loadingMessage, setLoadingMessage] = useState<string>('Cargando datos de reforma...');

  // Centralized translation — all strings come from AppStringsContext
  const { s: strings } = useAppStrings();

  // Lift ELI5 summary (and address) up to the listing page for share modal usage.
  // Guard against parent callback identity changes to avoid render loops.
  const lastSentRef = useRef<{ eli5Summary: any | null; address: string | null } | null>(null);
  useEffect(() => {
    if (!onDataReady) return;

    if (state !== 'renovation_options' || renovationOptions.length === 0) {
      const payload = { eli5Summary: null, address: null };
      const last = lastSentRef.current;
      if (last?.eli5Summary === payload.eli5Summary && last?.address === payload.address) return;
      lastSentRef.current = payload;
      onDataReady(payload);
      return;
    }

    const primary =
      renovationOptions.find(o => !!o.eli5_summary) ||
      renovationOptions.find(o => o.bracket === 'fair_market') ||
      renovationOptions[0];

    const eli5Summary = primary?.eli5_summary ?? null;
    const addr =
      typeof eli5Summary?.property_summary?.address === 'string'
        ? String(eli5Summary.property_summary.address).trim() || null
        : null;

    const payload = { eli5Summary, address: addr };
    const last = lastSentRef.current;
    if (last?.eli5Summary === payload.eli5Summary && last?.address === payload.address) return;
    lastSentRef.current = payload;
    onDataReady(payload);
  }, [onDataReady, renovationOptions, state]);

  // Stage labels — user-friendly, non-technical (Spanish default)
  // Wrapped in useMemo to avoid re-creating on every render (useCallback deps)
  const STAGE_LABELS = useMemo<Record<string, string>>(() => ({
    snapshot: 'Recopilando datos del inmueble',
    comparables: 'Buscando propiedades similares',
    clustering: 'Revisando fotos habitación por habitación',
    v5_room_tags: 'Identificando cada habitación',
    v5_pir: 'Inspeccionando el estado del inmueble',
    v5_select: 'Encontrando el mejor comparable',
    v5_comparables: 'Estudiando la propiedad de referencia',
    v5_delta: 'Calculando las obras necesarias',
    v5_delta_review: 'Alineando consistencia entre habitaciones',
    v5_decompose: 'Desglosando en partidas de trabajo',
    // V4-tail stages (construction pricing engine)
    v5_smart_m2: 'Midiendo cada habitación',
    v5_bcca_match: 'Buscando códigos de construcción',
    v5_quant_plan: 'Planificando cantidades',
    v5_forage: 'Midiendo desde las fotos',
    v5_boq_assembly: 'Montando el presupuesto',
    // Presentation stages
    v5_eli5: 'Preparando el resumen para ti',
    v5_room_images: 'Generando imágenes de reforma',
    v5_room_images_defurnish: 'Quitando muebles y despejando cada foto',
    v5_room_images_prompt_generation: 'Escribiendo prompts de reforma por habitación',
    v5_room_images_style_consistency: 'Alineando estilo entre todas las habitaciones',
    v5_room_images_photo_generation: 'Renderizando las imágenes finales',
    v5_negotiation: 'Preparando guía de negociación',
    v5_translations: 'Preparando traducciones',
    v5_finalize: 'Ajustes finales',
    // Legacy fallbacks
    v5_boq: 'Calculando el presupuesto de obra',
    v5_run: 'Redactando tu informe de reforma',
    smart_m2: 'Midiendo habitaciones',
    panorama: 'Creando panorámicas',
    pir: 'Inspeccionando el estado',
    strategy: 'Eligiendo estrategia',
    delta_scopes: 'Calculando alcance',
    boq_v3: 'Generando informe',
  }), []);

  // Fun subtitles under the main stage label (Spanish default)
  const STAGE_SUBTITLES = useMemo<Record<string, string>>(() => ({
    snapshot: 'Reuniendo todo lo que sabemos sobre este inmueble...',
    comparables: 'Rastreando el barrio en busca de ventas recientes similares...',
    clustering: 'Nuestra IA está mirando cada rincón de cada foto...',
    v5_room_tags: '¿Cocina, dormitorio, habitación misteriosa? Lo estamos averiguando...',
    v5_pir: 'Revisando paredes, suelos, instalaciones — una inspección completa...',
    v5_select: '¿Cuál es la mejor referencia del mercado? Vamos a verlo...',
    v5_comparables: 'Estudiando los acabados de la propiedad de referencia...',
    v5_delta: 'Comparando estado actual vs objetivo — detectando diferencias...',
    v5_delta_review: 'Revisando TODAS las habitaciones con contexto completo (tracked changes)...',
    v5_decompose: 'Convirtiendo ideas en partidas concretas con cantidades...',
    v5_smart_m2: 'Calculando metros cuadrados reales de cada habitación...',
    v5_bcca_match: 'Emparejando cada tarea con su código oficial de construcción...',
    v5_quant_plan: 'Diseñando fórmulas para calcular cantidades exactas...',
    v5_forage: 'Sacando medidas de las fotos con inteligencia artificial...',
    v5_boq_assembly: 'Montando todas las partidas en un presupuesto completo...',
    v5_eli5: 'Traduciendo jerga constructiva a un resumen que se entienda...',
    v5_room_images: 'Nuestra IA está renderizando el antes y después de cada habitación...',
    v5_room_images_defurnish: 'Primero limpiamos cada foto para evitar ruido visual...',
    v5_room_images_prompt_generation: 'Ahora describimos con precisión cada cambio visible...',
    v5_room_images_style_consistency: 'Revisando que toda la casa mantenga un estilo coherente...',
    v5_room_images_photo_generation: 'Generando el resultado final foto por foto...',
    v5_negotiation: 'Analizando los puntos clave para negociar el precio...',
    v5_translations: 'Traduciendo todo a inglés, alemán, francés, catalán e italiano...',
    v5_finalize: 'Ya casi — últimos retoques...',
    v5_run: 'Ya casi — ajustando cifras finales y puliendo el informe...',
  }), []);

  // ─── Helpers: extract asking price and target prices from raw API responses ───
  const extractAskingPrice = (listingResult: any): number => {
    const d = listingResult?.data || listingResult;
    return d?.price_eur || d?.price || d?.scraped_data?.price || d?.scraped_data?.price_eur || 0;
  };

  const extractTargetPrices = (bracketsResult: any) => {
    const defaults = { fast_sell: 0, fair_market: 0, out_of_market: 0 };
    if (!bracketsResult?.success || !bracketsResult?.hasData || !bracketsResult?.data) return defaults;
    const b = bracketsResult.data;
    return {
      fast_sell: b.filtered?.fast_sell || b.casafari?.fast_sell || 0,
      fair_market: b.filtered?.fair_market || b.casafari?.fair_market || 0,
      out_of_market: b.filtered?.premium || b.casafari?.premium || 0,
    };
  };

  // ─── Helper: apply pipeline status to state ───
  const applyPipelineStatus = useCallback((statusResult: any) => {
    const queued = statusResult.queued_jobs || 0;
    const inProg = statusResult.in_progress_jobs || 0;
    const completed = statusResult.completed_stages || 0;
    const total = statusResult.total_stages || 0;
    const stage = statusResult.current_stage || 'Procesando';
    const label = STAGE_LABELS[String(stage)] || String(stage);

    setState('loading');
    setPipelineCompletedStages(typeof completed === 'number' ? completed : null);
    setPipelineTotalStages(typeof total === 'number' ? total : null);
    setPipelineCurrentStage(String(stage));
    setPipelineStages(Array.isArray(statusResult?.stages) ? statusResult.stages : null);

    if (inProg === 0 && queued > 0) {
      setPipelineStatus('queued');
      setPipelineProgressMsg('En cola — hay otro análisis en curso. Vuelve en unos minutos.');
      setLoadingMessage('En cola — esperando turno...');
    } else {
      setPipelineStatus('running');
      setPipelineProgressMsg(`${label} (${completed}/${total || '?'})`);
      setLoadingMessage(label);
    }
  }, [STAGE_LABELS]);

  // ─── Helper: fetch all data after pipeline completion (parallel) ───
  const fetchCompletedData = useCallback(async (): Promise<boolean> => {
    const ts = `_t=${Date.now()}`;
    const [packagesResp, listingResp, bracketsResp] = await Promise.all([
      fetch(`/api/renovation/${listingId}/v048/packages?${ts}`),
      fetch(`/api/listings/${listingId}?${ts}`),
      fetch(`/api/renovation/${listingId}/comparables/brackets?${ts}`),
    ]);
    const [packagesResult, listingResult, bracketsResult] = await Promise.all([
      packagesResp.json(),
      listingResp.json(),
      bracketsResp.json(),
    ]);

    if (packagesResult.success && packagesResult.hasData && (packagesResult.packages?.length || 0) > 0) {
      const askingPrice = extractAskingPrice(listingResult);
      const targetPrices = extractTargetPrices(bracketsResult);

      if (bracketsResult?.data) {
        setBracketsData(bracketsResult.data);
      }

      const options = buildRenovationOptionsFromV048({
        packages: packagesResult.packages || [],
        strategySelection: packagesResult.strategy_selection,
        askingPrice,
        targetPrices,
      listing:listingResult.data,
      });

      if (options.length > 0) {
        setRenovationOptions(options);
        setPipelineStatus('complete');
          setState('renovation_options');

        // Update cache
        renoCache.set(String(listingId), {
          state: 'renovation_options',
          renovationOptions: options,
          bracketsData: bracketsResult?.data || null,
          hasCoordinates: bracketsResult?.hasCoordinates ?? true,
          timestamp: Date.now(),
        });
        return true;
      }
    }
    return false;
  }, [listingId]);

  // ==========================================================================
  // MAIN DATA LOADING — cache-first, parallel fetches, background revalidation
  // ==========================================================================
  useEffect(() => {
    if (mock) return;
    let pollInterval: NodeJS.Timeout | null = null;
    let cancelled = false;

    // ── 1. Instant display from cache ──
    const cacheKey = String(listingId);
    const cached = renoCache.get(cacheKey);
    if (cached && cached.state !== 'loading') {
      setState(cached.state);
      setRenovationOptions(cached.renovationOptions);
      setBracketsData(cached.bracketsData);
      setHasCoordinates(cached.hasCoordinates);
      console.log(`⚡ Reno cache hit for ${listingId} (age ${((Date.now() - cached.timestamp) / 1000).toFixed(0)}s)`);

      // If cache is fresh enough, skip network entirely ONLY when we already have
      // final renovation results. For initial/brackets states we still revalidate,
      // otherwise users can get "stuck" seeing stale "Iniciar análisis" UI.
      if (cached.state === 'renovation_options' && Date.now() - cached.timestamp < CACHE_MAX_AGE_MS) {
        return;
      }
      // Otherwise, revalidate in background (data already shown, no spinner)
    }

    // ── 2. Fetch fresh data from network ──
    const loadData = async () => {
      try {
        const ts = `_t=${Date.now()}`;

        // Fire ALL independent requests in parallel:
        //   - V5 packages (most likely to have the answer)
        //   - Pipeline status (to know if something is running)
        //   - Listing data (for asking price)
        //   - Brackets data (for target prices)
        const [v5Resp, statusResp, listingResp, bracketsResp] = await Promise.all([
          fetch(`/api/renovation/${listingId}/v048/packages?${ts}`),
          fetch(`/api/renovation/${listingId}/v048/status?${ts}`),
          fetch(`/api/listings/${listingId}?${ts}`),
          fetch(`/api/renovation/${listingId}/comparables/brackets?${ts}`),
        ]);

        if (cancelled) return;

        const [v5Result, statusResult, listingResult, bracketsResult] = await Promise.all([
          v5Resp.json(),
          statusResp.json(),
          listingResp.json(),
          bracketsResp.json(),
        ]);

        if (cancelled) return;

        const askingPrice = extractAskingPrice(listingResult);
        const targetPrices = extractTargetPrices(bracketsResult);
        const hasRun =
          !!statusResult?.run_id ||
          Number(statusResult?.queued_jobs || 0) > 0 ||
          Number(statusResult?.in_progress_jobs || 0) > 0 ||
          Number(statusResult?.failed_jobs || 0) > 0 ||
          Number(statusResult?.succeeded_jobs || 0) > 0 ||
          (statusResult?.status && statusResult.status !== 'idle' && statusResult.status !== 'none');
        setPipelineHasRun(!!hasRun);

        // Update brackets state
        if (bracketsResult.success && bracketsResult.hasData && bracketsResult.data) {
          setBracketsData(bracketsResult.data);
          setHasCoordinates(bracketsResult.hasCoordinates ?? true);
        }

        // ── STATUS-FIRST GATE ──────────────────────────────────────────
        // CRITICAL: Always check pipeline status BEFORE showing packages.
        // WHY: partial data (e.g. delta written before ELI5 ran) can produce
        // packages that look real but lack key sections.  The pipeline status
        // is the single source of truth.
        // ──────────────────────────────────────────────────────────────────

        const pipelineRunning = statusResult?.status === 'in_progress' || statusResult?.status === 'queued';
        const pipelineFailed = statusResult?.status === 'error';

        // 1. Pipeline RUNNING → always show progress, never packages
        if (pipelineRunning) {
          console.log('⏳ Pipeline in progress, starting polling...');
          applyPipelineStatus(statusResult);

          pollInterval = setInterval(async () => {
            try {
              const pollResp = await fetch(`/api/renovation/${listingId}/v048/status?_t=${Date.now()}`);
              const pollResult = await pollResp.json();

              if (pollResult.status === 'complete') {
                if (pollInterval) clearInterval(pollInterval);
                await fetchCompletedData();
                return;
              }

              if (pollResult.status === 'error' || pollResult.status === 'halted' || pollResult.status === 'stopped') {
                if (pollInterval) clearInterval(pollInterval);
                setError(pollResult.error || 'El análisis ha fallado. Usa "Resume" o "Clear & rerun" en admin.');
                setPipelineStatus('error');
                setState('initial');
                return;
              }

              if (pollResult.status === 'in_progress') {
                applyPipelineStatus(pollResult);
              }
            } catch (err) {
              console.error('Status poll error:', err);
            }
          }, 5000);

          return; // Polling handles the rest
        }

        // 2. Pipeline FAILED → show error, let user resume from admin
        if (pipelineFailed) {
          console.log('❌ Pipeline failed');
          const failedStage = statusResult?.current_stage || '';
          const stageLabel = failedStage ? (STAGE_LABELS[failedStage] || failedStage) : '';
          setError(
            stageLabel
              ? `El análisis ha fallado en "${stageLabel}". Usa "Resume" en admin para reintentar.`
              : 'El análisis ha fallado. Usa "Resume" o "Clear & rerun" en admin.'
          );
          setPipelineStatus('error');
          // Show pipeline progress so user can see where it stopped
          applyPipelineStatus(statusResult);
          return;
        }

        // 3. Pipeline COMPLETE or NO PIPELINE → try to show packages
        if (v5Result.success && v5Result.hasData && v5Result.packages?.length > 0) {
          console.log('✅ V5 packages found:', v5Result.packages.length);
          const options = buildRenovationOptionsFromV048({
            packages: v5Result.packages,
            strategySelection: v5Result.strategy_selection,
            askingPrice,
            targetPrices,
          listing:listingResult.data,
      });

          if (options.length > 0) {
            setRenovationOptions(options);
            setState('renovation_options');
            renoCache.set(cacheKey, {
              state: 'renovation_options',
              renovationOptions: options,
              bracketsData: bracketsResult?.data || null,
              hasCoordinates: bracketsResult?.hasCoordinates ?? true,
              timestamp: Date.now(),
            });
            return;
          }
        }

        // 4. No packages, no pipeline → show initial state
        setHasCoordinates(bracketsResult?.hasCoordinates ?? true);
        setState('initial');
        if (hasRun) {
          setError('El análisis existe, pero no se pudieron cargar resultados. Usa "Clear & rerun" en admin.');
        }
      } catch (err) {
        console.error('Failed to load renovation data:', err);
        // Only show error state if we don't already have cached data displayed
        if (!cached) setState('initial');
      }
    };
    
    loadData();
    
    return () => {
      cancelled = true;
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [listingId, applyPipelineStatus, fetchCompletedData]);

  // Fetch comparables from Casafari (only if none exist)
  const handleRun = async () => {
    setState('loading');
    setError(null);
    setLoadingMessage(strings.fetchingComps);
    
    try {
      const response = await fetch(`/api/renovation/${listingId}/comparables/brackets`, {
        method: 'POST',
      });
      
      const result = await response.json();
      
      if (result.success && result.data) {
        setBracketsData(result.data);
        setState('initial');
      } else {
        setError(result.error || strings.errorFetch);
        setState('initial');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : strings.unknownError);
      setState('initial');
    }
  };

  const handleBack = () => {
    setState('initial');
    setExpandedBracket(null);
  };

  // Pipeline state
  const [pipelineStatus, setPipelineStatus] = useState<string>('idle');
  const [pipelineProgressMsg, setPipelineProgressMsg] = useState<string>('');
  const [pipelineCompletedStages, setPipelineCompletedStages] = useState<number | null>(null);
  const [pipelineTotalStages, setPipelineTotalStages] = useState<number | null>(null);
  const [pipelineCurrentStage, setPipelineCurrentStage] = useState<string | null>(null);
  const [pipelineStages, setPipelineStages] = useState<any[] | null>(null);
  // Any existing run (queued/running/complete/error) for this listing.
  // WHY: prevent showing "Iniciar análisis" when the listing already has pipeline history.
  const [pipelineHasRun, setPipelineHasRun] = useState<boolean>(false);

  useEffect(() => {
    setPipelineHasRun(false);
  }, [listingId]);
  
  const handleRunPipeline = async () => {
    // Despite the name, this now triggers the V5 pipeline (v2 enqueue routed to V5)
    // Invalidate cache — we're about to generate new data
    invalidateRenoCache(listingId);

    setState('loading');
    setPipelineStatus('starting');
    setPipelineProgressMsg('Iniciando análisis...');
    setPipelineCompletedStages(null);
    setPipelineTotalStages(null);
    setLoadingMessage('Iniciando análisis...');
    setError(null);
    
    try {
      const startResp = await fetch(`/api/listings/${listingId}/run-pipeline`, { method: 'POST' });
      const startResult = await startResp.json().catch(() => ({}));
      if (!startResult?.success) {
        throw new Error(startResult?.error || 'Error al iniciar el análisis');
      }

      // Poll until complete/error, then load packages
      const pollInterval = setInterval(async () => {
        try {
          const statusResp = await fetch(`/api/renovation/${listingId}/v048/status?_t=${Date.now()}`);
          const status = await statusResp.json();
          
          if (status?.status === 'complete') {
            clearInterval(pollInterval);
            // Fetch all completion data in parallel (and update cache)
            const loaded = await fetchCompletedData();
            if (!loaded) {
              setPipelineStatus('running');
              setPipelineProgressMsg('Finalizando resultados...');
              setLoadingMessage('Finalizando resultados...');
            }
            return;
          }

          if (status?.status === 'error' || status?.status === 'halted' || status?.status === 'stopped') {
            clearInterval(pollInterval);
            setError(status?.error || 'Error en el análisis');
            setPipelineStatus('error');
            setState('initial');
            return;
          }

          if (status?.status === 'in_progress') {
            applyPipelineStatus(status);
          }
        } catch (e) {
          console.error('Status poll error:', e);
        }
      }, 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : strings.unknownError);
      setPipelineStatus('error');
      setState('initial');
    }
  };

  return (
    <div className="space-y-3">
      {/* Action Buttons - Only show when needed */}
      {state !== 'renovation_options' && state !== 'loading' && (
        <div className="flex items-center justify-between mb-4">
          {/* Run / Resume analysis (V5 pipeline) */}
          {state === 'initial' &&
            pipelineStatus !== 'running' &&
            pipelineStatus !== 'queued' &&
            !pipelineHasRun && (
            <button
              onClick={handleRunPipeline}
              disabled={!hasCoordinates}
              className={`
                w-full inline-flex items-center justify-center px-4 py-3 rounded-xl font-medium text-sm
                ${!hasCoordinates
                  ? 'bg-stone-100 text-stone-400 cursor-not-allowed' 
                  : 'bg-stone-900 text-white hover:bg-stone-800'}
                transition-colors
              `}
              title={!hasCoordinates ? strings.noCoords : undefined}
            >
              <Scale className="w-4 h-4 mr-2" />
              {pipelineStatus === 'error' ? strings.resumeAnalysis : strings.startAnalysis}
            </button>
          )}
        </div>
      )}
      
      {/* ── Pipeline Status — Vercel-style live progress ── */}
      {(pipelineStatus === 'running' || pipelineStatus === 'queued' || pipelineStatus === 'starting') && (
        <PipelineProgress
          pipelineStatus={pipelineStatus}
          currentStage={pipelineCurrentStage}
          completedStages={pipelineCompletedStages}
          totalStages={pipelineTotalStages}
          stages={pipelineStages}
          stageLabels={STAGE_LABELS}
          stageSubtitles={STAGE_SUBTITLES}
          strings={strings}
        />
        )}

      {/* Content */}
      <div>
        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading State - Shows only during initial data fetch, NOT during pipeline runs */}
        {state === 'loading' && pipelineStatus !== 'running' && pipelineStatus !== 'queued' && pipelineStatus !== 'starting' && (
          <div className="text-center py-8">
            <Loader2 className="animate-spin mx-auto h-8 w-8 text-stone-400 mb-3" />
            <p className="text-stone-500 text-sm">{strings.loadingData}</p>
          </div>
        )}

        {/* No Data State - Only show if we truly have nothing */}
        {state === 'initial' && !error && !bracketsData && (
          <div className="text-center py-8">
            <Scale className="mx-auto h-10 w-10 text-stone-300 mb-3" />
            <p className="text-stone-500 text-sm">
              {strings.runAnalysis}
            </p>
            {!hasCoordinates && (
              <p className="text-amber-600 text-xs mt-2">
                {strings.noCoordWarning}
              </p>
            )}
          </div>
        )}


        
        {/* (Pipeline running status is rendered above — single unified display) */}

        {/* Renovation View — show inline buyer layout; default to market-standard */}
        {state === 'renovation_options' && renovationOptions.length > 0 && (() => {
          // Default to the package that can render the "perfect" buyer layout.
          // WHY: today, only the market-standard strategy reliably includes `eli5_summary` + `room_images`.
          const primary =
            renovationOptions.find(o => !!o.eli5_summary) ||
            renovationOptions.find(o => o.bracket === 'fair_market') ||
            renovationOptions[0];
          return (
            <BracketAnalysisModal
              isOpen={true}
              onClose={() => onBack?.()}
              analysis={primary}
              listingId={listingId}
              hideEli5Numbers={!!isContractorView}
            />
          );
        })()}
      </div>
    </div>
  );
};

export default ComparablesCard;
