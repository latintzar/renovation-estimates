/**
 * Admin API Proxy — Run Logs (pipeline_job_events)
 * GET /api/admin/runs/{runId}/logs?limit=20000&event_type=log
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  try {
    const { runId } = await params;
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "20000";
    const eventType = searchParams.get("event_type");

    const buildQs = (lim: string) => {
      const qs = new URLSearchParams({ limit: lim, latest: "true" });
      if (eventType) qs.set("event_type", eventType);
      return qs;
    };

    const fetchLogs = async (lim: string) =>
      fetch(
        `${BACKEND_URL}/api/admin/runs/${encodeURIComponent(runId)}/logs?${buildQs(lim)}`,
        { cache: "no-store" }
      );

    // Backwards compatibility:
    // Some deployed backends cap the accepted limit value. Retry progressively so
    // the UI still renders logs instead of failing hard on 422 validation errors.
    let resp = await fetchLogs(limit);
    if (resp.status === 422) {
      const fallbacks = ["50000", "20000", "10000", "5000", "1000"];
      for (const candidate of fallbacks) {
        if (candidate === limit) continue;
        resp = await fetchLogs(candidate);
        if (resp.status !== 422) break;
      }
    }

    const data = await resp.json();
    return NextResponse.json(data, {
      status: resp.status,
      headers: { "Cache-Control": "no-store, must-revalidate" },
    });
  } catch (error) {
    console.error("[admin/runs/logs] proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch logs" },
      { status: 500 }
    );
  }
}
