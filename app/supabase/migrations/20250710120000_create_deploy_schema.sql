-- Create deploy schema
CREATE SCHEMA deploy;

-- Create deploy.projects table
CREATE TABLE deploy.projects (
  id UUID PRIMARY KEY,
  github_oath_access_token TEXT NULL,
  user_callback_url TEXT NULL,
  watch_path TEXT NULL,
  entrypoint TEXT NULL,
  git_branch TEXT NULL,
  git_url TEXT NULL,
  CONSTRAINT projects_id_fkey FOREIGN KEY (id) REFERENCES public.projects (id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Move public.deployments to deploy.deployments
ALTER TABLE public.deployments SET SCHEMA deploy;