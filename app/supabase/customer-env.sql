-- Make orgs "enterprise" by default
ALTER TABLE public.orgs
ADD COLUMN prem_status public.prem_status NOT NULL DEFAULT 'enterprise';