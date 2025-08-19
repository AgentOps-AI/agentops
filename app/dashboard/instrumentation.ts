import * as Sentry from '@sentry/nextjs';

export async function register() {
  if (process.env.NEXT_PUBLIC_ENVIRONMENT_TYPE === 'AGENTOPS') {
    if (process.env.NEXT_RUNTIME === 'nodejs') {
      await import('./sentry.server.config');
    }

    if (process.env.NEXT_RUNTIME === 'edge') {
      await import('./sentry.server.config');
    }
  }
}

export const onRequestError = Sentry.captureRequestError;
