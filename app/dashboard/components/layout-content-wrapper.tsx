'use client';

import { Container } from '@/components/ui/container';
import { Header } from '@/components/ui/header/header';
import { Navbar } from '@/components/ui/navbar/navbar';
import { cn } from '@/lib/utils';
import { PropsWithChildren } from 'react';
import { useSidebar } from '@/app/providers/sidebar-provider';

export function LayoutContentWrapper({ children }: PropsWithChildren) {
  const { isExpanded } = useSidebar();

  return (
    <div id="main-layout-container" className="flex">
      <div id="left-part" className="relative z-20">
        <Navbar mobile={false} />
      </div>
      <div
        id="right-part"
        className={cn(
          'flex flex-col pr-4 transition-all duration-300 max-sm:w-full',
          isExpanded ? 'w-[calc(100%-220px)]' : 'w-[calc(100%-66px)]',
        )}
      >
        <Header search={false} mobile={true} />
        <Container className="dark:bg-slate-900">
          <div className="min-h-screen bg-transparent">{children}</div>
        </Container>
      </div>
    </div>
  );
}
