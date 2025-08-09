'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/app/providers/project-provider';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { DateRange } from 'react-day-picker';
import { useCallback } from 'react';
import { TraceMetrics } from '@/lib/interfaces';
import { ITrace } from '@/types/ITrace';

export interface PaginatedTracesResponse {
  traces: ITrace[];
  metrics: TraceMetrics;
  total: number;
  offset: number;
  limit: number;
}

export const tracesQueryKey = (
  projectId: string | null,
  dateRange?: DateRange,
  searchQuery?: string,
  pageIndex?: number,
  pageSize?: number,
) => [
    'traces',
    projectId,
    searchQuery,
    dateRange?.from?.toISOString(),
    dateRange?.to?.toISOString(),
    pageIndex,
    pageSize,
  ];

const fetchTracesAPI = async (
  projectId: string,
  dateRange?: DateRange,
  searchQuery?: string,
  limit: number = 20,
  offset: number = 0,
  signal?: AbortSignal,
): Promise<PaginatedTracesResponse> => {
  if (!projectId)
    return { traces: [], metrics: {} as TraceMetrics, total: 0, offset: 0, limit: limit };

  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (searchQuery) {
    params.set('query', searchQuery);
  }
  if (dateRange?.from) {
    params.set('start_time', dateRange.from.toISOString());
  }
  if (dateRange?.to) {
    params.set('end_time', dateRange.to.toISOString());
  }

  try {
    const data = await fetchAuthenticatedApi<PaginatedTracesResponse>(
      `/v4/traces/list/${projectId}?${params.toString()}`,
      { signal },
    );
    return data || { traces: [], metrics: {} as TraceMetrics, total: 0, offset: 0, limit: limit };
  } catch (error) {
    console.error(`Error fetching traces for project ${projectId}:`, error);
    return { traces: [], metrics: {} as TraceMetrics, total: 0, offset: 0, limit: limit };
  }
};

export const useTraces = (
  dateRange?: DateRange,
  searchQuery?: string,
  pageIndex: number = 0,
  pageSize: number = 20,
) => {
  const { selectedProject } = useProject();
  const projectId = selectedProject?.id ?? null;
  const queryClient = useQueryClient();
  const query = useQuery<PaginatedTracesResponse, Error>({
    queryKey: tracesQueryKey(projectId, dateRange, searchQuery, pageIndex, pageSize),
    queryFn: ({ signal }: { signal?: AbortSignal }) => {
      const offset = pageIndex * pageSize;
      return fetchTracesAPI(projectId!, dateRange, searchQuery, pageSize, offset, signal);
    },
    enabled: !!projectId,
    placeholderData: (previousData) => previousData,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchInterval: false,
  });

  const refetchTraces = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: tracesQueryKey(projectId, dateRange, searchQuery),
    });
  }, [queryClient, projectId, dateRange, searchQuery]);

  return {
    ...query,
    refetchTraces,
    tracesData: query.data,
    totalTraces: query.data?.total ?? 0,
  };
};
