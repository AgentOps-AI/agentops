'use client';

import { CommonChart } from '@/components/charts/common-chart';
import { CustomizedAxisTick } from '@/components/ui/axis-tick';
import { ChartConfig } from '@/components/ui/chart';
import { ProjectMetrics } from '@/lib/interfaces';
import { scaleSymlog } from 'd3-scale';
import { useMemo } from 'react';
import { BarProps } from 'recharts';

const logScale = scaleSymlog();

const chartConfig = {
  value: {
    label: 'Count',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

// Helper function to format nanoseconds into human-readable time
const formatDuration = (ns: number): string => {
  if (ns < 1000) return `${ns}ns`;
  if (ns < 1000000) return `${(ns / 1000).toFixed(1)}µs`;
  if (ns < 1000000000) return `${(ns / 1000000).toFixed(1)}ms`;
  if (ns < 60000000000) return `${(ns / 1000000000).toFixed(1)}s`;
  return `${(ns / 60000000000).toFixed(1)}min`;
};

const config: BarProps[] = [
  {
    dataKey: 'value',
    radius: 9,
    className: 'fill-chart-primary-muted stroke-chart-primary stroke-[0.5px] drop-shadow-xl',
  },
];

export function TraceDurationDistributionBarChart({
  metrics,
  numBuckets = 20,
}: {
  metrics: ProjectMetrics;
  numBuckets: number;
}) {
  const chartData = useMemo(() => {
    // Expected format for trace_durations is an array of durations in nanoseconds
    const durations = metrics.trace_durations || [];

    if (durations.length === 0) {
      // Return empty buckets when no data
      return Array(numBuckets)
        .fill(0)
        .map((_, i) => ({
          name: `Bucket ${i + 1}`,
          value: 0,
          tooltipLabel: '0 traces (0.0%)',
        }));
    }

    // Sort durations to find range
    const sortedDurations = [...durations].sort((a, b) => a - b);
    const minDuration = sortedDurations[0] || 0;
    const maxDuration = sortedDurations[sortedDurations.length - 1] || 0;

    if (minDuration === maxDuration) {
      // If all durations are the same, create buckets around that value
      // Put all data in the middle bucket and pad with empty buckets
      const value = minDuration;
      const middleBucket = Math.floor(numBuckets / 2);

      // Create a reasonable range around the single value
      const padding = value === 0 ? 1000 : value * 0.1; // 10% padding or 1µs for zero values
      const rangeStart = Math.max(0, value - padding * middleBucket);
      const bucketSize = (padding * 2) / numBuckets;

      return Array(numBuckets)
        .fill(0)
        .map((_, i) => {
          const start = rangeStart + i * bucketSize;
          const end = rangeStart + (i + 1) * bucketSize;
          const count = i === middleBucket ? durations.length : 0;

          return {
            name: `${formatDuration(start)} - ${formatDuration(end)}`,
            value: count,
            tooltipLabel: `${count} traces (${((count / durations.length) * 100).toFixed(1)}%)`,
          };
        });
    }

    // Create buckets for the histogram
    const bucketSize = Math.ceil((maxDuration - minDuration) / numBuckets);

    // Initialize buckets
    const buckets = Array(numBuckets)
      .fill(0)
      .map((_, i) => {
        const start = minDuration + i * bucketSize;
        const end = minDuration + (i + 1) * bucketSize;
        return {
          start,
          end,
          count: 0,
          name: `${formatDuration(start)} - ${formatDuration(end)}`,
        };
      });

    // Count durations in each bucket
    durations.forEach((duration) => {
      const bucketIndex = Math.min(
        Math.floor((duration - minDuration) / bucketSize),
        numBuckets - 1,
      );
      if (bucketIndex >= 0 && bucketIndex < buckets.length) {
        buckets[bucketIndex].count++;
      }
    });

    // Convert to the format expected by Recharts
    return buckets.map((bucket) => ({
      name: bucket.name,
      value: bucket.count,
      tooltipLabel: `${bucket.count} traces (${((bucket.count / durations.length) * 100).toFixed(1)}%)`,
    }));
  }, [metrics.trace_durations, numBuckets]);

  // Check if all buckets are empty
  const isChartEmpty = useMemo(() => {
    return !chartData || chartData.every(point => point.value === 0);
  }, [chartData]);

  if (isChartEmpty) {
    return (
      <CommonChart
        chartData={[]}
        type="bar"
        config={[]}
        chartConfig={{}}
        xAxisProps={{ height: 30 }}
      />
    );
  }

  return (
    <CommonChart
      type="bar"
      chartData={chartData}
      chartConfig={chartConfig}
      xAxisProps={{
        dataKey: 'name',
        fontSize: 12,
        tickLine: false,
        axisLine: false,
        tick: (props) => <CustomizedAxisTick {...props} />,
        tickCount: Math.min(numBuckets, chartData.length),
        interval: 0,
        height: 90,
      }}
      yAxisProps={{
        fontSize: 12,
        tickLine: false,
        axisLine: false,
        domain: [0, 'dataMax'],
        scale: logScale,
        tickCount: 10,
      }}
      config={config}
      showLegend={false}
      tooltipContentProps={{
        formatter: (value, name, props) => [props.payload.tooltipLabel || value, ''],
      }}
    />
  );
}
