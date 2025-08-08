'use client';

import { Separator } from '@radix-ui/react-separator';
import Link from 'next/link';
import AgentOpsBanner from '@/components/icons/AgentOpsBanner';
import { BackgroundImageOverlay } from '@/components/ui/background-image-overlay';
import { Container } from '@/components/ui/container';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <>
      <nav className="fixed left-0 right-0 top-0 z-10 bg-white dark:bg-slate-950">
        <BackgroundImageOverlay
          additionalStyles={{
            backgroundRepeat: 'repeat',
            backgroundSize: '6px 6px',
          }}
          backgroundImageUrl="url(/image/diagonal-pattern.svg)"
          opacity={0.04}
        />
        <div className="flex items-center justify-between bg-[#F4F5FF] px-4 py-5 dark:bg-slate-900 sm:px-8">
          <div className="relative flex items-center gap-5 sm:gap-2">
            <Link href={'/'}>
              <AgentOpsBanner />
            </Link>
          </div>
          <div className="relative flex items-center gap-3"></div>
        </div>
        <div className="bg-muted/40 px-6 sm:px-10"></div>
        <div className="border-b border-gray-200 dark:border-gray-800"></div>
      </nav>

      <div className="flex justify-center"></div>

      <Container
        backgroundImageUrl="url(/image/diagonal-pattern.svg)"
        backgroundOpacity={0.04}
        styleProps={{
          backgroundRepeat: 'repeat',
          backgroundSize: '6px 6px',
        }}
        className="h-[100svh] overflow-hidden border-t border-gray-200 bg-[#F4F5FF] pt-10 dark:border-gray-800 dark:bg-slate-900"
      >
        <div className="align-center mx-auto max-w-7xl items-center justify-center px-4 py-4 pt-10 sm:px-6 lg:px-8">
          <div className="align-center mb-20 mt-10 flex flex-col items-center justify-center">
            <h2 className="text-4xl font-medium text-primary">
              <b>404</b> Page not found{' '}
            </h2>
            <h3 className="mt-4 text-xl font-normal text-gray-600 dark:text-gray-400">
              {`Sorry, we couldn't find the page you're looking for.`}
            </h3>
            <Separator className="mt-8" />
            <Link href="/">
              <Button>Go back</Button>
            </Link>
          </div>
        </div>
      </Container>
    </>
  );
}
