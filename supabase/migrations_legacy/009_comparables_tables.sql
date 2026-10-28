-- Migration: 009_comparables_tables.sql
-- Purpose: Store market comparables data and bracket analyses
-- Created: 2026-01-07

-- =============================================================================
-- TABLE: listing_market_stats
-- Stores Casafari market statistics and price estimates
-- =============================================================================

CREATE TABLE IF NOT EXISTS listing_market_stats (
    listing_id BIGINT PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Casafari Raw Price Estimates
    casafari_fast_sell INT,
    casafari_fair_market INT,
    casafari_premium INT,
    casafari_comparables_count INT,
    
    -- Our Filtered Price Estimates (±20% land/area)
    filtered_fast_sell INT,
    filtered_fair_market INT,
    filtered_premium INT,
    filtered_comparables_count INT,
    filter_tolerance DECIMAL(3,2) DEFAULT 0.20,
    
    -- Market Statistics
    average_price INT,
    average_price_per_sqm INT,
    average_days_on_market INT,
    sold_last_6_months INT,
    
    -- Reference
    asking_price INT,
    casafari_link TEXT,
    search_params JSONB,
    
    -- Raw response for debugging
    raw_casafari_response JSONB,
    raw_filtered_comparables JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- TABLE: listing_comparables
-- Stores individual comparable properties from Casafari
-- =============================================================================

CREATE TABLE IF NOT EXISTS listing_comparables (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Casafari Property Info
    casafari_property_id BIGINT NOT NULL,
    property_url TEXT,
    
    -- Classification
    price_bucket TEXT NOT NULL,  -- 'fast_sell', 'fair_market', 'premium'
    is_filtered BOOLEAN DEFAULT FALSE,  -- Whether it passed our ±20% filter
    similarity_score DECIMAL(4,3),
    
    -- Property Details
    sale_price INT,
    price_per_sqm INT,
    total_area INT,       -- m2_built
    living_area INT,      -- m2_useful
    plot_area INT,        -- m2_plot (CRITICAL for houses)
    bedrooms INT,
    bathrooms INT,
    
    -- Condition & Energy
    condition TEXT,
    construction_year INT,
    energy_rating TEXT,
    
    -- Location
    distance_km DECIMAL(4,2),
    address TEXT,
    zip_code TEXT,
    coordinates JSONB,
    
    -- Media
    photo_urls JSONB,
    
    -- Features
    features JSONB,
    property_type TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, casafari_property_id)
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_listing_comparables_listing ON listing_comparables(listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_comparables_bucket ON listing_comparables(listing_id, price_bucket);
CREATE INDEX IF NOT EXISTS idx_listing_comparables_filtered ON listing_comparables(listing_id, is_filtered);

-- =============================================================================
-- TABLE: listing_bracket_analyses
-- Stores full renovation analysis for each bracket
-- =============================================================================

CREATE TABLE IF NOT EXISTS listing_bracket_analyses (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    
    -- Which bracket/view
    view_type TEXT NOT NULL,  -- 'casafari' or 'filtered'
    bracket TEXT NOT NULL,    -- 'fast_sell', 'fair_market', 'premium'
    
    -- Target & Gap
    target_price INT NOT NULL,
    asking_price INT NOT NULL,
    gap INT NOT NULL,
    
    -- Pricing (from KGEstimator)
    renovation_cost INT,
    pem_subtotal INT,         -- Presupuesto Ejecución Material
    overhead_profit INT,      -- 19%
    iva INT,                  -- 21%
    line_items_count INT,
    scope_of_work JSONB,      -- Categories and items
    
    -- Math
    total_investment INT,
    potential_margin INT,
    
    -- Timeline
    estimated_weeks_min INT,
    estimated_weeks_max INT,
    timeline_breakdown JSONB,
    
    -- Visuals
    before_photo_url TEXT,
    after_photo_url TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'complete', 'failed'
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, view_type, bracket)
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_bracket_analyses_listing ON listing_bracket_analyses(listing_id);

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

ALTER TABLE listing_market_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_comparables ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_bracket_analyses ENABLE ROW LEVEL SECURITY;

-- Public read access (for now)
CREATE POLICY "Allow public read for listing_market_stats"
    ON listing_market_stats FOR SELECT USING (true);

CREATE POLICY "Allow public read for listing_comparables"
    ON listing_comparables FOR SELECT USING (true);

CREATE POLICY "Allow public read for listing_bracket_analyses"
    ON listing_bracket_analyses FOR SELECT USING (true);

-- Service role can do everything
CREATE POLICY "Allow service role full access to listing_market_stats"
    ON listing_market_stats FOR ALL USING (true);

CREATE POLICY "Allow service role full access to listing_comparables"
    ON listing_comparables FOR ALL USING (true);

CREATE POLICY "Allow service role full access to listing_bracket_analyses"
    ON listing_bracket_analyses FOR ALL USING (true);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE listing_market_stats IS 'Market statistics and price brackets from Casafari + our filtered calculations';
COMMENT ON TABLE listing_comparables IS 'Individual comparable properties from Casafari search';
COMMENT ON TABLE listing_bracket_analyses IS 'Full renovation analysis for each price bracket (delta, pricing, timeline, images)';

