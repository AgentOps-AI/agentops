import { ISpan } from '@/types/ISpan';
import { extractAG2ToolName } from '@/utils/ag2.utils';

export interface ProcessedSpan {
  name: string;
  index: number;
  id: string;
  start: number;
  end: number;
  value: number[];
  duration: number;
  type: string;
  originalSpan: ISpan | null;
  isFiller?: boolean;
  previewText?: string;
}

/**
 * Determines the visual type for ADK spans based on the span name pattern
 * @param spanName - The span name (e.g., "adk.agent.HumanApprovalWorkflow")
 * @param span - The full span object for accessing attributes
 * @returns Object with visualType and previewText
 */
export function processAdkSpan(
  spanName: string,
  span?: ISpan,
): { visualType: string; previewText: string } {
  const adkParts = spanName.split('.');

  if (adkParts.length >= 3) {
    const adkType = adkParts[1]; // Extract type from adk.{type}.{name}
    const adkName = adkParts.slice(2).join('.'); // Get the name part

    // Map ADK types to existing visual types
    switch (adkType) {
      case 'agent':
        // Check if this ADK agent has sub_agents, making it a workflow
        if (span?.span_attributes?.agent?.sub_agents?.length > 0) {
          return { visualType: 'workflow', previewText: adkName || spanName };
        }
        return { visualType: 'agent', previewText: adkName || spanName };
      case 'tool':
        return { visualType: 'tool', previewText: adkName || spanName };
      case 'llm':
        // For ADK LLM spans, try to extract completion message first
        if (span?.span_attributes?.gen_ai) {
          const { previewText: llmPreviewText, contentFound } = processLlmSpanContent(
            span.span_attributes.gen_ai,
          );
          if (contentFound && llmPreviewText) {
            return { visualType: 'llm', previewText: llmPreviewText };
          }
        }
        // Fallback to model name if no completion found
        return { visualType: 'llm', previewText: adkName || spanName };
      case 'task':
        return { visualType: 'task', previewText: adkName || spanName };
      case 'workflow':
        return { visualType: 'workflow', previewText: adkName || spanName };
      case 'operation':
        return { visualType: 'operation', previewText: adkName || spanName };
      default:
        return { visualType: 'other', previewText: adkName || spanName };
    }
  } else {
    // Malformed ADK span name, treat as other
    return { visualType: 'other', previewText: spanName };
  }
}

/**
 * Processes LLM span attributes to extract preview text
 * @param genAi - The gen_ai attributes from the span
 * @returns Object with previewText and whether content was found
 */
