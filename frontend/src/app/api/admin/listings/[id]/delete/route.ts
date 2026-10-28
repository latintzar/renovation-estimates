/**
 * Admin API Proxy — Delete listing
 * DELETE /api/admin/listings/{id}/delete
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const resp = await fetch(`${BACKEND_URL}/api/admin/listings/${id}`, {
      method: "DELETE",
    });
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`[admin/listings/${id}/delete] proxy error:`, error);
    return NextResponse.json(
      { success: false, error: "Failed to delete listing" },
      { status: 500 }
    );
  }
}
