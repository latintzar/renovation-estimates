/**
 * Scrape API Route
 * ================
 * 
 * Custom proxy for scrape endpoint with extended timeout.
 * The scrape can take 30-60 seconds (Scrapfly + 2x Gemini calls).
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Next.js route segment config - extend timeout to 120 seconds
export const maxDuration = 120;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    console.log('[Scrape Proxy] Starting request for:', body.url?.substring(0, 50));
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout
    
    const response = await fetch(`${BACKEND_URL}/api/scrape`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    const data = await response.json();
    
    console.log('[Scrape Proxy] Response received:', data.success ? 'SUCCESS' : 'FAILED');
    
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('[Scrape Proxy] Error:', error);
    
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { success: false, error: 'Request timed out after 90 seconds' },
        { status: 504 }
      );
    }
    
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Proxy error' },
      { status: 500 }
    );
  }
}

