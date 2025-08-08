export interface ISpan {
  span_id: string;
  parent_span_id: string;
  span_name: string;
  span_kind: string;
  service_name: string;
  start_time: string;
  end_time: string;
  duration: number;
  durationMs: number;
  status_code: string;
  status_message: string;
  attributes: Record<string, any>;
  resource_attributes: IResourceAttributes;
  event_timestamps: any[];
  event_names: any[];
  event_attributes: any[];
  link_trace_ids: any[];
  link_span_ids: any[];
  link_trace_states: any[];
  link_attributes: any[];
  span_type: string;
  span_attributes: ISpanAttributes;
  metrics?: IMetrics;
}

/**
 * Metrics for token usage and cost
 */
export interface IMetrics {
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cache_read_input_tokens?: number;
  reasoning_tokens?: number;
  success_tokens?: number;
  fail_tokens?: number;
  indeterminate_tokens?: number;
  prompt_cost?: string;
  completion_cost?: string;
  total_cost?: string;
  [key: string]: any;
}

/**
 * Represents a message in a conversation
 */
interface IMessage {
  [key: string]: {
    role: 'system' | 'user' | 'assistant' | string;
    content: string;
    finish_reason?: string;
  };
}

/**
 * OpenAI/LLM specific attributes
 */
interface IGenAIAttributes {
  system?: string;
  prompt?: IMessage[];
  completion?: IMessage[];
  request?: {
    model?: string;
    [key: string]: any;
  };
  response?: {
    id?: string;
    model?: string;
    [key: string]: any;
  };
  usage?: {
    prompt_tokens?: string;
    completion_tokens?: string;
    total_tokens?: string;
    [key: string]: any;
  };
  openai?: {
    api_base?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

/**
 * LLM specific attributes
 */
interface ILLMAttributes {
  usage?: {
    total_tokens?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

/**
 * Agent specific attributes
 */
interface IAgentAttributes {
  id?: string;
  models?: string;
  name?: string;
  role?: string;
  tools?: string;
  reasoning?: string;
  [key: string]: any;
}

/**
 * Tool specific attributes
 */
export interface IToolAttributes {
  description?: string;
  id?: string;
  name?: string;
  parameters?: string;
  result?: string;
  status?: string;
  [key: string]: any;
}

/**
 * Span attributes
 */
interface ISpanAttributes {
  span?: {
    kind?: string;
    [key: string]: any;
  };
  gen_ai?: IGenAIAttributes;
  llm?: ILLMAttributes;
  agent?: IAgentAttributes;
  tool?: IToolAttributes;
  arg?: {
    [key: string]: any;
  };
  result?: string;
  user?: {
    id?: string;
    [key: string]: any;
  };
  connection?: {
    type?: string;
    [key: string]: any;
  };
  database?: {
    type?: string;
    [key: string]: any;
  };
  error?: {
    message?: string;
    type?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

/**
 * Resource attributes
 */
interface IResourceAttributes {
  'agentops.project.id'?: string;
  'host.name'?: string;
  'os.type'?: string;
  'service.name'?: string;
  [key: string]: any;
}
