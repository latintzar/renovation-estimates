"use client";

/**
 * ComparablesMap Component
 * ========================
 *
 * Full-bleed Mapbox map showing the target listing and comparable properties.
 * - Target: large pulsing marker with label
 * - Selected comparable (reference): highlighted marker
 * - Other comparables: price-pill markers
 * - Clicking a marker overlays a ComparableCard at the bottom
 *
 * No card wrapper — intended to fill available space edge-to-edge.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { ChevronLeft, ChevronRight, Layers, LocateFixed, Satellite, Sun, X, Map as MapIconLucide } from "lucide-react";
import { cn } from "@/lib/utils";
import { ComparableCard, type ComparableForUi } from "./ComparableCard";
import { useAppStrings } from "@/hooks/AppStringsContext";

const MAPBOX_TOKEN =
  process.env.NEXT_PUBLIC_MAPBOX_TOKEN ||
  "";

type MapStyle = "streets" | "satellite" | "light";
const MAP_STYLES: Record<MapStyle, { url: string; icon: typeof MapIconLucide; label: string }> = {
  streets: { url: "mapbox://styles/mapbox/streets-v12", icon: MapIconLucide, label: "Map" },
  satellite: { url: "mapbox://styles/mapbox/satellite-streets-v12", icon: Satellite, label: "Satellite" },
  light: { url: "mapbox://styles/mapbox/light-v11", icon: Sun, label: "Light" },
};

type Coordinates = { latitude: number; longitude: number };

type MapLabels = {
  yourListing?: string;
  target?: string;
  selected?: string;
  comp?: string;
};

type ComparablesMapProps = {
  target: { lat: number; lng: number; title?: string | null; address?: string | null };
  comparables: ComparableForUi[];
  className?: string;
  /** i18n labels — defaults to English if not provided */
  labels?: MapLabels;
};

const hasValidCoords = (coords: Coordinates | null | undefined): coords is Coordinates =>
  !!coords &&
  Number.isFinite(Number(coords.latitude)) &&
  Number.isFinite(Number(coords.longitude)) &&
  Math.abs(Number(coords.latitude)) <= 90 &&
  Math.abs(Number(coords.longitude)) <= 180;

const formatPriceShort = (price: number | null | undefined): string => {
  if (typeof price !== "number" || !Number.isFinite(price)) return "—";
  const k = Math.round(price / 1000);
  return `€${k}k`;
};

/* Accent colour */
const ACCENT = "#da654d";

