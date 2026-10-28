/**
 * Run Pipeline API Route
 * ======================
 * 
 * Triggers the full V5 pipeline for a listing (including comparables).
 * Proxies POST to backend: /api/listings/{id}/v2/packages
 * 
 * The V5 pipeline runs these stages in order:
 *   1. Snapshot (fetch listing inputs)
 *   2. Comparables (Casafari fetch + snapshot)
 *   3. Clustering (constrained room types)
 *   4. Room tags → Target PIR → Select comparable
 *   5. Comparable clustering + room PIRs → Market targets
 *   6. Delta slots → Work items → BCCA match → BOQ
 *   7. ELI5 summary + Room images
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const listingId = parseInt((await params).id, 10);
  
  if (Number.isNaN(listingId)) {
    return NextResponse.json(
      { success: false, error: "Invalid listing ID" },
      { status: 400 }
    );
  }

  try {
    console.log(`[run-pipeline] Triggering V5 pipeline for listing ${listingId}`);

    const response = await fetch(
      `${BACKEND_URL}/api/listings/${listingId}/v2/packages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }
    );

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      console.error(`[run-pipeline] Backend error for listing ${listingId}:`, data);
      return NextResponse.json(
        { success: false, error: data?.error || data?.detail || `Backend error ${response.status}` },
        { status: response.status }
      );
    }

    console.log(`[run-pipeline] Pipeline enqueued for listing ${listingId}:`, {
      run_id: data?.run_id,
      success: data?.success,
    });

    return NextResponse.json({
      success: true,
      listing_id: listingId,
      run_id: data?.run_id,
    });
  } catch (error) {
    console.error(`[run-pipeline] Failed to trigger pipeline for listing ${listingId}:`, error);
    return NextResponse.json(
      { success: false, error: String(error) },
      { status: 500 }
    );
  }
}
