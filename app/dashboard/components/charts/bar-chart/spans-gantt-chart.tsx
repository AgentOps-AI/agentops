'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Rectangle,
} from 'recharts';

import { ISpan } from '@/types/ISpan';
import React, { useState, useMemo, useEffect } from 'react';
import { ChartCard } from '@/components/ui/chart-card';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { formatTimeInSeconds } from '@/lib/number_formatting_utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SpanTypeColorMap, spanTypeColors } from '@/app/lib/span-colors';
import {
  ProcessedSpan,
  processSpan,
  createFillerSpans,
  getDisplayTypes,
  calculateLatestSpanEnd,
  createFallbackSpan,
} from './span-processing';
import { extractAG2ToolName } from '@/utils/ag2.utils';

const CustomizedAxisTick = ({
  x,
  y,
  payload,
  totalDuration,
  traceStartTimeMs,
}: {
  x: number;
  y: number;
  payload: {
    value: number;
  };
  totalDuration: number;
  traceStartTimeMs: number;
}) => {
  if (payload.value !== 0 && Math.abs(payload.value - totalDuration) > 1) return null;
  if (payload.value === 0 && x < 10) x = 15;
  const formattedTime = formatTimeInSeconds(payload.value);
  const timestamp = new Date(traceStartTimeMs + payload.value).toLocaleTimeString();

  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={16} textAnchor="middle" fill="#64748B" fontSize={10} fontWeight="bold">
        {formattedTime}
      </text>
      <text
        x={payload.value === 0 ? -14 : 14}
        y={10}
        dy={16}
        textAnchor={payload.value === 0 ? 'start' : 'end'}
        fill="#64748B"
        fontSize={10}
        fontWeight="bold"
      >
        {timestamp}
      </text>
    </g>
  );
};

const CustomTooltip = ({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ProcessedSpan }>;
}) => {
  if (active && payload && payload.length) {
    const span = payload[0].payload.originalSpan;
    if (!span || payload[0].payload.isFiller) {
      return null;
    }
    const spanAttributes = span?.span_attributes?.gen_ai;
    return (
      <div
        className={cn(
          'grid min-w-[20rem] items-start gap-1.5 rounded-lg border border-slate-200/50 border-t-white bg-white px-4 py-2.5 text-xs shadow-2xl dark:border-slate-800 dark:border-slate-800/50 dark:bg-slate-950',
        )}
      >
        <div className="flex items-center">
          <div
            className="mr-2 h-6 w-4 rounded-sm"
            style={{
              backgroundColor:
                spanTypeColors[span.span_type as keyof typeof spanTypeColors]?.bg ||
                spanTypeColors.default.bg,
            }}
          />
          <h2 className="mr-4 text-[14px] font-normal">
            {(() => {
              // Check for AG2-specific tool name
              const ag2ToolName = extractAG2ToolName(span);
              if (ag2ToolName) {
                return ag2ToolName;
              }
              return span.span_name.substring(0, 38) + '...';
            })()}
          </h2>
          <p className="text-[14px] font-semibold">{span.service_name}</p>
        </div>
        <Separator />
        <h4 className="text-sm font-semibold">Timings:</h4>
        <p className="flex items-start justify-between text-sm">
          Duration: <span className="text-gray-500">{payload[0].payload.duration}ms</span>
        </p>
        <p className="flex items-start justify-between text-sm">
          Start - End:{' '}
          <span className="text-gray-500">
            {new Date(span.start_time).toLocaleTimeString()} -{' '}
            {new Date(span.end_time).toLocaleTimeString()}
          </span>
        </p>
        {spanAttributes?.usage && (
          <>
            <h4 className="text-sm font-semibold">Usage:</h4>
            <p className="text-sm">Prompt tokens: {spanAttributes.usage.prompt_tokens}</p>
            <p className="text-sm">Completion tokens: {spanAttributes.usage.completion_tokens}</p>
            <p className="text-sm">
              Total tokens:{' '}
              {Number(spanAttributes.usage.prompt_tokens) +
                Number(spanAttributes.usage.completion_tokens)}
            </p>
          </>
        )}
        <h4 className="text-sm font-semibold">ETC:</h4>
        <p className="text-sm text-gray-500">ID: {span.span_id.substring(0, 8)}...</p>
        <p className="text-sm">Type: {span.span_type}</p>
      </div>
    );
  }
  return null;
};

