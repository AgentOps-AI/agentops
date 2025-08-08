import React from 'react';
import { Container } from '@/components/ui/container';
import { Card, CardContent } from '@/components/ui/card';
import CollapsibleSection, { OutputViewer } from '../crewai/collapsible-section';
import { getIconForModel } from '@/lib/modelUtils';

interface ADKWorkflowSpanVisualizerProps {
    spanAttributes: any;
}

// Component to render subagents in a workflow context
const WorkflowSubagentsList = ({ subagents }: { subagents: any[] }) => {
    if (!subagents || subagents.length === 0) return null;

    return (
        <div className="space-y-4">
            {subagents.map((subagentData: any, index: number) => {
                // Direct access to agent and tool properties
                const agent = subagentData.agent;
                const tool = subagentData.tool;

                return (
                    <div key={index} className="relative">
                        {/* Connection line between steps */}
                        {index < subagents.length - 1 && (
                            <div className="absolute left-6 top-14 w-0.5 h-[calc(100%-3rem)] bg-[rgba(222,224,244,1)] dark:bg-gray-700" />
                        )}

                        <div className="flex gap-4">
                            {/* Step number circle */}
                            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-[#F7F8FF] dark:bg-gray-800 border-2 border-[rgba(222,224,244,1)] dark:border-gray-700 flex items-center justify-center">
                                <span className="text-sm font-semibold text-[rgba(20,27,52,1)] dark:text-[rgba(225,226,242,1)]">
                                    {index + 1}
                                </span>
                            </div>

                            {/* Step content */}
                            <div className="flex-1 bg-white dark:bg-gray-800/50 border border-[rgba(222,224,244,1)] dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <h4 className="font-semibold text-base text-[rgba(20,27,52,1)] dark:text-[rgba(225,226,242,1)]">
                                            {agent?.name || `Step ${index + 1}`}
                                        </h4>
                                        {agent?.model && (
                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 mt-1 text-xs font-medium rounded-full bg-[#F7F8FF] dark:bg-gray-700 text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                                <span className="w-3 h-3">{getIconForModel(agent.model)}</span>
                                                {agent.model}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {agent?.description && (
                                    <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-3">
                                        {agent.description}
                                    </p>
                                )}

                                {agent?.instruction && (
                                    <details className="group mb-3" open>
                                        <summary className="cursor-pointer text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] hover:text-[rgba(20,27,52,1)] dark:hover:text-[rgba(225,226,242,1)] transition-colors">
                                            View Instructions
                                        </summary>
                                        <pre className="mt-2 p-3 text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] bg-[#F7F8FF] dark:bg-gray-900/50 rounded-md whitespace-pre-wrap font-mono">
                                            {agent.instruction}
                                        </pre>
                                    </details>
                                )}

                                {tool && (
                                    <div className="mt-3 p-3 bg-[rgba(75,196,152,0.05)] dark:bg-[rgba(75,196,152,0.1)] rounded-md border border-[rgba(75,196,152,0.2)]">
                                        <p className="text-xs font-semibold text-[rgba(75,196,152,1)] mb-1">Tool: {tool.name}</p>
                                        <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                            {tool.description}
                                        </p>
                                    </div>
                                )}

                                {agent?.sub_agents && agent.sub_agents.length > 0 && (
                                    <div className="mt-4 ml-4">
                                        <p className="text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2">
                                            Nested Workflow Steps:
                                        </p>
                                        <WorkflowSubagentsList subagents={agent.sub_agents} />
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

const ADKWorkflowSpanVisualizer = ({ spanAttributes }: ADKWorkflowSpanVisualizerProps) => {
    // ADK workflow data is under spanAttributes.agent (workflows are agents with sub_agents)
    const adkWorkflowData = spanAttributes?.agent;
    // Check for the 'adk' object and sub_agents to ensure it's an ADK workflow
    const isTrulyADKWorkflow = !!(
        spanAttributes?.adk &&
        adkWorkflowData &&
        adkWorkflowData.sub_agents &&
        adkWorkflowData.sub_agents.length > 0
    );

    if (!isTrulyADKWorkflow) {
        return (
            <div className="max-w-2xl p-4">
                <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                    ADK workflow data not found or incomplete.
                </p>
            </div>
        );
    }

    const workflowName = adkWorkflowData.name || 'ADK Workflow';
    const description = adkWorkflowData.description;
    const instruction = adkWorkflowData.instruction;
    const subagents = adkWorkflowData.sub_agents || [];

    return (
        <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
            <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                <CardContent className="space-y-4">
                    {description && (
                        <CollapsibleSection title="Description" defaultExpanded={true}>
                            <OutputViewer outputData={description} />
                        </CollapsibleSection>
                    )}

                    {instruction && (
                        <CollapsibleSection title="Workflow Instructions" defaultExpanded={false}>
                            <OutputViewer outputData={instruction} />
                        </CollapsibleSection>
                    )}

                    <CollapsibleSection title="Workflow Steps" defaultExpanded={true}>
                        <WorkflowSubagentsList subagents={subagents} />
                    </CollapsibleSection>
                </CardContent>
            </Card>
        </Container>
    );
};

export default ADKWorkflowSpanVisualizer; 