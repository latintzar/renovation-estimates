/**
 * Listing Layout — Per-listing OG metadata
 * ==========================================
 *
 * WHY THIS EXISTS:
 * The listing page.tsx is "use client" and cannot export generateMetadata.
 * Without this layout, every listing uses the root layout's generic OG tags,
 * so WhatsApp/Telegram/iMessage previews show "Leo.casa" instead of the
 * actual property address, price, and photo.
 *
 * CRITICAL: metadataBase is set to app.leo.casa (NOT leo.casa) because
 * the middleware blocks /listing/* on the marketing domain. If the OG image
 * URL pointed to leo.casa, social crawlers would get a 404.
 */

import type { Metadata } from "next";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

const APP_BASE = "https://app.leo.casa";

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
};

type ListingRow = {
  title?: string;
  price_eur?: number;
  address?: string;
  city?: string;
  neighborhood?: string;
  bedrooms?: number;
  bathrooms?: number;
  sqm?: number;
};

const fmtPrice = (v: number): string =>
  `€${v.toLocaleString("es-ES", { maximumFractionDigits: 0 })}`;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;

  let listing: ListingRow | null = null;
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/listings?id=eq.${id}&select=title,price_eur,address,city,neighborhood,bedrooms,bathrooms,sqm&limit=1`,
      { headers, next: { revalidate: 300 } },
    );
    const rows = await resp.json();
    listing = Array.isArray(rows) ? rows[0] ?? null : null;
  } catch {
    // Graceful fallback — generic metadata
  }

  // Build display strings
  const location = listing?.address || listing?.neighborhood || listing?.city || listing?.title || "Propiedad";
  const shortLocation = location.length > 60 ? location.slice(0, 57) + "…" : location;

  const price =
    typeof listing?.price_eur === "number" && listing.price_eur > 0
      ? fmtPrice(listing.price_eur)
      : null;

  const specs: string[] = [];
  if (typeof listing?.bedrooms === "number" && listing.bedrooms > 0)
    specs.push(`${listing.bedrooms} hab`);
  if (typeof listing?.bathrooms === "number" && listing.bathrooms > 0)
    specs.push(`${Math.round(listing.bathrooms)} baño${listing.bathrooms > 1 ? "s" : ""}`);
  if (typeof listing?.sqm === "number" && listing.sqm > 0)
    specs.push(`${listing.sqm} m²`);

  const title = price
    ? `${shortLocation} — ${price}`
    : shortLocation;

  const description = [
    "Análisis de reforma con IA",
    specs.length > 0 ? specs.join(" · ") : null,
    price ? `Precio: ${price}` : null,
    "Coste de reforma, comparables y briefing para contratista.",
  ]
    .filter(Boolean)
    .join(" — ");

  const listingUrl = `${APP_BASE}/listing/${id}`;

  return {
    metadataBase: new URL(APP_BASE),
    title,
    description,
    openGraph: {
      type: "website",
      locale: "es_ES",
      alternateLocale: ["en_US"],
      url: listingUrl,
      siteName: "Leo.casa",
      title: `${title} | Leo.casa`,
      description,
      images: [
        {
          url: `${APP_BASE}/listing/${id}/opengraph-image`,
          width: 1200,
          height: 630,
          alt: `Análisis de reforma — ${shortLocation}`,
          type: "image/png",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | Leo.casa`,
      description,
      images: [`${APP_BASE}/listing/${id}/opengraph-image`],
    },
  };
}

export default function ListingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
