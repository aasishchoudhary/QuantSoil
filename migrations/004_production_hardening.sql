-- Production hardening for temporal state and contradiction evidence.
-- Existing 003 remains backward compatible; this migration adds database-enforced
-- non-overlap and persistent assertions/source health.
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE entity_state
    ADD COLUMN IF NOT EXISTS valid_range TSTZRANGE
    GENERATED ALWAYS AS (tstzrange(valid_from, valid_to, '[)')) STORED;

CREATE INDEX IF NOT EXISTS idx_entity_state_valid_range
    ON entity_state USING GIST (valid_range);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'entity_state_no_overlap'
    ) THEN
        ALTER TABLE entity_state
            ADD CONSTRAINT entity_state_no_overlap
            EXCLUDE USING GIST (entity_id WITH =, valid_range WITH &&);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS assertions (
    assertion_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    property_name TEXT NOT NULL,
    value JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    source_weight DOUBLE PRECISION NOT NULL CHECK (source_weight >= 0 AND source_weight <= 1),
    evidence_refs JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(evidence_refs) = 'array'),
    CHECK (jsonb_array_length(evidence_refs) > 0)
);

CREATE INDEX IF NOT EXISTS idx_assertions_entity_property
    ON assertions (entity_id, property_name, assertion_id);

CREATE INDEX IF NOT EXISTS idx_assertions_evidence_refs
    ON assertions USING GIN (evidence_refs);

CREATE TABLE IF NOT EXISTS source_health (
    source TEXT PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
        CHECK (consecutive_failures >= 0),
    CHECK (recorded_at >= observed_at)
);


-- Connector execution audit: immutable run summaries and rejected-record reasons.
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    records_seen INTEGER NOT NULL CHECK (records_seen >= 0),
    records_accepted INTEGER NOT NULL CHECK (records_accepted >= 0),
    records_rejected INTEGER NOT NULL CHECK (records_rejected >= 0),
    attempts INTEGER NOT NULL CHECK (attempts >= 1),
    error_type TEXT,
    CHECK (finished_at >= started_at),
    CHECK (records_accepted + records_rejected <= records_seen)
);

CREATE TABLE IF NOT EXISTS rejected_records (
    rejection_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    raw_payload_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('stale','invalid','duplicate')),
    reasons JSONB NOT NULL CHECK (jsonb_typeof(reasons) = 'array'),
    observed_at TIMESTAMPTZ NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_rejected_records_run ON rejected_records(run_id);
CREATE INDEX IF NOT EXISTS idx_rejected_records_source_record ON rejected_records(source, source_record_id);

ALTER TABLE rejected_records ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}'::jsonb;


-- Runtime job queue. Claims use row-level leases so multiple workers can
-- consume safely without requiring an external broker for the first deployment.
CREATE TABLE IF NOT EXISTS runtime_jobs (
    job_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','retry','failed')),
    lease_until TIMESTAMPTZ,
    last_error_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((status = 'running') = (lease_until IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_runtime_jobs_claim
    ON runtime_jobs (status, scheduled_at, job_id);

CREATE INDEX IF NOT EXISTS idx_runtime_jobs_lease
    ON runtime_jobs (lease_until)
    WHERE status = 'running';
