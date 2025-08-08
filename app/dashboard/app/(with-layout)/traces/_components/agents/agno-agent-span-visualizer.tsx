import BaseAgentSpanVisualizer from './base-agent-span-visualizer';
import CollapsibleSection, { OutputViewer } from '../crewai/collapsible-section';
import React from 'react';
import { getIconForModel } from '@/lib/modelUtils';

interface AgnoAgentVisualizerProps {
    spanAttributes: any;
}

const AgnoAgentSpanVisualizer = ({ spanAttributes }: AgnoAgentVisualizerProps) => {
    const agentData = spanAttributes?.agent;
    const genAiData = spanAttributes?.gen_ai;

    if (!agentData) {
        return (
            <div className="max-w-2xl p-4">
                <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                    No Agno agent data available.
                </p>
            </div>
        );
    }

    // Get model info
    const modelInfo = genAiData?.request?.model || genAiData?.response?.model || null;
    const modelIcon = modelInfo ? getIconForModel(modelInfo) : null;

    // Create agent data for the base visualizer
    const agentDataForBase = {
        name: agentData.model_provider ? `${agentData.model_provider} Agent` : 'Agno Agent',
    };

    // Agno doesn't seem to have tools in the example, but we'll check for them
    // Ensure tools is always an array
    const tools = Array.isArray(agentData.tools) ? agentData.tools : [];

    return (
        <BaseAgentSpanVisualizer agentData={agentDataForBase} tools={tools} agentType="Agno agent">
            {/* Model Information with Icon */}
            {modelInfo && (
                <div className="mb-3 flex items-center gap-2 text-sm">
                    <span className="flex items-center justify-center [&>svg]:h-5 [&>svg]:w-5">
                        {modelIcon}
                    </span>
                    <span className="font-semibold">Model:</span>
                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                        {modelInfo}
                    </span>
                </div>
            )}
            {/* Input */}
            {agentData.input && (
                <CollapsibleSection title="Input" defaultExpanded={true}>
                    <OutputViewer outputData={agentData.input} />
                </CollapsibleSection>
            )}

            {/* Output */}
            {agentData.output && (
                <CollapsibleSection title="Output" defaultExpanded={true}>
                    <OutputViewer outputData={agentData.output} />
                </CollapsibleSection>
            )}

            {/* Additional Metadata */}
            {(agentData.reasoning !== undefined ||
                agentData.markdown !== undefined ||
                agentData.show_tool_calls !== undefined) && (
                    <CollapsibleSection title="Configuration" defaultExpanded={false}>
                        <div className="space-y-2 text-sm">
                            {agentData.reasoning !== undefined && (
                                <div>
                                    <span className="font-semibold">Reasoning:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {agentData.reasoning}
                                    </span>
                                </div>
                            )}
                            {agentData.markdown !== undefined && (
                                <div>
                                    <span className="font-semibold">Markdown:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {agentData.markdown}
                                    </span>
                                </div>
                            )}
                            {agentData.show_tool_calls !== undefined && (
                                <div>
                                    <span className="font-semibold">Show Tool Calls:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {agentData.show_tool_calls}
                                    </span>
                                </div>
                            )}
                        </div>
                    </CollapsibleSection>
                )}

            {/* Session and Run IDs */}
            {(agentData.session_id || agentData.run_id || agentData.id) && (
                <CollapsibleSection title="Identifiers" defaultExpanded={false}>
                    <div className="space-y-2 text-sm">
                        {agentData.id && (
                            <div>
                                <span className="font-semibold">Agent ID:</span>{' '}
                                <span className="font-mono text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                    {agentData.id}
                                </span>
                            </div>
                        )}
                        {agentData.session_id && (
                            <div>
                                <span className="font-semibold">Session ID:</span>{' '}
                                <span className="font-mono text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                    {agentData.session_id}
                                </span>
                            </div>
                        )}
                        {agentData.run_id && (
                            <div>
                                <span className="font-semibold">Run ID:</span>{' '}
                                <span className="font-mono text-xs text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                    {agentData.run_id}
                                </span>
                            </div>
                        )}
                    </div>
                </CollapsibleSection>
            )}
        </BaseAgentSpanVisualizer>
    );
};

export default AgnoAgentSpanVisualizer; 