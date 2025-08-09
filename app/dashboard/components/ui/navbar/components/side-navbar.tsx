'use client';
import { Separator } from '@/components/ui/separator';
import { ILink, NavLinks } from './navlinks';
import Logo from '@/components/icons/Logo';
import UserMenu from '../../header/user-menu';
import { SmallThemeTogler } from '../../small-theme-togler';
import { ApiKeysButton } from '../../api-keys-button';
import { LayoutRightIcon as PanelRight } from 'hugeicons-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/app/providers/sidebar-provider';
import AgentOpsBanner from '@/components/icons/AgentOpsBanner';
import { useState } from 'react';
import Link from 'next/link';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import { usePathname } from 'next/navigation';
import { shouldShowPremiumBanner } from '@/utils/route-helpers';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { useUser } from '@/hooks/queries/useUser';
import { getClientBranding } from '../../client-branding';

export function SideNavbar(props: { helpLinks: ILink[]; dataLinks: ILink[] }) {
  const { isExpanded, setIsExpanded } = useSidebar();
  const [isHovering, setIsHovering] = useState(false);
  const { premStatus, isLoading: isPermissionsLoading } = useOrgFeatures();
  const pathname = usePathname();
  const { data: userData } = useUser();
  const clientBranding = getClientBranding(userData?.email ?? undefined);
  const isFoxyUser = !!clientBranding && clientBranding.name === 'FoxyAI';

  const showBanner = shouldShowPremiumBanner(pathname);

  const toggleSidebar = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <>
      <div
        className={cn(
          'sticky left-0 top-0 hidden h-screen flex-col items-start justify-start p-0 transition-all duration-300 sm:flex',
          isExpanded ? 'w-[220px]' : 'w-[66px]',
        )}
        onMouseEnter={() => !isExpanded && setIsHovering(true)}
        onMouseLeave={() => !isExpanded && setIsHovering(false)}
      >
        <div className="relative flex h-[60px] w-full items-center justify-center">
          {isExpanded ? (
            <div className="flex w-full items-center justify-between px-4">
              <Link href="/traces" className="flex items-center">
                <AgentOpsBanner foxyUser={isFoxyUser} />
              </Link>
              <button
                onClick={toggleSidebar}
                className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full transition-colors hover:bg-slate-200 dark:hover:bg-slate-700"
                aria-label="Collapse sidebar"
              >
                <PanelRight size={16} className="dark:text-white" />
              </button>
            </div>
          ) : (
            <div className="flex w-full items-center justify-center">
              <button
                className="relative flex h-10 w-10 cursor-pointer items-center justify-center rounded-md transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={toggleSidebar}
                aria-label="Expand sidebar"
              >
                <Logo
                  className={cn(
                    'absolute h-10 w-10 transition-opacity dark:text-white',
                    isHovering ? 'opacity-0' : 'opacity-100',
                  )}
                />
                <PanelRight
                  className={cn(
                    'absolute h-5 w-5 transition-opacity dark:text-white',
                    isHovering ? 'opacity-100' : 'opacity-0',
                  )}
                />
              </button>
            </div>
          )}
        </div>
        <Separator className="w-full" color="#DEE0F4" />

        <div
          className={cn(
            'flex w-full flex-col gap-4 py-3',
            isExpanded ? 'px-2' : 'items-center px-0',
          )}
        >
          <div
            className={cn(
              'group flex w-full min-w-10 flex-grow flex-col gap-4',
              !isExpanded && 'items-center',
            )}
          >
            <NavLinks
              links={props.dataLinks}
              withTitle={isExpanded}
              linkClasses={isExpanded ? 'justify-start w-full' : 'justify-center items-center'}
              className={!isExpanded ? 'flex flex-col items-center' : ''}
            />
            <Separator className="w-full" />
            <NavLinks
              links={props.helpLinks}
              withTitle={isExpanded}
              linkClasses={isExpanded ? 'justify-start w-full' : 'justify-center items-center'}
              className={!isExpanded ? 'flex flex-col items-center' : ''}
            />
            <Separator className="w-full" />
            <nav className="grid w-full gap-2 px-2">
              <SmallThemeTogler withTitle={isExpanded} alignLeft={isExpanded} />
              <ApiKeysButton withTitle={isExpanded} alignLeft={isExpanded} />
            </nav>
          </div>
        </div>
        <div className="mt-auto w-full">
          {!isPermissionsLoading && premStatus !== null && showBanner && (
            <div className="mb-2 w-full px-2">
              <Link href="/settings/organization" className="block w-full">
                <SubscriptionBadge tier={premStatus} expanded={isExpanded} className="w-full" />
              </Link>
            </div>
          )}

          <div
            className={cn(
              'mb-2 flex w-full items-center',
              isExpanded ? 'justify-start px-4' : 'justify-center px-0',
            )}
          >
            <UserMenu showText={isExpanded} />
          </div>
        </div>
      </div>
    </>
  );
}
