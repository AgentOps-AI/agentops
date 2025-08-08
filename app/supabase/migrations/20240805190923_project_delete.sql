-- Drop existing foreign key constraints
ALTER TABLE public.sessions
DROP CONSTRAINT IF EXISTS sessions_project_id_fkey;

ALTER TABLE public.sessions
DROP CONSTRAINT IF EXISTS sessions_project_id_secondary_fkey;

-- Add new foreign key constraints with ON DELETE CASCADE
ALTER TABLE public.sessions
ADD CONSTRAINT sessions_project_id_fkey
FOREIGN KEY (project_id)
REFERENCES projects (id)
ON UPDATE CASCADE
ON DELETE CASCADE;

ALTER TABLE public.sessions
ADD CONSTRAINT sessions_project_id_secondary_fkey
FOREIGN KEY (project_id_secondary)
REFERENCES projects (id)
ON UPDATE CASCADE
ON DELETE CASCADE;
