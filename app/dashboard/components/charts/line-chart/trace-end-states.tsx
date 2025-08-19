'use client';

import { CommonChart } from '@/components/charts/common-chart';
import { ChartConfig } from '@/components/ui/chart';
import { ProjectMetrics } from '@/lib/interfaces';
import {
  firstLineShadowEffect,
  secondLineShadowEffect,
  thirdLineShadowEffect,
} from '@/utils/common.utils';
import { useMemo, useState, useCallback, useRef } from 'react';
import { LineProps } from 'recharts';

const chartConfig = {
  Success: {
    label: 'Success',
    color: 'hsl(var(--chart-1))',
  },
  Indeterminate: {
    label: 'Indeterminate',
    color: 'hsl(var(--chart-2))',
  },
  Fail: {
    label: 'Fail',
    color: 'hsl(var(--chart-error))',
  },
} satisfies ChartConfig;

export function TraceEndChart({ metrics }: { metrics: ProjectMetrics }) {
  const [shadowsApplied, setShadowsApplied] = useState(false);
  const animationCompletedRef = useRef(false);

  const chartData = useMemo(() => {
    const readableDates: {
      [key: string]: { date: string; Success: number; Fail: number; Indeterminate: number };
    } = {};

    // Initialize dates from all three arrays
    const allDates = new Set<string>();

    metrics.success_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      allDates.add(date);
    });

    metrics.fail_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      allDates.add(date);
    });

    metrics.indeterminate_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      allDates.add(date);
    });

    // Initialize all dates with zero counts
    allDates.forEach((date) => {
      readableDates[date] = { date, Success: 0, Fail: 0, Indeterminate: 0 };
    });

    // Count occurrences for each date
    metrics.success_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      readableDates[date].Success++;
    });

    metrics.fail_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      readableDates[date].Fail++;
    });

    metrics.indeterminate_datetime?.forEach((dateStr) => {
      const date = dateStr.split('T')[0];
      readableDates[date].Indeterminate++;
    });

    return Object.values(readableDates).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
    );
  }, [metrics]);

  const handleAnimationEnd = useCallback(() => {
    if (!animationCompletedRef.current) {
      setShadowsApplied(true);
      animationCompletedRef.current = true;
    }
  }, []);

  const lineConfig: LineProps[] = useMemo(
    () => [
      {
        dataKey: 'Success',
        key: 'Success',
        type: 'monotone',
        stroke: 'var(--color-Success)',
        strokeWidth: 1.3,
        dot: false,
        onAnimationEnd: handleAnimationEnd,
        style: shadowsApplied ? { filter: firstLineShadowEffect } : {},
      },
      {
        dataKey: 'Indeterminate',
        key: 'Indeterminate',
        type: 'monotone',
        stroke: 'var(--color-Indeterminate)',
        strokeWidth: 1.3,
        dot: false,
        style: shadowsApplied ? { filter: secondLineShadowEffect } : {},
      },
      {
        dataKey: 'Fail',
        key: 'Fail',
        type: 'monotone',
        stroke: 'var(--color-Fail)',
        strokeWidth: 1.3,
        dot: false,
        style: shadowsApplied ? { filter: thirdLineShadowEffect } : {},
      },
    ],
    [shadowsApplied, handleAnimationEnd],
  );

  const hasData = !!(
    (metrics.success_datetime && metrics.success_datetime.length > 0) ||
    (metrics.fail_datetime && metrics.fail_datetime.length > 0) ||
    (metrics.indeterminate_datetime && metrics.indeterminate_datetime.length > 0)
  );

  if (!hasData) {
    return (
      <CommonChart
        chartData={[]}
        type="line"
        config={[]}
        chartConfig={{}}
        xAxisProps={{ height: 30 }}
        horizontalEmptyState
      />
    );
  }

  return (
    <>
      <CommonChart
        type="line"
        chartConfig={chartConfig}
        chartData={chartData}
        xAxisProps={{
          dataKey: 'date',
          height: 30,
          minTickGap: 32,
          tickCount: 10,
          tickFormatter: (value) => {
            const date = new Date(value);
            return date.toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            });
          },
        }}
        yAxisProps={{
          domain: [0, 'dataMax'],
          allowDecimals: false,
        }}
        tooltipContentProps={{
          className: 'w-[50px]',
          labelFormatter: (value) => {
            return new Date(value).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            });
          },
        }}
        config={lineConfig}
      />
    </>
  );
}
