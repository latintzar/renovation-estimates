"use client";

/**
 * ComparableDetailModal
 * =====================
 *
 * Full-screen modal displaying a comparable property in a listing-page style.
 * Supports left/right navigation between all comparables.
 *
 * Layout:
 *   - Sticky header with close + prev/next
 *   - Photo carousel
 *   - Price + specs hero
 *   - Address + metadata
 *   - Feature chips
 */

import React, { useCallback, useEffect, useState, useRef } from "react";
import {
  Bath,
  BedDouble,
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
  MapPin,
  Ruler,
  X,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStrings } from "@/hooks/AppStringsContext";
import type { ComparableForUi, ComparableFeatures } from "./ComparableCard";

/* ─── Helpers ──────────────────────────────────────── */

const eur = (v: number | null | undefined): string => {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
};

const fmtArea = (m2: number | null | undefined): string => {
  if (typeof m2 !== "number" || !Number.isFinite(m2) || m2 <= 0) return "—";
  return `${Math.round(m2)} m²`;
};

/* ─── Types ────────────────────────────────────────── */

type ComparableDetailModalProps = {
  isOpen: boolean;
  onClose: () => void;
  comparables: ComparableForUi[];
  initialIndex: number;
};

/* ─── Component ────────────────────────────────────── */

export const ComparableDetailModal: React.FC<ComparableDetailModalProps> = ({
  isOpen,
  onClose,
  comparables,
  initialIndex,
}) => {
  const { s } = useAppStrings();
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [photoIndex, setPhotoIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);

  // Reset photo when comparable changes
  useEffect(() => { setPhotoIndex(0); }, [currentIndex]);

  // Sync initialIndex when modal opens
  useEffect(() => { if (isOpen) setCurrentIndex(initialIndex); }, [isOpen, initialIndex]);

  // Lock body scroll
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    if (e.key === "ArrowLeft") setCurrentIndex((i) => (i - 1 + comparables.length) % comparables.length);
    if (e.key === "ArrowRight") setCurrentIndex((i) => (i + 1) % comparables.length);
  }, [onClose, comparables.length]);

  useEffect(() => {
    if (!isOpen) return;
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen || comparables.length === 0) return null;

  const comp = comparables[currentIndex];
  if (!comp) return null;

  const photos = Array.isArray(comp.photo_urls) ? comp.photo_urls.filter(Boolean) : [];
  const area = comp.total_area || comp.living_area || null;
  const title = comp.address ? String(comp.address).trim() : s.compProperty;
  const isRef = comp.comp_role === "reference" || comp.is_selected;
  const canNav = comparables.length > 1;

  const goPrev = () => setCurrentIndex((i) => (i - 1 + comparables.length) % comparables.length);
  const goNext = () => setCurrentIndex((i) => (i + 1) % comparables.length);

  // Touch swipe for the whole modal
  const handleTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX; };
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const diff = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(diff) > 60) {
      if (diff > 0) goPrev();
      else goNext();
    }
    touchStartX.current = null;
  };

  // Feature chips
  const features = comp.features;
  const chips: { key: string; label: string }[] = [];
  if (features) {
    if (features.elevator) chips.push({ key: "elevator", label: s.compElevator });
    if (features.balcony) chips.push({ key: "balcony", label: s.compBalcony });
    if (features.terrace) chips.push({ key: "terrace", label: s.compTerrace });
    if (features.parking) chips.push({ key: "parking", label: s.compParking });
    if (features.pool) chips.push({ key: "pool", label: s.compPool });
    if (features.storage) chips.push({ key: "storage", label: s.compStorage });
    if (features.air_conditioning) chips.push({ key: "ac", label: s.compAC });
    if (features.heating) chips.push({ key: "heating", label: String(features.heating).slice(0, 30) });
  }

  return (
    <div
      className="fixed inset-0 z-[70] bg-[#FDFBF7] overflow-y-auto"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* ── Sticky Header ── */}
      <header className="sticky top-0 z-10 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-200/60">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          {/* Prev */}
          {canNav ? (
            <button
              onClick={goPrev}
              className="p-2 -ml-2 text-stone-400 hover:text-stone-700 rounded-full transition-colors"
              aria-label={s.prevImage}
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          ) : <div className="w-9" />}

          {/* Title + counter */}
          <div className="text-center min-w-0 flex-1">
            <span className="font-serif text-base font-medium text-stone-900 block truncate">
              {isRef ? s.compReference : s.compProperty}
            </span>
            {canNav ? (
              <span className="text-[10px] text-stone-400 tabular-nums">
                {currentIndex + 1} / {comparables.length}
              </span>
            ) : null}
          </div>

          {/* Next / Close */}
          <div className="flex items-center gap-1">
            {canNav ? (
              <button
                onClick={goNext}
                className="p-2 text-stone-400 hover:text-stone-700 rounded-full transition-colors"
                aria-label={s.nextImage}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : null}
            <button
              onClick={onClose}
              className="p-2 -mr-2 text-stone-400 hover:text-stone-700 rounded-full transition-colors"
              aria-label={s.close}
              tabIndex={0}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto pb-16">
        {/* ── Photo Carousel ── */}
        {photos.length > 0 ? (
          <div className="relative">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photos[photoIndex % photos.length]}
              alt={title}
              className="w-full aspect-[4/3] object-cover"
            />

            {/* Photo nav */}
            {photos.length > 1 ? (
              <>
                <button
                  onClick={() => setPhotoIndex((i) => (i - 1 + photos.length) % photos.length)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60"
                  aria-label={s.prevImage}
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setPhotoIndex((i) => (i + 1) % photos.length)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60"
                  aria-label={s.nextImage}
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
                <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
                  {photos.slice(0, 8).map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setPhotoIndex(i)}
                      className={cn(
                        "w-1.5 h-1.5 rounded-full transition-all",
                        i === (photoIndex % photos.length) ? "bg-white w-4" : "bg-white/50",
                      )}
                    />
                  ))}
                  {photos.length > 8 ? <span className="text-[10px] text-white/60">+{photos.length - 8}</span> : null}
                </div>
              </>
            ) : null}

            {/* Role badge */}
            {isRef ? (
              <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-brand-600 border border-brand-700 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-white">
                <Check className="h-3 w-3" />
                {s.compReference}
              </span>
            ) : comp.comp_role === "above" || comp.comp_role === "below" ? (
              <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-stone-800 border border-stone-700 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-stone-100">
                {comp.comp_role === "above" ? s.compAbove : s.compBelow}
              </span>
            ) : null}
          </div>
        ) : (
          <div className="w-full aspect-[4/3] bg-stone-100 flex items-center justify-center">
            <ImageIcon className="w-12 h-12 text-stone-300" />
          </div>
        )}

        {/* ── Price Hero ── */}
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-serif text-3xl font-bold text-stone-900">{eur(comp.sale_price)}</p>
              <p className="text-sm text-stone-500 mt-0.5">
                {typeof comp.price_per_sqm === "number" ? `${eur(comp.price_per_sqm)}/m²` : ""}
              </p>
            </div>
            {typeof comp.distance_km === "number" && Number.isFinite(comp.distance_km) ? (
              <span className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-sm font-medium text-stone-600 tabular-nums">
                {comp.distance_km.toFixed(1)} km
              </span>
            ) : null}
          </div>
        </div>

        {/* ── Specs Row ── */}
        <div className="px-4 pb-4">
          <div className="flex items-center gap-4 py-3 px-4 bg-white rounded-xl border border-stone-100 shadow-sm">
            {area ? (
              <div className="flex items-center gap-1.5 text-stone-700">
                <Ruler className="h-4 w-4 text-stone-400" />
                <span className="text-sm font-medium">{fmtArea(area)}</span>
              </div>
            ) : null}
            {typeof comp.bedrooms === "number" ? (
              <div className="flex items-center gap-1.5 text-stone-700">
                <BedDouble className="h-4 w-4 text-stone-400" />
                <span className="text-sm font-medium">{comp.bedrooms}</span>
              </div>
            ) : null}
            {typeof comp.bathrooms === "number" ? (
              <div className="flex items-center gap-1.5 text-stone-700">
                <Bath className="h-4 w-4 text-stone-400" />
                <span className="text-sm font-medium">{comp.bathrooms}</span>
              </div>
            ) : null}
            {comp.property_type ? (
              <span className="text-sm text-stone-500 capitalize">{String(comp.property_type).slice(0, 24)}</span>
            ) : null}
          </div>
        </div>

        {/* ── Address ── */}
        {comp.address ? (
          <div className="px-4 pb-3">
            <div className="flex items-start gap-2 text-stone-600">
              <MapPin className="mt-0.5 h-4 w-4 text-stone-400 shrink-0" />
              <span className="text-sm capitalize">{String(comp.address).toLowerCase()}</span>
            </div>
          </div>
        ) : null}

        {/* ── Meta Row ── */}
        <div className="px-4 pb-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-stone-500">
            {comp.construction_year ? (
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-stone-400" />
                {comp.construction_year}
              </span>
            ) : null}
            {comp.energy_rating ? (
              <span className="inline-flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-stone-400" />
                {String(comp.energy_rating).toUpperCase()}
              </span>
            ) : null}
            {comp.condition ? (
              <span className="capitalize">{String(comp.condition).toLowerCase()}</span>
            ) : null}
          </div>
        </div>

        {/* ── Features ── */}
        {chips.length > 0 ? (
          <div className="px-4 pb-4">
            <div className="flex flex-wrap gap-2">
              {chips.map((c) => (
                <span
                  key={c.key}
                  className="rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-600 shadow-sm"
                >
                  {c.label}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {/* ── Swipe hint for mobile ── */}
        {canNav ? (
          <div className="px-4 pt-2 pb-6 text-center">
            <p className="text-[11px] text-stone-400">← {s.slideHint.replace(/[←→]/g, "").trim()} →</p>
          </div>
        ) : null}
      </div>
    </div>
  );
};
