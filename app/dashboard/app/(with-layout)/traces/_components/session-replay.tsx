import { SpansGanttChart } from '@/components/charts/bar-chart/spans-gantt-chart';
import CustomTabs from '@/components/ui/custom-tabs';
import { isEmpty } from 'lodash';
import { SpanPretty } from './span-pretty';
import { LlmSpanRaw } from './llm-span-raw';
import CrewAITaskVisualizer from './crewai/crew-ai-task-span-visualizer';
import CrewAIAgentSpanVisualizer from './crewai/crew-ai-agent-span-visualizer';
import ADKAgentSpanVisualizer from './agents/adk-agent-span-visualizer';
import ADKWorkflowSpanVisualizer from './agents/adk-workflow-span-visualizer';
import CrewAIWorkflowSpanVisualizer from './crewai/crew-ai-workflow-span-visualizer';
import AgnoAgentSpanVisualizer from './agents/agno-agent-span-visualizer';
import AgnoWorkflowSpanVisualizer from './agents/agno-workflow-span-visualizer';
import AG2AgentSpanVisualizer from './agents/ag2-agent-span-visualizer';
import { ISpan } from '@/types/ISpan';
import { UnifiedToolSpanViewer } from './event-visualizers/tool-span';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import Link from 'next/link';
import { useMemo } from 'react';
import { InformationCircleIcon as InfoIcon } from 'hugeicons-react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

interface SessionReplayProps {
  spans: ISpan[];
  selectedSpan: ISpan | null;
  setSelectedSpan: (span: ISpan | null) => void;
  traceStartTimeMs: number;
  renderMetadata: () => React.ReactNode;
  processedCompletions: any[];
  isLlmSpan: boolean;
  prompts: any;
}

