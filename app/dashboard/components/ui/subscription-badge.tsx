'use client';

import { Badge } from '@/components/ui/badge';
import {
  CrownIcon as Crown,
  ArrowRight01Icon as ArrowRight,
  Cancel01Icon as X,
} from 'hugeicons-react';
import { LabelImportantIcon as TagIcon } from 'hugeicons-react';
import { DiamondIcon as DiamondShapeIcon } from 'hugeicons-react';
import { cn } from '@/lib/utils';

interface SubscriptionBadgeProps {
  tier: string | null;
  expanded?: boolean;
  showUpgrade?: boolean;
  className?: string;
  isCancelling?: boolean;
  cancelDate?: number;
  isLegacyBilling?: boolean;
  legacyCancellationDate?: string | null;
}

export function SubscriptionBadge({
  tier,
  expanded = true,
  showUpgrade = true,
  className,
  isCancelling = false,
  cancelDate,
  isLegacyBilling = false,
  legacyCancellationDate,
}: SubscriptionBadgeProps) {
  // Legacy billing gets special treatment - show as "Legacy" with cancel date
  if (tier === 'pro' && isLegacyBilling) {
    const formattedDate = legacyCancellationDate
      ? new Date(legacyCancellationDate).toLocaleDateString()
      : '';

    return (
      <Badge
        variant="default"
        className={cn(
          'border-0 bg-gradient-to-r from-purple-600 to-purple-400 text-white shadow-sm dark:text-slate-900',
          expanded ? 'inline-flex items-center px-2 py-1' : 'flex justify-center p-1',
          className,
        )}
      >
        {expanded ? (
          <span className="relative z-10 flex items-center gap-1">
            <X size={12} className="text-white dark:text-slate-900" />
            Legacy{formattedDate && ` • Ends ${formattedDate}`}
          </span>
        ) : (
          <X size={14} className="text-white dark:text-slate-900" />
        )}
      </Badge>
    );
  }

  if (tier === 'pro' && isCancelling) {
    const formattedDate = cancelDate ? new Date(cancelDate * 1000).toLocaleDateString() : '';

    return (
      <Badge
        variant="default"
        className={cn(
          'border-0 bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-sm dark:text-slate-900',
          expanded ? 'inline-flex items-center px-2 py-1' : 'flex justify-center p-1',
          className,
        )}
      >
        {expanded ? (
          <span className="relative z-10 flex items-center gap-1">
            <X size={12} className="text-white dark:text-slate-900" />
            Cancelling{cancelDate && ` ${formattedDate}`}
          </span>
        ) : (
          <X size={14} className="text-white dark:text-slate-900" />
        )}
      </Badge>
    );
  }

  if (tier === 'pro') {
    return (
      <Badge
        variant="default"
        className={cn(
          'pro-shimmer-badge justify-center border-0 bg-gradient-to-r from-[#F3C41A] via-[#FFD700] to-[#F3C41A] text-white shadow-sm dark:text-slate-900',
          expanded ? 'inline-flex items-center px-2 py-1' : 'flex justify-center p-1',
          className,
        )}
      >
        <div className="shimmer-glint" />
        {expanded ? (
          <span className="relative z-10 flex items-center gap-1">
            <Crown size={12} className="text-white dark:text-slate-900" />
            Pro
          </span>
        ) : (
          <Crown size={14} className="text-white dark:text-slate-900" />
        )}
      </Badge>
    );
  }

  if (tier === 'free' || tier === null) {
    return (
      <Badge
        variant="default"
        className={cn(
          'cursor-pointer bg-primary text-white transition-colors hover:brightness-110 dark:text-[#141B34]',
          expanded && showUpgrade ? 'inline-flex items-center justify-between px-2 py-1' : '',
          expanded && !showUpgrade ? 'inline-flex items-center justify-center px-2 py-1' : '',
          !expanded ? 'flex justify-center p-1' : '',
          className,
        )}
      >
        {expanded ? (
          showUpgrade ? (
            <>
              <span className="flex items-center gap-1.5">
                <TagIcon className="h-4 w-4 stroke-white dark:stroke-[#141B34]" />
                Hobby Plan
              </span>
              <span className="flex items-center gap-1 text-xs font-semibold">
                Upgrade <ArrowRight size={12} />
              </span>
            </>
          ) : (
            <span className="flex items-center gap-1.5">
              <TagIcon className="h-4 w-4 stroke-white dark:stroke-[#141B34]" />
              Hobby
            </span>
          )
        ) : (
          <TagIcon className="h-4 w-4 stroke-white dark:stroke-[#141B34]" />
        )}
      </Badge>
    );
  }

  if (tier === 'enterprise') {
    return (
      <Badge
        variant="default"
        className={cn(
          'cursor-pointer justify-center bg-gradient-to-r from-blue-700 to-blue-400 text-white transition-colors',
          expanded ? 'inline-flex items-center px-2 py-1' : 'flex justify-center p-1',
          className,
        )}
      >
        {expanded ? (
          <span className="flex items-center gap-1">
            <DiamondShapeIcon className="h-4 w-4" />
            Enterprise
          </span>
        ) : (
          <DiamondShapeIcon className="h-4 w-4" />
        )}
      </Badge>
    );
  }

  return null;
}
