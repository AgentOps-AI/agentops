'use client';

import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/app/providers/project-provider';
import { ISpan } from '@/types/ISpan';
import { fetchAuthenticatedApi } from '@/lib/api-client';

type TraceDetailResponse = {
  id: string;
  timestamp: string;
  spans: ISpan[];
  metadata?: Record<string, any> | null;
};

export const traceDetailQueryKey = (traceId: string | null) => ['traceDetail', traceId];

/**
 * Fetches detailed data for a specific trace/session by its ID.
 */
const fetchTraceDetailAPI = async (
  traceId: string,
  projectId: string | null,
): Promise<TraceDetailResponse | null> => {
  if (!traceId || !projectId) {
    return null;
  }
  try {
    const data = await fetchAuthenticatedApi<TraceDetailResponse>(`/v4/traces/detail/${traceId}`);
    return data;
  } catch (error) {
    console.error(`Error fetching trace detail for ${traceId}:`, error);
    throw error;
  }
};

/**
 * Custom hook to fetch details for a specific trace using TanStack Query.
 *
 * @param traceId The ID of the trace to fetch. Query is disabled if null.
 */
export const useTraceDetail = (traceId: string | null) => {
  const { selectedProject } = useProject();
  const projectId = selectedProject?.id ?? null;

  const query = useQuery<TraceDetailResponse | null, Error>({
    queryKey: traceDetailQueryKey(traceId),
    queryFn: () => fetchTraceDetailAPI(traceId!, projectId),
    enabled: !!traceId && !!projectId,
    staleTime: 5 * 60 * 1000,
    retry: 5,
    retryDelay: (attemptIndex) => {
      // First retry immediately, then use exponential backoff with shorter delays
      if (attemptIndex === 0) return 0;
      return Math.min(500 * Math.pow(2, attemptIndex - 1), 2000); // 0ms, 500ms, 1000ms, 2000ms, 2000ms
    },
  });

  return {
    traceDetail: query.data,
    isLoading: query.isLoading,
    error: query.error,
    isFetching: query.isFetching,
    refetch: query.refetch,
    failureCount: query.failureCount,
    isError: query.isError,
  };
};
