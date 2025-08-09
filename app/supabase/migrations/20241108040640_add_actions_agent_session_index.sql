CREATE INDEX IF NOT EXISTS actions_agent_id_idx ON public.actions (agent_id);
CREATE INDEX IF NOT EXISTS llms_agent_id_idx ON public.llms(agent_id);
CREATE INDEX IF NOT EXISTS threads_agent_id_idx ON public.threads (agent_id);
CREATE INDEX IF NOT EXISTS tools_agent_id_idx ON public.tools (agent_id);

CREATE INDEX IF NOT EXISTS llms_thread_id_idx ON public.llms(thread_id);
