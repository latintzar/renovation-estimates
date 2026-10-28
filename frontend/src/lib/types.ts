/**
 * Lean MVP Frontend Types
 * =======================
 * 
 * TypeScript types matching the backend schema.
 * Aligned with ListingEditor full schema.
 */

// ============================================================================
// ENUMS
// ============================================================================

export type PipelineStatus = "scraped" | "analyzing" | "complete" | "failed";

export type TierName = "cosmetic" | "systems" | "structure";

export type ListingType = "sale" | "rent" | "rent_to_own";

export type PricePeriod = "total" | "month";

export type Condition = "new" | "good" | "renovate";

export type FloorLevel = "ground" | "intermediate" | "top";

export type PropertySubtype = 
  | "flat" 
  | "penthouse" 
  | "duplex" 
  | "studio" 
  | "chalet_detached" 
  | "chalet_semi" 
  | "chalet_terraced" 
  | "rustic";

export type HousingSituation = 
  | "free" 
  | "rented" 
  | "bare_ownership" 
  | "squatted" 
  | "auction";

export type AdOrigin = "standard" | "bank";

// ============================================================================
// NESTED TYPES
// ============================================================================

export interface Areas {
  constructed?: number;
  useful?: number;
}

export interface Agency {
  name?: string;
  logo_url?: string;
  phone?: string;
  email?: string;
  agent_name?: string;
  agent_photo_url?: string;
  agent_phone?: string;
  whatsapp?: string;
}

// ============================================================================
// LISTING TYPES
// ============================================================================

export interface Listing {
  id: number;
  user_id?: string;
  source_url: string;
  source_domain?: string;
  
  // Core Info
  title?: string;
  description?: string;
  
  // Numbers
  price_eur?: number;
  bedrooms?: number;
  bathrooms?: number;
  
  // Areas
  sqm?: number;
  m2_built?: number;
  m2_useful?: number;
  
  // Transaction
  listing_type?: ListingType;
  price_period?: PricePeriod;
  
  // Location
  address?: string;
  city?: string;
  neighborhood?: string;
  region?: string;
  postal_code?: string;
  country?: string;
  lat?: number;
  lng?: number;
  
  // Property Classification
  property_type?: string;
  property_subtype?: PropertySubtype;
  housing_situation?: HousingSituation;
  ad_origin?: AdOrigin;
  condition?: Condition;
  
  // Floor Info
  floor_level?: FloorLevel;
  floor_number?: number;
  
  // Boolean Amenities
  has_elevator?: boolean;
  is_exterior?: boolean;
  has_terrace?: boolean;
  has_balcony?: boolean;
  has_pool?: boolean;
  has_garage?: boolean;
  has_garden?: boolean;
  has_storage?: boolean;
  has_air_conditioning?: boolean;
  has_wardrobes?: boolean;
  is_accessible?: boolean;
  
  // Features
  features?: string[];
  amenities?: string[];
  
  // Reference
  reference?: string;
  
  // Agency
  agency?: Agency;
  
  // Metadata
  scraped_data?: Record<string, unknown>;
  pipeline_status?: PipelineStatus;
  pipeline_error?: string;
  created_at?: string;
  updated_at?: string;
  
  // Joined from listing_photos
  photos?: string[];
}

export interface ListingCreate {
  source_url: string;
  source_domain?: string;
  
  // Core Info
  title?: string;
  description?: string;
  
  // Numbers
  price_eur?: number;
  bedrooms?: number;
  bathrooms?: number;
  
  // Areas
  sqm?: number;
  m2_built?: number;
  m2_useful?: number;
  
  // Transaction
  listing_type?: ListingType;
  price_period?: PricePeriod;
  
  // Location
  address?: string;
  city?: string;
  neighborhood?: string;
  region?: string;
  country?: string;
  lat?: number;
  lng?: number;
  
  // Property Classification
  property_type?: string;
  property_subtype?: PropertySubtype;
  housing_situation?: HousingSituation;
  ad_origin?: AdOrigin;
  condition?: Condition;
  
  // Floor Info
  floor_level?: FloorLevel;
  floor_number?: number;
  
  // Boolean Amenities
  has_elevator?: boolean;
  is_exterior?: boolean;
  has_terrace?: boolean;
  has_balcony?: boolean;
  has_pool?: boolean;
  has_garage?: boolean;
  has_garden?: boolean;
  has_storage?: boolean;
  has_air_conditioning?: boolean;
  has_wardrobes?: boolean;
  is_accessible?: boolean;
  
  // Features
  features?: string[];
  amenities?: string[];
  
  // Photos
  image_urls?: string[];
  photo_urls?: string[];
  
  // Reference
  reference?: string;
  
  // Agency
  agency?: Agency;
  
  // Metadata
  scraped_data?: Record<string, unknown>;
}

// ============================================================================
// SCRAPING TYPES (Full Schema)
// ============================================================================

export interface ScrapedData {
  // Core Info
  title?: string;
  description?: string;
  
  // Numbers
  price?: number;  // Alias for price_eur
  price_eur?: number;
  bedrooms?: number;
  bathrooms?: number;
  
  // Areas
  areas?: Areas;
  m2_built?: number;
  m2_useful?: number;
  sqm?: number; // Legacy alias
  
  // Transaction
  listing_type?: ListingType;
  price_period?: PricePeriod;
  
  // Location
  address?: string;
  city?: string;
  neighborhood?: string;
  region?: string;
  country?: string;
  lat?: number;
  lng?: number;
  autocomplete_query?: string;
  
  // Property Classification
  property_type?: string;
  property_subtype?: PropertySubtype;
  housing_situation?: HousingSituation;
  ad_origin?: AdOrigin;
  condition?: Condition;
  
