'use client';
import Logo from '@/components/icons/Logo';
import { useEffect, useState } from 'react';
import { SearchInput } from './search-input';
import { useRouter } from 'next/navigation';
import { getTutorialSkipped, setTutorialSkipped } from '@/lib/idb';
import { Separator } from '../separator';
import { NavbarClient } from '../navbar/navbar-client';
import { BackgroundImageOverlay } from '../background-image-overlay';
import { useHeaderContext } from '@/app/providers/header-provider';
import { toast } from '../use-toast';
import { ChartLineData01Icon as OverviewIcon } from 'hugeicons-react';
import { cn } from '@/lib/utils';

export const Header = ({ search, mobile }: { search: boolean; mobile: boolean }) => {
  const router = useRouter();
  const { headerNotification, headerTitle, headerContent } = useHeaderContext();
  const [_forceDropdownOpen, setForceDropdownOpen] = useState<boolean>(false);
  const [isSkippedTutorial, setIsSkippedTutorial] = useState<boolean>(getTutorialSkipped());

  function handleSkipTutorial() {
    setTutorialSkipped(true);
    setIsSkippedTutorial(true);
    setForceDropdownOpen(false);
    toast({
      icon: <Logo className="h-[24px] w-[24px]" />,
      title: 'Hi, and welcome',
      description: (
        <div>
          Your new project has been set up, head over to the{' '}
          <div className="flex items-center gap-1">
            <OverviewIcon className="h-[15px] w-[15px]" />
            <div className="cursor-pointer underline" onClick={() => router.push('/overview')}>
              dashboard
            </div>{' '}
            for in-depth analysis.
          </div>
        </div>
      ),
    });
  }

  // this is so silly
  useEffect(() => {
    if (headerNotification) setForceDropdownOpen(true);
  }, [headerNotification]);

  return (
    <>
      <nav className="sticky left-0 right-0 top-0 z-10 backdrop-blur-md dark:bg-slate-950">
        <BackgroundImageOverlay
          additionalStyles={{
            backgroundRepeat: 'repeat',
            backgroundSize: '6px 6px',
            zIndex: 10,
          }}
          backgroundImageUrl="url(/image/diagonal-pattern.svg)"
          opacity={0.04}
        />

        {/* <PremiumAccountChecker /> */}

        <div
          className={cn(
            'relative h-[60px] w-full px-2 dark:bg-slate-900',
            'flex items-center justify-between',
          )}
        >
          {/* Left section */}
          <div className="relative z-[9999] flex items-center gap-5 sm:gap-2">
            <NavbarClient mobile={mobile} />

            {headerTitle && (
              <h2 className="my-auto flex h-[34px] items-center text-2xl font-medium text-primary">
                {headerTitle}
              </h2>
            )}

            {search && (
              <div className="ml-5 hidden md:flex">
                <SearchInput />
              </div>
            )}
          </div>

          {/* Right section */}
          <div>
            {headerContent !== null && (
              <div className="relative z-[1000]">
                <div className="rounded-md bg-[#E3E5F8] p-1 dark:bg-[#151924]">{headerContent}</div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-muted/40">
          <Separator className="w-full" color="#DEE0F4" />
        </div>
      </nav>

      {headerNotification && !isSkippedTutorial && (
        <div className="fixed bottom-4 left-[66px] z-[9999] rounded-2xl border border-white bg-[#F7F8FF] p-5 shadow-2xl dark:border-slate-800 dark:bg-slate-800 sm:h-40 sm:w-[271px] sm:rounded-2xl">
          <div className="relative">
            <div className="font-medium text-primary">Your profile</div>
            <div className="mt-3 pr-2 text-sm font-medium text-secondary dark:text-white">
              Here you can view your API key. Every time you create a project the key will be held
              here.
            </div>
            <div
              className="mt-3 flex cursor-pointer justify-end text-sm font-medium text-secondary dark:text-white"
              onClick={handleSkipTutorial}
            >
              Done
            </div>
          </div>
        </div>
      )}
    </>
  );
};
