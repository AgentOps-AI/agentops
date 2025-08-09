'use client';

import React, { Suspense, useEffect, useCallback, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

import { useToast } from '@/components/ui/use-toast';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { acceptOrgInviteAPI } from '@/lib/api/orgs';
import { BillingProvider, useBilling } from '@/app/providers/billing-provider';
import { OrgManagementDashboard } from './components/OrgManagementDashboard';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useBillingData } from '@/hooks/queries/useBillingData';
import { useSearchParams } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { CrownIcon as Crown, Cancel01Icon as X } from 'hugeicons-react';
import { useRef } from 'react';

interface CreateCheckoutSessionBody {
  price_id: string;
  discount_code?: string;
  quantity?: number;
}

interface UpdateSubscriptionBody {
  proration_behavior?: 'create_prorations' | 'always_invoice' | 'none';
  price_id?: string;
}

function InviteAcceptanceWrapper({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { toast } = useToast();
  const inviteOrgId = searchParams.get('invite');

  const [pendingInvite, setPendingInvite] = useState<string | null>(null);

  useEffect(() => {
    const storedInvite = sessionStorage.getItem('pendingInvite');
    if (storedInvite && !inviteOrgId) {
      setPendingInvite(storedInvite);
      sessionStorage.removeItem('pendingInvite');
    }
  }, [inviteOrgId]);

  const inviteToProcess = inviteOrgId || pendingInvite;
  const [isProcessingInvite, setIsProcessingInvite] = useState(!!inviteToProcess);
  const [inviteProcessed, setInviteProcessed] = useState(false);
  const [acceptedOrgId, setAcceptedOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (inviteToProcess && !inviteProcessed) {
      const handleInviteAcceptance = async () => {
        const maxRetries = 5;
        const baseDelay = 1000;

        for (let attempt = 0; attempt < maxRetries; attempt++) {
          const delay = baseDelay * Math.pow(2, attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));

          try {
            const response = await acceptOrgInviteAPI(inviteToProcess);

            if (response?.success) {
              toast({
                title: 'Invitation Accepted',
                description: 'You have successfully joined the organization!',
                variant: 'default',
              });

              setAcceptedOrgId(inviteToProcess);
              setInviteProcessed(true);
              setIsProcessingInvite(false);

              const url = new URL(window.location.href);
              url.searchParams.delete('invite');
              router.replace(url.toString());

              return;
            } else {
              if (response?.message && !response.message.includes('Authentication required')) {
                toast({
                  title: 'Failed to Accept Invitation',
                  description: response.message,
                  variant: 'destructive',
                });
                setInviteProcessed(true);
                setIsProcessingInvite(false);

                const url = new URL(window.location.href);
                url.searchParams.delete('invite');
                router.replace(url.toString());
                return;
              }

              if (attempt < maxRetries - 1) {
                continue;
              }

              toast({
                title: 'Failed to Accept Invitation',
                description: 'Unable to accept the invitation. Please try refreshing the page.',
                variant: 'destructive',
              });
            }
          } catch (error: unknown) {
            if (
              error instanceof Error &&
              error.message?.includes('401') &&
              attempt < maxRetries - 1
            ) {
              continue;
            }
            toast({
              title: 'Error',
              description:
                attempt === maxRetries - 1
                  ? 'Unable to accept invitation after multiple attempts. Please try refreshing the page.'
                  : 'An error occurred while accepting the invitation',
              variant: 'destructive',
            });
          }
        }

        setInviteProcessed(true);
        setIsProcessingInvite(false);

        const url = new URL(window.location.href);
        url.searchParams.delete('invite');
        router.replace(url.toString());
      };

      handleInviteAcceptance();
    }
  }, [inviteToProcess, router, toast, inviteProcessed]);

  if (isProcessingInvite) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="space-y-4 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin" />
          <p className="text-muted-foreground">Processing invitation...</p>
        </div>
      </div>
    );
  }

  if (acceptedOrgId && React.isValidElement(children)) {
    return (
      <>
        {React.cloneElement(children as React.ReactElement<{ defaultOrgId?: string }>, {
          defaultOrgId: acceptedOrgId,
        })}
      </>
    );
  }

  return <>{children}</>;
}

