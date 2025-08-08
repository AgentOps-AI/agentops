'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/lib/utils';
import { buttonVariants } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

export interface NavItem {
  title: string;
  href: string;
}

interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  items: NavItem[];
  onItemClick?: (item: NavItem) => void;
}

export function SidebarNav({ className, items, onItemClick, ...props }: SidebarNavProps) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <nav
      className={cn('flex flex-col sm:flex-wrap lg:flex-col lg:space-x-0 lg:space-y-1', className)}
      {...props}
    >
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          data-testid={`settings-nav-link-${item.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
          onMouseEnter={() => {
            router.prefetch(item.href);
          }}
          onMouseDown={() => {
            onItemClick?.(item);
            router.push(item.href);
          }}
          className={cn(
            buttonVariants({ variant: 'ghost' }),
            pathname?.startsWith(item.href)
              ? 'bg-slate-800 text-white hover:bg-slate-800 hover:text-white'
              : 'hover:bg-slate-800 hover:text-white hover:underline',
            'justify-start',
          )}
        >
          {item.title}
        </Link>
      ))}
    </nav>
  );
}
