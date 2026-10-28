-- Migration: 004_renovation_reports
-- Purpose: Store Pre-Inspection Renovation Reports with Essential/Modern packages
-- Date: 2026-01-05

-- ============================================================================
-- TABLE: renovation_reports
-- ============================================================================
-- Stores the generated renovation report for each listing.
-- One report per listing, upserted on regeneration.

CREATE TABLE IF NOT EXISTS renovation_reports (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Age estimation
    year_estimated INTEGER,
    year_confidence DECIMAL(3,2),  -- 0.00 to 1.00
    
    -- Summary
    summary TEXT,
    
    -- Package totals for quick access
    essential_total DECIMAL(12,2) DEFAULT 0,
    modern_total DECIMAL(12,2) DEFAULT 0,
    
    -- Full report data (JSON)
    -- Contains: packages, room_details, detected_conditions
    report_data JSONB DEFAULT '{}',
    
    -- Metadata
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one report per listing
    CONSTRAINT unique_listing_report UNIQUE (listing_id)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_renovation_reports_listing_id 
    ON renovation_reports(listing_id);

-- Enable RLS
ALTER TABLE renovation_reports ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read reports (they're public for listings)
CREATE POLICY "Enable read access for all users" ON renovation_reports
    FOR SELECT USING (true);

-- Policy: Service role can insert/update
CREATE POLICY "Enable insert for service role" ON renovation_reports
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for service role" ON renovation_reports
    FOR UPDATE USING (true);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_renovation_reports_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_renovation_reports_timestamp
    BEFORE UPDATE ON renovation_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_renovation_reports_timestamp();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE renovation_reports IS 'Pre-Inspection Renovation Reports with Essential (Safety) and Modern (Comfort) packages';
COMMENT ON COLUMN renovation_reports.year_estimated IS 'Estimated year of construction from visual analysis';
COMMENT ON COLUMN renovation_reports.year_confidence IS 'Confidence score for year estimation (0-1)';
COMMENT ON COLUMN renovation_reports.essential_total IS 'Total cost of Essential (Safety/Compliance) package';
COMMENT ON COLUMN renovation_reports.modern_total IS 'Total cost of Modern (Efficiency/Comfort) package';
COMMENT ON COLUMN renovation_reports.report_data IS 'Full report JSON including items, room_details, detected_conditions';

