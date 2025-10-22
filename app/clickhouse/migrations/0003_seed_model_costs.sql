INSERT INTO otel_2.model_costs_source (model, prompt_cost_per_1k, completion_cost_per_1k) VALUES
('gpt-4o-mini', 0.00015, 0.00060),
('gpt-4o',      0.00500, 0.01500),
('claude-3-5-sonnet', 0.00300, 0.01500),
('perplexity/sonar', 0.00010, 0.00040),
('perplexity/sonar-pro', 0.00050, 0.00150);

SYSTEM RELOAD DICTIONARY otel_2.model_costs_dict;
