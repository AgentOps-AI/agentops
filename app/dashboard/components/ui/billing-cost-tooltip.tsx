import React from 'react';
import { useAllStripePricing } from '@/hooks/queries/useStripeConfig';
import { formatPrice, formatNumber } from '@/lib/number_formatting_utils';
import { useProject } from '@/app/providers/project-provider';
import { DateRange } from 'react-day-picker';
import { format } from 'date-fns';
import { getPricingRates } from '@/lib/billing-utils';
import { useBillingDashboard } from '@/hooks/queries/useBillingDashboard';

interface BillingCostTooltipProps {
  dateRange?: DateRange;
  projectId?: string | null;
}

export function useBillingTooltipContent(dateRange?: DateRange, projectId?: string | null) {
  const { data: allPricing } = useAllStripePricing();
  const { selectedProject, activeOrgDetails } = useProject();

  const orgId = selectedProject?.org_id || activeOrgDetails?.id || null;

  const { data: billingData, isLoading } = useBillingDashboard(
    orgId,
    dateRange?.from ? format(dateRange.from, "yyyy-MM-dd'T'HH:mm:ss'Z'") : null,
    dateRange?.to ? format(dateRange.to, "yyyy-MM-dd'T'HH:mm:ss'Z'") : null,
  );

  const { tokenPricePerMillion, spanPricePerThousand } = getPricingRates(allPricing);

  if (isLoading) {
    return (
      <div className="space-y-2 text-sm">
        <div className="font-semibold">Loading billing breakdown...</div>
      </div>
    );
  }

  if (!billingData || !billingData.project_breakdown) {
    return (
      <div className="space-y-2 text-sm">
        <div className="font-semibold">No billing data available</div>
      </div>
    );
  }

  const relevantProjects = projectId
    ? billingData.project_breakdown.filter((p) => p.project_id === projectId)
    : billingData.project_breakdown;

  const totalTokens = relevantProjects.reduce((sum, p) => sum + p.tokens, 0);
  const totalSpans = relevantProjects.reduce((sum, p) => sum + p.spans, 0);
  const tokenCost = relevantProjects.reduce((sum, p) => sum + p.token_cost, 0) / 100;
  const spanCost = relevantProjects.reduce((sum, p) => sum + p.span_cost, 0) / 100;
  const totalCost = relevantProjects.reduce((sum, p) => sum + p.total_cost, 0) / 100;

  return (
    <div className="space-y-2 text-sm">
      <div className="font-semibold">Billing Breakdown</div>
      <div className="space-y-1 text-xs">
        <div className="flex items-center justify-between">
          <span>Token Usage Cost</span>
          <span className="font-medium">{formatPrice(tokenCost, { decimals: 4 })}</span>
        </div>
        <div className="pl-2 text-gray-500 dark:text-gray-400">
          {formatNumber(totalTokens)} tokens × {formatPrice(tokenPricePerMillion, { decimals: 2 })}
          /1M
        </div>

        <div className="flex items-center justify-between pt-1">
          <span>Span Upload Cost</span>
          <span className="font-medium">{formatPrice(spanCost, { decimals: 4 })}</span>
        </div>
        <div className="pl-2 text-gray-500 dark:text-gray-400">
          {formatNumber(totalSpans)} spans × {formatPrice(spanPricePerThousand, { decimals: 2 })}/1K
        </div>

        <div className="mt-2 flex justify-between border-t pt-1 font-medium">
          <span>Total Cost</span>
          <span>{formatPrice(totalCost, { decimals: 4 })}</span>
        </div>
      </div>
      <div className="mt-2 border-t pt-2 text-xs text-gray-500 dark:text-gray-400">
        This is your actual AgentOps billing cost. View your complete bill in organization settings.
        Questions? Contact{' '}
        <a href="mailto:support@agentops.ai" className="underline hover:no-underline">
          support@agentops.ai
        </a>
        .
      </div>
    </div>
  );
}

export function BillingCostTooltip({ dateRange, projectId }: BillingCostTooltipProps) {
  return useBillingTooltipContent(dateRange, projectId);
}
