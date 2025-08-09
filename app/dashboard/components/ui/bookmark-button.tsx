'use client';

import { Bookmark02Icon } from 'hugeicons-react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface BookmarkButtonProps {
  isBookmarked: boolean;
  onClick: (e: React.MouseEvent) => void;
  className?: string;
  size?: 'sm' | 'md';
}

export function BookmarkButton({ isBookmarked, onClick, className, size = 'sm' }: BookmarkButtonProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
  };

  return (
    <TooltipProvider>
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className={cn(
              'inline-flex items-center justify-center rounded-md transition-all duration-200',
              'hover:bg-gray-100 dark:hover:bg-gray-800',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
              size === 'sm' ? 'p-1' : 'p-1.5',
              className
            )}
            aria-label={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
          >
            <Bookmark02Icon
              className={cn(
                sizeClasses[size],
                'transition-all duration-200',
                isBookmarked
                  ? 'fill-yellow-500 text-yellow-500'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              )}
            />
          </button>
        </TooltipTrigger>
        <TooltipContent
          className="rounded-md bg-gray-900 px-2 py-1 text-xs text-white dark:bg-gray-100 dark:text-gray-900"
          sideOffset={5}
        >
          {isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}