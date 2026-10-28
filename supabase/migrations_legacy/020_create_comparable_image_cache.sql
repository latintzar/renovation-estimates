-- ============================================================================
-- Migration: Create comparable_image_cache table
-- Purpose: Store cached URLs for comparable images in Supabase Storage
-- 
-- This table tracks which comparable images have been cached to our own
-- storage, preventing rate limiting issues during PIR generation.
-- ============================================================================

-- Create table
CREATE TABLE IF NOT EXISTS comparable_image_cache (
    id BIGSERIAL PRIMARY KEY,
    comparable_id BIGINT NOT NULL UNIQUE,
    cached_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    image_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast lookup by comparable_id
CREATE INDEX IF NOT EXISTS idx_comparable_image_cache_comp_id 
    ON comparable_image_cache(comparable_id);

-- Add comment
COMMENT ON TABLE comparable_image_cache IS 
    'Cache of comparable images stored in Supabase Storage. Used to avoid rate limiting during PIR generation.';

-- Enable RLS
ALTER TABLE comparable_image_cache ENABLE ROW LEVEL SECURITY;

-- Create policy for service role access
CREATE POLICY "Service role can manage image cache"
    ON comparable_image_cache
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Also need to create the storage bucket
-- Run this manually in Supabase dashboard or via CLI:
-- supabase storage buckets create comparable-images --public
