"use client";

/**
 * Confirm Page
 * ============
 * 
 * Beautiful review and confirm scraped property data before saving.
 * Uses the ported ListingReviewMode with Leo.casa branding.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { ListingReviewMode } from "@/components/ListingReviewMode";
import { createListing, extractDomain } from "@/lib/api";
import { type ScrapedData, type ListingCreate } from "@/lib/types";

interface StoredData {
  data: ScrapedData;
  source_url: string;
}

export default function ConfirmPage() {
  const router = useRouter();
  const [storedData, setStoredData] = useState<StoredData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load scraped data from session storage
  useEffect(() => {
    const stored = sessionStorage.getItem("scraped_data");
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as StoredData;
        // Ensure source_url is in the data
        parsed.data.source_url = parsed.source_url;
        setStoredData(parsed);
      } catch (e) {
        console.error("Failed to parse stored data:", e);
        router.push("/");
      }
    } else {
      // No data, redirect to home
      router.push("/");
    }
    setIsLoading(false);
  }, [router]);

  // Handle confirm
  const handleConfirm = async () => {
    if (!storedData) return;

    const data = storedData.data;
    setIsSaving(true);
    setError(null);

    try {
      // Build listing create payload with full schema
      const listingData: ListingCreate = {
        source_url: storedData.source_url,
        source_domain: extractDomain(storedData.source_url),
        title: data.title,
        price_eur: data.price_eur,
        sqm: data.m2_built || (data as any).sqm,
        bedrooms: data.bedrooms,
        bathrooms: data.bathrooms,
        property_type: data.property_subtype || (data as any).property_type,
        floor_level: data.floor_level,
        has_elevator: data.has_elevator,
        address: data.address,
        city: data.city,
        region: data.region,
        description: data.description,
        features: data.features,
        image_urls: data.image_urls || data.photo_urls,
        scraped_data: data as unknown as Record<string, unknown>,
        // Full schema fields
        listing_type: data.listing_type,
        property_subtype: data.property_subtype,
        housing_situation: data.housing_situation,
        m2_built: data.m2_built,
        m2_useful: data.m2_useful,
        lat: data.lat,
        lng: data.lng,
        floor_number: data.floor_number,
        condition: data.condition,
        is_exterior: data.is_exterior,
        has_terrace: data.has_terrace,
        has_balcony: data.has_balcony,
        has_pool: data.has_pool,
        has_garage: data.has_garage,
        has_garden: data.has_garden,
        has_air_conditioning: data.has_air_conditioning,
        has_wardrobes: data.has_wardrobes,
        is_accessible: data.is_accessible,
        has_storage: data.has_storage,
      };

      const result = await createListing(listingData);

      if (result.success && result.data) {
        // Clear session storage
        sessionStorage.removeItem("scraped_data");

        // Navigate to listing page
        router.push(`/listing/${result.data.id}`);
      } else {
        setError((result as any).error || "Failed to save listing");
      }
    } catch (e) {
      console.error("Save error:", e);
      setError("Failed to save listing. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  // Handle cancel
  const handleCancel = () => {
    sessionStorage.removeItem("scraped_data");
    router.push("/");
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7]">
        <Loader2 className="w-8 h-8 animate-spin text-[#da654d]" />
      </div>
    );
  }

  // No data state
  if (!storedData) {
    return null; // Will redirect
  }

  // Transform image URLs to photo objects
  const photos = (storedData.data.image_urls || storedData.data.photo_urls || []).map((url: string) => ({
    url,
    label: '',
  }));

  return (
    <>
      <ListingReviewMode
        data={storedData.data}
        photos={photos}
        onCancel={handleCancel}
        onConfirm={handleConfirm}
        isSubmitting={isSaving}
      />

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-24 left-4 right-4 mx-auto max-w-lg z-50">
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm shadow-lg">
            {error}
          </div>
        </div>
      )}
    </>
  );
}