const CustomEmptyTt = () => {
  return null;
};

const SpanTypeFilters = ({
  spanTypes,
  hiddenTypes,
  toggleType,
  availableTypes,
}: {
  spanTypes: SpanTypeColorMap;
  hiddenTypes: Set<string>;
  toggleType: (type: string) => void;
  availableTypes: Set<string>;
}) => {
  // Get display types using the helper function
  const displayTypes = getDisplayTypes(availableTypes);

  return (
    <div className="mx-auto grid w-full max-w-3xl grid-cols-4 gap-2 px-2 md:grid-cols-5">
      {displayTypes.map(
        (type, i) =>
          type !== 'default' &&
          spanTypes[type] && (
            <div
              key={`${type}-${i}`}
              className="flex cursor-pointer items-center justify-center rounded-md border border-slate-100 bg-white px-2 py-1 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
              onClick={() => toggleType(type)}
            >
              <div
                className="mr-1.5 h-3 w-3 rounded-full"
                style={{
                  backgroundColor: spanTypes[type].bg,
                  border: `1px solid ${spanTypes[type].border}`,
                  opacity: hiddenTypes.has(type) ? 0.5 : 1,
                }}
              />
              <span
                className={`text-xs font-medium ${hiddenTypes.has(type) ? 'text-slate-400 dark:text-slate-500' : 'dark:text-slate-300'}`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </span>
            </div>
          ),
      )}
    </div>
  );
};

interface SpansGanttChartProps {
  data: ISpan[];
  traceStartTimeMs: number;
  selectedSpanId: string | null;
  onSpanSelect: (span: ISpan | null) => void;
  withScrollArea?: boolean;
}

const CustomBarShape = (props: {
  fill: string;
  stroke: string;
  strokeWidth: number;
  radius: number | [number, number, number, number];
  spanId?: string;
  previewText?: string;
  showBarText?: boolean;
  isDarkMode?: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  className?: string;
  [key: string]: any;
}) => {
  const {
    fill,
    stroke,
    strokeWidth,
    radius,
    spanId,
    previewText,
    showBarText,
    isDarkMode,
    x,
    y,
    width,
    height,
    className,
  } = props;

  const PADDING_PIXELS_INSIDE_BAR = 20;
  const textColor = isDarkMode ? 'rgba(225, 226, 242, 1)' : 'rgba(1, 27, 52, 0.85)';
  const shadowId = `shadow-${spanId || 'default'}`;
  const MAX_CHARS_OUTSIDE_BAR = 40; // Maximum characters for text outside bars (reduced from 50)

  const calcPreviewTextX = (width: number, x: number, text: string) => {
    const estimatedCharWidth = 10 * 0.4; // font size * font/pixel ratio
    const textPixelWidth = text.length * estimatedCharWidth;
    const availableWidth = width - PADDING_PIXELS_INSIDE_BAR * 2;

    // Only place text inside if the FULL text fits within the bar with padding
    if (width > 200 && textPixelWidth <= availableWidth) {
      // Text fits inside the bar
      return {
        x: x + PADDING_PIXELS_INSIDE_BAR / 2,
        text: text,
      };
    } else {
      // Text goes outside the bar - truncate if too long
      let displayText = text;
      if (text.length > MAX_CHARS_OUTSIDE_BAR) {
        displayText = text.substring(0, MAX_CHARS_OUTSIDE_BAR - 3) + '...';
      }

      return {
        x: x + width + PADDING_PIXELS_INSIDE_BAR / 2,
        text: displayText,
      };
    }
  };

  return (
    <g>
      <defs>
        <filter id={shadowId} x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="2" dy="2" stdDeviation="2" floodColor="rgba(0,0,0,0.3)" />
        </filter>
      </defs>
      <Rectangle
        {...props}
        data-testid={spanId ? `trace-detail-span-item-${spanId}` : 'trace-detail-span-item-unknown'}
        radius={radius}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeWidth}
        filter={`url(#${shadowId})`}
        className={className}
      />
      {showBarText && previewText && width > 1 && (
        <text
          x={calcPreviewTextX(width, x, previewText).x}
          y={y + height / 2}
          dy=".35em"
          fill={textColor}
          fontSize="10"
          fontWeight="normal"
          textAnchor="start"
          style={{ pointerEvents: 'none' }}
        >
          {calcPreviewTextX(width, x, previewText).text}
        </text>
      )}
    </g>
  );
};

