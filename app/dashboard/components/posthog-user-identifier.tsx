'use client';

import { useEffect } from 'react';
import { usePostHog } from 'posthog-js/react';
import { useUser } from '@/hooks/queries/useUser';

export function PostHogUserIdentifier() {
  const { data: user } = useUser();
  const posthog = usePostHog();

  useEffect(() => {
    // Only interact with PostHog if it's actually loaded
    // This prevents errors when analytics are disabled in local development
    if (!posthog || !(posthog as any).__loaded) return;

    if (user?.id) {
      posthog.identify(user.id, {
        email: user.email || undefined,
        name: user.full_name || undefined,
      });
    } else if (!user) {
      posthog.reset();
    }
  }, [posthog, user]);

  return null;
}
