import { Tables } from '@/lib/types_db';

export interface ISessionAndStats extends Omit<Tables<'sessions'>, 'host_env'> {
  host_env: HostEnv | null;
  stats: Tables<'stats'>;
}
export type HostEnv = {
  OS?: OS;
  RAM?: RAM;
  CPU?: CPU;
  SDK?: SDK;
  Disk?: Disk;
  'Installed Packages'?: InstalledPackages;
  'Virtual Environment'?: VirtualEnvironment;
  'Project Working Directory'?: ProjectWorkingDirectory;
};

type OS = {
  OS: string;
  Hostname: string;
  'OS Release': string;
  'OS Version': string;
};

type RAM = {
  Used: string;
  Total: string;
  Available: string;
  Percentage: string;
};

type CPU = {
  'CPU Usage': string;
  'Total cores': number;
  'Physical cores': number;
};

type SDK = {
  'Python Version': string;
  'System Packages': SystemPackages;
  'AgentOps SDK Version': string;
};

export type SystemPackages = {
  [key: string]: string;
};

type Disk = {
  [key: string]: {
    Free: string;
    Used: string;
    Total: string;
    Mountpoint: string;
    Percentage: string;
  };
};

type InstalledPackages = {
  'Installed Packages': {
    [key: string]: string;
  };
};

type VirtualEnvironment = {
  'Virtual Environment': string;
};

type ProjectWorkingDirectory = {
  'Project Working Directory': string;
};

/*
 * Prompt Messages and Completion Messages are validated against a json schema before
 * being stored in Supabase. While Supabase only knows that the fields are JSON, we
 * know their full shapes.
 */
export type llms = Omit<Tables<'llms'>, 'prompt' | 'completion'> & {
  prompt: prompt;
  completion: completion;
};

export type prompt = chatmlPrompt | promptCompletionString;
export type completion = {
  type: 'string' | 'chatml';
  string?: string;
  messages?: chatmlTextMessage;
};

export type chatmlPrompt = {
  type: 'chatml';
  messages: chatmlTextMessage[] | chatmlImageMessage[];
};

export type toolCall = {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
};

export type functionCall = toolCall;

type chatmlTextMessage = {
  role: string;
  content: string;
  tool_calls?: {
    id: string;
    function: {
      name: string;
      arguments: string;
    };
  }[];
};

type chatmlImageMessage = {
  role: 'user' | 'assistant';
  content:
    | {
        type: 'text';
        text: string;
      }
    | {
        type: 'image_url';
        image_url: {
          url: string;
        };
      };
};

type promptCompletionString = {
  type: 'string';
  string: string;
};

export interface IExtendedSession {
  id: string;
  agents: Tables<'agents'>[] | null;
  threads: Tables<'threads'>[] | null;
  llms: llms[] | null;
  actions: Tables<'actions'>[] | null;
  tools: Tables<'tools'>[] | null;
  errors: Tables<'errors'>[] | null;
}

export interface ILlms extends llms {
  type: 'LLM Call';
}

export interface ITools extends Tables<'tools'> {
  type: 'Tool';
}

export interface IActions extends Tables<'actions'> {
  type: 'Action';
}

export interface IErrors extends Tables<'errors'> {
  type: 'Error';
}

export type IEvent = IActions | ILlms | ITools;

/**
 * Pagination parameters for API requests
 */
export interface PaginationParams {
  limit?: number;
  offset?: number;
}

/**
 * Session representation
 */
export interface Session {
  id: string;
  projectId: string;
  startTime: Date;
  endTime: Date | null;
  durationMs: number;
  endState: string;
  tags: string[];
  metadata: Record<string, any>;
}

/**
 * Trace based on OpenTelemetry span
 */
export interface Trace {
  traceId: string;
  spanId: string;
  parentSpanId: string | null;
  name: string;
  startTime: Date;
  endTime: Date;
  durationNs: number;
  statusCode: 'UNSET' | 'OK' | 'ERROR';
  statusMessage: string;
  attributes: Record<string, any>;
  resourceAttributes: Record<string, any>;
  events: TraceEvent[];
  projectId: string;
}

/**
 * Event within a trace
 */
export interface TraceEvent {
  name: string;
  timestamp: Date;
  attributes: Record<string, any>;
}

