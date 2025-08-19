import { useQuery } from '@tanstack/react-query';
import { fetchOrgDetailAPI, IOrgDetailResponse, IUserOrg } from '@/lib/api/orgs';

export const orgUsersQueryKey = (orgId: string) => ['org-users', orgId];

export function useOrgUsers(orgId: string, orgDetail?: IOrgDetailResponse | null) {
  return useQuery<IUserOrg[]>({
    queryKey: orgUsersQueryKey(orgId),
    queryFn: async () => {
      if (orgDetail) {
        return orgDetail.users || [];
      }
      const detail = await fetchOrgDetailAPI(orgId);
      return detail?.users || [];
    },
    enabled: !!orgId,
  });
}
