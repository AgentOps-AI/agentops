'use client';

import { useState, useEffect, useMemo, Fragment } from 'react';
import { useTraceDetail } from '@/hooks/queries/useTraceDetail';
import { useTraceStats } from './use-trace-stats';
import { Button } from '@/components/ui/button';
import { ITrace } from '@/types/ITrace';
import { ISpan } from '@/types/ISpan';
import { Tags } from '@/components/ui/tags';
import Logo from '@/components/icons/Logo';
import { TraceMetaData } from './trace-meta-data';
import { cn, formatTime } from '@/lib/utils';
import { SessionReplay } from './session-replay';
import { GraphView } from './graph-view';
import Tab from './tab';
import { ProjectMetrics } from '@/lib/interfaces';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LogTraceViewer } from './log-trace-viewer';
import { ChevronDown } from 'lucide-react';
import { buildSpansTree } from '@/components/spans-list';
import { convertToObject } from './span-attribute-viewer';
import { AgentsViewer } from './agents-viewer';
import { TasksViewer } from './tasks-viewer';
import { TraceLogsViewer } from './trace-logs-viewer';
import { getIconForModel } from '@/lib/modelUtils';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2 } from 'lucide-react';
import { BaseDrilldownDrawer } from './base-drilldown-drawer';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import Link from 'next/link';
import { LockIcon } from 'hugeicons-react';
import { toast } from '@/components/ui/use-toast';
import { downloadTraceAsJson, copyTraceJsonToClipboard } from './trace-export';
import { InstrumentationWarning } from './instrumentation-warning';
import { useBookmarks } from '@/hooks/useBookmarks';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

type SessionTabTypes =
  | 'session-replay'
  | 'tree-view'
  | 'graph-view'
  | 'agents'
  | 'agents-overview'
  | 'system'
  | 'terminal-output'
  | 'metrics'
  | 'logs'
  | 'tasks';

const DIRECT_PROVIDERS = [
  'openai',
  'anthropic',
  'cohere',
  'mistralai',
  'gemini',
  'xai',
  'ollama',
  'groq',
];

const determineIconName = (
  actualModelName?: string | null,
  systemName?: string | null,
): string | undefined => {
  const an = actualModelName?.trim() || undefined;
  const sn = systemName?.trim() || undefined;

  if (sn && an) {
    if (
      DIRECT_PROVIDERS.includes(sn.toLowerCase()) ||
      an.toLowerCase().startsWith(sn.toLowerCase())
    ) {
      return sn;
    }
    return an;
  }
  return an || sn;
};

interface TraceDrilldownDrawerProps {
  id: string | null;
  trace: ITrace | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose?: () => void;
  metrics?: ProjectMetrics | undefined;
}

// Helper to check if spans contain Crew or OpenAI agents (TODO: include more)
const hasAgents = (spans: ISpan[]): boolean => {
  return spans.some(
    (span) =>
      (span.span_name?.endsWith('.agent') && span.span_attributes?.agent?.id) ||
      (span.span_type === 'agent' && span.span_attributes?.agent?.name) ||
      span.span_attributes?.crewai?.agents,
  );
};

// Helper to check if spans contain CrewAI tasks
const hasCrewAITasks = (spans: ISpan[]): boolean => {
  return spans.some((span) => span.span_attributes?.crewai?.task);
};

