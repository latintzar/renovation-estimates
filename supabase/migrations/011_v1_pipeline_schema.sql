-- =============================================================================
-- V1.0 Pipeline Database Schema Migration
-- =============================================================================
-- 
-- MIGRATION FOR: 8-Phase Ultimate Pipeline
-- 
-- Changes:
-- 1. Enhanced smart_m2 table with wall dimensions
-- 2. New unified_estimates_v1 table for 8-phase output
-- 3. New viewing_checklists_v1 table (Phase 6)
-- 4. New eli5_summaries_v1 table (Phase 7)
-- 5. New architect_reports_v1 table (Phase 8)
-- 6. Update package_generation_progress for V1.0 checkpoints
--
-- Run: npx supabase db push
-- =============================================================================

-- =============================================================================
-- 1. ENHANCED SMART_M2 TABLE
-- =============================================================================
-- Add wall dimensions to existing smart_m2 table (backward compatible)

-- Add new column for enhanced room data if not exists
DO $$ 
BEGIN
    -- The existing 'rooms' JSONB column will now store richer data:
    -- [{ 
    --   cluster_name, cluster_id, estimated_m2, 
    --   estimated_dimensions: { length_m, width_m, aspect_ratio, dimension_confidence },
    --   wall_descriptions: [{ name, name_es, length_m, features }],
    --   estimated_height_m, perimeter_m, wall_area_m2,
    --   confidence, reasoning 
    -- }]
    
    -- Add methodology column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'smart_m2' 
                   AND column_name = 'dimension_methodology') THEN
        ALTER TABLE smart_m2 ADD COLUMN dimension_methodology TEXT;
    END IF;
    
    -- Add version column to distinguish enhanced vs legacy data
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'smart_m2' 
                   AND column_name = 'schema_version') THEN
        ALTER TABLE smart_m2 ADD COLUMN schema_version TEXT DEFAULT 'v1.0';
    END IF;
END $$;

-- Update comments
COMMENT ON COLUMN smart_m2.rooms IS 'V1.0 Enhanced: [{cluster_name, cluster_id, estimated_m2, estimated_dimensions, wall_descriptions, estimated_height_m, perimeter_m, wall_area_m2, confidence, reasoning}]';
COMMENT ON COLUMN smart_m2.dimension_methodology IS 'How dimensions were estimated (e.g., "architectural proportions from total m²")';
COMMENT ON COLUMN smart_m2.schema_version IS 'Schema version: v1.0 includes wall dimensions';

-- =============================================================================
-- 2. UNIFIED ESTIMATES V1.0
-- =============================================================================
-- Stores the complete output from 8-phase pipeline