  // Floor Info
  floor_level?: FloorLevel;
  floor_number?: number;
  
  // Boolean Amenities
  has_elevator?: boolean;
  is_exterior?: boolean;
  has_terrace?: boolean;
  has_balcony?: boolean;
  has_pool?: boolean;
  has_garage?: boolean;
  has_garden?: boolean;
  has_storage?: boolean;
  has_air_conditioning?: boolean;
  has_wardrobes?: boolean;
  is_accessible?: boolean;
  
  // Orientations
  balcony_orientation?: string;
  terrace_orientation?: string;
  
  // Features
  features?: string[];
  amenities?: string[];
  additionalFeatures?: string[];
  roomsAndAmenities?: string;
  
  // Photos
  image_urls?: string[];
  photo_urls?: string[];
  
  // Reference & Source
  reference?: string;
  source_url?: string;
  scraped_at?: string;
  
  // Agency
  agency?: Agency;
  
  // Raw metadata
  raw_metadata?: Record<string, unknown>;
}

export interface ScrapeResponse {
  success: boolean;
  data?: ScrapedData;
  error?: string;
  source_url: string;
  source_domain: string;
}

// ============================================================================
// UI TYPES
// ============================================================================

export interface DomainConfig {
  name: string;
  color: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
}

export const KNOWN_DOMAINS: Record<string, DomainConfig> = {
  "idealista.com": {
    name: "Idealista",
    color: "#00b140",
    bgClass: "bg-green-50",
    textClass: "text-green-700",
    borderClass: "border-green-300",
  },
  "fotocasa.es": {
    name: "Fotocasa",
    color: "#ff6b35",
    bgClass: "bg-orange-50",
    textClass: "text-orange-700",
    borderClass: "border-orange-300",
  },
  "habitaclia.com": {
    name: "Habitaclia",
    color: "#ff6900",
    bgClass: "bg-orange-50",
    textClass: "text-orange-700",
    borderClass: "border-orange-300",
  },
  "pisos.com": {
    name: "Pisos.com",
    color: "#0066cc",
    bgClass: "bg-blue-50",
    textClass: "text-blue-700",
    borderClass: "border-blue-300",
  },
  "lucasfox.com": {
    name: "Lucas Fox",
    color: "#1a1a1a",
    bgClass: "bg-stone-100",
    textClass: "text-stone-700",
    borderClass: "border-stone-300",
  },
  "engelvoelkers.com": {
    name: "Engel & Völkers",
    color: "#c4122e",
    bgClass: "bg-red-50",
    textClass: "text-red-700",
    borderClass: "border-red-300",
  },
  "remax.es": {
    name: "RE/MAX",
    color: "#003da5",
    bgClass: "bg-blue-50",
    textClass: "text-blue-700",
    borderClass: "border-blue-300",
  },
  "kyero.com": {
    name: "Kyero",
    color: "#005eb8",
    bgClass: "bg-blue-50",
    textClass: "text-blue-700",
    borderClass: "border-blue-300",
  },
};

// ============================================================================
// PROPERTY TYPE OPTIONS (For UI dropdowns)
// ============================================================================

export const PROPERTY_SUBTYPES = [
  { value: "flat", label: "Flat / Piso" },
  { value: "penthouse", label: "Penthouse / Ático" },
  { value: "duplex", label: "Duplex / Dúplex" },
  { value: "studio", label: "Studio / Estudio" },
  { value: "chalet_detached", label: "Detached House / Chalet Independiente" },
  { value: "chalet_semi", label: "Semi-Detached / Chalet Pareado" },
  { value: "chalet_terraced", label: "Terraced / Chalet Adosado" },
  { value: "rustic", label: "Rustic Property / Finca Rústica" },
] as const;

export const HOUSING_SITUATIONS = [
  { value: "free", label: "Free (Standard)" },
  { value: "rented", label: "Rented (With Tenants)" },
  { value: "bare_ownership", label: "Bare Ownership (Nuda Propiedad)" },
  { value: "squatted", label: "Squatted (Okupado)" },
  { value: "auction", label: "Auction" },
] as const;

export const AD_ORIGINS = [
  { value: "standard", label: "Standard (Private/Agency)" },
  { value: "bank", label: "Bank Owned (De Banco)" },
] as const;

export const CONDITIONS = [
  { value: "new", label: "New / Obra Nueva" },
  { value: "good", label: "Good Condition / Buen Estado" },
  { value: "renovate", label: "To Renovate / A Reformar" },
] as const;

export const FLOOR_LEVELS = [
  { value: "ground", label: "Ground / Bajo" },
  { value: "intermediate", label: "Intermediate" },
  { value: "top", label: "Top / Ático" },
] as const;

// ============================================================================
// HELPERS
// ============================================================================

export function getDomainConfig(url: string): DomainConfig | null {
  try {
    const hostname = new URL(url).hostname.replace("www.", "");
    for (const [domain, config] of Object.entries(KNOWN_DOMAINS)) {
      if (hostname.includes(domain)) {
        return config;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return "unknown";
  }
}

export function formatPrice(price?: number, period?: PricePeriod): string {
  if (!price) return "Price on request";
  const formatted = new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(price);
  
  if (period === "month") {
    return `${formatted}/mes`;
  }
  return formatted;
}

export function formatSqm(sqm?: number): string {
  if (!sqm) return "";
  return `${sqm} m²`;
}

export function formatRooms(bedrooms?: number, bathrooms?: number): string {
  const parts = [];
  if (bedrooms) parts.push(`${bedrooms} bed`);
  if (bathrooms) parts.push(`${bathrooms} bath`);
  return parts.join(" · ");
}
