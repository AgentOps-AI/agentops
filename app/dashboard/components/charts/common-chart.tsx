'use client';

import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  ChartTooltipContentProps,
} from '@/components/ui/chart';
import { cn } from '@/lib/utils';
import { CSSProperties, PropsWithChildren, ReactElement, useMemo } from 'react';
import {
  Bar,
  BarChart,
  BarProps,
  CartesianGrid,
  CartesianGridProps,
  Legend,
  Line,
  LineChart,
  LineProps,
  Pie,
  PieChart,
  PieProps,
  ResponsiveContainer,
  XAxis,
  XAxisProps,
  YAxis,
  YAxisProps,
} from 'recharts';
import { CategoricalChartProps } from 'recharts/types/chart/generateCategoricalChart';
import EmptyDashboard from '../ui/empty-dashboard';
import { Skeleton } from '@/components/ui/skeleton';
interface CommonChartProps<T = any> {
  chartData: T[];
  chartConfig: ChartConfig;
  chartContainerClassName?: string;
  xAxisProps?: XAxisProps;
  yAxisProps?: YAxisProps;
  cartesianGrid?: CartesianGridProps;
  chartProps?: CategoricalChartProps;
  tooltipContentProps?: ChartTooltipContentProps;
  type: ChartType;
  config: (
    | PropsWithChildren<LineProps>
    | PropsWithChildren<BarProps>
    | PropsWithChildren<PieProps>
  )[];
  legend?: ReactElement;
  showLegend?: boolean;
  showTooltip?: boolean;
  chartContainerStyles?: CSSProperties;
  onChartDataClick?: (data: T) => void;
  horizontalEmptyState?: boolean;
  subTitle?: string;
  isLoading?: boolean;
}

type ChartType = 'bar' | 'line' | 'pie';

// Extract reusable chart element creators
const createChartElement = {
  line: (props: LineProps, key: React.Key, children: React.ReactNode) => (
    <Line {...props} ref={null} key={key} isAnimationActive>
      {children}
    </Line>
  ),
  pie: (props: PieProps, key: React.Key, children: React.ReactNode) => {
    return (
      <Pie {...props} ref={null} key={key} isAnimationActive>
        {
          //@ts-expect-error in version 2.15.0 children is moved to props.children
          children.props.children
        }
      </Pie>
    );
  },
  bar: (
    props: BarProps,
    key: React.Key,
    children: React.ReactNode,
    onClick?: (data: any) => void,
  ) => (
    <Bar {...props} ref={null} onClick={onClick} key={key} isAnimationActive>
      {children}
    </Bar>
  ),
};

export function CommonChart<T>({
  chartData,
  chartConfig,
  chartContainerStyles,
  xAxisProps = {},
  yAxisProps = {},
  cartesianGrid = {},
  chartProps = {},
  type = 'bar',
  config,
  legend,
  tooltipContentProps,
  showLegend = true,
  showTooltip = true,
  chartContainerClassName,
  onChartDataClick,
  horizontalEmptyState = false,
  subTitle,
  isLoading = false,
}: CommonChartProps<T>) {
  const containerClassName = useMemo(
    () => cn('aspect-auto h-[250px] w-full transition-all duration-300', chartContainerClassName),
    [chartContainerClassName],
  );

  const chartElements = useMemo(() => {
    return config.map(({ children, key, ...props }, i) => {
      const elementKey = key ?? i;
      return createChartElement[type](props as any, elementKey, children, onChartDataClick);
    });
  }, [config, type, onChartDataClick]);

  const legendElement = useMemo(() => {
    if (!showLegend) return null;
    return legend ? <Legend content={legend} /> : <ChartLegend content={<ChartLegendContent />} />;
  }, [showLegend, legend]);

  const tooltipElement = useMemo(() => {
    if (!showTooltip) return null;
    return (
      <ChartTooltip cursor={true} content={<ChartTooltipContent {...tooltipContentProps} />} />
    );
  }, [showTooltip, tooltipContentProps]);

  if (isLoading) {
    return (
      <ChartContainer
        config={chartConfig}
        className={containerClassName}
        style={chartContainerStyles}
      >
        <div className="flex h-full w-full items-center justify-center">
          <Skeleton className="h-full w-full animate-pulse bg-white/50" />
        </div>
      </ChartContainer>
    );
  }

  if (!chartData?.length) {
    return (
      <ChartContainer
        config={chartConfig}
        className={containerClassName}
        style={chartContainerStyles}
      >
        <EmptyDashboard
          showIcon={false}
          className="h-full text-base"
          horizontal={horizontalEmptyState}
          subTitle={subTitle}
        />
      </ChartContainer>
    );
  }

  return (
    <ChartContainer
      config={chartConfig}
      className={containerClassName}
      style={chartContainerStyles}
    >
      {type === 'line' && (
        <ResponsiveContainer width="100%" height="100%" minHeight={100} minWidth={300}>
          <LineChart data={chartData} {...chartProps}>
            <CartesianGrid vertical={false} {...cartesianGrid} />
            <YAxis {...yAxisProps} tickLine={false} axisLine={false} tickMargin={20} />
            <XAxis tickLine={false} axisLine={false} tickMargin={8} {...xAxisProps} />
            {/* {cartesianElements()} */}
            {tooltipElement}
            {legendElement}
            {chartElements}
          </LineChart>
        </ResponsiveContainer>
      )}

      {type === 'bar' && (
        <ResponsiveContainer width="100%" height="100%" minHeight={100} minWidth={300}>
          <BarChart data={chartData} {...chartProps}>
            <CartesianGrid vertical={false} {...cartesianGrid} />
            <YAxis {...yAxisProps} tickLine={false} axisLine={false} tickMargin={20} />
            <XAxis tickLine={false} axisLine={false} tickMargin={8} {...xAxisProps} />
            {tooltipElement}
            {legendElement}
            {chartElements}
          </BarChart>
        </ResponsiveContainer>
      )}

      {type === 'pie' && (
        <ResponsiveContainer width="100%" height="100%" minHeight={100} minWidth={300}>
          <PieChart data={chartData} {...chartProps}>
            {tooltipElement}
            {legendElement}
            {chartElements}
          </PieChart>
        </ResponsiveContainer>
      )}

      {/* 
        <ChartComponent
          accessibilityLayer
          data={chartData}
          margin={{
            left: 12,
            right: 12,
            top: 12,
          }}
          {...chartProps}
        >
          {type !== 'pie' && (
            <>
              <CartesianGrid vertical={false} {...cartesianGrid} />
            </>
          )}
          {cartesianElements()}
          {tooltipElement}
          {legendElement}
          {chartElements}
        </ChartComponent>
*/}
    </ChartContainer>
  );
}
