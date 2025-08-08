import { Card, CardContent } from '@/components/ui/card';
import { Container } from '@/components/ui/container';
import CollapsibleSection from '../crewai/collapsible-section';
import { ToolsContainer } from '../crewai/agent-tool-item';
import React from 'react';

export interface AgentData {
  name: string;
  // Other common fields can be added if they become universal
}

export interface Tool {
  // Define a generic tool structure or use 'any' for flexibility
  [key: string]: any;
}

interface BaseAgentSpanVisualizerProps {
  agentData: AgentData | null | undefined;
  tools: Tool[];
  agentType?: string;
  children?: React.ReactNode; // To render agent-specific sections
}

const BaseAgentSpanVisualizer = ({
  agentData,
  tools,
  agentType = 'agent',
  children,
}: BaseAgentSpanVisualizerProps) => {
  if (!agentData) {
    return (
      <div className="max-w-2xl p-4">
        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
          No {agentType} data available.
        </p>
      </div>
    );
  }

  return (
    <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
      <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
        <CardContent className="space-y-3">
          {/* Agent-specific details rendered here */}
          {children}

          {/* Tools */}
          {tools && tools.length > 0 && (
            <CollapsibleSection title="Tools" defaultExpanded={true}>
              <ToolsContainer tools={tools} />
            </CollapsibleSection>
          )}
        </CardContent>
      </Card>
    </Container>
  );
};

export default BaseAgentSpanVisualizer;
