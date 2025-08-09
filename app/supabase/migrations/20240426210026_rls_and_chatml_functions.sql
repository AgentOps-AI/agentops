-- Allow Users to update 
CREATE POLICY "Users can edit their own row in users" ON public.users FOR UPDATE
TO authenticated
USING (
  id = auth.uid ()
) WITH CHECK(
  id = auth.uid ()
);

-- Move JSONB Constraints to API server
ALTER TABLE public.llms
DROP CONSTRAINT check_prompt;
DROP FUNCTION IF EXISTS validate_prompt_schema;

ALTER TABLE public.llms
DROP CONSTRAINT check_completion;
DROP FUNCTION IF EXISTS validate_completion_schema;