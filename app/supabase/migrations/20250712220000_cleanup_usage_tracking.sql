-- Migration: Clean up unnecessary usage tracking
-- Date: July 12, 2025
-- Purpose: Remove org_usage_tracking table since we'll query ClickHouse directly

BEGIN;

-- Drop RLS policies first
DROP POLICY IF EXISTS "Org members can view usage" ON public.org_usage_tracking;

-- Drop indexes
DROP INDEX IF EXISTS idx_usage_tracking_rollup;

-- Drop the table
DROP TABLE IF EXISTS public.org_usage_tracking;

-- Keep billing_periods table for historical snapshots and invoicing
-- Keep all per-seat billing tables and columns

COMMIT;

-- Post-migration verification:
-- 
-- 1. Verify org_usage_tracking table removed:
-- SELECT EXISTS (
--     SELECT 1 FROM information_schema.tables 
--     WHERE table_schema = 'public' AND table_name = 'org_usage_tracking'
-- ); -- Should return false
-- 
-- 2. Verify billing_periods still exists:
-- SELECT EXISTS (
--     SELECT 1 FROM information_schema.tables 
--     WHERE table_schema = 'public' AND table_name = 'billing_periods'
-- ); -- Should return true 