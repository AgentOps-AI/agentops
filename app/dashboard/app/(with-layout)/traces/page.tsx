'use client';

import { Suspense, useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
  VisibilityState,
  Row,
  HeaderGroup,
  Header,
  Cell,
  Column,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useTraces } from '@/hooks/useTraces';
import { Pagination } from '@/components/ui/trace-selector/components/pagination';
import { useHeaderContext } from '@/app/providers/header-provider';
import { ChartCard } from '@/components/ui/chart-card';
import { cardTitleStyles, cardHeaderStyles } from '@/constants/styles';
import { DateRange } from 'react-day-picker';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import ProjectSelector from '@/components/ui/project-selector';
import { useProject } from '@/app/providers/project-provider';
import { useMetrics } from '@/hooks/useMetrics';
import { useProjects } from '@/hooks/queries/useProjects';
import { useOrgFeatures, isFreeUser, LIMITS } from '@/hooks/useOrgFeatures';
import { ColumnHeader } from '@/components/ui/trace-selector/components/column-header';
import { StatSkeleton, TraceSkeletonRow } from '@/components/ui/skeletons';
import { TraceToolbar } from '@/components/ui/trace-selector/components/trace-toolbar';
import { formatDate, formatMetric, formatPercentage } from '@/lib/utils';
import { FormattedTokenDisplay } from '@/components/ui/formatted-token-display';
import { formatMilliseconds } from '@/lib/number_formatting_utils';
import { BillingCostTooltip } from '@/components/ui/billing-cost-tooltip';
import { ITrace } from '@/types/ITrace';
import Logo from '@/components/icons/Logo';
import { TraceDrilldownDrawer } from '@/app/(with-layout)/traces/_components/trace-drilldown-drawer';
import { cn } from '@/lib/utils';
import { debounce } from 'lodash';
import { Tags } from '@/components/ui/tags';
import { startOfMonth, endOfMonth } from 'date-fns';
import { PremiumUpsellBanner } from '@/components/ui/premium-upsell-banner';
import { getIconForModel } from '@/lib/modelUtils';
import React from 'react';
import { Clock03Icon } from 'hugeicons-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { NoTracesFound } from '@/components/ui/no-traces-found';
import { useBookmarks } from '@/hooks/useBookmarks';
import { BookmarkButton } from '@/components/ui/bookmark-button';
interface TableHeaderProps<TData> {
  headerGroup: HeaderGroup<TData>;
}

interface TableCellProps<TData> {
  cell: Cell<TData, unknown>;
  index: number;
  row: Row<TData>;
}

interface TableRowProps<TData> {
  row: Row<TData>;
  onClick: (row: Row<TData>) => void;
  tableRowRefs: React.MutableRefObject<Record<number, HTMLTableRowElement | null>>;
}

const COLUMN_SIZES = {
  bookmark: 36,
  name: 300,
  timestamp: 200,
  status: 120,
  duration: 160,
  cost: 120,
  spans: 140,
  errors: 90,
  tags: 200,
} as const;

const TABLE_WIDTH = Object.values(COLUMN_SIZES).reduce((sum, size) => sum + size, 0);

function boldMatch(text: string, search: string): React.ReactNode {
  if (!search) return text;
  const regex = new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig');
  return text.split(regex).map((part, i) => (regex.test(part) ? <b key={i}>{part}</b> : part));
}

