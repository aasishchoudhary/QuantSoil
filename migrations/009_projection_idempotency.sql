-- Deterministic idempotency boundary for spatial projections.
CREATE UNIQUE INDEX IF NOT EXISTS uq_map_features_source_record_hash
    ON map_features (source, source_record_id, raw_payload_hash);
