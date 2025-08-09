-- Add foreign key constraints to ttd table
ALTER TABLE public.ttd
ADD CONSTRAINT ttd_session_id_fkey
FOREIGN KEY (session_id)
REFERENCES public.sessions(id)
ON UPDATE CASCADE
ON DELETE SET NULL;

ALTER TABLE public.ttd
ADD CONSTRAINT ttd_llm_id_fkey
FOREIGN KEY (llm_id)
REFERENCES public.llms(id)
ON UPDATE CASCADE
ON DELETE SET NULL;

-- Modify session_id and llm_id columns to allow NULL values
ALTER TABLE public.ttd
ALTER COLUMN session_id DROP NOT NULL,
ALTER COLUMN llm_id DROP NOT NULL;

CREATE INDEX ON public.ttd(session_id);
