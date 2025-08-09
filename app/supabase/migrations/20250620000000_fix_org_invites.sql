-- Migration: Fix org_invites table semantics and constraints
-- Date: June 20, 2025
-- Purpose: Rename columns to match their actual usage and fix the primary key constraint
-- 
-- IMPORTANT: Run the dry-run script first to verify no issues exist
-- 
-- Current state:
--   user_id = the inviter's ID (person SENDING the invite) 
--   inviter = the invitee's email (person RECEIVING the invite)
-- 
-- After migration:
--   inviter_id = the inviter's ID (person SENDING the invite)
--   invitee_email = the invitee's email (person RECEIVING the invite)

-- Start transaction to ensure atomicity
BEGIN;

-- Step 1: Drop existing constraints
-- These need to be dropped before renaming columns
ALTER TABLE public.org_invites DROP CONSTRAINT org_invites_pkey;
ALTER TABLE public.org_invites DROP CONSTRAINT org_invites_users_id_fkey;

-- Step 2: Rename columns to match actual usage
ALTER TABLE public.org_invites RENAME COLUMN user_id TO inviter_id;
ALTER TABLE public.org_invites RENAME COLUMN inviter TO invitee_email;

-- Step 3: Add new primary key on (org_id, invitee_email)
-- This allows one inviter to invite multiple people to the same org
-- But prevents duplicate invites to the same email for the same org
ALTER TABLE public.org_invites ADD CONSTRAINT org_invites_pkey PRIMARY KEY (org_id, invitee_email);

-- Step 4: Add performance indexes
CREATE INDEX idx_org_invites_inviter_id ON public.org_invites(inviter_id);
CREATE INDEX idx_org_invites_invitee_email ON public.org_invites(invitee_email);

-- Step 5: Re-add foreign key constraint with clear name
ALTER TABLE public.org_invites ADD CONSTRAINT org_invites_inviter_id_fkey 
  FOREIGN KEY (inviter_id) REFERENCES auth.users(id) ON UPDATE CASCADE ON DELETE CASCADE;

-- Step 6: Update RLS policies to use new column names
DROP POLICY IF EXISTS "Users can see their invitations" ON public.org_invites;
CREATE POLICY "Users can see invitations sent to them" ON public.org_invites FOR SELECT
TO authenticated
USING (
  invitee_email IN (
    SELECT email FROM auth.users WHERE id = auth.uid()
    UNION
    SELECT email FROM public.users WHERE id = auth.uid()
  )
);

-- Additional policy for org members to see their org's invites
CREATE POLICY "Org members can see org invites" ON public.org_invites FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.user_orgs 
    WHERE user_orgs.org_id = org_invites.org_id 
    AND user_orgs.user_id = auth.uid()
    AND user_orgs.role IN ('admin', 'owner')
  )
);

DROP POLICY IF EXISTS "Users can invite to their orgs" ON public.org_invites;
CREATE POLICY "Users can send invites for their orgs" ON public.org_invites FOR INSERT
TO authenticated
WITH CHECK (
  inviter_id = auth.uid() 
  AND EXISTS (
    SELECT 1 FROM public.user_orgs 
    WHERE org_id = org_invites.org_id 
    AND user_id = auth.uid()
  )
);

-- Drop existing DELETE policy if it exists and create new one
DROP POLICY IF EXISTS "Users can delete their invitations" ON public.org_invites;
CREATE POLICY "Org admins can delete org invites" ON public.org_invites FOR DELETE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.user_orgs 
    WHERE user_orgs.org_id = org_invites.org_id 
    AND user_orgs.user_id = auth.uid()
    AND user_orgs.role IN ('admin', 'owner')
  )
);

-- Step 7: Drop the database functions since backend handles these operations
DROP FUNCTION IF EXISTS create_org_invite;
DROP FUNCTION IF EXISTS accept_org_invite;

-- Step 8: Add a created_at column for better tracking (optional but useful)
ALTER TABLE public.org_invites ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Note: Any remaining functions that reference org_invites will need manual review
-- The create_org_invite and accept_org_invite functions have been dropped as they are
-- now handled by the backend application code

-- Commit the transaction
COMMIT;

-- Post-migration verification queries (run these manually to verify success):
-- 
-- 1. Verify column renames:
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_schema = 'public' AND table_name = 'org_invites';
-- 
-- 2. Verify new primary key:
-- SELECT conname, pg_get_constraintdef(oid) 
-- FROM pg_constraint 
-- WHERE conrelid = 'public.org_invites'::regclass AND contype = 'p';
-- 
-- 3. Verify indexes:
-- SELECT indexname FROM pg_indexes 
-- WHERE schemaname = 'public' AND tablename = 'org_invites';
-- 
-- 4. Verify RLS policies:
-- SELECT policyname FROM pg_policies 
-- WHERE schemaname = 'public' AND tablename = 'org_invites'; 