export function processLlmSpanContent(genAi: any): { previewText: string; contentFound: boolean } {
  let previewText = '';
  let contentFound = false;

  const getContentFromNestedKeyedObject = (keyedObject: any): string | null => {
    // keyedObject is like genAi.completion[0] which is expected to be an object like { "0": { content: "..." } }
    if (keyedObject && typeof keyedObject === 'object' && !Array.isArray(keyedObject)) {
      const keys = Object.keys(keyedObject);
      if (keys.length > 0) {
        const innerKey = keys[0]; // e.g., "0"
        const messageObject = keyedObject[innerKey];
        if (messageObject && typeof messageObject.content === 'string') {
          return messageObject.content;
        }
      }
    }
    return null;
  };

  if (genAi.completion) {
    // Attempt 1: OpenAI style (first item in completion array)
    if (Array.isArray(genAi.completion) && genAi.completion.length > 0) {
      const content = getContentFromNestedKeyedObject(genAi.completion[0]);
      if (content !== null) {
        previewText = content;
        contentFound = true;
      }
    }

    // Attempt 2: Existing "specific structure" (last item in completion array for tool_calls or content)
    if (!contentFound && Array.isArray(genAi.completion) && genAi.completion.length > 0) {
      const lastMessageContainer = genAi.completion[genAi.completion.length - 1];
      // lastMessageContainer is like { "0": { tool_calls: [], content: "..." } }
      if (
        lastMessageContainer &&
        typeof lastMessageContainer === 'object' &&
        !Array.isArray(lastMessageContainer)
      ) {
        const keys = Object.keys(lastMessageContainer);
        if (keys.length > 0) {
          const firstKey = keys[0]; // This is the "0" or similar key
          const messageObject = lastMessageContainer[firstKey]; // This is the { tool_calls: [], content: "" } object

          if (messageObject && typeof messageObject === 'object') {
            // Check for tool calls first
            if (
              messageObject.tool_calls &&
              Array.isArray(messageObject.tool_calls) &&
              messageObject.tool_calls.length > 0
            ) {
              const toolCall = messageObject.tool_calls[0];
              if (toolCall && typeof toolCall === 'object') {
                const toolCallKeys = Object.keys(toolCall);
                if (toolCallKeys.length > 0) {
                  const toolCallData = toolCall[toolCallKeys[0]];
                  if (toolCallData && toolCallData.name) {
                    let toolPreview = `${toolCallData.name}`;
                    if (toolCallData.arguments) {
                      try {
                        const args = JSON.parse(toolCallData.arguments);
                        const argSummary = Object.entries(args)
                          .slice(0, 2)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(', ');
                        if (argSummary) {
                          toolPreview += ` (${argSummary})`;
                        }
                      } catch {
                        // If JSON parsing fails, just show the tool name
                      }
                    }
                    previewText = toolPreview;
                    contentFound = true;
                  }
                }
              }
            }
            // Check for regular content if no tool calls found or processed
            else if (typeof messageObject.content === 'string') {
              previewText = messageObject.content;
              contentFound = true;
            }
          }
        }
      }
    }

    // Further Fallback for existing completion structures if new one not found
    if (!contentFound) {
      if (typeof genAi.completion === 'string') {
        previewText = genAi.completion;
        contentFound = true;
      } else if (
        Array.isArray(genAi.completion) &&
        genAi.completion.length > 0 &&
        typeof genAi.completion[0] === 'string'
      ) {
        previewText = genAi.completion[0];
        contentFound = true;
      } else if (
        Array.isArray(genAi.completion) &&
        genAi.completion.length > 0 &&
        typeof genAi.completion[0] === 'object' &&
        genAi.completion[0].content
      ) {
        // Handle array of message objects with content property
        previewText = genAi.completion[0].content;
        contentFound = true;
      } else if (typeof genAi.completion === 'object' && genAi.completion !== null) {
        // Check for direct content property
        if (genAi.completion.content && typeof genAi.completion.content === 'string') {
          previewText = genAi.completion.content;
          contentFound = true;
        } else {
          // Look for any string value in the completion object
          const firstStringVal = Object.values(genAi.completion).find((v) => typeof v === 'string');
          if (firstStringVal && typeof firstStringVal === 'string') {
            previewText = firstStringVal;
            contentFound = true;
          }
        }
      }
    }
  }

  // If no content from completion, try prompt as last resort
  if (!contentFound && genAi.prompt) {
    if (typeof genAi.prompt === 'string') {
      previewText = genAi.prompt;
      contentFound = true;
    } else if (
      Array.isArray(genAi.prompt) &&
      genAi.prompt.length > 0 &&
      typeof genAi.prompt[0] === 'string'
    ) {
      previewText = genAi.prompt[0];
      contentFound = true;
    } else if (
      Array.isArray(genAi.prompt) &&
      genAi.prompt.length > 0 &&
      typeof genAi.prompt[0] === 'object' &&
      genAi.prompt[0].content
    ) {
      // Handle array of message objects with content property
      previewText = genAi.prompt[0].content;
      contentFound = true;
    } else if (typeof genAi.prompt === 'object' && genAi.prompt !== null) {
      // Check for direct content property
      if (genAi.prompt.content && typeof genAi.prompt.content === 'string') {
        previewText = genAi.prompt.content;
        contentFound = true;
      } else {
        // Look for any string value in the prompt object
        const firstStringVal = Object.values(genAi.prompt).find((v) => typeof v === 'string');
        if (firstStringVal && typeof firstStringVal === 'string') {
          previewText = firstStringVal;
          contentFound = true;
        }
      }
    }
  }

  return { previewText, contentFound };
}

/**
 * Determines the span visualization type and preview text based on span properties
 * @param span - The span object to process
 * @returns Object with visualType and previewText
 */
