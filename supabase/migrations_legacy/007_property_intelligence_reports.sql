-- V0.3.2: Property Intelligence Reports Table
-- PETER AGENTIC V0.3.2

-- =============================================================================
-- PROPERTY INTELLIGENCE REPORTS
-- Stores comprehensive property analysis from V0.3.2 pipeline
-- =============================================================================

CREATE TABLE IF NOT EXISTS property_intelligence_reports (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Report data (full PropertyIntelligenceReport JSON)
    report_data JSONB NOT NULL,
    
    -- Key attributes extracted for quick access
    year_built INTEGER,
    year_source TEXT CHECK (year_source IN ('cadastre', 'listing', 'estimate')),
    energy_rating TEXT,
    energy_expected TEXT,
    finish_tier TEXT CHECK (finish_tier IN ('builder_grade', 'mid_range', 'high_end', 'luxury')),
    dominant_style TEXT,
    construction_era TEXT,
    
    -- Comparison attributes (JSONB for flexibility)
    comparison_attributes JSONB,
    
    -- Triggers identified
    triggers JSONB,
    trigger_count INTEGER DEFAULT 0,
    
    -- Regulatory assessment
    regulatory_assessment JSONB,
    has_cte_concerns BOOLEAN DEFAULT FALSE,
    has_rebt_concerns BOOLEAN DEFAULT FALSE,
    has_ite_concerns BOOLEAN DEFAULT FALSE,
    
    -- Rooms analyzed
    rooms_analyzed JSONB,
    room_count INTEGER DEFAULT 0,
    
    -- Metadata
    version TEXT DEFAULT 'v0.3.2',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one report per listing
    UNIQUE(listing_id)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_pir_listing ON property_intelligence_reports(listing_id);
CREATE INDEX IF NOT EXISTS idx_pir_energy ON property_intelligence_reports(energy_rating);
CREATE INDEX IF NOT EXISTS idx_pir_finish ON property_intelligence_reports(finish_tier);
CREATE INDEX IF NOT EXISTS idx_pir_era ON property_intelligence_reports(construction_era);

-- Full text search on report data
CREATE INDEX IF NOT EXISTS idx_pir_report_gin ON property_intelligence_reports USING GIN (report_data);

-- =============================================================================
-- COMPARATIVE GAP ANALYSES
-- Stores gap analysis results between target and comparables
-- =============================================================================

CREATE TABLE IF NOT EXISTS comparative_gap_analyses (
    id BIGSERIAL PRIMARY KEY,
    target_listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    comparable_listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Gap analysis data
    analysis_data JSONB NOT NULL,
    
    -- Summary fields
    gap_letters INTEGER,  -- Energy rating gap
    scope_level TEXT CHECK (scope_level IN ('cosmetic', 'moderate', 'comprehensive', 'full_gut')),
    intervention_count INTEGER DEFAULT 0,
    
    -- All intervention IDs (for KG lookup)
    intervention_ids TEXT[],
    
    -- Permits required
    permits_required JSONB,
    
    -- Risk factors
    risk_factors JSONB,
    
    -- Metadata
    version TEXT DEFAULT 'v0.3.2',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per target-comparable pair
    UNIQUE(target_listing_id, comparable_listing_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cga_target ON comparative_gap_analyses(target_listing_id);
CREATE INDEX IF NOT EXISTS idx_cga_comparable ON comparative_gap_analyses(comparable_listing_id);
CREATE INDEX IF NOT EXISTS idx_cga_scope ON comparative_gap_analyses(scope_level);

-- =============================================================================
-- AGGREGATED GAP ANALYSES
-- Stores aggregated gap analysis from multiple comparables
-- =============================================================================

CREATE TABLE IF NOT EXISTS aggregated_gap_analyses (
    id BIGSERIAL PRIMARY KEY,
    target_listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Comparables used
    comparable_listing_ids BIGINT[] NOT NULL,
    comparable_count INTEGER NOT NULL,
    
    -- Aggregated results
    aggregated_data JSONB NOT NULL,
    
    -- Consensus values
    scope_level_consensus TEXT CHECK (scope_level_consensus IN ('cosmetic', 'moderate', 'comprehensive', 'full_gut')),
    total_intervention_count INTEGER DEFAULT 0,
    energy_gap_letters INTEGER,
    
    -- All intervention IDs (union across all comparisons)
    all_intervention_ids TEXT[],
    
    -- Metadata
    version TEXT DEFAULT 'v0.3.2',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One aggregated analysis per target
    UNIQUE(target_listing_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_aga_target ON aggregated_gap_analyses(target_listing_id);
CREATE INDEX IF NOT EXISTS idx_aga_scope ON aggregated_gap_analyses(scope_level_consensus);

-- =============================================================================
-- TRIGGER FOR updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to property_intelligence_reports
DROP TRIGGER IF EXISTS update_pir_updated_at ON property_intelligence_reports;
CREATE TRIGGER update_pir_updated_at
    BEFORE UPDATE ON property_intelligence_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to aggregated_gap_analyses
DROP TRIGGER IF EXISTS update_aga_updated_at ON aggregated_gap_analyses;
CREATE TRIGGER update_aga_updated_at
    BEFORE UPDATE ON aggregated_gap_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE property_intelligence_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparative_gap_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_gap_analyses ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users
CREATE POLICY "Allow read access" ON property_intelligence_reports
    FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON comparative_gap_analyses
    FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON aggregated_gap_analyses
    FOR SELECT USING (true);

-- Allow insert/update for service role
CREATE POLICY "Allow service insert" ON property_intelligence_reports
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service update" ON property_intelligence_reports
    FOR UPDATE USING (true);
CREATE POLICY "Allow service insert" ON comparative_gap_analyses
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service insert" ON aggregated_gap_analyses
    FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service update" ON aggregated_gap_analyses
    FOR UPDATE USING (true);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE property_intelligence_reports IS 'V0.3.2 Property Intelligence Reports - comprehensive property analysis';
COMMENT ON TABLE comparative_gap_analyses IS 'V0.3.2 Comparative Gap Analyses - individual target vs comparable comparisons';
COMMENT ON TABLE aggregated_gap_analyses IS 'V0.3.2 Aggregated Gap Analyses - combined analysis from multiple comparables';