export const ComparablesMap: React.FC<ComparablesMapProps> = ({ target, comparables, className, labels }) => {
  const { s } = useAppStrings();
  const yourListingLabel = labels?.yourListing || s.mapYourListing;
  const targetLabel = labels?.target || s.mapTarget;
  const referenceLabel = s.compReference; // Matches the badge text on cards
  const compLabel = labels?.comp || s.mapComp;
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const targetMarkerRef = useRef<mapboxgl.Marker | null>(null);

  const [mapStyle, setMapStyle] = useState<MapStyle>("streets");
  const [showLayerMenu, setShowLayerMenu] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const touchStartX = useRef<number | null>(null);

  const mapPoints = useMemo(
    () => (Array.isArray(comparables) ? comparables : []).filter((c) => hasValidCoords(c.coordinates as Coordinates)),
    [comparables],
  );

  const selected = selectedIdx !== null ? mapPoints[selectedIdx] ?? null : null;

  const selectByComparable = useCallback(
    (c: ComparableForUi) => {
      const idx = mapPoints.findIndex((mp) => mp === c || (mp.casafari_property_id && mp.casafari_property_id === c.casafari_property_id));
      setSelectedIdx(idx >= 0 ? idx : null);
    },
    [mapPoints],
  );

  const goPrev = useCallback(() => {
    if (mapPoints.length === 0) return;
    setSelectedIdx((i) => {
      const next = i !== null ? (i - 1 + mapPoints.length) % mapPoints.length : 0;
      const c = mapPoints[next];
      const coords = c?.coordinates as Coordinates | null | undefined;
      if (coords && hasValidCoords(coords)) {
        mapRef.current?.easeTo({ center: [coords.longitude, coords.latitude], duration: 400 });
      }
      return next;
    });
  }, [mapPoints]);

  const goNext = useCallback(() => {
    if (mapPoints.length === 0) return;
    setSelectedIdx((i) => {
      const next = i !== null ? (i + 1) % mapPoints.length : 0;
      const c = mapPoints[next];
      const coords = c?.coordinates as Coordinates | null | undefined;
      if (coords && hasValidCoords(coords)) {
        mapRef.current?.easeTo({ center: [coords.longitude, coords.latitude], duration: 400 });
      }
      return next;
    });
  }, [mapPoints]);

  // Touch swipe handler for the bottom card overlay
  const handleCardTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX; };
  const handleCardTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const diff = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(diff) > 60) {
      if (diff > 0) goPrev();
      else goNext();
    }
    touchStartX.current = null;
  };

  const fitAllCenteredOnTarget = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const tLat = Number(target.lat);
    const tLng = Number(target.lng);
    if (!Number.isFinite(tLat) || !Number.isFinite(tLng)) return;

    let maxLatDelta = 0;
    let maxLngDelta = 0;
    for (const c of mapPoints) {
      const coords = c.coordinates as Coordinates | null | undefined;
      if (!hasValidCoords(coords)) continue;
      maxLatDelta = Math.max(maxLatDelta, Math.abs(coords.latitude - tLat));
      maxLngDelta = Math.max(maxLngDelta, Math.abs(coords.longitude - tLng));
    }

    if (maxLatDelta === 0 && maxLngDelta === 0) {
      map.easeTo({ center: [tLng, tLat], zoom: 14, duration: 600 });
      return;
    }

    const sw: [number, number] = [tLng - maxLngDelta, tLat - maxLatDelta];
    const ne: [number, number] = [tLng + maxLngDelta, tLat + maxLatDelta];
    map.fitBounds([sw, ne], { padding: 60, maxZoom: 15, duration: 700 });
  }, [mapPoints, target.lat, target.lng]);

  const centerTarget = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const tLat = Number(target.lat);
    const tLng = Number(target.lng);
    if (!Number.isFinite(tLat) || !Number.isFinite(tLng)) return;
    map.easeTo({ center: [tLng, tLat], zoom: 14, duration: 600 });
  }, [target.lat, target.lng]);

  // Init map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current || !MAPBOX_TOKEN) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;
    const tLat = Number(target.lat);
    const tLng = Number(target.lng);
    if (!Number.isFinite(tLat) || !Number.isFinite(tLng)) return;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLES[mapStyle].url,
      center: [tLng, tLat],
      zoom: 13.5,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => setIsLoaded(true));

    return () => {
      try { map.remove(); } finally { mapRef.current = null; }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.lat, target.lng]);

  // Update style
  useEffect(() => {
    mapRef.current?.setStyle(MAP_STYLES[mapStyle].url);
  }, [mapStyle]);

  // Render markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isLoaded) return;

    for (const m of markersRef.current) m.remove();
    markersRef.current = [];
    targetMarkerRef.current?.remove();
    targetMarkerRef.current = null;

    const tLat = Number(target.lat);
    const tLng = Number(target.lng);
    if (!Number.isFinite(tLat) || !Number.isFinite(tLng)) return;

    /* ── Target marker: large, pulsing, labelled — highest z-index ── */
    const targetEl = document.createElement("div");
    targetEl.style.zIndex = "10"; // Above all comparable markers
    targetEl.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;pointer-events:none;">
        <div style="
          width:20px; height:20px; border-radius:50%;
          background:${ACCENT}; border:3px solid #fff;
          box-shadow: 0 0 0 6px ${ACCENT}30, 0 2px 8px rgba(0,0,0,0.25);
          animation: targetPulse 2s ease-in-out infinite;
        "></div>
        <div style="
          margin-top:4px; padding:2px 8px; border-radius:10px;
          background:#fff; border:1px solid ${ACCENT}50;
          box-shadow:0 1px 4px rgba(0,0,0,0.12);
          font-size:10px; font-weight:700; color:${ACCENT};
          white-space:nowrap; letter-spacing:0.5px;
        ">${yourListingLabel}</div>
      </div>
    `;
    // Add the pulse animation
    const styleEl = document.createElement("style");
    styleEl.textContent = `
      @keyframes targetPulse {
        0%, 100% { box-shadow: 0 0 0 6px ${ACCENT}30, 0 2px 8px rgba(0,0,0,0.25); }
        50% { box-shadow: 0 0 0 12px ${ACCENT}15, 0 2px 8px rgba(0,0,0,0.25); }
      }
    `;
    document.head.appendChild(styleEl);

    targetMarkerRef.current = new mapboxgl.Marker({ element: targetEl, anchor: "center" })
      .setLngLat([tLng, tLat])
      .addTo(map);

    /* ── Comparable markers ── */
    for (const c of mapPoints) {
      const coords = c.coordinates as Coordinates | null | undefined;
      if (!hasValidCoords(coords)) continue;

      const el = document.createElement("button");
      el.type = "button";
      el.setAttribute("aria-label", `Comparable: ${c.address || "property"}`);

      const isRef = c.comp_role === "reference" || c.is_selected;
      const isAboveBelow = c.comp_role === "above" || c.comp_role === "below";

      // Reference / selected comparable gets brand green + larger
      // Above/Below get dark
      // Others get white
      let bgColor = "#fff";
      let textColor = "#44403c"; // stone-700
      let borderColor = "#e7e5e4"; // stone-200
      let fontSize = "11px";
      let fontWeight = "600";
      let extraLabel = "";

      if (isRef) {
        bgColor = "#16a34a"; // brand-600
        textColor = "#fff";
        borderColor = "#15803d"; // brand-700
        fontSize = "12px";
        fontWeight = "700";
        extraLabel = " ★";
      } else if (isAboveBelow) {
        bgColor = "#1c1917"; // stone-900
        textColor = "#f5f5f4"; // stone-100
        borderColor = "#44403c";
      }

      el.style.cssText = `
        display:inline-flex; align-items:center; gap:2px;
        padding:3px 8px; border-radius:20px;
        background:${bgColor}; color:${textColor};
        border:1.5px solid ${borderColor};
        font-size:${fontSize}; font-weight:${fontWeight};
        box-shadow:0 2px 6px rgba(0,0,0,0.12);
        cursor:pointer; white-space:nowrap;
        transition:transform 0.15s;
      `;
      el.textContent = formatPriceShort(c.sale_price) + extraLabel;
      el.onmouseenter = () => { el.style.transform = "scale(1.08)"; };
      el.onmouseleave = () => { el.style.transform = "scale(1)"; };
      el.onclick = () => {
        selectByComparable(c);
        map.easeTo({ center: [coords.longitude, coords.latitude], duration: 400 });
      };

      const marker = new mapboxgl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([coords.longitude, coords.latitude])
        .addTo(map);
      markersRef.current.push(marker);
    }

    fitAllCenteredOnTarget();
  }, [fitAllCenteredOnTarget, isLoaded, mapPoints, selectByComparable, target.lat, target.lng, target.title, yourListingLabel]);

  return (
    <div className={cn("relative w-full", className)}>
      {/* Map fills parent — no card/border wrapper */}
      <div ref={mapContainerRef} className="w-full h-full min-h-[60vh]" />
      {!MAPBOX_TOKEN && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-neutral-100 p-8 text-center text-sm text-neutral-600">
          Set NEXT_PUBLIC_MAPBOX_TOKEN to show the map.
        </div>
      )}

      {/* Floating controls — top-left */}
      <div className="absolute top-3 left-3 flex items-center gap-2 z-10">
        <button
          type="button"
          onClick={centerTarget}
          className="inline-flex items-center gap-1.5 rounded-full bg-white/95 backdrop-blur-sm px-3 py-2 text-[11px] font-medium text-stone-700 shadow-md border border-stone-200/60 hover:bg-white focus:outline-none"
          aria-label="Center on target"
        >
          <LocateFixed className="h-3.5 w-3.5 text-stone-500" />
          Center
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setShowLayerMenu((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-full bg-white/95 backdrop-blur-sm px-3 py-2 text-[11px] font-medium text-stone-700 shadow-md border border-stone-200/60 hover:bg-white focus:outline-none"
            aria-label="Map layers"
            aria-haspopup="menu"
            aria-expanded={showLayerMenu}
          >
            <Layers className="h-3.5 w-3.5 text-stone-500" />
            Style
          </button>

          {showLayerMenu ? (
            <div
              className="absolute left-0 mt-2 w-36 overflow-hidden rounded-xl border border-stone-200 bg-white shadow-lg z-20"
              role="menu"
            >
              {Object.entries(MAP_STYLES).map(([key, cfg]) => {
                const isActive = mapStyle === (key as MapStyle);
                const Icon = cfg.icon;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => { setMapStyle(key as MapStyle); setShowLayerMenu(false); }}
                    className={cn(
                      "w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-stone-50",
                      isActive && "bg-stone-50 font-medium",
                    )}
                    role="menuitem"
                  >
                    <Icon className="h-4 w-4 text-stone-400" />
                    <span className="text-stone-700">{cfg.label}</span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>

      {/* Legend — bottom-left (shifts up when a comparable card is selected) */}
      <div className={cn(
        "absolute left-3 z-10 flex items-center gap-3 rounded-full bg-white/90 backdrop-blur-sm px-3 py-1.5 shadow-sm border border-stone-200/60 transition-all",
        selected ? "bottom-[240px]" : "bottom-[100px]",
      )}>
        <span className="flex items-center gap-1.5 text-[10px] text-stone-500">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: ACCENT, border: "2px solid #fff", boxShadow: `0 0 0 2px ${ACCENT}40` }} />
          {targetLabel}
        </span>
        <span className="flex items-center gap-1.5 text-[10px] text-stone-500">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-600 border-2 border-white shadow-sm" />
          {referenceLabel}
        </span>
        <span className="flex items-center gap-1.5 text-[10px] text-stone-500">
          <span className="w-2.5 h-2.5 rounded-full bg-stone-900 border-2 border-white shadow-sm" />
          {compLabel}
        </span>
      </div>

      {/* Selected comparable overlay — sits above the footer + reforma hero button */}
      {selected ? (
        <div
          className="absolute left-0 right-0 bottom-[100px] p-3 z-10"
          onTouchStart={handleCardTouchStart}
          onTouchEnd={handleCardTouchEnd}
        >
          <div className="relative max-w-lg mx-auto">
            {/* Close button */}
            <button
              type="button"
              onClick={() => setSelectedIdx(null)}
              className="absolute -right-1 -top-3 z-20 rounded-full bg-white p-1.5 text-stone-500 shadow-md hover:bg-stone-50 focus:outline-none"
              aria-label={s.close}
            >
              <X className="h-4 w-4" />
            </button>

            {/* Prev/Next navigation */}
            {mapPoints.length > 1 ? (
              <>
                <button
                  type="button"
                  onClick={goPrev}
                  className="absolute -left-1 top-1/2 -translate-y-1/2 z-20 rounded-full bg-white p-1.5 text-stone-500 shadow-md hover:bg-stone-50 focus:outline-none"
                  aria-label={s.prevImage}
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={goNext}
                  className="absolute -right-1 top-1/2 -translate-y-1/2 z-20 rounded-full bg-white p-1.5 text-stone-500 shadow-md hover:bg-stone-50 focus:outline-none"
                  aria-label={s.nextImage}
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </>
            ) : null}

            {/* Counter pill */}
            {mapPoints.length > 1 ? (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-20 bg-stone-800 text-white text-[10px] font-medium px-2.5 py-0.5 rounded-full tabular-nums shadow-md">
                {(selectedIdx ?? 0) + 1} / {mapPoints.length}
              </div>
            ) : null}

            <ComparableCard
              comparable={selected}
              className="shadow-xl border-stone-300"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
};
