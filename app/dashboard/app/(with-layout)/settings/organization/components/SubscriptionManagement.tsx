import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  ArrowRight01Icon as ChevronRight,
  Cancel01Icon as X,
  Loading03Icon as Loader2,
  RefreshIcon as Refresh,
  CrownIcon as Crown,
  CheckmarkCircle01Icon as CheckCircle,
  DollarCircleIcon as DollarSign,
  DatabaseIcon as Database,
  ZapIcon as Zap,
} from 'hugeicons-react';
import { IOrg } from '@/types/IOrg';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { useTheme } from 'next-themes';
import { loadStripe, Appearance } from '@stripe/stripe-js';
import { CheckoutProvider } from '@stripe/react-stripe-js';
import EmbeddedCheckoutForm from './EmbeddedCheckoutForm';
import { useStripeConfig, useAllStripePricing } from '@/hooks/queries/useStripeConfig';
import { useBilling } from '@/app/providers/billing-provider';
import { useBillingDashboard } from '@/hooks/queries/useBillingDashboard';
import { cn } from '@/lib/utils';
import { formatPrice } from '@/lib/number_formatting_utils';
import { getPricingRates } from '@/lib/billing-utils';

interface SubscriptionManagementProps {
  org: IOrg;
  open: boolean;
  onClose: () => void;
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

export function SubscriptionManagement({
  org,
  open,
  onClose,
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
}: SubscriptionManagementProps) {
  const { resolvedTheme } = useTheme();
  const { data: stripeConfig } = useStripeConfig();
  const { data: allPricing } = useAllStripePricing();
  const billing = useBilling();
  const { data: _billingData } = useBillingDashboard(org.id, null, null);

  const { seatPrice, seatInterval, tokenPricePerMillion, spanPricePerThousand } =
    getPricingRates(allPricing);

  const [promoCode, setPromoCode] = useState('');
  const [promoError, setPromoError] = useState('');
  const [isCreatingFreeSubscription, setIsCreatingFreeSubscription] = useState(false);
  const [_stripeElementsLoaded, setStripeElementsLoaded] = useState(false);
  const [confirmationState, setConfirmationState] = useState<'cancel' | 'reactivate' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const canManage = ['owner', 'admin'].includes(org.current_user_role || '');
  const showCheckout = billing.shouldShowCheckout(org.id);
  const isPaymentProcessing = billing.isPaymentProcessing(org.id);

  const stripePromise = React.useMemo(() => {
    if (!stripeConfig?.publishableKey) {
      return loadStripe('default_publishable_key_if_not_set');
    }
    return loadStripe(stripeConfig.publishableKey);
  }, [stripeConfig?.publishableKey]);

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

  const handleCancelClick = async () => {
    if (confirmationState === 'cancel' && onCancelClicked) {
      setIsProcessing(true);
      try {
        await onCancelClicked(org.id, org.subscription_id);
        onClose();
      } finally {
        setIsProcessing(false);
        setConfirmationState(null);
      }
    } else {
      setConfirmationState('cancel');
    }
  };

  const handleReactivateClick = async () => {
    if (confirmationState === 'reactivate' && onReactivateClicked) {
      setIsProcessing(true);
      try {
        await onReactivateClicked(org.id, org.subscription_id);
        onClose();
      } finally {
        setIsProcessing(false);
        setConfirmationState(null);
      }
    } else {
      setConfirmationState('reactivate');
    }
  };

  const handleRefreshSubscription = async () => {
    if (onRefreshSubscription) {
      setIsProcessing(true);
      try {
        await onRefreshSubscription(org.id);
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const handleOpenPortal = async () => {
    if (onOpenCustomerPortal) {
      await onOpenCustomerPortal(org.id);
    }
  };

  const handleCheckoutFlow = async () => {
    setPromoError('');

    if (promoCode.trim() && onValidateDiscount) {
      const result = await onValidateDiscount(org.id, promoCode.trim());

      if (!result.valid) {
        setPromoError('Invalid promo code');
        return;
      }

      if (result.is_100_percent_off && onCreateFreeSubscription) {
        setIsCreatingFreeSubscription(true);
        try {
          await onCreateFreeSubscription(org.id, promoCode.trim());
          onClose();
        } finally {
          setIsCreatingFreeSubscription(false);
        }
        return;
      }
    }

    if (onCheckoutNeeded) {
      await onCheckoutNeeded(org.id);
    }
  };

  const renderFreeOrgContent = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Upgrade to Pro</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Unlock unlimited features and premium support
        </p>
      </div>

      {/* Pricing Preview */}
      <div className="space-y-4 rounded-lg border p-4">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Pricing Overview</h4>
        <div className="space-y-3">
          {/* Seat Pricing */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-blue-500"></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Per seat (includes owner)
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {formatPrice(seatPrice)}/{seatInterval}
            </span>
          </div>

          {/* Token Pricing */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-green-500"></div>
              <div className="flex items-center gap-1">
                <Zap size={14} className="text-gray-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Per 1M tokens</span>
              </div>
            </div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {formatPrice(tokenPricePerMillion, { decimals: 2 })}
            </span>
          </div>

          {/* Span Pricing */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
              <div className="flex items-center gap-1">
                <Database size={14} className="text-gray-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Per 1K spans</span>
              </div>
            </div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {formatPrice(spanPricePerThousand, { decimals: 2 })}
            </span>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-2 dark:border-gray-700">
          <p className="text-xs text-gray-500">
            Usage-based billing for tokens and spans. Only pay for what you use.
          </p>
        </div>
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
                {isCreatingFreeSubscription ? 'Creating subscription...' : 'Preparing checkout...'}
              </>
            ) : (
              'Continue to Payment'
            )}
          </Button>
        </div>
      )}
      {showCheckout && clientSecret && (
        <div className="space-y-4">
          {billing.validatedDiscountCode && billing.validatedDiscountDescription && (
            <div className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950/20">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                <div>
                  <p className="text-sm font-medium text-green-900 dark:text-green-100">
                    Discount applied: {billing.validatedDiscountCode}
                  </p>
                  <p className="text-xs text-green-700 dark:text-green-200">
                    {billing.validatedDiscountDescription}
                  </p>
                </div>
              </div>
            </div>
          )}
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
              onPaymentElementReady={() => setStripeElementsLoaded(true)}
              onSuccess={() => {
                setStripeElementsLoaded(false);
                onPaymentSuccess?.(org.id);
                onClose();
              }}
              onError={(errorMessage: string) => {
                console.error('Payment error:', errorMessage);
              }}
              orgId={org.id}
              pricePerSeat={(allPricing?.seat?.amount || 4000) / 100}
              isFullyDiscounted={
                billing.validatedDiscountDescription?.includes('100%') ||
                billing.validatedDiscountDescription?.toLowerCase().includes('free')
              }
            />
          </CheckoutProvider>
        </div>
      )}
    </div>
  );

  const renderProOrgContent = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
          Manage Subscription
        </h3>
        <div className="flex items-center justify-center gap-2">
          <SubscriptionBadge
            tier={org.prem_status}
            showUpgrade={false}
            isCancelling={!!org.subscription_cancel_at_period_end}
            cancelDate={org.subscription_end_date || undefined}
            isLegacyBilling={_billingData?.is_legacy_billing}
            legacyCancellationDate={_billingData?.legacy_cancellation_date}
          />
        </div>
        {org && (
          <p className="mt-2 text-sm text-gray-500">
            {org.subscription_start_date && org.subscription_end_date
              ? `${new Date(org.subscription_start_date * 1000).toLocaleDateString()} - ${new Date(org.subscription_end_date * 1000).toLocaleDateString()}`
              : org.subscription_end_date
                ? `Next billing: ${new Date(org.subscription_end_date * 1000).toLocaleDateString()}`
                : 'Active subscription'}
          </p>
        )}
      </div>

      {/* Current Period Usage & Costs */}
      {_billingData?.current_period && !_billingData?.is_legacy_billing && (
        <div className="space-y-4 rounded-lg border p-4">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            Current Period Costs
          </h4>

          {/* Total Cost Summary */}
          <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
            <div className="flex items-center gap-2">
              <DollarSign size={16} className="text-gray-600 dark:text-gray-400" />
              <span className="font-medium text-gray-900 dark:text-white">Total this period</span>
            </div>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {formatPrice(_billingData.current_period.total_cost / 100, { decimals: 2 })}
            </span>
          </div>

          {/* Cost Breakdown */}
          <div className="space-y-3">
            {/* Seat Costs */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-blue-500"></div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Seats ({_billingData.current_period.seat_count} members)
                </span>
              </div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {formatPrice(_billingData.current_period.seat_cost / 100)}
              </span>
            </div>

            {/* Usage Costs */}
            {_billingData.current_period.usage_breakdown?.map((usage) => (
              <div key={usage.usage_type} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'h-3 w-3 rounded-full',
                      usage.usage_type === 'tokens' ? 'bg-green-500' : 'bg-yellow-500',
                    )}
                  ></div>
                  <div className="flex items-center gap-1">
                    {usage.usage_type === 'tokens' ? (
                      <Zap size={14} className="text-gray-500" />
                    ) : (
                      <Database size={14} className="text-gray-500" />
                    )}
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {usage.usage_type === 'tokens' ? 'Tokens' : 'Spans'} (
                      {usage.quantity.toLocaleString()})
                    </span>
                  </div>
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {formatPrice(usage.cost_cents / 100, { decimals: 2 })}
                </span>
              </div>
            ))}

            {/* Show zero usage message if no usage costs */}
            {(!_billingData.current_period.usage_breakdown ||
              _billingData.current_period.usage_breakdown.length === 0) && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">Usage costs</span>
                </div>
                <span className="text-sm font-medium text-gray-500">{formatPrice(0)}</span>
              </div>
            )}
          </div>

          {/* Period Info */}
          <div className="border-t border-gray-200 pt-2 dark:border-gray-700">
            <p className="text-xs text-gray-500">
              Period: {new Date(_billingData.current_period.period_start).toLocaleDateString()} -{' '}
              {new Date(_billingData.current_period.period_end).toLocaleDateString()}
            </p>
          </div>
        </div>
      )}

