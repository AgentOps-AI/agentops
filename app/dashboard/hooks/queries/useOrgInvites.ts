import { useQuery } from '@tanstack/react-query';
import { fetchOrgSentInvitesAPI, IOrgInviteWithEmails } from '@/lib/api/orgs';

// Define query key
export const orgPendingInvitesQueryKey = (orgId: string) => ['orgPendingInvites', orgId];

/**
 * Custom hook to fetch pending invitations for a specific organization.
 * This is for admins/owners to view and manage pending invites they've sent.
 * @param orgId - The organization ID to fetch pending invites for
 */
export const useOrgPendingInvites = (orgId: string) => {
  return useQuery<IOrgInviteWithEmails[], Error>({
    queryKey: orgPendingInvitesQueryKey(orgId),
    queryFn: () => fetchOrgSentInvitesAPI(orgId),
    enabled: !!orgId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
