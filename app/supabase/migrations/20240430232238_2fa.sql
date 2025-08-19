CREATE OR REPLACE FUNCTION user_aal()
RETURNS text[] AS $$
DECLARE
    user_factors int;
BEGIN
    SELECT count(*)
    INTO user_factors
    FROM auth.mfa_factors
    WHERE auth.uid() = user_id AND status = 'verified';

    IF user_factors > 0 THEN
        RETURN ARRAY['aal2'];
    ELSE
        RETURN ARRAY['aal1', 'aal2'];
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE POLICY "MFA for actions"
  ON public.actions
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for agents"
  ON public.agents
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for errors"
  ON public.errors
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for llms"
  ON public.llms
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for orgs"
  ON public.orgs
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for projects"
  ON public.projects
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for sessions"
  ON public.sessions
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for stats"
  ON public.stats
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for threads"
  ON public.threads
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for tools"
  ON public.tools
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for user_orgs"
  ON public.user_orgs
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );

CREATE POLICY "MFA for users"
  ON users
  AS restrictive
  TO authenticated
  USING (
    ARRAY[(select auth.jwt()->>'aal')] <@ user_aal()
  );