/**
 * Session log based on OpenTelemetry log record
 */
export interface SessionLog {
  timestamp: Date;
  traceId: string | null;
  spanId: string | null;
  severityText: string;
  severityNumber: number;
  body: string | Record<string, any>;
  attributes: Record<string, any>;
  resourceAttributes: Record<string, any>;
}

/**
 * Session metric based on OpenTelemetry metric
 */
export interface SessionMetric {
  timestamp: Date;
  name: string;
  description: string;
  unit: string;
  dataType: 'GAUGE' | 'SUM' | 'HISTOGRAM' | 'EXPONENTIAL_HISTOGRAM' | 'SUMMARY';
  value: number | Record<string, any>;
  attributes: Record<string, any>;
  resourceAttributes: Record<string, any>;
}

/**
 * Session statistics
 */
export interface SessionStats {
  sessionId: string;
  projectId: string;
  startTime: Date;
  endTime: Date | null;
  durationMs: number;
  endState: string;
  traceCount: number;
  logCount: number;
  metricCount: number;
  errorCount: number;
}

/**
 * OpenTelemetry severity numbers
 * Based on https://opentelemetry.io/docs/specs/otel/logs/data-model/#field-severitynumber
 */
export enum SeverityNumber {
  UNSPECIFIED = 0,
  TRACE = 1,
  TRACE2 = 2,
  TRACE3 = 3,
  TRACE4 = 4,
  DEBUG = 5,
  DEBUG2 = 6,
  DEBUG3 = 7,
  DEBUG4 = 8,
  INFO = 9,
  INFO2 = 10,
  INFO3 = 11,
  INFO4 = 12,
  WARN = 13,
  WARN2 = 14,
  WARN3 = 15,
  WARN4 = 16,
  ERROR = 17,
  ERROR2 = 18,
  ERROR3 = 19,
  ERROR4 = 20,
  FATAL = 21,
  FATAL2 = 22,
  FATAL3 = 23,
  FATAL4 = 24,
}

/**
 * OpenTelemetry severity text values
 * Based on https://opentelemetry.io/docs/specs/otel/logs/data-model/#field-severitytext
 */
export enum SeverityText {
  TRACE = 'TRACE',
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
  FATAL = 'FATAL',
}

/**
 * OpenTelemetry span status codes
 * Based on https://opentelemetry.io/docs/specs/otel/trace/api/#set-status
 */
export enum SpanStatusCode {
  UNSET = 'UNSET',
  OK = 'OK',
  ERROR = 'ERROR',
}

/**
 * OpenTelemetry metric data types
 * Based on https://opentelemetry.io/docs/specs/otel/metrics/data-model/
 */
export enum MetricDataType {
  GAUGE = 'GAUGE',
  SUM = 'SUM',
  HISTOGRAM = 'HISTOGRAM',
  EXPONENTIAL_HISTOGRAM = 'EXPONENTIAL_HISTOGRAM',
  SUMMARY = 'SUMMARY',
}

export interface ProjectMetrics {
  project_id: string;
  trace_count: number;
  span_count: {
    total: number;
    success: number;
    fail: number;
    unknown: number;
    indeterminate: number;
  };
  token_metrics: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: {
      all: number;
      success: number;
      fail: number;
    };
    total_cost: number | string;
    average_cost_per_session: string;
    avg_tokens: {
      all: string;
      success: string;
      fail: string;
    };
    by_model?: Record<string, number>;
    by_system?: {
      llm: number;
      [key: string]: number;
    };
  };
  duration_metrics: {
    min_duration_ns: number;
    max_duration_ns: number;
    avg_duration_ns: number;
    total_duration_ns: number;
  };
  success_datetime?: string[];
  fail_datetime?: string[];
  indeterminate_datetime?: string[];
  spans_per_trace?: Record<string, number>[];
  failed_traces_dates?: Record<string, number>[];
  trace_cost_dates?: Record<string, number>[];
  trace_durations?: number[];
  freeplan_truncated?: boolean;
}

export interface TraceMetrics {
  trace_id: string;
  token_metrics: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    total_cost: number;
    by_model: Record<string, number>;
    by_system: {
      llm: number;
      [key: string]: number;
    };
  };
  start_time: string;
  end_time: string;
  total_duration_ns: number;
}
