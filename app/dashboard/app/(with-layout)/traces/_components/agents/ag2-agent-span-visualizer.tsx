import BaseAgentSpanVisualizer from '../agents/base-agent-span-visualizer';
import CollapsibleSection, { OutputViewer } from '../crewai/collapsible-section';
import React from 'react';

interface AG2AgentVisualizerProps {
  spanAttributes: any;
}

const AG2AgentSpanVisualizer = ({ spanAttributes }: AG2AgentVisualizerProps) => {
  // Extract AG2 agent data from span attributes
  const agentName = spanAttributes?.agent?.name;
  const agentSender = spanAttributes?.agent?.sender;
  const agentInput = spanAttributes?.agentops?.entity?.input;

  if (!agentName && !agentInput) {
    return (
      <div className="max-w-2xl p-4">
        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
          No AG2 agent data available.
        </p>
      </div>
    );
  }

  const agentDataForBase = {
    name: agentName || 'AG2 Agent',
  };

  // AG2 agents don't have tools in the same way as other frameworks
  const tools: any[] = [];

  return (
    <BaseAgentSpanVisualizer agentData={agentDataForBase} tools={tools} agentType="AG2 agent">
      {agentSender && (
        <CollapsibleSection title="Sender" defaultExpanded={true}>
          <OutputViewer outputData={agentSender} />
        </CollapsibleSection>
      )}
      {agentInput && (
        <CollapsibleSection title="Input" defaultExpanded={true}>
          <OutputViewer outputData={agentInput} />
        </CollapsibleSection>
      )}
    </BaseAgentSpanVisualizer>
  );
};

export default AG2AgentSpanVisualizer;