      {org.prem_status === 'pro' && _billingData?.is_legacy_billing && (
        <div className="rounded-lg border-l-4 border-l-purple-500 bg-purple-50 p-4 dark:bg-purple-950/20">
          <div className="flex items-start gap-3">
            <Crown
              size={20}
              className="mt-0.5 flex-shrink-0 text-purple-600 dark:text-purple-400"
            />
            <div className="flex-1">
              <h4 className="font-semibold text-purple-900 dark:text-purple-100">
                Legacy Billing Plan
              </h4>
              <p className="mt-1 text-sm text-purple-700 dark:text-purple-200">
                This subscription is on our legacy billing model and cannot be managed here. It will
                automatically end on{' '}
                <span className="font-medium">
                  {_billingData.legacy_cancellation_date
                    ? new Date(_billingData.legacy_cancellation_date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })
                    : 'Unknown'}
                </span>
                .
              </p>
            </div>
          </div>
        </div>
      )}

      {org.prem_status === 'pro' &&
        org.paid_member_count !== undefined &&
        !_billingData?.is_legacy_billing && (
          <div className="rounded-lg border p-4">
            <h4 className="mb-2 text-sm font-semibold">Licensed Members</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {org.paid_member_count || 0} licensed{' '}
              {org.paid_member_count === 1 ? 'member' : 'members'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Manage licenses in your organization settings
            </p>
          </div>
        )}
      {!org.subscription_id ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/20">
          <div className="flex items-start gap-3">
            <Crown size={20} className="mt-0.5 flex-shrink-0 text-amber-600 dark:text-amber-400" />
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
      ) : _billingData?.is_legacy_billing ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 dark:border-purple-800 dark:bg-purple-950/20">
            <p className="text-sm text-purple-700 dark:text-purple-200">
              Legacy subscriptions cannot be managed here. Your subscription will automatically end
              on the date shown above.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {org.subscription_cancel_at_period_end ? (
            <Button
              onClick={handleReactivateClick}
              disabled={isProcessing}
              variant="outline"
              className={cn(
                'w-full',
                confirmationState === 'reactivate' &&
                  'border-green-600 bg-green-50 dark:bg-green-950/20',
              )}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : confirmationState === 'reactivate' ? (
                <>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Confirm Reactivation
                </>
              ) : (
                <>
                  <Refresh className="mr-2 h-4 w-4" />
                  Reactivate Subscription
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleCancelClick}
              disabled={isProcessing}
              variant="outline"
              className={cn(
                'w-full',
                confirmationState === 'cancel' && 'border-red-600 bg-red-50 dark:bg-red-950/20',
              )}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : confirmationState === 'cancel' ? (
                <>
                  <X className="mr-2 h-4 w-4" />
                  Confirm Cancellation
                </>
              ) : (
                <>
                  <X className="mr-2 h-4 w-4" />
                  Cancel Subscription
                </>
              )}
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
              disabled={isProcessing}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Refresh size={14} />
              {isProcessing ? 'Refreshing...' : 'Refresh Data'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">{org.name}</DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          {isPaymentProcessing ? (
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
          ) : canManage ? (
            org.prem_status === 'free' ? (
              renderFreeOrgContent()
            ) : (
              renderProOrgContent()
            )
          ) : (
            <div className="py-8 text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                You don&apos;t have permission to manage this organization&apos;s subscription.
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
