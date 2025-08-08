export interface UsageCostBreakdown {
  usage_type: string;
  quantity: number;
  cost_cents: number;
}

export interface BillingPeriod {
  id: string;
  period_start: string;
  period_end: string;
  seat_cost: number;
  seat_count: number;
  usage_costs: Record<string, number>;
  usage_quantities: Record<string, number>;
  usage_breakdown: UsageCostBreakdown[];
  total_cost: number;
  status: 'current' | 'pending' | 'invoiced' | 'paid';
}

export interface ProjectUsageBreakdown {
  project_id: string;
  project_name: string;
  tokens: number;
  spans: number;
  token_cost: number; // in cents
  span_cost: number; // in cents
  total_cost: number; // in cents
}

export interface BillingDashboard {
  current_period: BillingPeriod | null;
  past_periods: BillingPeriod[];
  total_spent_all_time: number;
  is_legacy_billing: boolean;
  legacy_cancellation_date: string | null;
  project_breakdown?: ProjectUsageBreakdown[];
}

export type BillingDashboardResponse = BillingDashboard;
