ALTER TABLE public.sessions
ALTER COLUMN end_state SET DEFAULT 'Indeterminate'::public.end_state;

UPDATE public.sessions
SET end_state = 'Indeterminate'::public.end_state
WHERE end_state IS NULL;