-- Migration: 021_add_casafari_raw_response_columns.sql
-- Purpose: Store full Casafari responses without re-fetching
-- Created: 2026-01-22

ALTER TABLE IF EXISTS public.listing_market_stats
    ADD COLUMN IF NOT EXISTS raw_casafari_response JSONB,
    ADD COLUMN IF NOT EXISTS raw_filtered_comparables JSONB;
