'use client';

import Logo from '@/components/icons/Logo';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export function AgentOpsButton({ isCollapsed = false }: { isCollapsed?: boolean }) {
  return (
    <nav className="grid gap-1 px-2">
      {isCollapsed ? (
        <Link
          href="https://app.agentops.ai"
          className={cn(
            buttonVariants({
              variant: 'outline',
              size: 'icon',
            }),
            'h-9 w-9',
            'dark:bg-muted dark:text-muted-foreground dark:hover:bg-muted dark:hover:text-white',
          )}
        >
          <Logo className="h-5 w-5" />
          <span className="sr-only">AgentOps</span>
        </Link>
      ) : (
        <Link
          href="https://app.agentops.ai"
          className={cn(
            buttonVariants({
              variant: 'outline',
              size: 'sm',
            }),
            'justify-start overflow-hidden px-[7px] font-bold dark:bg-muted dark:text-white dark:hover:bg-muted dark:hover:text-white',
          )}
        >
          <Logo className="mr-2 h-5 w-5 flex-shrink-0" />
          AgentOps
        </Link>
      )}
    </nav>
  );
}
