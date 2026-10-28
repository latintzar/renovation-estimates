/**
 * Translation Languages API Route
 * ================================
 * 
 * Proxies supported languages request to the Python backend.
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/translate/languages`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    
    const data = await response.json();
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Translation languages proxy error:', error);
    return NextResponse.json(
      { error: 'Translation service unavailable' },
      { status: 503 }
    );
  }
}

