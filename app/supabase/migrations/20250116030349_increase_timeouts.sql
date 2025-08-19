-- Increase timeout to 10 minutes
ALTER ROLE "authenticated" SET "statement_timeout" TO '60s';
ALTER ROLE "authenticator" SET "statement_timeout" TO '60s';
