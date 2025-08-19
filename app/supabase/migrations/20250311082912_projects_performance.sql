-- Add a composite index to optimize project queries
CREATE INDEX IF NOT EXISTS idx_user_orgs_user_id_org_id ON public.user_orgs(user_id, org_id);

-- Add an index on projects.id to optimize the IN query
CREATE INDEX IF NOT EXISTS idx_projects_id ON public.projects(id);
