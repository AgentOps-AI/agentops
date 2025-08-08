'use client';

import { CustomizedAxisTick } from '@/components/ui/axis-tick';
import { ChartConfig } from '@/components/ui/chart';
import { ProjectMetrics } from '@/lib/interfaces';
import { thirdLineShadowEffect } from '@/utils/common.utils';
import { scaleSymlog } from 'd3-scale';
import { useMemo, useState, useCallback, useRef } from 'react';
import { LineProps } from 'recharts';
import { CommonChart } from '../common-chart';
import { DataPoint } from './chart';

const logScale = scaleSymlog();

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const chartConfig = {
  count: {
    label: 'Count',
    color: 'hsl(var(--chart-error))',
  },
} satisfies ChartConfig;

export function FailedTracesChart({
  metrics,
  showGrid,
}: {
  metrics: ProjectMetrics;
  showGrid: boolean;
  showYAxis: boolean;
}) {
  const [shadowsApplied, setShadowsApplied] = useState(false);
  const animationCompletedRef = useRef(false);

  const chartData = useMemo(() => {
    if (!metrics.fail_datetime || metrics.fail_datetime.length === 0) return [];

    const sortedDates = [...metrics.fail_datetime].sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    const from = new Date(sortedDates[0]).getTime();
    const to = new Date(sortedDates[sortedDates.length - 1]).getTime() + 24 * 60 * 60 * 1000;

    const bucketDuration = 24 * 60 * 60 * 1000;

    const dataPoints: DataPoint[] = [];

    let currentStart = from;
    while (currentStart < to) {
      const currentDate = new Date(currentStart);
      dataPoints.push({
        name: `${MONTHS[currentDate.getMonth()]} ${currentDate.getDate()}`,
        count: 0,
      });
      currentStart += bucketDuration;
    }

    metrics.fail_datetime.forEach((dateTimeStr: string) => {
      const timestamp = new Date(dateTimeStr).getTime();
      const diff = timestamp - from;
      const idx = Math.floor(diff / bucketDuration);
      if (idx >= 0 && idx < dataPoints.length) dataPoints[idx].count++;
    });

    return dataPoints;
  }, [metrics.fail_datetime]);

  const handleAnimationEnd = useCallback(() => {
    if (!animationCompletedRef.current) {
      setShadowsApplied(true);
      animationCompletedRef.current = true;
    }
  }, []);

  const lineConfig: LineProps[] = useMemo(
    () => [
      {
        dataKey: 'count',
        key: 'count',
        type: 'monotone',
        stroke: 'var(--color-count)',
        strokeWidth: 1.3,
        dot: false,
        onAnimationEnd: handleAnimationEnd,
        style: shadowsApplied ? { filter: thirdLineShadowEffect } : {},
        activeDot: {
          style: { cursor: 'pointer' },
        },
      },
    ],
    [shadowsApplied, handleAnimationEnd],
  );

  if (!metrics.fail_datetime || metrics.fail_datetime.length === 0) {
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
    <>
      <CommonChart
        type="line"
        chartConfig={chartConfig}
        chartData={chartData}
        xAxisProps={{
          dataKey: 'name',
          tick: (props) => <CustomizedAxisTick {...props} />,
          height: 50,
        }}
        yAxisProps={{
          domain: [0, 'dataMax'],
          allowDecimals: false,
          label: {
            angle: -90,
            position: 'insideLeft',
            style: { textAnchor: 'middle' },
            dx: -10,
          },
          scale: logScale,
        }}
        cartesianGrid={{
          horizontal: showGrid,
        }}
        tooltipContentProps={{
          indicator: 'dot',
        }}
        config={lineConfig}
        showLegend={false}
      />
    </>
  );
}
