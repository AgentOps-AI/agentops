import { useQuery } from '@tanstack/react-query';
import { fetchUserAPI } from '@/lib/api/user';
import { IUser } from '@/types/IUser';

// Define a query key for user data
export const userQueryKey = ['user'];

/**
 * Custom hook to fetch the authenticated user's data using TanStack Query.
 * Returns IUser object or null if not authenticated.
 */
export const useUser = () => {
  return useQuery<IUser | null, Error>({
    queryKey: userQueryKey,
    queryFn: fetchUserAPI,
    // User data is relatively stable but auth state can change
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Keep user data longer if offline support is desired
    // cacheTime: Infinity, // Example: Cache indefinitely
    // If fetchUserAPI returns null (not authenticated), RQ treats it as data: null
  });
};
