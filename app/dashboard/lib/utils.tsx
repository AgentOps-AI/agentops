import { type DataPoint } from '@/components/charts/line-chart/chart';
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  formatNumber,
  formatPrice,
  formatMetric,
  formatPercentage,
} from './number_formatting_utils';

import { DateRange } from 'react-day-picker';
import { isWithinInterval } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncateString(str: string | null, maxLength?: number) {
  if (!str) return '';
  if (!maxLength || str.length <= maxLength) {
    return str;
  }
  return str.substring(0, maxLength) + '...';
}

export function titleCase(str: string) {
  return str
    .split(' ')
    .map((word) =>
      word
        .split('-')
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
        .join('-'),
    )
    .join(' ');
}

export function parseTags(input: string | null | undefined): string[] {
  if (!input) {
    return [];
  }

  try {
    const tags = JSON.parse(input);

    if (Array.isArray(tags) && tags.every((item) => typeof item === 'string')) {
      return tags;
    }
  } catch (error) {
    console.error('Failed to parse tags:', error);
  }

  return [];
}

export function formatTime(time: number): string {
  // Input is now expected to be in milliseconds
  const timeInMs = time;

  if (timeInMs < 1000) {
    return `${timeInMs.toFixed(2)}ms`;
  } else if (timeInMs < 60000) {
    return `${(timeInMs / 1000).toFixed(2)}s`;
  } else {
    const totalSeconds = Math.floor(timeInMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
    }
    if (minutes > 0) {
      return `${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
    } else {
      return `${seconds.toString().padStart(2, '0')}s`;
    }
  }
}

export function formatTimeRange(time: number, duration: number) {
  return `${Math.floor(time / 60)}m ${Math.floor(time % 60)}s - ${Math.floor(
    (time + duration) / 60,
  )}m ${Math.floor((time + duration) % 60)}s`;
}

export function formatDate(isoTime: string) {
  return new Date(isoTime).toLocaleString(undefined, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });
}

export function sortDataIntoPresetIntervals(
  dataMax: number,
  numBuckets: number,
  bucketSizeOptions: number[],
  dataValues: number[],
  createName: (start: number, end: number) => string,
  dataPoints: DataPoint[],
  separateZeroBucket: boolean = false,
) {
  const rawBucketSize = dataMax / (numBuckets - 1);
  const bucketSize =
    bucketSizeOptions.find((size) => size >= rawBucketSize) ||
    bucketSizeOptions[bucketSizeOptions.length - 1];

  let currentStart = 0;
  while (currentStart < dataMax) {
    const bucketEnd = currentStart + bucketSize;
    dataPoints.push({
      name: createName(currentStart, bucketEnd),
      count: 0,
    });
    currentStart = bucketEnd;
  }

  dataValues.forEach((value) => {
    if (value === 0 && separateZeroBucket) {
      dataPoints[0].count++;
    } else {
      const bucketIndex = Math.min(
        Math.floor(value / bucketSize) + (separateZeroBucket ? 1 : 0),
        dataPoints.length - 1,
      );
      dataPoints[bucketIndex].count++;
    }
  });
}

export { formatNumber, formatPrice, formatMetric, formatPercentage };

export function filterByDateRange<T>(
  items: T[] | undefined | null,
  dateRange: DateRange | undefined,
  getTimestamp: (item: T) => string | Date,
): T[] {
  if (!items || !Array.isArray(items)) return [];
  if (!dateRange?.from || !dateRange?.to) return items;

  const start = dateRange.from;
  const end = dateRange.to;

  return items.filter((item) => {
    const timestamp = getTimestamp(item);
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    return isWithinInterval(date, { start, end });
  });
}

export function isSafariBrowser() {
  return /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
}

export const getDurationBar = (duration: number) => {
  // Define thresholds (in ms)
  const SHORT = 1000; // 1 second
  const MEDIUM = 5000; // 5 seconds

  // Calculate relative width (max 100px)
  const width = Math.min(Math.max(duration / 100, 10), 100);

  const color =
    duration <= SHORT ? 'bg-green-500' : duration <= MEDIUM ? 'bg-blue-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 rounded" style={{ width: width + 'px' }}>
        <div className={cn('h-full rounded', color)} style={{ width: '100%' }} />
      </div>
      <span className="text-xs"> {formatTime(duration)} </span>
    </div>
  );
};