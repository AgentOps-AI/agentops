CREATE OR REPLACE FUNCTION user_aal()
RETURNS text[] AS $$
DECLARE
    user_factors int;
BEGIN
    SELECT count(*)
    INTO user_factors
    FROM auth.mfa_factors
    WHERE (SELECT auth.uid()) = user_id AND status = 'verified';

    IF user_factors > 0 THEN
        RETURN ARRAY['aal2'];
    ELSE
        RETURN ARRAY['aal1', 'aal2'];
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

ALTER POLICY "MFA for actions"
  ON public.actions
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for agents"
  ON public.agents
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for errors"
  ON public.errors
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for llms"
  ON public.llms
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for orgs"
  ON public.orgs
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for projects"
  ON public.projects
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for sessions"
  ON public.sessions
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for stats"
  ON public.stats
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for threads"
  ON public.threads
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for tools"
  ON public.tools
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for user_orgs"
  ON public.user_orgs
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );

ALTER POLICY "MFA for users"
  ON users
  USING (
    ARRAY[((select auth.jwt())->>'aal')] <@ user_aal()
  );


ALTER POLICY "Users can view their own row in users" ON public.users 
TO authenticated
USING (
  id = (SELECT auth.uid())
);

ALTER POLICY "Users can edit their own row in users" ON public.users 
TO authenticated
USING (
  id = (SELECT auth.uid())
) WITH CHECK(
  id = (SELECT auth.uid())
);

ALTER POLICY "Users can view their user_orgs" ON public.user_orgs
TO authenticated
USING (
  user_id = (SELECT auth.uid())
) WITH CHECK(
  user_id = (SELECT auth.uid())
);

ALTER POLICY "Users can perform CRUD on orgs through org membership" ON public.orgs
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    WHERE user_orgs.org_id = orgs.id
  )
) WITH CHECK (
   (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    WHERE user_orgs.org_id = orgs.id
  )
);

ALTER POLICY "Users can perform CRUD on projects through org membership" ON public.projects
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id 
    FROM public.user_orgs
    WHERE public.user_orgs.org_id = public.projects.org_id
  )
)
WITH CHECK (
  (SELECT auth.uid()) IN (
    SELECT user_id 
    FROM public.user_orgs
    WHERE public.user_orgs.org_id = public.projects.org_id
  )
);

ALTER POLICY "Users can view sessions through org membership" ON public.sessions
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    WHERE projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
  )
);

ALTER POLICY "Users can delete sessions through org membership" ON public.sessions 
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    WHERE projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
  )
);

ALTER POLICY "Users can view stats through org membership" ON public.stats 
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = stats.session_id
  )
);

ALTER POLICY "Users can view agents through org membership" ON public.agents 
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = agents.session_id
  )
);

ALTER POLICY "Users can view threads through org membership" ON public.threads 
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = threads.session_id
  )
);

ALTER POLICY "Users can view llms through org membership" ON public.llms
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = llms.session_id
  )
);

ALTER POLICY "Users can view actions through org membership" ON public.actions
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = actions.session_id
  )
);

ALTER POLICY "Users can view tools through org membership" ON public.tools
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = tools.session_id
  )
);

ALTER POLICY "Users can view errors through org membership" ON public.errors
TO authenticated 
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = errors.session_id
  )
);

ALTER POLICY "Give users access to own images related to their sessions" 
ON storage.objects 
 TO authenticated 
USING (
  bucket_id = 'screenshots' 
  AND (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = (storage.foldername(name))[1]::uuid
  )
);

ALTER POLICY "Give users access to own blobs related to their sessions" 
ON storage.objects 
 TO authenticated 
USING (
  bucket_id = 'blobs' 
  AND (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = (storage.foldername(name))[1]::uuid
  )
);

CREATE INDEX ON public.sessions(init_timestamp);