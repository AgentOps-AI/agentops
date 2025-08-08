import { ThemeProvider } from '@/components/theme-provider';
import { Banner } from '@/components/ui/banner';
import { Toaster } from '@/components/ui/toaster';
import { cn } from '@/lib/utils';
import { Figtree } from 'next/font/google';
import localFont from 'next/font/local';
import Link from 'next/link';
import { PropsWithChildren } from 'react';
import './globals.css';
import { BackgroundImageOverlay } from '@/components/ui/background-image-overlay';
import { PostHogProvider } from '@/app/providers/posthog-provider';

const figtreeFont = Figtree({
  subsets: ['latin'],
  variable: '--font-figtree',
});

const nasalizationFont = localFont({
  src: '../public/font/nasalization/nasalization-rg.otf',
  variable: '--font-nasalization',
});

const meta = {
  title: 'AgentOps Dashboard',
  description: 'Build your next agent with evals, observability, and replays.',
  cardImage: '/og.png',
  robots: 'follow, index',
  favicon: '/favicon.ico',
  url: 'https://app.agentops.ai',
  metadataBase: new URL('https://app.agentops.ai'),
  type: 'website',
};

export const metadata = {
  metadataBase: meta.metadataBase,
  title: meta.title,
  description: meta.description,
  cardImage: meta.cardImage,
  robots: meta.robots,
  favicon: meta.favicon,
  url: meta.url,
  type: meta.type,
  openGraph: {
    url: meta.url,
    title: meta.title,
    description: meta.description,
    cardImage: meta.cardImage,
    type: meta.type,
    site_name: meta.title,
  },
  twitter: {
    card: 'summary_large_image',
    site: '@areibman',
    title: meta.title,
    description: meta.description,
    cardImage: meta.cardImage,
  },
};

export default async function RootLayout({ children }: PropsWithChildren) {
  const showBanner = process.env.NEXT_PUBLIC_PLAYGROUND === 'true';
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body
        className={cn(
          'min-h-screen bg-background antialiased',
          figtreeFont.className,
          figtreeFont.variable,
          nasalizationFont.variable,
          'bg-[#F4F5FF] dark:bg-slate-900',
        )}
      >
        <BackgroundImageOverlay
          backgroundImageUrl="url(/image/diagonal-pattern.svg)"
          opacity={0.04}
          additionalStyles={{
            backgroundRepeat: 'repeat',
            backgroundSize: '6px 6px',
            position: 'fixed',
            userSelect: 'none',
            pointerEvents: 'none',
          }}
        />
        <ThemeProvider attribute="class" defaultTheme="light" disableTransitionOnChange>
          <PostHogProvider>
            <Banner
              message={
                <div>
                  You are using AgentOps in Playground Mode. To access full features and save your
                  traces, log in or create an account. Upgrade here or{' '}
                  <Link
                    className="underline underline-offset-2"
                    href="https://cal.com/team/agency-ai/agentops-feedback"
                  >
                    give us feedback
                  </Link>{' '}
                  to unlock more free credits
                </div>
              }
              visible={showBanner}
            />

            {children}
            <Toaster />
          </PostHogProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
