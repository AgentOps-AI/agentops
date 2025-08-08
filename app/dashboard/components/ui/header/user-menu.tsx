'use client';

import { useEffect, useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '../avatar';
import {
  DollarCircleIcon as CircleDollarSignIcon,
  Loading03Icon as Loader2,
  UserIcon,
  AccountSetting01Icon as AccountSettingIcon,
  Key01Icon,
} from 'hugeicons-react';
import { MenuItemsProps } from '@/types/common.types';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { Separator } from '../separator';
import { deleteCache } from '@/lib/idb';
import { useUser } from '@/hooks/queries/useUser';
import project from '../../../package.json';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../tooltip';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { toast } from '@/components/ui/use-toast';
import { PrefetchKind } from 'next/dist/client/components/router-reducer/router-reducer-types';
import Image from 'next/image';
import { getClientBranding } from '../client-branding';

const iconStyles = 'mr-2 h-5 w-5';

const menuItems: MenuItemsProps[] = [
  {
    icon: <AccountSettingIcon className={iconStyles} />,
    label: 'Profile',
    href: '/settings/account',
  },
  {
    icon: <CircleDollarSignIcon className={iconStyles} />,
    label: 'Organization',
    href: '/settings/organization',
  },
  {
    icon: <Key01Icon className={iconStyles} />,
    label: 'API Keys',
    href: '/settings/projects',
  },
];

const UserMenu = ({
  forceDropdownOpen,
  showText = false,
}: {
  forceDropdownOpen?: boolean;
  showText?: boolean;
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { data: userData, isLoading: userDataLoading, error: userError } = useUser();
  const [loggingOut, setLoggingOut] = useState(false);
  const router = useRouter();

  // Get client branding (includes FoxyAI easter egg)
  const clientBranding = getClientBranding(userData?.email ?? undefined);

  const signOut = async () => {
    setLoggingOut(true);
    deleteCache();
    localStorage.removeItem('selectedProject');
    try {
      await fetchAuthenticatedApi('/auth/logout', { method: 'POST' });
      toast({ title: '✅ Signed Out Successfully' });
      router.push('/signin');
    } catch (error: unknown) {
      console.error('Sign Out Error');
      toast({
        title: '❌ Sign Out Failed',
        description: (error as Error).message,
        variant: 'destructive',
      });
      setLoggingOut(false);
    }
  };

  useEffect(() => {
    if (userError) {
      console.error('[UserMenu] Error loading user data:', userError.message);
    }
  }, [userError]);

  return (
    <>
      <div className="relative flex items-center gap-3">
        {userDataLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : userData ? (
          <DropdownMenu
            modal={false}
            open={isDropdownOpen || forceDropdownOpen === true}
            onOpenChange={setIsDropdownOpen}
          >
            <DropdownMenuTrigger data-testid="user-menu-dropdown-trigger">
              <div className="flex flex-col items-center justify-center sm:gap-2">
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Avatar
                      className="flex items-center justify-center"
                      data-testid="user-menu-avatar"
                    >
                      <AvatarImage src={userData?.avatar_url ?? ''} alt="avatar" />
                      <AvatarFallback>
                        <UserIcon />
                      </AvatarFallback>
                    </Avatar>
                    {clientBranding && (
                      <div className="absolute -bottom-1 -right-1 h-6 w-6 rounded-full p-0.5">
                        <Image
                          src={clientBranding.logo}
                          alt={clientBranding.name}
                          width={20}
                          height={20}
                          className="h-full w-full object-contain"
                        />
                      </div>
                    )}
                  </div>
                  {showText && (
                    <div className="ml-2 flex flex-col items-start">
                      <span className="text-sm font-medium" data-testid="user-menu-text-name">
                        {userData.full_name || 'User'}
                      </span>
                      <span
                        className="max-w-[120px] truncate text-xs text-muted-foreground"
                        data-testid="user-menu-text-email"
                      >
                        {userData.email}
                      </span>
                    </div>
                  )}
                </div>
                {userDataLoading && <Loader2 className="h-5 w-5 animate-spin" />}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        className="flex cursor-help items-center justify-center gap-1 text-center text-xs opacity-50"
                        data-testid="user-menu-version-trigger"
                      >
                        v{project.version}
                        {clientBranding && (
                          <span
                            className={`${clientBranding.color} ml-2 flex items-center gap-1`}
                            title={`${clientBranding.name} Partner`}
                          >
                            {clientBranding.versionRow}
                          </span>
                        )}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent
                      data-testid="user-menu-version-tooltip-content"
                      className="flex flex-col items-center text-center"
                    >
                      <p>Version: {project.version}</p>
                      {process.env.VERCEL_BUILD_HASH && (
                        <p>Hash: {process.env.VERCEL_BUILD_HASH}</p>
                      )}
                      {clientBranding && (
                        <p className={`${clientBranding.color} mt-1 flex items-center gap-1`}>
                          {clientBranding.tooltip}
                        </p>
                      )}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="ml-12 w-36">
              {menuItems.map(({ icon, href = '', label }) => (
                <DropdownMenuItem
                  key={label}
                  data-testid={`user-menu-item-${label.toLowerCase().replace(/\s+/g, '-')}`}
                  className={cn('cursor-pointer', {
                    'bg-[#E1E3F2] dark:bg-slate-800': forceDropdownOpen && label === 'API Keys',
                  })}
                  onMouseEnter={() => {
                    router.prefetch(href, { kind: PrefetchKind.FULL });
                  }}
                  onClick={() => router.push(href)}
                >
                  {icon}
                  <span>{label}</span>
                </DropdownMenuItem>
              ))}
              <Separator className="mt-1" />
              <DropdownMenuItem
                className="mt-1 cursor-pointer"
                data-testid="user-menu-button-logout"
                onClick={signOut}
                disabled={loggingOut}
              >
                {loggingOut ? <Loader2 className={iconStyles} /> : null}
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
    </>
  );
};

export default UserMenu;
