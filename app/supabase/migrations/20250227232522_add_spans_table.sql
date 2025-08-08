-- Add spans table for OpenTelemetry spans
CREATE TABLE public.spans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  agent_id UUID NULL,
  trace_id TEXT NOT NULL,
  span_id TEXT NOT NULL,
  parent_span_id TEXT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  start_time TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time TIMESTAMP WITH TIME ZONE NOT NULL,
  attributes BYTEA NULL,
  span_type TEXT NOT NULL,
  CONSTRAINT spans_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX ON public.spans(session_id);
CREATE INDEX ON public.spans(trace_id);
CREATE INDEX ON public.spans(span_id);
CREATE INDEX ON public.spans(span_type);
