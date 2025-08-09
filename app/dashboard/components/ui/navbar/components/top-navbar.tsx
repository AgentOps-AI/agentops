'use client';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { AgentOpsButton } from './agentops';
import { ILink, NavLinks } from './navlinks';
import { SidebarLeft01Icon as SidebarIcon } from 'hugeicons-react';
import { useRef } from 'react';
import { UserIcon } from 'hugeicons-react';
import { SmallThemeTogler } from '../../small-theme-togler';
import { ApiKeysButton } from '../../api-keys-button';

export function TopNavbar(props: { helpLinks: ILink[]; dataLinks: ILink[] }) {
  const toogglerRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <div className="flex items-center gap-4 sm:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button size="icon" variant="ghost" className="" ref={toogglerRef}>
              <SidebarIcon className="h-6 w-6" />
              <span className="sr-only">Toggle Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent
            side="left"
            className="group flex min-h-dvh max-w-xs flex-grow flex-col gap-4 px-3 py-2"
          >
            <AgentOpsButton isCollapsed={true}></AgentOpsButton>
            <Separator />
            <NavLinks links={props.dataLinks} onLinkClicked={() => toogglerRef.current?.click()} />
            <Separator />
            <NavLinks links={props.helpLinks} />
            <Separator />
            <div className="grid w-full gap-2">
              <SmallThemeTogler withTitle alignLeft />
              <ApiKeysButton withTitle alignLeft />
            </div>
            <NavLinks
              links={[
                {
                  title: 'Profile',
                  href: '/account',
                  icon: <UserIcon className="h-4 w-4" />,
                  variant: 'ghost',
                  onclick: () => {
                    toogglerRef.current?.click();
                  },
                },
              ]}
              className="mt-auto"
            />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