CREATE TABLE IF NOT EXISTS unified_estimates_v1 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Package type (same as V0.5)
    package_type TEXT NOT NULL CHECK (package_type IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- Phase outputs (JSONB for flexibility)
    phase_1_scope_boq JSONB,           -- Scope + BoQ items with BCCA codes
    phase_2_priced_items JSONB,        -- Items with prices (code lookup)
    phase_3_peer_review JSONB,         -- Reviewed items with adjustments
    phase_4_rendering_prompts JSONB,   -- AI image prompts
    phase_5_generated_images JSONB,    -- Image URLs from external service
    phase_6_viewing_checklist JSONB,   -- 20-minute viewing guide
    phase_7_eli5_summaries JSONB,      -- Plain language summaries
    phase_8_architect_report JSONB,    -- Professional report structure
    
    -- Key summary fields (for quick queries)
    total_cost DECIMAL(12, 2),
    cost_per_sqm DECIMAL(10, 2),
    total_weeks INTEGER,
    rooms_count INTEGER,
    line_items_count INTEGER,
    
    -- IVA breakdown (Spanish standard)
    pem_subtotal DECIMAL(12, 2),
    overhead_13pct DECIMAL(12, 2),
    profit_6pct DECIMAL(12, 2),
    iva_21pct DECIMAL(12, 2),
    final_total_with_iva DECIMAL(12, 2),
    
    -- Quality metrics
    confidence_score INTEGER CHECK (confidence_score BETWEEN 1 AND 100),
    sanity_check_passed BOOLEAN DEFAULT TRUE,
    cost_per_sqm_assessment TEXT,
    
    -- Energy compliance
    energy_current_rating TEXT,
    energy_target_rating TEXT,
    energy_improvement_letters INTEGER,
    energy_pathway_valid BOOLEAN,
    
    -- Risk flags
    risk_flags JSONB,
    recommendations JSONB,
    
    -- Phase execution metadata
    phase_times JSONB,                 -- Duration per phase
    phases_completed INTEGER DEFAULT 0,
    
    -- Version tracking
    model_version TEXT DEFAULT 'V1.0',
    pipeline_version TEXT DEFAULT '8-phase',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique: one estimate per listing per package type
    UNIQUE(listing_id, package_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_estimates_v1_listing ON unified_estimates_v1(listing_id);
CREATE INDEX IF NOT EXISTS idx_estimates_v1_cost ON unified_estimates_v1(total_cost);
CREATE INDEX IF NOT EXISTS idx_estimates_v1_package ON unified_estimates_v1(package_type);

-- Comments
COMMENT ON TABLE unified_estimates_v1 IS 'V1.0 8-Phase Pipeline: Complete renovation estimates with all phase outputs';
COMMENT ON COLUMN unified_estimates_v1.phase_1_scope_boq IS 'Phase 1: Scope + BoQ with BCCA codes, quantities, schedule';
COMMENT ON COLUMN unified_estimates_v1.phase_2_priced_items IS 'Phase 2: Code-based price lookup (deterministic)';
COMMENT ON COLUMN unified_estimates_v1.phase_3_peer_review IS 'Phase 3: Peer reviewed items with adjustments';
COMMENT ON COLUMN unified_estimates_v1.phase_7_eli5_summaries IS 'Phase 7: Plain language buyer summaries';
COMMENT ON COLUMN unified_estimates_v1.phase_8_architect_report IS 'Phase 8: Professional architect report by trades';

-- =============================================================================
-- 3. VIEWING CHECKLISTS (Phase 6 Output)
-- =============================================================================
-- Separate table for viewing checklists (useful for API queries)

CREATE TABLE IF NOT EXISTS viewing_checklists_v1 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    package_type TEXT NOT NULL CHECK (package_type IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- Checklist content
    address TEXT,
    total_duration_minutes INTEGER,
    mode1_sensory JSONB,               -- First impressions checks
    mode2_inspect JSONB,               -- Room-by-room checks
    mode3_ask JSONB,                   -- Questions for agent
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, package_type)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_viewing_v1_listing ON viewing_checklists_v1(listing_id);

-- Comment
COMMENT ON TABLE viewing_checklists_v1 IS 'V1.0 Phase 6: 20-minute property viewing checklists';

-- =============================================================================
-- 4. ELI5 SUMMARIES (Phase 7 Output)
-- =============================================================================
-- Separate table for buyer-friendly summaries

CREATE TABLE IF NOT EXISTS eli5_summaries_v1 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    package_type TEXT NOT NULL CHECK (package_type IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- Summary content
    property_summary JSONB,            -- Address, total cost, weeks
    energy_eli5 JSONB,                 -- Plain language energy explanation
    rooms JSONB,                       -- Per-room ELI5 summaries
    general_items_eli5 JSONB,          -- Site-wide items
    timeline_eli5 JSONB,               -- Timeline explanation
    
    -- Key metrics (for quick display)
    total_cost DECIMAL(12, 2),
    total_weeks INTEGER,
    rooms_count INTEGER,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, package_type)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_eli5_v1_listing ON eli5_summaries_v1(listing_id);

-- Comment
COMMENT ON TABLE eli5_summaries_v1 IS 'V1.0 Phase 7: Plain language room summaries for buyers';

-- =============================================================================
-- 5. ARCHITECT REPORTS (Phase 8 Output)
-- =============================================================================
-- Separate table for professional reports

CREATE TABLE IF NOT EXISTS architect_reports_v1 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    package_type TEXT NOT NULL CHECK (package_type IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- Report structure
    document_header JSONB,             -- Title, reference, date
    executive_summary JSONB,           -- Key numbers
    cost_breakdown JSONB,              -- PEM, overhead, profit, IVA
    by_trade JSONB,                    -- Items organized by BCCA chapter
    by_room JSONB,                     -- Cost per room
    timeline JSONB,                    -- Phases, milestones, critical path
    energy_compliance JSONB,           -- CTE DB-HE compliance
    compliance_notes JSONB,            -- Standards, permits
    risk_flags JSONB,
    recommendations JSONB,
    
    -- Quality
    confidence_score INTEGER,
    sanity_check_passed BOOLEAN,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, package_type)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_architect_v1_listing ON architect_reports_v1(listing_id);

-- Comment
COMMENT ON TABLE architect_reports_v1 IS 'V1.0 Phase 8: Professional architect reports by trade';

-- =============================================================================
-- 6. UPDATE PACKAGE GENERATION PROGRESS FOR V1.0
-- =============================================================================
-- Extend checkpoint values for 8-phase pipeline

ALTER TABLE package_generation_progress 
DROP CONSTRAINT IF EXISTS package_generation_progress_checkpoint_check;

-- V1.0 checkpoints (8 phases)
-- Note: Phase 2 (code) and Phase 5 (external) don't need separate checkpoints
ALTER TABLE package_generation_progress
ADD CONSTRAINT package_generation_progress_checkpoint_check CHECK (
    checkpoint IN (
        -- Legacy V0.4.8/V0.5 checkpoints (keep for backward compat)
        'clustering_complete',
        'year_estimation_complete',
        'images_cached',
        'pir_target_complete',
        'pir_comparables_complete',
        'bracket_pirs_synthesized',
        'strategic_reasoning_complete',
        'estimate_fast_sell_complete',
        'estimate_fair_market_complete',
        'estimate_out_of_market_complete',
        'visuals_complete',
        'viewing_guide_complete',
        -- V1.0 NEW checkpoints
        'smart_m2_complete',           -- M1: Enhanced with dimensions
        'phase_1_scope_boq_complete',  -- Phase 1
        'phase_2_pricing_complete',    -- Phase 2 (code)
        'phase_3_peer_review_complete', -- Phase 3
        'phase_4_prompts_complete',    -- Phase 4
        'phase_5_images_complete',     -- Phase 5 (external)
        'phase_6_checklist_complete',  -- Phase 6
        'phase_7_eli5_complete',       -- Phase 7
        'phase_8_report_complete',     -- Phase 8
        'v1_pipeline_complete'         -- All phases done
    )
);

-- =============================================================================
-- 7. HELPER FUNCTIONS
-- =============================================================================

-- Get V1 estimate for a listing/package
CREATE OR REPLACE FUNCTION get_v1_estimate(
    p_listing_id BIGINT,
    p_package_type TEXT
) RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_cost', total_cost,
        'total_weeks', total_weeks,
        'line_items_count', line_items_count,
        'confidence_score', confidence_score,
        'phases_completed', phases_completed,
        'has_eli5', phase_7_eli5_summaries IS NOT NULL,
        'has_report', phase_8_architect_report IS NOT NULL
    ) INTO result
    FROM unified_estimates_v1
    WHERE listing_id = p_listing_id AND package_type = p_package_type;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Check if V1 pipeline is complete
CREATE OR REPLACE FUNCTION is_v1_pipeline_complete(p_listing_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS(
        SELECT 1 FROM package_generation_progress
        WHERE listing_id = p_listing_id
          AND checkpoint = 'v1_pipeline_complete'
          AND status = 'completed'
    );
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. DATA MIGRATION (Optional - Run manually if needed)
-- =============================================================================
-- Migrate existing smart_m2 data to V1.0 schema format
-- This is OPTIONAL - only run if you have existing data to migrate

-- UPDATE smart_m2 SET schema_version = 'v0.5' WHERE schema_version IS NULL;

-- =============================================================================
-- DONE
-- =============================================================================

SELECT 'V1.0 Pipeline migration complete' AS status;
