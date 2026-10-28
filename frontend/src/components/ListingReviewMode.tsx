'use client';

/**
 * ListingReviewMode
 * =================
 * 
 * Beautiful review UI for scraped property data.
 * 
 * Supports multi-language translation via useTranslation hook.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ChevronLeft, 
  ChevronRight,
  ChevronDown,
  MapPin, 
  Bed, 
  Bath, 
  Ruler, 
  Building2, 
  ExternalLink,
  Loader2,
  Home,
  Waves,
  Trees,
  Car,
  Wind,
  DoorOpen,
  ArrowUpDown,
  Sparkles,
  Map,
  X,
  Navigation
} from 'lucide-react';
import { ScrapedData } from '@/lib/types';
import { MapModal } from './MapModal';
import { useAppStrings } from '@/hooks/AppStringsContext';

interface PhotoData {
  url: string;
  label?: string;
}

interface ListingReviewModeProps {
  data: ScrapedData;
  photos: PhotoData[];
  onCancel?: () => void;
  onConfirm?: () => void;
  isSubmitting?: boolean;
  /** View-only mode - hides confirm/cancel buttons */
  viewMode?: boolean;
  /** Back button handler for view mode */
  onBack?: () => void;
  /** Optional element to render in header right (e.g., language toggle) */
  headerRight?: React.ReactNode;
}

type SwipeableTrackProps = {
  photos: PhotoData[];
  index: number;
  onIndexChange: (next: number) => void;
  onTap?: () => void;
  onDraggingChange?: (dragging: boolean) => void;
  imageClassName: string;
  containerClassName?: string;
  ariaLabel?: string;
};

