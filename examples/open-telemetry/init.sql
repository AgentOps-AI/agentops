-- Development database schema
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    name TEXT NOT NULL,
    attributes JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_events_trace_id ON events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_organization_id ON events(organization_id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Basic RLS policies
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Cast organization_id from JWT claims to UUID
CREATE POLICY events_org_isolation ON events
    FOR ALL
    USING (organization_id = (current_setting('request.jwt.claims')::json->>'organization_id')::UUID); 