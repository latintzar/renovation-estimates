/**
 * Admin API Proxy — Resume ALL stopped/failed pipelines
 * POST /api/admin/resume-all
 */
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/resume-all`, {
      method: "POST",
    });
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[admin/resume-all] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to resume all pipelines" },
      { status: 500 }
    );
  }
}
