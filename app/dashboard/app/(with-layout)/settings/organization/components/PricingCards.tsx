'use client';

import { CheckmarkCircle01Icon as Check } from 'hugeicons-react';
import { useAllStripePricing } from '@/hooks/queries/useStripeConfig';
import { Skeleton } from '@/components/ui/skeleton';
import { getPricingRates } from '@/lib/billing-utils';

export default function PricingCards() {
  const { data: allPricing, isLoading: pricingLoading } = useAllStripePricing();
  const { seatPrice } = getPricingRates(allPricing);

  const plans = [
    {
      name: 'Basic',
      price: '$0',
      period: 'per month',
      description: 'Free up to 5,000 events',
      features: ['Agent Agnostic SDK', 'LLM Cost Tracking (400+ LLMs)', 'Replay Analytics'],
      current: false,
    },
    {
      name: 'Pro',
      price: pricingLoading ? '...' : `$${seatPrice}`,
      period: pricingLoading ? '' : 'per month',
      description: '100k events included',
      features: [
        'Everything in Basic plus:',
        '100k events included',
        'Unlimited log retention',
        'Session and event export',
        'Dedicated Slack and email support',
        'Role-based permissioning',
      ],
      current: true,
      highlight: true,
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: "Going beyond? Let's chat",
      features: [
        'Everything in Pro plus:',
        'SLA',
        'Slack Connect',
        'Custom SSO',
        'On-premise deployment',
        'Custom data retention policy',
        'Self-hosting (AWS, GCP, Azure)',
        'SOC-2, HIPAA, NIST AI RMF',
      ],
      current: false,
    },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {plans.map((plan) => (
        <div
          key={plan.name}
          className={`relative rounded-lg border p-6 ${
            plan.highlight
              ? 'border-orange-500 bg-gradient-to-b from-orange-50/50 to-white dark:from-orange-950/20 dark:to-slate-900'
              : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-slate-900'
          }`}
        >
          {plan.highlight && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-amber-600 to-orange-600 px-3 py-1 text-xs font-semibold text-white">
              Recommended
            </div>
          )}

          <div className="mb-4">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">{plan.name}</h3>
            <div className="mt-2">
              {pricingLoading && plan.name === 'Pro' ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <span className="text-3xl font-bold text-gray-900 dark:text-white">
                  {plan.price}
                </span>
              )}
              {plan.period && (
                <span className="ml-1 text-sm text-gray-500 dark:text-gray-400">{plan.period}</span>
              )}
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{plan.description}</p>
          </div>

          <div className="space-y-3">
            {plan.features.map((feature, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-500" />
                <span
                  className={`text-sm ${
                    feature.endsWith(':') ? 'font-semibold' : ''
                  } text-gray-700 dark:text-gray-300`}
                >
                  {feature}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
