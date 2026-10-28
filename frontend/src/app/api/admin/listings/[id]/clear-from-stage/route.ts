/**
 * Admin API Proxy — Clear from stage
 * POST /api/admin/listings/{id}/clear-from-stage
 * Body: { from_stage: "v5_forage" }
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const body = await request.json();
    const resp = await fetch(
      `${BACKEND_URL}/api/admin/listings/${id}/clear-from-stage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`[admin/listings/${id}/clear-from-stage] proxy error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to clear from stage" },
      { status: 500 }
    );
  }
}
