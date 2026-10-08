CREATE TABLE IF NOT EXISTS entity_state (
    state_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    observed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    geometry JSONB,
    confidence DOUBLE PRECISION,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (recorded_at >= observed_at),
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE INDEX IF NOT EXISTS idx_entity_state_entity_time
    ON entity_state (entity_id, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_entity_state_observed_at
    ON entity_state (observed_at);

CREATE INDEX IF NOT EXISTS idx_entity_state_properties
    ON entity_state USING GIN (properties);
