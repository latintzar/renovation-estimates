import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Force dynamic - no caching
export const dynamic = 'force-dynamic';
export const revalidate = 0;

// GET /api/renovation/[id]/v048/packages - Get V0.4.8 packages
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/listings/${id}/v2/packages`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Never cache backend response
    });
    
    if (!response.ok) {
      // If backend returns 404, return empty packages (no packages yet)
      if (response.status === 404) {
        return NextResponse.json({
          success: true,
          hasData: false,
          packages: [],
          message: 'No V0.4.8 packages found'
        }, {
          headers: {
            'Cache-Control': 'no-store, must-revalidate',
          }
        });
      }
      
      const error = await response.text();
      return NextResponse.json(
        { success: false, error: `Backend error: ${error}` },
        { 
          status: response.status,
          headers: {
            'Cache-Control': 'no-store, must-revalidate',
          }
        }
      );
    }
    
    const data = await response.json();
    
    // Transform V2 backend response (packages as dict) to frontend format (packages as array)
    let packagesArray: any[] = [];
    let hasData = false;
    
    if (data.packages && typeof data.packages === 'object') {
      // V2 backend returns packages as { conservative: {...}, market_standard: {...}, ... }
      packagesArray = Object.entries(data.packages).map(([key, pkg]: [string, any]) => {
        const boq = pkg.boq || {};
        const totalWithIva = boq.grand_total_with_iva || 0;
        const totalWeeks = Math.ceil((boq.total_labor_hours || 400) / 40); // ~40 hrs/week
        
        // Map generated_images to room_images format expected by frontend
        const generatedImages = pkg.generated_images || [];
        const roomImages = generatedImages.map((img: any) => ({
          room_id: img.room_id || 'unknown',
          room_name: img.room_name || img.room_id || 'Room',
          before_image: img.before_url || '',
          // after_data is base64 - convert to data URL
          after_image: img.after_data 
            ? `data:image/jpeg;base64,${img.after_data}` 
            : '',
          key_changes: [],
          is_hero: false,
        })).filter((img: any) => img.before_image && img.after_image);
        
        // Get first image as hero
        const heroImage = roomImages.length > 0 ? roomImages[0] : null;
        
        return {
          package_type: key,
          strategy_name: pkg.strategy_name || key,
          reference_comparable_id: pkg.reference_comparable_id,
          reference_sold_price: pkg.reference_sold_price,
          // Cost fields (frontend uses various names)
          grand_total: totalWithIva,
          grand_total_with_iva: totalWithIva,
          total_cost: totalWithIva,
          renovation_cost: totalWithIva,
          // Duration
          duration_weeks: totalWeeks,
          total_labor_hours: boq.total_labor_hours || 0,
          // Items
          line_items_count: boq.line_items_count || boq.line_items?.length || 0,
          line_items: boq.line_items || [],
          dimension_totals: boq.dimension_totals || {},
          // Other data
          delta_scopes: pkg.delta_scopes,
          // ELI5 Summary (from Phase 7)
          eli5_summary: pkg.eli5_summary,
          // Deprecated: architect report is no longer generated or shown
          architect_report: null,
          // Room images (from Phase 5)
          room_images: roomImages,
          // Hero images for fallback
          before_image: heroImage?.before_image || null,
          after_image: heroImage?.after_image || null,
          // Deprecated: was sourced from architect report
          energy_compliance: {},
          // Comparables (reference + neighbors)
          comparables: pkg.comparables || [],
        };
      });
      hasData = packagesArray.length > 0;
    }
    
    // Log for debugging
    console.log(`[V0.4.8 Packages] Listing ${id}: ${packagesArray.length} packages (transformed from V2)`);
    if (packagesArray[0]) {
      console.log(`[V0.4.8 Packages] First package: ${packagesArray[0].package_type}, items: ${packagesArray[0].line_items_count}, total: €${packagesArray[0].grand_total_with_iva}`);
    }
    
    return NextResponse.json({
      success: data.success,
      hasData,
      packages: packagesArray,
      strategy_selection: data.strategy_selection,
      target_pir: data.target_pir
    }, {
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
      }
    });
    
  } catch (error) {
    console.error('[V0.4.8 Packages] Error:', error);
    // If backend is unavailable, return empty packages
    return NextResponse.json({
      success: true,
      hasData: false,
      packages: [],
      message: 'Backend unavailable'
    }, {
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
      }
    });
  }
}

