// This file configures the initialization of Sentry on the client.
// The config you add here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from '@sentry/nextjs';

if (process.env.NEXT_PUBLIC_ENVIRONMENT_TYPE === 'AGENTOPS') {
  Sentry.init({
    dsn: process?.env?.NEXT_PUBLIC_SENTRY_DSN,
    environment: process?.env?.NEXT_PUBLIC_SENTRY_ENVIRONMENT,

    // Adjust this value in production, or use tracesSampler for greater control
    tracesSampleRate: 1,

    // Setting this option to true will print useful information to the console while you're setting up Sentry.
    debug: false,

    replaysOnErrorSampleRate: 1.0,

    // This sets the sample rate to be 10%. You may want this to be 100% while
    // in development and sample at a lower rate in production
    replaysSessionSampleRate: 0.0,

    // You can remove this option if you're not planning to use the Sentry Session Replay feature:
    integrations: [
      Sentry.replayIntegration({
        // Additional Replay configuration goes in here, for example:
        maskAllText: false,
        blockAllMedia: true,
      }),
      Sentry.feedbackIntegration({
        autoInject: false,
        showBranding: false,
        // Additional SDK configuration goes in here, for example:
      }),
    ],
    beforeSend(event, hint) {
      // Filter out PostHog events
      if (event?.request?.url?.includes('/ingest/s/')) {
        return null;
      }

      // Filter out events from this crawler
      if (document?.referrer?.includes('baidu.com')) {
        return null;
      }

      return event;
    },
  });
}
