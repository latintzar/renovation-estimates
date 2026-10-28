"use client";

/**
 * ComparableCard Component
 * ========================
 *
 * Displays a sold comparable property as a rich, compact card.
 * Layout: hero image (left 40%) + info panel (right 60%).
 *
 * Tapping anywhere on the card opens a swipeable fullscreen image gallery.
 */

import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  Bath,
  BedDouble,
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Home,
  Image as ImageIcon,
  MapPin,
  Ruler,
  Shield,
  X,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStrings, type AppStrings } from "@/hooks/AppStringsContext";

/* ─── Types ─────────────────────────────────────────── */

type Coordinates = { latitude: number; longitude: number };

export type ComparableFeatures = {
  elevator?: boolean;
  balcony?: boolean;
  terrace?: boolean;
  parking?: boolean;
  pool?: boolean;
  storage?: boolean;
  air_conditioning?: boolean;
  heating?: string;
  characteristics?: string[];
};

export type ComparableForUi = {
  id?: number | string | null;
  casafari_property_id?: number | string | null;
  sale_price?: number | null;
  price_per_sqm?: number | null;
  total_area?: number | null;
  living_area?: number | null;
  plot_area?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  condition?: string | null;
  construction_year?: number | null;
  energy_rating?: string | null;
  distance_km?: number | null;
  address?: string | null;
  photo_urls?: string[];
  coordinates?: Coordinates | null;
  features?: ComparableFeatures | null;
  property_type?: string | null;
  comp_role?: "reference" | "above" | "below" | null;
  is_selected?: boolean;
};

type ComparableCardProps = {
  comparable: ComparableForUi;
  className?: string;
};

/* ─── Helpers ───────────────────────────────────────── */

const fmt = {
  price(v: number | null | undefined): string {
    if (typeof v !== "number" || !Number.isFinite(v)) return "—";
    return `€${v.toLocaleString("es-ES")}`;
  },
  area(m2: number | null | undefined): string {
    if (typeof m2 !== "number" || !Number.isFinite(m2) || m2 <= 0) return "—";
    return `${Math.round(m2)} m²`;
  },
  num(n: number | null | undefined): string {
    if (typeof n !== "number" || !Number.isFinite(n)) return "—";
    return String(n);
  },
};

const getRoleConfig = (s: AppStrings): Record<string, { label: string; bg: string; text: string; border: string }> => ({
  reference: {
    label: s.compReference,
    bg: "bg-brand-600",
    text: "text-white",
    border: "border-brand-700",
  },
  above: {
    label: s.compAbove,
    bg: "bg-stone-800",
    text: "text-stone-100",
    border: "border-stone-700",
  },
  below: {
    label: s.compBelow,
    bg: "bg-stone-800",
    text: "text-stone-100",
    border: "border-stone-700",
  },
});

const featureChips = (features: ComparableFeatures | null | undefined, s: AppStrings): { key: string; label: string }[] => {
  if (!features) return [];
  const chips: { key: string; label: string }[] = [];
  if (features.elevator) chips.push({ key: "elevator", label: s.compElevator });
  if (features.balcony) chips.push({ key: "balcony", label: s.compBalcony });
  if (features.terrace) chips.push({ key: "terrace", label: s.compTerrace });
  if (features.parking) chips.push({ key: "parking", label: s.compParking });
  if (features.pool) chips.push({ key: "pool", label: s.compPool });
  if (features.storage) chips.push({ key: "storage", label: s.compStorage });
  if (features.air_conditioning) chips.push({ key: "ac", label: s.compAC });
  if (features.heating) chips.push({ key: "heating", label: String(features.heating).slice(0, 24) });
  return chips.slice(0, 5);
};

/* ─── Swipeable Fullscreen Gallery (iPhotos-style) ─── */