function BillingPageContent({ defaultOrgId }: { defaultOrgId?: string }) {
  const { data, loadingState, refetch } = useBillingData();
  const billing = useBilling();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const lastCallTimestamp = useRef<number>(0);

  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(defaultOrgId || null);
  const [showBillingBanner, setShowBillingBanner] = useState(true);

  // Check if banner was dismissed on component mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const dismissed = localStorage.getItem('billing-banner-dismissed');
      if (dismissed === 'true') {
        setShowBillingBanner(false);
      }
    }
  }, []);

  useEffect(() => {
    if (data?.orgs && data.orgs.length > 0 && !selectedOrgId) {
      if (defaultOrgId && data.orgs.some((org) => org.id === defaultOrgId)) {
        setSelectedOrgId(defaultOrgId);
      } else {
        setSelectedOrgId(data.orgs[0].id);
      }
    }
  }, [data?.orgs, selectedOrgId, defaultOrgId]);

  const handlePaymentSuccessFromRedirect = useCallback(
    (orgId: string) => {
      toast({
        title: 'Payment Successful!',
        description: 'Your subscription is being activated. This may take a few moments.',
        variant: 'default',
      });

      let pollCount = 0;
      const pollInterval = setInterval(async () => {
        const currentOrgs = await refetch.orgs();
        const updatedOrg = currentOrgs.data?.find((o) => o.id === orgId);
        pollCount++;

        if (updatedOrg?.subscription_id && updatedOrg.prem_status === 'pro') {
          clearInterval(pollInterval);

          billing.setPaymentProcessing(orgId, false);
          billing.resetOrgState(orgId);

          // Invalidate billing dashboard query to refresh seat count
          await queryClient.invalidateQueries({
            queryKey: ['billing-dashboard', orgId],
          });

          toast({
            title: 'Subscription Active!',
            description: 'Your Pro subscription is now active.',
            variant: 'default',
          });
        } else if (pollCount >= 10) {
          clearInterval(pollInterval);
          billing.setPaymentProcessing(orgId, false);

          if (!updatedOrg?.subscription_id) {
            toast({
              title: 'Update Delayed',
              description:
                'Your payment was successful but the update is taking longer than expected. Please refresh the page in a moment.',
              variant: 'default',
            });
            billing.resetOrgState(orgId);
          }
        }
      }, 3000);
    },
    [refetch, toast, billing, queryClient],
  );

  useEffect(() => {
    const urlOrgId = searchParams.get('org_id');
    const checkoutStatus = searchParams.get('checkout_status');
    const paymentWasInProgress =
      typeof window !== 'undefined' &&
      sessionStorage.getItem('stripe_payment_in_progress') === 'true';
    const sessionOrgId = typeof window !== 'undefined' ? sessionStorage.getItem('orgId') : null;

    const orgId = urlOrgId || sessionOrgId;

    if (orgId && (checkoutStatus === 'complete' || paymentWasInProgress)) {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('stripe_payment_in_progress');
        sessionStorage.removeItem('orgId');
      }

      billing.setPaymentProcessing(orgId, true);
      handlePaymentSuccessFromRedirect(orgId);

      const url = new URL(window.location.href);
      url.searchParams.delete('org_id');
      url.searchParams.delete('checkout_status');
      router.replace(url.toString());
    }
  }, [searchParams, router, billing, handlePaymentSuccessFromRedirect]);

  const getCurrentTierPriceId = () => {
    return data?.pricing?.seat?.priceId || '';
  };

  const handleValidateDiscount = async (orgId: string, discountCode: string) => {
    try {
      const response = await fetchAuthenticatedApi(
        `/opsboard/orgs/${orgId}/validate-discount-code`,
        {
          method: 'POST',
          body: JSON.stringify({ discount_code: discountCode }),
        },
      );

      if (response.valid) {
        billing.setDiscount(discountCode, response.discount_description);
        return {
          valid: true,
          discount_description: response.discount_description,
          is_100_percent_off: response.is_100_percent_off,
        };
      }

      return { valid: false };
    } catch (error) {
      return { valid: false };
    }
  };

  const fetchClientSecretInternal = async (orgId: string): Promise<string> => {
    const priceId = getCurrentTierPriceId();
    const currentOrg = data?.orgs?.find((org) => org.id === orgId);
    const quantity = currentOrg?.paid_member_count || 1;

    const body: CreateCheckoutSessionBody = {
      price_id: priceId,
      quantity: quantity,
    };

    if (billing.validatedDiscountCode) {
      body.discount_code = billing.validatedDiscountCode;
    }

    const response = await fetchAuthenticatedApi(
      `/opsboard/orgs/${orgId}/create-checkout-session`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    );

    return response.clientSecret;
  };

  const handleUpgradeClicked = async (orgId: string) => {
    // Prevent rapid double-clicks using timestamp-based debouncing
    const now = Date.now();
    if (now - lastCallTimestamp.current < 1000) {
      // 1 second debounce
      return;
    }
    lastCallTimestamp.current = now;

    // Prevent double-clicks by checking if already fetching
    if (billing.isFetchingClientSecret) {
      return;
    }

    try {
      billing.setFetchingClientSecret(true);
      const clientSecret = await fetchClientSecretInternal(orgId);
      billing.setClientSecret(clientSecret);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to start upgrade process. Please try again.',
        variant: 'destructive',
      });
    } finally {
      billing.setFetchingClientSecret(false);
    }
  };

  const handleRefreshSubscription = async (orgId: string) => {
    try {
      await fetchAuthenticatedApi(`/opsboard/orgs/${orgId}/subscription-detail`, {
        method: 'GET',
      });

      toast({
        title: 'Subscription Refreshed',
        description: 'Subscription details have been refreshed successfully.',
        variant: 'default',
      });

      // Refresh org data and billing dashboard
      await refetch.orgs();
      await queryClient.invalidateQueries({
        queryKey: ['billing-dashboard', orgId],
      });
    } catch (error) {
      toast({
        title: 'Refresh Failed',
        description: 'Failed to refresh subscription details. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateSubscription = async (
    orgId: string,
    options: {
      priceId?: string;
      prorationBehavior?: 'create_prorations' | 'always_invoice' | 'none';
    } = {},
  ) => {
    try {
      const body: UpdateSubscriptionBody = {
        proration_behavior: options.prorationBehavior || 'create_prorations',
      };

      if (options.priceId) {
        body.price_id = options.priceId;
      }

      const response = await fetchAuthenticatedApi(`/opsboard/orgs/${orgId}/update-subscription`, {
        method: 'POST',
        body: JSON.stringify(body),
      });

      toast({
        title: 'Subscription Updated',
        description: response.message || 'Your subscription has been updated successfully.',
        variant: 'default',
      });

      await refetch.orgs();
    } catch (error) {
      toast({
        title: 'Update Failed',
        description: 'Failed to update subscription. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleOpenCustomerPortal = async (orgId: string) => {
    try {
      const response = await fetchAuthenticatedApi(`/opsboard/orgs/${orgId}/customer-portal`, {
        method: 'POST',
      });

      if (response.url) {
        window.open(response.url, '_blank');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to open customer portal. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleCancelClicked = async (
    orgId: string,
    subscriptionId: string | null,
  ): Promise<void> => {
    try {
      if (!subscriptionId) {
        throw new Error('No subscription ID provided');
      }

      const response = await fetchAuthenticatedApi(`/opsboard/orgs/${orgId}/cancel-subscription`, {
        method: 'POST',
        body: JSON.stringify({ subscription_id: subscriptionId }),
      });

      toast({
        title: 'Subscription Cancelled',
        description:
          response.message ||
          'Your subscription has been cancelled and will end at the current billing period.',
        variant: 'default',
      });
      await refetch.orgs();
      await queryClient.invalidateQueries({
        queryKey: ['billing-dashboard', orgId],
      });
    } catch (error) {
      toast({
        title: 'Cancellation Failed',
        description: 'Failed to cancel subscription. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleReactivateClicked = async (
    orgId: string,
    subscriptionId: string | null,
  ): Promise<void> => {
    try {
      if (!subscriptionId) {
        throw new Error('No subscription ID provided');
      }

      const response = await fetchAuthenticatedApi(
        `/opsboard/orgs/${orgId}/reactivate-subscription`,
        {
          method: 'POST',
        },
      );

      toast({
        title: 'Subscription Reactivated',
        description: response.message || 'Your subscription has been reactivated successfully.',
        variant: 'default',
      });

      await refetch.orgs();
      await queryClient.invalidateQueries({
        queryKey: ['billing-dashboard', orgId],
      });
    } catch (error) {
      toast({
        title: 'Reactivation Failed',
        description: 'Failed to reactivate subscription. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleCheckoutNeeded = async (orgId: string) => {
    // Prevent rapid double-clicks using timestamp-based debouncing
    const now = Date.now();
    if (now - lastCallTimestamp.current < 1000) {
      // 1 second debounce
      return;
    }
    lastCallTimestamp.current = now;

    // Prevent double-clicks by checking if already fetching
    if (billing.isFetchingClientSecret) {
      return;
    }

    try {
      billing.setFetchingClientSecret(true);
      const clientSecret = await fetchClientSecretInternal(orgId);
      billing.setClientSecret(clientSecret);
      billing.setSelectedOrgForCheckout(orgId);
      billing.setExpandedOrg(orgId);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to set up checkout. Please try again.',
        variant: 'destructive',
      });
    } finally {
      billing.setFetchingClientSecret(false);
    }
  };

  const fetchClientSecret = async () => {
    const orgId = billing.selectedOrgForCheckout;
    if (!orgId) {
      throw new Error('No organization selected for checkout');
    }
    return await fetchClientSecretInternal(orgId);
  };

  const handlePaymentSuccess = async (_orgId: string) => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('stripe_payment_in_progress', 'true');
      sessionStorage.setItem('orgId', _orgId);
    }
    billing.setPaymentProcessing(_orgId, true);

    // Invalidate billing dashboard query to refresh seat count and other billing data
    await queryClient.invalidateQueries({
      queryKey: ['billing-dashboard', _orgId],
    });

    // Also refetch org data to ensure subscription badge updates
    await refetch.orgs();
  };

  const handleCreateFreeSubscription = async (orgId: string, discountCode?: string) => {
    try {
      const response = await fetchAuthenticatedApi(
        `/opsboard/orgs/${orgId}/create-free-subscription`,
        {
          method: 'POST',
          body: JSON.stringify({
            price_id: getCurrentTierPriceId(),
            discount_code: discountCode,
          }),
        },
      );

      toast({
        title: 'Subscription Created',
        description: response.message || 'Your free subscription has been created successfully.',
        variant: 'default',
      });

      await refetch.orgs();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create subscription. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const selectedOrg = data?.orgs?.find((org) => org.id === selectedOrgId);

  if (loadingState.isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-red-500">
            Error loading billing data: {loadingState.error?.message || 'Unknown error'}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loadingState.isLoading && !data?.orgs) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!data?.orgs || data.orgs.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-gray-500">
            No organizations found. Create an organization to manage billing.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Billing System Updated Banner */}
      {selectedOrg && showBillingBanner && (
        <Card className="border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-950/20">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <Crown className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400" />
                <div>
                  <h4 className="font-semibold text-blue-900 dark:text-blue-100">
                    Billing System Updated
                  </h4>
                  <p className="mt-1 text-sm text-blue-700 dark:text-blue-200">
                    We have updated our billing to include seat-based, and usage based billing. We
                    automatically cancelled your existing subscriptions. You can re-subscribe to set
                    up a new subscription. Charges will be added at the end of the first month of
                    your new subscription.
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  // Hide banner by setting localStorage flag and state
                  if (typeof window !== 'undefined') {
                    localStorage.setItem('billing-banner-dismissed', 'true');
                  }
                  setShowBillingBanner(false);
                }}
                className="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {selectedOrg && (
        <OrgManagementDashboard
          orgs={data.orgs}
          orgId={selectedOrg.id}
          org={selectedOrg}
          onOrgChange={setSelectedOrgId}
          onUpgradeClicked={handleUpgradeClicked}
          onCancelClicked={handleCancelClicked}
          onReactivateClicked={handleReactivateClicked}
          onUpdateSubscription={handleUpdateSubscription}
          onRefreshSubscription={handleRefreshSubscription}
          onOpenCustomerPortal={handleOpenCustomerPortal}
          onValidateDiscount={handleValidateDiscount}
          onCheckoutNeeded={handleCheckoutNeeded}
          onPaymentSuccess={handlePaymentSuccess}
          onCreateFreeSubscription={handleCreateFreeSubscription}
          clientSecret={billing.clientSecret}
          isFetchingClientSecret={billing.isFetchingClientSecret}
          fetchClientSecret={fetchClientSecret}
        />
      )}
    </div>
  );
}

export default function SettingsOrgManagementPage() {
  return (
    <BillingProvider>
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        }
      >
        <InviteAcceptanceWrapper>
          <BillingPageContent />
        </InviteAcceptanceWrapper>
      </Suspense>
    </BillingProvider>
  );
}
