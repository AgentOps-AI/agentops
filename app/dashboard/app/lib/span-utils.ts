export interface ParsedSpanName {
  baseName: string; // The main part of the name, typically including framework and entity type.
  typeSuffix: string; // The final segment of the name (e.g., a specific task name, action, or empty if no dot).
}

/**
 * Parses a span name string, which often follows conventions like `framework.entity_type.specific_name`,
 * into a `baseName` and a `typeSuffix`. The split occurs at the last dot.
 * This is a general utility. Specific components might apply further logic based on these parsed parts.
 *
 * Examples based on common conventions:
 * - "adk.agent.HumanApprovalWorkflow" -> { baseName: "adk.agent", typeSuffix: "HumanApprovalWorkflow" }
 * - "crewai.task.ResearchTask"      -> { baseName: "crewai.task", typeSuffix: "ResearchTask" }
 * - "my_custom_tool" (no dots)      -> { baseName: "my_custom_tool", typeSuffix: "" }
 * - "llm.generation"                -> { baseName: "llm", typeSuffix: "generation" }
 * - ".RawEventType"                 -> { baseName: "", typeSuffix: "RawEventType" }
 * - "FrameworkOnly."                -> { baseName: "FrameworkOnly", typeSuffix: "" }
 *
 * @param spanNameToParse The span name string to parse.
 * @returns An object with `baseName` and `typeSuffix`.
 */
export const parseSpanName = (spanNameToParse: string): ParsedSpanName => {
  const lastDotIndex = spanNameToParse.lastIndexOf('.');

  if (lastDotIndex !== -1) {
    // If a dot is found, split the string.
    // This handles cases like ".foo" (baseName="", typeSuffix="foo")
    // and "foo." (baseName="foo", typeSuffix="") correctly based on substring behavior.
    return {
      baseName: spanNameToParse.substring(0, lastDotIndex),
      typeSuffix: spanNameToParse.substring(lastDotIndex + 1),
    };
  }

  // No dot found, the entire string is the baseName, and typeSuffix is empty.
  return { baseName: spanNameToParse, typeSuffix: '' };
};

export interface SpanDisplayDetails {
  displayName: string;
  eventType: string;
}

/**
 * Determines the display name and event type from a raw span name and its attributes.
 * Handles ADK-specific naming conventions (e.g., "adk.agent.SpecificName") and falls back to generic parsing.
 * For ADK agent spans, it prioritizes `spanAttributes.agent.name` if available.
 * @param rawSpanName The raw span name string.
 * @param spanAttributes Optional span attributes, used for ADK agent name override.
 * @returns An object with `displayName` and `eventType`.
 */
export const getSpanDisplayDetails = (
  rawSpanName: string,
  spanAttributes?: any, // Using any for flexibility, consider a more specific type if available
): SpanDisplayDetails => {
  let displayName: string;
  let eventType: string;

  if (rawSpanName.startsWith('adk.')) {
    const parts = rawSpanName.split('.');
    eventType = parts.length > 1 ? parts[1] : 'adk';
    displayName =
      parts.length > 2 ? parts.slice(2).join('.') : parts.length > 1 ? parts[1] : rawSpanName;

    if (eventType.toLowerCase() === 'agent' && spanAttributes?.agent?.name) {
      displayName = spanAttributes.agent.name;
      // Check if this ADK agent has sub_agents, making it a workflow
      if (spanAttributes?.agent?.sub_agents?.length > 0) {
        eventType = 'workflow';
      }
    }
  } else if (rawSpanName.startsWith('ag2.')) {
    // Handle AG2 spans similar to ADK
    const parts = rawSpanName.split('.');
    eventType = parts.length > 1 ? parts[1] : 'ag2';
    displayName =
      parts.length > 2 ? parts.slice(2).join('.') : parts.length > 1 ? parts[1] : rawSpanName;

    // For AG2 agents, use the agent name from attributes if available
    if (eventType.toLowerCase() === 'agent' && spanAttributes?.agent?.name) {
      displayName = spanAttributes.agent.name;
    }
  } else {
    const parsed = parseSpanName(rawSpanName);
    displayName = parsed.baseName;
    eventType = parsed.typeSuffix;

    if (!displayName && parsed.typeSuffix) {
      displayName = parsed.typeSuffix;
    } else if (!displayName && !parsed.typeSuffix) {
      displayName = rawSpanName;
    }
    // If eventType is empty after parsing a non-ADK name, it means the original name had no dot.
    // In such cases, the eventType might be implicitly derived or considered 'unknown'/default by the caller.
    // For now, we leave eventType as potentially empty, as per parseSpanName's behavior for no-dot names.
  }

  return { displayName, eventType };
};
