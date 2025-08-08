'use client';

import { PaymentElement, useCheckout } from '@stripe/react-stripe-js';
import React, { FormEvent, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  CheckmarkCircle01Icon as CheckCircle,
  ZapIcon as Zap,
  DatabaseIcon as Database,
} from 'hugeicons-react';
import { useAllStripePricing } from '@/hooks/queries/useStripeConfig';
import { formatPrice } from '@/lib/number_formatting_utils';
import { getPricingRates } from '@/lib/billing-utils';

interface EmbeddedCheckoutFormProps {
  onSuccess: () => void;
  onError: (message: string) => void;
  onPaymentElementReady?: () => void;
  orgId?: string;
  pricePerSeat?: number;
  isFullyDiscounted?: boolean;
}

export default function EmbeddedCheckoutForm({
  onSuccess,
  onError,
  onPaymentElementReady,
  orgId,
  pricePerSeat,
  isFullyDiscounted = false,
}: EmbeddedCheckoutFormProps) {
  const checkout = useCheckout();
  const { data: allPricing } = useAllStripePricing();
  const [isLoading, setIsLoading] = useState(false);
  const [paymentSuccessful, setPaymentSuccessful] = useState(false);

  const { tokenPricePerMillion, spanPricePerThousand } = getPricingRates(allPricing);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handlePaymentElementReady = () => {
    if (onPaymentElementReady) {
      onPaymentElementReady();
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!checkout) {
      onError('Stripe Checkout is not available yet. Please wait a moment and try again.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('stripe_payment_in_progress', 'true');
      if (orgId) {
        sessionStorage.setItem('orgId', orgId);
      }
    }

    const result = await checkout.confirm();

    setIsLoading(false);

    if (result.type === 'error') {
      const message = result.error.message || 'An unexpected error occurred.';
      setErrorMessage(message);
      onError(message);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('stripe_payment_in_progress');
        if (orgId) {
          sessionStorage.removeItem('orgId');
        }
      }
    } else if (result.type === 'success') {
      setPaymentSuccessful(true);
      onSuccess();
    } else {
      const message = 'An unexpected outcome from payment confirmation.';
      setErrorMessage(message);
      onError(message);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('stripe_payment_in_progress');
        if (orgId) {
          sessionStorage.removeItem('orgId');
        }
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {pricePerSeat && (
        <div className="rounded-lg border bg-gray-50 p-4 dark:bg-gray-900/50">
          <h4 className="mb-2 text-sm font-medium">Order Summary</h4>
          <div className="space-y-3">
            {/* Base Plan */}
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Pro Plan (1 seat for owner)</span>
              <span className="font-medium">${pricePerSeat.toFixed(2)}/month</span>
            </div>

            {/* Usage Pricing */}
            <div className="space-y-2 border-t border-gray-200 pt-2 dark:border-gray-700">
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                Usage-based pricing:
              </p>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-green-500"></div>
                  <Zap size={12} className="text-gray-500" />
                  <span className="text-gray-600 dark:text-gray-400">Per 1M tokens</span>
                </div>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {formatPrice(tokenPricePerMillion, {
                    decimals: 2,
                  })}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
                  <Database size={12} className="text-gray-500" />
                  <span className="text-gray-600 dark:text-gray-400">Per 1K spans</span>
                </div>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {formatPrice(spanPricePerThousand, { decimals: 2 })}
                </span>
              </div>

              {/* Free Usage Tier Information */}
              <div className="space-y-1 border-t border-gray-200 pt-2 dark:border-gray-700">
                <p className="text-xs font-medium text-green-700 dark:text-green-300">
                  Included free each month:
                </p>
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full bg-green-500"></div>
                    <Zap size={12} className="text-green-600" />
                    <span className="text-green-600 dark:text-green-400">Up to ~50K tokens</span>
                  </div>
                  <span className="text-xs text-green-600 dark:text-green-400">Free</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
                    <Database size={12} className="text-yellow-600" />
                    <span className="text-yellow-600 dark:text-yellow-400">Up to ~100K spans</span>
                  </div>
                  <span className="text-xs text-yellow-600 dark:text-yellow-400">Free</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Usage charges only apply when you exceed these thresholds.
                </p>
              </div>
            </div>

            <div className="text-xs text-gray-500 dark:text-gray-400">
              All organization members are automatically licensed and billed.
            </div>
          </div>
        </div>
      )}
      <div className="space-y-2">
        {!isFullyDiscounted ? (
          <PaymentElement id="payment-element" onReady={handlePaymentElementReady} />
        ) : (
          <div className="rounded-md bg-green-50 p-4 text-center dark:bg-green-950/20">
            <CheckCircle className="mx-auto mb-2 h-8 w-8 text-green-600 dark:text-green-400" />
            <p className="text-sm font-medium text-green-900 dark:text-green-100">
              No payment required
            </p>
            <p className="mt-1 text-sm text-green-700 dark:text-green-200">
              Your promo code covers the full amount
            </p>
          </div>
        )}
        {errorMessage && <div className="text-sm font-medium text-destructive">{errorMessage}</div>}
      </div>
      <Button disabled={!checkout || isLoading || paymentSuccessful} className="w-full">
        {paymentSuccessful ? (
          <>
            <CheckCircle className="mr-2 h-4 w-4" />
            Payment Successful - Updating...
          </>
        ) : isLoading ? (
          'Processing...'
        ) : (
          'Complete Order'
        )}
      </Button>
    </form>
  );
}
