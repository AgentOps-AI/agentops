'use client';

import { DropdownMenuTrigger } from '@radix-ui/react-dropdown-menu';
import { Table } from '@tanstack/react-table';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
} from '@/components/ui/dropdown-menu';
import { ColumnDeleteIcon } from 'hugeicons-react';
import { CommonTooltip } from '@/components/ui/common-tooltip';

interface ColumnsToggleProps<TData> {
  table: Table<TData>;
}

export function ColumnsToggle<TData>({ table }: ColumnsToggleProps<TData>) {
  return (
    <DropdownMenu>
      <CommonTooltip content="Toggle Columns">
        <DropdownMenuTrigger asChild>
          <div className="ml-auto border-none bg-transparent hover:bg-transparent dark:hover:bg-transparent lg:flex">
            <Button size="icon" variant="icon" className="h-8 w-8 rounded-lg p-0 shadow-xl">
              <ColumnDeleteIcon className="h-4 w-4" />
            </Button>
          </div>
        </DropdownMenuTrigger>
      </CommonTooltip>
      <DropdownMenuContent align="end" className="w-[150px]">
        {/* <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator /> */}
        {table
          .getAllColumns()
          .filter((column) => typeof column.accessorFn !== 'undefined' && column.getCanHide())
          .map((column) => {
            return (
              <DropdownMenuCheckboxItem
                key={column.id}
                className="cursor-pointer capitalize"
                checked={column.getIsVisible()}
                onCheckedChange={(value) => column.toggleVisibility(!!value)}
                onSelect={(event) => event.preventDefault()}
              >
                {column.id === 'init_timestamp' ? 'Timestamp' : column.id}
              </DropdownMenuCheckboxItem>
            );
          })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
