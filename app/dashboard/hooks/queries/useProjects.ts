import { useQuery, UseQueryOptions, useQueryClient } from '@tanstack/react-query';
import { fetchProjects } from '@/lib/api/projects';
import { IProject, IHostingProject } from '@/types/IProject';
import { fetchDeployments, fetchDeploymentHistory, DeploymentHistoryResponse } from '@/lib/api/projects';

export const projectsQueryKey = ['projects'];

/**
 * Custom hook to fetch user projects, optionally filtering by organization.
 */
// Add optional orgId parameter and options parameter
export const useProjects = (
  orgId?: string,
  options?: Omit<UseQueryOptions<IProject[], Error, IProject[]>, 'queryKey' | 'queryFn' | 'select'>,
) => {
  return useQuery<IProject[], Error, IProject[]>({
    queryKey: projectsQueryKey,
    queryFn: fetchProjects,
    staleTime: 10 * 60 * 1000, // 10 minutes - projects don't change frequently
    gcTime: 60 * 60 * 1000, // Keep in cache for 1 hour
    refetchOnWindowFocus: false, // Don't refetch when tab gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
    select: (allProjects) => {
      if (!orgId) {
        return allProjects ?? [];
      }
      return allProjects?.filter((project) => project.org.id === orgId) ?? [];
    },
    ...options,
  });
};

/**
 * Custom hook to fetch a single project by ID, using the cached list if available.
 */
export const useProject = (projectId?: string) => {
  const queryClient = useQueryClient();
  const projects = queryClient.getQueryData<IProject[]>(projectsQueryKey);
  const project = projects?.find((p) => p.id === projectId);
  // Optionally, you could trigger a refetch if not found, but for now just return the cached value
  return { project };
};

export const deploymentsQueryKey = ['deployments'];

export const useDeployments = (
  options?: Omit<UseQueryOptions<IHostingProject[], Error, IHostingProject[]>, 'queryKey' | 'queryFn' | 'select'>,
) => {
  return useQuery<IHostingProject[], Error, IHostingProject[]>({
    queryKey: deploymentsQueryKey,
    queryFn: fetchDeployments,
    staleTime: 10 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    ...options,
  });
};

/**
 * Custom hook to fetch a single deployment by ID, using the deployments query and returning loading/error states.
 */
export const useDeployment = (deploymentId?: string) => {
  const { data: deployments, isLoading, error } = useDeployments();
  const deployment = deployments?.find((d) => d.id === deploymentId);
  return { deployment, isLoading, error };
};

export const deploymentHistoryQueryKey = (projectId: string) => ['deployment-history', projectId];

/**
 * Custom hook to fetch deployment history for a specific project.
 */
export const useDeploymentHistory = (
  projectId?: string,
  options?: Omit<UseQueryOptions<DeploymentHistoryResponse, Error, DeploymentHistoryResponse>, 'queryKey' | 'queryFn'>,
) => {
  return useQuery<DeploymentHistoryResponse, Error, DeploymentHistoryResponse>({
    queryKey: deploymentHistoryQueryKey(projectId || ''),
    queryFn: () => fetchDeploymentHistory(projectId!),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    ...options,
  });
};


