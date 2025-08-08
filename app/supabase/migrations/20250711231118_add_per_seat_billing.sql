-- Migration: Add per-seat billing support
-- Date: January 31, 2025
-- Purpose: Enable per-seat billing where organizations pay based on licensed members

BEGIN;

-- Add paid status to user_orgs table (tracks which members count against paid seats)
ALTER TABLE public.user_orgs
ADD COLUMN is_paid BOOLEAN DEFAULT FALSE;

-- Create audit log table for billing changes
CREATE TABLE public.billing_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES public.orgs(id),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    action VARCHAR(50) NOT NULL, -- 'seats_updated', 'member_licensed', 'member_unlicensed'
    details JSONB NOT NULL, -- JSON with before/after values
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create webhook events table for idempotency
CREATE TABLE public.webhook_events (
    event_id VARCHAR PRIMARY KEY,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for performance
CREATE INDEX idx_user_orgs_is_paid ON public.user_orgs(org_id, is_paid);
CREATE INDEX idx_billing_audit_logs_org_id ON public.billing_audit_logs(org_id);
CREATE INDEX idx_webhook_events_processed_at ON public.webhook_events(processed_at);

-- Enable RLS on new tables
ALTER TABLE public.billing_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

-- RLS policies for billing_audit_logs
CREATE POLICY "Org admins can view billing audit logs" ON public.billing_audit_logs
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.user_orgs
        WHERE user_orgs.org_id = billing_audit_logs.org_id
        AND user_orgs.user_id = auth.uid()
        AND user_orgs.role IN ('admin', 'owner')
    )
);

-- RLS policies for webhook_events (internal use only, no user access)
-- No SELECT/INSERT/UPDATE/DELETE policies means only backend can access

-- Mark only the owner as paid for existing pro orgs
UPDATE public.user_orgs uo
SET is_paid = TRUE
FROM public.orgs o
WHERE uo.org_id = o.id 
AND o.prem_status = 'pro'
AND uo.role = 'owner';

-- Edge case: If no owner exists, mark the first admin as paid
UPDATE public.user_orgs uo
SET is_paid = TRUE
FROM (
    SELECT DISTINCT ON (org_id) user_id, org_id 
    FROM public.user_orgs 
    WHERE role = 'admin' 
    AND org_id IN (
        SELECT o.id FROM public.orgs o 
        WHERE o.prem_status = 'pro' 
        AND NOT EXISTS (
            SELECT 1 FROM public.user_orgs uo2 
            WHERE uo2.org_id = o.id AND uo2.role = 'owner'
        )
    )
    ORDER BY org_id, user_id -- Deterministic ordering
) first_admin
WHERE uo.user_id = first_admin.user_id AND uo.org_id = first_admin.org_id;

-- Add subscription_id column to orgs table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'orgs' 
                  AND column_name = 'subscription_id') THEN
        ALTER TABLE public.orgs ADD COLUMN subscription_id TEXT NULL;
    END IF;
END $$;

COMMIT;

-- Post-migration verification queries (run these manually to verify success):
-- 
-- 1. Verify is_paid column added:
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_schema = 'public' AND table_name = 'user_orgs' AND column_name = 'is_paid';
-- 
-- 2. Verify new tables created:
-- SELECT tablename FROM pg_tables 
-- WHERE schemaname = 'public' AND tablename IN ('billing_audit_logs', 'webhook_events');
-- 
-- 3. Verify indexes created:
-- SELECT indexname FROM pg_indexes 
-- WHERE schemaname = 'public' AND tablename IN ('user_orgs', 'billing_audit_logs', 'webhook_events');
-- 
-- 4. Verify pro org owners marked as paid:
-- SELECT o.name, COUNT(uo.user_id) as paid_members
-- FROM public.orgs o
-- JOIN public.user_orgs uo ON o.id = uo.org_id
-- WHERE o.prem_status = 'pro' AND uo.is_paid = TRUE
-- GROUP BY o.id, o.name; 