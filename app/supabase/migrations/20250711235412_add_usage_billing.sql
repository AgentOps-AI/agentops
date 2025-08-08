-- Track usage during billing periods
CREATE TABLE public.org_usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES public.orgs(id) ON DELETE CASCADE,
    usage_type VARCHAR(50) NOT NULL, -- 'tokens', 'spans', future: 'storage', etc.
    quantity BIGINT NOT NULL DEFAULT 0,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, usage_type, period_start)
);

-- Billing period snapshots for dashboard
CREATE TABLE public.billing_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES public.orgs(id) ON DELETE CASCADE,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    stripe_invoice_id VARCHAR(255),
    
    -- Costs breakdown (stored as cents)
    seat_cost INTEGER NOT NULL DEFAULT 0,
    seat_count INTEGER NOT NULL DEFAULT 0,
    
    -- Usage costs (JSON for extensibility)
    usage_costs JSONB NOT NULL DEFAULT '{}', -- {"tokens": 1500, "spans": 2000}
    usage_quantities JSONB NOT NULL DEFAULT '{}', -- {"tokens": 5000000, "spans": 125000}
    
    total_cost INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'invoiced', 'paid'
    invoiced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(org_id, period_start)
);

-- Indexes for performance
CREATE INDEX idx_billing_periods_org ON public.billing_periods(org_id, period_end DESC);
CREATE INDEX idx_usage_tracking_rollup ON public.org_usage_tracking(org_id, period_end, usage_type);

-- RLS policies
ALTER TABLE public.org_usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_periods ENABLE ROW LEVEL SECURITY;

-- Only org members can view their usage
CREATE POLICY "Org members can view usage" ON public.org_usage_tracking
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.user_orgs uo
            WHERE uo.org_id = org_usage_tracking.org_id
            AND uo.user_id = auth.uid()
        )
    );

CREATE POLICY "Org members can view billing periods" ON public.billing_periods
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.user_orgs uo
            WHERE uo.org_id = billing_periods.org_id
            AND uo.user_id = auth.uid()
        )
    ); 