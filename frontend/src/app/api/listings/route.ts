/**
 * Listings API Proxy
 * ==================
 * 
 * Proxies requests to the backend to avoid CORS issues.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") || "50";
  const offset = searchParams.get("offset") || "0";

  try {
    const response = await fetch(
      `${BACKEND_URL}/api/listings?limit=${limit}&offset=${offset}`,
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/listings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

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

