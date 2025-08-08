'use client';

import { Button } from './button';
import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';
import { CancelCircleIcon, RefreshIcon } from 'hugeicons-react';

interface ErrorDisplayProps {
  /** The error message to display */
  error?: Error | null;
  /** Custom error message to display instead of the error's message */
  message?: string;
  /** Function to call when the retry button is clicked */
  onRetry?: () => void;
  /** Whether to show the retry button */
  showRetry?: boolean;
  /** Additional context for error reporting */
  errorContext?: Record<string, any>;
  /** Whether to report this error to Sentry automatically */
  reportToSentry?: boolean;
  /** Size variant for the error display */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

export function ErrorDisplay({
  error,
  message,
  onRetry,
  showRetry = true,
  errorContext = {},
  reportToSentry = true,
  size = 'md',
  className = '',
}: ErrorDisplayProps) {
  // Report error to Sentry when component mounts (if enabled)
  useEffect(() => {
    if (reportToSentry && error) {
      Sentry.withScope((scope: any) => {
        scope.setTag('error_source', 'error_display_component');
        scope.setLevel('error');
        scope.setContext('error_context', errorContext);
        Sentry.captureException(error);
      });
    }
  }, [error, reportToSentry, errorContext]);

  if (!error && !message) {
    return null;
  }

  const displayMessage = message || error?.message || 'An unexpected error occurred';

  const sizeClasses = {
    sm: 'text-sm p-3',
    md: 'text-base p-4',
    lg: 'text-lg p-6',
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  return (
    <div
      className={`rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950 ${sizeClasses[size]} ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <CancelCircleIcon
            className={`${iconSizes[size]} text-red-500 dark:text-red-400`}
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-red-700 dark:text-red-300 font-medium">
            {displayMessage}
          </p>
          {showRetry && onRetry && (
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="border-red-300 text-red-700 hover:bg-red-100 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900"
              >
                <RefreshIcon className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to create error display props with automatic Sentry reporting
 */
export function useErrorDisplay(
  error: Error | null,
  context: Record<string, any> = {}
) {
  return {
    error,
    errorContext: context,
    reportToSentry: true,
  };
}