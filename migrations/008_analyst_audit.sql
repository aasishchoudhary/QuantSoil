CREATE TABLE IF NOT EXISTS analyst_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at TIMESTAMPTZ NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL CHECK (status_code >= 100 AND status_code <= 599),
    correlation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyst_audit_time
    ON analyst_audit (occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_analyst_audit_path_time
    ON analyst_audit (path, occurred_at DESC);
