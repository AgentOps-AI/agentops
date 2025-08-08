import { ISpan } from '@/types/ISpan';
import { AgentInfo } from '../types';
import { parseJsonData } from '../utils';

// Process ADK agent data
export const processADKAgent = (span: ISpan): AgentInfo | null => {
    if (
        span.span_type !== 'agent' ||
        !span.span_attributes?.agent?.description ||
        (span.span_name?.endsWith('.agent') && span.span_attributes?.agent?.id) ||
        span.span_name?.startsWith('adk.workflow.') // Skip explicit ADK workflow spans
    ) {
        return null;
    }

    const agentAttributes = span.span_attributes.agent;
    const agentKey = agentAttributes.id || agentAttributes.name;

    if (!agentKey) {
        console.warn(
            'ADK Agent span found with description but no agent.id or agent.name, skipping span_id:',
            span.span_id,
        );
        return null;
    }

    // Skip if this is actually a workflow (has sub_agents)
    if (agentAttributes.sub_agents && agentAttributes.sub_agents.length > 0) {
        return null;
    }

    // Handle tools - check both agent.tools and span_attributes.tool
    let tools = parseJsonData(agentAttributes?.tools, []);

    // If there's a tool at the span level, add it to the tools array
    if (span.span_attributes?.tool) {
        tools = [...tools, span.span_attributes.tool];
    }

    const handoffs = parseJsonData(span.span_attributes.handoffs, []);

    return {
        id: agentKey,
        role: agentAttributes.name || agentAttributes.id || 'Unknown ADK Agent',
        description: agentAttributes.description,
        instruction: agentAttributes.instruction,
        model: agentAttributes?.models || agentAttributes?.model || '',
        tools,
        handoffs,
        rawData: {
            ...agentAttributes,
            handoffs,
            tool: span.span_attributes?.tool,
        },
        type: 'adk',
    };
}; 