const SwipeGallery: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  images: string[];
  initialIndex?: number;
  title?: string;
}> = ({ isOpen, onClose, images, initialIndex = 0, title }) => {
  const { s } = useAppStrings();
  const [idx, setIdx] = useState(initialIndex);
  const trackRef = useRef<HTMLDivElement>(null);
  const safeImages = Array.isArray(images) ? images.filter(Boolean) : [];

  // Gesture state
  const drag = useRef({
    startX: 0,
    startY: 0,
    currentX: 0,
    dragging: false,
    startTime: 0,
  });

  const [offset, setOffset] = useState(0);
  const [transitioning, setTransitioning] = useState(false);

  const goTo = useCallback((next: number) => {
    setTransitioning(true);
    setIdx(next);
    setOffset(0);
    const timer = setTimeout(() => setTransitioning(false), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length !== 1) return;
    const d = drag.current;
    d.startX = e.touches[0].clientX;
    d.startY = e.touches[0].clientY;
    d.currentX = d.startX;
    d.dragging = true;
    d.startTime = Date.now();
    setTransitioning(false);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const d = drag.current;
    if (!d.dragging || e.touches.length !== 1) return;
    d.currentX = e.touches[0].clientX;
    const dx = d.currentX - d.startX;
    // Resist overscroll at edges
    const atStart = idx === 0 && dx > 0;
    const atEnd = idx === safeImages.length - 1 && dx < 0;
    const damped = (atStart || atEnd) ? dx * 0.3 : dx;
    setOffset(damped);
  }, [idx, safeImages.length]);

  const handleTouchEnd = useCallback(() => {
    const d = drag.current;
    if (!d.dragging) return;
    d.dragging = false;
    const dx = d.currentX - d.startX;
    const elapsed = Date.now() - d.startTime;
    const velocity = Math.abs(dx) / Math.max(elapsed, 1);
    const threshold = window.innerWidth * 0.2;
    const isSwipe = Math.abs(dx) > threshold || velocity > 0.5;

    if (isSwipe && dx < 0 && idx < safeImages.length - 1) {
      goTo(idx + 1);
    } else if (isSwipe && dx > 0 && idx > 0) {
      goTo(idx - 1);
    } else {
      setTransitioning(true);
      setOffset(0);
      setTimeout(() => setTransitioning(false), 300);
    }
  }, [idx, safeImages.length, goTo]);

  // Reset index when opening
  const prevOpen = useRef(false);
  if (isOpen && !prevOpen.current) {
    // Opening — reset
    if (idx !== initialIndex) setIdx(initialIndex);
    setOffset(0);
    setTransitioning(false);
  }
  prevOpen.current = isOpen;

  if (!isOpen || safeImages.length === 0) return null;

  const translateX = -(idx * 100) + (offset / (typeof window !== "undefined" ? window.innerWidth : 400)) * 100;

  return (
    <div
      className="fixed inset-0 z-[70] bg-black flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label={title || "Images"}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 z-10">
        <button
          type="button"
          onClick={onClose}
          className="rounded-full bg-white/10 p-2 text-white hover:bg-white/20 focus:outline-none"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        {safeImages.length > 1 && (
          <p className="text-xs text-white/50 tabular-nums">
            {idx + 1} / {safeImages.length}
          </p>
        )}
        <div className="w-9" />
      </div>

      {/* Swipeable track */}
      <div
        className="flex-1 overflow-hidden relative"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div
          ref={trackRef}
          className="flex h-full"
          style={{
            transform: `translateX(${translateX}%)`,
            transition: transitioning ? "transform 300ms cubic-bezier(0.25, 1, 0.5, 1)" : "none",
            willChange: "transform",
          }}
        >
          {safeImages.map((url, i) => (
            <div
              key={i}
              className="w-full h-full shrink-0 flex items-center justify-center px-2"
              style={{ minWidth: "100%" }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={url}
                alt={`${title || "Photo"} ${i + 1}`}
                className="max-w-full max-h-full object-contain select-none"
                draggable={false}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Arrow buttons (desktop) */}
      {safeImages.length > 1 && (
        <>
          {idx > 0 && (
            <button
              type="button"
              onClick={() => goTo(idx - 1)}
              className="absolute left-3 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm text-white flex items-center justify-center hover:bg-white/20 transition-colors"
              aria-label={s.prevImage}
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}
          {idx < safeImages.length - 1 && (
            <button
              type="button"
              onClick={() => goTo(idx + 1)}
              className="absolute right-3 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm text-white flex items-center justify-center hover:bg-white/20 transition-colors"
              aria-label={s.nextImage}
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          )}
        </>
      )}

      {/* Dot indicators */}
      {safeImages.length > 1 && safeImages.length <= 20 && (
        <div className="flex justify-center gap-1.5 py-4">
          {safeImages.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => goTo(i)}
              className={cn(
                "rounded-full transition-all",
                i === idx ? "w-5 h-1.5 bg-white" : "w-1.5 h-1.5 bg-white/40",
              )}
              aria-label={`Image ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/* ─── Main Card ─────────────────────────────────────── */

export const ComparableCard: React.FC<ComparableCardProps> = ({ comparable, className }) => {
  const { s } = useAppStrings();
  const [galleryOpen, setGalleryOpen] = useState(false);

  const areaM2 = useMemo(
    () => comparable.total_area || comparable.living_area || null,
    [comparable.living_area, comparable.total_area],
  );

  const roleConfig = useMemo(() => getRoleConfig(s), [s]);
  const role = comparable.comp_role ? roleConfig[comparable.comp_role] : null;
  const chips = featureChips(comparable.features, s);
  const title = comparable.address ? String(comparable.address).trim() : s.compProperty;
  const photoCount = Array.isArray(comparable.photo_urls) ? comparable.photo_urls.length : 0;
  const hero = photoCount > 0 ? comparable.photo_urls?.[0] : null;

  const handleCardClick = () => {
    if (photoCount > 0) setGalleryOpen(true);
  };

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={handleCardClick}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleCardClick(); }}
        className={cn(
          "w-full text-left rounded-2xl overflow-hidden",
          "border border-stone-200/80 bg-white",
          "shadow-sm hover:shadow-md transition-shadow",
          "focus:outline-none focus:ring-2 focus:ring-brand-500/30",
          photoCount > 0 && "cursor-pointer",
          className,
        )}
        aria-label={`Comparable: ${title}`}
      >
        <div className="flex">
          {/* ── Left: Hero Image ── */}
          <div className="relative w-[40%] min-h-[120px] bg-stone-100">
            <div className="aspect-[4/3] w-full">
              {hero ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={hero} alt={title} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-stone-300">
                  <ImageIcon className="h-8 w-8" />
                </div>
              )}
            </div>

            {/* Role badge */}
            {role ? (
              <span
                className={cn(
                  "absolute left-2 top-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                  role.bg,
                  role.text,
                  role.border,
                )}
              >
                {comparable.is_selected ? <Check className="h-3 w-3" /> : null}
                {role.label}
              </span>
            ) : null}

            {/* Photo count */}
            {photoCount > 1 ? (
              <span className="absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white">
                <ImageIcon className="h-3 w-3" />
                {photoCount}
              </span>
            ) : null}
          </div>

          {/* ── Right: Info Panel ── */}
          <div className="flex-1 px-3.5 py-3 flex flex-col justify-between min-h-[120px]">
            {/* Price row */}
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-serif text-xl font-semibold text-stone-900 leading-tight">
                    {fmt.price(comparable.sale_price)}
                  </p>
                  <p className="text-[11px] text-stone-500 mt-0.5">
                    {typeof comparable.price_per_sqm === "number"
                      ? `${fmt.price(comparable.price_per_sqm)}/m²`
                      : "—/m²"}
                  </p>
                </div>
                {typeof comparable.distance_km === "number" && Number.isFinite(comparable.distance_km) ? (
                  <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-600 tabular-nums">
                    {comparable.distance_km.toFixed(1)} km
                  </span>
                ) : null}
              </div>

              {/* Specs row */}
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-stone-700">
                {areaM2 ? (
                  <span className="inline-flex items-center gap-1">
                    <Ruler className="h-3.5 w-3.5 text-stone-400" />
                    {fmt.area(areaM2)}
                  </span>
                ) : null}
                {typeof comparable.bedrooms === "number" ? (
                  <span className="inline-flex items-center gap-1">
                    <BedDouble className="h-3.5 w-3.5 text-stone-400" />
                    {fmt.num(comparable.bedrooms)}
                  </span>
                ) : null}
                {typeof comparable.bathrooms === "number" ? (
                  <span className="inline-flex items-center gap-1">
                    <Bath className="h-3.5 w-3.5 text-stone-400" />
                    {fmt.num(comparable.bathrooms)}
                  </span>
                ) : null}
                {comparable.property_type ? (
                  <span className="text-stone-500 capitalize">
                    {String(comparable.property_type).slice(0, 18)}
                  </span>
                ) : null}
              </div>
            </div>

            {/* Location + meta */}
            <div className="mt-2 space-y-1">
              {comparable.address ? (
                <p className="text-[12px] text-stone-500 line-clamp-1 inline-flex items-start gap-1">
                  <MapPin className="mt-0.5 h-3 w-3 text-stone-400 shrink-0" />
                  <span className="capitalize">{String(comparable.address).toLowerCase()}</span>
                </p>
              ) : null}
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[11px] text-stone-400">
                {comparable.construction_year ? (
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {comparable.construction_year}
                  </span>
                ) : null}
                {comparable.energy_rating ? (
                  <span className="inline-flex items-center gap-1">
                    <Zap className="h-3 w-3" />
                    {String(comparable.energy_rating).toUpperCase()}
                  </span>
                ) : null}
                {comparable.condition ? (
                  <span className="capitalize">{String(comparable.condition).toLowerCase().slice(0, 24)}</span>
                ) : null}
              </div>
            </div>

            {/* Feature chips */}
            {chips.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {chips.map((c) => (
                  <span
                    key={c.key}
                    className="rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-[10px] font-medium text-stone-600"
                  >
                    {c.label}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <SwipeGallery
        isOpen={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        images={comparable.photo_urls || []}
        title={title}
      />
    </>
  );
};
