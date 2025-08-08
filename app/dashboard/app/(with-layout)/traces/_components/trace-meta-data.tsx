import { FormattedTokenDisplay } from '@/components/ui/formatted-token-display';
import { ProjectMetrics } from '@/lib/interfaces';
import { getIconForModel } from '@/lib/modelUtils';
import { formatTime } from '@/lib/utils';
import { IMetrics, ISpan } from '@/types/ISpan';
import { ITrace } from '@/types/ITrace';
import { spanTypeColors } from '@/app/lib/span-colors';
import React from 'react';
import {
  UserIcon,
  CheckmarkSquare01Icon,
  Message01Icon,
  Wrench01Icon,
  Settings01Icon,
  Triangle01Icon,
  WorkflowCircle03Icon,
  CircleIcon,
  CodeIcon,
} from 'hugeicons-react';
import { getSpanDisplayDetails } from '@/app/lib/span-utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { extractAG2ToolName } from '@/utils/ag2.utils';

type TraceMetaDataProps = {
  selectedTrace: ITrace | null;
  selectedSpan: ISpan | null;
  metrics?: ProjectMetrics | undefined;
  rootSpan: ISpan | null;
};

export const TraceMetaData = ({
  selectedTrace,
  metrics,
  rootSpan,
  selectedSpan,
}: TraceMetaDataProps) => {
  // Use direct variable approach for the top panel
  const displaySpan = selectedSpan || rootSpan;
  const initialRawSpanName =
    displaySpan?.span_name || selectedTrace?.root_span_name || 'Trace Details';

  // Use the new utility to get both displayName and eventType
  const { displayName, eventType } = getSpanDisplayDetails(
    initialRawSpanName,
    displaySpan?.span_attributes,
  );

  // For tool spans, prefer the actual tool name from attributes
  let toolName = displaySpan?.span_attributes?.tool?.name ||
    displaySpan?.span_attributes?.tool?.function_name;
  
  // Check for AG2-specific tool name extraction
  const ag2ToolName = extractAG2ToolName(displaySpan);
  if (ag2ToolName) {
    toolName = ag2ToolName;
  }
  
  const finalDisplayName = (eventType === 'tool' || eventType === 'tool_usage') && toolName && toolName !== 'function'
    ? toolName
    : displayName;

  const displayModelName = displaySpan?.span_attributes?.gen_ai?.response?.model ||
    displaySpan?.span_attributes?.gen_ai?.request?.model ||
    displaySpan?.span_attributes?.agent?.model;

  // Extract cost and token data from the selected span if available
  const spanGenAi = displaySpan?.span_attributes?.gen_ai;
  const spanUsage = spanGenAi?.usage || {};

  // Find metrics data from all possible locations in the span
  const metricsData: IMetrics | undefined =
    displaySpan?.metrics || displaySpan?.span_attributes?.metrics;

  // Extract cost values - keep as strings to preserve exact values
  const promptCost = metricsData?.prompt_cost;
  const completionCost = metricsData?.completion_cost;
  const totalCost = metricsData?.total_cost;

  // Check if costs are zero or undefined
  const hasPromptCost = promptCost !== undefined && Number(promptCost) > 0;
  const hasCompletionCost = completionCost !== undefined && Number(completionCost) > 0;
  const hasTotalCost = totalCost !== undefined && Number(totalCost) > 0;
  const hasAnyCost = hasPromptCost || hasCompletionCost || hasTotalCost;

  // Check if this is an LLM span that should have cost but doesn't
  const isLlmSpan = eventType === 'llm' || displaySpan?.span_attributes?.gen_ai;
  const shouldHaveCost = isLlmSpan && displayModelName;
  const hasCostCalculationIssue = shouldHaveCost && !hasAnyCost;

  if (!selectedTrace) {
    return null;
  }

  // Get token info from metrics or fallback
  const displayPromptTokens =
    metricsData?.prompt_tokens !== undefined
      ? Number(metricsData.prompt_tokens)
      : spanUsage.prompt_tokens !== undefined
        ? Number(spanUsage.prompt_tokens)
        : selectedSpan === null ? metrics?.token_metrics?.prompt_tokens : undefined;

  const displayCompletionTokens =
    metricsData?.completion_tokens !== undefined
      ? Number(metricsData.completion_tokens)
      : spanUsage.completion_tokens !== undefined
        ? Number(spanUsage.completion_tokens)
        : selectedSpan === null ? metrics?.token_metrics?.completion_tokens : undefined;

  const displayTotalTokens =
    metricsData?.total_tokens !== undefined
      ? Number(metricsData.total_tokens)
      : displayPromptTokens !== undefined && displayCompletionTokens !== undefined
        ? displayPromptTokens + displayCompletionTokens
        : spanUsage.total_tokens !== undefined
          ? Number(spanUsage.total_tokens)
          : selectedSpan === null ? metrics?.token_metrics?.total_tokens : undefined;

  // Check if tokens are greater than zero
  const hasPromptTokens =
    displayPromptTokens !== undefined &&
    (typeof displayPromptTokens === 'number' ? displayPromptTokens > 0 : true);
  const hasCompletionTokens =
    displayCompletionTokens !== undefined &&
    (typeof displayCompletionTokens === 'number' ? displayCompletionTokens > 0 : true);
  const hasTotalTokens =
    displayTotalTokens !== undefined &&
    (typeof displayTotalTokens === 'number' ? displayTotalTokens > 0 : true);
  const hasAnyTokens = hasPromptTokens || hasCompletionTokens || hasTotalTokens;

  // Format costs - display exact values
  const promptCostFormatted = promptCost !== undefined ? `$${promptCost}` : 'N/A';
  const completionCostFormatted = completionCost !== undefined ? `$${completionCost}` : 'N/A';
  const totalCostFormatted =
    totalCost !== undefined
      ? `$${totalCost}`
      : selectedSpan === null && metrics?.token_metrics?.total_cost
        ? `$${metrics.token_metrics.total_cost}`
        : 'N/A';

  // Use span-specific time and duration when available
  const spanDurationMs = displaySpan?.duration ? displaySpan.duration / 1000000 : undefined;
  const durationFormatted = spanDurationMs
    ? formatTime(spanDurationMs)
    : selectedTrace.duration
      ? formatTime(selectedTrace.duration / 1000000)
      : 'N/A';

  const spanStartTime = displaySpan?.start_time
    ? new Date(displaySpan.start_time).toLocaleTimeString()
    : selectedTrace.start_time
      ? new Date(selectedTrace.start_time).toLocaleTimeString()
      : 'N/A';

  const spanEndTime = displaySpan?.end_time
    ? new Date(displaySpan.end_time).toLocaleTimeString()
    : selectedTrace.end_time
      ? new Date(selectedTrace.end_time).toLocaleTimeString()
      : 'N/A';

  // Render header based on event type
  const renderHeader = () => {
    const type = eventType.toLowerCase();
    // Handle type checking to avoid TypeScript errors
    const colorClass =
      spanTypeColors[type as keyof typeof spanTypeColors]?.text || spanTypeColors.default.text;

    switch (type) {
      case 'agent':
        return (
          <div className="flex items-center gap-2">
              <UserIcon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">Agent:</span> {finalDisplayName}
          </div>
        );
      case 'llm':
        return (
          <div className="flex items-center gap-2">
            <Message01Icon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">LLM:</span> {finalDisplayName}
          </div>
        );
      case 'tool':
      case 'tool_usage':
        return (
          <div className="flex items-center gap-2">
            <Wrench01Icon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">Tool:</span> {finalDisplayName}
          </div>
        );
      case 'operation':
        return (
          <div className="flex items-center gap-2">
            <Settings01Icon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">Operation:</span> {finalDisplayName}
          </div>
        );
      case 'task':
        return (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <CheckmarkSquare01Icon className={`h-5 w-5 ${colorClass}`} />
              <span className="font-bold">Task:</span>
            </div>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2">
            <Triangle01Icon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">Error:</span> {finalDisplayName}
          </div>
        );
      case 'workflow':
        return (
          <div className="flex items-center gap-2">
            <WorkflowCircle03Icon className={`h-5 w-5 ${colorClass}`} />
            <span className="font-bold">Workflow:</span> {finalDisplayName}
          </div>
        );
      case 'session':
        return (
          <div className="flex items-center gap-2">
            <CodeIcon className={`h-5 w-5`} />
            <span className="font-bold">Session:</span> {finalDisplayName}
          </div>
        );
      case 'other':
        return (
          <div className="flex items-center gap-2">
            <CircleIcon className={`h-5 w-5`} />
            <span className="font-bold">Other:</span> {finalDisplayName}
          </div>
        );
      default:
        return finalDisplayName;
    }
  };

  return (
    <div className="flex h-full flex-col text-base text-black dark:text-white">
      <div className="flex-shrink-0 border-b border-gray-200 pb-2 dark:border-slate-700">
        <div
          className="mb-2 text-xl font-semibold text-black dark:text-white"
          data-testid="trace-header-name"
        >
          {renderHeader()}
        </div>

        <div className="grid grid-cols-[1.25fr_1fr_1fr] gap-4">
          {/* Column 1: Basic Info */}
          <div className="flex flex-col gap-1 overflow-hidden">
            <div className="text-sm whitespace-nowrap" data-testid="trace-header-timestamp">
              <span className="font-semibold">Time:</span> {spanStartTime} - {spanEndTime}
            </div>
            <div className="text-sm" data-testid="trace-header-duration">
              <span className="font-semibold">Duration:</span> {durationFormatted}
            </div>

            {displayModelName && (
              <div className="flex items-center gap-1 overflow-hidden text-ellipsis text-sm">
                <span className="font-semibold">Model:</span>
                <span className="h-4 w-4 flex-shrink-0">{getIconForModel(displayModelName)}</span>
                <span className="truncate">{displayModelName}</span>
              </div>
            )}
          </div>

          {/* Column 2: Cost Info */}
          {hasAnyCost ? (
            <div className="flex flex-col gap-1">
              <div className="text-sm font-semibold">Cost</div>
              {hasPromptCost && (
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-semibold">Prompt:</span> <span>{promptCostFormatted}</span>
                </div>
              )}
              {hasCompletionCost && (
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-semibold">Completion:</span>{' '}
                  <span>{completionCostFormatted}</span>
                </div>
              )}
              {hasTotalCost && (
                <div className="text-sm text-black dark:text-white">
                  <span className="font-semibold">Total:</span> <span>{totalCostFormatted}</span>
                </div>
              )}
            </div>
          ) : hasCostCalculationIssue ? (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-sm font-semibold">
                Cost
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
                          This might be because you're using an unrecognized model
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <div className="text-sm text-gray-500">N/A</div>
            </div>
          ) : (
            <div className="flex-col gap-1" />
          )}

          {/* Column 3: Token Info */}
          {hasAnyTokens ? (
            <div className="flex flex-col gap-1">
              <div className="text-sm font-semibold">Tokens</div>
              {hasPromptTokens && (
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-semibold">Prompt:</span>{' '}
                  <FormattedTokenDisplay value={Number(displayPromptTokens)} />
                </div>
              )}
              {hasCompletionTokens && (
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-semibold">Completion:</span>{' '}
                  <FormattedTokenDisplay value={Number(displayCompletionTokens)} />
                </div>
              )}
              {hasTotalTokens && (
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-semibold">Total:</span>{' '}
                  <FormattedTokenDisplay value={Number(displayTotalTokens)} />
                </div>
              )}
            </div>
          ) : (
            <div className="flex-col gap-1" />
          )}
        </div>
      </div>
      {displaySpan?.span_attributes.tools && (
        <div className="flex flex-col gap-1 text-sm">
          <div className="font-semibold">Tool</div>
          <div className="text-black dark:text-white">{displaySpan?.span_attributes.tools}</div>
        </div>
      )}

      {displaySpan?.status_code === 'ERROR' && displaySpan?.status_message && (
        <div className="mt-2 flex flex-col gap-1 text-sm">
          <div className="font-semibold text-red-600 dark:text-red-400">Error Message</div>
          <div className="overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-100 p-3 font-mono text-sm text-red-600 dark:border-slate-700 dark:bg-slate-800 dark:text-red-400">
            {displaySpan.status_message}
          </div>
        </div>
      )}

      {!selectedSpan && (
        <div className="flex flex-1 items-center justify-center text-sm text-gray-500">
          Select a span in the waterfall to view details.
        </div>
      )}
    </div>
  );
};
