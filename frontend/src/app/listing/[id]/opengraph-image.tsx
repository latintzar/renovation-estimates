/**
 * Dynamic Open Graph Image for Listing Pages
 * ============================================
 *
 * Styled like the Reforma tab metrics on the listing page:
 *   - Left: after-renovation hero photo (from generated images)
 *   - Right: three metrics vertically centered (Inversion, Valor+, Plazo)
 *   - Bottom: address + Leo.casa branding
 *
 * Data sources (all from Supabase):
 *   - listings: price_eur, address/city/title
 *   - unified_estimates (v5_eli5_market_standard): property_summary.total_cost, total_weeks
 *   - unified_estimates (v5_selected_comparable): median_value (reference sold price)
 *   - unified_estimates (v5_generated_images_market_standard): generated_images[0].after_data
 *   - photo_clusters: fallback hero photo URL (if no generated after image)
 *
 * Dimensions: 1200x630
 */

import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Analisis de reforma - Leo.casa";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

const hdrs = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
};

type ListingRow = {
  title?: string;
  price_eur?: number;
  address?: string;
  city?: string;
};

const formatCompactPrice = (v: number): string => {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return "\u20AC" + (v / 1_000_000).toFixed(1) + "M";
  if (abs >= 1_000) return "\u20AC" + Math.round(v / 1_000) + "K";
  return "\u20AC" + Math.round(v);
};

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  // 1. Fetch listing basics
  let listing: ListingRow | null = null;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/listings?id=eq.${id}&select=title,price_eur,address,city&limit=1`,
      { headers: hdrs },
    );
    const rows = await resp.json();
    listing = Array.isArray(rows) ? rows[0] ?? null : null;
  } catch {
    // graceful fallback
  }

  // 2. Fetch renovation data (ELI5 -> total_cost + total_weeks)
  let totalCost: number | null = null;
  let totalWeeks: number | null = null;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/unified_estimates?listing_id=eq.${id}&package_type=eq.v5_eli5_market_standard&select=estimate_data&limit=1`,
      { headers: hdrs },
    );
    const rows = await resp.json();
    const summary = rows?.[0]?.estimate_data?.property_summary;
    if (summary) {
      if (typeof summary.total_cost === "number" && summary.total_cost > 0)
        totalCost = summary.total_cost;
      if (typeof summary.total_weeks === "number" && summary.total_weeks > 0)
        totalWeeks = summary.total_weeks;
    }
  } catch {
    // fallback
  }

  // 3. Fetch comparable sold price (selected_comparable -> median_value)
  let comparableSoldPrice: number | null = null;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/unified_estimates?listing_id=eq.${id}&package_type=eq.v5_selected_comparable&select=estimate_data&limit=1`,
      { headers: hdrs },
    );
    const rows = await resp.json();
    const mv = rows?.[0]?.estimate_data?.median_value;
    if (typeof mv === "number" && mv > 0) comparableSoldPrice = mv;
  } catch {
    // fallback
  }

  // 4. Fetch after-renovation photo (generated images -> base64)
  let photoSrc: string | null = null;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/unified_estimates?listing_id=eq.${id}&package_type=eq.v5_generated_images_market_standard&select=estimate_data&limit=1`,
      { headers: hdrs },
    );
    const rows = await resp.json();
    const images = rows?.[0]?.estimate_data?.generated_images;
    if (Array.isArray(images) && images.length > 0) {
      const afterData = images[0]?.after_data;
      if (typeof afterData === "string" && afterData.length > 100) {
        photoSrc = "data:image/jpeg;base64," + afterData;
      }
    }
  } catch {
    // fallback
  }

  // 4b. Fallback: use before photo from photo_clusters
  if (!photoSrc) {
    const preferredRooms =
      "open_plan_living_dining,living_room,kitchen,bedroom_primary";
    try {
      const resp = await fetch(
        `${SUPABASE_URL}/rest/v1/photo_clusters?listing_id=eq.${id}&room_type=in.(${preferredRooms})&select=photo_urls&limit=1`,
        { headers: hdrs },
      );
      const rows = await resp.json();
      photoSrc = rows?.[0]?.photo_urls?.[0] ?? null;
    } catch {
      // fallback
    }
    if (!photoSrc) {
      try {
        const resp = await fetch(
          `${SUPABASE_URL}/rest/v1/photo_clusters?listing_id=eq.${id}&select=photo_urls&limit=1`,
          { headers: hdrs },
        );
        const rows = await resp.json();
        photoSrc = rows?.[0]?.photo_urls?.[0] ?? null;
      } catch {
        // fallback
      }
    }
  }

  // 5. Compute derived values
  const askingPrice =
    typeof listing?.price_eur === "number" ? listing.price_eur : 0;
  const valorPlus =
    comparableSoldPrice && askingPrice
      ? comparableSoldPrice - askingPrice
      : null;
  const isPositive = valorPlus !== null && valorPlus >= 0;

  const address =
    listing?.address || listing?.city || listing?.title || "Propiedad";
  const shortAddress =
    address.length > 50 ? address.slice(0, 47) + "\u2026" : address;

  // 6. Render - ComparablesCard style, matching listing page fonts
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f5f5f4",
          fontFamily: "system-ui, -apple-system, sans-serif",
          padding: 40,
        }}
      >
        {/* Card */}
        <div
          style={{
            display: "flex",
            width: "100%",
            height: "100%",
            backgroundColor: "#ffffff",
            borderRadius: 32,
            overflow: "hidden",
            border: "1px solid #e7e5e4",
          }}
        >
          {/* Left: After photo (55%) */}
          <div
            style={{
              width: "55%",
              height: "100%",
              display: "flex",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {photoSrc ? (
              <img
                src={photoSrc}
                alt=""
                width={660}
                height={550}
                style={{ objectFit: "cover", width: "100%", height: "100%" }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background:
                    "linear-gradient(135deg, #d6d3d1 0%, #a8a29e 100%)",
                  fontSize: 80,
                  opacity: 0.4,
                }}
              >
                Leo.casa
              </div>
            )}

            {/* Address overlay at bottom of photo */}
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                display: "flex",
                padding: "48px 24px 20px 24px",
                background:
                  "linear-gradient(to top, rgba(0,0,0,0.7), transparent)",
              }}
            >
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: "#ffffff",
                  lineHeight: 1.3,
                }}
              >
                {shortAddress}
              </span>
            </div>
          </div>

          {/* Right: Stats (45%) - vertically centered */}
          <div
            style={{
              width: "45%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 32px",
            }}
          >
            {/* Inversion */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                marginBottom: 36,
              }}
            >
              <span
                style={{
                  fontSize: 17,
                  fontWeight: 600,
                  color: "#a8a29e",
                  letterSpacing: "0.08em",
                  marginBottom: 6,
                }}
              >
                Inversi\u00F3n
              </span>
              <span
                style={{
                  fontSize: 64,
                  fontWeight: 900,
                  color: "#1c1917",
                  letterSpacing: "-2px",
                  lineHeight: 1,
                }}
              >
                {totalCost ? formatCompactPrice(totalCost) : "\u2014"}
              </span>
            </div>

            {/* Valor + */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                marginBottom: 36,
              }}
            >
              <span
                style={{
                  fontSize: 17,
                  fontWeight: 600,
                  color: "#a8a29e",
                  letterSpacing: "0.08em",
                  marginBottom: 6,
                }}
              >
                Valor +
              </span>
              <span
                style={{
                  fontSize: 64,
                  fontWeight: 900,
                  lineHeight: 1,
                  letterSpacing: "-2px",
                  color:
                    valorPlus !== null
                      ? isPositive
                        ? "#059669"
                        : "#ef4444"
                      : "#a8a29e",
                }}
              >
                {valorPlus !== null
                  ? (valorPlus >= 0 ? "+" : "") + formatCompactPrice(valorPlus)
                  : "\u2014"}
              </span>
            </div>

            {/* Plazo */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: 17,
                  fontWeight: 600,
                  color: "#a8a29e",
                  letterSpacing: "0.08em",
                  marginBottom: 6,
                }}
              >
                Plazo
              </span>
              <span
                style={{
                  fontSize: 64,
                  fontWeight: 900,
                  color: "#1c1917",
                  letterSpacing: "-2px",
                  lineHeight: 1,
                }}
              >
                {totalWeeks ? totalWeeks + " sem" : "\u2014"}
              </span>
            </div>

            {/* Leo.casa branding */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                marginTop: "auto",
                paddingTop: 20,
                paddingBottom: 16,
              }}
            >
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  fontStyle: "italic",
                  color: "#1c1917",
                }}
              >
                Leo
              </span>
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 400,
                  color: "#78716c",
                }}
              >
                .casa
              </span>
            </div>
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
