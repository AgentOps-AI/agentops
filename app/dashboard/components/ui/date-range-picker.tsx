'use client';

import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn, isSafariBrowser } from '@/lib/utils';
import { addMonths, endOfDay, format, startOfDay, subDays, addHours, isValid } from 'date-fns';
import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { DateRange } from 'react-day-picker';
import { Calendar01Icon as CalenderIcon } from 'hugeicons-react';
import { InformationCircleIcon as InfoIcon } from 'hugeicons-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const initialRange = {
  from: startOfDay(subDays(new Date(), 14)),
  to: endOfDay(new Date()),
};

function isValidDateRange(range: DateRange | undefined): boolean {
  if (!range) return false;
  if (!range.from || !range.to) return false;
  if (!isValid(range.from) || !isValid(range.to)) return false;
  return range.from <= range.to;
}

export const DateRangePicker = ({
  isRanged,
  defaultRange,
  onDateChanged,
  onApply,
  noShadow,
  wrapperClassNames,
  maxLookbackDays,
  tierName,
}: {
  isRanged?: boolean;
  defaultRange: DateRange;
  setSelectedRange?: CallableFunction;
  onDateChanged?: (range: DateRange) => void;
  onApply?: (range: DateRange) => void;
  noShadow?: boolean;
  wrapperClassNames?: string;
  maxLookbackDays?: number | null;
  tierName?: string;
}) => {
  const minAllowedDate = useMemo(() => {
    const date =
      typeof maxLookbackDays === 'number' ? startOfDay(subDays(new Date(), maxLookbackDays)) : null;
    return date;
  }, [maxLookbackDays]);

  const [showDateClampedWarning, setShowDateClampedWarning] = useState(false);

  const getAdjustedRange = useCallback(
    (range: DateRange): DateRange => {
      let { from, to } = range;

      if (minAllowedDate && from && from < minAllowedDate) {
        from = minAllowedDate;
      }
      if (to && from && to < from) {
        to = from;
      }
      const maxAllowedToDate = endOfDay(new Date());
      if (to && to > maxAllowedToDate) {
        to = maxAllowedToDate;
      }

      return { from, to };
    },
    [minAllowedDate, maxLookbackDays, tierName],
  );

  const [localRange, setLocalRange] = useState<DateRange>(() => {
    const adjusted = getAdjustedRange(isValidDateRange(defaultRange) ? defaultRange : initialRange);
    return adjusted;
  });

  const [open, setOpen] = useState(false);

  const lastAppliedRange = useRef<{ from: number | null; to: number | null } | null>(null);

  // Remove the automatic onApply effect - onApply should only be called when Apply button is clicked

  useEffect(() => {
    if (
      minAllowedDate &&
      localRange.from &&
      localRange.from.getTime() === minAllowedDate.getTime() &&
      tierName === 'free'
    ) {
      setShowDateClampedWarning(true);
      const timer = setTimeout(() => {
        setShowDateClampedWarning(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [localRange.from, minAllowedDate, tierName]);

  const handleLastDay = (day: Date) => {
    if (!isValid(day)) return;
    setLocalRange(
      getAdjustedRange({
        from: startOfDay(day),
        to: localRange.to,
      }),
    );
  };

  const handleFromDate = (day: Date) => {
    if (!isValid(day)) return;

    if (localRange.to && day <= localRange.to) {
      const adjustedRange = getAdjustedRange({
        from: startOfDay(day),
        to: localRange.to,
      });
      setLocalRange(adjustedRange);
    } else {
      setLocalRange(initialRange);
    }
  };

  const handleToDate = (day: Date) => {
    if (!isValid(day)) return;

    if (localRange.from && day >= localRange.from) {
      const adjustedRange = getAdjustedRange({
        from: localRange.from,
        to: endOfDay(day),
      });
      setLocalRange(adjustedRange);
    } else {
      setLocalRange(initialRange);
    }
  };

  const handleRangeSelect = (range: DateRange | undefined) => {
    if (!range || !isValidDateRange(range)) return;
    const adjustedRange = getAdjustedRange(range);
    setLocalRange(adjustedRange);
    onDateChanged?.(adjustedRange);
  };

  useEffect(() => {
    if (!onDateChanged) {
      return;
    }

    if (isValidDateRange(localRange)) {
      const localFromDay = localRange.from ? startOfDay(localRange.from).getTime() : null;
      const localToDay = localRange.to ? endOfDay(localRange.to).getTime() : null;
      const defaultFromDay = defaultRange?.from ? startOfDay(defaultRange.from).getTime() : null;
      const defaultToDay = defaultRange?.to ? endOfDay(defaultRange.to).getTime() : null;

      if (localFromDay !== defaultFromDay || localToDay !== defaultToDay) {
        onDateChanged(getAdjustedRange(localRange));
      }
    }
  }, [localRange, defaultRange, onDateChanged, getAdjustedRange]);

  return (
    <div className={cn('flex flex-col', wrapperClassNames)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              className={cn(
                'relative flex h-10 items-center justify-between gap-2 overflow-hidden rounded-md border border-[#DEE0F4] bg-[#F7F8FF] px-3 py-2 text-sm font-medium text-primary shadow-md hover:bg-[#E1E3F2] dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700',
                !noShadow && 'shadow-sm',
              )}
            >
              <span
                style={{
                  opacity: 0.3,
                  backgroundImage: 'url(/image/grainy.png)',
                  backgroundSize: '28px 28px',
                }}
                className="absolute inset-0 z-0 dark:hidden"
              />
              <CalenderIcon className="relative z-10 h-4 w-4" />
              <span className="relative z-10 truncate">
                {localRange.from && localRange.to
                  ? `${format(localRange.from, 'MMM d, yyyy')} - ${format(localRange.to, 'MMM d, yyyy')}`
                  : 'Select date range'}
              </span>
            </Button>
          </div>
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="end"
          className={cn(
            'grid w-auto rounded-md bg-[#F7F8FF] p-0 p-2 max-sm:w-full sm:grid-cols-5',
            !noShadow && 'shadow-md',
            '@supports (-webkit-touch-callout: none) { margin-right: 20px; }',
            isSafariBrowser() && 'max-lg:mr-20',
          )}
        >
          <div className="col-span-1 flex flex-col gap-0 max-sm:hidden">
            <Button
              variant="ghost"
              onMouseDown={() => {
                setLocalRange(getAdjustedRange(initialRange));
              }}
            >
              Today
            </Button>
            <Button
              variant="ghost"
              onMouseDown={() => {
                const range = {
                  from: startOfDay(subDays(new Date(), 6)),
                  to: endOfDay(new Date()),
                };
                setLocalRange(getAdjustedRange(range));
              }}
            >
              Last 7 Days
            </Button>
            <Button
              variant="ghost"
              onMouseDown={() => {
                setLocalRange({
                  from: startOfDay(subDays(new Date(), 13)),
                  to: endOfDay(new Date()),
                });
              }}
            >
              Last 14 Days
            </Button>
            <Button
              variant="ghost"
              onMouseDown={() => {
                setLocalRange({
                  from: startOfDay(subDays(new Date(), 29)),
                  to: endOfDay(new Date()),
                });
              }}
            >
              Last 30 Days
            </Button>
          </div>

          {isRanged && (
            <div className="flex flex-col sm:col-span-4">
              <div className="pt-2 text-center text-sm font-medium">Date range</div>
              <Calendar
                defaultMonth={localRange.from}
                mode="range"
                numberOfMonths={2}
                selected={localRange}
                toDate={addHours(new Date(), 12)}
                fromDate={minAllowedDate || undefined}
                disabled={
                  minAllowedDate
                    ? { before: minAllowedDate, after: endOfDay(new Date()) }
                    : { after: endOfDay(new Date()) }
                }
                onDayClick={handleLastDay}
                onSelect={handleRangeSelect}
              />
              <div className="ml-auto flex justify-end">
                <Button
                  onClick={() => {
                    if (isValidDateRange(localRange)) {
                      const normalizedLocal = {
                        from: localRange.from ? startOfDay(localRange.from).getTime() : null,
                        to: localRange.to ? endOfDay(localRange.to).getTime() : null,
                      };

                      // Only call onApply if this range hasn't been applied yet
                      if (
                        !lastAppliedRange.current ||
                        lastAppliedRange.current.from !== normalizedLocal.from ||
                        lastAppliedRange.current.to !== normalizedLocal.to
                      ) {
                        lastAppliedRange.current = normalizedLocal;
                        onApply?.(localRange);
                      }
                      setOpen(false);
                    }
                  }}
                >
                  Apply
                </Button>
              </div>
              {showDateClampedWarning && (
                <Alert className="mt-2 border-blue-300 bg-blue-50 text-blue-700">
                  <InfoIcon className="h-4 w-4" />
                  <AlertDescription>
                    Date adjusted to your plan&apos;s {maxLookbackDays}-day limit.{' '}
                    <a href="/settings/organization" className="underline hover:text-blue-800">
                      Upgrade for full history
                    </a>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {!isRanged && (
            <>
              <div className="flex flex-col sm:col-span-2">
                <div className="pt-2 text-center text-sm font-medium">Start Date</div>
                <Calendar
                  defaultMonth={localRange.from}
                  mode="range"
                  selected={localRange}
                  onDayClick={handleFromDate}
                  fromDate={minAllowedDate || undefined}
                  toDate={endOfDay(new Date())}
                  disabled={
                    minAllowedDate
                      ? { before: minAllowedDate, after: endOfDay(new Date()) }
                      : { after: endOfDay(new Date()) }
                  }
                />
              </div>

              <div className="flex flex-col sm:col-span-2">
                <div className="pt-2 text-center text-sm font-medium">End Date</div>
                <Calendar
                  className="sm:col-span-2"
                  defaultMonth={addMonths(localRange.from!, 1)}
                  initialFocus
                  mode="range"
                  selected={localRange}
                  onDayClick={handleToDate}
                  fromDate={minAllowedDate || undefined}
                  toDate={endOfDay(new Date())}
                  disabled={
                    minAllowedDate
                      ? { before: minAllowedDate, after: endOfDay(new Date()) }
                      : { after: endOfDay(new Date()) }
                  }
                />
              </div>
            </>
          )}
        </PopoverContent>
      </Popover>
    </div>
  );
};
