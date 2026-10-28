"use client";

/**
 * Listing Page
 * ============
 * 
 * Full property detail view using the same UI as the confirm page.
 * Reuses ListingReviewMode in view-only mode.
 * 
 * Multi-language support: EN, ES, DE, FR, CA (Catalan), IT
 */

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, ArrowLeft, Share2 } from "lucide-react";
import { ListingReviewMode, ListingBottomNav, LanguageToggle, type ListingTab } from "@/components";
import { getListing, getListingPhotos } from "@/lib/api";
import { type Listing, type ScrapedData } from "@/lib/types";
import { ComparablesCard, ComparablesTab, ShareModal } from "@/components/renovation";
import { useAppStrings } from "@/hooks/AppStringsContext";
import { preloadTranslations } from "@/hooks/useTranslation";

export default function ListingPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const [listing, setListing] = useState<Listing | null>(null);
  const [photos, setPhotos] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Tab navigation state
  const [activeTab, setActiveTab] = useState<ListingTab>("renovation");

  // Share modal state (used by the share button in renovation header)
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareEli5Summary, setShareEli5Summary] = useState<any | null>(null);
  const [shareEli5Address, setShareEli5Address] = useState<string | null>(null);

  const handleRenoDataReady = useCallback((data: { eli5Summary: any | null; address: string | null }) => {
    setShareEli5Summary(data.eli5Summary);
    setShareEli5Address(data.address);
  }, []);
  
  // Centralized translation — all UI strings from context
  const { s: uiStrings, language, translateListing, isTranslating, isSourceLanguage } = useAppStrings();
  const [translatedContent, setTranslatedContent] = useState<{
    title?: string;
    description?: string;
  }>({});

  const listingId = Number(params.id);
  const isContractorView = searchParams.get("view") === "contractor";

  // Load listing data
  useEffect(() => {
    if (!listingId) return;

    const loadListing = async () => {
      setIsLoading(true);
      try {
        const result = await getListing(listingId);
        if (result.success && result.data) {
          setListing(result.data);
          
          // Load photos
          const photosResult = await getListingPhotos(listingId);
          if (photosResult.success && photosResult.data) {
            setPhotos(photosResult.data);
          } else if (result.data.photos) {
            // Fallback to photos from listing
            setPhotos(result.data.photos);
          }
        } else {
          setError((result as any).error || "Anuncio no encontrado");
        }
      } catch (e) {
        console.error("Load error:", e);
        setError("Error al cargar el anuncio");
      } finally {
        setIsLoading(false);
      }
    };

    loadListing();
  }, [listingId]);

  // Pre-load pipeline-computed translations into the global cache, then translate.
  // If pre-computed translations exist (from the v5_translations pipeline stage),
  // they'll be available instantly via the cache — no on-demand API calls needed.
  useEffect(() => {
    if (!listing || language === 'es') {
      setTranslatedContent({
        title: listing?.title,
        description: listing?.description,
      });
      return;
    }

    const doTranslate = async () => {
      // Try to preload pipeline-computed translations into the global cache first.
      // This is a single fast DB read. If available, translateListing will find
      // everything in cache and return instantly.
      await preloadTranslations(listingId, language);

      const result = await translateListing({
        title: listing.title,
        description: listing.description,
      });
      setTranslatedContent({
        title: result.title,
        description: result.description,
      });
    };

    doTranslate();
  }, [listing, language, listingId, translateListing]);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7]">
        <Loader2 className="w-8 h-8 animate-spin text-[#da654d]" />
      </div>
    );
  }

  // Error state
  if (error || !listing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-[#FDFBF7]">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <h1 className="text-xl font-semibold text-stone-900 mb-2">
          {error || uiStrings.listingNotFound}
        </h1>
        <Link
          href="/"
          className="text-[#da654d] hover:text-[#c8553d] flex items-center gap-1"
        >
          <ArrowLeft className="w-4 h-4" />
          {uiStrings.backToHome}
        </Link>
      </div>
    );
  }

  // Convert listing to ScrapedData format for ListingReviewMode
  // Map ALL available fields from the database
  // Use translated content when available
  const scrapedData = {
    title: translatedContent.title || listing.title,
    description: translatedContent.description || listing.description,
    price: listing.price_eur,  // ListingReviewMode expects 'price'
    price_eur: listing.price_eur,
    bedrooms: listing.bedrooms,
    bathrooms: listing.bathrooms,
    m2_built: listing.m2_built || listing.sqm,
    m2_useful: listing.m2_useful,
    address: listing.address,
    neighborhood: listing.neighborhood,
    city: listing.city,
    region: listing.region,
    country: listing.country,
    lat: listing.lat,
    lng: listing.lng,
    property_subtype: listing.property_subtype,
    condition: listing.condition,
    floor_level: listing.floor_level,
    floor_number: listing.floor_number,
    has_elevator: listing.has_elevator,
    is_exterior: listing.is_exterior,
    has_terrace: listing.has_terrace,
    has_balcony: listing.has_balcony,
    has_pool: listing.has_pool,
    has_garage: listing.has_garage,
    has_garden: listing.has_garden,
    has_storage: listing.has_storage,
    has_air_conditioning: listing.has_air_conditioning,
    source_url: listing.source_url,
    image_urls: photos,
  } as ScrapedData;

  // Convert photos to PhotoData format
  const photoData = photos.map(url => ({ url, label: '' }));

  return (
    <>
      {/* Translation indicator */}
      {isTranslating && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-lg border border-stone-200 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-[#da654d]" />
          <span className="text-sm text-stone-600">{uiStrings.translating}</span>
        </div>
      )}

      {/* ========== LISTING TAB ========== */}
      {/* PRELOADED: All tabs mounted on page load, CSS controls visibility */}
      <div className={activeTab === "listing" ? "block" : "hidden"}>
        <ListingReviewMode
          data={scrapedData}
          photos={photoData}
          viewMode={true}
          headerRight={<LanguageToggle compact />}
        />
      </div>

      {/* ========== RENOVATION TAB ========== */}
      {/* PRELOADED: Data fetches immediately on page load */}
      <div className={activeTab === "renovation" ? "block" : "hidden"}>
        {/* Header for renovation tab */}
        <header className="sticky top-0 z-30 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-100">
          <div className="max-w-lg mx-auto px-4 py-4">
            <div className="relative flex items-center justify-center min-h-[28px]">
              <span className="font-serif text-lg font-medium text-stone-900">
                {uiStrings.reforma}
              </span>
              {/* Language toggle + Share — absolute right for true centering */}
              <div className="absolute right-0 flex items-center gap-1">
                <LanguageToggle compact />
                <div className="relative">
                  <button
                    onClick={() => setShareModalOpen(true)}
                    className="p-1 text-stone-400 hover:text-stone-700 rounded-full"
                    aria-label={uiStrings.share}
                    aria-haspopup="dialog"
                  >
                    <Share2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>
        
        <div className="bg-[#FDFBF7] px-4 pb-20 pt-6">
          <div className="max-w-lg mx-auto space-y-4">
            {/* ========== RENOVATION PACKAGES ========== */}
            <ComparablesCard
              listingId={listingId}
              onBack={() => setActiveTab("listing")}
              isContractorView={isContractorView}
              onDataReady={handleRenoDataReady}
            />
          </div>
        </div>
      </div>

      {/* ========== COMPARABLES TAB ========== */}
      {/* LAZY: ComparablesTab only fetches when active */}
      <div className={activeTab === "comparables" ? "block" : "hidden"}>
        <header className="sticky top-0 z-30 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-100">
          <div className="max-w-lg mx-auto px-4 py-4">
            <div className="relative flex items-center justify-center min-h-[28px]">
              <span className="font-serif text-lg font-medium text-stone-900">
                {uiStrings.comps ?? "Comparables"}
              </span>
              <div className="absolute right-0">
                <LanguageToggle compact />
              </div>
            </div>
          </div>
        </header>

        <div className="bg-[#FDFBF7] px-4 pb-20 pt-6">
          <div className="max-w-lg mx-auto">
            <ComparablesTab
              listingId={listingId}
              isActive={activeTab === "comparables"}
              mapLabels={{
                yourListing: uiStrings.mapYourListing,
                target: uiStrings.mapTarget,
                selected: uiStrings.mapSelected,
                comp: uiStrings.mapComp,
              }}
            />
          </div>
        </div>
      </div>

      <ShareModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        listingId={listingId}
        address={shareEli5Address ?? listing.address ?? undefined}
        eli5={shareEli5Summary}
        isContractorView={isContractorView}
      />

      {/* Tab Navigation */}
      <ListingBottomNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        labels={{ renovation: uiStrings.reforma, comparables: uiStrings.comps, listing: uiStrings.listing }}
      />
    </>
  );
}
