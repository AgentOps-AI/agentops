-- Create functions for checking if a user belongs to an org / is admin
CREATE OR REPLACE FUNCTION user_projects()
RETURNS SETOF uuid AS $$
BEGIN
  RETURN QUERY
  SELECT id 
  FROM public.projects
  WHERE projects.org_id in (
    SELECT org_id 
    FROM user_orgs
    WHERE user_id = (SELECT auth.uid())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


DROP POLICY IF EXISTS "Users can view sessions through org membership" ON public.sessions;

CREATE POLICY "Users can view sessions through org membership" ON public.sessions
FOR SELECT
USING (
  project_id in (select user_projects()) OR
  project_id_secondary in (select user_projects())
);

DROP POLICY IF EXISTS "Users can delete sessions through org membership" ON public.sessions;

CREATE POLICY "Users can delete sessions through org membership" ON public.sessions 
FOR DELETE
USING (
  project_id in (select user_projects()) OR
  project_id_secondary in (select user_projects())
);

DROP POLICY IF EXISTS "Users can view stats through org membership" ON public.stats;

CREATE POLICY "Users can view stats through org membership" ON public.stats FOR
SELECT
USING (
    EXISTS (
        SELECT 1
        FROM public.sessions
        WHERE sessions.id = stats.session_id
    )
  );
