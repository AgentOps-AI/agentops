import { useQuery } from '@tanstack/react-query';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { useOrgs } from './useOrgs';

interface StripePricingItem {
  priceId: string | null;
  amount: number;
  currency: string;
  unit_size?: number;
  display_unit?: string;
}

interface StripeSeatPricing extends StripePricingItem {
  interval: string;
  interval_count: number | null;
}

interface StripeConfig {
  priceId: string;
  publishableKey: string;
  amount?: number;
  currency?: string;
  interval?: string;
  interval_count?: number;
}

interface StripePricingResponse {
  seat: StripeSeatPricing;
  tokens?: StripePricingItem;
  spans?: StripePricingItem;
}

export const useStripeConfig = () => {
  const { data: orgs } = useOrgs();
  const firstOrgId = orgs?.[0]?.id;

  return useQuery<StripeConfig>({
    queryKey: ['stripe-config', firstOrgId],
    queryFn: async () => {
      const publishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

      if (!publishableKey) {
        throw new Error('Stripe publishable key not found in environment variables');
      }

      let config: StripeConfig = {
        priceId: '', // Will be set from backend API if available
        publishableKey,
      };

      if (firstOrgId) {
        try {
          const pricing = await fetchAuthenticatedApi<StripePricingResponse>(
            `/opsboard/orgs/${firstOrgId}/stripe-pricing`,
          );

          if (pricing?.seat) {
            config = {
              ...config,
              priceId: pricing.seat.priceId || '',
              amount: pricing.seat.amount,
              currency: pricing.seat.currency,
              interval: pricing.seat.interval,
              interval_count: pricing.seat.interval_count || undefined,
            };
          }
        } catch (error) {
          console.warn('Failed to fetch Stripe pricing details:', error);
        }
      }

      return config;
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
    enabled: !!firstOrgId,
  });
};

// New hook specifically for all pricing data including usage costs
export const useAllStripePricing = () => {
  const { data: orgs } = useOrgs();
  const firstOrgId = orgs?.[0]?.id;

  return useQuery<StripePricingResponse>({
    queryKey: ['stripe-pricing-all', firstOrgId],
    queryFn: async () => {
      if (!firstOrgId) {
        throw new Error('No organization available');
      }

      try {
        const pricing = await fetchAuthenticatedApi<StripePricingResponse>(
          `/opsboard/orgs/${firstOrgId}/stripe-pricing`,
        );

        return pricing;
      } catch (error) {
        console.warn('Failed to fetch Stripe pricing from backend, using defaults:', error);
        // Return default pricing structure when backend fails
        return {
          seat: {
            priceId: null,
            amount: 4000, // $40.00 in cents
            currency: 'usd',
            interval: 'month',
            interval_count: 1,
          },
          tokens: {
            priceId: null,
            amount: 0.02, // $0.0002 = 0.02 cents (fractional cents)
            currency: 'usd',
            unit_size: 1000,
            display_unit: 'thousand tokens',
          },
          spans: {
            priceId: null,
            amount: 0.01, // $0.0001 = 0.01 cents (fractional cents)
            currency: 'usd',
            unit_size: 1000,
            display_unit: 'thousand spans',
          },
        };
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1, // Change from false to 1 to allow one retry
    enabled: !!firstOrgId,
  });
};
