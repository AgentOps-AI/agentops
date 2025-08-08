import { useMemo } from 'react';
import { AgentsViewerProps, AgentInfo } from './types';
import { AgentCard } from './components/AgentCard';
import { processCrewAIAgent } from './processors/crewai';
import { processADKAgent } from './processors/adk';
import { processOpenAIAgent } from './processors/openai';
import { processAgnoAgent } from './processors/agno';
import { processAG2Agent } from './processors/ag2';

export const AgentsViewer = ({ spans }: AgentsViewerProps) => {
    // Extract agent data from spans
    const agentData = useMemo(() => {
        const agentMap = new Map<string, AgentInfo>();

        // Process all spans to extract agent data
        spans.forEach((span) => {
            // Try to process as Agno agent first (check for .agno. in span name)
            let agent = processAgnoAgent(span);
            if (agent) {
                if (!agentMap.has(agent.id)) {
                    agentMap.set(agent.id, agent);
                }
                return; // Move to next span if processed
            }

            // Try to process as AG2 agent (check for ag2.agent. in span name)
            agent = processAG2Agent(span);
            if (agent) {
                if (!agentMap.has(agent.id)) {
                    agentMap.set(agent.id, agent);
                }
                return; // Move to next span if processed
            }

            // Try to process as CrewAI agent (specific pattern)
            agent = processCrewAIAgent(span);
            if (agent) {
                if (!agentMap.has(agent.id)) {
                    agentMap.set(agent.id, agent);
                }
                return; // Move to next span if processed
            }

            // Try to process as ADK agent
            agent = processADKAgent(span);
            if (agent) {
                if (!agentMap.has(agent.id)) {
                    agentMap.set(agent.id, agent);
                }
                return; // Move to next span if processed
            }

            // Try to process as OpenAI agent (more general)
            agent = processOpenAIAgent(span);
            if (agent) {
                if (!agentMap.has(agent.id)) {
                    agentMap.set(agent.id, agent);
                }
                // No return here, it's the last processor for this span
            }
        });

        return Array.from(agentMap.values());
    }, [spans]);

    return (
        <div className="h-full overflow-y-auto">
            <div className="p-6">
                {agentData.length === 0 ? (
                    <div className="p-4 text-center">No agent data found</div>
                ) : (
                    agentData.map((agent) => <AgentCard key={agent.id} agent={agent} />)
                )}
                <div className="h-10"></div>
            </div>
        </div>
    );
}; 