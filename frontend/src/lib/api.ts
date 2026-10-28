/**
 * Lean MVP API Client
 * ====================
 * 
 * Handles all API calls to the backend.
 * Proxied through Next.js to avoid CORS.
 */

// Types from shared types file
import type { 
  Listing, 
  ScrapedData, 
  ScrapeResponse,
  ListingCreate,
} from "./types";

// ============================================================================
// CONFIG
// ============================================================================

const API_BASE = "/api";

// ============================================================================
// HELPERS
// ============================================================================

interface ApiError {
  success: false;
  error: string;
}

interface ApiSuccess<T> {
  success: true;
  data: T;
}

type ApiResult<T> = ApiSuccess<T> | ApiError;

async function apiCall<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.error || `HTTP ${response.status}`,
      };
    }

    // Handle API responses that have success field
    if ("success" in data) {
      if (data.success) {
        return { success: true, data: data.data };
      } else {
        return { success: false, error: data.error || "Unknown error" };
      }
    }

    return { success: true, data };
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

// ============================================================================
// SCRAPING
// ============================================================================

/**
 * Validation response from URL validator
 */
export interface ValidationResult {
  is_valid: boolean;
  confidence: string;
  detected_type: string;
  rejection_reason?: string;
  error?: string;
}

/**
 * Validate if a URL is a property listing (fast, cheap check)
 * Call this BEFORE scrapeUrl to reject non-listing URLs early.
 */
export async function validateUrl(url: string): Promise<ApiResult<ValidationResult>> {
  try {
    const response = await fetch(`${API_BASE}/scrape/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.error || `HTTP ${response.status}`,
      };
    }
    
    return {
      success: true,
      data: {
        is_valid: data.is_valid,
        confidence: data.confidence,
        detected_type: data.detected_type,
        rejection_reason: data.rejection_reason,
        error: data.error,
      },
    };
  } catch (error) {
    // On error, allow through (don't block)
    console.error("Validation error:", error);
    return {
      success: true,
      data: {
        is_valid: true,
        confidence: "low",
        detected_type: "unknown",
        error: error instanceof Error ? error.message : "Network error",
      },
    };
  }
}

/**
 * Scrape a property listing URL
 */
export async function scrapeUrl(url: string): Promise<ApiResult<ScrapedData>> {
  // apiCall already extracts .data from the response
  // The response from backend is: { success: true, data: ScrapedData, ... }
  // After apiCall extracts .data, result.data IS the ScrapedData
  const result = await apiCall<ScrapedData>("/scrape", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

  return result;
}

/**
 * Quick scrape for preview (faster)
 */
export async function scrapePreview(url: string): Promise<ApiResult<ScrapedData>> {
  const result = await apiCall<ScrapedData>("/scrape/preview", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

  return result;
}

// ============================================================================
// LISTINGS
// ============================================================================

export interface ListingsResult {
  listings: Listing[];
  total: number;
}

/**
 * Get all listings
 */
export async function getListings(
  limit = 50,
  offset = 0
): Promise<ApiResult<ListingsResult>> {
  const result = await apiCall<Listing[]>(
    `/listings?limit=${limit}&offset=${offset}`
  );

  if (!result.success) {
    return result;
  }

  // result.data is already the array (apiCall unwraps data.data)
  const listings = Array.isArray(result.data) ? result.data : [];
  return {
    success: true,
    data: {
      listings,
      total: listings.length,
    },
  };
}

/**
 * Get a single listing
 */
export async function getListing(id: number): Promise<ApiResult<Listing>> {
  return apiCall<Listing>(`/listings/${id}`);
}

/**
 * Create a new listing (after scraping + confirmation)
 */
export async function createListing(data: ListingCreate): Promise<ApiResult<Listing>> {
  return apiCall<Listing>("/listings", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Trigger the full V5 pipeline for a listing (including comparables).
 * This enqueues all pipeline stages: snapshot → comparables → clustering → PIR → 
 * delta → work items → BCCA → BOQ → ELI5 → room images.
 */
export async function runPipeline(listingId: number): Promise<ApiResult<{ run_id: string }>> {
  return apiCall<{ run_id: string }>(`/listings/${listingId}/run-pipeline`, {
    method: "POST",
  });
}

/**
 * Update a listing
 */
export async function updateListing(
  id: number,
  data: Partial<Listing>
): Promise<ApiResult<Listing>> {
  return apiCall<Listing>(`/listings/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * Delete a listing
 */
export async function deleteListing(id: number): Promise<ApiResult<void>> {
  return apiCall<void>(`/listings/${id}`, {
    method: "DELETE",
  });
}

/**
 * Get photos for a listing
 */
export async function getListingPhotos(id: number): Promise<ApiResult<string[]>> {
  const result = await apiCall<{ data: string[] }>(`/listings/${id}/photos`);
  
  if (!result.success) {
    return result;
  }
  
  return {
    success: true,
    data: result.data.data || result.data as unknown as string[],
  };
}

// ============================================================================
// DOMAIN UTILITIES
// ============================================================================

export interface DomainInfo {
  name: string;
  color: string;
  bgClass: string;
  textClass: string;
}

const KNOWN_DOMAINS: Record<string, DomainInfo> = {
  "idealista.com": {
    name: "Idealista",
    color: "#00b140",
    bgClass: "bg-green-50",
    textClass: "text-green-700",
  },
  "fotocasa.es": {
    name: "Fotocasa",
    color: "#ff6b35",
    bgClass: "bg-orange-50",
    textClass: "text-orange-700",
  },
  "lucasfox.com": {
    name: "Lucas Fox",
    color: "#1a1a1a",
    bgClass: "bg-stone-100",
    textClass: "text-stone-700",
  },
  "engelvoelkers.com": {
    name: "Engel & Völkers",
    color: "#c4122e",
    bgClass: "bg-red-50",
    textClass: "text-red-700",
  },
};

/**
 * Get domain info for styling
 */
export function getDomainInfo(url: string): DomainInfo | null {
  try {
    const hostname = new URL(url).hostname.replace("www.", "");
    for (const [domain, info] of Object.entries(KNOWN_DOMAINS)) {
      if (hostname.includes(domain)) {
        return info;
      }
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Extract domain from URL
 */
export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return "unknown";
  }
}

/**
 * Check if URL is valid
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url.startsWith("http") ? url : `https://${url}`);
    return true;
  } catch {
    return false;
  }
}

