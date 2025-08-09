import { Table } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ArrowDown01Icon,
  ArrowLeft01Icon,
  ArrowLeftDoubleIcon,
  ArrowRight01Icon,
  ArrowRightDoubleIcon
} from 'hugeicons-react';

interface PaginationProps<TData> {
  table: Table<TData>;
}

export function Pagination<TData>({ table }: PaginationProps<TData>) {
  return (
    <div className="flex items-center justify-end px-2">
      <div className="flex items-center space-x-2">
        <div className="flex items-center space-x-2">
          <p className="text-sm font-medium text-secondary dark:text-white">Per page</p>
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(value) => {
              table.setPageSize(Number(value));
            }}
          >
            <SelectTrigger
              className="relative h-8 w-[70px] rounded-lg bg-[#E1E3F2]"
              icon={
                <ArrowDown01Icon className="absolute ml-7 h-6 w-6 rounded-md border-4 border-[#F7F8FF] bg-[#F7F8FF] dark:border-slate-800 dark:bg-slate-800" />
              }
            >
              <SelectValue placeholder={table.getState().pagination.pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {[5, 10, 20, 50, 100].map((pageSize) => (
                <SelectItem key={pageSize} value={`${pageSize}`}>
                  {pageSize}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex w-[100px] items-center justify-center text-sm font-medium text-secondary dark:text-white">
          Page {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
        </div>
        <div className="flex items-center">
          <Button
            variant="outline"
            className="hidden h-8 w-8 border-none bg-transparent p-0 hover:bg-[#E1E3F2] lg:flex"
            onMouseDown={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            <span className="sr-only">Go to first page</span>
            <ArrowLeftDoubleIcon size={16} />
          </Button>
          <Button
            variant="outline"
            className="h-8 w-8 border-none bg-transparent p-0 hover:bg-[#E1E3F2]"
            onMouseDown={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <span className="sr-only">Go to previous page</span>
            <ArrowLeft01Icon size={16} />
          </Button>
          <Button
            variant="outline"
            className="h-8 w-8 border-none bg-transparent p-0 hover:bg-[#E1E3F2]"
            onMouseDown={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <span className="sr-only">Go to next page</span>
            <ArrowRight01Icon size={16} />
          </Button>
          <Button
            variant="outline"
            className="hidden h-8 w-8 border-none bg-transparent p-0 hover:bg-[#E1E3F2] lg:flex"
            onMouseDown={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            <span className="sr-only">Go to last page</span>
            <ArrowRightDoubleIcon size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
}
