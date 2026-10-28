/**
 * Listing Comparables API
 * =======================
 * GET /api/listings/{id}/comparables
 *
 * Returns the target listing basics + all cached comparables (sold) with enough
 * fields to render useful cards and map pins (including coordinates).
 *
 * Notes:
 * - This is a Supabase REST read using the service role key (server-side only).
 * - No LLM / pipeline calls here; this is a cheap DB read.
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SB_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SB_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || "";

const headers = {
  apikey: SB_KEY,
  Authorization: `Bearer ${SB_KEY}`,
  "Content-Type": "application/json",
};

async function sbGet(path: string) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers, cache: "no-store" });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    console.error(`[sbGet] ${r.status} for ${path.slice(0, 80)}: ${text.slice(0, 200)}`);
    return null;
  }
  return r.json();
}

type Coordinates = { latitude: number; longitude: number };

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const listingId = Number(id);
  if (!Number.isFinite(listingId) || listingId <= 0) {
    return NextResponse.json({ success: false, error: "Invalid listing id" }, { status: 400 });
  }

  try {
    const [listings, comps, selectedRows] = await Promise.all([
      sbGet(`listings?id=eq.${id}&select=id,title,address,lat,lng`),
      sbGet(
        [
          `listing_comparables?listing_id=eq.${id}`,
          `select=id,casafari_property_id,property_url,price_bucket,is_filtered,similarity_score,` +
            `sale_price,price_per_sqm,total_area,living_area,plot_area,bedrooms,bathrooms,` +
            `condition,construction_year,energy_rating,distance_km,address,zip_code,coordinates,photo_urls,features`,
          `order=distance_km.asc`,
        ].join("&"),
      ),
      sbGet(
        `unified_estimates?listing_id=eq.${id}&package_type=eq.v5_selected_comparable&select=estimate_data`,
      ),
    ]);

    const listing = listings?.[0];
    if (!listing) {
      return NextResponse.json({ success: false, error: "Listing not found" }, { status: 404 });
    }

    const selectedCompId = selectedRows?.[0]?.estimate_data?.selected_comparable_id ?? null;
    const selectedCasafariId = selectedCompId != null ? String(selectedCompId) : null;

    const comparablesRaw: Record<string, unknown>[] = Array.isArray(comps) ? comps : [];

    const comparables = comparablesRaw.map((c) => ({
      id: c.id,
      casafari_property_id: c.casafari_property_id,
      property_url: c.property_url,
      price_bucket: c.price_bucket,
      is_filtered: c.is_filtered,
      similarity_score: c.similarity_score,
      sale_price: c.sale_price,
      price_per_sqm: c.price_per_sqm,
      total_area: c.total_area,
      living_area: c.living_area,
      plot_area: c.plot_area,
      bedrooms: c.bedrooms,
      bathrooms: c.bathrooms,
      condition: c.condition,
      construction_year: c.construction_year,
      energy_rating: c.energy_rating,
      distance_km: c.distance_km,
      address: c.address,
      zip_code: c.zip_code,
      coordinates: c.coordinates as Coordinates | null,
      photo_urls: Array.isArray(c.photo_urls) ? c.photo_urls : [],
      features: c.features || null,
      // Derive property_type from features.characteristics if available
      property_type: null as string | null,
      // Derived fields used by the UI
      is_selected: selectedCasafariId
        ? String(c.casafari_property_id) === selectedCasafariId
        : false,
      comp_role: null as "reference" | "above" | "below" | null,
    }));

    // Derive comp_role around the selected comparable (by sale_price).
    const priced = [...comparables].filter((c) => typeof c.sale_price === "number");
    priced.sort((a, b) => Number(a.sale_price) - Number(b.sale_price));
    const refIdx = selectedCasafariId
      ? priced.findIndex((c) => String(c.casafari_property_id) === selectedCasafariId)
      : -1;

    const referenceIndex = refIdx >= 0 ? refIdx : (priced.length > 0 ? 0 : -1);
    if (referenceIndex >= 0) {
      const ref = priced[referenceIndex];
      if (ref) ref.comp_role = "reference";
      const below = priced[referenceIndex - 1];
      if (below) below.comp_role = "below";
      const above = priced[referenceIndex + 1];
      if (above) above.comp_role = "above";
    }

    const hasCoordinates =
      Number.isFinite(Number(listing.lat)) &&
      Number.isFinite(Number(listing.lng)) &&
      comparables.some((c) => {
        const coords = c.coordinates as Coordinates | null;
        return (
          !!coords &&
          Number.isFinite(Number(coords.latitude)) &&
          Number.isFinite(Number(coords.longitude))
        );
      });

    return NextResponse.json({
      success: true,
      hasCoordinates,
      target: {
        id: listing.id,
        title: listing.title || `Listing ${id}`,
        address: listing.address || null,
        lat: listing.lat,
        lng: listing.lng,
      },
      selected_comparable_id: selectedCompId,
      comparables,
    });
  } catch (error) {
    console.error(`[listings/${id}/comparables] error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch comparables" },
      { status: 500 },
    );
  }
}

