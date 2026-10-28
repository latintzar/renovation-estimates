-- =============================================================================
-- V0.4.8 Database Tables Migration
-- =============================================================================
-- 
-- Tables for the 9-Phase Unified Estimator:
-- - package_generation_progress: Checkpoint tracking
-- - unified_estimates_v048: Package estimates
-- - property_intelligence_reports_v048: PIR storage
-- - photo_clusters_v048: Photo clustering results
--
-- Run: npx supabase db push
-- =============================================================================

-- =============================================================================
-- 1. PACKAGE GENERATION PROGRESS (Checkpointing)
-- =============================================================================

CREATE TABLE IF NOT EXISTS package_generation_progress (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Checkpoint tracking
    checkpoint TEXT NOT NULL,
    checkpoint_data JSONB,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT,
    
    -- Status
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed')),
    error_message TEXT,
    
    -- Metadata
    model_version TEXT DEFAULT 'V0.4.8',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one checkpoint per listing
    UNIQUE(listing_id, checkpoint)
);

-- Index for fast checkpoint lookups
CREATE INDEX IF NOT EXISTS idx_pkg_progress_listing 
ON package_generation_progress(listing_id, checkpoint);

-- =============================================================================
-- 2. UNIFIED ESTIMATES (Package Storage)
-- =============================================================================

CREATE TABLE IF NOT EXISTS unified_estimates_v048 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Package type
    package_type TEXT NOT NULL CHECK (package_type IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- The estimate (full JSON)
    estimate_data JSONB NOT NULL,
    
    -- Key summary fields (for quick queries)
    total_cost DECIMAL(12, 2),
    cost_per_m2 DECIMAL(10, 2),
    total_weeks INTEGER,
    room_count INTEGER,
    line_item_count INTEGER,
    
    -- Validation metrics
    room_attribution_pct FLOAT,
    kg_grounding_pct FLOAT,
    bcca_match_pct FLOAT,
    
    -- Quality
    sanity_check_passed BOOLEAN DEFAULT TRUE,
    overall_confidence TEXT CHECK (overall_confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    
    -- Metadata
    model_version TEXT DEFAULT 'V0.4.8',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    phase_durations JSONB,  -- Time per phase for cost analysis
    
    -- Unique: one estimate per listing per package type
    UNIQUE(listing_id, package_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_estimates_listing ON unified_estimates_v048(listing_id);
CREATE INDEX IF NOT EXISTS idx_estimates_cost ON unified_estimates_v048(total_cost);

-- =============================================================================
-- 3. PROPERTY INTELLIGENCE REPORTS (PIR Storage)
-- =============================================================================

CREATE TABLE IF NOT EXISTS property_intelligence_reports_v048 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- PIR type
    pir_type TEXT NOT NULL CHECK (pir_type IN ('target', 'comparable')),
    
    -- The PIR (full JSON)
    pir_data JSONB NOT NULL,
    
    -- Key fields (for quick queries)
    room_count INTEGER,
    year_built INTEGER,
    year_source TEXT,
    condition_score INTEGER,
    
    -- Photo analysis
    total_photos INTEGER,
    ai_image_count INTEGER,
    cluster_count INTEGER,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique: one PIR per listing
    UNIQUE(listing_id, pir_type)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_pir_listing ON property_intelligence_reports_v048(listing_id);

-- =============================================================================
-- 4. PHOTO CLUSTERS (V0.4.8 version)
-- =============================================================================

CREATE TABLE IF NOT EXISTS photo_clusters_v048 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Cluster info
    cluster_id TEXT NOT NULL,
    cluster_name TEXT,
    room_type TEXT,
    
    -- Photos
    photo_urls JSONB,  -- Array of URLs
    photo_count INTEGER,
    
    -- AI detection
    is_real BOOLEAN DEFAULT TRUE,
    confidence FLOAT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_clusters_v048_listing ON photo_clusters_v048(listing_id);

-- =============================================================================
-- 5. HELPER FUNCTIONS
-- =============================================================================

-- Function to update listing with year info
CREATE OR REPLACE FUNCTION update_listing_year(
    p_listing_id BIGINT,
    p_year_built INTEGER,
    p_year_source TEXT
) RETURNS VOID AS $$
BEGIN
    UPDATE listings
    SET 
        year_built = p_year_built,
        year_source = p_year_source,
        updated_at = NOW()
    WHERE id = p_listing_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest checkpoint for a listing
CREATE OR REPLACE FUNCTION get_latest_checkpoint(p_listing_id BIGINT)
RETURNS TEXT AS $$
DECLARE
    latest_checkpoint TEXT;
BEGIN
    SELECT checkpoint INTO latest_checkpoint
    FROM package_generation_progress
    WHERE listing_id = p_listing_id
      AND status = 'completed'
    ORDER BY completed_at DESC
    LIMIT 1;
    
    RETURN latest_checkpoint;
END;
$$ LANGUAGE plpgsql;

-- Function to check if package generation is complete
CREATE OR REPLACE FUNCTION is_package_generation_complete(p_listing_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    visuals_done BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM package_generation_progress
        WHERE listing_id = p_listing_id
          AND checkpoint = 'visuals_complete'
          AND status = 'completed'
    ) INTO visuals_done;
    
    RETURN visuals_done;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 6. ADD COLUMNS TO EXISTING TABLES (if not exist)
-- =============================================================================

-- Add year columns to listings if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'year_built') THEN
        ALTER TABLE listings ADD COLUMN year_built INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'year_source') THEN
        ALTER TABLE listings ADD COLUMN year_source TEXT;
    END IF;
END $$;

-- =============================================================================
-- 7. COMMENTS
-- =============================================================================

COMMENT ON TABLE package_generation_progress IS 'V0.4.8 checkpoint tracking for resume capability';
COMMENT ON TABLE unified_estimates_v048 IS 'V0.4.8 package estimates (fast_sell, fair_market, out_of_market)';
COMMENT ON TABLE property_intelligence_reports_v048 IS 'V0.4.8 Property Intelligence Reports for target and comparables';
COMMENT ON TABLE photo_clusters_v048 IS 'V0.4.8 photo clustering results with AI detection';

-- Done!
SELECT 'V0.4.8 migration complete' AS status;

