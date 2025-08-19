import { Skeleton } from './skeleton';
import { TableCell, TableRow } from './table';

/**
 * Skeleton placeholder for a single line statistic value.
 */
export const StatSkeleton = () => (
  <Skeleton className="h-8 w-1/2" />
);

/**
 * Skeleton placeholder for a chart area.
 */
export const ChartSkeleton = () => (
  <Skeleton className="h-[300px] w-full" />
);

// Match column sizes from traces/page.tsx for consistency
const TRACE_COLUMN_SIZES = {
  name: 260,
  timestamp: 200,
  status: 160,
  duration: 160,
  spans: 160,
  errors: 90,
} as const;

/**
 * Skeleton placeholder for a row in the traces table.
 */
export const TraceSkeletonRow = () => (
  <TableRow className="hover:bg-transparent">
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.name}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.timestamp}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.status}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.duration}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.spans}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    <TableCell style={{ width: `${TRACE_COLUMN_SIZES.errors}px` }}>
      <Skeleton className="h-5 w-full" />
    </TableCell>
    {/* Consider adding placeholder for delete action if applicable */}
  </TableRow>
);

/**
 * Skeleton placeholder for a project card.
 */
export const ProjectCardSkeleton = () => (
  <div className="flex flex-col space-y-3 rounded-xl border border-border bg-card p-6 shadow-md">
    <Skeleton className="h-5 w-3/4" />
    <Skeleton className="h-4 w-1/2" />
    <div className="flex justify-end pt-2">
      <Skeleton className="h-8 w-20" />
    </div>
  </div>
);