export function determineSpanType(span: ISpan): { visualType: string; previewText: string } {
  let visualType = 'other';
  let previewText = span.span_name || '';

  // Check for ADK spans first (highest priority)
  if (span.span_name.startsWith('adk.')) {
    return processAdkSpan(span.span_name, span);
  }

  // ===== AG2 (AutoGen2) Specific Processing =====
  // AG2 is a multi-agent framework with specific patterns for span names and data storage
  if (span.span_name.startsWith('ag2.')) {
    const ag2Parts = span.span_name.split('.');
    if (ag2Parts.length >= 3) {
      const ag2Type = ag2Parts[1]; // Extract type from ag2.{type}.{name}

      if (ag2Type === 'agent') {
        visualType = 'agent';
        // Use agent name as preview text
        previewText = span.span_attributes?.agent?.name || span.span_name;
        return { visualType, previewText };
      } else if (ag2Type === 'tool') {
        visualType = 'tool';
        // Use AG2-specific tool name extraction
        const ag2ToolName = extractAG2ToolName(span);
        if (ag2ToolName) {
          previewText = ag2ToolName;
        } else {
          // Fallback to tool.name, but avoid showing "function"
          const toolName = span.span_attributes?.tool?.name;
          previewText = (toolName && toolName !== 'function') ? toolName : span.span_name;
        }
        return { visualType, previewText };
      }
    }
  }

  // Check for Agno spans
  if (span.span_name.startsWith('agno.')) {
    const agnoParts = span.span_name.split('.');
    if (agnoParts.length >= 3) {
      const agnoType = agnoParts[1]; // Extract type from agno.{type}.{action}.{name}

      if (agnoType === 'tool') {
        visualType = 'tool';
        // Use tool parameters or name as preview text
        if (span.span_attributes?.tool?.parameters) {
          try {
            const params = JSON.parse(span.span_attributes.tool.parameters);
            const paramSummary = Object.entries(params)
              .slice(0, 2)
              .map(([k, v]) => `${k}: ${v}`)
              .join(', ');
            previewText = `${span.span_attributes?.tool?.name || 'tool'} (${paramSummary})`;
          } catch {
            previewText = span.span_attributes?.tool?.name || span.span_name;
          }
        } else {
          previewText = span.span_attributes?.tool?.name || span.span_name;
        }
        return { visualType, previewText };
      } else if (agnoType === 'agent') {
        visualType = 'agent';
        // Use agent input as preview text
        if (span.span_attributes?.agent?.input) {
          previewText = span.span_attributes.agent.input;
        } else if (span.span_attributes?.agentops?.entity?.input) {
          previewText = span.span_attributes.agentops.entity.input;
        } else {
          previewText = span.span_name;
        }
        return { visualType, previewText };
      } else if (agnoType === 'team') {
        // Agno team workflows 
        visualType = 'workflow';
        previewText = span.span_attributes?.team?.display_name || span.span_attributes?.team?.name || span.span_name;
        return { visualType, previewText };
      }
    }
  }

  // Check for specific name endings - these take highest priority for non-ADK spans
  if (span.span_name.endsWith('.session')) {
    visualType = 'session';
  } else if (span.span_name.endsWith('.agent')) {
    visualType = 'agent';
    // Check for agent input field first (for Agno and other agents that have input)
    if (span.span_attributes?.agent?.input) {
      previewText = span.span_attributes.agent.input;
    } else if (span.span_attributes?.agentops?.entity?.input) {
      // Fallback to agentops entity input if available
      previewText = span.span_attributes.agentops.entity.input;
    } else {
      previewText = span.span_attributes?.agent?.name || span.span_name;
    }
  } else if (span.span_name.endsWith('.operation')) {
    visualType = 'operation';
  } else if (span.span_name.endsWith('.task')) {
    visualType = 'task';
    previewText =
      span.span_attributes?.task?.input ||
      span.span_attributes?.task?.description ||
      span.span_name;
  } else if (span.span_name.endsWith('.workflow')) {
    visualType = 'workflow';
    // Check if it's an Agno workflow with team data
    if (span.span_attributes?.gen_ai?.system === 'agno' && span.span_attributes?.team) {
      previewText = span.span_attributes.team.display_name || span.span_attributes.team.name || span.span_name;
    }
  } else if (span.span_name.endsWith('.tool')) {
    visualType = 'tool';
    // Check for tool input or name
    if (span.span_attributes?.tool?.input) {
      previewText = span.span_attributes.tool.input;
    } else if (span.span_attributes?.agentops?.entity?.input) {
      // Fallback to agentops entity input for generic tools
      previewText = span.span_attributes.agentops.entity.input;
    } else {
      previewText = span.span_attributes?.tool?.name || span.span_name;
    }
  }
  // Check if it's an Agno tool (has gen_ai.system='agno' and span.kind='tool')
  else if (
    span.span_attributes?.gen_ai?.system === 'agno' &&
    span.span_attributes?.agentops?.span?.kind === 'tool'
  ) {
    visualType = 'tool';
    // Use tool parameters or name as preview text
    if (span.span_attributes?.tool?.parameters) {
      try {
        const params = JSON.parse(span.span_attributes.tool.parameters);
        const paramSummary = Object.entries(params)
          .slice(0, 2)
          .map(([k, v]) => `${k}: ${v}`)
          .join(', ');
        previewText = `${span.span_attributes?.tool?.name || 'tool'} (${paramSummary})`;
      } catch {
        previewText = span.span_attributes?.tool?.name || span.span_name;
      }
    } else {
      previewText = span.span_attributes?.tool?.name || span.span_name;
    }
  }
  // Only mark as 'request' (LLM) if it's a request type AND has gen_ai attributes
  else if (span.span_type === 'request' && !span.span_attributes?.gen_ai) {
    visualType = 'other';
  }
  // Then check if it's an LLM based on gen_ai attributes (but not Agno tools)
  else if (span.span_attributes?.gen_ai) {
    visualType = 'llm';
    const { previewText: llmPreviewText, contentFound } = processLlmSpanContent(
      span.span_attributes.gen_ai,
    );
    if (contentFound && llmPreviewText) {
      previewText = llmPreviewText;
    } else {
      // Fallback to span name if no completion content found
      previewText = span.span_name;
    }
  } else {
    // Default to span_type if no specific ending matches
    visualType = span.span_type;

    // Special handling for agents identified by span_type with input field
    if (span.span_type === 'agent') {
      if (span.span_attributes?.agent?.input) {
        previewText = span.span_attributes.agent.input;
      } else if (span.span_attributes?.agentops?.entity?.input) {
        // Fallback to agentops entity input if available
        previewText = span.span_attributes.agentops.entity.input;
      }
    }

    // Special handling for workflows identified by span type or span kind
    if (span.span_type === 'workflow' || span.span_attributes?.agentops?.span?.kind === 'workflow') {
      visualType = 'workflow';
      // Check if it's an Agno workflow with team data
      if (span.span_attributes?.gen_ai?.system === 'agno' && span.span_attributes?.team) {
        previewText = span.span_attributes.team.display_name || span.span_attributes.team.name || span.span_name;
      }
    }

    // Special handling for tools identified by span_type
    if (span.span_type === 'tool' || span.span_attributes?.agentops?.span?.kind === 'tool') {
      visualType = 'tool';
      // Use tool parameters or name as preview text
      if (span.span_attributes?.tool?.parameters) {
        try {
          const params = JSON.parse(span.span_attributes.tool.parameters);
          const paramSummary = Object.entries(params)
            .slice(0, 2)
            .map(([k, v]) => `${k}: ${v}`)
            .join(', ');
          previewText = `${span.span_attributes?.tool?.name || 'tool'} (${paramSummary})`;
        } catch {
          previewText = span.span_attributes?.tool?.name || span.span_name;
        }
      } else {
        previewText = span.span_attributes?.tool?.name || span.span_name;
      }
    }
  }

  // Mark spans with ERROR status code as errors (overrides other categorizations)
  if (span.status_code === 'ERROR') {
    visualType = 'error';
    previewText = span.status_message || 'Error';
  }

  return { visualType, previewText };
}

