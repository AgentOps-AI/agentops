import { formatDuration, intervalToDuration } from 'date-fns';

// Standard abbreviation config
const ABBREVIATIONS = [
  { threshold: 1e12, suffix: 'T' },
  { threshold: 1e9, suffix: 'B' },
  { threshold: 1e6, suffix: 'M' },
  { threshold: 1e3, suffix: 'K' },
] as const;

/**
 * Core number formatter - handles all abbreviation logic
 */
function formatWithAbbreviation(
  value: number,
  options: {
    decimals?: number;
    threshold?: number;
    forceAbbreviation?: boolean;
  } = {},
): { display: string; full: string } {
  const { decimals = 2, threshold = 1e6, forceAbbreviation = false } = options;

  const full = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: decimals,
    useGrouping: true,
  }).format(value);

  if (!forceAbbreviation && Math.abs(value) < threshold) {
    return { display: full, full };
  }

  const abbrev = ABBREVIATIONS.find((a) => Math.abs(value) >= a.threshold);
  if (!abbrev) return { display: full, full };

  const scaled = value / abbrev.threshold;
  const display = `${scaled.toFixed(scaled >= 100 ? 0 : 1)}${abbrev.suffix}`;

  return { display, full };
}

/**
 * Format number with grouping
 */
export function formatNumber(number: string | number | null | undefined, decimals = 0): string {
  if (number == null) return '';

  const num = typeof number === 'string' ? parseFloat(number) : number;
  if (isNaN(num)) return '';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: Math.min(Math.max(0, decimals), 20),
    minimumFractionDigits: decimals,
    useGrouping: true,
  }).format(num);
}

/**
 * Format price with currency
 */
export function formatPrice(
  price: number | string | null | undefined,
  options: { currency?: string; locale?: string; decimals?: number } = {},
): string {
  const { currency = 'USD', locale = 'en-US', decimals = 2 } = options;

  if (price == null) return '';

  const num = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(num)) return '';

  // Currency-specific defaults
  const currencyDecimals = { JPY: 0, KRW: 0, VND: 0 }[currency] ?? decimals;
  const finalDecimals = decimals !== 2 ? decimals : currencyDecimals;

  if (num === 0) {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(0);
  }

  // Handle tiny amounts
  const threshold = 1 / Math.pow(10, finalDecimals);
  if (num > 0 && num < threshold) {
    return `< ${new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: finalDecimals,
      maximumFractionDigits: finalDecimals,
    }).format(threshold)}`;
  }

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: Math.min(finalDecimals, 6),
    maximumFractionDigits: Math.min(finalDecimals, 6),
  }).format(num);
}

/**
 * Format large prices with abbreviations
 */
export function formatLargePrice(
  price: number | string | null | undefined,
  options: { currency?: string; locale?: string; decimals?: number } = {},
): string {
  const { currency = 'USD', locale = 'en-US', decimals = 2 } = options;

  if (price == null) return '';

  const num = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(num)) return '';

  if (num === 0) {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(0);
  }

  // Use abbreviation for amounts >= 100K
  if (Math.abs(num) < 100000) {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  }

  const { display } = formatWithAbbreviation(Math.abs(num), {
    threshold: 100000,
    forceAbbreviation: true,
  });
  const currencySymbol = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
    .format(0)
    .replace(/[\d\s]/g, '');

  return `${num < 0 ? '-' : ''}${currencySymbol}${display}`;
}

/**
 * Format tokens with abbreviations
 */
export function formatTokens(tokens: number | string | null | undefined): {
  display: string;
  full: string;
} {
  if (tokens == null) return { display: '0', full: '0' };

  const num = typeof tokens === 'string' ? parseFloat(tokens) : tokens;
  if (isNaN(num)) return { display: '0', full: '0' };

  return formatWithAbbreviation(num, { decimals: 0, threshold: 1e6 });
}

/**
 * Format cost with proper decimal handling
 */
export function formatCost(cost: number | string | null | undefined): string {
  if (cost == null) return '$0.000000';

  const num = typeof cost === 'string' ? parseFloat(cost) : cost;
  if (isNaN(num)) return '$0.000000';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 6,
    maximumFractionDigits: 6,
  }).format(num);
}

/**
 * Format metric with prefix/suffix
 */
export function formatMetric(
  value: number | string | null | undefined,
  options: { prefix?: string; suffix?: string; defaultValue?: string } = {},
): string {
  if (value == null) return options.defaultValue || 'N/A';

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return options.defaultValue || 'N/A';

  const { prefix = '', suffix = '' } = options;
  if (num === 0) return `${prefix}0${suffix}`;

  const decimals = num > 0 && num < 0.01 ? 3 : 2;
  return `${prefix}${num.toFixed(decimals)}${suffix}`;
}

/**
 * Format percentage
 */
export function formatPercentage(
  value: number | string | null | undefined,
  options: { alreadyMultiplied?: boolean; defaultValue?: string } = {},
): string {
  if (value == null) return options.defaultValue || 'N/A';

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return options.defaultValue || 'N/A';

  const percentage = options.alreadyMultiplied ? num : num * 100;
  return `${percentage.toFixed(2)}%`;
}

/**
 * Format milliseconds duration
 */
export function formatMilliseconds(startDate: string, endDate: string, mss: number): string {
  if (!mss || isNaN(mss)) return 'N/A';

  const ms = mss / 1000000; // nanoseconds to milliseconds

  if (ms < 1000) {
    return `${(ms / 1000).toFixed(2)}s`;
  }

  const duration = intervalToDuration({
    start: new Date(startDate),
    end: new Date(endDate),
  });

  return formatDuration(duration, {
    format: ['days', 'hours', 'minutes', 'seconds'],
    delimiter: ' ',
    zero: false,
  })
    .replace(/(\d+)\s+day(?:s)?/gi, '$1d')
    .replace(/(\d+)\s+hour(?:s)?/gi, '$1h')
    .replace(/(\d+)\s+minute(?:s)?/gi, '$1m')
    .replace(/(\d+)\s+second(?:s)?/gi, '$1s');
}

/**
 * Format time in seconds
 */
export const formatTimeInSeconds = (ms: number): string => `${(ms / 1000).toFixed(2)}s`;
