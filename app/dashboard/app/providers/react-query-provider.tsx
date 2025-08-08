'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

interface ReactQueryProviderProps {
  children: React.ReactNode;
}

/**
 * Provider for setting up and configuring React Query.
 * This component initializes a QueryClient and makes it available to its children
 * via the QueryClientProvider. It also includes ReactQueryDevtools for debugging.
 *
 * @param {ReactQueryProviderProps} props - The component props.
 * @param {React.ReactNode} props.children - The child components that will have access to React Query.
 * @returns {JSX.Element} The QueryClientProvider wrapping the children.
 */
export default function ReactQueryProvider({ children }: ReactQueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* This is purely for debugging, and automatically wont be shown in production */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
