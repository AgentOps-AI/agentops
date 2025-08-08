ALTER ROLE "authenticated" SET "statement_timeout" TO '15s';
ALTER ROLE "authenticator" SET "statement_timeout" TO '15s';

CREATE INDEX ON public.user_orgs(org_id);
CREATE INDEX ON public.user_orgs(user_id);