/**
 * Admin API Proxy — Listing detail
 * GET /api/admin/listings/{id}
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/listings/${id}`, {
      cache: "no-store",
    });
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`[admin/listings/${id}] proxy error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch listing detail" },
      { status: 500 }
    );
  }
}
