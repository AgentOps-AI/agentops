# OpenAI Responses Implementation Guide

This document outlines the structure and implementation details of OpenAI's response formats, and how AgentOps instruments these responses for telemetry and observability.

## OpenAI API Response Formats

OpenAI provides two primary API response formats, which need to be handled differently:

1. **Traditional Completions API Format** 
   - Uses terminology: `prompt_tokens`, `completion_tokens`, `total_tokens`
   - Simpler, more direct structure with `choices` array
   - Accessible via the `LegacyAPIResponse` class
   - Example usage stats:
     ```json
     {
       "usage": {
         "prompt_tokens": 10,
         "completion_tokens": 20,
         "total_tokens": 30
       }
     }
     ```

2. **Response API Format** (used by newer APIs, including Agents SDK)
   - Uses terminology: `input_tokens`, `output_tokens`, `total_tokens`
   - More complex, nested structure: `output → message → content → [items] → text`
   - Accessible via the `Response` class
   - Includes additional token details like `reasoning_tokens`
   - Example usage stats:
     ```json
     {
       "usage": {
         "input_tokens": 10,
         "output_tokens": 20,
         "total_tokens": 30,
         "output_tokens_details": {
           "reasoning_tokens": 5
         }
       }
     }
     ```

## Core Response Classes

### OpenAI Response Structure

- **BaseAPIResponse**: Common base class with shared functionality
- **APIResponse**: Synchronous handling
- **AsyncAPIResponse**: Asynchronous handling
- **LegacyAPIResponse**: Backward compatibility

### Modern Response API Structure

- **Response**: Main container with rich metadata
- **ResponseOutputItem**: Items in the output array
- **ResponseOutputText**: Text content within output items
- **ResponseUsage**: Token usage statistics

### ParsedResponse Classes

- **ParsedResponse**: Adds generic parsing capability
- **ParsedResponseOutputText**: Text with parsed content
- **ParsedResponseOutputMessage**: Structured message with parsed content

## Implementation in AgentOps

AgentOps provides a unified interface to handle both response formats through:

1. **Standardized Attribute Mapping**:
   - Maps both API formats to consistent semantic conventions
   - Uses attribute path conventions like `SpanAttributes.LLM_USAGE_PROMPT_TOKENS`

2. **Token Mapping Strategy**:
   - Normalizes token usage fields between different API formats
   - Example from `process_token_usage()`:

   ```python
   # Define mapping for standard usage metrics (target → source)
   token_mapping = {
       SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
       SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
       SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: ["completion_tokens", "output_tokens"],
   }
   ```

3. **Content Extraction**:
   - Handles different content formats and nested structures
   - For Response API format, traverses the nested structure:
     ```
     output → message → content → [items] → text
     ```

## Response API Content Extraction Process

The Response API requires special handling due to its nested structure:

```python
if "output" in response_dict:
    # Process each output item for detailed attributes
    for i, item in enumerate(response_dict["output"]):
        # Extract role if present
        if "role" in item:
            attributes[f"gen_ai.completion.{i}.role"] = item["role"]
        
        # Extract text content if present
        if "content" in item:
            content_items = item["content"]
            
            if isinstance(content_items, list):
                # Combine text from all text items
                texts = []
                for content_item in content_items:
                    if content_item.get("type") == "output_text" and "text" in content_item:
                        texts.append(content_item["text"])
                
                # Join texts (even if empty)
                attributes[f"gen_ai.completion.{i}.content"] = " ".join(texts)
```

## Usage Metrics

Both token formats can be instrumented with these key metrics:

1. **Token Counters**:
   - `gen_ai.usage.prompt_tokens` / `gen_ai.usage.input_tokens`
   - `gen_ai.usage.completion_tokens` / `gen_ai.usage.output_tokens`
   - `gen_ai.usage.total_tokens`
   - `gen_ai.usage.reasoning_tokens` (when available)

2. **Histograms**:
   - `gen_ai.operation.duration`: Duration of operations in seconds
   - `gen_ai.token_usage`: Token usage broken down by token type

## Best Practices

1. **Target → Source Mapping Pattern**
   - Use consistent dictionary mapping where keys are target attribute names
   - Example:
     ```python
     mapping = {
         # Target semantic convention → source field
         SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
     }
     ```

2. **Don't Parse Content JSON**
   - Keep raw response content as strings, avoid parsing JSON
   - Maintain exact structure for accurate observability

3. **Handle Streaming Operations**
   - Track token usage incrementally
   - Accumulate metrics across streaming chunks
   - Finalize spans after completion

4. **Attribute Consistency**
   - Use semantic convention constants throughout
   - Follow structured attribute naming conventions

## Future Enhancements

1. **Complete Response Object Structure**
   - Model all response fields, including metadata and status

2. **Extended Token Details**
   - Capture additional token metrics as they become available
   - Support for model-specific token breakdowns

3. **Unified Content Extraction**
   - Consistent handler for all content formats
   - Support for non-text content types (images, audio)

4. **Response Status Tracking**
   - Track response lifecycle throughout streaming
   - Capture errors and partial responses