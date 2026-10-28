/**
 * Comparables Brackets API Route
 * ===============================
 * 
 * Proxy to backend:
 * GET/POST /api/renovation/{id}/comparables/brackets
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Comparables brackets can change as the pipeline runs — never cache.
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/renovation/${id}/comparables/brackets`, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    console.error('Failed to fetch comparables brackets:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to connect to backend' },
      { status: 500, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/renovation/${id}/comparables/brackets`, {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    console.error('Failed to run comparables brackets:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to connect to backend' },
      { status: 500, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