/**
 * Processes preview text by removing trailing periods for non-ADK spans
 * @param previewText - The preview text to process
 * @param spanName - The original span name to check if it's an ADK span
 * @returns Processed preview text
 */
export function processPreviewText(previewText: string, spanName: string): string {
  // General rule: If previewText contains a period, chop off text after the last period.
  // Skip this for ADK spans since they have meaningful periods in their names
  if (previewText && previewText.includes('.') && !spanName.startsWith('adk.')) {
    const lastPeriodIndex = previewText.lastIndexOf('.');
    return previewText.substring(0, lastPeriodIndex);
  }
  return previewText;
}

/**
 * Sanitizes timing values to prevent NaN errors
 * @param offsetFromTraceStartMs - The offset from trace start
 * @param durationMs - The duration in milliseconds
 * @returns Object with sanitized values
 */
export function sanitizeTimingValues(offsetFromTraceStartMs: number, durationMs: number) {
  const sanitizedOffsetFromTraceStartMs = isNaN(offsetFromTraceStartMs)
    ? 0
    : offsetFromTraceStartMs;
  const sanitizedDurationMs = isNaN(durationMs) ? 1 : durationMs;
  const sanitizedEnd = sanitizedOffsetFromTraceStartMs + sanitizedDurationMs;

  return {
    sanitizedOffsetFromTraceStartMs,
    sanitizedDurationMs,
    sanitizedEnd,
  };
}

