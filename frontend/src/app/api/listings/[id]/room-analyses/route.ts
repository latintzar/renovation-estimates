/**
 * Room Analyses API Proxy
 * =======================
 * 
 * Proxies requests to the backend to avoid CORS issues.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const id = (await context.params).id;
    
    const response = await fetch(
      `${BACKEND_URL}/api/listings/${id}/room-analyses`,
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      const text = await response.text();
      console.error("Backend error:", text);
      return NextResponse.json(
        { success: false, error: text },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}

