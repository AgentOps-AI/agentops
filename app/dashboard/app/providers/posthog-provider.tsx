// app/providers.tsx
'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import { usePostHog } from 'posthog-js/react';

import posthog from 'posthog-js';
import { PostHogProvider as PHProvider } from 'posthog-js/react';

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const isProd = process.env.NODE_ENV === 'production';

  // Initialise PostHog only in production builds to avoid noisy 401/404 errors
  useEffect(() => {
    if (!isProd) return;

    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;

    // Only initialize PostHog if we have a valid key and we're not in development without it
    if (posthogKey && posthogKey.trim() !== '') {
      console.log('Initializing PostHog with key:', posthogKey.substring(0, 8) + '...');
      posthog.init(posthogKey, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
        person_profiles: 'identified_only', // or 'always' to create profiles for anonymous users as well
        capture_pageview: false, // Disable automatic pageview capture, as we capture manually
      });
    } else {
      console.log('PostHog disabled: No NEXT_PUBLIC_POSTHOG_KEY provided or key is empty');
    }
  }, [isProd]);

  // When not in production, skip rendering the PostHogProvider entirely
  if (!isProd) {
    return <>{children}</>;
  }

  return (
    <PHProvider client={posthog}>
      <SuspendedPostHogPageView />
      {children}
    </PHProvider>
  );
}

function PostHogPageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const posthog = usePostHog();

  // Track pageviews only if PostHog is properly initialized
  useEffect(() => {
    // Check if PostHog is available and properly loaded
    if (pathname && posthog && posthog.__loaded && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
      let url = window.origin + pathname;
      if (searchParams.toString()) {
        url = url + '?' + searchParams.toString();
      }

      posthog.capture('$pageview', { $current_url: url });
    }
  }, [pathname, searchParams, posthog]);

  return null;
}

// Wrap PostHogPageView in Suspense to avoid the useSearchParams usage above
// from de-opting the whole app into client-side rendering
// See: https://nextjs.org/docs/messages/deopted-into-client-rendering
function SuspendedPostHogPageView() {
  return (
    <Suspense fallback={null}>
      <PostHogPageView />
    </Suspense>
  );
}
