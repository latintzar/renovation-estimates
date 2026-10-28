"use client";

/**
 * ComparablesTab Component
 * ========================
 *
 * Container for the "Comparables" tab. Fetches comparable data,
 * provides list/map toggle, and renders content.
 *
 * In MAP mode: full-bleed (breaks out of px padding), stretches to bottom nav.
 * In LIST mode: normal padded layout with cards.
 */

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { LayoutList, Loader2, Map as MapIcon, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { ComparableCard, type ComparableForUi } from "./ComparableCard";
import { useAppStrings } from "@/hooks/AppStringsContext";

const LazyComparablesMap = dynamic(
  () => import("./ComparablesMap").then((m) => m.ComparablesMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-[60vh] bg-stone-50">
        <div className="text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-stone-400" />
          <p className="mt-2 text-sm text-stone-400">Loading map…</p>{/* fallback during dynamic import */}
        </div>
      </div>
    ),
  },
);

type ComparablesApiResponse = {
  success: boolean;
  error?: string;
  hasCoordinates?: boolean;
  target?: { id: number; title: string; address: string | null; lat: number; lng: number };
  comparables?: ComparableForUi[];
};

type ViewMode = "list" | "map";

type MapLabels = {
  yourListing?: string;
  target?: string;
  selected?: string;
  comp?: string;
};

type ComparablesTabProps = {
  listingId: number;
  isActive: boolean;
  className?: string;
  /** i18n labels for the map markers and legend */
  mapLabels?: MapLabels;
};

export const ComparablesTab: React.FC<ComparablesTabProps> = ({ listingId, isActive, className, mapLabels }) => {
  const { s } = useAppStrings();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ComparablesApiResponse | null>(null);

  useEffect(() => {
    if (!isActive || !listingId || data?.success) return;

    const run = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const resp = await fetch(`/api/listings/${listingId}/comparables`, { cache: "no-store" });
        const json = (await resp.json()) as ComparablesApiResponse;
        if (!json?.success) {
          setError(json?.error || s.failedLoadComps);
          setData(null);
          return;
        }
        setData(json);
      } catch {
        setError(s.failedLoadComps);
        setData(null);
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [data?.success, isActive, listingId]);

  const comparables = useMemo(() => {
    const comps = Array.isArray(data?.comparables) ? data?.comparables : [];
    const score = (c: ComparableForUi) => {
      if (c.comp_role === "reference") return 0;
      if (c.comp_role === "below") return 1;
      if (c.comp_role === "above") return 2;
      return 3;
    };
    return [...comps].sort((a, b) => {
      const s = score(a) - score(b);
      if (s !== 0) return s;
      const da = typeof a.distance_km === "number" ? a.distance_km : 999;
      const db = typeof b.distance_km === "number" ? b.distance_km : 999;
      return da - db;
    });
  }, [data?.comparables]);

  const hasCoordinates = Boolean(data?.hasCoordinates) && data?.target != null;
  const mapDisabled = !hasCoordinates;
  const isMapView = viewMode === "map" && !mapDisabled;

  return (
    <div className={className}>
      {/* Header + toggle — always visible inside the padded area */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-[11px] text-stone-400 mt-0.5">
            {comparables.length > 0
              ? `${comparables.length} ${comparables.length === 1 ? s.comparableFound : s.comparablesFound}`
              : s.recentlySold}
          </p>
        </div>

        <div className="inline-flex rounded-full border border-stone-200 bg-white p-0.5 shadow-sm">
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-medium transition-all",
              viewMode === "list"
                ? "bg-stone-900 text-white shadow-sm"
                : "text-stone-500 hover:text-stone-700",
            )}
            aria-label={s.listView}
            tabIndex={0}
          >
            <LayoutList className="h-3.5 w-3.5" />
            {s.listView}
          </button>
          <button
            type="button"
            onClick={() => setViewMode("map")}
            disabled={mapDisabled}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-medium transition-all",
              mapDisabled
                ? "text-stone-300 cursor-not-allowed"
                : viewMode === "map"
                  ? "bg-stone-900 text-white shadow-sm"
                  : "text-stone-500 hover:text-stone-700",
            )}
            aria-label={s.mapView}
            title={mapDisabled ? s.mapRequiresCoords : undefined}
            tabIndex={0}
          >
            <MapIcon className="h-3.5 w-3.5" />
            {s.mapView}
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-stone-400" />
          <p className="mt-3 text-sm text-stone-500">{s.loadingComparables}</p>
        </div>
      ) : null}

      {/* Error */}
      {!isLoading && error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50/50 p-5 text-center">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      ) : null}

      {/* Not yet loaded */}
      {!isLoading && !error && !data?.success ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
          <Search className="mx-auto h-7 w-7 text-stone-300" />
          <p className="mt-3 text-sm text-stone-500">{s.openTabToLoad}</p>
        </div>
      ) : null}

      {/* Content */}
      {!isLoading && !error && data?.success ? (
        <>
          {isMapView ? (
            /* Map: break out of padded container for full bleed, stretch to top of footer.
               Offset: sticky header (~56px) + pt-6 (24px) + subtitle row (~28px) + mb-3 (12px) ≈ 120px.
               The footer is fixed at bottom; the map goes behind it (opaque white covers it).
               Using 100dvh for proper mobile viewport handling. */
            <div className="-mx-4 -mb-20" style={{ height: "calc(100dvh - 120px)" }}>
              <LazyComparablesMap
                target={data.target!}
                comparables={comparables}
                className="h-full"
                labels={mapLabels}
              />
            </div>
          ) : (
            /* List view */
            <div className="space-y-3 pb-2">
              {comparables.length > 0 ? (
                comparables.map((c, idx) => (
                  <ComparableCard
                    key={`${String(c.casafari_property_id || c.id || idx)}`}
                    comparable={c}
                  />
                ))
              ) : (
                <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
                  <Search className="mx-auto h-7 w-7 text-stone-300" />
                  <p className="mt-3 text-sm text-stone-500">{s.noComparablesFound}</p>
                </div>
              )}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
};
