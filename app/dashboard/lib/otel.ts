import { useState, useEffect } from 'react';

type QueryType = 'traces' | 'logs' | 'metrics';

interface UseOtelDataProps {
  queryType: QueryType;
  params: any;
  enabled?: boolean;
}

export function useOtelData<T>({ queryType, params, enabled = true }: UseOtelDataProps) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/clickhouse', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            queryType,
            params,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to fetch data');
        }

        const result = await response.json();
        setData(result.data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [queryType, JSON.stringify(params), enabled]);

  return { data, isLoading, error };
}

// Types for trace data
export interface Trace {
  trace_id: string;
  service_name: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  status_code: string;
  // Add other fields as needed
}

export interface Span {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  name: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  service_name: string;
  status_code: string;
  attributes: Record<string, any>;
  events: Array<{
    name: string;
    timestamp: string;
    attributes: Record<string, any>;
  }>;
  // Add other fields as needed
}

export interface TraceQueryParams {
  project_id?: string;
  start_time?: string;
  end_time?: string;
  service_name?: string;
  span_name?: string;
  status_code?: string;
  limit?: number;
  offset?: number;
  // Add other query parameters as needed
}

export interface TraceSearchParams extends TraceQueryParams {
  query?: string;
  // Add other search-specific parameters
}
