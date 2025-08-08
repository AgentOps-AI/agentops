'use client';

import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/app/providers/project-provider';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { DateRange } from 'react-day-picker';
import { formatISO, startOfDay, endOfDay } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { ProjectMetrics } from '@/lib/interfaces';

export const projectMetricsQueryKey = (projectId: string | null, dateRange?: DateRange) => [
  'projectMetrics',
  projectId,
  dateRange?.from ? formatISO(startOfDay(dateRange.from)) : undefined,
  dateRange?.to ? formatISO(endOfDay(dateRange.to)) : undefined,
];

const fetchMetricsAPI = async (
  projectId: string,
  dateRange?: DateRange,
): Promise<ProjectMetrics | null> => {
  if (!projectId) return null;

  // Construct query parameters
  const params = new URLSearchParams();
  if (dateRange?.from) {
    params.set('start_time', formatISO(startOfDay(dateRange.from)));
  }
  if (dateRange?.to) {
    params.set('end_time', formatISO(endOfDay(dateRange.to)));
  }

  try {
    // Use the correct V4 endpoint (with the typo)
    const data = await fetchAuthenticatedApi<ProjectMetrics>(
      `/v4/meterics/project/${projectId}?${params.toString()}`,
    );
    return data;
  } catch (error) {
    console.error(`Error fetching metrics for project ${projectId}:`, error);
    throw error;
  }
};

export function useMetrics(dateRange?: DateRange) {
  const { selectedProject } = useProject();
  const projectId = selectedProject?.id ?? null;
  const queryClient = useQueryClient();

  const query = useQuery<ProjectMetrics | null, Error>({
    queryKey: projectMetricsQueryKey(projectId, dateRange),
    queryFn: () => fetchMetricsAPI(projectId!, dateRange),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - matches backend cache TTL
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes (was cacheTime)
    refetchOnWindowFocus: false, // Don't refetch when tab gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
    refetchInterval: false, // No automatic refetching
  });

  const refreshMetrics = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: projectMetricsQueryKey(projectId, dateRange),
    });
  }, [queryClient, projectId, dateRange]);

  return {
    metrics: query.data,
    refreshMetrics,
    metricsLoading: query.isLoading,
    error: query.error,
    isFetching: query.isFetching,
  };
}
