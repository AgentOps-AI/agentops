# OpenAI Response Instrumentation Implementation

This document describes the implementation of the OpenAI responses instrumentation in AgentOps, including key decisions, challenges, and solutions.

## Overview

The OpenAI responses instrumentation is designed to capture telemetry data from both API formats:

1. **Traditional Chat Completions API** - Uses prompt_tokens/completion_tokens terminology with a simpler structure
2. **New Response API Format** - Uses input_tokens/output_tokens terminology with a more complex nested structure

The implementation ensures consistent attributes are extracted from both formats, allowing for unified telemetry and observability regardless of which API format is used.

## Key Components

The implementation consists of:

1. **Response Extractors** (`extractors.py`)
   - Functions to extract structured data from both API formats
   - Normalization of token usage metrics between formats
   - Attribute mapping using semantic conventions

2. **Response Instrumentor** (`../instrumentor.py`)
   - Patches both API formats to capture telemetry
   - Maintains trace context between different API calls
   - Uses a non-invasive approach to avoid breaking existing functionality

3. **Utility Functions** (`__init__.py`)
   - Token usage normalization
   - Get value helper for handling different field paths
   - Common attribute extraction for both formats

## Implementation Challenges

### 1. API Format Differences

The two OpenAI API formats have significant structural differences:

- **Chat Completions API**: Uses a `choices` array with `message.content`
- **Response API**: Uses a nested structure with `output → message → content → [items] → text`

Solution: We implemented dedicated extractors for each format that normalize to the same semantic conventions.

### 2. Response Method Patching

We needed to intercept responses from both API formats without breaking their functionality. Key challenges:

- The `parse` method needed to be patched in a way that preserves its original behavior
- We must avoid interfering with the class's built-in functionality and attributes
- The patching must be resilient to different OpenAI client versions

Solution: We implemented a non-invasive patching approach that:
- Stores the original method
- Creates a wrapped version that calls the original with the same arguments
- Adds telemetry capture after the original method runs

```python
# Store the original method
original_parse = Response.parse

# Define wrapped method with the same signature as the original
@functools.wraps(original_parse)
def instrumented_parse(*args, **kwargs):
    # Call original parse method with the same arguments
    result = original_parse(*args, **kwargs)
    
    # [Add telemetry capture here]
    
    return result

# Apply the patch
Response.parse = instrumented_parse
```

### 3. Context Propagation

Ensuring that different API calls are properly linked in the same trace was essential. Our solution:

- Get the current active span and context before creating new spans
- Pass the current context when creating new spans to maintain the parent-child relationship
- Set parent IDs explicitly for visibility in the trace

```python
# Get the current active span and context
current_span = get_current_span()
current_context = context_api.get_current()

# Create a new span in the existing context
with tracer.start_as_current_span(
    name="openai.response.parse",
    context=current_context,
    kind=SpanKind.CLIENT,
    attributes={...}
) as span:
    # Link to parent span
    if current_span != INVALID_SPAN:
        span.set_attribute(CoreAttributes.PARENT_ID, current_span.get_span_context().span_id)
```

### 4. Token Usage Normalization

The two API formats use different terminology for token metrics:

- **Chat Completions API**: `prompt_tokens`, `completion_tokens`
- **Response API**: `input_tokens`, `output_tokens`, plus additional metrics like `reasoning_tokens`

Solution: We implemented mapping dictionaries that normalize both formats to consistent attribute names:

```python
token_mapping = {
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: ["completion_tokens", "output_tokens"],
}
```

## Integration with OpenTelemetry

Our instrumentation integrates with the existing OpenTelemetry instrumentation for OpenAI:

1. We add our instrumentation to the available instrumentors list
2. Our extractors use the same semantic conventions as the core OpenTelemetry instrumentation
3. We maintain context propagation to ensure proper trace hierarchy

## Testing

The implementation includes:

1. Unit tests for extractors (`tests.py`)
2. Integration tests with the AgentOps instrumentation system
3. A demonstration script showing both API formats working together (`examples/openai_responses/dual_api_example.py`)

## Known Issues and Future Improvements

1. **OpenTelemetry Compatibility**: The underlying OpenTelemetry instrumentation expects `SpanAttributes.LLM_COMPLETIONS`, which is intentionally not exposed in our semantic conventions. This causes a non-critical error in the logs but doesn't impact functionality.

2. **Client Implementation Variations**: Different OpenAI client versions may have different implementation details. Our instrumentation tries to be resilient to these differences, but might need updates as the client evolves.

3. **Future Extensions**: 
   - Add support for multi-modal content types
   - Enhanced token metrics tracking
   - Additional attribute extraction for new API features