/**
 * Processes a single span into the format needed for the gantt chart
 * @param span - The span to process
 * @param index - The index of the span
 * @param traceStartTimeMs - The start time of the trace in milliseconds
 * @returns Processed span object
 */
export function processSpan(span: ISpan, index: number, traceStartTimeMs: number): ProcessedSpan {
  const spanStartTimeMs = new Date(span.start_time).getTime();
  const offsetFromTraceStartMs = spanStartTimeMs - traceStartTimeMs;
  const durationMs = span.duration / 1000000;

  // Determine the span visualization type and preview text
  const { visualType, previewText: rawPreviewText } = determineSpanType(span);

  // Process the preview text
  const previewText = processPreviewText(rawPreviewText, span.span_name);

  // Sanitize timing values
  const { sanitizedOffsetFromTraceStartMs, sanitizedDurationMs, sanitizedEnd } =
    sanitizeTimingValues(offsetFromTraceStartMs, durationMs);

  return {
    name: span.span_name,
    index,
    id: span.span_id,
    start: sanitizedOffsetFromTraceStartMs,
    end: sanitizedEnd,
    value: [sanitizedOffsetFromTraceStartMs, sanitizedEnd],
    duration: sanitizedDurationMs,
    type: visualType,
    originalSpan: span,
    previewText: previewText,
  };
}

/**
 * Creates filler spans when there are fewer than the minimum required
 * @param processedSpans - The already processed spans
 * @param minSpans - The minimum number of spans required
 * @returns Array of filler spans to add
 */
export function createFillerSpans(
  processedSpans: ProcessedSpan[],
  minSpans: number = 10,
): ProcessedSpan[] {
  if (processedSpans.length >= minSpans) {
    return [];
  }

  const lastBarEnd = processedSpans.length > 0 ? processedSpans[processedSpans.length - 1].end : 0;
  const fillerBarsNeeded = minSpans - processedSpans.length;
  const fillerSpans: ProcessedSpan[] = [];

  for (let i = 0; i < fillerBarsNeeded; i++) {
    fillerSpans.push({
      name: `Filler ${i + 1}`,
      index: processedSpans.length + i,
      id: `filler-${i}`,
      start: lastBarEnd,
      end: lastBarEnd,
      value: [lastBarEnd, lastBarEnd],
      duration: 0,
      type: 'default',
      originalSpan: null,
      isFiller: true,
      previewText: '',
    });
  }

  return fillerSpans;
}

/**
 * Configuration for span type filtering
 */
export const SPAN_TYPE_FILTER_CONFIG = {
  // Define the order of span types
  orderedTypes: [
    'agent',
    'llm',
    'tool',
    'operation',
    'task',
    'error',
    'workflow',
    'other',
    'session',
  ],
  // Always include these types in filters
  alwaysIncluded: new Set(['agent', 'tool', 'llm']),
  // Fallback type when no types are available
  fallbackType: 'session',
};

/**
 * Gets the display types for span type filters
 * @param availableTypes - Set of types that exist in the data
 * @returns Array of types to display in filters
 */
export function getDisplayTypes(availableTypes: Set<string>): string[] {
  const { orderedTypes, alwaysIncluded, fallbackType } = SPAN_TYPE_FILTER_CONFIG;

  // Filter to show always included types and other types that exist in the data, maintaining the order
  const typesToShow = orderedTypes.filter(
    (type) => alwaysIncluded.has(type) || availableTypes.has(type),
  );

  // If no types are available, at least show fallback
  return typesToShow.length > 0 ? typesToShow : [fallbackType];
}

/**
 * Calculates the latest span end time, ensuring it's always at least 1
 * @param processedSpans - Array of processed spans
 * @returns The latest end time
 */
export function calculateLatestSpanEnd(processedSpans: ProcessedSpan[]): number {
  return Math.max(1, ...processedSpans.map((span) => (isNaN(span.end) ? 0 : span.end)));
}

/**
 * Creates a fallback span for when all types are filtered out
 * @returns A fallback ProcessedSpan object
 */
export function createFallbackSpan(): ProcessedSpan {
  return {
    name: 'No spans visible',
    index: 0,
    id: 'no-data',
    start: 0,
    end: 1,
    value: [0, 1],
    duration: 1,
    type: 'default',
    originalSpan: null,
    isFiller: true,
    previewText: '',
  };
}
