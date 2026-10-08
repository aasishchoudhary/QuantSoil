CREATE TABLE IF NOT EXISTS derived_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    evidence_refs JSONB NOT NULL,
    payload JSONB NOT NULL,
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(evidence_refs) = 'array'),
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE INDEX IF NOT EXISTS idx_derived_events_type_time
    ON derived_events (event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_derived_events_evidence
    ON derived_events USING GIN (evidence_refs);
