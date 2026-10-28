-- ============================================================================
-- Migration 008: Comparables Tables
-- ============================================================================
-- 
-- Tables for storing Casafari comparable properties and their analyses.
-- 
-- Features:
-- 1. listing_market_stats: Market statistics and price estimates
-- 2. listing_comparables: Individual comparable properties with analyses
--
-- Usage:
-- - Run via Supabase MCP: apply_migration("008_comparables_tables", <this SQL>)
-- - Or run directly in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- Table 1: Market Statistics
-- ============================================================================
-- Stores market statistics and price estimates from Casafari for a listing.
-- One row per listing.

CREATE TABLE IF NOT EXISTS listing_market_stats (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Price estimates from Casafari
    fast_sell_price INTEGER,           -- Below market price for quick sale
    fair_market_price INTEGER,         -- True market value
    out_of_market_price INTEGER,       -- Above market (slow to sell)
    
    -- Market statistics
    average_price INTEGER,             -- Average price of comparables
    average_price_per_sqm INTEGER,     -- Average €/m² in area
    average_days_on_market INTEGER,    -- Days to sell (average)
    sold_last_6_months INTEGER,        -- Transaction volume
    
    -- Casafari data
    casafari_link TEXT,                -- Link to Casafari analysis
    search_params JSONB,               -- Parameters used for search
    raw_response JSONB,                -- Full Casafari response (optional)
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One market stats record per listing
    UNIQUE(listing_id)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_market_stats_listing 
    ON listing_market_stats(listing_id);


-- ============================================================================
-- Table 2: Comparable Properties
-- ============================================================================
-- Stores individual comparable properties from Casafari with our analysis results.
-- Multiple rows per listing (typically 9: 3 per price bucket).

CREATE TABLE IF NOT EXISTS listing_comparables (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    casafari_property_id BIGINT NOT NULL,
    
    -- Price bucket classification
    price_bucket TEXT NOT NULL CHECK (price_bucket IN ('fast_sell', 'fair_market', 'out_of_market')),
    
    -- Property data from Casafari
    sale_price INTEGER,
    price_per_sqm INTEGER,
    total_area INTEGER,
    bedrooms INTEGER,
    bathrooms INTEGER,
    condition TEXT,
    construction_year INTEGER,
    distance_km NUMERIC(5,2),          -- Distance from target listing
    address TEXT,
    zip_code TEXT,
    property_url TEXT,
    photo_urls JSONB,                  -- Array of photo URLs
    coordinates JSONB,                 -- {latitude, longitude}
    features JSONB,                    -- {floor, orientation, view, characteristics}
    energy_rating TEXT,
    days_on_market INTEGER,
    
    -- OUR ANALYSIS RESULTS (from verify_rules.py and assess_uniclass.py)
    rule_verifications JSONB,          -- Results from verify_rules.py
    uniclass_assessments JSONB,        -- Results from assess_uniclass.py
    compliance_summary TEXT,           -- Human-readable summary "4/5 rules passed"
    compliance_score NUMERIC(3,2),     -- 0.00 to 1.00 compliance score
    analysis_status TEXT DEFAULT 'pending' CHECK (analysis_status IN ('pending', 'running', 'complete', 'failed')),
    analysis_error TEXT,               -- Error message if analysis failed
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    analyzed_at TIMESTAMPTZ,           -- When analysis was completed
    
    -- Unique constraint: one entry per property per listing
    UNIQUE(listing_id, casafari_property_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_comparables_listing 
    ON listing_comparables(listing_id);
CREATE INDEX IF NOT EXISTS idx_comparables_bucket 
    ON listing_comparables(listing_id, price_bucket);
CREATE INDEX IF NOT EXISTS idx_comparables_status 
    ON listing_comparables(analysis_status);


-- ============================================================================
-- Trigger: Update timestamp on listing_market_stats
-- ============================================================================

CREATE OR REPLACE FUNCTION update_market_stats_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_market_stats_updated ON listing_market_stats;
CREATE TRIGGER trg_market_stats_updated
    BEFORE UPDATE ON listing_market_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_market_stats_timestamp();


-- ============================================================================
-- RLS Policies (Row Level Security)
-- ============================================================================

-- Enable RLS
ALTER TABLE listing_market_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_comparables ENABLE ROW LEVEL SECURITY;

-- Policies for listing_market_stats
CREATE POLICY "Market stats are viewable by everyone"
    ON listing_market_stats FOR SELECT
    USING (true);

CREATE POLICY "Market stats can be inserted by authenticated users"
    ON listing_market_stats FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Market stats can be updated by authenticated users"
    ON listing_market_stats FOR UPDATE
    USING (true);

-- Policies for listing_comparables
CREATE POLICY "Comparables are viewable by everyone"
    ON listing_comparables FOR SELECT
    USING (true);

CREATE POLICY "Comparables can be inserted by authenticated users"
    ON listing_comparables FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Comparables can be updated by authenticated users"
    ON listing_comparables FOR UPDATE
    USING (true);


-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE listing_market_stats IS 
    'Market statistics and price estimates from Casafari for comparable property analysis';

COMMENT ON TABLE listing_comparables IS 
    'Individual comparable properties from Casafari with rule verification and Uniclass assessment results';

COMMENT ON COLUMN listing_comparables.price_bucket IS 
    'Price tier classification: fast_sell (below market), fair_market (market value), out_of_market (above market)';

COMMENT ON COLUMN listing_comparables.rule_verifications IS 
    'Results from verify_rules.py - Spanish building code compliance checks';

COMMENT ON COLUMN listing_comparables.uniclass_assessments IS 
    'Results from assess_uniclass.py - Structured Uniclass element codes and conditions';

