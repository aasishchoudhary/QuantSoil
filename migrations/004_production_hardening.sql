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
    assertion_id UUID PRIMARY KEY,
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
