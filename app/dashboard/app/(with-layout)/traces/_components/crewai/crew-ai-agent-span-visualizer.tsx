import BaseAgentSpanVisualizer from '../agents/base-agent-span-visualizer';
import CollapsibleSection, { OutputViewer } from './collapsible-section';
import React from 'react';

interface CrewAIAgentVisualizerProps {
  spanAttributes: any;
}

const CrewAIAgentSpanVisualizer = ({ spanAttributes }: CrewAIAgentVisualizerProps) => {
  const crewaiAgentData = spanAttributes?.crewai?.agent;

  if (!crewaiAgentData) {
    return (
      <div className="max-w-2xl p-4">
        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
          No CrewAI agent data available.
        </p>
      </div>
    );
  }

  const agentDataForBase = {
    name: crewaiAgentData.role || 'CrewAI Agent', // Use role as name
  };
  // Ensure tools is always an array
  const tools = Array.isArray(crewaiAgentData.tool) ? crewaiAgentData.tool : [];

  return (
    <BaseAgentSpanVisualizer agentData={agentDataForBase} tools={tools} agentType="CrewAI agent">
      {crewaiAgentData.goal && (
        <CollapsibleSection title="Goal" defaultExpanded={true}>
          <OutputViewer outputData={crewaiAgentData.goal} />
        </CollapsibleSection>
      )}
      {crewaiAgentData.backstory && (
        <CollapsibleSection title="Backstory" defaultExpanded={true}>
          <OutputViewer outputData={crewaiAgentData.backstory} />
        </CollapsibleSection>
      )}
    </BaseAgentSpanVisualizer>
  );
};

export default CrewAIAgentSpanVisualizer;