export default function SessionDrillDowns() {
  const [selectedTrace, setSelectedTrace] = useState<ITrace | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({ 'delete?': false });
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [inputValue, setInputValue] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showBookmarkedOnly, setShowBookmarkedOnly] = useState(false);

  const { setHeaderTitle, setHeaderContent } = useHeaderContext();
  const { isBookmarked, toggleBookmark, bookmarks } = useBookmarks();

  const router = useRouter();
  const { sharedDateRange, setSharedDateRange, selectedProject, setSelectedProject } = useProject();

  const searchParams = useSearchParams();
  const { premStatus, isLoading: isPermissionsLoading } = useOrgFeatures();

  const { data: projects, isLoading: projectsLoading } = useProjects();

  const { columns } = TracesColumns(inputValue, isBookmarked, toggleBookmark);

  const [paginationState, setPaginationState] = useState({
    pageIndex: 0,
    pageSize: 20,
  });

  const { pageIndex, pageSize } = paginationState;

  const {
    data: tracesData,
    refetchTraces,
    isLoading,
    isFetching,
  } = useTraces(sharedDateRange, searchQuery, pageIndex, pageSize);

  const { metrics, metricsLoading, refreshMetrics } = useMetrics(sharedDateRange);

  const currentMonthRange = {
    from: startOfMonth(new Date()),
    to: endOfMonth(new Date()),
  };
  const { metrics: monthlyMetrics, metricsLoading: monthlyMetricsLoading } =
    useMetrics(currentMonthRange);

  const isSpanLimitExceeded = useMemo(() => {
    if (isPermissionsLoading || !monthlyMetrics || monthlyMetricsLoading) {
      return false;
    }

    const isFree = !premStatus || premStatus.toLowerCase() === 'free';
    if (!isFree) return false;

    const maxSpans = 10000;
    const currentSpans = monthlyMetrics.span_count?.total || 0;
    return currentSpans >= maxSpans;
  }, [premStatus, isPermissionsLoading, monthlyMetrics, monthlyMetricsLoading]);

  const currentTraceId = searchParams.get('trace_id');
  const tableRowRefs = useRef<Record<number, HTMLTableRowElement | null>>({});

  const debouncedSetSearchQuery = useCallback(
    debounce((value: string) => {
      setSearchQuery(value);
    }, 340),
    [],
  );

  useEffect(() => {
    return () => {
      debouncedSetSearchQuery.cancel?.();
    };
  }, [debouncedSetSearchQuery]);

  const handleInputChange = (value: string) => {
    setInputValue(value);
    debouncedSetSearchQuery(value);
  };

  const handleToggleBookmarkedFilter = () => {
    setShowBookmarkedOnly(!showBookmarkedOnly);
    // Reset to first page when toggling filter
    setPaginationState((prev) => ({ ...prev, pageIndex: 0 }));
  };

  const handleDateApply = useCallback(
    (newRange: DateRange) => {
      setSharedDateRange(newRange);
    },
    [setSharedDateRange],
  );

  const handleRowClick = useCallback(
    (row: Row<ITrace>) => {
      if (isSpanLimitExceeded && (!premStatus || premStatus.toLowerCase() === 'free')) {
        router.push('/settings/organization');
        return;
      }

      try {
        const traceId = row.original?.trace_id;
        if (traceId) {
          const current = new URLSearchParams(Array.from(searchParams.entries()));
          current.set('trace_id', traceId);
          const search = current.toString();
          router.replace(`?${search}`, { scroll: false });
          setSelectedTrace(row.original);
        } else {
          console.error('No trace ID found:', row);
        }
      } catch (error) {
        console.error('Error handling row click:', error);
      }
    },
    [router, searchParams, setSelectedTrace, isSpanLimitExceeded, premStatus],
  );

  useEffect(() => {
    if (currentTraceId) {
      const traceFromCurrentPage = tracesData?.traces?.find((t) => t.trace_id === currentTraceId);
      if (traceFromCurrentPage) {
        setSelectedTrace(traceFromCurrentPage);
      } else {
        setSelectedTrace({ trace_id: currentTraceId } as ITrace);
      }
    } else {
      setSelectedTrace(null);
    }
  }, [currentTraceId, tracesData?.traces]);

  const columnData = TracesColumns(inputValue, isBookmarked, toggleBookmark);

  const filteredTraces = useMemo(() => {
    if (!showBookmarkedOnly || !tracesData?.traces) {
      return tracesData?.traces ?? [];
    }
    return tracesData.traces.filter((trace) => bookmarks.has(trace.trace_id));
  }, [tracesData?.traces, showBookmarkedOnly, bookmarks]);

  const paginatedFilteredTraces = useMemo(() => {
    if (!showBookmarkedOnly) {
      return filteredTraces;
    }
    const startIndex = pageIndex * pageSize;
    const endIndex = startIndex + pageSize;
    return filteredTraces.slice(startIndex, endIndex);
  }, [filteredTraces, showBookmarkedOnly, pageIndex, pageSize]);

  const totalTraces = showBookmarkedOnly ? filteredTraces.length : (tracesData?.total ?? 0);
  const pageCount = pageSize > 0 ? Math.ceil(totalTraces / pageSize) : 0;

  const table = useReactTable({
    data: paginatedFilteredTraces,
    columns: columnData.columns,
    pageCount: pageCount,
    state: {
      sorting,
      columnVisibility,
      columnFilters,
      pagination: paginationState,
    },
    onPaginationChange: setPaginationState,
    manualPagination: true,
    defaultColumn: {
      size: 100,
      minSize: 50,
      maxSize: 500,
    },
    enableRowSelection: true,
    enableMultiRowSelection: false,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  });

  useEffect(() => {
    setHeaderTitle('Traces');
    setHeaderContent(
      <div className="flex flex-nowrap items-center gap-1 sm:gap-2">
        <DateRangePicker
          wrapperClassNames="border-transparent"
          isRanged
          onApply={handleDateApply}
          defaultRange={sharedDateRange}
          noShadow
        />
        <ProjectSelector
          projects={projects}
          isLoading={projectsLoading}
          selectedProject={selectedProject}
          setSelectedProject={setSelectedProject}
          noShadow
        />
      </div>,
    );
  }, [
    setHeaderTitle,
    setHeaderContent,
    handleDateApply,
    sharedDateRange,
    projects,
    projectsLoading,
    selectedProject,
    setSelectedProject,
  ]);

  const TableHeaderRow = ({ headerGroup }: TableHeaderProps<ITrace>) => (
    <TableRow key={headerGroup.id} className="border-none">
      {headerGroup.headers.map((header: Header<ITrace, unknown>) => (
        <TableHead key={header.id} style={{ width: `${header.getSize()}px` }}>
          {header.isPlaceholder
            ? null
            : flexRender(header.column.columnDef.header, header.getContext())}
        </TableHead>
      ))}
    </TableRow>
  );

  const TableBodyRow = ({ row, onClick, tableRowRefs }: TableRowProps<ITrace>) => {
    return (
      <TableRow
        id={row.original.trace_id}
        key={row.id}
        data-state={row.getIsSelected() && 'selected'}
        data-testid="trace-list-row"
        className={cn(
          'cursor-pointer hover:rounded-xl hover:bg-[#E1E3F2] data-[state=selected]:rounded-xl data-[state=selected]:bg-[#E1E3F2] dark:hover:bg-slate-600 dark:data-[state=selected]:bg-slate-600',
        )}
        onClick={() => onClick(row)}
        ref={(el) => {
          tableRowRefs.current[row.index] = el;
        }}
      >
        {row.getVisibleCells().map((cell: Cell<ITrace, unknown>, index: number) => (
          <TableBodyCell key={cell.id + 'bc'} cell={cell} index={index} row={row} />
        ))}
      </TableRow>
    );
  };

  const TableBodyCell = ({ cell }: TableCellProps<ITrace>) => {
    return (
      <TableCell key={cell.id} style={{ width: `${cell.column.getSize()}px` }}>
        <div className="flex items-center gap-2">
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </div>
      </TableCell>
    );
  };

  const hasFilteredTokenMetrics = !!metrics?.token_metrics;

  const hasFreePlanTruncatedTraces = useMemo(() => {
    return tracesData?.traces?.some((trace) => trace.freeplan_truncated) || false;
  }, [tracesData?.traces]);

  return (
    <div className="flex flex-col gap-2 p-2">
      <div />
      <div className="mb-2 flex w-full flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="m-0 flex-shrink-0 text-2xl font-medium text-primary">Overall metrics</h2>
        {(hasFreePlanTruncatedTraces || (isSpanLimitExceeded && isFreeUser(premStatus))) && (
          <div className="flex w-full flex-shrink-0 justify-end lg:ml-4 lg:w-auto">
            <PremiumUpsellBanner
              title={
                isSpanLimitExceeded && hasFreePlanTruncatedTraces
                  ? 'Upgrade to unlock full access'
                  : isSpanLimitExceeded
                    ? 'Monthly span limit reached'
                    : `Showing last ${LIMITS.free.tracesLookbackDays} days`
              }
              messages={[
                ...(hasFreePlanTruncatedTraces
                  ? [
                      `Your current plan limits trace visibility to the last ${LIMITS.free.tracesLookbackDays} days. `,
                    ]
                  : []),
                ...(isSpanLimitExceeded && isFreeUser(premStatus)
                  ? [
                      `You've reached your monthly limit of ${LIMITS.free.maxSpansMonthly?.toLocaleString()} spans.${hasFreePlanTruncatedTraces ? ' Upgrade' : ' You cannot view new traces until next month or by upgrading'} to Pro for unlimited spans.`,
                    ]
                  : []),
              ]}
              ctaText={'View all with Pro'}
            />
          </div>
        )}
      </div>
      <div className="mb-2 grid gap-2 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4">
        <ChartCard
          tooltipContent={
            <BillingCostTooltip dateRange={sharedDateRange} projectId={selectedProject?.id} />
          }
          title={'Total Cost'}
          cardTitleStyles={cardTitleStyles}
          cardTitleTextStyles={'h-10'}
          cardHeaderStyles={cardHeaderStyles}
          cardStyles="shadow-sm h-24"
          cardContentStyles="p-0 pl-2"
        >
          {metricsLoading || !hasFilteredTokenMetrics ? (
            <StatSkeleton />
          ) : (
            <div className="flex items-center justify-between gap-10 text-xl font-semibold text-primary">
              <div className="flex items-center gap-2">
                <span>
                  {formatMetric(metrics.token_metrics.total_cost, {
                    prefix: '$',
                    defaultValue: 'N/A',
                  })}
                </span>
              </div>
            </div>
          )}
        </ChartCard>

        <ChartCard
          tooltipContent={'Tokens generated'}
          title={'Tokens generated'}
          cardTitleStyles={cardTitleStyles}
          cardTitleTextStyles={'h-10'}
          cardHeaderStyles={cardHeaderStyles}
          cardStyles="shadow-sm h-24"
          cardContentStyles="p-0 pl-2"
        >
          {metricsLoading || !hasFilteredTokenMetrics ? (
            <StatSkeleton />
          ) : (
            <div className="flex items-center justify-between gap-10 text-xl font-semibold text-primary">
              <div className="flex items-center gap-2">
                <FormattedTokenDisplay value={metrics.token_metrics.total_tokens?.all} />
              </div>
            </div>
          )}
        </ChartCard>

        <ChartCard
          tooltipContent={'Percentage failed'}
          title={'Fail Rate'}
          cardTitleStyles={cardTitleStyles}
          cardTitleTextStyles={'h-10'}
          cardHeaderStyles={cardHeaderStyles}
          cardStyles="shadow-sm h-24"
          cardContentStyles="p-0 pl-2"
        >
          {metricsLoading || !metrics ? (
            <StatSkeleton />
          ) : (
            <div className="flex items-center justify-between gap-10 text-xl font-semibold text-primary">
              <div className="flex items-center gap-2">
                <span>
                  {formatPercentage(
                    (metrics.fail_datetime?.length ?? 0) /
                      ((metrics.success_datetime?.length ?? 0) +
                        (metrics.fail_datetime?.length ?? 0)),
                  )}
                </span>
              </div>
            </div>
          )}
        </ChartCard>

        <ChartCard
          tooltipContent={'Total events from the project'}
          title={'Total Events'}
          cardTitleStyles={cardTitleStyles}
          cardTitleTextStyles={'h-10'}
          cardHeaderStyles={cardHeaderStyles}
          cardStyles="shadow-sm h-24"
          cardContentStyles="p-0 pl-2"
        >
          {metricsLoading || !metrics?.span_count ? (
            <StatSkeleton />
          ) : (
            <div className="flex items-center justify-between gap-10 text-xl font-semibold text-primary">
              <div className="flex items-center gap-2">
                <FormattedTokenDisplay value={metrics.span_count.total} />
              </div>
            </div>
          )}
        </ChartCard>
      </div>

      <Suspense fallback={<>Loading Table...</>}>
        <div
          className="rounded-md bg-white/50 p-4 shadow-xl dark:bg-slate-800/70 dark:shadow-none"
          data-testid="traces-list-container"
        >
          <TraceToolbar
            table={table}
            isRefreshing={isLoading || isFetching}
            refreshSessions={() => {
              refreshMetrics();
              refetchTraces();
            }}
            searchQuery={inputValue}
            onSearchChange={handleInputChange}
            showBookmarkedOnly={showBookmarkedOnly}
            onToggleBookmarkedFilter={handleToggleBookmarkedFilter}
          />
          <div className="overflow-x-auto">
            <div style={{ minWidth: `${TABLE_WIDTH}px`, maxWidth: `${TABLE_WIDTH}px` }}>
              <Table className="table-fixed">
                <TableHeader className="sticky top-0">
                  {table.getHeaderGroups().map((headerGroup: HeaderGroup<ITrace>) => (
                    <TableHeaderRow key={headerGroup.id} headerGroup={headerGroup} />
                  ))}
                </TableHeader>
                <TableBody
                  className={cn(
                    isFetching &&
                      !isLoading &&
                      'opacity-50 transition-opacity duration-150 ease-in-out',
                    isSpanLimitExceeded && isFreeUser(premStatus) && 'opacity-50',
                  )}
                >
                  {isLoading || tracesData === undefined ? (
                    Array.from({ length: pageSize }).map((_, index) => (
                      <TraceSkeletonRow key={`skeleton-${index}`} />
                    ))
                  ) : table.getRowModel().rows?.length ? (
                    table
                      .getRowModel()
                      .rows.map((row) => (
                        <TableBodyRow
                          key={row.id}
                          row={row}
                          onClick={handleRowClick}
                          tableRowRefs={tableRowRefs}
                        />
                      ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length}
                        className="h-auto p-0 text-center"
                        data-testid="traces-list-empty-state"
                      >
                        <NoTracesFound />
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
          <Pagination table={table} />
        </div>
      </Suspense>
      <TraceDrilldownDrawer
        trace={selectedTrace}
        id={currentTraceId}
        open={!!currentTraceId}
        onOpenChange={(isOpen: boolean) => {
          if (!isOpen) {
            setSelectedTrace(null);
            const current = new URLSearchParams(Array.from(searchParams.entries()));
            current.delete('trace_id');
            const search = current.toString();
            const query = search ? `?${search}` : '';
            router.replace(`${window.location.pathname}${query}`, { scroll: false });
          }
        }}
        metrics={metrics && metrics.project_id ? metrics : undefined}
      />
    </div>
  );
}

function TracesColumns(
  searchTerm = '',
  isBookmarked: (id: string) => boolean,
  toggleBookmark: (id: string) => void,
) {
  const formatSpanName = (name: string): string => {
    if (name.endsWith('.session')) {
      const prefix = name.slice(0, name.lastIndexOf('.session'));
      return prefix
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join('_');
    }

    if (name.startsWith('llm:')) {
      return name.slice(4);
    }

    let formattedName = name
      .replace(/\./g, ' ')
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');

    formattedName = formattedName.replace(/Openai/g, 'OpenAI').replace(/Crewai/g, 'CrewAI');

    return formattedName;
  };

  const columns: ColumnDef<ITrace>[] = [
    {
      id: 'bookmark',
      size: COLUMN_SIZES.bookmark,
      header: () => null,
      minSize: COLUMN_SIZES.bookmark,
      maxSize: COLUMN_SIZES.bookmark,
      cell: ({ row }) => {
        const traceId = row.original.trace_id;
        return (
          <div className="flex items-center justify-center">
            <BookmarkButton
              isBookmarked={isBookmarked(traceId)}
              onClick={(e) => {
                e.stopPropagation(); // Prevent row click
                toggleBookmark(traceId);
              }}
              size="sm"
            />
          </div>
        );
      },
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'root_span_name',
      id: 'name',
      size: COLUMN_SIZES.name,
      header: ({ column }) => <ColumnHeader column={column} title="Name" />,
      cell: ({ row }) => {
        const {
          root_span_name: name = 'N/A',
          trace_id: traceId,
          freeplan_truncated,
        } = row.original;
        const ServiceIconComponent = getIconForModel(name);
        const formattedName = formatSpanName(name);
        return (
          <div
            className="group flex min-w-0 cursor-pointer flex-col justify-between pl-2 pr-1 font-medium text-primary sm:h-8"
            data-testid="trace-row-name-container"
          >
            <div className="flex items-center text-base font-semibold leading-tight">
              <div className="mr-2 flex items-center justify-center">
                {ServiceIconComponent ? (
                  React.cloneElement(ServiceIconComponent as React.ReactElement, {
                    className: 'h-5 w-5 flex-shrink-0 align-middle',
                  })
                ) : (
                  <Logo className="h-5 w-5 flex-shrink-0 align-middle" />
                )}
              </div>
              <span className="truncate align-middle">{boldMatch(formattedName, searchTerm)}</span>
              {/* Show warning icon for unnamed traces */}
              {formattedName === 'Default' && (
                <TooltipProvider>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <div
                        className="ml-2 flex h-4 w-4 flex-shrink-0 cursor-help items-center justify-center rounded-full border border-yellow-500 text-xs font-bold text-yellow-500"
                        aria-label="Unnamed trace information"
                      >
                        ?
                      </div>
                    </TooltipTrigger>
                    <TooltipContent
                      className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-80"
                      side="bottom"
                      sideOffset={8}
                    >
                      <div className="space-y-2">
                        <p className="font-medium">This trace is unnamed</p>
                        <p>
                          You can name your traces when creating them manually. This helps organize
                          and identify your traces more easily.
                        </p>
                        <a
                          href="https://docs.agentops.ai/v2/concepts/traces#manual-trace-creation"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block text-blue-300 underline hover:text-blue-200"
                        >
                          Learn how to create named traces →
                        </a>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {/* Show warning indicator for traces with only a single session span */}
              {row.original.span_count === 1 && name.endsWith('.session') && (
                <TooltipProvider>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <div
                        className="ml-2 flex h-4 w-4 flex-shrink-0 cursor-help items-center justify-center rounded-full border border-orange-500 text-xs font-bold text-orange-500"
                        aria-label="Instrumentation warning"
                      >
                        ⚠
                      </div>
                    </TooltipTrigger>
                    <TooltipContent
                      className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-80"
                      side="bottom"
                      sideOffset={8}
                    >
                      <div className="space-y-2">
                        <p className="font-medium">Limited instrumentation detected</p>
                        <p>
                          This trace contains only a single session span. AgentOps may not be
                          properly tracking your LLM calls, tools, and agents.
                        </p>
                        <a
                          href="https://docs.agentops.ai/v2/usage/sdk-reference"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block text-blue-300 underline hover:text-blue-200"
                        >
                          SDK Setup Guide →
                        </a>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {freeplan_truncated && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Clock03Icon
                        className="ml-2 h-4 w-4 flex-shrink-0 font-bold text-amber-600"
                        aria-label="Limited data available"
                      />
                    </TooltipTrigger>
                    <TooltipContent
                      className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-72"
                      side="bottom"
                      sideOffset={8}
                    >
                      Older trace - limited data available on free plan
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <div className="flex items-center gap-1 text-[10px] text-gray-500">
              <code>{boldMatch(traceId, searchTerm)}</code>
            </div>
          </div>
        );
      },
      enableSorting: true,
      enableHiding: false,
      filterFn: (row, id, value) => {
        const name = row.getValue(id) as string;
        return name?.toLowerCase().includes((value as string).toLowerCase());
      },
    },
    {
      accessorKey: 'start_time',
      id: 'timestamp',
      size: COLUMN_SIZES.timestamp,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Timestamp" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const startTime = row.original.start_time;
        const formattedDate = formatDate(startTime) || 'N/A';
        const isTruncated = row.original.freeplan_truncated;

        return (
          <div
            className={cn(
              'flex items-center justify-between gap-2 truncate pl-2 pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60',
            )}
            data-testid="trace-row-timestamp"
          >
            <span>{formattedDate}</span>
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: 'tags',
      id: 'tags',
      size: COLUMN_SIZES.tags,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Tags" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const tags = row.original.tags || [];
        const isTruncated = row.original.freeplan_truncated;
        return (
          <div
            className={cn(
              'truncate pl-2 pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60 blur-[4px]',
            )}
            data-testid="trace-row-tags"
          >
            {tags.length > 0 && <Tags tags={tags} showDivider={false} />}
          </div>
        );
      },
      enableSorting: true,
      sortingFn: (rowA: Row<ITrace>, rowB: Row<ITrace>) => {
        const tagsA = rowA.original.tags || [];
        const tagsB = rowB.original.tags || [];

        const aHasTags = tagsA.length > 0;
        const bHasTags = tagsB.length > 0;

        if (aHasTags && !bHasTags) {
          return -1;
        }
        if (!aHasTags && bHasTags) {
          return 1;
        }
        return tagsB.length - tagsA.length;
      },
    },
    {
      accessorKey: 'error_count',
      id: 'status',
      size: COLUMN_SIZES.status,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Status" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const isTruncated = row.original.freeplan_truncated;
        return (
          <div
            className={cn(
              'flex items-center justify-between gap-2 truncate pl-2 pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60 blur-[4px]',
            )}
          >
            <span
              data-testid="trace-row-status"
              className={`${
                row.original.error_count === 0
                  ? 'text-green-500'
                  : row.original.error_count > 0
                    ? 'text-red-500'
                    : row.original.span_count === 0
                      ? 'text-yellow-500'
                      : 'text-primary'
              }`}
            >
              {row.original.error_count === 0
                ? 'OK'
                : row.original.error_count > 0
                  ? 'ERROR'
                  : row.original.span_count === 0
                    ? 'UNSET'
                    : 'N/A'}
            </span>
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: 'duration',
      id: 'duration',
      size: COLUMN_SIZES.duration,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Duration" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const {
          start_time,
          end_time,
          duration: providedDuration,
          freeplan_truncated: isTruncated,
        } = row.original;

        // --- Constants for bar logic ---
        const MAX_DURATION_FOR_BAR_MS = 120000; // 2 minutes (bar width scales up to this)
        const LONG_DURATION_THRESHOLD_MS = 60000; // 1 minute
        const MEDIUM_DURATION_THRESHOLD_MS = 30000; // 30 seconds
        const SHORT_DURATION_MIN_WIDTH_PERCENT = 10; // Min width for non-zero short runs

        // --- Calculate duration for the bar (in milliseconds) ---
        let durationForBar: number = 0; // Initialize to 0 to satisfy linter
        let successfullyCalculatedFromTimes = false;

        if (start_time && end_time) {
          const startTimeMs = new Date(start_time).getTime();
          const endTimeMs = new Date(end_time).getTime();
          if (!isNaN(startTimeMs) && !isNaN(endTimeMs) && endTimeMs >= startTimeMs) {
            durationForBar = endTimeMs - startTimeMs;
            successfullyCalculatedFromTimes = true;
          }
        }

        if (!successfullyCalculatedFromTimes) {
          if (typeof providedDuration === 'number') {
            durationForBar = providedDuration;
          } else {
            const num = parseFloat(String(providedDuration));
            durationForBar = isNaN(num) ? 0 : num;
          }
        }
        durationForBar = Math.max(0, durationForBar); // Ensure non-negative

        // --- Formatted text for display (using potentially different logic if formatMilliseconds is robust) ---
        const formattedDurationText = formatMilliseconds(start_time, end_time, providedDuration);

        // --- Determine bar color (muted colors to reduce distraction) ---
        let barColorClass: string;
        if (durationForBar >= LONG_DURATION_THRESHOLD_MS) {
          barColorClass = 'bg-amber-400/60'; // Long - muted amber instead of red
        } else if (durationForBar >= MEDIUM_DURATION_THRESHOLD_MS) {
          barColorClass = 'bg-slate-400/60'; // Medium - muted slate instead of blue
        } else {
          barColorClass = 'bg-emerald-400/60'; // Short - muted emerald instead of bright green
        }

        // --- Determine bar display width percentage ---
        let displayWidthPercentage = 0;
        if (durationForBar > 0) {
          const calculatedPercentage = (durationForBar / MAX_DURATION_FOR_BAR_MS) * 100;
          if (barColorClass === 'bg-green-500') {
            displayWidthPercentage = Math.min(
              Math.max(calculatedPercentage, SHORT_DURATION_MIN_WIDTH_PERCENT),
              100,
            );
          } else {
            displayWidthPercentage = Math.min(calculatedPercentage, 100);
          }
        }

        return (
          <div
            className="flex items-center gap-2 truncate pl-2 pr-1 font-medium text-primary sm:h-11"
            data-testid="trace-row-duration"
          >
            {/* Option 1: Muted progress bar */}
            <div
              className={cn(
                'h-2 w-16 rounded-full bg-slate-200/30',
                isTruncated && 'opacity-60 blur-[4px]',
              )}
            >
              {/* Subtle track background */}
              {displayWidthPercentage > 0 && (
                <div
                  className={`h-2 rounded-full transition-all duration-200 ${barColorClass}`}
                  style={{ width: `${displayWidthPercentage}%` }}
                />
              )}
            </div>

            {/* Option 2: Mini latency dots (alternative visual) */}
            {/* Uncomment the following block to use mini dots instead of progress bar */}
            {/*
            <div className={cn('flex gap-0.5', isTruncated && 'opacity-60 blur-[4px]')}>
              {Array.from({ length: 5 }, (_, i) => {
                const dotColor = i < Math.ceil((durationForBar / MAX_DURATION_FOR_BAR_MS) * 5) 
                  ? barColorClass.replace('bg-', 'bg-').replace('/60', '') 
                  : 'bg-slate-200/30';
                return (
                  <div
                    key={i}
                    className={`h-1.5 w-1.5 rounded-full transition-all duration-200 ${dotColor}`}
                  />
                );
              })}
            </div>
            */}

            {/* Option 3: Mini sparkline graph (alternative visual) */}
            {/* Uncomment the following block to use mini sparkline instead of progress bar */}
            {/*
            <div className={cn('h-4 w-12 flex items-end gap-px', isTruncated && 'opacity-60 blur-[4px]')}>
              {Array.from({ length: 8 }, (_, i) => {
                const height = Math.min(4, Math.max(1, Math.floor((durationForBar / MAX_DURATION_FOR_BAR_MS) * 4 * (i + 1) / 8)));
                const barColor = durationForBar >= LONG_DURATION_THRESHOLD_MS 
                  ? 'bg-amber-400/40' 
                  : durationForBar >= MEDIUM_DURATION_THRESHOLD_MS 
                    ? 'bg-slate-400/40' 
                    : 'bg-emerald-400/40';
                return (
                  <div
                    key={i}
                    className={`w-0.5 rounded-sm transition-all duration-200 ${barColor}`}
                    style={{ height: `${height * 4}px` }}
                  />
                );
              })}
            </div>
            */}

            <span className={cn(isTruncated && 'opacity-60 blur-[4px]')}>
              {formattedDurationText}
            </span>
          </div>
        );
      },
      enableSorting: true,
      sortingFn: (rowA: Row<ITrace>, rowB: Row<ITrace>) => {
        const a = rowA.original.duration || 0;
        const b = rowB.original.duration || 0;
        return a < b ? -1 : a > b ? 1 : 0;
      },
    },
    {
      accessorKey: 'total_cost',
      id: 'cost',
      size: COLUMN_SIZES.cost,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Cost" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const cost = row.original.total_cost;
        const isTruncated = row.original.freeplan_truncated;

        return (
          <div
            className={cn(
              'flex items-center justify-between gap-2 truncate pl-2 pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60 blur-[4px]',
            )}
            data-testid="trace-row-cost"
          >
            {cost !== undefined && cost !== null && cost > 0 ? `$${cost.toFixed(7)}` : '$0.0000000'}
          </div>
        );
      },
      enableSorting: true,
      sortingFn: (rowA: Row<ITrace>, rowB: Row<ITrace>) => {
        const a = rowA.original.total_cost || 0;
        const b = rowB.original.total_cost || 0;
        return a < b ? -1 : a > b ? 1 : 0;
      },
    },
    {
      accessorKey: 'span_count',
      id: 'spans',
      size: COLUMN_SIZES.spans,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="# of Spans" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const isTruncated = row.original.freeplan_truncated;
        return (
          <div
            className={cn(
              'flex items-center justify-between gap-2 truncate pl-2 pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60 blur-[4px]',
            )}
            data-testid="trace-row-spans"
          >
            {row.original.span_count ?? 'N/A'}
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: 'error_count',
      id: 'errors',
      size: COLUMN_SIZES.errors,
      header: ({ column }: { column: Column<ITrace, unknown> }) => (
        <ColumnHeader<ITrace, unknown> column={column} title="Errors" />
      ),
      cell: ({ row }: { row: Row<ITrace> }) => {
        const isTruncated = row.original.freeplan_truncated;
        return (
          <div
            className={cn(
              'flex items-center justify-between gap-2 truncate pr-1 font-medium text-primary sm:h-11',
              isTruncated && 'opacity-60 blur-[4px]',
            )}
            data-testid="trace-row-errors"
          >
            {row.original.error_count ?? 'N/A'}
          </div>
        );
      },
      enableSorting: true,
    },
  ];
  return { columns };
}
