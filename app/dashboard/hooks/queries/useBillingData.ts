import { useUser } from './useUser';
import { useOrgs } from './useOrgs';
import { useStripeConfig, useAllStripePricing } from './useStripeConfig';

export interface BillingData {
  user: ReturnType<typeof useUser>['data'];
  orgs: ReturnType<typeof useOrgs>['data'];
  stripeConfig: ReturnType<typeof useStripeConfig>['data'];
  pricing: ReturnType<typeof useAllStripePricing>['data'];
}

export interface BillingLoadingState {
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  loadingStates: {
    user: boolean;
    orgs: boolean;
    stripeConfig: boolean;
    pricing: boolean;
  };
}

/**
 * Unified hook for all billing-related data fetching
 * Provides a single loading state and error handling
 */
export function useBillingData() {
  const userQuery = useUser();
  const orgsQuery = useOrgs();
  const stripeConfigQuery = useStripeConfig();
  const pricingQuery = useAllStripePricing();

  const loadingStates = {
    user: userQuery.isLoading,
    orgs: orgsQuery.isLoading,
    stripeConfig: stripeConfigQuery.isLoading,
    pricing: pricingQuery.isLoading,
  };

  const isLoading = Object.values(loadingStates).some(Boolean);
  const isError = [userQuery, orgsQuery, stripeConfigQuery, pricingQuery].some((q) => q.isError);
  const error =
    [userQuery, orgsQuery, stripeConfigQuery, pricingQuery].find((q) => q.error)?.error || null;

  const data: BillingData = {
    user: userQuery.data,
    orgs: orgsQuery.data,
    stripeConfig: stripeConfigQuery.data,
    pricing: pricingQuery.data,
  };

  const refetch = {
    user: userQuery.refetch,
    orgs: orgsQuery.refetch,
    stripeConfig: stripeConfigQuery.refetch,
    pricing: pricingQuery.refetch,
    all: async () => {
      await Promise.all([
        userQuery.refetch(),
        orgsQuery.refetch(),
        stripeConfigQuery.refetch(),
        pricingQuery.refetch(),
      ]);
    },
  };

  return {
    data,
    loadingState: {
      isLoading,
      isError,
      error,
      loadingStates,
    } as BillingLoadingState,
    refetch,

    // Individual query states for granular control
    queries: {
      user: userQuery,
      orgs: orgsQuery,
      stripeConfig: stripeConfigQuery,
      pricing: pricingQuery,
    },
  };
}
