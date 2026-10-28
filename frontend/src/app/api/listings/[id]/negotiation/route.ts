/**
 * Listing Negotiation API
 * =======================
 * GET /api/listings/{id}/negotiation
 *
 * Returns negotiation advice + room photos for evidence display.
 * Merges v5_negotiation data with v5_clusters photo data so the
 * frontend can show photos of problem areas alongside each issue.
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SB_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SB_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || "";

const headers = {
  apikey: SB_KEY,
  Authorization: `Bearer ${SB_KEY}`,
  "Content-Type": "application/json",
};

interface Cluster {
  cluster_id: string;
  room_type: string;
  photo_urls?: string[];
  photos?: string[];
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  try {
    // Fetch negotiation data + clusters in parallel
    const [negResp, clusterResp] = await Promise.all([
      fetch(
        `${SB_URL}/rest/v1/unified_estimates?listing_id=eq.${id}&package_type=eq.v5_negotiation&select=estimate_data`,
        { headers, cache: "no-store" },
      ),
      fetch(
        `${SB_URL}/rest/v1/unified_estimates?listing_id=eq.${id}&package_type=eq.v5_clusters&select=estimate_data`,
        { headers, cache: "no-store" },
      ),
    ]);

    if (!negResp.ok) {
      console.error(`[negotiation/${id}] Supabase error: ${negResp.status}`);
      return NextResponse.json({ success: false, error: "Database error" }, { status: 500 });
    }

    const negRows = await negResp.json();
    const data = negRows?.[0]?.estimate_data;

    if (!data || !data.main_issue) {
      return NextResponse.json({ success: true, hasData: false });
    }

    // Build room_id → photo_urls map from clusters
    const roomPhotos: Record<string, string[]> = {};
    if (clusterResp.ok) {
      const clusterRows = await clusterResp.json();
      const clusterData = clusterRows?.[0]?.estimate_data;
      const clusters: Cluster[] = clusterData?.clusters || [];
      for (const c of clusters) {
        const rid = c.cluster_id || "";
        const urls = c.photo_urls || c.photos || [];
        if (rid && urls.length > 0) {
          roomPhotos[rid] = urls.map((u: string) =>
            typeof u === "string" ? u : "",
          ).filter(Boolean);
        }
      }
    }

    return NextResponse.json({
      success: true,
      hasData: true,
      negotiation: data,
      roomPhotos,
    });
  } catch (error) {
    console.error(`[negotiation/${id}] error:`, error);
    return NextResponse.json({ success: false, error: "Failed to load negotiation data" }, { status: 500 });
  }
}
