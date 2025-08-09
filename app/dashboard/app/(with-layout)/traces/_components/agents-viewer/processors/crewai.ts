import { ISpan } from '@/types/ISpan';
import { AgentInfo } from '../types';

// Process CrewAI agent data
export const processCrewAIAgent = (span: ISpan): AgentInfo | null => {
    if (!span.span_name?.endsWith('.agent') || !span.span_attributes?.agent?.id) {
        return null;
    }

    // Skip if this is a workflow
    if (span.span_name?.endsWith('.workflow')) {
        return null;
    }

    const agentId = span.span_attributes.agent.id;
    const rawTools = span.span_attributes.crewai?.agent?.tool || [];

    // Process tools to ensure they have proper structure
    const tools = rawTools.map((tool: any) => {
        // If tool is a string, convert it to an object
        if (typeof tool === 'string') {
            return { name: tool };
        }
        // If tool has a 'description' key that contains the actual tool data
        if (tool.description && typeof tool.description === 'object') {
            return tool.description;
        }
        return tool;
    });

    return {
        id: agentId,
        role: span.span_attributes.agent?.role || 'Unknown Agent',
        goal: span.span_attributes.crewai?.agent?.goal || '',
        backstory: span.span_attributes.crewai?.agent?.backstory || '',
        model: span.span_attributes.agent?.models || '',
        tools,
        handoffs: [],
        rawData: {
            ...span.span_attributes.agent,
            ...span.span_attributes.crewai?.agent,
        },
        type: 'crewai',
    };
}; 