export function SpansGanttChart({
  data,
  traceStartTimeMs,
  selectedSpanId,
  onSpanSelect,
}: SpansGanttChartProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showBarText, setShowBarText] = useState(true);
  const [focusBar, setFocusBar] = useState<number | null>(null);
  const [_mouseLeave, setMouseLeave] = useState(true);
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const [reactiveIsDarkMode, setReactiveIsDarkMode] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Set initial state
    setReactiveIsDarkMode(document.documentElement.classList.contains('dark'));

    const observer = new MutationObserver((mutationsList) => {
      for (const mutation of mutationsList) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
          setReactiveIsDarkMode(document.documentElement.classList.contains('dark'));
        }
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    return () => {
      observer.disconnect();
    };
  }, []); // Run once on mount to set up observer

  const processedData = useMemo(() => {
    const mapped = data.map((span: ISpan, index: number) =>
      processSpan(span, index, traceStartTimeMs),
    );

    mapped.sort((a, b) => a.start - b.start);
    const fillerSpans = createFillerSpans(mapped, 10);

    return [...mapped, ...fillerSpans];
  }, [data, traceStartTimeMs]);

  const latestSpanEnd = useMemo(() => calculateLatestSpanEnd(processedData), [processedData]);
  const totalTraceDuration = Math.max(1, latestSpanEnd);
  const extendedDomain = useMemo(() => {
    const extraSpace = totalTraceDuration * 0.25;
    return totalTraceDuration + extraSpace;
  }, [totalTraceDuration]);

  const handleBarClick = (barData: ProcessedSpan, _index: number) => {
    const clickedSpan = barData?.originalSpan;
    if (clickedSpan) {
      if (selectedSpanId === clickedSpan.span_id) {
        onSpanSelect(null);
      } else {
        onSpanSelect(clickedSpan);
      }
    }
  };

  const toggleBarType = (type: string) => {
    setHiddenTypes((prev) => {
      const newHiddenTypes = new Set(prev);
      newHiddenTypes.has(type) ? newHiddenTypes.delete(type) : newHiddenTypes.add(type);
      return newHiddenTypes;
    });
  };

  const filteredData = useMemo(() => {
    const filtered = processedData.filter(
      (entry) => entry.isFiller || !hiddenTypes.has(entry.type),
    );

    // If all span types are filtered out, return a dummy entry to prevent chart crashes
    if (filtered.length === 0) {
      return [createFallbackSpan()];
    }

    return filtered;
  }, [processedData, hiddenTypes]);

  const handleMouseMove = (state: {
    isTooltipActive?: boolean;
    activeTooltipIndex?: number | null;
  }) => {
    if (state.isTooltipActive) {
      setFocusBar(state?.activeTooltipIndex ?? null);
      setMouseLeave(false);
    } else {
      setFocusBar(null);
      setMouseLeave(true);
    }
  };

  const scrollbarStyles = {
    scrollbarWidth: 'thin' as const,
    scrollbarColor: 'rgba(156, 163, 175, 0.3) transparent',
  };

  const ScrollableBarsChart = (
    <ScrollArea
      className="flex-1 overflow-y-auto [&::-webkit-scrollbar-thumb:hover]:bg-gray-300/50 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-gray-300/30 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:w-[4px]"
      style={scrollbarStyles}
    >
      <div style={{ minHeight: '140px' }}>
        <ResponsiveContainer width="100%" height={Math.max(filteredData.length * 30, 140)}>
          <BarChart
            layout="vertical"
            data={filteredData}
            margin={{ top: 5, right: 10, left: 4, bottom: 5 }}
            barCategoryGap={2}
            barGap={0}
            onMouseMove={handleMouseMove}
          >
            <XAxis type="number" domain={[0, extendedDomain]} allowDataOverflow={true} hide />
            <YAxis
              type="category"
              dataKey="name"
              width={0}
              tick={false}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={false}
              active={showTooltip}
              wrapperStyle={{ backgroundColor: 'transparent', zIndex: 100 }}
              content={showTooltip ? <CustomTooltip /> : <CustomEmptyTt />}
            />
            <Bar
              dataKey="value"
              onClick={handleBarClick}
              maxBarSize={20}
              minPointSize={20}
              className="cursor-pointer"
              radius={5}
              shape={(props: any) => {
                const index = props.index as number | undefined;
                if (index === undefined || index < 0 || index >= filteredData.length) {
                  return <CustomBarShape {...props} key={index} fill="transparent" stroke="none" />;
                }
                const entry = filteredData[index] as ProcessedSpan;
                if (!entry) {
                  return <CustomBarShape {...props} key={index} fill="transparent" stroke="none" />;
                }
                if (entry.isFiller) {
                  return <CustomBarShape {...props} key={index} fill="transparent" stroke="none" />;
                }
                const isHighlighted = focusBar === index || selectedSpanId === entry.id;
                const colors =
                  spanTypeColors[entry.type as keyof typeof spanTypeColors] ||
                  spanTypeColors.default;
                const shapeProps = {
                  ...props,
                  fill: colors.bg,
                  stroke: isHighlighted ? colors.selectedBorder : colors.border,
                  strokeWidth: isHighlighted ? 3 : 1,
                  strokeOpacity: isHighlighted ? 0.8 : 1,
                  radius: 5,
                  spanId: entry.id,
                  previewText: entry.previewText,
                  showBarText: showBarText,
                  isDarkMode: reactiveIsDarkMode,
                };
                return <CustomBarShape {...shapeProps} key={index} />;
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ScrollArea>
  );

  /**
   * This is hackery.
   * We need to have a fixed height for the XAxis chart so that the bars don't shift when the tooltip is active.
   * https://github.com/recharts/recharts/issues/1364#issuecomment-2608588147
   * but its quality hackery I redid for the opposite axis as the comment.
   */
  const FixedXAxisChart = (
    <div
      className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700"
      style={{ height: '60px' }}
    >
      <ResponsiveContainer width="100%" height={60}>
        <BarChart data={filteredData} margin={{ top: 15, right: 10, left: 2, bottom: 5 }}>
          <CartesianGrid vertical stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            type="number"
            domain={[0, extendedDomain]}
            allowDataOverflow={true}
            tickCount={10}
            ticks={[0, totalTraceDuration]}
            tickFormatter={(value) => formatTimeInSeconds(value)}
            padding={{ left: 30, right: 10 }}
            tick={(props: any) => (
              <CustomizedAxisTick
                {...props}
                totalDuration={totalTraceDuration}
                traceStartTimeMs={traceStartTimeMs}
              />
            )}
            orientation="bottom"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const FiltersSection = (
    <div className="flex-shrink-0 rounded-md border-gray-200 py-2 dark:border-gray-700">
      <SpanTypeFilters
        spanTypes={spanTypeColors}
        hiddenTypes={hiddenTypes}
        toggleType={toggleBarType}
        availableTypes={
          new Set(processedData.filter((span) => !span.isFiller).map((span) => span.type))
        }
      />
    </div>
  );

  const TogglesSection = (
    <div className="absolute bottom-20 left-4 z-[99] rounded-md border border-slate-200 bg-white px-2 py-1 shadow-md dark:border-slate-700 dark:bg-slate-800 dark:shadow-slate-900/50">
      <div className="flex flex-col gap-y-1">
        <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-900 dark:text-slate-300">
          <Checkbox checked={showBarText} onCheckedChange={() => setShowBarText(!showBarText)} />
          Show Bar Text
        </label>
        <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-900 dark:text-slate-300">
          <Checkbox checked={showTooltip} onCheckedChange={() => setShowTooltip(!showTooltip)} />
          Show tooltip
        </label>
      </div>
    </div>
  );

  const chartContent = (
    <div className="relative flex h-full flex-col">
      {FiltersSection}
      <div
        className="flex-1 overflow-x-auto overflow-y-hidden [&::-webkit-scrollbar-thumb:hover]:bg-gray-300/50 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-gray-300/30 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:h-[4px]"
        style={scrollbarStyles}
      >
        <div className="flex h-full min-w-[800px] flex-col">
          {ScrollableBarsChart}
          {FixedXAxisChart}
        </div>
      </div>
      {TogglesSection}
    </div>
  );

  return (
    <ChartCard
      containerStyles="relative z-[1] h-full flex flex-col"
      cardStyles="shadow-xl sm:p-0 flex flex-col h-full overflow-hidden"
      cardHeaderStyles="mb-0 p-2 pb-0 pt-0"
      cardContentStyles="h-full overflow-hidden"
    >
      {chartContent}
    </ChartCard>
  );
}
