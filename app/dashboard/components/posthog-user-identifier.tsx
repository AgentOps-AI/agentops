'use client';

import { useEffect } from 'react';
import { usePostHog } from 'posthog-js/react';
import { useUser } from '@/hooks/queries/useUser';

export function PostHogUserIdentifier() {
  const { data: user } = useUser();
  const posthog = usePostHog();

  useEffect(() => {
    // Only proceed if PostHog is available and initialized
    if (posthog && posthog.__loaded) {
      if (user?.id) {
        posthog.identify(user.id, {
          email: user.email || undefined,
          name: user.full_name || undefined,
        });
      } else if (!user) {
        posthog.reset();
      }
    }
  }, [posthog, user]);

  return null;
}
