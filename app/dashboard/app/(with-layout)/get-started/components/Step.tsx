import { ArrowRight01Icon as ChevronRight } from 'hugeicons-react';
import { cn } from '@/lib/utils';
import { StepProps } from '../types';

export function Step({ label, isActive, isComplete, onClick }: StepProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'text-orange-500'
          : isComplete
            ? 'text-gray-900 hover:text-orange-500 dark:text-gray-100'
            : 'cursor-default text-gray-400',
      )}
    >
      {label}
      <ChevronRight className="h-4 w-4" />
    </button>
  );
}
