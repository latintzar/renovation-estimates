/**
 * Admin API — Listing + Comparables summary
 * GET /api/admin/listings/{id}/comparables
 *
 * Returns the target listing basics + all comparables with key fields,
 * plus which one was selected by the pipeline.
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SB_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SB_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || "";

const headers = {
  apikey: SB_KEY,
  Authorization: `Bearer ${SB_KEY}`,
  "Content-Type": "application/json",
};

async function sbGet(path: string) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers, cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    // Fetch listing, comparables, and selected comparable ID in parallel
    const [listings, comps, selectedRows] = await Promise.all([
      sbGet(
        `listings?id=eq.${id}&select=id,title,price_eur,bedrooms,bathrooms,sqm,m2_plot,property_type,lat,lng,scraped_data`
      ),
      sbGet(
        `listing_comparables?listing_id=eq.${id}&select=casafari_property_id,sale_price,price_per_sqm,total_area,living_area,bedrooms,bathrooms,condition,distance_km,address,photo_urls,coordinates&order=sale_price.asc`
      ),
      sbGet(
        `unified_estimates?listing_id=eq.${id}&package_type=eq.v5_selected_comparable&select=estimate_data`
      ),
    ]);

    const listing = listings?.[0];
    if (!listing) {
      return NextResponse.json({ success: false, error: "Listing not found" }, { status: 404 });
    }

    const scraped = listing.scraped_data || {};
    const selectedCompId = selectedRows?.[0]?.estimate_data?.selected_comparable_id;

    // Build target summary from best available data
    const target = {
      id: listing.id,
      title: listing.title || scraped.title || `Listing ${id}`,
      price_eur: listing.price_eur || scraped.price_eur,
      bedrooms: listing.bedrooms || scraped.bedrooms,
      bathrooms: listing.bathrooms || scraped.bathrooms,
      m2: listing.sqm || scraped.m2_built || scraped.m2_useful,
      property_type: listing.property_type || scraped.property_subtype || scraped.property_type,
      condition: scraped.condition,
      energy_rating: scraped.energy_rating,
      photo_url: scraped.image_urls?.[0] || scraped.photo_urls?.[0] || null,
    };

    // Build comparable summaries
    const comparables = (comps || []).map((c: Record<string, unknown>) => ({
      casafari_property_id: c.casafari_property_id,
      sale_price: c.sale_price,
      price_per_sqm: c.price_per_sqm,
      m2: c.total_area || c.living_area,
      bedrooms: c.bedrooms,
      bathrooms: c.bathrooms,
      condition: c.condition,
      distance_km: c.distance_km,
      address: c.address,
      photo_url: Array.isArray(c.photo_urls) ? c.photo_urls[0] : null,
      coordinates: c.coordinates || null,
      is_selected: String(c.casafari_property_id) === String(selectedCompId),
    }));

    return NextResponse.json({
      success: true,
      target,
      comparables,
      selected_comparable_id: selectedCompId || null,
    });
  } catch (error) {
    console.error(`[admin/listings/${id}/comparables] error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch comparables" },
      { status: 500 }
    );
  }
}
