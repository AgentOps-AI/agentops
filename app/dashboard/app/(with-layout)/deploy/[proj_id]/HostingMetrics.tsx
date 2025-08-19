import React, { useMemo } from 'react';
import { useMetrics } from '@/hooks/useMetrics';
import { CommonChart } from '@/components/charts/common-chart';

const latencyChartConfig = {
  latency: {
    label: 'Latency (ms)',
    color: 'hsl(var(--chart-2))',
  },
};

export default function HostingMetrics() {
  const { metrics, metricsLoading } = useMetrics();

  // Fake latency line chart data
  const latencyData = [
    { name: 'Mon', latency: 120 },
    { name: 'Tue', latency: 110 },
    { name: 'Wed', latency: 140 },
    { name: 'Thu', latency: 100 },
    { name: 'Fri', latency: 130 },
    { name: 'Sat', latency: 90 },
    { name: 'Sun', latency: 105 },
  ];

  return (
    <div className="border border-[rgba(222,224,244,1)] rounded-lg p-6 bg-white">
      <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-3">Hosting Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Trace Count Stat */}
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">Trace Count</div>
          <div className="text-[48px] font-bold text-[rgba(20,27,52,1)] leading-none">
            {metricsLoading ? <span className="animate-pulse">...</span> : metrics?.trace_count ?? '--'}
          </div>
        </div>
        {/* Latency Line Chart */}
        <div>
          <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">Latency (ms)</div>
          <CommonChart
            type="line"
            chartData={latencyData}
            chartConfig={latencyChartConfig}
            config={[{ dataKey: 'latency', type: 'monotone', stroke: 'hsl(var(--chart-2))', strokeWidth: 2, dot: true }]}
            xAxisProps={{ dataKey: 'name', fontSize: 12, tickLine: false, axisLine: false, height: 30 }}
            yAxisProps={{ allowDecimals: false, domain: [0, 'dataMax'] }}
            showLegend={false}
          />
        </div>
      </div>
    </div>
  );
} 