export const TraceDrilldownDrawer = ({
  trace,
  id,
  open,
  onOpenChange,
  onClose,
  metrics,
}: TraceDrilldownDrawerProps) => {
  const {
    traceDetail,
    isLoading: isSpansLoading,
    error: fetchError,
    refetch,
    failureCount,
    isError,
  } = useTraceDetail(id);
  const [selectedSpan, setSelectedSpan] = useState<ISpan | null>(null);
  const spans = useMemo(() => traceDetail?.spans ?? [], [traceDetail]);
  const [activeTab, setActiveTab] = useState<SessionTabTypes>(() => {
    // Initialize from localStorage, defaulting to 'session-replay' (Waterfall View) if not found
    if (typeof window !== 'undefined') {
      const savedView = localStorage.getItem('traceViewPreference');
      if (
        savedView === 'tree-view' ||
        savedView === 'session-replay' ||
        savedView === 'graph-view'
      ) {
        return savedView as SessionTabTypes;
      }
    }
    return 'session-replay';
  });
  const { permissions: orgPermissions } = useOrgFeatures();
  const { isBookmarked, toggleBookmark } = useBookmarks();

  // Use trace start time from either the trace prop or the fetched trace detail
  const traceStartTime = trace?.start_time || traceDetail?.timestamp;
  // Calculate trace start time in milliseconds, using the earliest span time as fallback
  const traceStartTimeMs = useMemo(() => {
    if (traceStartTime) {
      return new Date(traceStartTime).getTime();
    }
    // If we don't have a trace start time but have spans, use the earliest span start time
    if (spans.length > 0) {
      const earliestSpan = spans.reduce((earliest, span) => {
        const spanStartMs = new Date(span.start_time).getTime();
        const earliestStartMs = new Date(earliest.start_time).getTime();
        return spanStartMs < earliestStartMs ? span : earliest;
      });
      return new Date(earliestSpan.start_time).getTime();
    }
    return Date.now(); // Last resort fallback
  }, [traceStartTime, spans]);

  const { totalCostAcrossSpans, tokenStats, llmCount, toolCount } = useTraceStats(spans);

  // Check if this trace has only a single session span (indicates poor instrumentation)
  const shouldShowInstrumentationWarning = useMemo(() => {
    return spans.length === 1 && spans[0]?.span_name?.endsWith('.session');
  }, [spans]);

  // Use trace metadata from either source, preferring the trace prop if available
  const isTraceRestricted = trace?.freeplan_truncated || false;
  const traceId = trace?.trace_id || id || '';
  const traceEndTime = trace?.end_time || null;
  const traceSpanCount = trace?.span_count;

  // Calculate duration from spans if not available from trace
  const calculatedDuration = useMemo(() => {
    if (trace?.duration) {
      return trace.duration;
    }
    if (spans.length > 0) {
      // Calculate duration from the spans
      const earliestStart = Math.min(...spans.map((s) => new Date(s.start_time).getTime()));
      const latestEnd = Math.max(...spans.map((s) => new Date(s.end_time).getTime()));
      return (latestEnd - earliestStart) * 1000000; // Convert to nanoseconds
    }
    return 0;
  }, [trace?.duration, spans]);

  // Only show initial loading if we're actually fetching data for the first time
  const isInitialLoad = id && isSpansLoading && !traceDetail && failureCount === 0;

  useEffect(() => {
    if (!open || !id) {
      setSelectedSpan(null);
    }
  }, [open, id]);

  const errorContent = (
    <div className="px-4 py-8 text-center ">
      <p className="mb-2 text-sm font-medium text-red-500">
        {isError && failureCount > 0
          ? `Sorry, we couldn't find the trace after ${failureCount} attempts. It might still be processing or there was an issue.`
          : fetchError?.message || 'An unknown error occurred'}
      </p>
      <br />
      <div className="flex items-center justify-center gap-2">
        {!isError && failureCount > 0 && (
          <Button variant="outline" onClick={() => refetch()}>
            Try Again
          </Button>
        )}
        <Button
          variant="outline"
          onClick={() => {
            onOpenChange(false);
            onClose?.();
          }}
        >
          {isError && failureCount > 0 ? 'Back to Traces' : 'Go back to traces'}
        </Button>
      </div>
    </div>
  );

  const handleTabChange = (tab: SessionTabTypes) => {
    setActiveTab(tab);
    // Persist the view preference to localStorage
    if (
      typeof window !== 'undefined' &&
      (tab === 'session-replay' || tab === 'tree-view' || tab === 'graph-view')
    ) {
      localStorage.setItem('traceViewPreference', tab);
    }
  };

  const isLlmSpan = !!selectedSpan?.span_attributes?.gen_ai;
  const prompts = selectedSpan?.span_attributes?.gen_ai?.prompt;
  const processedCompletions = useMemo(() => {
    if (!selectedSpan || !isLlmSpan) return [];

    const genAi = selectedSpan.span_attributes?.gen_ai;
    if (!genAi?.completion) return [];

    try {
      const completionData = genAi.completion;
      let rawCompletions: any[];
      if (typeof completionData === 'string') {
        const parsed = convertToObject(completionData);
        rawCompletions = Array.isArray(parsed) ? parsed : [parsed];
      } else {
        rawCompletions = Array.isArray(completionData) ? completionData : [completionData];
      }

      return rawCompletions
        .map((item) => {
          if (!item || typeof item !== 'object') return null;
          const key = Object.keys(item)[0];
          return key ? item[key] : null;
        })
        .filter(Boolean);
    } catch (error) {
      console.error('[Drawer] Error processing completion data:', error);
      return [];
    }
  }, [selectedSpan, isLlmSpan, prompts]);

  const rootSpan = useMemo(() => {
    if (!spans || spans.length === 0) return null;
    try {
      const tree = buildSpansTree(spans);
      return tree?.[0]?.originalSpan ?? null;
    } catch (error) {
      console.error('[Drawer] Error building spans tree:', error);
      return null;
    }
  }, [spans]);

  // Extract unique models from all spans - memoized for performance
  const uniqueModels = useMemo(() => {
    if (!spans || spans.length === 0) return [];

    const modelInfos = spans
      .map((span) => {
        const genAi = span.span_attributes?.gen_ai;
        const agentModel = span.span_attributes?.agent?.model;

        // Handle ADK agent models
        if (!genAi && agentModel) {
          return {
            displayName: agentModel.trim(),
            iconName: agentModel.trim(),
          };
        }

        if (!genAi) return null;

        const responseModel = genAi.response?.model;
        const requestModel = genAi.request?.model;
        const systemNameAttr = genAi.system;

        const actualModelName = responseModel || requestModel;
        const resolvedDisplayName = (actualModelName || systemNameAttr)?.trim();

        if (!resolvedDisplayName) return null;

        const iconName = determineIconName(actualModelName, systemNameAttr) || resolvedDisplayName;

        return {
          displayName: resolvedDisplayName,
          iconName: iconName,
        };
      })
      .filter((info): info is { displayName: string; iconName: string } => info !== null);

    const uniqueModelMap = modelInfos.reduce((acc, modelInfo) => {
      if (!acc.has(modelInfo.displayName)) {
        acc.set(modelInfo.displayName, modelInfo);
      }
      return acc;
    }, new Map<string, { displayName: string; iconName: string }>());

    return Array.from(uniqueModelMap.values());
  }, [spans]);

  const renderMetadata = () => {
    // If we don't have a proper trace object but have traceDetail, create a synthetic trace for metadata display
    const displayTrace =
      trace && trace.start_time
        ? trace
        : traceDetail
          ? ({
              trace_id: traceId,
              root_span_name: rootSpan?.name || 'Unknown',
              root_service_name: rootSpan?.service_name || 'Unknown',
              start_time: traceDetail.timestamp,
              end_time: traceDetail.timestamp, // Use start time as fallback
              duration: calculatedDuration,
              span_count: spans.length,
              error_count: spans.filter((s) => s.status_code === 'ERROR').length,
              tags: [],
              freeplan_truncated: false,
            } as ITrace)
          : null;

    if (!displayTrace) {
      return (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      );
    }
    return (
      <TraceMetaData
        selectedTrace={displayTrace}
        metrics={metrics}
        rootSpan={rootSpan}
        selectedSpan={selectedSpan}
      />
    );
  };
  const divider = <div className="h-6 border-l border-gray-300 dark:border-gray-600"></div>;

  const stickySectionContent = (
    <>
      {/* Header */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pb-4 text-sm">
        {/* AgentOps Logo and Version - only show when version is available */}
        {spans && spans.length > 0 && spans[0]?.span_attributes?.instrumentation?.version && (
          <div className={cn('flex items-center gap-1 font-medium text-primary')}>
            <Logo className="h-5 w-5" />
            <span>v{spans[0].span_attributes.instrumentation.version}</span>
          </div>
        )}

        {/* Display all unique models from LLM spans - optimized with useMemo */}
        {uniqueModels && uniqueModels.length > 0 && (
          <>
            {uniqueModels.map(({ displayName, iconName }, idx) => (
              <Fragment key={`model-${idx}`}>
                <div className={cn('flex items-center gap-1 font-medium text-primary')}>
                  <span className="h-5 w-5">{getIconForModel(iconName || displayName)}</span>
                  {displayName}
                </div>
              </Fragment>
            ))}
            {divider}
          </>
        )}

        <div className="flex items-center gap-3 rounded-md bg-[#E1E3F2] px-3 py-1 dark:bg-gray-800">
          {calculatedDuration > 0 && (
            <div className={cn('flex gap-2 font-medium text-secondary dark:text-white')}>
              Duration:
              <span className="text-primary">{formatTime(calculatedDuration / 1000000)}</span>
            </div>
          )}

          {(totalCostAcrossSpans.hasAnyCost || totalCostAcrossSpans.hasCostCalculationIssues) && (
            <>
              <div className="h-4 border-l border-gray-300 dark:border-gray-600"></div>
              <div className="flex items-center gap-2 font-medium text-secondary dark:text-white">
                Total Cost:
                {totalCostAcrossSpans.hasAnyCost ? (
                  <span className="text-primary">{totalCostAcrossSpans.formattedTotalCost}</span>
                ) : (
                  <>
                    <span className="text-primary">N/A</span>
                    <TooltipProvider>
                      <Tooltip delayDuration={0}>
                        <TooltipTrigger asChild>
                          <div
                            className="flex h-4 w-4 flex-shrink-0 cursor-help items-center justify-center rounded-full border border-yellow-500 text-xs font-bold text-yellow-500"
                            aria-label="Cost calculation warning"
                          >
                            ?
                          </div>
                        </TooltipTrigger>
                        <TooltipContent
                          className="w-80 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md"
                          side="bottom"
                          sideOffset={8}
                        >
                          <div className="space-y-2">
                            <p className="font-medium">Unable to calculate cost</p>
                            <p>
                            This might be because you're using an unrecognized model.
                            </p>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </>
                )}
              </div>
            </>
          )}
        </div>

        <div className="h-6 border-l border-gray-300 dark:border-gray-600"></div>
        <div className="flex gap-2 font-medium text-secondary dark:text-white">
          LLM Calls:
          <span className="text-primary">{llmCount.toLocaleString()}</span>
        </div>
        <div className="flex gap-2 font-medium text-secondary dark:text-white">
          Tool Calls:
          <span className="text-primary">{toolCount.toLocaleString()}</span>
        </div>
        {(trace?.error_count !== undefined || traceDetail) && (
          <div className="flex gap-2 font-medium text-secondary dark:text-white">
            Errors:
            <span className={cn('text-primary', (trace?.error_count || 0) > 0 && 'text-red-500')}>
              {(trace?.error_count ?? 0).toLocaleString()}
            </span>
          </div>
        )}
        {tokenStats.hasAnyTokens && (
          <div className="flex gap-2 font-medium text-secondary dark:text-white">
            Total Tokens:
            <span className="text-primary">{tokenStats.totalTokens.toLocaleString()}</span>
          </div>
        )}

        {/* Tags section */}
        {trace?.tags && trace.tags.length > 0 && <Tags tags={trace.tags} />}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 px-6 dark:border-gray-700">
        <div className="-ml-4 flex">
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  'relative flex items-center gap-1 px-4 py-1.5 font-medium',
                  activeTab === 'session-replay' ||
                    activeTab === 'tree-view' ||
                    activeTab === 'graph-view'
                    ? 'text-primary'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                )}
              >
                {activeTab === 'session-replay'
                  ? 'Waterfall View'
                  : activeTab === 'tree-view'
                    ? 'Tree View'
                    : activeTab === 'graph-view'
                      ? 'Graph View'
                      : 'Waterfall View'}
                <ChevronDown className="h-4 w-4" />
                {(activeTab === 'session-replay' ||
                  activeTab === 'tree-view' ||
                  activeTab === 'graph-view') && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-black shadow-[0_1px_3px_rgba(0,0,0,0.3)] dark:bg-white/80 dark:shadow-[0_1px_3px_rgba(255,255,255,0.2)]"></div>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-44"
              onPointerDownOutside={(e) => e.stopPropagation()}
            >
              <DropdownMenuItem
                onClick={() => handleTabChange('session-replay')}
                className={cn(activeTab === 'session-replay' && 'bg-[#E1E3F2] dark:bg-slate-700')}
              >
                Waterfall View
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleTabChange('tree-view')}
                className={cn(activeTab === 'tree-view' && 'bg-[#E1E3F2] dark:bg-slate-700')}
              >
                Tree View
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleTabChange('graph-view')}
                className={cn(activeTab === 'graph-view' && 'bg-[#E1E3F2] dark:bg-slate-700')}
              >
                Graph View
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {spans.length > 0 && hasAgents(spans) && (
            <Tab
              label="Agents"
              isActive={activeTab === 'agents'}
              onClick={() => handleTabChange('agents')}
            />
          )}
          {spans.length > 0 && hasCrewAITasks(spans) && (
            <Tab
              label="Tasks and Outputs"
              isActive={activeTab === 'tasks'}
              onClick={() => handleTabChange('tasks')}
            />
          )}
          <Tab
            label="Terminal Logs"
            isActive={activeTab === 'logs'}
            onClick={() => handleTabChange('logs')}
          />
        </div>
      </div>
    </>
  );

  return (
    <BaseDrilldownDrawer
      open={open}
      onOpenChange={onOpenChange}
      onClose={onClose}
      id={id ?? 'no-trace'}
      isRefreshing={isSpansLoading}
      onRefresh={refetch}
      onExport={() => {
        if (id && spans.length > 0) {
          // Create a synthetic trace if we only have a placeholder
          const exportTrace =
            trace && trace.start_time
              ? trace
              : ({
                  trace_id: traceId,
                  root_span_name: rootSpan?.name || 'Unknown',
                  root_service_name: rootSpan?.service_name || 'Unknown',
                  start_time: traceDetail?.timestamp || new Date().toISOString(),
                  end_time: traceDetail?.timestamp || new Date().toISOString(),
                  duration: calculatedDuration,
                  span_count: spans.length,
                  error_count: spans.filter((s) => s.status_code === 'ERROR').length,
                  tags: [],
                  freeplan_truncated: false,
                } as ITrace);
          downloadTraceAsJson(id, exportTrace, spans);
        } else {
          toast({
            title: 'No data to export',
            description: 'Trace data is not available for export.',
            variant: 'destructive',
          });
        }
      }}
      onCopyJson={() => {
        // Create a synthetic trace if we only have a placeholder
        const exportTrace =
          trace && trace.start_time
            ? trace
            : ({
                trace_id: traceId,
                root_span_name: rootSpan?.name || 'Unknown',
                root_service_name: rootSpan?.service_name || 'Unknown',
                start_time: traceDetail?.timestamp || new Date().toISOString(),
                end_time: traceDetail?.timestamp || new Date().toISOString(),
                duration: calculatedDuration,
                span_count: spans.length,
                error_count: spans.filter((s) => s.status_code === 'ERROR').length,
                tags: [],
                freeplan_truncated: false,
              } as ITrace);
        copyTraceJsonToClipboard(exportTrace, spans);
      }}
      stickyContent={
        !fetchError && !isError && !isSpansLoading && !isInitialLoad && spans && spans.length > 0
          ? stickySectionContent
          : undefined
      }
      firstSpan={spans.length > 0 ? spans[0] : undefined}
      isBookmarked={id ? isBookmarked(id) : false}
      onToggleBookmark={id ? () => toggleBookmark(id) : undefined}
    >
      {(isSpansLoading || isInitialLoad) && failureCount === 0 && (
        <div className="flex h-full items-center justify-center text-center">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="ml-2">Loading trace details...</p>
        </div>
      )}
      {(isSpansLoading || isInitialLoad) && failureCount > 0 && (
        <div className="flex h-full items-center justify-center text-center">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="ml-2">Still looking for the trace... Attempt {failureCount} of 5.</p>
        </div>
      )}
      {!isSpansLoading && !isInitialLoad && (isError || fetchError) ? (
        errorContent
      ) : !isSpansLoading && !isInitialLoad && !fetchError && !isError ? (
        <>
          <div className="relative flex h-full flex-col p-4">
            {isTraceRestricted && orgPermissions?.tierName === 'free' && (
              <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/10 backdrop-blur-md">
                <div className="max-w-md rounded-lg bg-white p-8 text-center shadow-2xl dark:bg-gray-800">
                  <LockIcon className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                  <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
                    Trace Data Restricted
                  </h3>
                  <p className="mb-6 text-gray-600 dark:text-gray-300">
                    This trace is older than your plan&apos;s data retention limit. Upgrade to Pro
                    to access historical trace data without restrictions.
                  </p>
                  <Button
                    asChild
                    className="relative w-full overflow-hidden border border-[#DEE0F4] bg-gradient-to-r from-[#DEE0F4] to-[#A3A8C9] text-[#141B34] hover:from-[#BFC4E0] hover:to-[#7B81A6] dark:border-[#A3A8C9] dark:text-[#23263A]"
                  >
                    <Link
                      href="/settings/organization"
                      className="relative z-0 flex h-full items-center justify-center"
                    >
                      <style jsx>{`
                        @keyframes shine {
                          0% {
                            left: -60%;
                            opacity: 0.2;
                          }
                          20% {
                            opacity: 0.6;
                          }
                          50% {
                            left: 100%;
                            opacity: 0.6;
                          }
                          80% {
                            opacity: 0.2;
                          }
                          100% {
                            left: 100%;
                            opacity: 0;
                          }
                        }
                        .animate-shine {
                          position: absolute;
                          top: 0;
                          left: -60%;
                          width: 60%;
                          height: 100%;
                          background: linear-gradient(90deg, transparent, #bfc4e0 60%, transparent);
                          opacity: 0.7;
                          border-radius: 0.375rem;
                          animation: shine 2.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
                          pointer-events: none;
                        }
                      `}</style>
                      Upgrade to Pro
                      <div className="animate-shine" />
                    </Link>
                  </Button>
                  <Button
                    variant="ghost"
                    className="mt-2 w-full"
                    onClick={() => {
                      onOpenChange(false);
                      onClose?.();
                    }}
                  >
                    Back to Traces
                  </Button>
                </div>
              </div>
            )}

            <div className="flex-1 overflow-hidden">
              {activeTab === 'session-replay' && (
                <div className="h-full overflow-hidden">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <SessionReplay
                    spans={spans}
                    selectedSpan={selectedSpan}
                    setSelectedSpan={setSelectedSpan}
                    traceStartTimeMs={traceStartTimeMs}
                    renderMetadata={renderMetadata}
                    processedCompletions={processedCompletions}
                    isLlmSpan={isLlmSpan}
                    prompts={prompts}
                  />
                </div>
              )}

              {activeTab === 'tree-view' && (
                <div className="h-full overflow-hidden">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <LogTraceViewer
                    spans={spans}
                    traceStartTimeMs={traceStartTimeMs}
                    selectedSpan={selectedSpan}
                    setSelectedSpan={setSelectedSpan}
                    renderMetadata={renderMetadata}
                    processedCompletions={processedCompletions}
                    isLlmSpan={isLlmSpan}
                    prompts={prompts}
                  />
                </div>
              )}

              {activeTab === 'graph-view' && (
                <div className="h-full overflow-hidden">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <GraphView
                    spans={spans}
                    selectedSpan={selectedSpan}
                    setSelectedSpan={setSelectedSpan}
                    traceStartTimeMs={traceStartTimeMs}
                    renderMetadata={renderMetadata}
                    processedCompletions={processedCompletions}
                    isLlmSpan={isLlmSpan}
                    prompts={prompts}
                  />
                </div>
              )}

              {activeTab === 'agents' && (
                <div className="h-full w-full overflow-y-auto">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <div className="p-4">
                    <AgentsViewer spans={spans} />
                  </div>
                </div>
              )}
              {activeTab === 'tasks' && (
                <div className="h-full w-full overflow-y-auto">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <div className="p-4">
                    <TasksViewer spans={spans} />
                  </div>
                </div>
              )}
              {activeTab === 'logs' && (
                <div className="h-full" data-testid="trace-detail-logs-view">
                  {shouldShowInstrumentationWarning && <InstrumentationWarning />}
                  <TraceLogsViewer traceId={id} />
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </BaseDrilldownDrawer>
  );
};
