import { useQuery } from '@tanstack/react-query';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { DateRange } from 'react-day-picker';
import { format } from 'date-fns';

interface ProjectBillingData {
  project_id: string;
  project_name: string;
  tokens: number;
  spans: number;
  token_cost: number;
  span_cost: number;
  total_cost: number;
}

interface BillingResponse {
  project_breakdown?: ProjectBillingData[];
}

export const projectBillingQueryKey = (
  orgId: string | null,
  projectId: string | null,
  dateRange: DateRange | undefined,
) => [
  'project-billing',
  orgId,
  projectId,
  dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : null,
  dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : null,
];

const fetchProjectBilling = async (
  orgId: string,
  projectId: string,
  dateRange: DateRange | undefined,
): Promise<ProjectBillingData | null> => {
  if (!orgId || !projectId) {
    return null;
  }

  const params = new URLSearchParams();
  if (dateRange?.from) {
    params.append('start_date', format(dateRange.from, "yyyy-MM-dd'T'HH:mm:ss'Z'"));
  }
  if (dateRange?.to) {
    params.append('end_date', format(dateRange.to, "yyyy-MM-dd'T'HH:mm:ss'Z'"));
  }
  params.append('project_id', projectId);

  const url = `/opsboard/orgs/${orgId}/billing/dashboard?${params.toString()}`;

  const response = await fetchAuthenticatedApi<BillingResponse>(url);

  // The endpoint returns project_breakdown array, we need to find our project
  if (response?.project_breakdown && response.project_breakdown.length > 0) {
    const projectData = response.project_breakdown.find((p) => p.project_id === projectId);
    return projectData || null;
  }

  return null;
};

export const useBillingForProject = (
  orgId: string | null,
  projectId: string | null,
  dateRange: DateRange | undefined,
) => {
  return useQuery<ProjectBillingData | null>({
    queryKey: projectBillingQueryKey(orgId, projectId, dateRange),
    queryFn: () => fetchProjectBilling(orgId!, projectId!, dateRange),
    enabled: !!orgId && !!projectId,
  });
};
