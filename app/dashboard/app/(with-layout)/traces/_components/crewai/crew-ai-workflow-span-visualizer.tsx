import React from 'react';
import { Container } from '@/components/ui/container';
import { Card, CardContent } from '@/components/ui/card';
import CollapsibleSection, { OutputViewer } from './collapsible-section';
import { getIconForModel } from '@/lib/modelUtils';

interface CrewAIWorkflowSpanVisualizerProps {
    spanAttributes: any;
}

// Component to render agents/tasks in a workflow context
const WorkflowAgentsList = ({ agents }: { agents: any[] }) => {
    if (!agents || !Array.isArray(agents) || agents.length === 0) return null;

    return (
        <div className="space-y-4">
            {agents.map((agentData: any, index: number) => {
                // Access agent properties directly
                const agent = agentData?.agent || agentData;
                const task = agentData?.task;
                const tools = Array.isArray(agentData?.tools) ? agentData.tools :
                    Array.isArray(agent?.tools) ? agent.tools : [];

                return (
                    <div key={index} className="relative">
                        {/* Connection line between steps */}
                        {index < agents.length - 1 && (
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
                            <div className="flex-1 bg-white dark:bg-gray-800/50 border border-[rgba(222,224,244,1)] dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow overflow-hidden">
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-[rgba(139,92,246,0.1)] text-[rgba(139,92,246,1)] dark:bg-[rgba(139,92,246,0.2)]">
                                                {agent?.role || agent?.name || 'Agent'}
                                            </span>
                                            {agent?.llm && (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-[#F7F8FF] dark:bg-gray-700 text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                                    <span className="w-3 h-3">{getIconForModel(agent.llm)}</span>
                                                    {agent.llm}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {agent?.goal && (
                                    <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-3 break-words">
                                        <strong className="font-semibold">Goal:</strong> {agent.goal}
                                    </p>
                                )}

                                {agent?.backstory && (
                                    <details className="group mb-3" open>
                                        <summary className="cursor-pointer text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] hover:text-[rgba(20,27,52,1)] dark:hover:text-[rgba(225,226,242,1)] transition-colors">
                                            View Backstory
                                        </summary>
                                        <pre className="mt-2 p-3 text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] bg-[#F7F8FF] dark:bg-gray-900/50 rounded-md whitespace-pre-wrap break-words font-mono">
                                            {agent.backstory}
                                        </pre>
                                    </details>
                                )}

                                {task && (
                                    <div className="mt-3 p-3 bg-[rgba(59,130,246,0.05)] dark:bg-[rgba(59,130,246,0.1)] rounded-md border border-[rgba(59,130,246,0.2)] overflow-hidden">
                                        <p className="text-xs font-semibold text-[rgba(59,130,246,1)] mb-1 truncate">
                                            Task: {task.name || 'Unnamed Task'}
                                        </p>
                                        {task.description && (
                                            <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2 break-words">
                                                {task.description}
                                            </p>
                                        )}
                                        {task.expected_output && (
                                            <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] break-words">
                                                <strong>Expected Output:</strong> {task.expected_output}
                                            </p>
                                        )}
                                    </div>
                                )}

                                {Array.isArray(tools) && tools.length > 0 && (
                                    <div className="mt-3 p-3 bg-[rgba(75,196,152,0.05)] dark:bg-[rgba(75,196,152,0.1)] rounded-md border border-[rgba(75,196,152,0.2)] overflow-hidden">
                                        <p className="text-xs font-semibold text-[rgba(75,196,152,1)] mb-1">Tools:</p>
                                        <ul className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] space-y-1">
                                            {tools.map((tool: any, toolIndex: number) => (
                                                <li key={toolIndex} className="truncate">
                                                    • {typeof tool === 'string' ? tool : (tool?.name || tool?.tool_name || 'Unknown Tool')}
                                                    {tool?.description && (
                                                        <span className="text-[rgba(20,27,52,0.5)] dark:text-[rgba(225,226,242,0.5)] break-words">
                                                            {' - '}{tool.description}
                                                        </span>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Recursive rendering for nested agents */}
                                {agent?.agents && Array.isArray(agent.agents) && agent.agents.length > 0 && (
                                    <div className="mt-4 ml-4">
                                        <p className="text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2">
                                            Nested Workflow Steps:
                                        </p>
                                        <WorkflowAgentsList agents={agent.agents} />
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

const CrewAIWorkflowSpanVisualizer = ({ spanAttributes }: CrewAIWorkflowSpanVisualizerProps) => {
    try {
        // CrewAI workflow data is structured with agents at crewai.agents and tasks at crewai.crew.tasks
        const crewaiData = spanAttributes?.crewai;

        // Ensure agents and tasks are arrays
        const agents = Array.isArray(crewaiData?.agents) ? crewaiData.agents : [];
        const crewData = crewaiData?.crew || {};
        const tasks = Array.isArray(crewData?.tasks) ? crewData.tasks : [];

        // Check if this is actually a workflow with agents or tasks
        const isCrewWorkflow = !!(
            crewaiData &&
            (agents.length > 0 || tasks.length > 0)
        );

        if (!isCrewWorkflow) {
            // If no workflow data, show raw JSON
            return (
                <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent max-w-5xl mx-auto">
                    <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                        <CardContent className="space-y-4">
                            <div className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                <p className="mb-2">CrewAI workflow data not found or incomplete. Showing raw data:</p>
                                <CollapsibleSection title="Raw Span Attributes" defaultExpanded={true}>
                                    <div className="max-w-none">
                                        <OutputViewer outputData={spanAttributes} />
                                    </div>
                                </CollapsibleSection>
                            </div>
                        </CardContent>
                    </Card>
                </Container>
            );
        }

        // Extract workflow information
        const cacheEfficiency = crewData.cache_efficiency;
        const tokenEfficiency = crewData.token_efficiency;
        const result = crewData.result;

        // Create a map of agents by ID for easy lookup
        const agentMap = new Map();
        if (Array.isArray(agents)) {
            agents.forEach((agent: any) => {
                if (agent?.id) {
                    agentMap.set(agent.id, agent);
                }
            });
        }

        // Combine agents with their tasks
        let workflowSteps: Array<{
            agent: any;
            task: any;
            tools: any[];
        }> = [];

        if (Array.isArray(tasks) && tasks.length > 0) {
            // If we have tasks, map them to agents
            workflowSteps = tasks.map((task: any) => {
                const agentId = task?.agent_id;
                const agent = agentMap.get(agentId) || (Array.isArray(agents) ? agents.find((a: any) => a?.role === task?.agent) : null);

                return {
                    agent: agent || { role: task?.agent || 'Unknown Agent' },
                    task: task,
                    tools: task?.tools || agent?.tools || []
                };
            });
        } else if (Array.isArray(agents) && agents.length > 0) {
            // If we have agents but no tasks, display agents directly
            workflowSteps = agents.map((agent: any) => ({
                agent: agent,
                task: null,
                tools: agent?.tools || []
            }));
        }

        return (
            <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent max-w-5xl mx-auto">
                <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                    <CardContent className="space-y-4">
                        {/* Workflow metadata */}
                        <div className="flex items-center gap-4 mb-4">
                            {cacheEfficiency && (
                                <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-[rgba(75,196,152,0.1)] text-[rgba(75,196,152,1)]">
                                    Cache Efficiency: {(parseFloat(cacheEfficiency) * 100).toFixed(1)}%
                                </span>
                            )}
                            {tokenEfficiency && (
                                <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-[rgba(59,130,246,0.1)] text-[rgba(59,130,246,1)]">
                                    Token Efficiency: {(parseFloat(tokenEfficiency) * 100).toFixed(1)}%
                                </span>
                            )}
                        </div>

                        {result && (
                            <CollapsibleSection title="Workflow Result" defaultExpanded={false}>
                                <div className="max-w-none">
                                    <OutputViewer outputData={result} />
                                </div>
                            </CollapsibleSection>
                        )}

                        <CollapsibleSection title="Workflow Steps" defaultExpanded={true}>
                            <div className="space-y-4">
                                {workflowSteps.map((step: any, index: number) => {
                                    const { agent, task, tools } = step;

                                    return (
                                        <div key={index} className="relative">
                                            {/* Connection line between steps */}
                                            {index < workflowSteps.length - 1 && (
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
                                                <div className="flex-1 bg-white dark:bg-gray-800/50 border border-[rgba(222,224,244,1)] dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow overflow-hidden">
                                                    <div className="flex items-start justify-between mb-2">
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-[rgba(139,92,246,0.1)] text-[rgba(139,92,246,1)] dark:bg-[rgba(139,92,246,0.2)]">
                                                                    {agent?.role || task?.agent || 'Agent'}
                                                                </span>
                                                                {agent?.llm && (
                                                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-[#F7F8FF] dark:bg-gray-700 text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                                                        <span className="w-3 h-3">{getIconForModel(agent.llm)}</span>
                                                                        {agent.llm}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        {task?.status && (
                                                            <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${task.status === 'completed'
                                                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                                                                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                                                                }`}>
                                                                {task.status}
                                                            </span>
                                                        )}
                                                    </div>

                                                    {agent?.goal && (
                                                        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-3 break-words">
                                                            <strong className="font-semibold">Goal:</strong> {agent.goal}
                                                        </p>
                                                    )}

                                                    {agent?.backstory && (
                                                        <details className="group mb-3">
                                                            <summary className="cursor-pointer text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] hover:text-[rgba(20,27,52,1)] dark:hover:text-[rgba(225,226,242,1)] transition-colors">
                                                                View Backstory
                                                            </summary>
                                                            <div className="mt-2 p-3 text-xs bg-[#F7F8FF] dark:bg-gray-900/50 rounded-md">
                                                                <pre className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] whitespace-pre-wrap break-words font-mono">
                                                                    {agent.backstory}
                                                                </pre>
                                                            </div>
                                                        </details>
                                                    )}

                                                    {task && (
                                                        <div className="mt-3 p-3 bg-[rgba(59,130,246,0.05)] dark:bg-[rgba(59,130,246,0.1)] rounded-md border border-[rgba(59,130,246,0.2)] overflow-hidden">
                                                            <div className="group relative">
                                                                <p className="text-xs font-semibold text-[rgba(59,130,246,1)] mb-1 truncate">
                                                                    Task: {task.summary || 'Task Details'}
                                                                </p>
                                                            </div>
                                                            {task.description && (
                                                                <details className="group mb-2">
                                                                    <summary className="cursor-pointer text-xs font-medium text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                                                        View Description
                                                                    </summary>
                                                                    <p className="mt-1 text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] whitespace-pre-wrap break-words">
                                                                        {task.description}
                                                                    </p>
                                                                </details>
                                                            )}
                                                            {task.expected_output && (
                                                                <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] break-words">
                                                                    <strong>Expected Output:</strong> {task.expected_output}
                                                                </p>
                                                            )}
                                                            {task.raw && (
                                                                <details className="group mt-2">
                                                                    <summary className="cursor-pointer text-xs font-medium text-[rgba(75,196,152,1)]">
                                                                        View Output
                                                                    </summary>
                                                                    <div className="mt-1 p-2 text-xs bg-white dark:bg-gray-900/50 rounded overflow-hidden">
                                                                        <pre className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] whitespace-pre-wrap break-words font-mono max-h-60 overflow-y-auto">
                                                                            {task.raw}
                                                                        </pre>
                                                                    </div>
                                                                </details>
                                                            )}
                                                        </div>
                                                    )}

                                                    {Array.isArray(tools) && tools.length > 0 && (
                                                        <div className="mt-3">
                                                            <p className="text-xs font-semibold text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2">
                                                                Tools ({tools.length})
                                                            </p>
                                                            <div className="space-y-2">
                                                                {tools.map((tool: any, toolIndex: number) => {
                                                                    // Parse tool description which contains name, arguments, and description
                                                                    let toolArguments = '';
                                                                    let toolDescription = '';
                                                                    let hasParsedFormat = false;

                                                                    if (tool.description) {
                                                                        const argsMatch = tool.description.match(/Tool Arguments:\s*({[\s\S]*?})\s*Tool Description:/);
                                                                        const descMatch = tool.description.match(/Tool Description:\s*(.+)$/m);

                                                                        if (argsMatch) {
                                                                            toolArguments = argsMatch[1];
                                                                            hasParsedFormat = true;
                                                                            // Try to format JSON for better readability
                                                                            try {
                                                                                const parsed = JSON.parse(toolArguments.replace(/'/g, '"'));
                                                                                toolArguments = JSON.stringify(parsed, null, 2);
                                                                            } catch (e) {
                                                                                // Keep original if parsing fails
                                                                            }
                                                                        }
                                                                        if (descMatch) {
                                                                            toolDescription = descMatch[1];
                                                                            hasParsedFormat = true;
                                                                        }
                                                                    }

                                                                    return (
                                                                        <div key={toolIndex} className="p-3 bg-[rgba(75,196,152,0.05)] dark:bg-[rgba(75,196,152,0.1)] rounded-md border border-[rgba(75,196,152,0.2)] overflow-hidden">
                                                                            <div className="flex items-center gap-2 mb-2">
                                                                                <svg className="w-3 h-3 text-[rgba(75,196,152,1)] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                                                </svg>
                                                                                <p className="text-xs font-semibold text-[rgba(75,196,152,1)] truncate">
                                                                                    {tool.name || 'Unknown Tool'}
                                                                                </p>
                                                                            </div>

                                                                            {toolArguments && (
                                                                                <div className="mb-2">
                                                                                    <p className="text-xs font-medium text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-1">
                                                                                        Arguments:
                                                                                    </p>
                                                                                    <pre className="text-xs bg-gray-100 dark:bg-gray-900/50 rounded p-2 overflow-x-auto">
                                                                                        <code className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                                                                            {toolArguments}
                                                                                        </code>
                                                                                    </pre>
                                                                                </div>
                                                                            )}

                                                                            {toolDescription && (
                                                                                <div>
                                                                                    <p className="text-xs font-medium text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-1">
                                                                                        Description:
                                                                                    </p>
                                                                                    <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] break-words">
                                                                                        {toolDescription}
                                                                                    </p>
                                                                                </div>
                                                                            )}

                                                                            {/* Fallback for tools that don't follow the expected format */}
                                                                            {(!hasParsedFormat && tool.description) && (
                                                                                <p className="text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] break-words">
                                                                                    {tool.description}
                                                                                </p>
                                                                            )}
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Agent settings */}
                                                    {(agent?.max_iter || agent?.allow_delegation !== undefined || agent?.verbose !== undefined) && (
                                                        <div className="mt-2 flex flex-wrap gap-2">
                                                            {agent.max_iter && (
                                                                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                                                                    Max Iterations: {agent.max_iter}
                                                                </span>
                                                            )}
                                                            {agent.allow_delegation !== undefined && (
                                                                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                                                                    Delegation: {agent.allow_delegation}
                                                                </span>
                                                            )}
                                                            {agent.verbose !== undefined && (
                                                                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                                                                    Verbose: {agent.verbose}
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </CollapsibleSection>
                    </CardContent>
                </Card>
            </Container>
        );
    } catch (error) {
        console.error("Error rendering CrewAIWorkflowSpanVisualizer:", error);
        return (
            <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent max-w-5xl mx-auto">
                <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                    <CardContent className="space-y-4">
                        <div className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                            <p className="mb-2">Error rendering CrewAI workflow visualization:</p>
                            <p>{error instanceof Error ? error.message : String(error)}</p>
                            <p>Showing raw span attributes for debugging:</p>
                            <CollapsibleSection title="Raw Span Attributes" defaultExpanded={true}>
                                <div className="max-w-none">
                                    <OutputViewer outputData={spanAttributes} />
                                </div>
                            </CollapsibleSection>
                        </div>
                    </CardContent>
                </Card>
            </Container>
        );
    }
};

export default CrewAIWorkflowSpanVisualizer; 