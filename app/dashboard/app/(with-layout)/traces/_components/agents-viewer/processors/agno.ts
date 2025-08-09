import { ISpan } from '@/types/ISpan';
import { AgentInfo } from '../types';

// Process Agno agent data
export const processAgnoAgent = (span: ISpan): AgentInfo | null => {
    if (
        !span.span_name?.includes('.agno.') ||
        span.span_type !== 'agent' ||
        !span.span_attributes?.agent
    ) {
        return null;
    }

    const agentAttributes = span.span_attributes.agent;
    const agentId = agentAttributes.id || agentAttributes.name || 'unknown-agno-agent';

    // For Agno, tools are stored in span_attributes.tool as an array of objects
    // with name and description fields
    let tools: any[] = [];

    if (span.span_attributes?.tool) {
        // span_attributes.tool can be an array or a single object
        tools = Array.isArray(span.span_attributes.tool)
            ? span.span_attributes.tool
            : [span.span_attributes.tool];
    } else if (agentAttributes.tools) {
        // Fallback to parsing tools from agent.tools if no detailed tool info
        try {
            const toolNames = typeof agentAttributes.tools === 'string'
                ? JSON.parse(agentAttributes.tools)
                : agentAttributes.tools;
            // Convert tool names to objects for consistent display
            tools = Array.isArray(toolNames)
                ? toolNames.map((name: string) => ({ name }))
                : [{ name: toolNames }];
        } catch (e) {
            // If parsing fails, treat as a single tool name
            tools = [{ name: agentAttributes.tools }];
        }
    }

    // Get model info from gen_ai attributes
    const genAiData = span.span_attributes?.gen_ai;
    const model = genAiData?.request?.model || genAiData?.response?.model || '';

    return {
        id: agentId,
        role: agentAttributes.role || agentAttributes.display_name || agentAttributes.name || 'Agno Agent',
        displayName: agentAttributes.display_name,
        instruction: agentAttributes.instruction,
        input: agentAttributes.input,
        output: agentAttributes.output,
        model,
        modelProvider: agentAttributes.model_provider,
        tools,
        handoffs: [],
        reasoning: agentAttributes.reasoning,
        markdown: agentAttributes.markdown,
        showToolCalls: agentAttributes.show_tool_calls,
        sessionId: agentAttributes.session_id,
        runId: agentAttributes.run_id || agentAttributes.run_session_id,
        rawData: {
            ...agentAttributes,
            gen_ai: genAiData,
            tool: span.span_attributes?.tool,
        },
        type: 'agno',
    };
}; 