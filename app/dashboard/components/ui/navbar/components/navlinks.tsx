import Link from 'next/link';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../tooltip';
import { ReactNode } from 'react';
import { NavItemVariant } from '../navbar-client';
import { ArrowUpRight01Icon as ExternalLinkIcon } from 'hugeicons-react';

interface NavProps {
  links: ILink[];
  className?: string;
  onLinkClicked?: () => void;
  withTitle?: boolean;
  linkClasses?: string;
}

export interface ILink {
  title: string;
  href: string;
  onclick?: CallableFunction;
  icon: ReactNode;
  variant: NavItemVariant;
  disabled?: boolean;
  tooltip?: string;
  badge?: string;
}

export function NavLinks({
  links,
  className = '',
  onLinkClicked,
  withTitle = true,
  linkClasses = '',
}: NavProps) {
  const router = useRouter();

  function click(link: ILink) {
    if (typeof link.onclick === 'function') {
      link.onclick();
    }
    if (link.href) {
      router.push(link.href);
    }
  }

  const renderLink = (link: ILink) => {
    const linkElement = (
      <Link
        href={link.disabled ? '#' : link.href}
        onMouseDown={() => !link.disabled && click(link)}
        onClick={(e) => {
          if (link.disabled) {
            e.preventDefault();
            return;
          }
          if (link.href) {
            router.push(link.href);
          }
          onLinkClicked?.();
        }}
        className={cn(
          buttonVariants({
            variant: link.variant,
            size: 'sm',
          }),
          'justify-start overflow-hidden rounded-lg border-4 border-transparent px-1.5 dark:border-none dark:px-2.5',
          link.variant === 'default' &&
          'border-[#E3E5F8] dark:bg-muted dark:text-white dark:hover:bg-muted dark:hover:text-white',
          link.variant === 'ghost' && 'hover:bg-[#E4E6F4] dark:text-white dark:hover:bg-slate-800',
          withTitle && 'w-full',
          'cursor-pointer',
          link.disabled && 'cursor-not-allowed opacity-60 hover:bg-transparent',
          linkClasses,
        )}
        style={withTitle ? { width: '100%' } : {}}
      >
        <div className="flex items-center relative">
          {link.icon}
          {withTitle && (
            <span className="ml-3 whitespace-nowrap dark:text-white flex items-center gap-1">
              {link.title}
              {link.onclick && link.title !== 'Support' && link.title !== 'Patch Notes' && <ExternalLinkIcon className="h-3 w-3" />}
              {link.badge && (
                <span className="ml-1.5 inline-flex items-center rounded-full bg-blue-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                  {link.badge}
                </span>
              )}
            </span>
          )}
          {!withTitle && link.badge && (
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
          )}
        </div>
      </Link>
    );

    // Only use tooltip when titles are not shown or when there's a custom tooltip
    if (!withTitle || link.tooltip) {
      return (
        <TooltipProvider key={link.title} delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>{linkElement}</TooltipTrigger>
            <TooltipContent side="right">
              <p>{link.tooltip || link.title}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return linkElement;
  };

  return (
    <nav className={cn('grid w-full gap-2 px-2', className)}>
      {links.map((link) => (
        <div key={link.title} className={withTitle ? 'w-full' : ''}>
          {renderLink(link)}
        </div>
      ))}
    </nav>
  );
}
