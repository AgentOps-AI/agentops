import { ISpan } from '@/types/ISpan';
import { AgentInfo } from '../types';
import { parseJsonData } from '../utils';

// Process AG2 agent data
export const processAG2Agent = (span: ISpan): AgentInfo | null => {
    // Check if this is an AG2 agent span
    if (!span.span_name?.startsWith('ag2.agent.') || span.span_type !== 'agent') {
        return null;
    }

    const agentAttributes = span.span_attributes?.agent;
    if (!agentAttributes?.name) {
        return null;
    }

    const agentName = agentAttributes.name;
    const sender = agentAttributes.sender || '';
    const input = span.span_attributes?.agentops?.entity?.input || '';

    // Extract tools if available (AG2 might store them differently)
    const tools = parseJsonData(agentAttributes?.tools, []);
    const handoffs = parseJsonData(agentAttributes?.handoffs, []);

    return {
        id: agentName,
        role: agentName,
        description: sender ? `Receives messages from: ${sender}` : undefined,
        input: input,
        tools,
        handoffs,
        rawData: {
            ...agentAttributes,
            ...span.span_attributes?.agentops?.entity,
            sender,
        },
        type: 'ag2',
    };
}; 