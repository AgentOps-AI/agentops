import { ArrowDown01Icon as ChevronDownIcon } from 'hugeicons-react';
import { Cancel01Icon as CloseIcon } from 'hugeicons-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { Separator } from '@/components/ui/separator';
import { Column } from '@tanstack/react-table';
import * as React from 'react';
import { Checkbox } from '../../checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '../../popover';

interface FacetedFilter<TData, TValue> {
  column?: Column<TData, TValue>;
  title?: string;
  options: {
    value: string | null;
    label: string;
    icon?: React.ComponentType<{
      className?: string;
    }>;
  }[];
  firstIcon: React.ReactNode;
}

export function FacetedFilter<TData, TValue>({
  column,
  title,
  options,
  firstIcon,
}: FacetedFilter<TData, TValue>) {
  const facets = column?.getFacetedUniqueValues();
  const selectedValues = new Set(column?.getFilterValue() as null[] | string[]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-8 border-none bg-[#E1E3F2] text-sm hover:bg-[#E1E3F2] dark:bg-slate-800"
        >
          <span className={selectedValues?.size > 0 ? '' : 'mr-3'}>{firstIcon}</span>
          {selectedValues?.size === 0 && (
            <span className="text-secondary dark:text-white">{title}</span>
          )}
          {selectedValues?.size > 0 && (
            <>
              <Separator orientation="vertical" className="mx-2 h-4" />
              <Badge variant="secondary" className="rounded-sm px-1 font-normal lg:hidden">
                {selectedValues.size}
              </Badge>
              <div className="hidden space-x-2 lg:flex">
                {selectedValues.size > 2 ? (
                  <Badge
                    variant="secondary"
                    className="rounded-md bg-[#F7F8FF] px-2 text-xs font-medium text-black shadow-xl dark:bg-slate-950"
                  >
                    {selectedValues.size} selected
                  </Badge>
                ) : (
                  options
                    .filter((option) => selectedValues.has(option.value))
                    .map((option) => {
                      const isSelected = selectedValues.has(option.value);
                      return (
                        <Badge
                          variant="secondary"
                          key={option.value}
                          className="rounded-md bg-[#F7F8FF] px-2 text-xs font-medium text-black shadow-xl dark:bg-slate-950"
                        >
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              if (isSelected) {
                                selectedValues.delete(option.value);
                              }
                              const filterValues = Array.from(selectedValues);
                              column?.setFilterValue(
                                filterValues.length ? filterValues : undefined,
                              );
                            }}
                          >
                            <CloseIcon className="mr-1 h-3 w-3" />
                          </div>
                          {option.label}
                        </Badge>
                      );
                    })
                )}
              </div>
            </>
          )}
          {selectedValues.size === 0 && (
            <ChevronDownIcon className="ml-3 h-4 w-4 rounded-md border-0 dark:border-slate-800 dark:bg-slate-800" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selectedValues.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    className="cursor-pointer gap-2"
                    onSelect={() => {
                      if (isSelected) {
                        selectedValues.delete(option.value);
                      } else {
                        selectedValues.add(option.value);
                      }
                      const filterValues = Array.from(selectedValues);
                      column?.setFilterValue(filterValues.length ? filterValues : undefined);
                    }}
                  >
                    <Checkbox checked={isSelected} />
                    {option.icon && <option.icon className="mr-2 h-4 w-4 text-muted-foreground" />}
                    <span>{option.label}</span>
                    {facets?.get(option.value) && (
                      <span className="ml-auto flex h-4 w-4 items-center justify-center font-mono text-xs">
                        {facets.get(option.value)}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => column?.setFilterValue(undefined)}
                    className="justify-center text-center"
                  >
                    Clear filters
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
