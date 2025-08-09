import { ISpan } from '@/types/ISpan';

// Common agent data structure
export interface AgentInfo {
    id: string;
    role: string;
    goal?: string;
    backstory?: string;
    description?: string;
    instruction?: string;
    model?: string;
    tools: any[];
    handoffs: string[];
    rawData: any;
    type: 'crewai' | 'openai' | 'adk' | 'agno' | 'ag2';
    // Agno-specific fields
    displayName?: string;
    input?: string;
    output?: string;
    modelProvider?: string;
    reasoning?: string | boolean;
    markdown?: string | boolean;
    showToolCalls?: string | boolean;
    sessionId?: string;
    runId?: string;
}

export interface AgentsViewerProps {
    spans: ISpan[];
}

export interface TextSectionProps {
    title: string;
    content: string;
}

export interface AgentCardProps {
    agent: AgentInfo;
} 