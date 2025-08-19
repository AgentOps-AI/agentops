import { useProject } from '@/app/providers/project-provider';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { IOrg } from '@/types/IOrg';
import { OrgFeaturePermissions, getDerivedPermissions } from '@/types/IPermissions';

interface UseOrgFeaturesReturn {
  premStatus: string | null;
  isLoading: boolean;
  error: Error | null;
  orgDetails: IOrg | null;
  permissions: OrgFeaturePermissions | null;
}

/**
 * Hook to fetch organization details based on the selected project's org.
 * This is now independent of ProjectProvider to avoid circular dependencies.
 */
export function useActiveOrg() {
  const { selectedProject } = useProject();
  const orgId = selectedProject?.org_id || selectedProject?.org?.id;

  return useQuery<IOrg | null, Error>({
    queryKey: ['org', orgId],
    queryFn: async () => {
      if (!orgId) return null;
      return fetchAuthenticatedApi<IOrg>(`/opsboard/orgs/${orgId}`);
    },
    enabled: !!orgId,
    staleTime: 30 * 1000, // 30 seconds - reduced for faster subscription updates
    // Return null immediately if no orgId to prevent loading state
    initialData: orgId ? undefined : null,
  });
}

/**
 * Simplified hook to access organization premium status and details.
 * Now fetches org data independently to avoid circular dependencies.
 */
export function useOrgFeatures(): UseOrgFeaturesReturn {
  const {
    data: activeOrgDetails,
    isLoading: isOrgDataLoading,
    error: orgFetchError,
  } = useActiveOrg();
  const { selectedProject } = useProject();

  // Always call useMemo to maintain hooks order
  const permissions = useMemo(() => {
    if (!activeOrgDetails) return null;
    return getDerivedPermissions(activeOrgDetails);
  }, [activeOrgDetails]);

  // If no project is selected, return null status without loading
  if (!selectedProject) {
    return {
      premStatus: null,
      isLoading: false,
      error: null,
      orgDetails: null,
      permissions: null,
    };
  }

  const premStatus = activeOrgDetails?.prem_status || 'free';

  return {
    premStatus,
    isLoading: isOrgDataLoading,
    error: orgFetchError,
    orgDetails: activeOrgDetails || null,
    permissions,
  };
}

// Simple helper functions for common checks
export const isFreeUser = (premStatus: string | null) => {
  return !premStatus || premStatus.toLowerCase() === 'free';
};

export const isProUser = (premStatus: string | null) => {
  return premStatus?.toLowerCase() === 'pro';
};

// Simple constants for limits
export const LIMITS = {
  free: {
    tracesLookbackDays: 3,
    metricsLookbackDays: 30,
    logsLookbackDays: 3,
    spanWaterfallLimit: 30,
    logLinesLimit: 100,
    maxSpansMonthly: 5000,
    maxProjects: 1,
    maxSeats: 1,
  },
  pro: {
    tracesLookbackDays: 365 * 10, // effectively unlimited
    metricsLookbackDays: 365 * 10,
    logsLookbackDays: 365 * 10,
    spanWaterfallLimit: null, // unlimited
    logLinesLimit: null,
    maxSpansMonthly: 100000,
    maxProjects: null,
    maxSeats: null,
  },
};
