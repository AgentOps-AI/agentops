import React from 'react';
import { cn } from '@/lib/utils';

interface TagsProps {
  tags: string[];
  className?: string;
  tagClassName?: string;
  showDivider?: boolean;
}

export function Tags({ tags, className, tagClassName, showDivider = true }: TagsProps) {
  if (!tags || tags.length === 0) return null;

  return (
    <>
      {showDivider && (
        <div className="h-6 border-l border-[rgba(222,224,244,1)] dark:border-gray-600"></div>
      )}
      <div className={cn('flex flex-wrap items-center gap-1', className)}>
        {tags.map((tag, index) => (
          <span
            key={index}
            className={cn(
              'text-[rgba(20, 27, 52, 0.74)] dark:text-[rgba(225, 226, 242, 1)] rounded-full bg-[#E5E6F3] px-2 py-0.5 text-xs shadow-sm dark:bg-gray-700',
              tagClassName,
            )}
            style={{ opacity: 0.9 }}
          >
            {tag}
          </span>
        ))}
      </div>
    </>
  );
}
