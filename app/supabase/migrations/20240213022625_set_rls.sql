ALTER TABLE
  public.prices enable ROW LEVEL SECURITY;
ALTER TABLE
  public.products enable ROW LEVEL SECURITY;
ALTER TABLE
  public.subscriptions enable ROW LEVEL SECURITY;
ALTER TABLE
  public.customers enable ROW LEVEL SECURITY;
ALTER TABLE
  public.users enable ROW LEVEL SECURITY;

ALTER TABLE
  public.orgs enable ROW LEVEL SECURITY;

ALTER TABLE
  public.projects enable ROW LEVEL SECURITY;

ALTER TABLE
  public.user_orgs enable ROW LEVEL SECURITY;

ALTER TABLE
  public.sessions enable ROW LEVEL SECURITY;

ALTER TABLE
  public.agents enable ROW LEVEL SECURITY;

ALTER TABLE
  public.threads enable ROW LEVEL SECURITY;

ALTER TABLE
  public.stats enable ROW LEVEL SECURITY;

ALTER TABLE
  public.llms enable ROW LEVEL SECURITY;

ALTER TABLE
  public.actions enable ROW LEVEL SECURITY;

ALTER TABLE
  public.tools enable ROW LEVEL SECURITY;

ALTER TABLE
  public.errors enable ROW LEVEL SECURITY;

ALTER TABLE
  public.developer_errors enable ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own row in users" ON public.users FOR SELECT
USING (
  id = auth.uid ()
);

CREATE POLICY "Users can view their user_orgs" ON public.user_orgs FOR ALL
USING (
  user_id = auth.uid ()
) WITH CHECK(
  user_id = auth.uid ()
);

CREATE policy "Users can perform CRUD on orgs through org membership" ON public.orgs FOR ALL 
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    WHERE user_orgs.org_id = orgs.id
  )
) WITH CHECK (
   auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    WHERE user_orgs.org_id = orgs.id
  )
);

CREATE policy "Users can perform CRUD on projects through org membership" ON public.projects FOR ALL
USING (
  auth.uid() IN (
    SELECT user_id 
    FROM public.user_orgs
    WHERE public.user_orgs.org_id = public.projects.org_id
  )
)
WITH CHECK (
  auth.uid() IN (
    SELECT user_id 
    FROM public.user_orgs
    WHERE public.user_orgs.org_id = public.projects.org_id
  )
);

CREATE POLICY "Users can view sessions through org membership" ON public.sessions
FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    WHERE projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
  )
);

CREATE POLICY "Users can delete sessions through org membership" ON public.sessions 
FOR DELETE
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    WHERE projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
  )
);

CREATE POLICY "Users can view stats through org membership" ON public.stats FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = stats.session_id
  )
);

CREATE POLICY "Users can view agents through org membership" ON public.agents FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = agents.session_id
  )
);

CREATE POLICY "Users can view threads through org membership" ON public.threads FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = threads.session_id
  )
);

CREATE POLICY "Users can view llms through org membership" ON public.llms FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = llms.session_id
  )
);

CREATE POLICY "Users can view actions through org membership" ON public.actions FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = actions.session_id
  )
);

CREATE POLICY "Users can view tools through org membership" ON public.tools FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = tools.session_id
  )
);

CREATE POLICY "Users can view errors through org membership" ON public.errors FOR
SELECT
USING (
  auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = errors.session_id
  )
);

CREATE POLICY "Give users access to own images related to their sessions" 
ON storage.objects 
FOR SELECT TO authenticated 
USING (
  bucket_id = 'screenshots' 
  AND auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = (storage.foldername(name))[1]::uuid
  )
);

CREATE POLICY "Give users access to own blobs related to their sessions" 
ON storage.objects 
FOR SELECT TO authenticated 
USING (
  bucket_id = 'blobs' 
  AND auth.uid() IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = (storage.foldername(name))[1]::uuid
  )
);