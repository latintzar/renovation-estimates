/**
 * Admin API Proxy — List all listings
 * GET /api/admin/listings
 */
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/listings`, {
      cache: "no-store",
    });
    const data = await resp.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store, must-revalidate" },
    });
  } catch (error) {
    console.error("[admin/listings] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch listings" },
      { status: 500 }
    );
  }
}
