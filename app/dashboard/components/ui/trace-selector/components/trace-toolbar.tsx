'use client';

import { FilterIcon, Bookmark02Icon } from 'hugeicons-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ColumnsToggle } from '@/components/ui/trace-selector/components/column-toggles';
import { Cross2Icon } from '@radix-ui/react-icons';
import { Table } from '@tanstack/react-table';
import { useRef } from 'react';
import { ITrace } from '@/types/ITrace';
import { cn } from '@/lib/utils';

export function TraceToolbar({
  table,
  searchQuery,
  onSearchChange,
  showBookmarkedOnly,
  onToggleBookmarkedFilter,
}: {
  table: Table<ITrace>;
  isRefreshing: boolean;
  refreshSessions: () => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  showBookmarkedOnly: boolean;
  onToggleBookmarkedFilter: () => void;
}) {
  const isFiltered = table.getState().columnFilters.length > 0;
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-2">
      <div className="flex items-center gap-2">
        <ColumnsToggle table={table} />
        <div className="relative">
          <FilterIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform " />
          <Input
            placeholder="Filter by name, ID, or tag"
            ref={inputRef}
            value={searchQuery}
            data-testid="trace-toolbar-input-name-filter"
            onChange={(event) => {
              onSearchChange(event.target.value);
            }}
            className="peer h-8 w-[300px] pl-10 text-sm"
          />
        </div>
        <Button
          variant="ghost"
          onClick={onToggleBookmarkedFilter}
          className={cn(
            "h-8 px-2 lg:px-3 flex items-center gap-2",
            showBookmarkedOnly && "bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400 dark:hover:bg-yellow-900/30"
          )}
          data-testid="trace-toolbar-bookmark-filter"
        >
          <Bookmark02Icon 
            className={cn(
              "h-4 w-4",
              showBookmarkedOnly ? "fill-yellow-500 text-yellow-500" : "text-gray-500"
            )}
          />
          {showBookmarkedOnly ? "Bookmarked" : "All"}
        </Button>
        {(isFiltered || showBookmarkedOnly) && (
          <Button
            variant="ghost"
            onMouseDown={() => {
              table.resetColumnFilters();
              if (showBookmarkedOnly) {
                onToggleBookmarkedFilter();
              }
            }}
            className="h-8 px-2 lg:px-3"
          >
            Reset
            <Cross2Icon className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
