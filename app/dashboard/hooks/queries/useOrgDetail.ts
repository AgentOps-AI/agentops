import { useQuery } from '@tanstack/react-query';
import { fetchOrgDetailAPI, IOrgDetailResponse } from '@/lib/api/orgs';

export const orgDetailQueryKey = (orgId: string) => ['org-detail', orgId];

export const useOrgDetail = (orgId: string) => {
  return useQuery<IOrgDetailResponse | null>({
    queryKey: orgDetailQueryKey(orgId),
    queryFn: () => fetchOrgDetailAPI(orgId),
    enabled: !!orgId,
  });
};
