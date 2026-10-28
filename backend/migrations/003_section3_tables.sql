-- §3 Feasible Paths - Database Tables
-- =====================================
-- Run this migration to add tables for Section 3

-- Room Groups (A1)
CREATE TABLE IF NOT EXISTS room_groups (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    group_id TEXT NOT NULL,
    group_name TEXT NOT NULL,
    cluster_ids JSONB DEFAULT '[]',
    rationale TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_room_groups_listing ON room_groups(listing_id);

-- Tier Designs (A3)
CREATE TABLE IF NOT EXISTS tier_designs (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    philosophy TEXT,
    style_direction JSONB,
    budget JSONB,
    room_group_specs JSONB,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_tier_designs_listing ON tier_designs(listing_id);

-- Renovation Scope (R1 work items)
CREATE TABLE IF NOT EXISTS renovation_scope (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    work_items JSONB NOT NULL DEFAULT '[]',
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_renovation_scope_listing ON renovation_scope(listing_id);

-- Renovation Research (R2 J-Reno searches)
CREATE TABLE IF NOT EXISTS renovation_research (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    research_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_renovation_research_listing ON renovation_research(listing_id);

-- Scope Pricing (R3a)
CREATE TABLE IF NOT EXISTS scope_pricing (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    priced_items JSONB DEFAULT '[]',
    total_cost_min INTEGER,
    total_cost_max INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_scope_pricing_listing ON scope_pricing(listing_id);

-- Scope Timeline (R3b)
CREATE TABLE IF NOT EXISTS scope_timeline (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    phases JSONB DEFAULT '[]',
    item_placement JSONB DEFAULT '[]',
    total_duration_weeks INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_scope_timeline_listing ON scope_timeline(listing_id);

-- Scope Permits (R3c)
CREATE TABLE IF NOT EXISTS scope_permits (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    permits JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_scope_permits_listing ON scope_permits(listing_id);

-- Final Scope (R4 merged output)
CREATE TABLE IF NOT EXISTS final_scope (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE UNIQUE,
    tiers JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_final_scope_listing ON final_scope(listing_id);

-- Defurnished Photos (V1)
CREATE TABLE IF NOT EXISTS defurnished_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    cluster_id TEXT NOT NULL,
    original_url TEXT NOT NULL,
    defurnished_data TEXT,  -- Base64 encoded image
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_defurnished_photos_listing ON defurnished_photos(listing_id);

-- Tier Before Photos (V2)
CREATE TABLE IF NOT EXISTS tier_before_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    cluster_id TEXT NOT NULL,
    photo_url TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_tier_before_photos_listing ON tier_before_photos(listing_id);

-- Render Prompts (V3)
CREATE TABLE IF NOT EXISTS render_prompts (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    render_prompt TEXT NOT NULL,
    key_changes JSONB DEFAULT '[]',
    style_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_render_prompts_listing ON render_prompts(listing_id);

-- After Photos (V4)
CREATE TABLE IF NOT EXISTS after_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('cosmetic', 'systems', 'structure')),
    cluster_id TEXT NOT NULL,
    after_data TEXT,  -- Base64 encoded image
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(listing_id, tier)
);

CREATE INDEX IF NOT EXISTS idx_after_photos_listing ON after_photos(listing_id);

-- Add tier boundary fields to tier_assessment if not exists
DO $$
BEGIN
    -- Add minimum_required column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'tier_assessment' AND column_name = 'minimum_required') THEN
        ALTER TABLE tier_assessment ADD COLUMN minimum_required TEXT;
    END IF;
    
    -- Add maximum_possible column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'tier_assessment' AND column_name = 'maximum_possible') THEN
        ALTER TABLE tier_assessment ADD COLUMN maximum_possible TEXT;
    END IF;
END $$;

-- Enable RLS on all new tables
ALTER TABLE room_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_designs ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_research ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_permits ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE defurnished_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_before_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE after_photos ENABLE ROW LEVEL SECURITY;

-- Create permissive policies for service role access
CREATE POLICY IF NOT EXISTS "Service role full access to room_groups"
    ON room_groups FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to tier_designs"
    ON tier_designs FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to renovation_scope"
    ON renovation_scope FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to renovation_research"
    ON renovation_research FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to scope_pricing"
    ON scope_pricing FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to scope_timeline"
    ON scope_timeline FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to scope_permits"
    ON scope_permits FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to final_scope"
    ON final_scope FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to defurnished_photos"
    ON defurnished_photos FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to tier_before_photos"
    ON tier_before_photos FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to render_prompts"
    ON render_prompts FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access to after_photos"
    ON after_photos FOR ALL USING (true);

