'use client';

import { useHeaderContext } from '@/app/providers/header-provider';
import { Loading03Icon as Loader2 } from 'hugeicons-react';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

const settingsPages = [
  {
    id: 'account',
    title: 'Account',
    description: 'Update your account settings. Set your preferred language and timezone.',
    href: '/settings/account',
  },
  {
    id: 'organization',
    title: 'Organization',
    description: 'Manage your organization, billing, subscription, and team members.',
    href: '/settings/organization',
  },
  {
    id: 'projects',
    title: 'Projects & API Keys',
    description: 'Manage your projects and API keys.',
    href: '/settings/projects',
  },
];

interface SettingsLayoutProps {
  children: React.ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const { setHeaderTitle, setHeaderContent } = useHeaderContext();
  const router = useRouter();
  const pathname = usePathname();

  const activeTab = useMemo(() => {
    if (pathname?.includes('/settings/organization')) return 'organization';
    if (pathname?.includes('/settings/projects')) return 'projects';
    return 'account';
  }, [pathname]);

  const activePageInfo = useMemo(() => {
    return settingsPages.find((page) => page.id === activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (activePageInfo) {
      setIsLoaded(pathname?.startsWith(activePageInfo.href) ?? false);
    }
  }, [pathname, activePageInfo]);

  const handleTabChange = (tabId: string) => {
    if (tabId === activeTab) return;

    setIsLoaded(false);
    const targetPage = settingsPages.find((page) => page.id === tabId);
    if (targetPage) {
      router.push(targetPage.href);
    }
  };

  useEffect(() => {
    setHeaderTitle('Settings');
    setHeaderContent(null);
  }, []);

  return (
    <div className="p-2 max-sm:p-2 lg:space-y-6">
      <div className="space-y-4">
        <div className="border-b border-[#DEE0F4]">
          <nav className="flex space-x-8 overflow-x-auto">
            {settingsPages.map((page) => (
              <button
                key={page.id}
                onClick={() => handleTabChange(page.id)}
                className={cn(
                  'flex min-w-0 items-center whitespace-nowrap border-b-2 pb-3 pt-2 text-base font-medium transition-colors',
                  activeTab === page.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:border-gray-300 hover:text-foreground',
                )}
              >
                <span className="font-medium">{page.title}</span>
              </button>
            ))}
          </nav>
        </div>
        <div className="min-h-[400px]">
          {isLoaded ? (
            <div className="mt-6">{children}</div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
