import { EventsPerTraceChart } from '@/components/charts/bar-chart/events-per-trace';
import { TraceCostDistributionChart } from '@/components/charts/bar-chart/trace-cost-distribution-chart';
import { TraceDurationDistributionBarChart } from '@/components/charts/bar-chart/trace-duration-distribution-chart';
import { FailedTracesChart } from '@/components/charts/line-chart/failed-traces-chart';
import { TraceEndChart } from '@/components/charts/line-chart/trace-end-states';
import { TraceEndStatesPieChart } from '@/components/charts/pie-chart/trace-end-states';
import { ChartCard } from '@/components/ui/chart-card';
import { ProjectMetrics } from '@/lib/interfaces';
import { memo } from 'react';
import { ChartSkeleton } from '@/components/ui/skeletons';

type OverviewChartsProps = {
  metrics: ProjectMetrics | null | undefined;
  isLoaded: boolean;
};

const OverviewChartsComponent = ({ metrics, isLoaded }: OverviewChartsProps) => {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        <ChartCard
          title="Span End States"
          containerStyles="sm:col-span-2 h-full"
          cardStyles="shadow-xl sm:p-0 h-full"
          footerStyles="flex justify-center gap-8 mt-3"
        >
          {!isLoaded || !metrics ? <ChartSkeleton /> : <TraceEndChart metrics={metrics} />}
        </ChartCard>

        <ChartCard
          title="Span End States Distribution"
          containerStyles="sm:col-span-2 md:col-span-1 h-full"
          cardStyles="shadow-xl sm:p-0 h-full"
          cardHeaderStyles="mb-0 pb-0"
        >
          {!isLoaded || !metrics ? <ChartSkeleton /> : <TraceEndStatesPieChart metrics={metrics} />}
        </ChartCard>

        <ChartCard
          title="Failed Spans"
          cardStyles="h-full sm:p-0"
          containerStyles="sm:col-span-2 md:col-span-1"
        >
          {!isLoaded || !metrics ? (
            <ChartSkeleton />
          ) : (
            <FailedTracesChart metrics={metrics} showGrid showYAxis />
          )}
        </ChartCard>

        <ChartCard
          title="Trace Cost Distribution"
          cardStyles="h-full sm:p-0"
          containerStyles="sm:col-span-2 md:col-span-1"
        >
          {!isLoaded || !metrics ? (
            <ChartSkeleton />
          ) : (
            <TraceCostDistributionChart metrics={metrics} numBuckets={10} />
          )}
        </ChartCard>

        <ChartCard
          title="Spans Per Trace"
          cardStyles="h-full sm:p-0"
          containerStyles="sm:col-span-2 md:col-span-1"
        >
          {!isLoaded || !metrics ? <ChartSkeleton /> : <EventsPerTraceChart metrics={metrics} />}
        </ChartCard>

        <ChartCard
          title="Trace Duration Distribution"
          cardStyles="h-full sm:p-0"
          containerStyles="sm:col-span-3"
        >
          {!isLoaded || !metrics ? (
            <ChartSkeleton />
          ) : (
            <TraceDurationDistributionBarChart metrics={metrics} numBuckets={30} />
          )}
        </ChartCard>
      </div>
    </>
  );
};

export const OverviewCharts = memo(OverviewChartsComponent);
