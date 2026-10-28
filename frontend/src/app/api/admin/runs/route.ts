/**
 * Admin API Proxy — List Pipeline Runs
 * GET /api/admin/runs?limit=50&offset=0&listing_id=123
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    const offset = searchParams.get("offset") || "0";
    const listingId = searchParams.get("listing_id");

    const params = new URLSearchParams({ limit, offset });
    if (listingId) params.set("listing_id", listingId);

    const resp = await fetch(`${BACKEND_URL}/api/admin/runs?${params}`, {
      cache: "no-store",
    });

    const data = await resp.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store, must-revalidate" },
    });
  } catch (error) {
    console.error("[admin/runs] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch runs" },
      { status: 500 }
    );
  }
}
