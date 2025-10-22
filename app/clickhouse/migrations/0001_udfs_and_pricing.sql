CREATE TABLE IF NOT EXISTS otel_2.model_costs_source
(
    `model` String,
    `prompt_cost_per_1k` Float64,
    `completion_cost_per_1k` Float64
)
ENGINE = MergeTree
ORDER BY model;

DROP DICTIONARY IF EXISTS otel_2.model_costs_dict;
CREATE DICTIONARY otel_2.model_costs_dict
(
    `model` String,
    `prompt_cost_per_1k` Float64,
    `completion_cost_per_1k` Float64
)
PRIMARY KEY model
SOURCE(CLICKHOUSE(HOST 'localhost' PORT 9000 USER 'default' DB 'otel_2' TABLE 'model_costs_source'))
LIFETIME(MIN 0 MAX 0)
LAYOUT(COMPLEX_KEY_HASHED());

DROP FUNCTION IF EXISTS normalize_model_name;
CREATE FUNCTION normalize_model_name AS model ->
    multiIf(
        lower(model) = 'sonar-pro', 'perplexity/sonar-pro',
        lower(model) = 'sonar',     'perplexity/sonar',
        lower(model)
    );

DROP FUNCTION IF EXISTS calculate_prompt_cost;
CREATE FUNCTION calculate_prompt_cost AS (tokens, model) ->
    if((tokens > 0) AND (model != ''),
        round((toFloat64(tokens) / 1000) * dictGetOrDefault('model_costs_dict', 'prompt_cost_per_1k', normalize_model_name(model), 0.), 7),
        0.);

DROP FUNCTION IF EXISTS calculate_completion_cost;
CREATE FUNCTION calculate_completion_cost AS (tokens, model) ->
    if((tokens > 0) AND (model != ''),
        round((toFloat64(tokens) / 1000) * dictGetOrDefault('model_costs_dict', 'completion_cost_per_1k', normalize_model_name(model), 0.), 7),
        0.);
