CREATE TABLE public.ttd (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ttd_id UUID NOT NULL,
  branch_name text NOT NULL,
  session_id UUID NOT NULL,
  llm_id UUID NOT NULL,
  prompt jsonb NULL,
  completion jsonb NULL,
  model text NULL,
  prompt_tokens numeric NULL,
  completion_tokens numeric NULL,
  params text NULL,
  returns text NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now()
) tablespace pg_default;

ALTER TABLE
  public.ttd enable ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD ttd through org membership" ON public.ttd FOR ALL 
TO authenticated
USING (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = ttd.session_id
  )
) WITH CHECK (
  (SELECT auth.uid()) IN (
    SELECT user_id
    FROM user_orgs
    JOIN projects ON user_orgs.org_id = projects.org_id
    JOIN sessions ON projects.id = sessions.project_id OR projects.id = sessions.project_id_secondary
    WHERE sessions.id = ttd.session_id
  )
);

CREATE POLICY "MFA for ttd"
  ON public.ttd
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );