/** @type {import('next').NextConfig} */

// This file sets a custom webpack configuration to use your Next.js app
// with Sentry.
// https://nextjs.org/docs/api-reference/next.config.js/introduction
const { withSentryConfig } = require('@sentry/nextjs');
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
  openAnalyzer: false,
  outputDir: process.env.ANALYZE === 'true' ? './bundle_analytics' : '.next/analyze',
});

// Check if code instrumentation is enabled via environment variable
// const shouldInstrument = process.env.INSTRUMENT_CODE === 'true'; // Keep for reference, but comment out

const nextConfig = {
  reactStrictMode: true,
  env: {
    VERCEL_BUILD_HASH: process.env.VERCEL_GIT_COMMIT_SHA,
  },
  experimental: {
    serverActions: {
      timeout: 65,
    },
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
        port: '',
      },
    ],
    // formats: ['image/avif', 'image/webp'], // TODO: add formats
  },

  // Conditionally add Babel configuration for istanbul plugin - REMOVED FOR NOW
  // Only add Babel config if instrumentation is needed, otherwise let Next.js use SWC
  // ...(shouldInstrument && {
  //   compiler: {
  //     // Force Babel usage when instrumenting
  //     // This overrides Next.js's default SWC compiler
  //     forceSwcTransforms: false,
  //   },
  //   webpack: (config, { isServer }) => {
  //     // Add babel-loader rule
  //     config.module.rules.push({
  //       test: /\.(js|jsx|ts|tsx)$/,
  //       exclude: /node_modules/,
  //       use: {
  //         loader: 'babel-loader',
  //         options: {
  //           presets: ['next/babel'],
  //           plugins: [
  //             // Add istanbul plugin only when instrumenting
  //             'istanbul',
  //           ],
  //         },
  //       },
  //     });
  //     return config;
  //   },
  // }),

  // This is required to support PostHog trailing slash API requests
  skipTrailingSlashRedirect: true,

  async rewrites() {
    return [
      {
        source: '/ingest/static/:path*',
        destination: 'https://us-assets.i.posthog.com/static/:path*',
      },
      {
        source: '/ingest/:path*',
        destination: 'https://us.i.posthog.com/:path*',
      },
      {
        source: '/ingest/decide',
        destination: 'https://us.i.posthog.com/decide',
      },
      {
        source: '/functions/v1/:path*',
        destination: 'https://qjkcnuesiiqjpohzdjjm.supabase.co/functions/v1/:path*',
      },
      {
        source: '/auth/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/:path*`,
      },
      {
        source: '/opsboard/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/opsboard/:path*`,
      },
      {
        source: '/logs/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'https://api.agentops.ai'}/v3/logs/:path*`,
      },
      {
        source: '/api-v4/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'https://api.agentops.ai'}/:path*`,
      },
      {
        source: '/api-metrics/:path*',
        destination: 'http://0.0.0.0:8000/:path*',
      },
    ];
  },

  async redirects() {
    return [
      {
        source: '/drilldown',
        destination: '/traces',
        permanent: true,
      },
      {
        source: '/sessions',
        destination: '/traces',
        permanent: true,
      },
      {
        source: '/sessions/:path*',
        destination: '/traces/:path*',
        permanent: true,
      },
    ];
  },
};

const sentryOptions = {
  // Additional config options for the Sentry webpack plugin. Keep in mind that
  // the following options are set automatically, and overriding them is not
  // recommended:
  //   release, url, configFile, stripPrefix, urlPrefix, include, ignore

  org: process?.env?.NEXT_PUBLIC_SENTRY_ORG,
  project: process?.env?.NEXT_PUBLIC_SENTRY_PROJECT,

  // An auth token is required for uploading source maps.
  authToken: process?.env?.SENTRY_AUTH_TOKEN,

  // Suppresses source map uploading logs during build
  silent: true,

  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options.
  widenClientFileUpload: true,

  // Transpiles SDK to be compatible with IE11 (increases bundle size)
  transpileClientSDK: false,

  // Automatically annotate React components to show their full name in breadcrumbs and session replay
  reactComponentAnnotation: {
    enabled: true,
  },

  // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
  // This can increase your server load as well as your hosting bill.
  // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
  // side errors will fail.
  tunnelRoute: '/monitoring-tunnel',

  // Hides source maps from generated client bundles
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/#use-hidden-source-map
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Enables automatic instrumentation of Vercel Cron Monitors.
  // See the following for more information:
  // https://docs.sentry.io/product/crons/
  // https://vercel.com/docs/cron-jobs
  automaticVercelMonitors: true,
};

// Make sure adding Sentry options is the last code to run before exporting
// Only use senty in prod
const config =
  process.env.NODE_ENV === 'production' ? withSentryConfig(nextConfig, sentryOptions) : nextConfig;

module.exports = withBundleAnalyzer(config);
