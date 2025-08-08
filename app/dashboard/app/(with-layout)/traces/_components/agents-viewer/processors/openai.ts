import { ISpan } from '@/types/ISpan';
import { AgentInfo } from '../types';
import { parseJsonData } from '../utils';

// Process OpenAI agent data
export const processOpenAIAgent = (span: ISpan): AgentInfo | null => {
    const agentAttributes = span.span_attributes?.agent;

    if (
        span.span_type !== 'agent' ||
        !agentAttributes?.name ||
        (span.span_name?.endsWith('.agent') && agentAttributes?.id) ||
        agentAttributes?.description ||
        span.span_name?.endsWith('.workflow') // Skip workflow spans
    ) {
        return null;
    }

    const agentName = agentAttributes.name;

    const tools = parseJsonData(agentAttributes?.tools, []);
    const handoffs = parseJsonData(span.span_attributes.handoffs, []);

    return {
        id: agentName,
        role: agentName,
        model: agentAttributes?.models || '',
        tools,
        handoffs,
        rawData: {
            ...agentAttributes,
            handoffs,
        },
        type: 'openai',
    };
}; 