import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useBillingDashboard } from '@/hooks/queries/useBillingDashboard';
import { useStripeConfig, useAllStripePricing } from '@/hooks/queries/useStripeConfig';
import { Skeleton } from '@/components/ui/skeleton';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { useBilling } from '@/app/providers/billing-provider';
import { useTheme } from 'next-themes';
import { loadStripe, Appearance } from '@stripe/stripe-js';
import { CheckoutProvider } from '@stripe/react-stripe-js';
import EmbeddedCheckoutForm from './EmbeddedCheckoutForm';
import { BillingCalculator } from './BillingCalculator';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { DollarSign, Zap, Database, Users, BarChart3 } from 'lucide-react';
import {
  ArrowRight01Icon as ChevronRight,
  Cancel01Icon as X,
  Loading03Icon as Loader2,
  RefreshIcon as Refresh,
  CrownIcon as Crown,
  CheckmarkCircle01Icon as CheckCircle,
  Edit02Icon as Edit,
} from 'hugeicons-react';
import { IOrg } from '@/types/IOrg';
import { BillingBreakdownChart } from '@/components/charts/pie-chart/billing-breakdown-chart';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MembersList } from './MembersList';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { updateOrgAPI } from '@/lib/api/orgs';
import { useToast } from '@/components/ui/use-toast';
import { getPricingRates } from '@/lib/billing-utils';
import { ProjectCostBreakdown } from './ProjectCostBreakdown';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useOrgUsers } from '@/hooks/queries/useOrgUsers';
import { orgsQueryKey } from '@/hooks/queries/useOrgs';
import { projectsQueryKey } from '@/hooks/queries/useProjects';
import { formatPrice, formatNumber } from '@/lib/number_formatting_utils';
import { DateRange } from 'react-day-picker';
import { BillingPeriod, ProjectUsageBreakdown } from '@/types/billing.types';
import { format, parseISO, startOfDay, endOfDay } from 'date-fns';

interface OrgManagementDashboardProps {
  orgs: IOrg[];
  orgId: string;
  org?: IOrg;
  onOrgChange: (orgId: string) => void;
  onUpgradeClicked?: (orgId: string) => void;
  onCancelClicked?: (orgId: string, subscriptionId: string | null) => Promise<void>;
  onReactivateClicked?: (orgId: string, subscriptionId: string | null) => Promise<void>;
  onUpdateSubscription?: (
    orgId: string,
    options?: {
      priceId?: string;
      prorationBehavior?: 'create_prorations' | 'always_invoice' | 'none';
    },
  ) => Promise<void>;
  onRefreshSubscription?: (orgId: string) => Promise<void>;
  onOpenCustomerPortal?: (orgId: string) => Promise<void>;
  onValidateDiscount?: (
    orgId: string,
    discountCode: string,
  ) => Promise<{
    valid: boolean;
    discount_description?: string;
    is_100_percent_off?: boolean;
  }>;
  onCheckoutNeeded?: (orgId: string) => Promise<void>;
  onPaymentSuccess?: (orgId: string) => void;
  onCreateFreeSubscription?: (orgId: string, discountCode?: string) => Promise<void>;
  clientSecret: string | null;
  isFetchingClientSecret: boolean;
  fetchClientSecret: () => Promise<string>;
}

const COLORS = {
  seats: '#3b82f6',
  tokens: '#10b981',
  spans: '#f59e0b',
};

const CostCard = ({
  title,
  value,
  icon: Icon,
  colorClass,
  breakdown,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
  breakdown: string[];
  period: string;
}) => (
  <div className={`rounded-lg ${colorClass}/20 p-4`}>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
        <p className={`text-2xl font-bold ${colorClass}`}>{formatPrice(value)}</p>
        <div className="mt-1 space-y-0.5">
          {breakdown.map((item, index) => (
            <p key={index} className="text-xs text-gray-500">
              {item}
            </p>
          ))}
        </div>
      </div>
      <Icon className={`h-8 w-8 ${colorClass} opacity-30`} />
    </div>
  </div>
);

