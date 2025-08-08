import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface SelectableCardProps {
  id: number;
  title: string;
  description?: string;
  icon?: ReactNode;
  benefit?: string;
  selected?: boolean;
  onClick?: () => void;
}

export function SelectableCard({
  title,
  description,
  icon,
  benefit,
  selected,
  onClick,
}: SelectableCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'relative mb-4 cursor-pointer rounded-xl border-2 p-6 transition-all duration-300',
        'hover:border-black hover:shadow-lg dark:hover:border-white',
        'flex items-start gap-4',
        selected
          ? 'border-black shadow-lg dark:border-white'
          : 'border-gray-100 dark:border-gray-800',
      )}
    >
      {icon && (
        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900/30">
          <div className="flex h-6 w-6 items-center justify-center">{icon}</div>
        </div>
      )}
      <div className="flex-1">
        <h3 className="mb-1 text-lg font-semibold">{title}</h3>
        {description && (
          <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">{description}</p>
        )}
        {benefit && <p className="text-sm text-purple-600 dark:text-purple-400">{benefit}</p>}
      </div>
    </div>
  );
}
