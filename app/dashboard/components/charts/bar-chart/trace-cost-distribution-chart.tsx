'use client';

import { CommonChart } from '@/components/charts/common-chart';
import { CustomizedAxisTick } from '@/components/ui/axis-tick';
import { ChartConfig } from '@/components/ui/chart';
import { ProjectMetrics } from '@/lib/interfaces';
import { formatPrice } from '@/lib/utils';
import { scaleSymlog } from 'd3-scale';
import { useMemo } from 'react';
import { BarProps } from 'recharts';
import { DataPoint } from './chart';

const logScale = scaleSymlog();

const chartConfig = {
  count: {
    label: 'Number of Traces',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

const config: BarProps[] = [
  {
    dataKey: 'count',
    radius: 9,
    className: 'fill-chart-primary-muted stroke-chart-primary stroke-[0.5px] drop-shadow-xl',
  },
];

export function TraceCostDistributionChart({
  metrics,
  numBuckets = 10,
}: {
  metrics: ProjectMetrics;
  numBuckets?: number;
}) {
  // This function handles formatting trace cost data for the chart
  const formatTraceDataForChart = (traceCostDates: Record<string, number>) => {
    // Always return exactly numBuckets buckets
    let dataPoints: DataPoint[] = [];

    if (!traceCostDates || Object.keys(traceCostDates).length === 0) {
      // Return empty buckets when no data
      return Array.from({ length: numBuckets }, (_, i) => {
        const start = i * 0.1;
        const end = (i + 1) * 0.1;
        return {
          name: `${formatPrice(start)} - ${formatPrice(end)}`,
          count: 0,
        };
      });
    }

    // Convert the trace_cost_dates dictionary to an array of costs
    const costValues = Object.values(traceCostDates);

    // Find max cost for scaling
    const maxCost = Math.max(...costValues);
    const minCost = Math.min(...costValues.filter(v => v > 0));

    if (maxCost === 0 || maxCost === minCost) {
      // If all costs are zero or the same, create buckets around that value
      const value = maxCost;
      const middleBucket = Math.floor(numBuckets / 2);

      // Create a reasonable range around the single value
      const padding = value === 0 ? 0.01 : value * 0.1; // 10% padding or $0.01 for zero values
      const rangeStart = Math.max(0, value - padding * middleBucket);
      const bucketSize = (padding * 2) / numBuckets;

      dataPoints = Array.from({ length: numBuckets }, (_, i) => ({
        name: `${formatPrice(rangeStart + i * bucketSize)} - ${formatPrice(rangeStart + (i + 1) * bucketSize)}`,
        count: 0,
      }));

      // If there are actual costs, put them in the middle bucket
      if (maxCost > 0) {
        // Count the number of traces instead of summing costs
        dataPoints[middleBucket].count = Object.keys(traceCostDates).length;
      }

      return dataPoints;
    }

    // Calculate bucket size to ensure exactly numBuckets
    const bucketSize = maxCost / numBuckets;

    // Initialize exactly numBuckets buckets with proper labels
    dataPoints = Array.from({ length: numBuckets }, (_, i) => {
      const start = i * bucketSize;
      const end = (i + 1) * bucketSize;
      return {
        name: `${formatPrice(start)} - ${formatPrice(end)}`,
        count: 0,
      };
    });

    // Count the traces in each bucket using reduce
    const bucketCounts = Object.entries(traceCostDates).reduce((acc, [_, cost]) => {
      if (cost <= 0) return acc;

      const bucketIndex = Math.min(Math.floor(cost / bucketSize), numBuckets - 1);

      if (bucketIndex >= 0 && bucketIndex < acc.length) {
        acc[bucketIndex].count += 1;
      }

      return acc;
    }, dataPoints);

    // Return all buckets, even empty ones, to ensure we have exactly numBuckets
    return bucketCounts;
  };

  // Implementation for useMemo with the formatter
  const chartData = useMemo(() => {
    return formatTraceDataForChart(
      metrics.trace_cost_dates &&
        typeof metrics.trace_cost_dates === 'object' &&
        !Array.isArray(metrics.trace_cost_dates)
        ? metrics.trace_cost_dates
        : {},
    );
  }, [metrics.trace_cost_dates, numBuckets]);

  // Check if all buckets are empty
  const isChartEmpty = useMemo(() => {
    return !chartData || chartData.every(point => point.count === 0) || metrics.trace_count === 0;
  }, [chartData, metrics.trace_count]);

  // Only show empty chart if no data
  if (isChartEmpty) {
    return (
      <CommonChart
        chartData={[]}
        type="line"
        config={[]}
        chartConfig={{}}
        xAxisProps={{ height: 30 }}
      />
    );
  }

  return (
    <CommonChart
      type="bar"
      chartConfig={chartConfig}
      chartData={chartData}
      xAxisProps={{
        dataKey: 'name',
        interval: 0,
        tick: (props) => <CustomizedAxisTick {...props} />,
        height: 60,
      }}
      yAxisProps={{
        allowDecimals: false,
        scale: logScale,
        tickCount: 10,
        domain: [0, 'dataMax'],
      }}
      tooltipContentProps={{
        indicator: 'dot',
        formatter: (value) => [`${value} `, 'Traces'],
      }}
      config={config}
      showLegend={false}
    />
  );
}