export const SessionReplay = ({
  spans,
  selectedSpan,
  setSelectedSpan,
  traceStartTimeMs,
  renderMetadata,
  processedCompletions,
  isLlmSpan,
  prompts,
}: SessionReplayProps) => {
  const { permissions: orgPermissions, isLoading: isPermissionsLoading } = useOrgFeatures();

  const spanWaterfallLimit = orgPermissions?.dataAccess?.spanWaterfallLimit;
  const isSpanLimitedForFreePlan = useMemo(() => {
    if (isPermissionsLoading || !orgPermissions) return false;
    return (
      orgPermissions.tierName === 'free' &&
      typeof spanWaterfallLimit === 'number' &&
      spans.length > spanWaterfallLimit
    );
  }, [spans.length, spanWaterfallLimit, orgPermissions, isPermissionsLoading]);

  const isCrewAISpan = !!selectedSpan?.span_attributes?.crewai;
  const isADKAgentSpan = !!(
    selectedSpan?.span_attributes?.adk &&
    selectedSpan?.span_attributes?.agent &&
    selectedSpan?.span_type === 'agent'
  );
  const isADKWorkflowSpan = !!(
    selectedSpan?.span_attributes?.adk &&
    selectedSpan?.span_attributes?.agent &&
    selectedSpan?.span_attributes?.agent?.sub_agents &&
    selectedSpan?.span_attributes?.agent?.sub_agents.length > 0
  );
  const isAgnoAgentSpan = !!(
    selectedSpan?.span_attributes?.agent &&
    selectedSpan?.span_attributes?.gen_ai?.system === 'agno' &&
    selectedSpan?.span_type === 'agent'
  );
  const isAgnoWorkflowSpan = !!(
    selectedSpan?.span_attributes?.team &&
    selectedSpan?.span_attributes?.gen_ai?.system === 'agno' &&
    selectedSpan?.span_attributes?.agentops?.span?.kind === 'workflow'
  );
  const isAG2AgentSpan = !!(
    selectedSpan?.span_name?.startsWith('ag2.agent.') &&
    selectedSpan?.span_attributes?.agentops?.span?.kind === 'agent'
  );
  const isCrewAIWorkflowSpan = !!(
    selectedSpan?.span_attributes?.crewai &&
    (selectedSpan?.span_attributes?.crewai?.crew ||
      (selectedSpan?.span_attributes?.crewai?.agents && selectedSpan?.span_attributes?.crewai?.agents.length > 0))
  );
  const hasCompletionsToShow = processedCompletions.length > 0;
  const shouldShowCrewAITaskTab = isCrewAISpan && !!selectedSpan?.span_attributes?.crewai?.task && !isCrewAIWorkflowSpan;
  const shouldShowCrewAIAgentTab = isCrewAISpan && !!selectedSpan?.span_attributes?.crewai?.agent && !isCrewAIWorkflowSpan;
  const shouldShowADKAgentTab = isADKAgentSpan && !isADKWorkflowSpan; // Only show agent tab if not a workflow
  const shouldShowAgnoAgentTab = isAgnoAgentSpan;
  const shouldShowAG2AgentTab = isAG2AgentSpan;
  const shouldShowADKWorkflowTab = isADKWorkflowSpan;
  const shouldShowAgnoWorkflowTab = isAgnoWorkflowSpan;
  const shouldShowCrewAIWorkflowTab = isCrewAIWorkflowSpan;
  const shouldShowAgentView = shouldShowCrewAIAgentTab || shouldShowADKAgentTab || shouldShowAgnoAgentTab || shouldShowAG2AgentTab;
  const shouldShowWorkflowView = shouldShowADKWorkflowTab || shouldShowAgnoWorkflowTab || shouldShowCrewAIWorkflowTab;
  const shouldShowCrewAIToolTab = !!selectedSpan?.span_attributes?.tool;
  const isGenericToolSpan = !!(
    selectedSpan?.span_attributes?.agentops?.span?.kind === 'tool' ||
    (selectedSpan?.span_type === 'tool' && !isCrewAISpan) ||
    (selectedSpan?.span_name?.endsWith('.tool') &&
      selectedSpan?.span_attributes?.agentops?.entity?.input &&
      selectedSpan?.span_attributes?.operation?.name) ||
    selectedSpan?.span_name?.startsWith('ag2.tool.')
  );
  // Don't show separate Tool View tab for ADK agents, workflows, Agno agents, or Agno workflows (tools are shown within their respective views)
  const shouldShowToolTab =
    (shouldShowCrewAIToolTab || (isGenericToolSpan && !shouldShowCrewAITaskTab)) &&
    !isADKAgentSpan &&
    !isADKWorkflowSpan &&
    !isAgnoAgentSpan &&
    !isAgnoWorkflowSpan;

  return (
    <ResizablePanelGroup direction="horizontal" className="flex h-full w-full gap-4">
      <ResizablePanel defaultSize={1} minSize={20} className="relative overflow-hidden">
        <div className="h-full" data-testid="trace-detail-span-list">
          <SpansGanttChart
            data={spans}
            traceStartTimeMs={traceStartTimeMs}
            selectedSpanId={selectedSpan?.span_id || null}
            onSpanSelect={setSelectedSpan}
            withScrollArea={false}
          />
          {isSpanLimitedForFreePlan && typeof spanWaterfallLimit === 'number' && (
            <div className="absolute bottom-2 left-2 right-2 flex items-start gap-2 rounded-md border border-blue-300 bg-blue-50/95 p-2 text-xs text-blue-700 backdrop-blur-sm">
              <InfoIcon className="h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-medium">Waterfall view limited</p>
                <p>
                  Showing first {spanWaterfallLimit} of {spans.length} spans.{' '}
                  <Link
                    href="/settings/billing"
                    className="font-semibold underline hover:text-blue-800"
                  >
                    Upgrade to see all spans
                  </Link>
                </p>
              </div>
            </div>
          )}
        </div>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={1} minSize={20} className="flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {!selectedSpan ? (
            <div
              className="flex h-full items-center justify-center rounded-md border border-dashed text-gray-500 dark:border-slate-700"
              data-testid="trace-detail-select-span-prompt"
            >
              Select a span in the waterfall chart to view details.
            </div>
          ) : (
            <>
              <div
                className="flex h-full w-full flex-col gap-4 p-4"
                id="trace-details-container"
                data-testid="trace-detail-span-content"
              >
                <div id="trace-meta-data" className="w-full" data-testid="trace-detail-metadata">
                  {renderMetadata()}
                </div>
                <CustomTabs
                  generalTabsContainerClassNames="h-full w-full"
                  tabs={[
                    ...((isLlmSpan && hasCompletionsToShow) || !isEmpty(prompts)
                      ? [
                        {
                          value: 'span-pretty',
                          label: 'Prettify',
                          content: (
                            <div id="trace-span-pretty" className=" w-full">
                              <SpanPretty selectedSpan={selectedSpan} />
                            </div>
                          ),
                        },
                      ]
                      : []),
                    ...(shouldShowCrewAITaskTab
                      ? [
                        {
                          value: 'crew-ai-task-visualizer',
                          label: 'Task View',
                          content: (
                            <div id="trace-crew-ai-task-visualizer" className="h-[450px] w-full">
                              <CrewAITaskVisualizer
                                spanAttributes={selectedSpan.span_attributes}
                              />
                            </div>
                          ),
                        },
                      ]
                      : []),
                    ...(shouldShowAgentView
                      ? [
                        {
                          value: 'agent-visualizer',
                          label: 'Agent View',
                          content: (
                            <div id="trace-agent-visualizer" className="h-[450px] w-full">
                              {shouldShowCrewAIAgentTab && (
                                <CrewAIAgentSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                              {shouldShowADKAgentTab && (
                                <ADKAgentSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                              {shouldShowAgnoAgentTab && (
                                <AgnoAgentSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                              {shouldShowAG2AgentTab && (
                                <AG2AgentSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                            </div>
                          ),
                        },
                      ]
                      : []),
                    ...(shouldShowWorkflowView
                      ? [
                        {
                          value: 'workflow-visualizer',
                          label: 'Workflow View',
                          content: (
                            <div id="trace-workflow-visualizer" className="h-[450px] w-full">
                              {shouldShowADKWorkflowTab && (
                                <ADKWorkflowSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                              {shouldShowAgnoWorkflowTab && (
                                <AgnoWorkflowSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                              {shouldShowCrewAIWorkflowTab && (
                                <CrewAIWorkflowSpanVisualizer
                                  spanAttributes={selectedSpan.span_attributes}
                                />
                              )}
                            </div>
                          ),
                        },
                      ]
                      : []),
                    ...(shouldShowToolTab
                      ? [
                        {
                          value: 'tool-visualizer',
                          label: 'Tool View',
                          content: (
                            <div id="trace-tool-visualizer" className="h-[450px] w-full">
                              <UnifiedToolSpanViewer toolSpan={selectedSpan} />
                            </div>
                          ),
                        },
                      ]
                      : []),
                    {
                      value: 'llm-span-raw',
                      label: 'Raw JSON',
                      'data-testid': 'trace-detail-tabs-button-raw-json',
                      content: (
                        <div id="trace-llm-span-raw" className="h-[450px] w-full">
                          <LlmSpanRaw selectedSpan={selectedSpan} />
                        </div>
                      ),
                    },
                  ]}
                  defaultValue={'llm-span-raw'}
                  activeTabId={
                    (isLlmSpan && hasCompletionsToShow) || !isEmpty(prompts)
                      ? 'span-pretty'
                      : shouldShowCrewAITaskTab
                        ? 'crew-ai-task-visualizer'
                        : shouldShowWorkflowView
                          ? 'workflow-visualizer'
                          : shouldShowAgentView
                            ? 'agent-visualizer'
                            : shouldShowToolTab
                              ? 'tool-visualizer'
                              : 'llm-span-raw'
                  }
                />
              </div>
            </>
          )}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
};
