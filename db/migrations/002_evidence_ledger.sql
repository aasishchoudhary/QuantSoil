-- Evidence ledger data plane.
-- PostgreSQL 16+. Raw payload bytes should be retained in immutable object
-- storage; this table stores the content identity and provenance index.

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    acquired_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL,
    raw_payload_hash CHAR(64) NOT NULL,
    parser_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    license_class TEXT NOT NULL,
    payload_uri TEXT,
    payload_size_bytes BIGINT CHECK (payload_size_bytes IS NULL OR payload_size_bytes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_record_id, raw_payload_hash)
);

CREATE INDEX IF NOT EXISTS idx_evidence_source_record
    ON evidence_records (source, source_record_id);

CREATE INDEX IF NOT EXISTS idx_evidence_observed_at
    ON evidence_records (observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_hash
    ON evidence_records (raw_payload_hash);

COMMENT ON TABLE evidence_records IS
    'Immutable provenance index for source evidence. Raw payload bytes are retained separately.';
