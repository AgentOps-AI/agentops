import { ISpan } from '@/types/ISpan';
import {
    determineSpanType as processDetermineSpanType,
    processPreviewText
} from '@/components/charts/bar-chart/span-processing';

export interface SpanDisplayInfo {
    displayName: string;
    spanType: string;
    shortType: string;
}



/**
 * Gets a short uppercase label for the span type
 */
function getShortTypeLabel(spanType: string): string {
    const typeMap: Record<string, string> = {
        session: 'Session',
        agent: 'Agent',
        operation: 'OP',
        task: 'Task',
        workflow: 'Workflow',
        llm: 'LLM',
        tool: 'Tool',
        tool_usage: 'Tool',
        error: 'Error',
        other: 'Span',
    };

    return typeMap[spanType] || spanType.toUpperCase();
}

/**
 * Processes preview text to ensure it's not too long and handles edge cases
 */
function processDisplayName(text: string, fallback: string, maxLength: number = 50): string {
    if (!text || text.trim() === '') {
        return fallback;
    }

    // Clean up the text
    let processed = text.trim();

    // Remove quotes if they wrap the entire string
    if (
        (processed.startsWith('"') && processed.endsWith('"')) ||
        (processed.startsWith("'") && processed.endsWith("'"))
    ) {
        processed = processed.slice(1, -1);
    }

    // Truncate if too long
    if (processed.length > maxLength) {
        return processed.substring(0, maxLength - 3) + '...';
    }

    return processed;
}

/**
 * Get display information for a span
 * This is the main function to use for consistent span display across the app
 */
export function getSpanDisplayInfo(span: ISpan): SpanDisplayInfo {
    // Use the same logic as the Gantt chart for determining span type and preview text
    const { visualType, previewText: rawPreviewText } = processDetermineSpanType(span);

    const spanType = visualType;
    const shortType = getShortTypeLabel(spanType);

    // Process the preview text exactly like the Gantt chart
    const previewText = processPreviewText(rawPreviewText, span.span_name);

    // For LLM spans, allow longer preview text to show more content
    const maxLength = spanType === 'llm' ? 100 : 50;
    const displayName = processDisplayName(previewText, span.span_name, maxLength);

    return {
        displayName,
        spanType,
        shortType,
    };
} 