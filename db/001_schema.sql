-- ============================================================================
-- LEAN MVP DATABASE SCHEMA (COMPLETE)
-- Project: Leo_casa (imxmapzfzeloiiatgoqd)
-- Version: 1.0 (Fresh Start)
-- Created: 2024-12-24
-- 
-- This is THE schema. Apply once to fresh Supabase project.
-- Includes: Core + Pipeline + Billing + "Close and Come Back" architecture
-- ============================================================================

-- ============================================================================
-- SECTION 1: CORE TABLES
-- ============================================================================

-- User Profiles (extends Supabase Auth)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Subscriptions (Pre-wired for Stripe/RevenueCat)
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Plan & Status
    plan TEXT NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'buyer_intelligence', 'pro', 'enterprise')),
    status TEXT NOT NULL DEFAULT 'inactive'
        CHECK (status IN ('active', 'inactive', 'cancelled', 'past_due', 'trialing')),
    
    -- Billing Provider (for future Stripe/RevenueCat integration)
    provider TEXT,                      -- 'stripe' | 'revenuecat' | 'manual'
    provider_subscription_id TEXT,      -- Stripe: sub_xxx, RevenueCat: entitlement ID
    provider_customer_id TEXT,          -- Stripe: cus_xxx
    provider_price_id TEXT,             -- Stripe: price_xxx
    
    -- Period Tracking
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    
    -- Usage (for metered/credit-based plans)
    analyses_remaining INT DEFAULT 0,
    analyses_this_period INT DEFAULT 0,
    max_analyses_per_period INT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Listings (core property data)
CREATE TABLE IF NOT EXISTS listings (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Source
    source_url TEXT NOT NULL,
    source_domain TEXT,
    
    -- Basic Info
    title TEXT,
    price_eur NUMERIC,
    currency TEXT DEFAULT 'EUR',
    
    -- Location
    address TEXT,
    city TEXT,
    region TEXT,
    country TEXT DEFAULT 'ES',
    lat NUMERIC,
    lng NUMERIC,
    
    -- Property Details
    property_type TEXT,
    bedrooms INTEGER,
    bathrooms NUMERIC,
    sqm INTEGER,
    floor_level TEXT,
    has_elevator BOOLEAN,
    
    -- Raw Data
    description TEXT,
    features JSONB DEFAULT '[]',
    scraped_data JSONB DEFAULT '{}',
    
    -- Pipeline Status (simple status for listing card display)
    pipeline_status TEXT DEFAULT 'scraped'
        CHECK (pipeline_status IN ('scraped', 'analyzing', 'complete', 'failed')),
    pipeline_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Listing Photos
CREATE TABLE IF NOT EXISTS listing_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    storage_path TEXT,
    display_order INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    room_type TEXT,
    cluster_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SECTION 2: PIPELINE TRACKING ("Close and Come Back" Architecture)
-- ============================================================================

-- Pipeline Runs (one per analysis request)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error Tracking
    error_message TEXT,
    error_step TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline Steps (individual steps with status)
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    
    -- Step Identification
    step_key TEXT NOT NULL,           -- 'text_analysis', 'photo_analysis', etc.
    step_order INT NOT NULL,
    step_title TEXT NOT NULL,         -- Human-readable: "Analyzing Property Text"
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INT,
    
    -- Output (step result stored here)
    output JSONB,
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(run_id, step_key)
);

-- Pipeline Events (event log for SSE streaming - THE KEY TO RECONNECTION!)
CREATE TABLE IF NOT EXISTS pipeline_events (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    
    -- Event Data
    event_type TEXT NOT NULL
        CHECK (event_type IN ('thought', 'step_start', 'step_complete', 'step_failed', 'output', 'log', 'error', 'done')),
    event_data JSONB NOT NULL,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SECTION 3: TEXT ANALYSIS [T1-T4]
-- ============================================================================

CREATE TABLE IF NOT EXISTS text_analysis (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,              -- 'facts', 'categories', 'snippets', 'unknowns'
    result JSONB NOT NULL,
    model_used TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, phase)
);

-- ============================================================================
-- SECTION 4: PHOTO ANALYSIS [P1-P3]
-- ============================================================================

