import React, { useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { formatPrice, formatNumber } from '@/lib/number_formatting_utils';
import { Zap, Database, DollarSign, RotateCcw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { DateRange } from 'react-day-picker';
import { startOfDay } from 'date-fns';
import { ProjectUsageBreakdown } from '@/types/billing.types';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

interface ProjectCostBreakdownProps {
  orgId: string;
  projectCosts: ProjectUsageBreakdown[];
  isLoading: boolean;
  error: Error | null;
  activeDateRange: DateRange;
  defaultDateRange: DateRange;
  onDateRangeChange: (range: DateRange | undefined) => void;
  className?: string;
}

interface ProjectCostRowProps {
  project: ProjectUsageBreakdown;
}

interface DateRangeControlsProps {
  range: DateRange;
  onApply: (range: DateRange) => void;
  onResetToBillingPeriod: () => void;
  isBillingPeriodSelected: boolean;
}

function ProjectCostRow({ project }: ProjectCostRowProps) {
  return (
    <div className="flex items-center justify-between rounded-md px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800/50">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="truncate text-sm font-medium text-gray-900 dark:text-white">
          {project.project_name}
        </span>
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
        {project.tokens > 0 ? (
          <div className="flex w-24 items-center gap-1">
            <Zap className="h-3 w-3 text-green-500" />
            <span>{formatNumber(project.tokens)} tokens</span>
          </div>
        ) : (
          <div className="w-24" />
        )}
        {project.spans > 0 ? (
          <div className="flex w-24 items-center gap-1">
            <Database className="h-3 w-3 text-amber-500" />
            <span>{formatNumber(project.spans)} spans</span>
          </div>
        ) : (
          <div className="w-24" />
        )}
      </div>
      <div className="ml-3 w-20 text-right text-sm font-medium text-gray-900 dark:text-white">
        {formatPrice(project.total_cost / 100)}
      </div>
    </div>
  );
}

function DateRangeControls({
  range,
  onApply,
  onResetToBillingPeriod,
  isBillingPeriodSelected,
}: DateRangeControlsProps) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="text-sm text-gray-600 dark:text-gray-400">Date Range:</div>
      <div className="flex items-center gap-2">
        <DateRangePicker
          key={`${range.from?.getTime() || 'no-from'}-${range.to?.getTime() || 'no-to'}`}
          isRanged
          defaultRange={range}
          onApply={onApply}
          noShadow
          wrapperClassNames="border-0"
        />

        <Button
          variant="outline"
          size="sm"
          onClick={onResetToBillingPeriod}
          className="h-7 text-xs"
          disabled={isBillingPeriodSelected}
        >
          <RotateCcw className="mr-1 h-3 w-3" />
          Current Billing Period
        </Button>
      </div>
    </div>
  );
}

export function ProjectCostBreakdown({
  projectCosts,
  isLoading,
  error,
  activeDateRange,
  defaultDateRange,
  onDateRangeChange,
  className,
}: ProjectCostBreakdownProps) {
  const handleResetToBillingPeriod = useCallback(() => {
    onDateRangeChange(undefined);
  }, [onDateRangeChange]);

  const handleApply = useCallback(
    (newRange: DateRange) => {
      onDateRangeChange(newRange);
    },
    [onDateRangeChange],
  );

  const isBillingPeriodSelected = useMemo(() => {
    const activeFrom = activeDateRange.from ? startOfDay(activeDateRange.from).getTime() : null;
    const activeTo = activeDateRange.to ? startOfDay(activeDateRange.to).getTime() : null;
    const defaultFrom = defaultDateRange.from ? startOfDay(defaultDateRange.from).getTime() : null;
    const defaultTo = defaultDateRange.to ? startOfDay(defaultDateRange.to).getTime() : null;

    return activeFrom === defaultFrom && activeTo === defaultTo;
  }, [activeDateRange, defaultDateRange]);

  const dateControls = (
    <DateRangeControls
      range={activeDateRange}
      onApply={handleApply}
      onResetToBillingPeriod={handleResetToBillingPeriod}
      isBillingPeriodSelected={isBillingPeriodSelected}
    />
  );

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <DollarSign className="h-5 w-5" />
            Project Cost Breakdown
          </CardTitle>
          {dateControls}
        </CardHeader>
        <CardContent className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <DollarSign className="h-5 w-5" />
            Project Cost Breakdown
          </CardTitle>
          {dateControls}
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">Unable to load project cost data</p>
        </CardContent>
      </Card>
    );
  }

  if (!projectCosts || projectCosts.length === 0) {
    return (
      <Card className={className}>
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <DollarSign className="h-5 w-5" />
            Project Cost Breakdown
          </CardTitle>
          {dateControls}
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">No usage data for this period</p>
        </CardContent>
      </Card>
    );
  }

  const totalCost = projectCosts.reduce((sum, project) => sum + project.total_cost, 0);
  const totalTokens = projectCosts.reduce((sum, project) => sum + project.tokens, 0);
  const totalSpans = projectCosts.reduce((sum, project) => sum + project.spans, 0);
  const totalTokenCost = projectCosts.reduce((sum, project) => sum + project.token_cost, 0);
  const totalSpanCost = projectCosts.reduce((sum, project) => sum + project.span_cost, 0);

  const zeroCostProjects = projectCosts.filter((p) => p.total_cost === 0);
  const projectsWithCost = projectCosts.filter((p) => p.total_cost > 0);

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between text-lg">
          <div className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            <CardTitle>Project Cost Breakdown</CardTitle>
          </div>
          <Badge variant="secondary" className="text-sm">
            {formatPrice(totalCost / 100)}
          </Badge>
        </div>

        {dateControls}
      </CardHeader>

      <CardContent className="pb-4 pt-2">
        <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2 text-sm dark:border-gray-700">
          <div className="min-w-0 flex-1">
            <span className="text-gray-500 dark:text-gray-400">
              {projectCosts.length} project{projectCosts.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex items-center gap-4 text-gray-500 dark:text-gray-400">
            <div className="w-24 text-center">
              <div className="flex items-center justify-center gap-1">
                <Zap className="h-4 w-4 text-green-500" />
                <span>{formatNumber(totalTokens)}</span>
              </div>
              <div className="text-xs text-green-600 dark:text-green-400">
                {formatPrice(totalTokenCost / 100)}
              </div>
            </div>
            <div className="w-24 text-center">
              <div className="flex items-center justify-center gap-1">
                <Database className="h-4 w-4 text-amber-500" />
                <span>{formatNumber(totalSpans)}</span>
              </div>
              <div className="text-xs text-amber-600 dark:text-amber-400">
                {formatPrice(totalSpanCost / 100)}
              </div>
            </div>
          </div>
          <div className="ml-3 w-20 text-right font-medium">Total</div>
        </div>

        <div className="space-y-0.5 pt-1">
          {projectsWithCost.map((project) => (
            <ProjectCostRow key={project.project_id} project={project} />
          ))}
        </div>
        {zeroCostProjects.length > 0 && (
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="zero-cost-projects">
              <AccordionTrigger>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {zeroCostProjects.length} projects with no cost
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-0.5">
                  {zeroCostProjects.map((project) => (
                    <ProjectCostRow key={project.project_id} project={project} />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          Costs calculated using the same billing data as the dashboard above.
        </p>
      </CardContent>
    </Card>
  );
}
