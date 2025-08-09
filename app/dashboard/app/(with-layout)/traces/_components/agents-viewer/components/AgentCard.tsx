import { getIconForModel } from '@/lib/modelUtils';
import { Card, CardContent } from '@/components/ui/card';
import { UserIcon, Wrench01Icon, ArrowMoveUpRightIcon } from 'hugeicons-react';
import { AgentCardProps } from '../types';
import { TextSection } from './TextSection';

export const AgentCard = ({ agent }: AgentCardProps) => {
    const PrettyView = () => (
        <div className="space-y-4">
            <div className="space-y-3 text-sm">
                {agent.model && (
                    <p className="flex items-center gap-2">
                        <span className="font-bold">Model:</span>
                        <span className="flex items-center gap-1">
                            <span className="h-4 w-4">{getIconForModel(agent.model)}</span>
                            {agent.model}
                        </span>
                    </p>
                )}
                {/* Common fields across agent types */}
                {agent.input && <TextSection title="Input" content={agent.input} />}

                {agent.output && <TextSection title="Output" content={agent.output} />}

                {agent.backstory && <TextSection title="Backstory" content={agent.backstory} />}

                {agent.goal && <TextSection title="Goal" content={agent.goal} />}

                {agent.description && <TextSection title="Description" content={agent.description} />}

                {agent.instruction && <TextSection title="Instructions" content={agent.instruction} />}

                {agent.handoffs && agent.handoffs.length > 0 && (
                    <div className="mt-4 pt-2">
                        <div className="flex items-center gap-2">
                            <ArrowMoveUpRightIcon
                                className="h-4 w-4"
                                style={{ color: 'rgba(20, 27, 52, 0.68)' }}
                            />
                            <span className="font-bold">Handoffs:</span>
                        </div>
                        <div className="mt-1 pl-6">
                            <ul className="list-disc space-y-1">
                                {agent.handoffs.map((handoff: string, index: number) => (
                                    <li key={index}>{handoff}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}

                <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                        <div className="mt-1 space-y-1">

                            {/* Agno configuration */}
                            {agent.type === 'agno' && (agent.reasoning !== undefined || agent.markdown !== undefined || agent.showToolCalls !== undefined) && (
                                <div className="rounded-md border p-3" style={{ borderColor: 'rgba(222, 224, 244, 1)' }}>
                                    <span className="font-bold">Configuration</span>
                                    <div className="mt-2 space-y-1">
                                        {agent.reasoning !== undefined && (
                                            <p className="text-xs">
                                                <span className="font-semibold">Reasoning:</span> {String(agent.reasoning)}
                                            </p>
                                        )}
                                        {agent.markdown !== undefined && (
                                            <p className="text-xs">
                                                <span className="font-semibold">Markdown:</span> {String(agent.markdown)}
                                            </p>
                                        )}
                                        {agent.showToolCalls !== undefined && (
                                            <p className="text-xs">
                                                <span className="font-semibold">Show Tool Calls:</span> {String(agent.showToolCalls)}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {agent.tools && agent.tools.length > 0 && (
                                <div className="mt-4 pt-4">
                                    <div className="flex items-center gap-2">
                                        <Wrench01Icon className="h-4 w-4" />
                                        <span className="font-bold">Tools:</span>
                                    </div>
                                    <div className="mt-2 space-y-3">
                                        {agent.tools.map((tool: any, index: number) => {
                                            // Handle string tools (OpenAI format)
                                            if (typeof tool === 'string') {
                                                return (
                                                    <div
                                                        key={index}
                                                        className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                        style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <span>{tool}</span>
                                                        </div>
                                                    </div>
                                                );
                                            }

                                            // Handle ADK tools (simple objects with name and description)
                                            if (agent.type === 'adk' && tool.name) {
                                                return (
                                                    <div
                                                        key={index}
                                                        className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                        style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-bold">Name: </span>
                                                            <span>{tool.name}</span>
                                                        </div>
                                                        {tool.description && (
                                                            <div
                                                                className="mt-2 border-t pt-2"
                                                                style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                            >
                                                                <span className="font-bold">Description: </span>
                                                                <span className="text-xs">{tool.description}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            }

                                            // Handle Agno tools (objects with name and description)
                                            if (agent.type === 'agno' && tool.name) {
                                                return (
                                                    <div
                                                        key={index}
                                                        className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                        style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-bold">Name: </span>
                                                            <span>{tool.name}</span>
                                                        </div>
                                                        {tool.description && (
                                                            <div
                                                                className="mt-2 border-t pt-2"
                                                                style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                            >
                                                                <span className="font-bold">Description: </span>
                                                                <span className="text-xs">{tool.description}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            }

                                            // Object tools (CrewAI format)
                                            if (agent.type === 'crewai') {
                                                // Check if tool is already a simple object with name/description
                                                if (tool.name || tool.description) {
                                                    return (
                                                        <div
                                                            key={index}
                                                            className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                            style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                        >
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-bold">Name: </span>
                                                                <span>{tool.name || 'Unnamed Tool'}</span>
                                                            </div>
                                                            {tool.description && (
                                                                <div
                                                                    className="mt-2 border-t pt-2"
                                                                    style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                                >
                                                                    <span className="font-bold">Description: </span>
                                                                    <span className="text-xs">{tool.description}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                }

                                                // Handle nested tool structure
                                                const toolKey = Object.keys(tool)[0];
                                                const toolObj = tool[toolKey];

                                                // If the tool value is just a string, treat it as the tool name or description
                                                if (typeof toolObj === 'string') {
                                                    // If the key is 'description', use the value as the name
                                                    const displayName = toolKey === 'description' ? toolObj : toolKey;
                                                    return (
                                                        <div
                                                            key={index}
                                                            className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                            style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                        >
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-bold">Name: </span>
                                                                <span>{displayName}</span>
                                                            </div>
                                                            {toolKey === 'description' && (
                                                                <div
                                                                    className="mt-2 border-t pt-2"
                                                                    style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                                >
                                                                    <span className="font-bold">Description: </span>
                                                                    <span className="text-xs">{toolObj}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                }

                                                return (
                                                    <div
                                                        key={index}
                                                        className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                        style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-bold">Name: </span>
                                                            <span>{toolObj?.name || toolKey || 'Unnamed Tool'}</span>
                                                        </div>
                                                        {toolObj?.description && (
                                                            <div
                                                                className="mt-2 border-t pt-2"
                                                                style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                            >
                                                                <span className="font-bold">Description: </span>
                                                                <span className="text-xs">{toolObj.description}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            }

                                            // Fallback for other tool formats
                                            return (
                                                <div
                                                    key={index}
                                                    className="mb-3 rounded-md border p-3 shadow-sm dark:bg-gray-800"
                                                    style={{ borderColor: 'rgba(222, 224, 244, 1)' }}
                                                >
                                                    <pre className="overflow-auto text-xs">
                                                        {JSON.stringify(tool, null, 2)}
                                                    </pre>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="mb-4 rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
            <Card className="rounded-xl border-white bg-transparent px-3 shadow-xl transition-all duration-300">
                <CardContent className="p-4">
                    <div className="mb-4 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <UserIcon className="h-5 w-5" />
                            <h3 className="text-lg font-bold">{agent.role}</h3>
                        </div>
                    </div>
                    <div className="mb-4 border-b" style={{ borderColor: 'rgba(222, 224, 244, 1)' }}></div>
                    <PrettyView />
                </CardContent>
            </Card>
        </div>
    );
}; 