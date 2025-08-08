import { ChartCard } from '@/components/ui/chart-card';
import { StatSkeleton } from '@/components/ui/skeletons';
import { cardHeaderStyles, cardTitleStyles } from '@/constants/styles';
import { formatPrice, formatPercentage } from '@/lib/utils';
import { formatNumber } from '@/lib/number_formatting_utils';
import React, { memo } from 'react';
import { ProjectMetrics } from '@/lib/interfaces';
import { FormattedTokenDisplay } from '@/components/ui/formatted-token-display';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import { startOfMonth, endOfMonth } from 'date-fns';
import { DateRange } from 'react-day-picker';
import { useMetrics as useMonthlyMetrics } from '@/hooks/useMetrics';
import { BillingCostTooltip } from '@/components/ui/billing-cost-tooltip';

type OverviewStatsProps = {
  metrics: ProjectMetrics | null | undefined;
  isLoading: boolean;
  dateRange?: DateRange;
  projectId?: string | null;
};

type StatItem = {
  title: string;
  value: React.ReactNode;
  isLoading: boolean;
  tooltipContent: React.ReactNode;
  cardTitleTextStyles?: string;
};

const OverviewStatsComponent = ({
  metrics,
  isLoading,
  dateRange,
  projectId,
}: OverviewStatsProps) => {
  const { permissions } = useOrgFeatures();

  const currentMonthRange = {
    from: startOfMonth(new Date()),
    to: endOfMonth(new Date()),
  };
  const { metrics: monthlyMetrics, metricsLoading: monthlyLoading } =
    useMonthlyMetrics(currentMonthRange);

  const hasFilteredTokenMetrics = !!metrics?.token_metrics;

  const stats: StatItem[] = [
    {
      title: 'Total Cost',
      value: hasFilteredTokenMetrics ? formatPrice(metrics.token_metrics.total_cost) : null,
      isLoading: isLoading || !hasFilteredTokenMetrics,
      tooltipContent: hasFilteredTokenMetrics ? (
        <BillingCostTooltip dateRange={dateRange} projectId={projectId} />
      ) : (
        'Total cost of the project'
      ),
    },
    {
      title: 'Tokens generated',
      value: hasFilteredTokenMetrics ? (
        <FormattedTokenDisplay value={metrics.token_metrics.total_tokens?.all} />
      ) : null,
      isLoading: isLoading || !hasFilteredTokenMetrics,
      tooltipContent: 'Tokens generated',
    },
    {
      title: 'Fail Rate',
      value: metrics
        ? formatPercentage(
            (metrics.fail_datetime?.length ?? 0) /
              ((metrics.success_datetime?.length ?? 0) + (metrics.fail_datetime?.length ?? 0)),
          )
        : null,
      isLoading: isLoading || !metrics,
      tooltipContent: 'Percentage failed',
    },
    {
      title: 'Total Events',
      value: metrics?.span_count ? (
        <FormattedTokenDisplay value={metrics.span_count.total} />
      ) : null,
      isLoading: isLoading || !metrics?.span_count,
      tooltipContent: 'Total events from the project',
    },
  ];

  if (permissions?.billingAndUsage.maxSpansMonthly) {
    const maxSpans = permissions.billingAndUsage.maxSpansMonthly;
    const currentSpans = monthlyMetrics?.span_count?.total || 0;
    const usagePercentage = Math.min((currentSpans / maxSpans) * 100, 100);

    stats.push({
      title: 'Monthly Spans',
      value: monthlyLoading ? null : (
        <div className="flex flex-col items-start">
          <div className="flex flex-wrap items-center">
            <span className={usagePercentage > 90 ? 'text-red-600' : ''}>
              {formatNumber(currentSpans)} / {formatNumber(maxSpans)}
            </span>
          </div>
          {usagePercentage > 90 && (
            <span className="mt-1 whitespace-nowrap text-xs text-red-600">
              {usagePercentage.toFixed(0)}% used
            </span>
          )}
        </div>
      ),
      isLoading: isLoading || monthlyLoading,
      tooltipContent: 'Spans used this month (resets monthly)',
      ...(usagePercentage > 90 && { cardTitleTextStyles: 'h-7' }),
    });
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-5">
      {stats.map((stat, index) => (
        <ChartCard
          key={index}
          tooltipContent={stat.tooltipContent}
          title={stat.title}
          cardTitleStyles={cardTitleStyles}
          cardTitleTextStyles={stat.cardTitleTextStyles || 'h-10'}
          cardHeaderStyles={cardHeaderStyles}
          cardStyles="shadow-sm h-24"
          cardContentStyles="p-0 pl-2"
        >
          {stat.isLoading ? (
            <StatSkeleton />
          ) : (
            <div className="flex items-center justify-between gap-10 text-xl font-semibold text-primary">
              <div className="flex items-center gap-2">{stat.value}</div>
            </div>
          )}
        </ChartCard>
      ))}
    </div>
  );
};

export const OverviewStats = memo(OverviewStatsComponent);
