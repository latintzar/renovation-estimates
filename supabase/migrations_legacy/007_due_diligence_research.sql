-- Migration: Due Diligence Research Table
-- Section 3: Comprehensive property due diligence with AI-generated queries

-- Create the due_diligence_research table
CREATE TABLE IF NOT EXISTS due_diligence_research (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Overall risk assessment
    overall_risk_score NUMERIC(5,2),  -- 0-100
    overall_risk_level TEXT CHECK (overall_risk_level IN ('low', 'medium', 'high', 'critical', 'unknown')),
    
    -- Category results (JSONB array of category findings)
    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- All sources combined (JSONB array for easy querying)
    all_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Query stats
    total_queries INTEGER DEFAULT 0,
    total_sources INTEGER DEFAULT 0,
    
    -- Property context used for generation
    property_context JSONB,
    
    -- Model/processing info
    model_used TEXT,
    processing_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one record per listing
    CONSTRAINT unique_due_diligence_per_listing UNIQUE (listing_id)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_due_diligence_listing_id ON due_diligence_research(listing_id);
CREATE INDEX IF NOT EXISTS idx_due_diligence_risk_level ON due_diligence_research(overall_risk_level);
CREATE INDEX IF NOT EXISTS idx_due_diligence_created_at ON due_diligence_research(created_at DESC);

-- Index for searching within categories JSONB
CREATE INDEX IF NOT EXISTS idx_due_diligence_categories ON due_diligence_research USING GIN (categories);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_due_diligence_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic updated_at
DROP TRIGGER IF EXISTS trigger_due_diligence_updated_at ON due_diligence_research;
CREATE TRIGGER trigger_due_diligence_updated_at
    BEFORE UPDATE ON due_diligence_research
    FOR EACH ROW
    EXECUTE FUNCTION update_due_diligence_updated_at();

-- Enable RLS
ALTER TABLE due_diligence_research ENABLE ROW LEVEL SECURITY;

-- RLS Policies (allow all for now, can be restricted later)
DROP POLICY IF EXISTS "Allow all access to due_diligence_research" ON due_diligence_research;
CREATE POLICY "Allow all access to due_diligence_research"
    ON due_diligence_research
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE due_diligence_research IS 'Section 3: AI-powered property due diligence across 7 mega-categories';
COMMENT ON COLUMN due_diligence_research.categories IS 'Array of category results with findings, sources, and risk levels';
COMMENT ON COLUMN due_diligence_research.all_sources IS 'Flattened array of all sources for easy UI rendering';
COMMENT ON COLUMN due_diligence_research.overall_risk_score IS 'Weighted average risk score across all categories (0-100)';

