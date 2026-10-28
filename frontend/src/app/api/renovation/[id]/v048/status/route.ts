import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Status endpoints must never be cached — they are the app’s source of truth.
export const dynamic = 'force-dynamic';
export const revalidate = 0;

// GET /api/renovation/[id]/v048/status - Get V0.4.8 pipeline status
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/listings/${id}/v2/status`, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      // If backend returns 404, return idle status
      if (response.status === 404) {
        return NextResponse.json(
          {
            success: true,
            status: 'idle',
            progress: 'Not started',
            checkpoints_completed: 0,
            total_checkpoints: 8,
          },
          { headers: { 'Cache-Control': 'no-store' } }
        );
      }
      
      const error = await response.text();
      return NextResponse.json(
        { success: false, error: `Backend error: ${error}` },
        { status: response.status, headers: { 'Cache-Control': 'no-store' } }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } });
    
  } catch (error) {
    console.error('[V0.4.8 Status] Error:', error);
    // If backend is unavailable, return idle status
    return NextResponse.json(
      {
        success: true,
        status: 'idle',
        progress: 'Backend unavailable',
        checkpoints_completed: 0,
        total_checkpoints: 8,
      },
      { headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

