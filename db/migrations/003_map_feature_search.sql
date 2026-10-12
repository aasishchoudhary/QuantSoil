-- Trigram index for bounded, case-insensitive global search over map metadata.
-- Search remains a read-only projection query; source evidence is not modified.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_map_features_global_search
ON map_features USING GIN (
    lower(concat_ws(' ', feature_type, source, source_record_id, properties::text)) gin_trgm_ops
);
