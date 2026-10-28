"""
V0.3.2 Pipeline Orchestrator
PETER AGENTIC V0.3.2

Unified pipeline that:
1. Generates Property Intelligence Report for target
2. Generates Property Intelligence Report for comparables
3. Runs Comparative Gap Analysis
4. Generates Renovation Scope (via V0.3 pricing pipeline)

This is the main entry point for the complete analysis.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import steps
from .steps.property_intelligence import (
    generate_property_intelligence_report,
    save_property_intelligence_report,
)
from .steps.comparative_gap_analysis import (
    generate_comparative_gap_analysis,
    generate_aggregated_gap_analysis,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA LOADING HELPERS
# =============================================================================

def get_output_dir() -> Path:
    """Get output directory for pipeline results."""
    output_dir = Path(__file__).parent.parent / "output" / "v032_pipeline"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


async def load_listing_data(listing_id: int, supabase_client: Any = None) -> Optional[Dict]:
    """Load listing data from database or file."""
    try:
        if supabase_client:
            result = supabase_client.table('listings').select('*').eq('id', listing_id).execute()
            if result.data:
                return result.data[0]
        
        # Fallback: try loading from output file
        output_dir = Path(__file__).parent.parent / "output"
        possible_files = [
            output_dir / f"listing_{listing_id}.json",
            output_dir / f"listings/{listing_id}.json",
        ]
        for f in possible_files:
            if f.exists():
                with open(f, 'r', encoding='utf-8') as file:
                    return json.load(file)
        
        return None
    except Exception as e:
        logger.error(f"Failed to load listing {listing_id}: {e}")
        return None


async def load_room_clusters(listing_id: int, supabase_client: Any = None) -> List[Dict]:
    """Load room clusters for a listing."""
    try:
        if supabase_client:
            result = supabase_client.table('room_clusters').select('*').eq('listing_id', listing_id).execute()
            if result.data:
                return result.data
        
        # Fallback: create synthetic clusters from photo URLs
        listing_data = await load_listing_data(listing_id, supabase_client)
        if listing_data and 'photo_urls' in listing_data:
            photos = listing_data.get('photo_urls', [])
            if isinstance(photos, str):
                photos = json.loads(photos)
            
            # Simple clustering: assign photos to generic rooms
            clusters = []
            if photos:
                # Split photos evenly across generic room types
                room_types = ['living_room', 'kitchen', 'bathroom', 'bedroom', 'general']
                photos_per_room = max(1, len(photos) // len(room_types))
                
                for i, room_type in enumerate(room_types):
                    start = i * photos_per_room
                    end = start + photos_per_room if i < len(room_types) - 1 else len(photos)
                    if start < len(photos):
                        clusters.append({
                            'room_id': f'room_{i+1}',
                            'room_type': room_type,
                            'room_name': room_type.replace('_', ' ').title(),
                            'photo_urls': photos[start:end],
                        })
            
            return clusters
        
        return []
    except Exception as e:
        logger.error(f"Failed to load room clusters for listing {listing_id}: {e}")
        return []


async def load_comparables(listing_id: int, supabase_client: Any = None) -> List[int]:
    """Load comparable listing IDs for a target."""
    try:
        if supabase_client:
            result = supabase_client.table('comparable_listings').select('comparable_id').eq('target_listing_id', listing_id).execute()
            if result.data:
                return [r['comparable_id'] for r in result.data]
        
        # Fallback: check if we have stored comparables
        output_dir = Path(__file__).parent.parent / "output"
        comp_file = output_dir / f"comparables_{listing_id}.json"
        if comp_file.exists():
            with open(comp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('comparable_ids', [])
        
        return []
    except Exception as e:
        logger.error(f"Failed to load comparables for listing {listing_id}: {e}")
        return []


def get_year_built(listing_data: Dict) -> Tuple[int, str]:
    """Extract year built from listing data."""
    # Try cadastre
    cadastre_year = listing_data.get('cadastre_year')
    if cadastre_year:
        return int(cadastre_year), 'cadastre'
    
    # Try listing
    listing_year = listing_data.get('year_built') or listing_data.get('construccion_year')
    if listing_year:
        return int(listing_year), 'listing'
    
    # Estimate from description
    # Default to 1980 (most common renovation target era)
    return 1980, 'estimate'


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

async def run_v032_pipeline(
    target_listing_id: int,
    comparable_listing_ids: Optional[List[int]] = None,
    supabase_client: Any = None,
    skip_comparables: bool = False,
) -> Dict:
    """
    Run the complete V0.3.2 pipeline.
    
    Args:
        target_listing_id: The target listing to analyze
        comparable_listing_ids: Optional list of comparable IDs (auto-detect if None)
        supabase_client: Optional Supabase client
        skip_comparables: If True, only generate target PIR (no gap analysis)
    
    Returns:
        Dict with pipeline results
    """
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info(f"V0.3.2 PIPELINE START - Target Listing {target_listing_id}")
    logger.info("=" * 70)
    
    results = {
        'target_listing_id': target_listing_id,
        'started_at': start_time.isoformat(),
        'steps': {},
        'success': False,
    }
    
    # ==========================================================================
    # STEP 1: Load target data
    # ==========================================================================
    logger.info("\n📥 STEP 1: Loading target listing data...")
    
    target_data = await load_listing_data(target_listing_id, supabase_client)
    if not target_data:
        results['error'] = f"Failed to load target listing {target_listing_id}"
        logger.error(results['error'])
        return results
    
    year_built, year_source = get_year_built(target_data)
    target_clusters = await load_room_clusters(target_listing_id, supabase_client)
    
    logger.info(f"  ✅ Loaded listing: {target_data.get('address', 'Unknown')}")
    logger.info(f"  ✅ Year built: {year_built} (source: {year_source})")
    logger.info(f"  ✅ Room clusters: {len(target_clusters)}")
    
    results['steps']['load_target'] = {
        'success': True,
        'address': target_data.get('address'),
        'year_built': year_built,
        'clusters': len(target_clusters),
    }
    
    # ==========================================================================
    # STEP 2: Generate Target Property Intelligence Report
    # ==========================================================================
    logger.info("\n🔍 STEP 2: Generating Target Property Intelligence Report...")
    
    target_pir = await generate_property_intelligence_report(
        listing_id=target_listing_id,
        listing_data=target_data,
        year_built=year_built,
        year_source=year_source,
        room_clusters=target_clusters,
    )
    
    if not target_pir:
        results['error'] = "Failed to generate target PIR"
        logger.error(results['error'])
        return results
    
    # Save target PIR
    await save_property_intelligence_report(target_pir, target_listing_id, supabase_client)
    
    results['steps']['target_pir'] = {
        'success': True,
        'rooms_analyzed': len(target_pir.get('rooms', [])) if isinstance(target_pir, dict) else len(getattr(target_pir, 'rooms', [])),
    }
    results['target_pir'] = target_pir if isinstance(target_pir, dict) else target_pir.model_dump()
    
    if skip_comparables:
        logger.info("\n⏭️ Skipping comparables (skip_comparables=True)")
        results['success'] = True
        results['completed_at'] = datetime.now().isoformat()
        return results
    
    # ==========================================================================
    # STEP 3: Load Comparables
    # ==========================================================================
    logger.info("\n📥 STEP 3: Loading comparable listings...")
    
    if comparable_listing_ids is None:
        comparable_listing_ids = await load_comparables(target_listing_id, supabase_client)
    
    if not comparable_listing_ids:
        logger.warning("  ⚠️ No comparables found - generating target-only report")
        results['steps']['comparables'] = {
            'success': True,
            'count': 0,
            'note': 'No comparables available',
        }
        results['success'] = True
        results['completed_at'] = datetime.now().isoformat()
        return results
    
    logger.info(f"  ✅ Found {len(comparable_listing_ids)} comparables: {comparable_listing_ids}")
    
    results['steps']['comparables'] = {
        'success': True,
        'count': len(comparable_listing_ids),
        'ids': comparable_listing_ids,
    }
    
    # ==========================================================================
    # STEP 4: Generate Comparable PIRs
    # ==========================================================================
    logger.info("\n🔍 STEP 4: Generating Comparable Property Intelligence Reports...")
    
    comparable_pirs = []
    for comp_id in comparable_listing_ids:
        logger.info(f"  Processing comparable {comp_id}...")
        
        comp_data = await load_listing_data(comp_id, supabase_client)
        if not comp_data:
            logger.warning(f"    ⚠️ Failed to load comparable {comp_id}")
            continue
        
        comp_year, comp_year_source = get_year_built(comp_data)
        comp_clusters = await load_room_clusters(comp_id, supabase_client)
        
        comp_pir = await generate_property_intelligence_report(
            listing_id=comp_id,
            listing_data=comp_data,
            year_built=comp_year,
            year_source=comp_year_source,
            room_clusters=comp_clusters,
        )
        
        if comp_pir:
            await save_property_intelligence_report(comp_pir, comp_id, supabase_client)
            comparable_pirs.append({
                'listing_id': comp_id,
                'pir': comp_pir if isinstance(comp_pir, dict) else comp_pir.model_dump(),
            })
            logger.info(f"    ✅ Generated PIR for comparable {comp_id}")
    
    results['steps']['comparable_pirs'] = {
        'success': len(comparable_pirs) > 0,
        'generated': len(comparable_pirs),
        'failed': len(comparable_listing_ids) - len(comparable_pirs),
    }
    
    if not comparable_pirs:
        logger.warning("  ⚠️ No comparable PIRs generated")
        results['success'] = True
        results['completed_at'] = datetime.now().isoformat()
        return results
    
    # ==========================================================================
    # STEP 5: Comparative Gap Analysis
    # ==========================================================================
    logger.info("\n📊 STEP 5: Running Comparative Gap Analysis...")
    
    target_pir_dict = target_pir if isinstance(target_pir, dict) else target_pir.model_dump()
    
    gap_analysis = await generate_aggregated_gap_analysis(
        target_pir=target_pir_dict,
        comparable_pirs=[c['pir'] for c in comparable_pirs],
        target_listing_id=target_listing_id,
        comparable_listing_ids=[c['listing_id'] for c in comparable_pirs],
    )
    
    if not gap_analysis:
        results['error'] = "Failed to generate gap analysis"
        logger.error(results['error'])
        return results
    
    results['steps']['gap_analysis'] = {
        'success': True,
        'intervention_count': gap_analysis.get('aggregated', {}).get('intervention_count', 0),
        'scope_level': gap_analysis.get('aggregated', {}).get('scope_level_consensus', 'unknown'),
    }
    results['gap_analysis'] = gap_analysis
    
    logger.info(f"  ✅ Gap analysis complete")
    logger.info(f"     Interventions: {gap_analysis.get('aggregated', {}).get('intervention_count', 0)}")
    logger.info(f"     Scope level: {gap_analysis.get('aggregated', {}).get('scope_level_consensus', 'unknown')}")
    
    # ==========================================================================
    # STEP 6: Save Results
    # ==========================================================================
    logger.info("\n💾 STEP 6: Saving pipeline results...")
    
    output_dir = get_output_dir()
    output_file = output_dir / f"v032_result_{target_listing_id}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"  ✅ Saved to {output_file}")
    
    # ==========================================================================
    # COMPLETE
    # ==========================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    results['success'] = True
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = duration
    
    logger.info("\n" + "=" * 70)
    logger.info(f"V0.3.2 PIPELINE COMPLETE - {duration:.1f}s")
    logger.info("=" * 70)
    
    return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

async def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='V0.3.2 Pipeline Orchestrator')
    parser.add_argument('listing_id', type=int, help='Target listing ID')
    parser.add_argument('--comparables', type=int, nargs='*', help='Comparable listing IDs')
    parser.add_argument('--skip-comparables', action='store_true', help='Skip comparable analysis')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
    )
    
    # Run pipeline
    results = await run_v032_pipeline(
        target_listing_id=args.listing_id,
        comparable_listing_ids=args.comparables,
        skip_comparables=args.skip_comparables,
    )
    
    print("\n" + "=" * 70)
    print("PIPELINE RESULTS")
    print("=" * 70)
    print(json.dumps({
        'success': results.get('success'),
        'duration': results.get('duration_seconds'),
        'steps': results.get('steps'),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