export function OrgManagementDashboard({
  orgs,
  orgId,
  org,
  onOrgChange,
  onCancelClicked,
  onReactivateClicked,
  onRefreshSubscription,
  onOpenCustomerPortal,
  onValidateDiscount,
  onCheckoutNeeded,
  onPaymentSuccess,
  onCreateFreeSubscription,
  clientSecret,
  isFetchingClientSecret,
  fetchClientSecret,
}: OrgManagementDashboardProps) {
  const [selectedDateRange, setSelectedDateRange] = useState<DateRange | undefined>();
  const [customDateRange, setCustomDateRange] = useState<DateRange | undefined>();
  const [activeTab, setActiveTab] = useState<'calculator' | 'seats' | 'projects'>('seats');
  const [editOrgDialogOpen, setEditOrgDialogOpen] = useState(false);
  const [editOrgName, setEditOrgName] = useState('');

  const { data: orgUsers, isLoading: isLoadingUsers } = useOrgUsers(orgId);
  const { data: stripeConfig } = useStripeConfig();
  const { data: allPricing, isLoading: pricingLoading } = useAllStripePricing();
  const { resolvedTheme } = useTheme();
  const billing = useBilling();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { tokenPricePerMillion, spanPricePerThousand } = getPricingRates(allPricing);

  const [promoCode, setPromoCode] = useState('');
  const [promoError, setPromoError] = useState('');
  const [isCreatingFreeSubscription, setIsCreatingFreeSubscription] = useState(false);

  // First, get the current dashboard data without any date filters to determine default period
  const { data: dashboard, isLoading, error } = useBillingDashboard(orgId, null, null);

  const defaultDateRange = useMemo(() => {
    // If no period is selected, default to current period from Stripe
    const period = dashboard?.current_period;

    return {
      from: period ? parseISO(period.period_start) : undefined,
      to: period ? parseISO(period.period_end) : undefined,
    };
  }, [dashboard]);

  // Use custom date range if available, otherwise selected period, otherwise default to current period
  const activeDateRange = customDateRange || selectedDateRange || defaultDateRange;

  // Get filtered dashboard data based on the active date range
  const {
    data: filteredDashboard,
    isLoading: isFilteredLoading,
    error: filteredError,
  } = useBillingDashboard(
    orgId,
    activeDateRange?.from && (customDateRange || selectedDateRange)
      ? format(startOfDay(activeDateRange.from), "yyyy-MM-dd'T'HH:mm:ss'Z'")
      : null,
    activeDateRange?.to && (customDateRange || selectedDateRange)
      ? format(endOfDay(activeDateRange.to), "yyyy-MM-dd'T'HH:mm:ss'Z'")
      : null,
  );

  // Use filtered data when available, otherwise use default dashboard
  const displayDashboard = customDateRange || selectedDateRange ? filteredDashboard : dashboard;
  const displayLoading = customDateRange || selectedDateRange ? isFilteredLoading : isLoading;
  const displayError = customDateRange || selectedDateRange ? filteredError : error;

  useEffect(() => {
    setCustomDateRange(undefined);
  }, [selectedDateRange]);

  const canManage = org && ['owner', 'admin'].includes(org.current_user_role || '');
  const showCheckout = billing.shouldShowCheckout(orgId);
  const isPaymentProcessing = billing.isPaymentProcessing(orgId);

  const updateOrgMutation = useMutation({
    mutationFn: (newName: string) => updateOrgAPI(orgId, { name: newName }),
    onSuccess: async (_updatedOrg) => {
      toast({
        title: 'Organization Updated',
        description: 'Organization name has been updated successfully.',
        variant: 'default',
      });

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: orgsQueryKey }),
        queryClient.invalidateQueries({ queryKey: ['org-detail', orgId] }),
        queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
        // Invalidate any other queries that might contain org data
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey.some(
              (key) => typeof key === 'string' && (key.includes('org') || key.includes('project')),
            ),
        }),
      ]);

      setEditOrgDialogOpen(false);
      setEditOrgName('');
    },
    onError: async (error: Error) => {
      console.error('Org update error:', error);

      if (error.message.includes('validation') || error.message.includes('attribute')) {
        toast({
          title: 'Organization Update',
          description: 'The update may have succeeded. Refreshing data...',
          variant: 'default',
        });

        await Promise.all([
          queryClient.invalidateQueries({ queryKey: orgsQueryKey }),
          queryClient.invalidateQueries({ queryKey: ['org-detail', orgId] }),
          queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
          queryClient.invalidateQueries({
            predicate: (query) =>
              query.queryKey.some(
                (key) =>
                  typeof key === 'string' && (key.includes('org') || key.includes('project')),
              ),
          }),
        ]);

        setEditOrgDialogOpen(false);
        setEditOrgName('');
      } else {
        toast({
          title: 'Update Failed',
          description: error.message || 'Failed to update organization name. Please try again.',
          variant: 'destructive',
        });
      }
    },
  });

  const stripePromise = useMemo(() => {
    if (!stripeConfig?.publishableKey) {
      return loadStripe('default_publishable_key_if_not_set');
    }
    return loadStripe(stripeConfig.publishableKey);
  }, [stripeConfig?.publishableKey]);

  const periodOptions = useMemo(() => {
    if (!dashboard) return [];

    let currentPeriodLabel = 'Current Period';
    if (dashboard.current_period) {
      const periodStart = new Date(dashboard.current_period.period_start);
      const periodEnd = new Date(dashboard.current_period.period_end);

      currentPeriodLabel = `${periodStart.toLocaleDateString('en-US')} - ${periodEnd.toLocaleDateString('en-US')}`;
    } else if (org?.subscription_start_date && org?.subscription_end_date) {
      const startDate = new Date(org.subscription_start_date * 1000);
      const endDate = new Date(org.subscription_end_date * 1000);

      currentPeriodLabel = `${startDate.toLocaleDateString('en-US')} - ${endDate.toLocaleDateString('en-US')}`;
    }

    const options: { value: 'current' | string; label: string; dateRange?: DateRange }[] = [
      {
        value: 'current',
        label: currentPeriodLabel,
        dateRange: dashboard.current_period
          ? {
              from: parseISO(dashboard.current_period.period_start),
              to: parseISO(dashboard.current_period.period_end),
            }
          : undefined,
      },
    ];

    if (dashboard.past_periods && dashboard.past_periods.length > 0) {
      dashboard.past_periods.forEach((period: BillingPeriod) => {
        const periodStart = new Date(period.period_start);
        const periodEnd = new Date(period.period_end);
        const label = `${periodStart.toLocaleDateString('en-US')} - ${periodEnd.toLocaleDateString('en-US')}`;

        options.push({
          value: period.id,
          label,
          dateRange: {
            from: parseISO(period.period_start),
            to: parseISO(period.period_end),
          },
        });
      });
    }

    return options;
  }, [dashboard, org]);

  const getStripeAppearance = (): Appearance => {
    const isDark = resolvedTheme === 'dark';
    return {
      theme: isDark ? 'night' : 'stripe',
      variables: {
        colorPrimary: isDark ? '#ffffff' : '#141b34',
        colorBackground: isDark ? '#0f172a' : '#ffffff',
        colorText: isDark ? '#e1e2f2' : '#141b34',
        colorDanger: '#e65a7e',
        fontFamily: 'Figtree, system-ui, sans-serif',
        spacingUnit: '4px',
        borderRadius: '8px',
      },
    };
  };

  const handleCheckoutFlow = async () => {
    setPromoError('');

    if (promoCode.trim() && onValidateDiscount) {
      const result = await onValidateDiscount(orgId, promoCode.trim());

      if (!result.valid) {
        setPromoError('Invalid promo code');
        return;
      }

      if (result.is_100_percent_off && onCreateFreeSubscription) {
        setIsCreatingFreeSubscription(true);
        try {
          await onCreateFreeSubscription(orgId, promoCode.trim());
        } finally {
          setIsCreatingFreeSubscription(false);
        }
        return;
      }
    }

    if (onCheckoutNeeded) {
      await onCheckoutNeeded(orgId);
    }
  };

  const handleCancelClick = async () => {
    if (onCancelClicked && org?.subscription_id) {
      await onCancelClicked(orgId, org.subscription_id);
    }
  };

  const handleReactivateClick = async () => {
    if (onReactivateClicked && org?.subscription_id) {
      await onReactivateClicked(orgId, org.subscription_id);
    }
  };

  const handleRefreshSubscription = async () => {
    if (onRefreshSubscription) {
      await onRefreshSubscription(orgId);
    }
  };

  const handleOpenPortal = async () => {
    if (onOpenCustomerPortal) {
      await onOpenCustomerPortal(orgId);
    }
  };

  const handleEditOrgName = () => {
    setEditOrgName(org?.name || '');
    setEditOrgDialogOpen(true);
  };

  const handleSubmitOrgNameEdit = () => {
    if (!editOrgName.trim()) {
      toast({
        title: 'Name Required',
        description: 'Organization name cannot be empty.',
        variant: 'destructive',
      });
      return;
    }
    updateOrgMutation.mutate(editOrgName.trim());
  };

  const ownersAndAdmins = useMemo(() => {
    if (!orgUsers) return [];
    return orgUsers.filter((user) => user.role === 'owner' || user.role === 'admin');
  }, [orgUsers]);

  if (!canManage) {
    return (
      <div className="space-y-6">
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold">Organization Management</h1>
          <div className="max-w-md">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Organization
            </label>
            <Select value={orgId} onValueChange={onOrgChange}>
              <SelectTrigger className="mt-2 h-16">
                <div className="flex w-full items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950/30">
                        <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                          {org?.name?.charAt(0)?.toUpperCase() || 'O'}
                        </span>
                      </div>
                      {org?.prem_status === 'pro' && (
                        <div className="absolute -bottom-1 -right-1">
                          <SubscriptionBadge
                            tier="pro"
                            showUpgrade={false}
                            expanded={false}
                            className="h-5 w-5 p-0.5"
                          />
                        </div>
                      )}
                    </div>
                    <div className="text-left">
                      <p className="font-medium text-gray-900 dark:text-white">
                        {org?.name || 'Loading...'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {org?.current_user_role || ''}
                      </p>
                    </div>
                  </div>
                </div>
              </SelectTrigger>
              <SelectContent>
                {orgs.map((orgOption) => (
                  <SelectItem key={orgOption.id} value={orgOption.id}>
                    <div className="flex w-full items-center gap-3 py-1">
                      <div className="relative">
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950/30">
                          <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
                            {orgOption.name?.charAt(0)?.toUpperCase() || 'O'}
                          </span>
                        </div>
                        {orgOption.prem_status === 'pro' && (
                          <div className="absolute -bottom-0.5 -right-0.5">
                            <SubscriptionBadge
                              tier="pro"
                              showUpgrade={false}
                              expanded={false}
                              className="h-4 w-4 p-0.5"
                            />
                          </div>
                        )}
                      </div>
                      <span className="font-medium">{orgOption.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                You are a member of <span className="font-semibold">{org?.name}</span>.
              </p>
              {ownersAndAdmins.length > 0 && (
                <div>
                  <p className="mb-2 text-sm text-gray-700 dark:text-gray-300">
                    If you need organization changes, please contact your owner or admin:
                  </p>
                  <ul className="space-y-1">
                    {ownersAndAdmins.map((user) => (
                      <li key={user.user_id} className="text-sm text-gray-600 dark:text-gray-400">
                        • {user.user_email} ({user.role})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (displayLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (displayError || !displayDashboard) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-gray-500">Unable to load billing data</p>
        </CardContent>
      </Card>
    );
  }

  const currentPeriod = displayDashboard?.current_period;

  const costBreakdown = currentPeriod
    ? [
        { name: 'Seats', value: currentPeriod.seat_cost / 100, color: COLORS.seats },
        {
          name: 'Tokens',
          value: (currentPeriod.usage_costs.tokens || 0) / 100,
          color: COLORS.tokens,
        },
        { name: 'Spans', value: (currentPeriod.usage_costs.spans || 0) / 100, color: COLORS.spans },
      ].filter((item) => item.value > 0)
    : [];

  const totalUsageCost =
    displayDashboard?.project_breakdown?.reduce(
      (acc: number, p: ProjectUsageBreakdown) => acc + p.total_cost,
      0,
    ) || 0;

  const renderSubscriptionSection = () => {
    if (isPaymentProcessing) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-950/30">
            <CheckCircle size={32} className="text-green-600 dark:text-green-400" />
          </div>
          <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
            Payment Successful!
          </h3>
          <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
            Your subscription is being activated.
          </p>
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-green-600 dark:text-green-400" />
            <span className="text-sm text-green-700 dark:text-green-200">
              Activating your Pro subscription...
            </span>
          </div>
        </div>
      );
    }

    if (org?.prem_status === 'pro' && dashboard?.is_legacy_billing) {
      const legacyEndDate = dashboard.legacy_cancellation_date
        ? new Date(dashboard.legacy_cancellation_date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })
        : 'Unknown';

      return (
        <div className="space-y-6">
          <div className="rounded-lg border-l-4 border-l-purple-500 bg-purple-50 p-4 dark:bg-purple-950/20">
            <div className="flex items-start gap-3">
              <Crown
                size={20}
                className="mt-0.5 flex-shrink-0 text-purple-600 dark:text-purple-400"
              />
              <div className="flex-1">
                <h4 className="font-semibold text-purple-900 dark:text-purple-100">
                  Legacy Subscription Ending
                </h4>
                <p className="mt-1 text-sm text-purple-700 dark:text-purple-200">
                  Your current subscription will end on{' '}
                  <span className="font-medium">{legacyEndDate}</span>. To continue using Pro
                  features, upgrade to our new per-seat billing plan.
                </p>
              </div>
            </div>
          </div>
          <div className="text-center">
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              Upgrade to New Pro Plan
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Seamless transition to our improved per-seat + usage billing model
            </p>
          </div>
          {!showCheckout && (
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Promo code (optional)
                </label>
                <Input
                  type="text"
                  placeholder="Enter promo code"
                  value={promoCode}
                  onChange={(e) => {
                    setPromoCode(e.target.value);
                    setPromoError('');
                  }}
                />
                {promoError && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{promoError}</p>
                )}
              </div>
              <Button
                onClick={handleCheckoutFlow}
                disabled={isFetchingClientSecret || isCreatingFreeSubscription}
                className="w-full"
                size="lg"
              >
                {isFetchingClientSecret || isCreatingFreeSubscription ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {isCreatingFreeSubscription
                      ? 'Creating subscription...'
                      : 'Preparing checkout...'}
                  </>
                ) : (
                  <>
                    <Crown className="mr-2 h-4 w-4" />
                    Upgrade to New Pro Plan
                  </>
                )}
              </Button>
            </div>
          )}
          {showCheckout && clientSecret && (
            <CheckoutProvider
              stripe={stripePromise}
              options={{
                fetchClientSecret,
                elementsOptions: {
                  appearance: getStripeAppearance(),
                },
              }}
            >
              <EmbeddedCheckoutForm
                onPaymentElementReady={() => {}}
                onSuccess={() => {
                  onPaymentSuccess?.(orgId);
                }}
                onError={() => {}}
                orgId={orgId}
                pricePerSeat={(allPricing?.seat?.amount || 4000) / 100}
                isFullyDiscounted={
                  billing.validatedDiscountDescription?.includes('100%') ||
                  billing.validatedDiscountDescription?.toLowerCase().includes('free')
                }
              />
            </CheckoutProvider>
          )}
        </div>
      );
    }
    if (org?.prem_status === 'free') {
      return (
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              Upgrade to Pro
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Unlock unlimited features and premium support
            </p>
          </div>
          {!showCheckout && (
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Promo code (optional)
                </label>
                <Input
                  type="text"
                  placeholder="Enter promo code"
                  value={promoCode}
                  onChange={(e) => {
                    setPromoCode(e.target.value);
                    setPromoError('');
                  }}
                />
                {promoError && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{promoError}</p>
                )}
              </div>
              <Button
                onClick={handleCheckoutFlow}
                disabled={isFetchingClientSecret || isCreatingFreeSubscription}
                className="w-full"
              >
                {isFetchingClientSecret || isCreatingFreeSubscription ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {isCreatingFreeSubscription
                      ? 'Creating subscription...'
                      : 'Preparing checkout...'}
                  </>
                ) : (
                  'Continue to Payment'
                )}
              </Button>
            </div>
          )}
          {showCheckout && clientSecret && (
            <CheckoutProvider
              stripe={stripePromise}
              options={{
                fetchClientSecret,
                elementsOptions: {
                  appearance: getStripeAppearance(),
                },
              }}
            >
              <EmbeddedCheckoutForm
                onPaymentElementReady={() => {}}
                onSuccess={() => {
                  onPaymentSuccess?.(orgId);
                }}
                onError={() => {}}
                orgId={orgId}
                pricePerSeat={(allPricing?.seat?.amount || 4000) / 100}
                isFullyDiscounted={
                  billing.validatedDiscountDescription?.includes('100%') ||
                  billing.validatedDiscountDescription?.toLowerCase().includes('free')
                }
              />
            </CheckoutProvider>
          )}
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="rounded-lg border p-4">
          <h4 className="mb-2 text-sm font-semibold">Current Subscription</h4>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {Math.max(1, org?.paid_member_count || 1)} licensed{' '}
                {Math.max(1, org?.paid_member_count || 1) === 1 ? 'member' : 'members'}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                ${(allPricing?.seat?.amount || 4000) / 100} per seat per{' '}
                {allPricing?.seat?.interval || 'month'}
              </p>
            </div>
            <Badge variant="default">
              $
              {(
                Math.max(1, org?.paid_member_count || 1) *
                ((allPricing?.seat?.amount || 4000) / 100)
              ).toFixed(2)}
              /{allPricing?.seat?.interval || 'month'}
            </Badge>
          </div>
        </div>

        {!org?.subscription_id ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/20">
            <div className="flex items-start gap-3">
              <Crown
                size={20}
                className="mt-0.5 flex-shrink-0 text-amber-600 dark:text-amber-400"
              />
              <div>
                <p className="text-sm text-amber-700 dark:text-amber-200">
                  Contact{' '}
                  <a
                    href="mailto:alex@agentops.ai"
                    className="font-medium underline hover:no-underline"
                  >
                    alex@agentops.ai
                  </a>{' '}
                  to manage this subscription.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {org.subscription_cancel_at_period_end ? (
              <Button onClick={handleReactivateClick} variant="outline" className="w-full">
                <Refresh className="mr-2 h-4 w-4" />
                Reactivate Subscription
              </Button>
            ) : (
              <Button onClick={handleCancelClick} variant="outline" className="w-full">
                <X className="mr-2 h-4 w-4" />
                Cancel Subscription
              </Button>
            )}
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={handleOpenPortal}
                variant="outline"
                className="flex items-center gap-2"
              >
                <ChevronRight size={14} />
                Billing Portal
              </Button>
              <Button
                onClick={handleRefreshSubscription}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Refresh size={14} />
                Refresh Data
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Organization Management</h1>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Management</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Organization
              </label>
              <div className="flex gap-2">
                <Select value={orgId} onValueChange={onOrgChange}>
                  <SelectTrigger className="h-16">
                    <div className="flex w-full items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950/30">
                            <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                              {org?.name?.charAt(0)?.toUpperCase() || 'O'}
                            </span>
                          </div>
                          {org?.prem_status === 'pro' && (
                            <div className="absolute -bottom-1 -right-1">
                              <SubscriptionBadge
                                tier="pro"
                                showUpgrade={false}
                                expanded={false}
                                className="h-5 w-5 p-0.5"
                              />
                            </div>
                          )}
                        </div>
                        <div className="text-left">
                          <p className="font-medium text-gray-900 dark:text-white">
                            {org?.name || 'Loading...'}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {org?.current_user_role || ''}
                          </p>
                        </div>
                      </div>
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    {orgs.map((orgOption) => (
                      <SelectItem key={orgOption.id} value={orgOption.id}>
                        <div className="flex w-full items-center gap-3 py-1">
                          <div className="relative">
                            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950/30">
                              <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
                                {orgOption.name?.charAt(0)?.toUpperCase() || 'O'}
                              </span>
                            </div>
                            {orgOption.prem_status === 'pro' && (
                              <div className="absolute -bottom-0.5 -right-0.5">
                                <SubscriptionBadge
                                  tier="pro"
                                  showUpgrade={false}
                                  expanded={false}
                                  className="h-4 w-4 p-0.5"
                                />
                              </div>
                            )}
                          </div>
                          <span className="font-medium">{orgOption.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {canManage && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleEditOrgName}
                    className="h-16 w-16 flex-shrink-0"
                    title="Edit organization name"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Billing Period
              </label>
              <Select
                value={selectedDateRange ? 'selected' : 'current'}
                onValueChange={(value) => {
                  if (value === 'current') {
                    setSelectedDateRange(undefined);
                  } else {
                    const option = periodOptions.find((opt) => opt.value === value);
                    if (option?.dateRange) {
                      setSelectedDateRange(option.dateRange);
                    }
                  }
                }}
              >
                <SelectTrigger className="h-16">
                  <SelectValue placeholder="Select period" />
                </SelectTrigger>
                <SelectContent>
                  {periodOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold">Subscription</h3>
                <SubscriptionBadge
                  tier={org?.prem_status || 'free'}
                  showUpgrade={false}
                  isCancelling={!!org?.subscription_cancel_at_period_end}
                  cancelDate={org?.subscription_end_date || undefined}
                  isLegacyBilling={dashboard?.is_legacy_billing}
                  legacyCancellationDate={dashboard?.legacy_cancellation_date}
                />
              </div>
              <div>{renderSubscriptionSection()}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {selectedDateRange
                ? `${periodOptions.find((p) => p.dateRange?.from?.getTime() === selectedDateRange.from?.getTime())?.label || 'Selected Period'} Overview`
                : `${periodOptions.find((p) => p.value === 'current')?.label || 'Current Period'} Overview`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentPeriod ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <CostCard
                    title="Seat Cost"
                    value={(currentPeriod.seat_cost || 0) / 100}
                    icon={Users}
                    colorClass="text-blue-600 dark:text-blue-400"
                    breakdown={[
                      `${currentPeriod.seat_count} licensed ${currentPeriod.seat_count === 1 ? 'member' : 'members'}`,
                      `${formatPrice((allPricing?.seat?.amount || 0) / 100)} per seat`,
                    ]}
                    period={allPricing?.seat?.interval || 'month'}
                  />
                  <CostCard
                    title="Usage Cost"
                    value={totalUsageCost / 100}
                    icon={Zap}
                    colorClass="text-green-600 dark:text-green-400"
                    breakdown={[
                      `${formatNumber(currentPeriod.usage_quantities.tokens || 0)} tokens`,
                      `${formatNumber(currentPeriod.usage_quantities.spans || 0)} spans`,
                    ]}
                    period={allPricing?.seat?.interval || 'month'}
                  />
                </div>
                {costBreakdown.length > 0 && (
                  <BillingBreakdownChart costBreakdown={costBreakdown} />
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">No billing data for current period</p>
                <div className="grid grid-cols-1 gap-4">
                  <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-950/20">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Base (Seats)</p>
                        <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">$0.00</p>
                        <p className="mt-1 text-xs text-gray-500">0 licensed members</p>
                        <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
                          $
                          {allPricing?.seat?.amount
                            ? (allPricing.seat.amount / 100).toFixed(2)
                            : '40.00'}{' '}
                          per seat per {allPricing?.seat?.interval || 'month'}
                        </p>
                      </div>
                      <DollarSign className="h-8 w-8 text-blue-500 opacity-50" />
                    </div>
                  </div>
                  <div className="rounded-lg bg-green-50 p-4 dark:bg-green-950/20">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">API Tokens</p>
                        <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                          $0.00
                        </p>
                        <p className="mt-1 text-xs text-gray-500">0 tokens</p>
                        <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                          {formatPrice(tokenPricePerMillion, {
                            decimals: 2,
                          })}{' '}
                          per 1M tokens
                        </p>
                      </div>
                      <Zap className="h-8 w-8 text-green-500 opacity-50" />
                    </div>
                  </div>
                  <div className="rounded-lg bg-amber-50 p-4 dark:bg-amber-950/20">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Span Uploads</p>
                        <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                          $0.00
                        </p>
                        <p className="mt-1 text-xs text-gray-500">0 spans</p>
                        <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                          {formatPrice(spanPricePerThousand, {
                            decimals: 2,
                          })}{' '}
                          per 1K spans
                        </p>
                      </div>
                      <Database className="h-8 w-8 text-amber-500 opacity-50" />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="seats" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Seats & Users
          </TabsTrigger>
          <TabsTrigger value="projects" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Project Costs
          </TabsTrigger>
          <TabsTrigger value="calculator" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Calculator
          </TabsTrigger>
        </TabsList>
        <TabsContent value="projects" className="space-y-6">
          <div>
            <ProjectCostBreakdown
              orgId={orgId}
              projectCosts={displayDashboard?.project_breakdown || []}
              isLoading={displayLoading}
              error={displayError}
              activeDateRange={activeDateRange}
              defaultDateRange={defaultDateRange}
              onDateRangeChange={setCustomDateRange}
            />
          </div>
        </TabsContent>
        <TabsContent value="calculator" className="space-y-6">
          <BillingCalculator allPricing={allPricing} pricingLoading={pricingLoading} />
        </TabsContent>
        <TabsContent value="seats" className="space-y-6">
          {org?.prem_status === 'pro' ? (
            <Card>
              <CardContent className="pt-6">
                {!isLoadingUsers && orgUsers && (
                  <MembersList
                    orgId={orgId}
                    canManage={canManage || false}
                    onLicenseChange={async () => {
                      await queryClient.invalidateQueries({
                        queryKey: ['billing-dashboard', orgId],
                      });
                      await queryClient.refetchQueries({ queryKey: ['billing-dashboard', orgId] });
                    }}
                    seatCount={Math.max(1, org.paid_member_count || 1)}
                    pricePerSeat={(allPricing?.seat?.amount || 4000) / 100}
                    billingInterval={allPricing?.seat?.interval || 'mo'}
                    currentPeriodStart={currentPeriod?.period_start || undefined}
                    currentPeriodEnd={currentPeriod?.period_end || undefined}
                  />
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Seat Management</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Upgrade to Pro to manage team members and seat licenses
                </p>
                <Button
                  onClick={() => {
                    /* Upgrade functionality handled in subscription section */
                  }}
                  className="mt-4"
                  variant="outline"
                >
                  <Crown className="mr-2 h-4 w-4" />
                  Upgrade to Pro
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Edit Organization Name Modal */}
      <Dialog open={editOrgDialogOpen} onOpenChange={setEditOrgDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Organization Name</DialogTitle>
            <DialogDescription>
              Update the name of your organization. This will be visible to all members.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="org-name" className="text-right">
                Name
              </Label>
              <Input
                id="org-name"
                value={editOrgName}
                onChange={(e) => setEditOrgName(e.target.value)}
                className="col-span-3"
                placeholder="Enter organization name"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSubmitOrgNameEdit();
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditOrgDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSubmitOrgNameEdit}
              disabled={updateOrgMutation.isPending || !editOrgName.trim()}
            >
              {updateOrgMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                'Update'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
