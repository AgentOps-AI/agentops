'use client';

import { useRouter } from 'next/navigation';
import { Separator } from '@/components/ui/separator';
import { useEffect, useCallback, useMemo } from 'react';
import { DateRange } from 'react-day-picker';
import { OverviewCharts } from './overview-chart';
import { OverviewStats } from './overview-stats';
import { OverviewFilters } from './overview-filters';
import { useHeaderContext } from '@/app/providers/header-provider';
import ProjectSelector from '@/components/ui/project-selector';
import { useMetrics } from '@/hooks/useMetrics';
import { useUser } from '@/hooks/queries/useUser';
import { useProjects } from '@/hooks/queries/useProjects';
import { useProject } from '@/app/providers/project-provider';
import { LockPasswordIcon } from 'hugeicons-react';
import { PremiumUpsellBanner } from '@/components/ui/premium-upsell-banner';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';
import { useOrgFeatures, isFreeUser, LIMITS } from '@/hooks/useOrgFeatures';
import { startOfMonth, endOfMonth } from 'date-fns';
import { formatNumber } from '@/lib/number_formatting_utils';
import { NoTracesFound } from '@/components/ui/no-traces-found';
import { Skeleton } from '@/components/ui/skeleton';

export default function Overview() {
  const { setHeaderTitle, setHeaderContent } = useHeaderContext();
  const { sharedDateRange, setSharedDateRange } = useProject();
  const { isLoading: userDataLoading } = useUser();
  const { data: projects, isLoading: projectsHookLoading } = useProjects();
  const { selectedProject, setSelectedProject } = useProject();
  const router = useRouter();
  const {
    metrics,
    metricsLoading,
    refreshMetrics,
    error: metricsError,
    isFetching,
  } = useMetrics(sharedDateRange);

  const { premStatus, isLoading: isPermissionsLoading } = useOrgFeatures();

  const currentMonthRange = {
    from: startOfMonth(new Date()),
    to: endOfMonth(new Date()),
  };
  const { metrics: monthlyMetrics, metricsLoading: monthlyMetricsLoading } =
    useMetrics(currentMonthRange);

  const isApproachingSpanLimit = useMemo(() => {
    if (isPermissionsLoading || !monthlyMetrics || monthlyMetricsLoading) {
      return false;
    }

    const isFree = isFreeUser(premStatus);
    const maxSpans = isFree ? LIMITS.free.maxSpansMonthly : LIMITS.pro.maxSpansMonthly;
    const currentSpans = monthlyMetrics.span_count?.total || 0;
    return currentSpans >= maxSpans * 0.8; // Show when at 80% of limit
  }, [premStatus, isPermissionsLoading, monthlyMetrics, monthlyMetricsLoading]);

  const hasFreePlanTruncatedMetrics = useMemo(() => {
    return !!metrics?.freeplan_truncated;
  }, [metrics?.freeplan_truncated]);

  const hasHistoricalData = useMemo(() => {
    if (!isFreeUser(premStatus)) return false;

    return hasFreePlanTruncatedMetrics;
  }, [premStatus, hasFreePlanTruncatedMetrics]);

  const bottomSectionContent = useMemo(() => {
    const hasTraces = metrics && metrics.trace_count > 0;

    if (metricsLoading) {
      return 'loading';
    }

    if (!hasTraces) {
      return 'get-started';
    }

    return 'charts';
  }, [metrics, metricsLoading]);

  const topBannerContent = useMemo(() => {
    const isFree = isFreeUser(premStatus);
    const hasTraces = metrics && metrics.trace_count > 0;

    if (!isPermissionsLoading && metrics) {
      if (isApproachingSpanLimit && hasTraces) {
        if (isFree) {
          return {
            type: 'span-limit',
            title: "You're approaching your monthly limits",
            messages: [
              `You've used ${(((monthlyMetrics?.span_count?.total || 0) / LIMITS.free.maxSpansMonthly) * 100).toFixed(0)}% of your monthly span limit.`,
              'Upgrade to Pro for 100k events included, longer trace retention, and advanced features.',
            ],
          };
        } else {
          return {
            type: 'span-limit',
            title: "You're approaching your monthly limits",
            messages: [
              `You've used ${(((monthlyMetrics?.span_count?.total || 0) / LIMITS.pro.maxSpansMonthly) * 100).toFixed(0)}% of your monthly span limit.`,
              'Contact us for an Enterprise plan with custom limits.',
            ],
          };
        }
      }

      if (isFree && hasFreePlanTruncatedMetrics) {
        if (!hasTraces) {
          // No traces found, but data exists outside the visibility window
          return {
            type: 'historical-data',
            title: 'Upgrade to unlock full access',
            messages: [
              `Your traces are hidden due to the ${LIMITS.free.metricsLookbackDays || 30}-day limit on the free plan.`,
              'Upgrade to Pro to access all your historical data and advanced analytics.',
            ],
            ctaText: 'View all with Pro',
          };
        } else {
          // Has traces and showing truncated data
          return {
            type: 'truncated-data',
            title: `Showing last ${LIMITS.free.metricsLookbackDays || 30} days`,
            messages: [
              `Your current plan limits metrics visibility to the last ${LIMITS.free.metricsLookbackDays || 30} days.`,
              'Upgrade to Pro for unlimited historical data, 90-day retention, and advanced analytics.',
            ],
            ctaText: 'View all with Pro',
          };
        }
      }
    }

    return null;
  }, [
    premStatus,
    isPermissionsLoading,
    metrics,
    isApproachingSpanLimit,
    hasFreePlanTruncatedMetrics,
    monthlyMetrics,
  ]);

  const handleDateApply = useCallback(
    (newRange: DateRange) => {
      setSharedDateRange(newRange);
    },
    [setSharedDateRange],
  );

  const handleRefresh = useCallback(() => {
    refreshMetrics();
  }, [refreshMetrics]);

  const headerContentElement = useMemo(() => {
    return (
      <div className="flex flex-nowrap items-center gap-1 sm:gap-2">
        <div className="flex-shrink-0">
          <OverviewFilters
            selectedRange={sharedDateRange}
            onDateChanged={handleDateApply}
            isRefreshing={isFetching}
            onRefresh={handleRefresh}
          />
        </div>
        <div className="flex-shrink-0">
          <ProjectSelector
            projects={projects}
            isLoading={projectsHookLoading}
            selectedProject={selectedProject}
            setSelectedProject={setSelectedProject}
            noShadow
          />
        </div>
      </div>
    );
  }, [
    sharedDateRange,
    handleDateApply,
    handleRefresh,
    isFetching,
    projects,
    projectsHookLoading,
    selectedProject,
    setSelectedProject,
  ]);

  useEffect(() => {
    setHeaderTitle('Dashboard');
    setHeaderContent(headerContentElement);
  }, [setHeaderTitle, setHeaderContent, headerContentElement]);

  const pageLoading = userDataLoading || projectsHookLoading;

  if (pageLoading) {
    return (
      <div className="flex flex-col gap-2 p-2 lg:w-full min-[1920px]:max-w-6xl">
        {/* Title skeleton */}
        <div className="mt-2 flex items-center gap-2">
          <Skeleton className="h-8 w-32" />
        </div>

        {/* Overview Stats skeleton */}
        <OverviewStats
          metrics={null}
          isLoading={true}
          dateRange={sharedDateRange}
          projectId={selectedProject?.id}
        />

        <div className="pt-3">
          <Separator />
        </div>

        {/* Analytics title skeleton */}
        <div className="flex justify-between pt-8">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-28" />
          </div>
        </div>

        {/* Charts skeleton */}
        <OverviewCharts metrics={null} isLoaded={false} />
      </div>
    );
  }

  if (metricsError) {
    return (
      <div className="flex h-screen items-center justify-center text-red-500">
        Error loading metrics: {metricsError.message}
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-2 p-2 lg:w-full min-[1920px]:max-w-6xl">
        <div className="mt-2 flex items-center gap-2">
          <span className="text-2xl font-medium text-primary">Overview</span>
          {hasFreePlanTruncatedMetrics && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <LockPasswordIcon className="h-5 w-5 cursor-help text-gray-500" />
                </TooltipTrigger>
                <TooltipContent
                  className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-72"
                  side="bottom"
                  sideOffset={8}
                >
                  Data limited to last {LIMITS.free.metricsLookbackDays || 30} days on your current
                  plan.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Top Banner */}
        {topBannerContent && (
          <PremiumUpsellBanner
            title={topBannerContent.title}
            messages={topBannerContent.messages}
            ctaText={topBannerContent.ctaText}
          />
        )}

        <OverviewStats
          metrics={metrics}
          isLoading={metricsLoading}
          dateRange={sharedDateRange}
          projectId={selectedProject?.id}
        />

        <div className="pt-3">
          <Separator />
        </div>
        <div className="flex justify-between pt-8">
          <div className="flex items-center gap-2">
            <div className="text-2xl font-medium text-primary">Analytics</div>
            {!isPermissionsLoading && metrics && (
              <>
                {isFreeUser(premStatus) ? (
                  <div className="flex items-center gap-2">
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <LockPasswordIcon className="h-5 w-5 cursor-help text-gray-500" />
                        </TooltipTrigger>
                        <TooltipContent
                          className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-72"
                          side="bottom"
                          sideOffset={8}
                        >
                          Span usage limited to {formatNumber(LIMITS.free.maxSpansMonthly)} per
                          month on the free plan
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                ) : null}
              </>
            )}
          </div>
          {!isPermissionsLoading && metrics && (
            <div className="flex items-center gap-3">
              {isFreeUser(premStatus) ? (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span>
                    {formatNumber(monthlyMetrics?.span_count?.total || 0)} /{' '}
                    {formatNumber(LIMITS.free.maxSpansMonthly)} spans this month
                  </span>
                  <Progress
                    value={Math.min(
                      100,
                      ((monthlyMetrics?.span_count?.total || 0) / LIMITS.free.maxSpansMonthly) *
                        100,
                    )}
                    className="h-2 w-24 flex-shrink-0"
                  />
                </div>
              ) : (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span>
                    {formatNumber(monthlyMetrics?.span_count?.total || 0)} /{' '}
                    {formatNumber(LIMITS.pro.maxSpansMonthly)} spans this month
                  </span>
                  <Progress
                    value={Math.min(
                      100,
                      ((monthlyMetrics?.span_count?.total || 0) / LIMITS.pro.maxSpansMonthly) * 100,
                    )}
                    className="h-2 w-24 flex-shrink-0"
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom Section */}
        {bottomSectionContent === 'loading' && <OverviewCharts metrics={null} isLoaded={false} />}

        {bottomSectionContent === 'get-started' && <NoTracesFound />}

        {bottomSectionContent === 'charts' && (
          <OverviewCharts metrics={metrics} isLoaded={!metricsLoading} />
        )}
      </div>
    </>
  );
}
