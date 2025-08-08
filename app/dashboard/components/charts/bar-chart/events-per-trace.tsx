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
  count: {
    label: 'Count:',
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

export function EventsPerTraceChart({
  metrics,
  numBuckets = 10
}: {
  metrics: ProjectMetrics;
  numBuckets?: number;
}) {
  // Use useMemo to format the data properly
  const formattedData = useMemo(() => {
    if (!metrics || !metrics.spans_per_trace ||
      (Array.isArray(metrics.spans_per_trace) && metrics.spans_per_trace.length === 0)) {
      // Return empty buckets when no data
      return Array(numBuckets)
        .fill(0)
        .map((_, i) => ({
          name: String(i + 1),
          count: 0,
        }));
    }

    // Handle both array and single object cases
    let mergedData: Record<string, number> = {};

    if (Array.isArray(metrics.spans_per_trace)) {
      // If it's an array, merge all records
      metrics.spans_per_trace.forEach((record) => {
        Object.entries(record).forEach(([key, value]) => {
          if (typeof value === 'number') {
            mergedData[key] = (mergedData[key] || 0) + value;
          }
        });
      });
    } else {
      // If it's a single object, use it directly
      mergedData = metrics.spans_per_trace as Record<string, number>;
    }

    // Convert spans_per_trace to a proper object format
    const spansData = Object.entries(mergedData);

    if (spansData.length === 0) {
      // Return empty buckets when no data
      return Array(numBuckets)
        .fill(0)
        .map((_, i) => ({
          name: String(i + 1),
          count: 0,
        }));
    }

    // Find the range of spans per trace
    const spanCounts = spansData.map(([key]) => parseInt(key, 10)).filter(n => !isNaN(n));

    if (spanCounts.length === 0) {
      return Array(numBuckets)
        .fill(0)
        .map((_, i) => ({
          name: String(i + 1),
          count: 0,
        }));
    }

    const minSpanCount = Math.min(...spanCounts);
    const maxSpanCount = Math.max(...spanCounts);

    // If all traces have the same number of spans, create buckets around that value
    if (minSpanCount === maxSpanCount || spansData.length === 1) {
      const value = maxSpanCount;
      const result: Array<{ name: string; count: number }> = [];

      // Create a range of buckets centered around the single value
      const startBucket = Math.max(1, value - Math.floor(numBuckets / 2));

      for (let i = 0; i < numBuckets; i++) {
        const bucketValue = startBucket + i;
        const existingData = spansData.find(([key]) => parseInt(key, 10) === bucketValue);

        result.push({
          name: String(bucketValue),
          count: existingData ? existingData[1] : 0,
        });
      }

      return result;
    }

    // Determine the range we need to cover
    const range = maxSpanCount - minSpanCount + 1;

    if (range >= numBuckets) {
      // If we have more unique values than numBuckets, create histogram buckets
      const bucketSize = Math.ceil((maxSpanCount - minSpanCount + 1) / numBuckets);
      const result: Array<{ name: string; count: number }> = [];

      // Initialize buckets
      for (let i = 0; i < numBuckets; i++) {
        const start = minSpanCount + i * bucketSize;
        const end = Math.min(minSpanCount + (i + 1) * bucketSize - 1, maxSpanCount);

        // For single value buckets, just show the number
        // For ranges, show "start-end"
        const label = start === end ? String(start) : `${start}-${end}`;

        result.push({
          name: label,
          count: 0,
        });
      }

      // Count traces in each bucket
      spansData.forEach(([key, value]) => {
        const spanCount = parseInt(key, 10);
        if (!isNaN(spanCount)) {
          const bucketIndex = Math.min(
            Math.floor((spanCount - minSpanCount) / bucketSize),
            numBuckets - 1
          );
          if (bucketIndex >= 0 && bucketIndex < result.length) {
            result[bucketIndex].count += value;
          }
        }
      });

      return result;
    } else {
      // If we have fewer unique values than numBuckets, pad with empty buckets
      const result: Array<{ name: string; count: number }> = [];
      const padding = Math.floor((numBuckets - range) / 2);
      const start = Math.max(1, minSpanCount - padding);

      for (let i = 0; i < numBuckets; i++) {
        const bucketValue = start + i;
        const existingData = spansData.find(([key]) => parseInt(key, 10) === bucketValue);

        result.push({
          name: String(bucketValue),
          count: existingData ? existingData[1] : 0,
        });
      }

      return result;
    }
  }, [metrics, numBuckets]);

  // Check if all buckets are empty
  const isChartEmpty = useMemo(() => {
    return !formattedData || formattedData.every(point => point.count === 0);
  }, [formattedData]);

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
      chartData={formattedData}
      chartConfig={chartConfig}
      xAxisProps={{
        dataKey: 'name',
        fontSize: 12,
        tickLine: false,
        axisLine: false,
        tick: (props) => <CustomizedAxisTick {...props} />,
        height: 50,
        interval: 0,
        allowDecimals: false,
      }}
      yAxisProps={{
        allowDecimals: false,
        tickCount: 10,
        scale: logScale,
      }}
      tooltipContentProps={{
        labelFormatter: (label) => `${label} Events`,
      }}
      config={config}
      showLegend={false}
    />
  );
}
