'use client';

import React, { useMemo, useState } from 'react';
import { ISpan } from '@/types/ISpan';
import { cn, formatTime } from '@/lib/utils';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getSpanDisplayInfo } from '@/utils/span-display.utils';
import { spanTypeColors } from '@/app/lib/span-colors';
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
import { UnifiedToolSpanViewer } from './event-visualizers/tool-span';
import CustomTabs from '@/components/ui/custom-tabs';
import { isEmpty } from 'lodash';
import { getIconForModel } from '@/lib/modelUtils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ChartCard } from '@/components/ui/chart-card';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

interface SpanNode {
  span: ISpan;
  children: SpanNode[];
  level: number;
}

interface LogTraceViewerProps {
  spans: ISpan[];
  traceStartTimeMs: number;
  selectedSpan: ISpan | null;
  setSelectedSpan: (span: ISpan | null) => void;
  renderMetadata: () => React.ReactNode;
  processedCompletions: any[];
  isLlmSpan: boolean;
  prompts: any;
}

// Build a tree structure from flat spans using parent_span_id
const buildSpanTree = (spans: ISpan[]): SpanNode[] => {
  const spanMap = new Map<string, SpanNode>();
  const rootNodes: SpanNode[] = [];

  // First pass: create nodes for all spans
  spans.forEach((span) => {
    spanMap.set(span.span_id, {
      span,
      children: [],
      level: 0,
    });
  });

  // Second pass: build the tree structure
  spans.forEach((span) => {
    const node = spanMap.get(span.span_id);
    if (!node) return;

    if (span.parent_span_id && spanMap.has(span.parent_span_id)) {
      const parentNode = spanMap.get(span.parent_span_id);
      if (parentNode) {
        parentNode.children.push(node);
        node.level = parentNode.level + 1;
      }
    } else {
      // No parent or parent not found - this is a root node
      rootNodes.push(node);
    }
  });

  // Sort children by start_time
  const sortChildren = (nodes: SpanNode[]) => {
    nodes.sort((a, b) => {
      const aTime = new Date(a.span.start_time).getTime();
      const bTime = new Date(b.span.start_time).getTime();
      return aTime - bTime;
    });
    nodes.forEach((node) => sortChildren(node.children));
  };

  sortChildren(rootNodes);

  return rootNodes;
};