CREATE TABLE IF NOT EXISTS photo_clusters (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    cluster_id TEXT NOT NULL,
    room_type TEXT NOT NULL,
    room_name TEXT,
    photo_urls JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS whole_property_analysis (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    condition_score INTEGER CHECK (condition_score BETWEEN 1 AND 100),
    condition_label TEXT,
    
    structure JSONB,
    finishes JSONB,
    lighting JSONB,
    
    issues TEXT[],
    strengths TEXT[],
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS room_analyses (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    cluster_id TEXT NOT NULL,
    
    condition_score INTEGER CHECK (condition_score BETWEEN 1 AND 100),
    elements JSONB,
    renovation_needs TEXT[],
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, cluster_id)
);

-- ============================================================================
-- SECTION 4.5: SIZING [M1]
-- ============================================================================

CREATE TABLE IF NOT EXISTS smart_m2 (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    rooms JSONB NOT NULL,           -- [{ cluster_name, estimated_m2, estimated_height_m, confidence, reasoning }]
    circulation_and_walls_m2 NUMERIC,
    total_check NUMERIC,            -- Must equal listings.sqm
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SECTION 5: CONTEXT [C1-C2]
-- ============================================================================

CREATE TABLE IF NOT EXISTS context_research (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    costs JSONB,
    timings JSONB,
    permits JSONB,
    laws_regulations JSONB,
    incentives JSONB,
    
    all_sources JSONB,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cost_baseline (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    location_multiplier NUMERIC,
    sqm_rate_cosmetic JSONB,        -- { min: number, max: number }
    sqm_rate_systems JSONB,
    sqm_rate_structure JSONB,
    per_room_breakdown JSONB,       -- [{ room_name, m2, needs[], cost_estimate }]
    sources JSONB,                  -- [{ url, domain, extracted_price, credibility }]
    
    search_query_count INTEGER,     -- Number of Google searches performed
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SECTION 6: ARCHITECT [A1-A3]
-- ============================================================================

CREATE TABLE IF NOT EXISTS room_groups (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    groups JSONB NOT NULL,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tier Assessment stores BOTH slider values (§1 Home Condition + §2 Reno Difficulty)
CREATE TABLE IF NOT EXISTS tier_assessment (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    
    -- §1 HOME CONDITION SLIDER (0-100)
    home_condition_score INTEGER CHECK (home_condition_score BETWEEN 0 AND 100),
    home_condition_label TEXT,
    home_condition_summary TEXT,
    home_condition_reasons TEXT[],
    
    -- §2 RENOVATION DIFFICULTY SLIDER (0-100)
    reno_difficulty_score INTEGER CHECK (reno_difficulty_score BETWEEN 0 AND 100),
    reno_difficulty_label TEXT,
    reno_difficulty_summary TEXT,
    reno_difficulty_factors TEXT[],
    
    -- Tier Enablement (§3 Feasible Paths)
    minimum_required TEXT CHECK (minimum_required IN ('cosmetic', 'systems', 'structure')),
    maximum_possible TEXT CHECK (maximum_possible IN ('cosmetic', 'systems', 'structure')),
    tier_cosmetic_enabled BOOLEAN DEFAULT TRUE,
    tier_systems_enabled BOOLEAN DEFAULT TRUE,
    tier_structure_enabled BOOLEAN DEFAULT TRUE,
    disabled_tier_reasons JSONB,      -- { cosmetic: "reason", systems: "reason", structure: "reason" }
    
    -- §4 Confirm in Person
    confirm_list TEXT[],
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tier_designs (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    style_direction JSONB,
    budget_range JSONB,               -- { min_eur: number, max_eur: number, display: string }
    design_rationale TEXT,
    room_group_specs JSONB,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

-- ============================================================================
-- SECTION 7: SCOPE [R1-R4]
-- ============================================================================

CREATE TABLE IF NOT EXISTS renovation_scope (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    scope_items JSONB NOT NULL,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS renovation_research (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    research_results JSONB,
    sources JSONB,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS scope_pricing (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    total_min INTEGER,
    total_max INTEGER,
    currency TEXT DEFAULT 'EUR',
    line_items JSONB,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS scope_timeline (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    total_weeks_min INTEGER,
    total_weeks_max INTEGER,
    phases JSONB,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS scope_permits (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    permits_required JSONB,
    total_permit_time TEXT,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS final_scope (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    price_range JSONB,                -- { min_eur, max_eur, display }
    timeline_weeks JSONB,             -- { min, max, display }
    scope_summary TEXT,
    work_items JSONB,
    timeline_phases JSONB,
    permits JSONB,
    sources JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

-- ============================================================================
-- SECTION 8: VISUALS [V1-V4]
-- ============================================================================

CREATE TABLE IF NOT EXISTS defurnished_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    original_url TEXT NOT NULL,
    defurnished_url TEXT,
    room_type TEXT,
    cluster_id TEXT,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, original_url)
);

CREATE TABLE IF NOT EXISTS visual_selections (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    selected_photo_url TEXT NOT NULL,
    room_type TEXT,
    cluster_id TEXT,
    
    elements_to_change JSONB,
    selection_reasoning TEXT,
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS render_prompts (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    prompt TEXT NOT NULL,
    style_keywords TEXT[],
    
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

CREATE TABLE IF NOT EXISTS after_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    
    before_url TEXT NOT NULL,
    after_url TEXT NOT NULL,
    room_type TEXT,
    cluster_id TEXT,
    
    model_used TEXT DEFAULT 'gemini-3-image-preview',
    generation_params JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(listing_id, tier)
);

-- ============================================================================
-- SECTION 9: INDEXES (Performance)
-- ============================================================================

-- Core
CREATE INDEX IF NOT EXISTS idx_listings_user ON listings(user_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(pipeline_status);
CREATE INDEX IF NOT EXISTS idx_listings_source_url ON listings(source_url);
CREATE INDEX IF NOT EXISTS idx_listing_photos_listing ON listing_photos(listing_id);

-- Subscriptions
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_provider ON user_subscriptions(provider, provider_subscription_id);

-- Pipeline ("Close and Come Back")
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_listing ON pipeline_runs(listing_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_run ON pipeline_steps(run_id, step_order);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_run_id ON pipeline_events(run_id, id);  -- Critical for SSE reconnection
CREATE INDEX IF NOT EXISTS idx_pipeline_events_created ON pipeline_events(created_at);  -- For cleanup

-- Analysis
CREATE INDEX IF NOT EXISTS idx_text_analysis_listing ON text_analysis(listing_id);
CREATE INDEX IF NOT EXISTS idx_photo_clusters_listing ON photo_clusters(listing_id);
CREATE INDEX IF NOT EXISTS idx_tier_assessment_listing ON tier_assessment(listing_id);
CREATE INDEX IF NOT EXISTS idx_final_scope_listing ON final_scope(listing_id);
CREATE INDEX IF NOT EXISTS idx_after_photos_listing ON after_photos(listing_id);

-- ============================================================================
-- SECTION 10: HELPER FUNCTIONS
-- ============================================================================

-- Check if user has Buyer Intelligence access
CREATE OR REPLACE FUNCTION has_buyer_intelligence(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_subscriptions
        WHERE user_id = p_user_id
        AND status IN ('active', 'trialing')
        AND plan IN ('buyer_intelligence', 'pro', 'enterprise')
        AND (current_period_end IS NULL OR current_period_end > NOW())
    );
END;
$$;

-- Get complete Buyer Intelligence UI data for a listing
CREATE OR REPLACE FUNCTION get_buyer_intelligence(p_listing_id BIGINT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        -- §1 Home Condition (Slider)
        'home_condition', (
            SELECT jsonb_build_object(
                'score', ta.home_condition_score,
                'label', ta.home_condition_label,
                'summary', ta.home_condition_summary,
                'reasons', ta.home_condition_reasons
            )
            FROM tier_assessment ta
            WHERE ta.listing_id = p_listing_id
        ),
        
        -- §2 Renovation Difficulty (Slider)
        'reno_difficulty', (
            SELECT jsonb_build_object(
                'score', ta.reno_difficulty_score,
                'label', ta.reno_difficulty_label,
                'summary', ta.reno_difficulty_summary,
                'factors', ta.reno_difficulty_factors
            )
            FROM tier_assessment ta
            WHERE ta.listing_id = p_listing_id
        ),
        
        -- §2 References (expandable)
        'references', (
            SELECT jsonb_build_object(
                'permits', cr.permits,
                'incentives', cr.incentives,
                'timings', cr.timings,
                'sources', cr.all_sources
            )
            FROM context_research cr
            WHERE cr.listing_id = p_listing_id
        ),
        
        -- §3 Feasible Tiers
        'feasible_tiers', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'tier', fs.tier,
                    'enabled', CASE 
                        WHEN fs.tier = 'cosmetic' THEN ta.tier_cosmetic_enabled
                        WHEN fs.tier = 'systems' THEN ta.tier_systems_enabled
                        WHEN fs.tier = 'structure' THEN ta.tier_structure_enabled
                        ELSE TRUE
                    END,
                    'disabled_reason', CASE 
                        WHEN fs.tier = 'cosmetic' AND NOT ta.tier_cosmetic_enabled THEN ta.disabled_tier_reasons->>'cosmetic'
                        WHEN fs.tier = 'systems' AND NOT ta.tier_systems_enabled THEN ta.disabled_tier_reasons->>'systems'
                        WHEN fs.tier = 'structure' AND NOT ta.tier_structure_enabled THEN ta.disabled_tier_reasons->>'structure'
                        ELSE NULL
                    END,
                    'price_range', fs.price_range,
                    'timeline_weeks', fs.timeline_weeks,
                    'work_items', fs.work_items,
                    'timeline_phases', fs.timeline_phases,
                    'permits', fs.permits,
                    'before_url', ap.before_url,
                    'after_url', ap.after_url,
                    'style', td.style_direction,
                    'sources', fs.sources
                )
            )
            FROM final_scope fs
            LEFT JOIN after_photos ap ON ap.listing_id = fs.listing_id AND ap.tier = fs.tier
            LEFT JOIN tier_designs td ON td.listing_id = fs.listing_id AND td.tier = fs.tier
            LEFT JOIN tier_assessment ta ON ta.listing_id = fs.listing_id
            WHERE fs.listing_id = p_listing_id
        ),
        
        -- §4 Confirm in Person
        'confirm_in_person', (
            SELECT COALESCE(ta.confirm_list, ARRAY[]::TEXT[]) || 
                   COALESCE((
                       SELECT (result->>'questions_for_viewing')::TEXT[]
                       FROM text_analysis
                       WHERE listing_id = p_listing_id AND phase = 'unknowns'
                   ), ARRAY[]::TEXT[])
            FROM tier_assessment ta
            WHERE ta.listing_id = p_listing_id
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- Get latest pipeline run for a listing
CREATE OR REPLACE FUNCTION get_latest_pipeline_run(p_listing_id BIGINT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'run', (
            SELECT row_to_json(pr.*)
            FROM pipeline_runs pr
            WHERE pr.listing_id = p_listing_id
            ORDER BY pr.created_at DESC
            LIMIT 1
        ),
        'steps', (
            SELECT jsonb_agg(row_to_json(ps.*) ORDER BY ps.step_order)
            FROM pipeline_steps ps
            WHERE ps.run_id = (
                SELECT id FROM pipeline_runs
                WHERE listing_id = p_listing_id
                ORDER BY created_at DESC
                LIMIT 1
            )
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- ============================================================================
-- SECTION 11: ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE text_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE whole_property_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE room_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_research ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_baseline ENABLE ROW LEVEL SECURITY;
ALTER TABLE room_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_designs ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_research ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_permits ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE defurnished_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE visual_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE after_photos ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES (MVP: Allow all for testing, tighten later)
-- ============================================================================

-- User Profiles
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Service role full access to profiles" ON user_profiles FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- User Subscriptions
CREATE POLICY "Users can view own subscription" ON user_subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role manages subscriptions" ON user_subscriptions FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Listings (MVP: Open for testing)
CREATE POLICY "Allow public read on listings" ON listings FOR SELECT USING (true);
CREATE POLICY "Allow public insert on listings" ON listings FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on listings" ON listings FOR UPDATE USING (true);

-- Pipeline tables (MVP: Open for testing)
CREATE POLICY "Allow all on listing_photos" ON listing_photos FOR ALL USING (true);
CREATE POLICY "Allow all on pipeline_runs" ON pipeline_runs FOR ALL USING (true);
CREATE POLICY "Allow all on pipeline_steps" ON pipeline_steps FOR ALL USING (true);
CREATE POLICY "Allow all on pipeline_events" ON pipeline_events FOR ALL USING (true);
CREATE POLICY "Allow all on text_analysis" ON text_analysis FOR ALL USING (true);
CREATE POLICY "Allow all on photo_clusters" ON photo_clusters FOR ALL USING (true);
CREATE POLICY "Allow all on whole_property_analysis" ON whole_property_analysis FOR ALL USING (true);
CREATE POLICY "Allow all on room_analyses" ON room_analyses FOR ALL USING (true);
CREATE POLICY "Allow all on context_research" ON context_research FOR ALL USING (true);
CREATE POLICY "Allow all on cost_baseline" ON cost_baseline FOR ALL USING (true);
CREATE POLICY "Allow all on room_groups" ON room_groups FOR ALL USING (true);
CREATE POLICY "Allow all on tier_assessment" ON tier_assessment FOR ALL USING (true);
CREATE POLICY "Allow all on tier_designs" ON tier_designs FOR ALL USING (true);
CREATE POLICY "Allow all on renovation_scope" ON renovation_scope FOR ALL USING (true);
CREATE POLICY "Allow all on renovation_research" ON renovation_research FOR ALL USING (true);
CREATE POLICY "Allow all on scope_pricing" ON scope_pricing FOR ALL USING (true);
CREATE POLICY "Allow all on scope_timeline" ON scope_timeline FOR ALL USING (true);
CREATE POLICY "Allow all on scope_permits" ON scope_permits FOR ALL USING (true);
CREATE POLICY "Allow all on final_scope" ON final_scope FOR ALL USING (true);
CREATE POLICY "Allow all on defurnished_photos" ON defurnished_photos FOR ALL USING (true);
CREATE POLICY "Allow all on visual_selections" ON visual_selections FOR ALL USING (true);
CREATE POLICY "Allow all on render_prompts" ON render_prompts FOR ALL USING (true);
CREATE POLICY "Allow all on after_photos" ON after_photos FOR ALL USING (true);

-- ============================================================================
-- DONE! Fresh schema ready for Lean MVP.
-- ============================================================================
