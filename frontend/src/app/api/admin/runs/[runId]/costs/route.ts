/**
 * Admin API Proxy — Run Cost Tracking
 * GET /api/admin/runs/{runId}/costs
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  try {
    const { runId } = await params;
    const resp = await fetch(
      `${BACKEND_URL}/api/admin/runs/${encodeURIComponent(runId)}/costs`,
      { cache: "no-store" }
    );

    const data = await resp.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store, must-revalidate" },
    });
  } catch (error) {
    console.error("[admin/runs/costs] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch cost data" },
      { status: 500 }
    );
  }
}
