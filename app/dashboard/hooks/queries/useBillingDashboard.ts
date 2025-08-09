'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { DateRange } from 'react-day-picker';
import { BillingDashboardResponse } from '@/types/billing.types';

export const billingDashboardQueryKey = (
  orgId: string | null,
  startDate: string | null,
  endDate: string | null,
) => ['billing-dashboard', orgId, startDate, endDate];

const fetchBillingDashboardAPI = async (
  orgId: string,
  startDate: string | null,
  endDate: string | null,
): Promise<BillingDashboardResponse | null> => {
  if (!orgId) return null;

  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const url = `/opsboard/orgs/${orgId}/billing/dashboard?${params.toString()}`;
  return await fetchAuthenticatedApi<BillingDashboardResponse>(url);
};

export const useBillingDashboard = (
  orgId: string | null,
  startDate: string | null,
  endDate: string | null,
) => {
  return useQuery<BillingDashboardResponse | null, Error>({
    queryKey: billingDashboardQueryKey(orgId, startDate, endDate),
    queryFn: () => fetchBillingDashboardAPI(orgId!, startDate, endDate),
    enabled: !!orgId,
  });
};
