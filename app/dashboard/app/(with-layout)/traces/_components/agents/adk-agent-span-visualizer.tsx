import BaseAgentSpanVisualizer, { AgentData, Tool } from './base-agent-span-visualizer';
import CollapsibleSection, { OutputViewer } from '../crewai/collapsible-section'; // For OutputViewer and CollapsibleSection
import React from 'react';

interface ADKAgentSpanVisualizerProps {
  spanAttributes: any; // Replace 'any' with a more specific type if ADK span attributes are known
}

// Component to render subagents
const SubagentsList = ({ subagents }: { subagents: any[] }) => {
  if (!subagents || subagents.length === 0) return null;

  return (
    <div className="space-y-4">
      {subagents.map((subagentWrapper: any, index: number) => {
        const key = Object.keys(subagentWrapper)[0];
        const subagentData = subagentWrapper[key];
        const agent = subagentData.agent;
        const tool = subagentData.tool;

        return (
          <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h4 className="font-semibold text-sm mb-2">
              {agent?.name || `Subagent ${key}`}
            </h4>
            {agent?.description && (
              <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2">
                {agent.description}
              </p>
            )}
            {agent?.model && (
              <p className="text-xs text-[rgba(20,27,52,0.5)] dark:text-[rgba(225,226,242,0.5)] mb-2">
                Model: {agent.model}
              </p>
            )}
            {agent?.instruction && (
              <div className="mb-2">
                <p className="text-xs font-semibold mb-1">Instructions:</p>
                <pre className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] whitespace-pre-wrap">
                  {agent.instruction}
                </pre>
              </div>
            )}
            {tool && (
              <div className="mt-2">
                <p className="text-xs font-semibold mb-1">Tool:</p>
                <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                  {tool.name} - {tool.description}
                </p>
              </div>
            )}
            {agent?.sub_agents && agent.sub_agents.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold mb-2">Nested Subagents:</p>
                <SubagentsList subagents={agent.sub_agents} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

const ADKAgentSpanVisualizer = ({ spanAttributes }: ADKAgentSpanVisualizerProps) => {
  // ADK agent data is directly under spanAttributes.agent
  const adkAgentData = spanAttributes?.agent;
  // Check for the 'adk' object to ensure it's an ADK span, along with agent data
  const isTrulyADKAgent = !!(spanAttributes?.adk && adkAgentData);

  if (!isTrulyADKAgent) {
    return (
      <div className="max-w-2xl p-4">
        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
          ADK agent data not found or incomplete in the expected structure.
        </p>
      </div>
    );
  }

  const agentDataForBase: AgentData = {
    name: adkAgentData.name || adkAgentData.id || 'ADK Agent',
  };

  // Extract ADK-specific data
  const description = adkAgentData.description;
  const instruction = adkAgentData.instruction;
  const subagents = adkAgentData.sub_agents || [];

  // Tools can be in spanAttributes.tool (singular) or adkAgentData.tools
  const tools: Tool[] = [];
  if (spanAttributes.tool) {
    // Single tool case - wrap it in an object as expected by ToolItem
    tools.push({ tool: spanAttributes.tool });
  } else if (adkAgentData.tools) {
    // Multiple tools case
    const toolsArray = Array.isArray(adkAgentData.tools) ? adkAgentData.tools : [adkAgentData.tools];
    toolsArray.forEach((tool: any) => {
      // If tool is already wrapped, use as is, otherwise wrap it
      if (tool && typeof tool === 'object' && Object.keys(tool).length === 1) {
        tools.push(tool);
      } else {
        tools.push({ tool });
      }
    });
  }

  return (
    <BaseAgentSpanVisualizer
      agentData={agentDataForBase}
      tools={tools}
      agentType="ADK agent"
    >
      {/* ADK specific sections */}
      {description && (
        <CollapsibleSection title="Description" defaultExpanded={true}>
          <OutputViewer outputData={description} />
        </CollapsibleSection>
      )}

      {instruction && (
        <CollapsibleSection title="Instructions" defaultExpanded={true}>
          <OutputViewer outputData={instruction} />
        </CollapsibleSection>
      )}

      {subagents && subagents.length > 0 && (
        <CollapsibleSection title="Subagents" defaultExpanded={true}>
          <SubagentsList subagents={subagents} />
        </CollapsibleSection>
      )}
    </BaseAgentSpanVisualizer>
  );
};

export default ADKAgentSpanVisualizer;
