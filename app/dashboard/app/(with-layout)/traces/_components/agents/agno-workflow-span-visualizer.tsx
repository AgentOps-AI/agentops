import React from 'react';
import { Container } from '@/components/ui/container';
import { Card, CardContent } from '@/components/ui/card';
import CollapsibleSection, { OutputViewer } from '../crewai/collapsible-section';
import { getIconForModel } from '@/lib/modelUtils';

interface AgnoWorkflowSpanVisualizerProps {
    spanAttributes: any;
}

// Component to render team members
const TeamMembersList = ({ members }: { members: any[] }) => {
    if (!members || members.length === 0) return null;

    return (
        <div className="space-y-4">
            {members.map((member: any, index: number) => {
                return (
                    <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                        <h4 className="font-semibold text-sm mb-2">
                            {member.name || `Member ${index + 1}`}
                        </h4>
                        {member.role && (
                            <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)] mb-2">
                                <span className="font-semibold">Role:</span> {member.role}
                            </p>
                        )}
                        {member.model && (
                            <div className="flex items-center gap-2 text-xs text-[rgba(20,27,52,0.5)] dark:text-[rgba(225,226,242,0.5)]">
                                <span className="flex items-center justify-center [&>svg]:h-4 [&>svg]:w-4">
                                    {getIconForModel(member.model)}
                                </span>
                                <span>
                                    <span className="font-semibold">Model:</span> {member.model}
                                </span>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

const AgnoWorkflowSpanVisualizer = ({ spanAttributes }: AgnoWorkflowSpanVisualizerProps) => {
    // Agno workflow data is stored in span_attributes.team
    const teamData = spanAttributes?.team;
    const workflowData = spanAttributes?.workflow;

    // Check if this is truly an Agno workflow
    const isTrulyAgnoWorkflow = !!(
        spanAttributes?.gen_ai?.system === 'agno' &&
        spanAttributes?.agentops?.span?.kind === 'workflow' &&
        teamData
    );

    if (!isTrulyAgnoWorkflow) {
        return (
            <div className="max-w-2xl p-4">
                <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                    Agno workflow data not found or incomplete.
                </p>
            </div>
        );
    }

    const workflowName = teamData.display_name || teamData.name || 'Agno Workflow';
    const members = teamData.member || [];
    const mode = teamData.mode;
    const workflowType = workflowData?.type;

    return (
        <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
            <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                <CardContent className="space-y-3">
                    {/* Workflow Details */}
                    <div className="mb-3">
                        <h3 className="text-lg font-semibold mb-2">{workflowName}</h3>
                        <div className="space-y-1 text-sm">
                            {mode && (
                                <div>
                                    <span className="font-semibold">Mode:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {mode}
                                    </span>
                                </div>
                            )}
                            {workflowType && (
                                <div>
                                    <span className="font-semibold">Type:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {workflowType}
                                    </span>
                                </div>
                            )}
                            {teamData.members_count && (
                                <div>
                                    <span className="font-semibold">Team Size:</span>{' '}
                                    <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                        {teamData.members_count} members
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Team Members */}
                    <CollapsibleSection title="Team Members" defaultExpanded={true}>
                        <TeamMembersList members={members} />
                    </CollapsibleSection>

                    {/* Additional Configuration */}
                    {(teamData.streaming !== undefined || teamData.stream_intermediate_steps !== undefined) && (
                        <CollapsibleSection title="Configuration" defaultExpanded={false}>
                            <div className="space-y-2 text-sm">
                                {teamData.streaming !== undefined && (
                                    <div>
                                        <span className="font-semibold">Streaming:</span>{' '}
                                        <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                            {teamData.streaming}
                                        </span>
                                    </div>
                                )}
                                {teamData.stream_intermediate_steps !== undefined && (
                                    <div>
                                        <span className="font-semibold">Stream Intermediate Steps:</span>{' '}
                                        <span className="text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                                            {teamData.stream_intermediate_steps}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </CollapsibleSection>
                    )}
                </CardContent>
            </Card>
        </Container>
    );
};

export default AgnoWorkflowSpanVisualizer; 