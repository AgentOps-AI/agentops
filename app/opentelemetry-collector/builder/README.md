# OpenTelemetry Collector Builder

This package transforms token cost data from the `tokencost` package into YAML configurations for the OpenTelemetry collector, enabling real-time cost calculation for LLM application traces. It also provides tools for generating and managing OpenTelemetry collector configuration files.

## Goals

- Extract token cost data from the `tokencost` package's JSON model price database
- Transform this data into YAML configuration for OpenTelemetry collector-contrib processors
- Generate complete configurations for the OpenTelemetry collector
- Apply OTTL (OpenTelemetry Transformation Language) transforms to spans with `gen_ai.usage.completion_tokens` and/or `gen_ai.usage.prompt_tokens` attributes
- Match costs to the appropriate model using the `gen_ai.request.model` span attribute
- Enable real-time cost attribution on LLM API spans based on model and token usage

## How It Works

1. The builder loads token pricing data from the `tokencost` package's `model_prices.json` file
2. This data is parsed and converted to appropriate decimal precision formats
3. Template files in the config directory are processed, injecting the model costs
4. The resulting YAML configurations for the OpenTelemetry collector are generated
5. These configurations include OTTL transformations that identify spans with the `gen_ai.request.model` attribute and apply the corresponding cost data

## Usage

```bash
# Generate configurations with default output directory
python -m builder build_configs

# Generate configurations with custom output directory
python -m builder build_configs -o /path/to/output/directory
```

The generated configuration will conditionally apply cost transformations to spans with token usage attributes, allowing for automatic cost attribution in your telemetry pipeline. This is also used in the Docker build process to generate configurations at build time.

## Configuration Format

The exported YAML configuration creates a transform processor that:

1. Populates a span cache with model-specific cost per token values during the build process
2. Inspects spans for the `gen_ai.request.model` attribute to identify the LLM model in use
3. Uses OTTL transforms with `where` clauses to calculate and attribute costs based on `gen_ai.usage.prompt_tokens` and `gen_ai.usage.completion_tokens`
4. Applies the relevant model-specific costs only when both model and token usage attributes are present

This allows the OpenTelemetry collector to automatically calculate and attribute costs for LLM API calls as they pass through the telemetry pipeline. The configuration uses conditional logic to match the model name from span attributes to the appropriate pricing data from the tokencost package.

## OTTL Configuration Example

Below is an example of how the OTTL transformations are implemented in the OpenTelemetry collector configuration YAML:

```yaml
processors:
  transform:
    trace_statements:
      # We are using root-level trace_statements so that the cache is shared across
      # all transforms in the pipeline (as opposed to `- scope: span` which creates
      # a new cache for each transform)

      # Cost data gets populated dynamically on container build
      # For each model in the tokencost database, we add input and output costs
      # Example:
      # - set(span.cache["_input_costs"]["gpt-4"], 0.00001)
      # - set(span.cache["_output_costs"]["gpt-4"], 0.00003)

      # Set prompt cost on spans that have prompt tokens and a known model
      - set(span.attributes["gen_ai.usage.prompt_cost"],
          Double(span.attributes["gen_ai.usage.prompt_tokens"]) *
          span.cache["_input_costs"][span.attributes["gen_ai.request.model"]])
          where (
            span.attributes["gen_ai.usage.prompt_tokens"] != nil and
            span.attributes["gen_ai.request.model"] != nil and
            span.cache["_input_costs"][span.attributes["gen_ai.request.model"]] != nil)

      # Set completion cost on spans that have completion tokens and a known model
      - set(span.attributes["gen_ai.usage.completion_cost"],
          Double(span.attributes["gen_ai.usage.completion_tokens"]) *
          span.cache["_output_costs"][span.attributes["gen_ai.request.model"]])
          where (
            span.attributes["gen_ai.usage.completion_tokens"] != nil and
            span.attributes["gen_ai.request.model"] != nil and
            span.cache["_output_costs"][span.attributes["gen_ai.request.model"]] != nil)
```

This example demonstrates how we:

1. Store model costs in a span cache using the "_input_costs" and "_output_costs" dictionaries to avoid polluting attributes
2. Use root-level trace_statements to ensure the cache is shared across all transformations in the pipeline
3. Dynamically populate the cost data during container build time from the tokencost package
4. Use conditional "where" clauses to only apply cost calculations when:
   - The span has the required attributes (gen_ai.usage.prompt_tokens/completion_tokens)
   - The span specifies a model (gen_ai.request.model)
   - The model has known costs in our cache
5. Apply targeted conditions to minimize unnecessary processing and only calculate costs when all required data is present

The key advantage of this implementation is that cost data is:
1. Dynamically generated at build time from the latest tokencost data
2. Stored in memory only (not in actual span attributes until calculations are done)
3. Used only when spans have the appropriate attributes
4. Applied uniformly across all spans in the pipeline

The actual processor configuration includes model cost data for all models available in the tokencost package database, populated through a Jinja2 template at build time.


## Implementation References

The implementation uses these OpenTelemetry Transformation Language (OTTL) features:

- [OTTL Where Clauses](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md#where) - Used for conditional application of transformations
- [Span Cache](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/contexts/ottlspan/README.md#spancache) - Storing model cost data without polluting span attributes
- [Double Function](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/ottlfuncs/README.md#double) - Converting token counts to floating point for calculations
- [Nil Checks](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md#nil) - Ensuring attributes exist before processing
- [Set Function](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/ottlfuncs/README.md#set) - Creating new span attributes with calculated costs
- [Dictionary Access](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md#indexing) - Accessing model costs by model name

This implementation follows the [OpenTelemetry Semantic Conventions for AI/ML](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/ai/ai-spans.md) and leverages [Jinja2 Templates](https://jinja.palletsprojects.com/) for configuration generation at build time.