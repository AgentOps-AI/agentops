import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { DollarSign, Zap, Database, Users } from 'lucide-react';
import { formatPrice, formatLargePrice, formatNumber } from '@/lib/number_formatting_utils';
import { BillingBreakdownChart } from '@/components/charts/pie-chart/billing-breakdown-chart';
import { calculateTokenCost, calculateSpanCost, getPricingRates } from '@/lib/billing-utils';

interface BillingCalculatorProps {
  allPricing?: {
    seat?: { amount: number; interval: string };
    tokens?: { amount: number };
    spans?: { amount: number };
  };
  pricingLoading?: boolean;
}

interface CalculatorState {
  seats: number;
  tokensMillions: number;
  spansThousands: number;
}

const COLORS = {
  seats: '#3b82f6',
  tokens: '#10b981',
  spans: '#f59e0b',
};

export function BillingCalculator({ allPricing, pricingLoading }: BillingCalculatorProps) {
  const [calculatorState, setCalculatorState] = useState<CalculatorState>({
    seats: 1,
    tokensMillions: 1,
    spansThousands: 10,
  });

  // Get pricing rates using centralized utility
  const { seatPrice, tokenPricePerMillion, spanPricePerThousand } = getPricingRates(allPricing);

  // Calculate costs
  const costs = useMemo(() => {
    const seatCost = calculatorState.seats * seatPrice;
    const tokenCost = calculateTokenCost(calculatorState.tokensMillions * 1_000_000, allPricing);
    const spanCost = calculateSpanCost(calculatorState.spansThousands * 1_000, allPricing);
    const totalCost = seatCost + tokenCost + spanCost;

    return {
      seats: seatCost,
      tokens: tokenCost,
      spans: spanCost,
      total: totalCost,
    };
  }, [calculatorState, seatPrice, allPricing]);

  // Create cost breakdown for chart
  const costBreakdown = useMemo(() => {
    return [
      { name: 'Seats', value: costs.seats, color: COLORS.seats },
      { name: 'Tokens', value: costs.tokens, color: COLORS.tokens },
      { name: 'Spans', value: costs.spans, color: COLORS.spans },
    ].filter((item) => item.value > 0);
  }, [costs]);

  const handleInputChange = (field: keyof CalculatorState, value: number) => {
    setCalculatorState((prev) => ({
      ...prev,
      [field]: Math.max(0, value),
    }));
  };

  const handleSliderChange = (field: keyof CalculatorState, values: number[]) => {
    setCalculatorState((prev) => ({
      ...prev,
      [field]: values[0],
    }));
  };

  if (pricingLoading) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Loading Calculator...
          </h3>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
          Billing Calculator
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Estimate your monthly costs based on expected usage
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Controls */}
        <div className="space-y-6">
          {/* Seats Calculator */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Users className="h-5 w-5 text-blue-500" />
                Team Members
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="seats-input" className="text-sm font-medium">
                  Number of licensed members{' '}
                  <span className="italic text-gray-500">
                    ({formatPrice(seatPrice)} per seat per {allPricing?.seat?.interval || 'month'})
                  </span>
                </Label>
                <Input
                  id="seats-input"
                  type="number"
                  min="1"
                  max="100"
                  value={calculatorState.seats}
                  onChange={(e) => handleInputChange('seats', parseInt(e.target.value) || 0)}
                  className="text-lg font-semibold"
                />
              </div>
              <div className="space-y-2">
                <Slider
                  value={[calculatorState.seats]}
                  onValueChange={(values) => handleSliderChange('seats', values)}
                  max={100}
                  min={1}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1</span>
                  <span>100</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tokens Calculator */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Zap className="h-5 w-5 text-green-500" />
                API Tokens
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tokens-input" className="text-sm font-medium">
                  Millions of tokens per month{' '}
                  <span className="italic text-gray-500">
                    ({formatPrice(tokenPricePerMillion, { decimals: 2 })} per 1M tokens)
                  </span>
                </Label>
                <Input
                  id="tokens-input"
                  type="number"
                  min="0"
                  step="1"
                  value={calculatorState.tokensMillions}
                  onChange={(e) =>
                    handleInputChange('tokensMillions', parseFloat(e.target.value) || 0)
                  }
                  className="text-lg font-semibold"
                />
              </div>
              <div className="space-y-2">
                <Slider
                  value={[calculatorState.tokensMillions]}
                  onValueChange={(values) => handleSliderChange('tokensMillions', values)}
                  max={100000}
                  min={0}
                  step={100}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>0M</span>
                  <span>100B</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Spans Calculator */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-5 w-5 text-amber-500" />
                Span Uploads
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="spans-input" className="text-sm font-medium">
                  Thousands of spans per month{' '}
                  <span className="italic text-gray-500">
                    ({formatPrice(spanPricePerThousand, { decimals: 2 })} per 1K spans)
                  </span>
                </Label>
                <Input
                  id="spans-input"
                  type="number"
                  min="0"
                  step="1"
                  value={calculatorState.spansThousands}
                  onChange={(e) =>
                    handleInputChange('spansThousands', parseInt(e.target.value) || 0)
                  }
                  className="text-lg font-semibold"
                />
              </div>
              <div className="space-y-2">
                <Slider
                  value={[calculatorState.spansThousands]}
                  onValueChange={(values) => handleSliderChange('spansThousands', values)}
                  max={1000}
                  min={0}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>0K</span>
                  <span>1000K</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Cost Summary */}
        <div className="space-y-6">
          {/* Cost Breakdown Chart */}
          {costBreakdown.length > 0 && <BillingBreakdownChart costBreakdown={costBreakdown} />}

          {/* Estimated Total Cost */}
          <div className="flex justify-center">
            <div className="w-full max-w-md">
              <Card className="h-full border-2 border-primary bg-gradient-to-br from-primary/5 to-primary/10">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <DollarSign className="h-6 w-6 text-primary" />
                    Estimated Monthly Total
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col justify-center">
                  <div className="text-center">
                    <p className="break-words text-4xl font-bold text-primary">
                      {formatLargePrice(costs.total)}
                    </p>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      per month for your estimated usage
                    </p>
                  </div>

                  <div className="mt-6 space-y-2 border-t pt-4">
                    <div className="flex justify-between text-sm">
                      <span className="truncate">Base (Seats):</span>
                      <span className="ml-2 text-right font-medium">
                        {formatLargePrice(costs.seats)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="truncate">API Tokens:</span>
                      <span className="ml-2 text-right font-medium">
                        {formatLargePrice(costs.tokens)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="truncate">Span Uploads:</span>
                      <span className="ml-2 text-right font-medium">
                        {formatLargePrice(costs.spans)}
                      </span>
                    </div>
                    <div className="flex justify-between border-t pt-2 font-semibold">
                      <span className="truncate">Total:</span>
                      <span className="ml-2 text-right">{formatLargePrice(costs.total)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
