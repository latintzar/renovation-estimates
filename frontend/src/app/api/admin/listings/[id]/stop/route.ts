/**
 * Admin API Proxy — Stop a listing's pipeline
 * POST /api/admin/listings/{id}/stop
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const resp = await fetch(
      `${BACKEND_URL}/api/admin/listings/${id}/stop`,
      { method: "POST" }
    );
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`[admin/listings/${id}/stop] proxy error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to stop pipeline" },
      { status: 500 }
    );
  }
}
