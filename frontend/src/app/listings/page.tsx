"use client";

/**
 * Listings Page - app.leo.casa/listings
 * ======================================
 * 
 * Property feed with full-screen paste modal for adding new listings.
 * When a new listing is added, the V5 pipeline auto-triggers (including comparables).
 * This is the primary "home" for the app.
 */

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { PropertyCard, PropertyCardSkeleton, PasteLinkModal } from "@/components";
import { getListings, scrapeUrl, createListing } from "@/lib/api";
import { type Listing, type ScrapedData } from "@/lib/types";
import { useAppStrings, type AppStrings } from "@/hooks/AppStringsContext";

type PipelineState = "idle" | "scraping" | "creating" | "triggering" | "done" | "error";

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [isLoadingListings, setIsLoadingListings] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pipelineState, setPipelineState] = useState<PipelineState>("idle");
  const [error, setError] = useState<string | null>(null);

  // Centralized translation — all strings from AppStringsContext
  const { s } = useAppStrings();

  // Map pipeline states to centralized string keys
  const pipelineLabels: Record<PipelineState, string> = {
    idle: "",
    scraping: s.pipelineScraping,
    creating: s.pipelineCreating,
    triggering: s.pipelineTriggering,
    done: s.pipelineDone,
    error: s.pipelineError,
  };

  // Load existing listings on mount
  useEffect(() => {
    loadListings();
  }, []);

  // Global Cmd/Ctrl+V paste handler for desktop (when modal is closed)
  useEffect(() => {
    const handleGlobalPaste = async (e: KeyboardEvent) => {
      if (!((e.metaKey || e.ctrlKey) && e.key === "v")) return;
      if (isModalOpen) return;
      
      const activeElement = document.activeElement;
      if (activeElement?.tagName === "INPUT" || activeElement?.tagName === "TEXTAREA") return;

      e.preventDefault();
      setIsModalOpen(true);
    };

    window.addEventListener("keydown", handleGlobalPaste);
    return () => window.removeEventListener("keydown", handleGlobalPaste);
  }, [isModalOpen]);

  const loadListings = async () => {
    setIsLoadingListings(true);
    try {
      const result = await getListings();
      if (result.success) {
        setListings(result.data.listings || []);
      }
    } catch (e) {
      console.error("Failed to load listings:", e);
    } finally {
      setIsLoadingListings(false);
    }
  };

  // Handle URL submission — scrape, create listing, auto-trigger pipeline
  const handleUrlSubmit = useCallback(async (url: string) => {
    setPipelineState("scraping");
    setError(null);

    try {
      // Step 1: Scrape
      const result = await scrapeUrl(url);
      if (!result.success || !result.data) {
        throw new Error((result as any).error || "Error al extraer datos del enlace");
      }

      // Step 2: Create listing
      setPipelineState("creating");
      const scrapedData = result.data as ScrapedData;
      const photos = scrapedData.image_urls || scrapedData.photo_urls || [];
      
      const createResult = await createListing({
        title: scrapedData.title || "Propiedad sin título",
        description: scrapedData.description,
        price_eur: scrapedData.price_eur,
        bedrooms: scrapedData.bedrooms,
        bathrooms: scrapedData.bathrooms,
        m2_built: scrapedData.m2_built,
        m2_useful: scrapedData.m2_useful,
        address: scrapedData.address,
        city: scrapedData.city,
        neighborhood: scrapedData.neighborhood,
        lat: scrapedData.lat,
        lng: scrapedData.lng,
        property_subtype: scrapedData.property_subtype,
        condition: scrapedData.condition,
        floor_level: scrapedData.floor_level,
        floor_number: scrapedData.floor_number,
        has_elevator: scrapedData.has_elevator,
        is_exterior: scrapedData.is_exterior,
        has_terrace: scrapedData.has_terrace,
        has_balcony: scrapedData.has_balcony,
        has_pool: scrapedData.has_pool,
        has_garage: scrapedData.has_garage,
        has_garden: scrapedData.has_garden,
        has_storage: scrapedData.has_storage,
        has_air_conditioning: scrapedData.has_air_conditioning,
        source_url: url,
        image_urls: photos,
        scraped_data: scrapedData as unknown as Record<string, unknown>,
      });

      if (!createResult.success || !createResult.data) {
        throw new Error((createResult as any).error || "Error al crear el anuncio");
      }

      const listingId = createResult.data.id;

      // Step 3: Auto-trigger the V5 pipeline (including comparables)
      setPipelineState("triggering");
      try {
        const pipelineResult = await fetch(`/api/listings/${listingId}/run-pipeline`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const pipelineData = await pipelineResult.json();
        
        if (!pipelineData.success) {
          console.warn("Pipeline trigger warning:", pipelineData.error);
          // Don't fail — listing was created. Pipeline can be retried.
        }
      } catch (pipelineError) {
        console.warn("Pipeline trigger failed (listing still created):", pipelineError);
        // Non-fatal: listing exists, pipeline can be retried from the detail page
      }

      // Step 4: Done — navigate to listing
      setPipelineState("done");
      setIsModalOpen(false);
      router.push(`/listing/${listingId}`);
      
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error al procesar el enlace. Inténtalo de nuevo.";
      setPipelineState("error");
      setError(msg);
      console.error("Submit error:", e);
    }
  }, [router]);

  const isProcessing = ["scraping", "creating", "triggering"].includes(pipelineState);

  return (
    <div className="min-h-screen bg-[#FDFBF7] pb-20">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-100">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <span className="font-serif text-xl font-medium tracking-tight text-stone-900">
              Leo.casa
            </span>
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-sm font-medium transition-colors"
              aria-label={s.addProperty}
              tabIndex={0}
            >
              <Sparkles className="w-4 h-4" />
              {s.addProperty}
            </button>
          </div>
        </div>
      </header>

      {/* Pipeline Progress Toast (shows during processing) */}
      {isProcessing && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-stone-900 text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 animate-slide-in">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm font-medium">{pipelineLabels[pipelineState]}</span>
        </div>
      )}

      {/* Property Feed */}
      <section className="px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {/* Section Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-medium text-stone-900">
              {s.yourProperties}
            </h2>
            {listings.length > 0 && (
              <span className="text-sm text-stone-500">
                {listings.length} {s.saved}
              </span>
            )}
          </div>

          {/* Listings Grid */}
          {isLoadingListings ? (
            <div className="space-y-4">
              <PropertyCardSkeleton />
              <PropertyCardSkeleton />
            </div>
          ) : listings.length > 0 ? (
            <div className="space-y-4">
              {listings.map((listing, i) => (
                <PropertyCard
                  key={listing.id}
                  listing={listing}
                  className={`animate-slide-in stagger-${Math.min(i + 1, 5)}`}
                />
              ))}
            </div>
          ) : (
            <EmptyState onAdd={() => setIsModalOpen(true)} strings={s} />
          )}
        </div>
      </section>

      {/* Paste Link Modal */}
      <PasteLinkModal
        isOpen={isModalOpen}
        onClose={() => {
          if (!isProcessing) {
            setIsModalOpen(false);
            setError(null);
            setPipelineState("idle");
          }
        }}
        onSubmit={handleUrlSubmit}
        isLoading={isProcessing}
        error={error}
      />
    </div>
  );
}

// Empty State Component
function EmptyState({ onAdd, strings }: { onAdd: () => void; strings: AppStrings }) {
  return (
    <div className="text-center py-16 px-4">
      <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-stone-100 flex items-center justify-center">
        <Sparkles className="w-7 h-7 text-stone-400" />
      </div>
      <h3 className="font-serif text-lg font-medium text-stone-900 mb-2">
        {strings.noProperties}
      </h3>
      <p className="text-stone-500 text-sm max-w-xs mx-auto leading-relaxed mb-6">
        {strings.emptyDesc}
      </p>
      <button
        onClick={onAdd}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-stone-900 hover:bg-stone-800 text-white rounded-xl font-medium transition-colors"
        aria-label={strings.addProperty}
        tabIndex={0}
      >
        <Sparkles className="w-4 h-4" />
        {strings.addProperty}
      </button>
      <p className="text-stone-400 text-xs mt-4">
        {strings.pasteHint} <kbd className="px-1.5 py-0.5 bg-stone-100 rounded text-stone-500 font-mono text-[10px]">Ctrl+V</kbd> {strings.pasteAnywhere}
      </p>
    </div>
  );
}
