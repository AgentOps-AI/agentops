import { useMemo } from 'react';
import { ISpan } from '@/types/ISpan';

interface TotalCostAcrossSpans {
  totalCost: number;
  formattedTotalCost: string;
  hasAnyCost: boolean;
  hasCostCalculationIssues: boolean;
}

interface TokenStats {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  hasAnyTokens: boolean;
}

export function useTraceStats(spans: ISpan[] = []) {
  const totalCostAcrossSpans: TotalCostAcrossSpans = useMemo(() => {
    if (!spans || spans.length === 0)
      return { 
        totalCost: 0, 
        formattedTotalCost: '$0.0000000', 
        hasAnyCost: false,
        hasCostCalculationIssues: false 
      };

    let total = 0;
    let hasNonZeroCost = false;
    let hasCostCalculationIssues = false;

    spans.forEach((span) => {
      const costData = span.metrics || span.span_attributes?.metrics;
      
      // Check if this is an LLM span that should have cost
      const isLlmSpan = !!(span.span_name?.includes('llm') || 
                           span.span_attributes?.gen_ai ||
                           span.span_attributes?.agent?.model);
      
      const hasModel = !!(span.span_attributes?.gen_ai?.response?.model ||
                          span.span_attributes?.gen_ai?.request?.model ||
                          span.span_attributes?.agent?.model);
      
      const shouldHaveCost = isLlmSpan && hasModel;
      const hasCost = !!(costData?.total_cost && Number(costData.total_cost) > 0);
      
      // If it should have cost but doesn't, mark as having calculation issues
      if (shouldHaveCost && !hasCost) {
        hasCostCalculationIssues = true;
      }
      
      if (costData?.total_cost) {
        const costValue = Number(costData.total_cost);
        if (costValue > 0) {
          total += costValue;
          hasNonZeroCost = true;
        }
      }
    });

    return {
      totalCost: total,
      formattedTotalCost: `$${total.toFixed(7)}`,
      hasAnyCost: hasNonZeroCost,
      hasCostCalculationIssues,
    };
  }, [spans]);

  const tokenStats: TokenStats = useMemo(() => {
    if (!spans || spans.length === 0)
      return {
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
        hasAnyTokens: false,
      };

    let promptTotal = 0;
    let completionTotal = 0;
    let totalTokensFound = 0;
    let hasTokens = false;

    spans.forEach((span) => {
      const metricsData = span.metrics || span.span_attributes?.metrics;
      const genAiData = span.span_attributes?.gen_ai?.usage;

      if (metricsData?.prompt_tokens) {
        const tokens = Number(metricsData.prompt_tokens);
        if (tokens > 0) {
          promptTotal += tokens;
          hasTokens = true;
        }
      } else if (genAiData?.prompt_tokens) {
        const tokens = Number(genAiData.prompt_tokens);
        if (tokens > 0) {
          promptTotal += tokens;
          hasTokens = true;
        }
      }

      if (metricsData?.completion_tokens) {
        const tokens = Number(metricsData.completion_tokens);
        if (tokens > 0) {
          completionTotal += tokens;
          hasTokens = true;
        }
      } else if (genAiData?.completion_tokens) {
        const tokens = Number(genAiData.completion_tokens);
        if (tokens > 0) {
          completionTotal += tokens;
          hasTokens = true;
        }
      }

      if (metricsData?.total_tokens) {
        const tokens = Number(metricsData.total_tokens);
        if (tokens > 0) {
          totalTokensFound += tokens;
          hasTokens = true;
        }
      } else if (genAiData?.total_tokens) {
        const tokens = Number(genAiData.total_tokens);
        if (tokens > 0) {
          totalTokensFound += tokens;
          hasTokens = true;
        }
      }
    });

    const calculatedTotal = totalTokensFound > 0 ? totalTokensFound : promptTotal + completionTotal;

    return {
      promptTokens: promptTotal,
      completionTokens: completionTotal,
      totalTokens: calculatedTotal,
      hasAnyTokens: hasTokens,
    };
  }, [spans]);

  const llmCount = useMemo(
    () => spans.filter((span) => !!span.span_attributes?.gen_ai).length,
    [spans],
  );
  const toolCount = useMemo(
    () => spans.filter((span) => !!span.span_attributes?.tool).length,
    [spans],
  );

  return { totalCostAcrossSpans, tokenStats, llmCount, toolCount };
} 