// Swipeable track (iPhoto-ish): drag left/right to switch photos.
function SwipeableTrack({
  photos,
  index,
  onIndexChange,
  onTap,
  onDraggingChange,
  imageClassName,
  containerClassName,
  ariaLabel,
}: SwipeableTrackProps) {
  const safePhotos = Array.isArray(photos) ? photos.filter(p => Boolean(p?.url)) : [];
  const wrapRef = useRef<HTMLDivElement>(null);
  const lastDragEndedAtRef = useRef(0);

  const drag = useRef({
    pointerId: null as number | null,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    startTime: 0,
    dragging: false,
    moved: false,
  });

  const [offsetPx, setOffsetPx] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const [containerWidth, setContainerWidth] = useState(1);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const update = () => setContainerWidth(Math.max(el.clientWidth, 1));
    update();

    const ro = new ResizeObserver(() => update());
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const clampIndex = useCallback((next: number) => {
    const max = Math.max(safePhotos.length - 1, 0);
    return Math.min(Math.max(next, 0), max);
  }, [safePhotos.length]);

  const goTo = useCallback((next: number) => {
    const clamped = clampIndex(next);
    if (clamped === index) {
      setTransitioning(true);
      setOffsetPx(0);
      window.setTimeout(() => setTransitioning(false), 300);
      return;
    }

    setTransitioning(true);
    setOffsetPx(0);
    onIndexChange(clamped);
    window.setTimeout(() => setTransitioning(false), 300);
  }, [clampIndex, index, onIndexChange]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;

    const d = drag.current;
    d.pointerId = e.pointerId;
    d.startX = e.clientX;
    d.startY = e.clientY;
    d.currentX = e.clientX;
    d.currentY = e.clientY;
    d.startTime = Date.now();
    d.dragging = true;
    d.moved = false;

    setTransitioning(false);
    onDraggingChange?.(true);

    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // Best-effort only; some browsers can throw here.
    }
  }, [onDraggingChange]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    const d = drag.current;
    if (!d.dragging || d.pointerId !== e.pointerId) return;

    d.currentX = e.clientX;
    d.currentY = e.clientY;

    const dx = d.currentX - d.startX;
    const dy = d.currentY - d.startY;

    // If the user is scrolling vertically, don't hijack.
    if (!d.moved && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 12) {
      d.dragging = false;
      d.pointerId = null;
      setOffsetPx(0);
      onDraggingChange?.(false);
      return;
    }

    if (Math.abs(dx) > 6) d.moved = true;

    const atStart = index === 0 && dx > 0;
    const atEnd = index === safePhotos.length - 1 && dx < 0;
    const damped = (atStart || atEnd) ? dx * 0.3 : dx;
    setOffsetPx(damped);
  }, [index, onDraggingChange, safePhotos.length]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    const d = drag.current;
    if (!d.dragging || d.pointerId !== e.pointerId) return;

    d.dragging = false;
    d.pointerId = null;
    onDraggingChange?.(false);

    const dx = d.currentX - d.startX;
    const elapsed = Date.now() - d.startTime;
    const velocity = Math.abs(dx) / Math.max(elapsed, 1);
    const threshold = containerWidth * 0.2;

    const isSwipe = Math.abs(dx) > threshold || velocity > 0.5;
    const didMove = d.moved || Math.abs(dx) > 8;

    if (!didMove) {
      onTap?.();
      setOffsetPx(0);
      return;
    }

    lastDragEndedAtRef.current = Date.now();

    if (isSwipe && dx < 0 && index < safePhotos.length - 1) {
      goTo(index + 1);
      return;
    }
    if (isSwipe && dx > 0 && index > 0) {
      goTo(index - 1);
      return;
    }

    setTransitioning(true);
    setOffsetPx(0);
    window.setTimeout(() => setTransitioning(false), 300);
  }, [containerWidth, goTo, index, onDraggingChange, onTap, safePhotos.length]);

  const handlePointerCancel = useCallback((e: React.PointerEvent) => {
    const d = drag.current;
    if (d.pointerId !== e.pointerId) return;
    d.dragging = false;
    d.pointerId = null;
    setTransitioning(true);
    setOffsetPx(0);
    onDraggingChange?.(false);
    window.setTimeout(() => setTransitioning(false), 300);
  }, [onDraggingChange]);

  if (safePhotos.length === 0) return null;

  const translateX = -(index * 100) + (offsetPx / containerWidth) * 100;

  return (
    <div
      ref={wrapRef}
      className={containerClassName}
      onClickCapture={(e) => {
        // Some browsers will dispatch a click after a drag. Suppress it to
        // prevent swipe → accidental "open fullscreen" or other click actions.
        if (Date.now() - lastDragEndedAtRef.current < 450) {
          e.preventDefault();
          e.stopPropagation();
        }
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      role="group"
      aria-label={ariaLabel || 'Photo carousel'}
    >
      <div
        className="flex h-full"
        style={{
          transform: `translateX(${translateX}%)`,
          transition: transitioning ? 'transform 300ms cubic-bezier(0.25, 1, 0.5, 1)' : 'none',
          willChange: 'transform',
        }}
      >
        {safePhotos.map((p, i) => (
          <div
            key={`${p.url}-${i}`}
            className="w-full h-full shrink-0"
            style={{ minWidth: '100%' }}
          >
            <img
              src={p.url}
              alt={`Foto ${i + 1}`}
              className={imageClassName}
              draggable={false}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// Full Screen Photo Viewer - iOS Photos style swipe
function FullScreenPhotoViewer({
  photos,
  initialIndex,
  onClose,
  onIndexChange,
}: {
  photos: PhotoData[];
  initialIndex: number;
  onClose: () => void;
  onIndexChange: (index: number) => void;
}) {
  const safePhotos = Array.isArray(photos) ? photos.filter(p => Boolean(p?.url)) : [];
  const [currentIndex, setCurrentIndex] = useState(() => Math.min(Math.max(initialIndex, 0), Math.max(safePhotos.length - 1, 0)));

  useEffect(() => {
    setCurrentIndex(Math.min(Math.max(initialIndex, 0), Math.max(safePhotos.length - 1, 0)));
  }, [initialIndex, safePhotos.length]);

  // Sync with parent
  useEffect(() => {
    onIndexChange(currentIndex);
  }, [currentIndex, onIndexChange]);

  const goNext = useCallback(() => {
    setCurrentIndex(prev => Math.min(prev + 1, safePhotos.length - 1));
  }, [safePhotos.length]);

  const goPrev = useCallback(() => {
    setCurrentIndex(prev => Math.max(prev - 1, 0));
  }, []);

  if (safePhotos.length === 0) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black"
      role="dialog"
      aria-modal="true"
      aria-label="Fotos"
    >
      {/* Close button */}
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/70 rounded-full transition-colors"
        aria-label="Cerrar"
      >
        <X className="w-6 h-6 text-white" />
      </button>

      {/* Photo counter */}
      <div className="absolute top-4 left-4 z-10 px-3 py-1.5 bg-black/50 rounded-full text-white text-sm font-medium tabular-nums">
        {currentIndex + 1} / {safePhotos.length}
      </div>

      {/* Swipeable track */}
      <SwipeableTrack
        photos={safePhotos}
        index={currentIndex}
        onIndexChange={setCurrentIndex}
        imageClassName="max-w-full max-h-full object-contain select-none"
        containerClassName="absolute inset-0 flex items-center justify-center p-4 overflow-hidden touch-pan-y"
        ariaLabel="Fullscreen photo carousel"
      />

      {/* Navigation arrows (desktop) */}
      {safePhotos.length > 1 && (
        <>
          {currentIndex > 0 && (
            <button
              type="button"
              onClick={goPrev}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 rounded-full transition-colors"
              aria-label="Foto anterior"
            >
              <ChevronLeft className="w-6 h-6 text-white" />
            </button>
          )}
          {currentIndex < safePhotos.length - 1 && (
            <button
              type="button"
              onClick={goNext}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 rounded-full transition-colors"
              aria-label="Siguiente foto"
            >
              <ChevronRight className="w-6 h-6 text-white" />
            </button>
          )}
        </>
      )}
    </div>
  );
}

export function ListingReviewMode({
  data,
  photos,
  onCancel,
  onConfirm,
  isSubmitting = false,
  viewMode = false,
  onBack,
  headerRight,
}: ListingReviewModeProps) {
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [isCarouselHovered, setIsCarouselHovered] = useState(false);
  const [isCarouselDragging, setIsCarouselDragging] = useState(false);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isFullScreenOpen, setIsFullScreenOpen] = useState(false);
  // Description collapsed by default only in view mode (listing page), expanded on confirm page
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(!viewMode);
  
  // Centralized translation — all UI strings from context
  const { s: translatedStrings } = useAppStrings();

  // Auto-advance carousel
  useEffect(() => {
    if (photos.length <= 1 || isCarouselHovered || isCarouselDragging) return;
    const interval = setInterval(() => {
      setCurrentPhotoIndex(prev => (prev + 1) % photos.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [photos.length, isCarouselHovered, isCarouselDragging]);

  const nextPhoto = useCallback(() => {
    setCurrentPhotoIndex(prev => Math.min(prev + 1, photos.length - 1));
  }, [photos.length]);

  const prevPhoto = useCallback(() => {
    setCurrentPhotoIndex(prev => Math.max(prev - 1, 0));
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') prevPhoto();
      if (e.key === 'ArrowRight') nextPhoto();
      if (e.key === 'Escape' && isFullScreenOpen) setIsFullScreenOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nextPhoto, prevPhoto, isFullScreenOpen]);

  // Handle tap on carousel to open full screen
  const handleCarouselClick = useCallback(() => {
    setIsFullScreenOpen(true);
  }, []);

  const formatPrice = (price?: number) => {
    if (!price) return '—';
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0
    }).format(price);
  };

  const getConditionLabel = (condition?: string) => {
    const labels: Record<string, string> = {
      'new': translatedStrings.newBuild,
      'good': translatedStrings.goodCondition,
      'renovate': translatedStrings.toRenovate,
      'renovated': translatedStrings.renovated
    };
    return labels[condition || ''] || condition || '—';
  };

  const getFloorLabel = (level?: string, number?: number) => {
    if (level === 'ground') return translatedStrings.ground;
    if (level === 'top') return translatedStrings.top;
    if (number !== undefined && number !== null) return `${number}ª`;
    if (level === 'intermediate') return translatedStrings.intermediate;
    return level || '—';
  };

  const amenities = [
    { key: 'has_elevator', icon: ArrowUpDown, label: translatedStrings.elevator },
    { key: 'is_exterior', icon: Wind, label: translatedStrings.exterior },
    { key: 'has_terrace', icon: Home, label: translatedStrings.terrace },
    { key: 'has_balcony', icon: DoorOpen, label: translatedStrings.balcony },
    { key: 'has_pool', icon: Waves, label: translatedStrings.pool },
    { key: 'has_garage', icon: Car, label: translatedStrings.garage },
    { key: 'has_garden', icon: Trees, label: translatedStrings.garden },
    { key: 'has_air_conditioning', icon: Wind, label: translatedStrings.airConditioning },
  ];

  const activeAmenities = amenities.filter(a => data[a.key as keyof ScrapedData]);

  // Get domain for branding
  const getDomain = (url?: string) => {
    if (!url) return null;
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return null;
    }
  };

  const domain = getDomain(data.source_url);

  return (
    <div className={`min-h-screen bg-[#FDFBF7] flex flex-col ${viewMode ? 'pb-6' : 'pb-24'}`}>
      {/* Header */}
      <header className="sticky top-0 bg-[#FDFBF7] border-b border-stone-100 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-center relative">
          {viewMode && onBack && (
            <button 
              onClick={onBack}
              className="absolute left-4 p-2 -ml-2 text-stone-500 hover:text-stone-700"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          )}
          <span className="font-serif text-xl font-medium tracking-tight text-stone-900">
            {viewMode ? translatedStrings.propertyDetails : translatedStrings.reviewListing}
          </span>
          {headerRight && (
            <div className="absolute right-4">
              {headerRight}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
          {/* Photo Carousel - Simple with buttons */}
          <div className="mb-6">
            <div 
              role="button"
              tabIndex={0}
              aria-label="Abrir fotos en pantalla completa"
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleCarouselClick(); }}
              className="relative rounded-2xl overflow-hidden bg-stone-900 aspect-[16/10] cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#da654d]/30"
              onMouseEnter={() => setIsCarouselHovered(true)}
              onMouseLeave={() => setIsCarouselHovered(false)}
              onClick={handleCarouselClick}
            >
              {photos.length > 0 ? (
                <>
                  {/* Swipeable track */}
                  <SwipeableTrack
                    photos={photos}
                    index={currentPhotoIndex}
                    onIndexChange={setCurrentPhotoIndex}
                    onTap={handleCarouselClick}
                    onDraggingChange={setIsCarouselDragging}
                    imageClassName="w-full h-full object-cover select-none"
                    containerClassName="absolute inset-0 overflow-hidden touch-pan-y"
                    ariaLabel="Listing photo carousel"
                  />
                  
                  {/* Gradient overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />

                  {photos.length > 1 && (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); prevPhoto(); }}
                        className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white p-2.5 rounded-full shadow-lg transition-all hover:scale-110 z-10"
                        aria-label="Foto anterior"
                      >
                        <ChevronLeft className="h-4 w-4 text-stone-800" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); nextPhoto(); }}
                        className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white p-2.5 rounded-full shadow-lg transition-all hover:scale-110 z-10"
                        aria-label="Siguiente foto"
                      >
                        <ChevronRight className="h-4 w-4 text-stone-800" />
                      </button>
                    </>
                  )}

                  {/* Photo counter */}
                  <div className="absolute bottom-3 left-3 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-full">
                    <span className="text-white text-sm font-medium">
                      {currentPhotoIndex + 1} / {photos.length}
                    </span>
                  </div>

                </>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-stone-200">
                  <div className="text-center text-stone-400">
                    <Building2 className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>{translatedStrings.noPhotos}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Thumbnail strip - BELOW carousel */}
            {photos.length > 1 && (
              <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
                {photos.slice(0, 10).map((photo, idx) => (
                  <button
                    key={idx}
                    onClick={() => setCurrentPhotoIndex(idx)}
                    className={`flex-shrink-0 w-16 h-12 rounded-lg overflow-hidden border-2 transition-all ${
                      idx === currentPhotoIndex 
                        ? 'border-[#da654d] shadow-md ring-2 ring-[#da654d]/20' 
                        : 'border-stone-200 opacity-70 hover:opacity-100 hover:border-stone-300'
                    }`}
                  >
                    <img src={photo.url} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
                {photos.length > 10 && (
                  <div className="flex-shrink-0 w-16 h-12 rounded-lg bg-stone-100 border-2 border-stone-200 flex items-center justify-center text-stone-500 text-sm font-medium">
                    +{photos.length - 10}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Property Info Card */}
          <div className="bg-white border border-stone-200 rounded-xl shadow-sm p-6">
            {/* Price */}
            <div className="flex items-baseline gap-3 mb-4">
              <p className="text-3xl font-bold text-stone-900">
                {formatPrice(data.price)}
              </p>
              {data.m2_built && data.price && (
                <p className="text-sm text-stone-500">
                  ({formatPrice(Math.round(data.price / data.m2_built))}/m²)
                </p>
              )}
            </div>

            {/* Title */}
            <h1 className="text-xl font-serif font-semibold text-stone-900 mb-2">
              {data.title || 'Anuncio de propiedad'}
            </h1>
            
            {/* Address + Get Directions */}
            <div className="flex items-center gap-3 mb-5 pb-5 border-b border-stone-100">
              <button
                onClick={() => data.lat && data.lng && setIsMapOpen(true)}
                disabled={!data.lat || !data.lng}
                className="group flex items-center gap-2 text-stone-600 flex-1 text-left hover:text-stone-900 transition-colors disabled:cursor-default disabled:hover:text-stone-600"
              >
                <MapPin className="h-4 w-4 text-[#da654d]" />
                <span className="text-sm">{data.address || data.city || translatedStrings.addressNotAvailable}</span>
              </button>
              {data.lat && data.lng && (
                  <a
                    href={`https://www.google.com/maps/dir/?api=1&destination=${data.lat},${data.lng}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#da654d] hover:bg-[#c8553d] text-white text-xs font-medium transition-colors active:scale-95 shrink-0"
                  >
                    <Navigation className="h-3.5 w-3.5" />
                    {translatedStrings.directions}
                  </a>
              )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-4 gap-3 mb-5">
              <div className="text-center p-3 bg-stone-50 rounded-lg overflow-hidden">
                <Ruler className="h-4 w-4 mx-auto mb-1 text-stone-400" />
                <p className="text-lg font-semibold text-stone-800 truncate">{data.m2_built || '—'}</p>
                <p className="text-xs text-stone-500">{translatedStrings.sqm}</p>
              </div>
              <div className="text-center p-3 bg-stone-50 rounded-lg overflow-hidden">
                <Bed className="h-4 w-4 mx-auto mb-1 text-stone-400" />
                <p className="text-lg font-semibold text-stone-800 truncate">{data.bedrooms || '—'}</p>
                <p className="text-xs text-stone-500">{translatedStrings.rooms}</p>
              </div>
              <div className="text-center p-3 bg-stone-50 rounded-lg overflow-hidden">
                <Bath className="h-4 w-4 mx-auto mb-1 text-stone-400" />
                <p className="text-lg font-semibold text-stone-800 truncate">{data.bathrooms || '—'}</p>
                <p className="text-xs text-stone-500">{translatedStrings.baths}</p>
              </div>
              <div className="text-center p-3 bg-stone-50 rounded-lg overflow-hidden">
                <Building2 className="h-4 w-4 mx-auto mb-1 text-stone-400" />
                <p className="text-xs font-semibold text-stone-800 truncate leading-5">{getFloorLabel(data.floor_level, data.floor_number)}</p>
                <p className="text-xs text-stone-500">{translatedStrings.floor}</p>
              </div>
            </div>

            {/* Amenities */}
            {activeAmenities.length > 0 && (
              <div className="mb-5">
                <div className="flex flex-wrap gap-2">
                  {activeAmenities.map(amenity => (
                    <span 
                      key={amenity.key} 
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-sm"
                    >
                      <amenity.icon className="h-3 w-3" />
                      {amenity.label}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Property Type & Condition */}
            <div className="flex flex-wrap gap-3 mb-5 text-sm">
              {data.condition && (
                <span className="px-3 py-1 border border-stone-200 rounded-full font-medium text-stone-700">
                  {getConditionLabel(data.condition)}
                </span>
              )}
              {data.property_subtype && (
                <span className="px-3 py-1 border border-stone-200 rounded-full font-medium text-stone-700 capitalize">
                  {data.property_subtype.replace(/_/g, ' ')}
                </span>
              )}
            </div>

            {/* Description */}
            {data.description && (
              <div className="border-t border-stone-100 pt-4">
                {viewMode ? (
                  // Collapsible in view mode (listing page)
                  <>
                    <button
                      onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
                      className="flex items-center justify-between w-full text-left"
                    >
                      <span className="text-sm font-medium text-stone-700">{translatedStrings.description}</span>
                      <ChevronDown 
                        className={`h-4 w-4 text-stone-400 transition-transform duration-200 ${
                          isDescriptionExpanded ? 'rotate-180' : ''
                        }`} 
                      />
                    </button>
                    <div 
                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                        isDescriptionExpanded ? 'max-h-[2000px] opacity-100 mt-2' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <p className="text-sm text-stone-600 leading-relaxed whitespace-pre-line">
                        {data.description}
                      </p>
                    </div>
                  </>
                ) : (
                  // Always visible on confirm page
                  <>
                    <span className="text-sm font-medium text-stone-700 block mb-2">{translatedStrings.description}</span>
                    <p className="text-sm text-stone-600 leading-relaxed whitespace-pre-line">
                      {data.description}
                    </p>
                  </>
                )}
              </div>
            )}

            {/* Source Link */}
            {data.source_url && (
              <div className="border-t border-stone-100 pt-4 mt-4">
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-[#da654d] hover:text-[#c8553d] transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  {translatedStrings.viewOn} {domain || 'sitio original'}
                </a>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Sticky Bottom Bar - only show in review mode */}
      {!viewMode && onCancel && onConfirm && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 shadow-lg z-50">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
            {/* Small Cancel Button (no fill) */}
            <button 
              onClick={onCancel}
              disabled={isSubmitting}
              className="px-4 py-2 text-stone-500 hover:text-stone-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {translatedStrings.cancel}
            </button>
            
            {/* Main CTA - Analyse with Leo */}
            <button
              onClick={onConfirm}
              disabled={isSubmitting}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-[#da654d] hover:bg-[#c8553d] disabled:bg-[#da654d]/50 text-white rounded-xl font-medium transition-colors shadow-lg text-base"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>{translatedStrings.processing}</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5" />
                  <span>{translatedStrings.analyseWithLeo}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Map Modal */}
      {data.lat && data.lng && (
        <MapModal
          isOpen={isMapOpen}
          onClose={() => setIsMapOpen(false)}
          lat={data.lat}
          lng={data.lng}
          address={data.address || data.city}
          title={data.title}
        />
      )}

      {/* Full Screen Photo Viewer */}
      {isFullScreenOpen && (
        <FullScreenPhotoViewer
          photos={photos}
          initialIndex={currentPhotoIndex}
          onClose={() => setIsFullScreenOpen(false)}
          onIndexChange={setCurrentPhotoIndex}
        />
      )}
    </div>
  );
}

export default ListingReviewMode;