-- New user web hook
CREATE TRIGGER "new-user-email" 
AFTER INSERT
ON "auth"."users" for each row
EXECUTE FUNCTION "supabase_functions"."http_request"(
  'https://${PROJECT_ID}.supabase.co/functions/v1/new-user',
  'POST',
  '{
    "Content-Type":"application/json",
    "Authorization":"Bearer ${ANON_PUBLIC_TOKEN}"
  }',
  '{}',
  '1000'
);