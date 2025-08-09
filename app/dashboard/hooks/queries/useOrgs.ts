import { useQuery } from '@tanstack/react-query';
import { fetchOrgsAPI } from '@/lib/api/orgs';
import { IOrg } from '@/types/IOrg';

// Define a query key for organization data
export const orgsQueryKey = ['organizations'];

/**
 * Custom hook to fetch the list of organizations for the current user
 * using TanStack Query.
 */
export const useOrgs = () => {
  return useQuery<IOrg[], Error>({
    queryKey: orgsQueryKey,
    queryFn: fetchOrgsAPI,
    // Stale time can be longer for orgs as they change less frequently
    staleTime: 15 * 60 * 1000, // 15 minutes
    // cacheTime: 60 * 60 * 1000, // 1 hour (optional)
  });
};
