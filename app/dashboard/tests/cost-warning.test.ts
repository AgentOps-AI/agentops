import { ISpan } from '@/types/ISpan';

// Mock spans for testing cost calculation warning logic
const createMockSpan = (overrides: Partial<ISpan> = {}): ISpan => ({
  span_id: 'test-span-id',
  parent_span_id: 'test-parent-span-id',
  span_name: 'test-span',
  span_kind: 'INTERNAL',
  service_name: 'test-service',
  start_time: '2024-01-01T00:00:00Z',
  end_time: '2024-01-01T00:00:01Z',
  duration: 1000000,
  durationMs: 1000,
  status_code: 'OK',
  status_message: '',
  attributes: {},
  resource_attributes: {},
  event_timestamps: [],
  event_names: [],
  event_attributes: [],
  link_trace_ids: [],
  link_span_ids: [],
  link_trace_states: [],
  link_attributes: [],
  span_type: 'test',
  span_attributes: {},
  ...overrides,
});

describe('Cost Calculation Warning Logic', () => {
  test('should detect LLM span with model but no cost', () => {
    const llmSpanWithModel = createMockSpan({
      span_name: 'llm:test',
      span_attributes: {
        gen_ai: {
          response: {
            model: 'gpt-4',
          },
        },
      },
    });

    // This span should have cost but doesn't
    const isLlmSpan = !!(
      llmSpanWithModel.span_name?.includes('llm') ||
      llmSpanWithModel.span_attributes?.gen_ai ||
      llmSpanWithModel.span_attributes?.agent?.model
    );

    const hasModel = !!(
      llmSpanWithModel.span_attributes?.gen_ai?.response?.model ||
      llmSpanWithModel.span_attributes?.gen_ai?.request?.model ||
      llmSpanWithModel.span_attributes?.agent?.model
    );

    const shouldHaveCost = isLlmSpan && hasModel;
    const hasCost = !!(
      llmSpanWithModel.metrics?.total_cost && Number(llmSpanWithModel.metrics.total_cost) > 0
    );

    expect(shouldHaveCost).toBe(true);
    expect(hasCost).toBe(false);
  });

  test('should not detect non-LLM span without cost', () => {
    const toolSpan = createMockSpan({
      span_name: 'tool:test',
      span_attributes: {
        tool: {
          name: 'test-tool',
        },
      },
    });

    const isLlmSpan = !!(
      toolSpan.span_name?.includes('llm') ||
      toolSpan.span_attributes?.gen_ai ||
      toolSpan.span_attributes?.agent?.model
    );

    const hasModel = !!(
      toolSpan.span_attributes?.gen_ai?.response?.model ||
      toolSpan.span_attributes?.gen_ai?.request?.model ||
      toolSpan.span_attributes?.agent?.model
    );

    const shouldHaveCost = isLlmSpan && hasModel;

    expect(shouldHaveCost).toBe(false);
  });

  test('should not detect LLM span without model', () => {
    const llmSpanWithoutModel = createMockSpan({
      span_name: 'llm:test',
      span_attributes: {
        gen_ai: {
          // No model specified
        },
      },
    });

    const isLlmSpan = !!(
      llmSpanWithoutModel.span_name?.includes('llm') ||
      llmSpanWithoutModel.span_attributes?.gen_ai ||
      llmSpanWithoutModel.span_attributes?.agent?.model
    );

    const hasModel = !!(
      llmSpanWithoutModel.span_attributes?.gen_ai?.response?.model ||
      llmSpanWithoutModel.span_attributes?.gen_ai?.request?.model ||
      llmSpanWithoutModel.span_attributes?.agent?.model
    );

    const shouldHaveCost = isLlmSpan && hasModel;

    expect(shouldHaveCost).toBe(false);
  });

  test('should not detect LLM span with model and cost', () => {
    const llmSpanWithCost = createMockSpan({
      span_name: 'llm:test',
      span_attributes: {
        gen_ai: {
          response: {
            model: 'gpt-4',
          },
        },
      },
      metrics: {
        total_cost: '0.001',
      },
    });

    const isLlmSpan = !!(
      llmSpanWithCost.span_name?.includes('llm') ||
      llmSpanWithCost.span_attributes?.gen_ai ||
      llmSpanWithCost.span_attributes?.agent?.model
    );

    const hasModel = !!(
      llmSpanWithCost.span_attributes?.gen_ai?.response?.model ||
      llmSpanWithCost.span_attributes?.gen_ai?.request?.model ||
      llmSpanWithCost.span_attributes?.agent?.model
    );

    const shouldHaveCost = isLlmSpan && hasModel;
    const hasCost = !!(
      llmSpanWithCost.metrics?.total_cost && Number(llmSpanWithCost.metrics.total_cost) > 0
    );

    expect(shouldHaveCost).toBe(true);
    expect(hasCost).toBe(true);
  });

  test('should detect agent span with model but no cost', () => {
    const agentSpanWithModel = createMockSpan({
      span_name: 'agent:test',
      span_attributes: {
        agent: {
          model: 'gpt-4',
        },
      },
    });

    const isLlmSpan = !!(
      agentSpanWithModel.span_name?.includes('llm') ||
      agentSpanWithModel.span_attributes?.gen_ai ||
      agentSpanWithModel.span_attributes?.agent?.model
    );

    const hasModel = !!(
      agentSpanWithModel.span_attributes?.gen_ai?.response?.model ||
      agentSpanWithModel.span_attributes?.gen_ai?.request?.model ||
      agentSpanWithModel.span_attributes?.agent?.model
    );

    const shouldHaveCost = isLlmSpan && hasModel;
    const hasCost = !!(
      agentSpanWithModel.metrics?.total_cost && Number(agentSpanWithModel.metrics.total_cost) > 0
    );

    expect(shouldHaveCost).toBe(true);
    expect(hasCost).toBe(false);
  });
});
