/**
 * Admin API Proxy — Pipeline version (staleness detection)
 * GET /api/admin/pipeline-version
 */
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/pipeline-version`, {
      cache: "no-store",
    });
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[admin/pipeline-version] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch pipeline version" },
      { status: 500 }
    );
  }
}
