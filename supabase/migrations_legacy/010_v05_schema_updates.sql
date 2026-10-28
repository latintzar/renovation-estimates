-- =============================================================================
-- V0.5 Database Schema Updates
-- =============================================================================
-- 
-- Updates for Schema Continuity Architecture:
-- 1. Expand pir_type constraint to allow bracket PIRs
-- 2. Add model_version column to track V0.5 vs V0.4.8
-- 3. Add v05_schema_continuity flag to unified_estimates
--
-- Run: npx supabase db push
-- =============================================================================

-- =============================================================================
-- 1. UPDATE PIR TYPE CONSTRAINT
-- =============================================================================
-- V0.5 stores bracket PIRs with types: bracket_fast_sell, bracket_fair_market, bracket_out_of_market

-- Drop the old constraint
ALTER TABLE property_intelligence_reports_v048 
DROP CONSTRAINT IF EXISTS property_intelligence_reports_v048_pir_type_check;

-- Add new constraint allowing bracket types AND strategic reasoning
ALTER TABLE property_intelligence_reports_v048 
ADD CONSTRAINT property_intelligence_reports_v048_pir_type_check 
CHECK (pir_type IN (
    'target', 
    'comparable',
    'bracket_fast_sell',
    'bracket_fair_market', 
    'bracket_out_of_market',
    'strategic_reasoning_fast_sell',
    'strategic_reasoning_fair_market',
    'strategic_reasoning_out_of_market'
));

-- =============================================================================
-- 2. ADD MODEL VERSION COLUMN TO PIR TABLE
-- =============================================================================

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'property_intelligence_reports_v048' 
                   AND column_name = 'model_version') THEN
        ALTER TABLE property_intelligence_reports_v048 
        ADD COLUMN model_version TEXT DEFAULT 'V0.4.8';
    END IF;
END $$;

-- =============================================================================
-- 3. ADD V0.5 FLAGS TO UNIFIED ESTIMATES
-- =============================================================================

DO $$ 
BEGIN
    -- Flag for schema continuity architecture
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'unified_estimates_v048' 
                   AND column_name = 'v05_schema_continuity') THEN
        ALTER TABLE unified_estimates_v048 
        ADD COLUMN v05_schema_continuity BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Item counts for validation
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'unified_estimates_v048' 
                   AND column_name = 'item_counts') THEN
        ALTER TABLE unified_estimates_v048 
        ADD COLUMN item_counts JSONB;
    END IF;
END $$;

-- =============================================================================
-- 4. UPDATE MODEL VERSION DEFAULT
-- =============================================================================

-- Update default model version to V0.5 for new records
ALTER TABLE package_generation_progress 
ALTER COLUMN model_version SET DEFAULT 'V0.5';

ALTER TABLE unified_estimates_v048 
ALTER COLUMN model_version SET DEFAULT 'V0.5';

-- =============================================================================
-- 5. ADD COMMENTS
-- =============================================================================

COMMENT ON COLUMN property_intelligence_reports_v048.pir_type IS 
'PIR type: target, comparable, bracket_fast_sell, bracket_fair_market, bracket_out_of_market';

COMMENT ON COLUMN unified_estimates_v048.v05_schema_continuity IS 
'V0.5 schema continuity: all phases use unified item schema, items cannot be lost';

-- =============================================================================
-- DONE
-- =============================================================================

SELECT 'V0.5 migration complete' AS status;
