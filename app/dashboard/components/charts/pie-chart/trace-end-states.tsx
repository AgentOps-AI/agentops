'use client';

import { CommonChart } from '@/components/charts/common-chart';
import { ChartConfig } from '@/components/ui/chart';
import { ProjectMetrics } from '@/lib/interfaces';
import { firstLineShadowEffect } from '@/utils/common.utils';
import { memo, useMemo, useState, useRef, useCallback } from 'react';
import { Cell, Label, PieProps } from 'recharts';

function InnerShadowFilter({ id = 'inner-shadow' }: { id?: string }) {
  return (
    <svg width="0" height="0">
      <defs>
        <filter id={id} x="-50%" y="-50%" width="200%" height="200%">
          <feComponentTransfer in="SourceAlpha">
            <feFuncA type="table" tableValues="1 0" />
          </feComponentTransfer>
          <feGaussianBlur stdDeviation="3" />
          <feOffset dx="3" dy="3" result="offsetblur" />
          <feFlood floodColor="rgba(0, 0, 0, 0.2)" result="color" />
          <feComposite in2="offsetblur" operator="in" />
          <feComposite in2="SourceAlpha" operator="in" />
          <feMerge>
            <feMergeNode in="SourceGraphic" />
            <feMergeNode />
          </feMerge>
        </filter>
      </defs>
    </svg>
  );
}

const chartConfig: ChartConfig = {
  Success: {
    label: 'Success',
    color: 'hsl(var(--chart-1))',
  },
  Indeterminate: {
    label: 'Indeterminate',
    color: '#E1E2F2',
  },
  Fail: {
    label: 'Fail',
    color: 'hsl(var(--chart-error))',
  },
};

function TraceEndStatesPieChartComponent({ metrics }: { metrics: ProjectMetrics }) {
  const [shadowsVisible, setShadowsVisible] = useState(false);
  const animationEndedOnce = useRef(false);

  const chartData = useMemo(() => {
    const counts = {
      Success: metrics.span_count.success,
      Indeterminate: metrics.span_count.unknown,
      Fail: metrics.span_count.fail,
    };

    return Object.entries(counts).map(([state, count]) => ({
      state,
      count,
    }));
  }, [metrics]);

  const totalSessions = useMemo(() => {
    return chartData.reduce((acc, curr) => acc + curr.count, 0);
  }, [chartData]);

  const handleAnimationEnd = useCallback(() => {
    if (!animationEndedOnce.current) {
      setShadowsVisible(true);
      animationEndedOnce.current = true;
    }
  }, []);

  const getFilter = useCallback(
    (state: string) => {
      if (!shadowsVisible) return undefined;
      if (state === 'Indeterminate') return 'url(#inner-shadow)';
      if (state === 'Fail') return firstLineShadowEffect;
      return firstLineShadowEffect;
    },
    [shadowsVisible],
  );

  const pieSpecificConfig: PieProps[] = useMemo(
    () => [
      {
        data: chartData,
        dataKey: 'count',
        key: 'count',
        nameKey: 'state',
        innerRadius: 85,
        outerRadius: 100,
        strokeWidth: 5,
        paddingAngle: 4,
        cornerRadius: 3,
        onAnimationEnd: handleAnimationEnd,
        children: (
          <>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={chartConfig[entry.state as keyof typeof chartConfig].color}
                filter={getFilter(entry.state)}
              />
            ))}
            <Label
              content={({ viewBox }) => {
                if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                  return (
                    <text
                      x={viewBox.cx}
                      y={viewBox.cy}
                      textAnchor="middle"
                      dominantBaseline="middle"
                    >
                      <tspan
                        x={viewBox.cx}
                        y={viewBox.cy}
                        className="fill-foreground text-3xl font-bold"
                      >
                        {totalSessions.toLocaleString()}
                      </tspan>
                      <tspan
                        x={viewBox.cx}
                        y={(viewBox.cy || 0) + 24}
                        className="fill-muted-foreground"
                      >
                        Spans
                      </tspan>
                    </text>
                  );
                }
              }}
            />
          </>
        ),
      },
    ],
    [chartData, getFilter, handleAnimationEnd, totalSessions],
  );

  if (metrics.span_count.total === 0) {
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
    <div>
      <InnerShadowFilter id="inner-shadow" />
      <CommonChart
        type="pie"
        chartData={chartData}
        chartConfig={chartConfig}
        tooltipContentProps={{
          indicator: 'dot',
        }}
        config={pieSpecificConfig}
        chartContainerClassName="h-[300px]"
      />
    </div>
  );
}

export const TraceEndStatesPieChart = memo(TraceEndStatesPieChartComponent);