const SpanTreeNode: React.FC<{
  node: SpanNode;
  traceStartTimeMs: number;
  expandedSpans: Set<string>;
  toggleExpanded: (spanId: string) => void;
  selectedSpanId: string | null;
  onSpanSelect: (span: ISpan) => void;
}> = ({ node, traceStartTimeMs, expandedSpans, toggleExpanded, selectedSpanId, onSpanSelect }) => {
  const { span, children, level } = node;
  const hasChildren = children.length > 0;
  const isExpanded = expandedSpans.has(span.span_id);

  const startTimeMs = new Date(span.start_time).getTime();
  const relativeStartMs = startTimeMs - traceStartTimeMs;
  const durationMs = span.duration / 1000000; // Convert nanoseconds to milliseconds

  const { displayName, spanType, shortType } = getSpanDisplayInfo(span);
  const hasError = span.status_code === 'ERROR';

  // Get colors from the shared color map
  const typeColors = hasError
    ? spanTypeColors.error
    : spanTypeColors[spanType as keyof typeof spanTypeColors] || spanTypeColors.default;

  // Get model name for LLM spans
  const modelName =
    spanType === 'llm'
      ? span.span_attributes?.gen_ai?.response?.model ||
      span.span_attributes?.gen_ai?.request?.model ||
      span.span_attributes?.gen_ai?.system ||
      null
      : null;

  return (
    <div className="font-mono text-xs">
      <div
        className={cn(
          'flex cursor-pointer items-center gap-1 rounded px-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-800',
          hasError && 'text-red-600 dark:text-red-400',
          selectedSpanId === span.span_id && 'bg-gray-100 dark:bg-gray-700',
        )}
        style={{ paddingLeft: `${level * 24 + 8}px` }}
        onClick={() => onSpanSelect(span)}
      >
        <span className="w-14 text-right text-gray-500 dark:text-gray-400">
          {formatTime(relativeStartMs)}
        </span>

        {hasChildren && (
          <Button
            variant="ghost"
            size="sm"
            className="h-4 w-4 p-0"
            onClick={(e) => {
              e.stopPropagation();
              toggleExpanded(span.span_id);
            }}
          >
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </Button>
        )}

        {spanType === 'llm' && modelName ? (
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <span
                className="relative rounded px-2 py-0.5 text-xs font-medium text-white"
                style={{
                  backgroundColor: typeColors.bg,
                  border: `1px solid ${typeColors.border}`,
                  boxShadow:
                    selectedSpanId === span.span_id
                      ? `0 0 0 2px ${typeColors.selectedBorder}`
                      : undefined,
                  filter: 'drop-shadow(2px 2px 2px rgba(0,0,0,0.3))',
                }}
              >
                {shortType}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <div className="flex items-center gap-2">
                <span className="flex items-center justify-center [&>svg]:h-4 [&>svg]:w-4">
                  {getIconForModel(modelName)}
                </span>
                <p>{modelName}</p>
              </div>
            </TooltipContent>
          </Tooltip>
        ) : (
          <span
            className="relative rounded px-2 py-0.5 text-xs font-medium text-white"
            style={{
              backgroundColor: typeColors.bg,
              border: `1px solid ${typeColors.border}`,
              boxShadow:
                selectedSpanId === span.span_id
                  ? `0 0 0 2px ${typeColors.selectedBorder}`
                  : undefined,
              filter: 'drop-shadow(2px 2px 2px rgba(0,0,0,0.3))',
            }}
          >
            {shortType}
          </span>
        )}

        <span className={cn('ml-1 flex-1 truncate', hasError && 'font-semibold')}>
          {displayName}
        </span>

        <span className="w-12 text-right text-gray-500 dark:text-gray-400">
          {formatTime(durationMs)}
        </span>
      </div>

      {isExpanded && children.length > 0 && (
        <div>
          {children.map((childNode) => (
            <SpanTreeNode
              key={childNode.span.span_id}
              node={childNode}
              traceStartTimeMs={traceStartTimeMs}
              expandedSpans={expandedSpans}
              toggleExpanded={toggleExpanded}
              selectedSpanId={selectedSpanId}
              onSpanSelect={onSpanSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const LogTraceViewer: React.FC<LogTraceViewerProps> = ({
  spans,
  traceStartTimeMs,
  selectedSpan,
  setSelectedSpan,
  renderMetadata,
  processedCompletions,
  isLlmSpan,
  prompts,
}) => {
  // Initialize with all spans expanded by default
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(
    new Set(spans.map((span) => span.span_id)),
  );

  const spanTree = useMemo(() => buildSpanTree(spans), [spans]);

  const toggleExpanded = (spanId: string) => {
    setExpandedSpans((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(spanId)) {
        newSet.delete(spanId);
      } else {
        newSet.add(spanId);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    const allSpanIds = spans.map((span) => span.span_id);
    setExpandedSpans(new Set(allSpanIds));
  };

  const collapseAll = () => {
    setExpandedSpans(new Set());
  };

  // Check for special span types
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
    <TooltipProvider>
      <ResizablePanelGroup direction="horizontal" className="flex h-full w-full gap-4">
        <ResizablePanel defaultSize={50} minSize={20} className="relative overflow-hidden">
          <div className={'relative h-full overflow-hidden'} data-testid="trace-detail-log-tree">
            <ChartCard
              containerStyles="relative z-[1] h-full flex flex-col"
              cardStyles="shadow-xl sm:p-0 flex flex-col h-full overflow-hidden"
              cardHeaderStyles="mb-0 p-2 pb-0 pt-0"
              cardContentStyles="h-full overflow-hidden p-0"
            >
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-700">
                  <h3 className="text-sm font-medium">Trace Tree View</h3>
                  <div className="flex gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 shadow-md dark:border-slate-700 dark:bg-slate-800 dark:shadow-slate-900/50">
                    <button
                      onClick={expandAll}
                      className="rounded px-2 py-0.5 text-xs font-medium text-slate-900 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
                    >
                      Expand All
                    </button>
                    <div className="w-px bg-slate-200 dark:bg-slate-600" />
                    <button
                      onClick={collapseAll}
                      className="rounded px-2 py-0.5 text-xs font-medium text-slate-900 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
                    >
                      Collapse All
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  {spanTree.length === 0 ? (
                    <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                      No spans to display
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {spanTree.map((node) => (
                        <SpanTreeNode
                          key={node.span.span_id}
                          node={node}
                          traceStartTimeMs={traceStartTimeMs}
                          expandedSpans={expandedSpans}
                          toggleExpanded={toggleExpanded}
                          selectedSpanId={selectedSpan?.span_id || null}
                          onSpanSelect={setSelectedSpan}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </ChartCard>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {!selectedSpan ? (
              <div
                className="flex h-full items-center justify-center rounded-md border border-dashed text-gray-500 dark:border-slate-700"
                data-testid="trace-detail-select-span-prompt"
              >
                Select a span in the tree to view details.
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
                              <div
                                id="trace-crew-ai-task-visualizer"
                                className="h-[450px] w-full"
                              >
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
    </TooltipProvider>
  );
};
