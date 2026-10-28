/**
 * URL Validation API Route
 * ========================
 * 
 * Quick validation to check if URL is a property listing.
 * Uses Gemini 2.5 Flash Lite for fast, cheap classification.
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    console.log('[Validate Proxy] Checking URL:', body.url?.substring(0, 50));
    
    const response = await fetch(`${BACKEND_URL}/api/scrape/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    
    console.log('[Validate Proxy] Result:', data.is_valid ? 'VALID' : `REJECTED (${data.detected_type})`);
    
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('[Validate Proxy] Error:', error);
    
    // On error, allow through (don't block)
    return NextResponse.json({
      success: false,
      is_valid: true,  // Allow through on error
      confidence: 'low',
      detected_type: 'unknown',
      error: error instanceof Error ? error.message : 'Proxy error',
    });
  }
}

