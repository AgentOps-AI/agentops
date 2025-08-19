interface StripePricing {
  seat?: { amount: number; interval: string };
  tokens?: { amount: number };
  spans?: { amount: number };
}

/**
 * Calculate token cost using standardized billing rates
 * @param tokenCount - Number of tokens
 * @param allPricing - Stripe pricing data
 * @returns Cost in dollars
 */
export function calculateTokenCost(tokenCount: number, allPricing?: StripePricing): number {
  if (!tokenCount || tokenCount <= 0) return 0;

  // Price per 1M tokens in dollars
  const tokenPricePerMillion = ((allPricing?.tokens?.amount || 0.02) * 1000) / 100;

  return (tokenCount / 1_000_000) * tokenPricePerMillion;
}

/**
 * Calculate span cost using standardized billing rates
 * @param spanCount - Number of spans
 * @param allPricing - Stripe pricing data
 * @returns Cost in dollars
 */
export function calculateSpanCost(spanCount: number, allPricing?: StripePricing): number {
  if (!spanCount || spanCount <= 0) return 0;

  // Price per 1K spans in dollars
  const spanPricePerThousand = (allPricing?.spans?.amount || 0.01) / 100;

  return (spanCount / 1_000) * spanPricePerThousand;
}

/**
 * Calculate total usage cost (tokens + spans)
 * @param tokenCount - Number of tokens
 * @param spanCount - Number of spans
 * @param allPricing - Stripe pricing data
 * @returns Total cost in dollars
 */
export function calculateUsageCost(
  tokenCount: number,
  spanCount: number,
  allPricing?: StripePricing,
): number {
  return calculateTokenCost(tokenCount, allPricing) + calculateSpanCost(spanCount, allPricing);
}

/**
 * Get pricing rates for display
 * @param allPricing - Stripe pricing data
 * @returns Pricing rates in dollars
 */
export function getPricingRates(allPricing?: StripePricing) {
  const tokenPricePerMillion = ((allPricing?.tokens?.amount || 0.02) * 1000) / 100;
  const spanPricePerThousand = (allPricing?.spans?.amount || 0.01) / 100;

  return {
    tokenPricePerMillion,
    spanPricePerThousand,
    seatPrice: (allPricing?.seat?.amount || 4000) / 100,
    seatInterval: allPricing?.seat?.interval || 'month',
  };
}
