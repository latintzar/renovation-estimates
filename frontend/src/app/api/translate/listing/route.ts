/**
 * Translation Listing API Route
 * ==============================
 * 
 * Proxies listing translation requests to the Python backend.
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BACKEND_URL}/api/translate/listing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Translation listing proxy error:', error);
    return NextResponse.json(
      { error: 'Translation service unavailable' },
      { status: 503 }
    );
  }
}

