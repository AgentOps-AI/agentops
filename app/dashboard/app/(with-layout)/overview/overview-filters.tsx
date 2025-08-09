import { RefreshIcon } from 'hugeicons-react';
import { Button } from '@/components/ui/button';
import { CommonTooltip } from '@/components/ui/common-tooltip';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { iconDivStyles } from '@/constants/styles';
import { cn } from '@/lib/utils';
import { DateRange } from 'react-day-picker';

type OverviewFiltersProps = {
  isRefreshing: boolean;
  onRefresh: () => void;
  onDateChanged: (range: DateRange) => void;
  selectedRange: DateRange;
  maxLookbackDays?: number | null;
  tierName?: string;
};

const RefreshIconButton = ({
  className,
  onClick,
  isRefreshing,
}: {
  className: string;
  onClick: () => void;
  isRefreshing: boolean;
}) => {
  return (
    <CommonTooltip content="Refresh">
      <div className={cn(iconDivStyles, className)}>
        <Button
          onMouseDown={onClick}
          variant="ghost"
          size="icon"
          className="m-0 h-9 w-9 p-0 hover:bg-[#E4E6F4] hover:shadow-none"
        >
          <RefreshIcon className={isRefreshing ? 'animate-spin-fast' : ''} />
        </Button>
      </div>
    </CommonTooltip>
  );
};

const FiltersPartComponent = ({
  selectedRange,
  onDateChanged,
  onRefresh,
  isRefreshing,
  maxLookbackDays,
  tierName,
}: OverviewFiltersProps) => {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <RefreshIconButton
        className="m-0 hidden h-auto border-none p-0 shadow-none lg:flex"
        onClick={onRefresh}
        isRefreshing={isRefreshing}
      />
      <div className="flex items-center gap-1 rounded-lg dark:bg-[#151924] max-sm:flex-wrap">
        <RefreshIconButton
          className="m-0 flex h-auto border-none shadow-none lg:hidden"
          onClick={onRefresh}
          isRefreshing={isRefreshing}
        />
        <DateRangePicker
          wrapperClassNames={'border-0'}
          noShadow
          isRanged
          onApply={onDateChanged}
          defaultRange={selectedRange}
          maxLookbackDays={maxLookbackDays}
          tierName={tierName}
        />
      </div>
    </div>
  );
};

export const OverviewFilters = FiltersPartComponent;
