/**
 * Utility functions for AG2 (AutoGen2) specific logic
 * AG2 is a multi-agent framework that has specific patterns for storing tool and agent data
 */

import { ISpan } from '@/types/ISpan';

/**
 * Extracts the actual tool name from an AG2 tool span
 * AG2 stores the actual tool name in gen_ai.request.tools[0].name
 * while tool.name just contains "function"
 * 
 * @param span - The span to extract tool name from
 * @returns The actual tool name or null if not found
 */
export function extractAG2ToolName(span: ISpan | null | undefined): string | null {
  if (!span) return null;
  
  // Check if this is an AG2 tool span
  if (!span.span_name?.startsWith('ag2.tool.')) return null;
  
  // AG2 stores the actual tool name in gen_ai.request.tools
  const genAiTools = span.span_attributes?.gen_ai?.request?.tools;
  if (genAiTools && Array.isArray(genAiTools) && genAiTools.length > 0 && genAiTools[0].name) {
    return genAiTools[0].name;
  }
  
  return null;
}

/**
 * Checks if a span is an AG2 span based on its name pattern
 * @param spanName - The span name to check
 * @returns true if this is an AG2 span
 */
export function isAG2Span(spanName: string | undefined | null): boolean {
  return spanName?.startsWith('ag2.') || false;
}

/**
 * Gets the type of AG2 span (agent, tool, etc.)
 * @param spanName - The span name to parse
 * @returns The AG2 span type or null
 */
export function getAG2SpanType(spanName: string | undefined | null): string | null {
  if (!spanName?.startsWith('ag2.')) return null;
  
  const parts = spanName.split('.');
  return parts.length >= 2 ? parts[1] : null;
}

/**
 * Deserializes AG2 tool result which is stored as a JSON string
 * @param result - The result string to deserialize
 * @returns The deserialized result or the original string if parsing fails
 */
export function deserializeAG2ToolResult(result: string | undefined | null): {
  content?: string;
  name?: string;
  role?: string;
  raw: string;
} | null {
  if (!result || typeof result !== 'string') return null;
  
  try {
    const parsed = JSON.parse(result);
    if (typeof parsed === 'object' && parsed !== null) {
      return {
        content: parsed.content,
        name: parsed.name,
        role: parsed.role,
        raw: result
      };
    }
  } catch (e) {
    // If parsing fails, return the raw string
  }
  
  return { raw: result };
}

/**
 * Formats AG2 tool arguments which are stored as JSON strings
 * @param args - The arguments string to format
 * @returns Formatted arguments string
 */
export function formatAG2ToolArguments(args: string | undefined | null): string {
  if (!args || typeof args !== 'string') return '';
  
  try {
    const parsed = JSON.parse(args);
    return JSON.stringify(parsed, null, 2);
  } catch (e) {
    // Return original if parsing fails
    return args;
  }
} 