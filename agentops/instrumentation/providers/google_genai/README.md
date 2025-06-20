# Google Generative AI (Gemini) Instrumentation

This module provides OpenTelemetry instrumentation for Google's Generative AI (Gemini) API. The instrumentation allows you to trace all API calls made using the `google-genai` Python SDK, capturing:

- Model parameters (temperature, max_tokens, etc.)
- Prompt content (with privacy controls)
- Response text and token usage
- Streaming metrics
- Token counting
- Performance and error data

## Supported Features

The instrumentation covers all major API methods including:

### Client-Based API
- `client.models.generate_content`
- `client.models.generate_content_stream`
- `client.models.count_tokens`
- `client.models.compute_tokens`
- And their corresponding async variants

## Metrics

The instrumentation captures the following metrics:

- Input tokens used
- Output tokens generated
- Total tokens consumed
- Operation duration
- Exception counts

These metrics are available as OpenTelemetry span attributes and can be viewed in your observability platform of choice when properly configured.