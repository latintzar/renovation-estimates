/**
 * Admin API Proxy — Stop ALL running pipelines
 * POST /api/admin/stop-all
 */
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/stop-all`, {
      method: "POST",
    });
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[admin/stop-all] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to stop all pipelines" },
      { status: 500 }
    );
  }
}
