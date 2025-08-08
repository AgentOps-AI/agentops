-- Create deployments table in deploy schema
CREATE TABLE public.deployments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT timezone('utc'::text, now()),
  shutdown_time TIMESTAMP WITH TIME ZONE NULL,
  image_id TEXT NULL, -- docker id
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  build_log TEXT NULL,
  CONSTRAINT deployments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX ON public.deployments(project_id);

-- Add userCallbackUrl column to public.projects
ALTER TABLE public.projects
ADD COLUMN user_callback_url TEXT NULL;
