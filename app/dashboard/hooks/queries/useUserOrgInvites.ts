import { useQuery } from '@tanstack/react-query';
import { fetchMyPendingInvitesAPI, IOrgInviteResponse } from '@/lib/api/orgs';

// Define query key for user's own invitations
export const userOrgInvitesQueryKey = ['userOrgInvites'];

/**
 * Custom hook to fetch the authenticated user's pending organization invitations.
 * This is for users to see invitations they've received to join organizations.
 */
export const useUserOrgInvites = () => {
  return useQuery<IOrgInviteResponse[], Error>({
    queryKey: userOrgInvitesQueryKey,
    queryFn: async () => {
      const invites = await fetchMyPendingInvitesAPI();
      return invites ?? [];
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
