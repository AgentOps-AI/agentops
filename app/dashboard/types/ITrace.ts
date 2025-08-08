export interface ITrace {
  trace_id: string;
  root_service_name: string;
  root_span_name: string;
  start_time: string;
  end_time: string;
  duration: number;
  span_count: number;
  error_count: number;
  tags?: string[];
  freeplan_truncated?: boolean;
  total_cost?: number;
}
