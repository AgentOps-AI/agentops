
INSERT INTO otel_2.model_costs_source (model, prompt_cost_per_1k, completion_cost_per_1k) VALUES
('ai21/jamba-instruct', 0.00100, 0.00400),
('ai21/jamba-1-5-large', 0.00250, 0.01000),
('anthropic/claude-3-5-haiku', 0.00080, 0.00400),
('anthropic/claude-3-5-sonnet', 0.00300, 0.01500),
('anthropic/claude-3-opus', 0.01500, 0.07500),
('anthropic/claude-3-sonnet', 0.00300, 0.01500),
('anthropic/claude-3-haiku', 0.00025, 0.00125),
('openai/gpt-4o', 0.00500, 0.01500),
('openai/gpt-4o-mini', 0.00015, 0.00060),
('openai/gpt-4.1', 0.01000, 0.03000),
('openai/gpt-4o-realtime', 0.01500, 0.06000),
('openai/gpt-3.5-turbo', 0.00050, 0.00150),
('perplexity/sonar', 0.00010, 0.00040),
('perplexity/sonar-pro', 0.00050, 0.00150),
('mistral/mistral-large', 0.00300, 0.01200),
('mistral/mistral-small', 0.00020, 0.00060),
('groq/llama-3.1-8b-instant', 0.00005, 0.00010),
('groq/llama-3.1-70b-versatile', 0.00059, 0.00079),
('google/gemini-1.5-pro', 0.00125, 0.00500),
('google/gemini-1.5-flash', 0.000075, 0.00030);

SYSTEM RELOAD DICTIONARY otel_2.model_costs_dict;
