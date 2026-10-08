CREATE TABLE IF NOT EXISTS predictions (
    event_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    model_version TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    probability DOUBLE PRECISION NOT NULL CHECK (probability >= 0 AND probability <= 1),
    horizon_seconds DOUBLE PRECISION NOT NULL CHECK (horizon_seconds > 0),
    target JSONB NOT NULL,
    evidence_refs JSONB NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_entity_time
    ON predictions (entity_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS prediction_scores (
    event_id TEXT PRIMARY KEY REFERENCES predictions(event_id),
    outcome SMALLINT NOT NULL CHECK (outcome IN (0,1)),
    brier_loss DOUBLE PRECISION NOT NULL CHECK (brier_loss >= 0),
    log_loss DOUBLE PRECISION NOT NULL CHECK (log_loss >= 0),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
