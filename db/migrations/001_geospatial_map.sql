-- Geospatial map data plane.
-- PostgreSQL 16+ / PostGIS 3.x.
-- Observations remain the authoritative evidence boundary; map_features are
-- spatial projections that retain provenance references.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS map_features (
    feature_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_type TEXT NOT NULL,
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    observation_id UUID,
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
    observed_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    raw_payload_hash CHAR(64) NOT NULL,
    parser_version TEXT NOT NULL,
    license_class TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_map_features_geometry
    ON map_features USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_map_features_observed_at
    ON map_features (observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_map_features_source
    ON map_features (source);

CREATE INDEX IF NOT EXISTS idx_map_features_type
    ON map_features (feature_type);

CREATE INDEX IF NOT EXISTS idx_map_features_properties
    ON map_features USING GIN (properties);

COMMENT ON TABLE map_features IS
    'Spatial projection for map rendering. It is not a replacement for immutable evidence.';

CREATE OR REPLACE FUNCTION map_features_in_bbox(
    min_lon DOUBLE PRECISION,
    min_lat DOUBLE PRECISION,
    max_lon DOUBLE PRECISION,
    max_lat DOUBLE PRECISION,
    at_time TIMESTAMPTZ DEFAULT NULL,
    result_limit INTEGER DEFAULT 500
)
RETURNS TABLE (
    feature_id UUID,
    feature_type TEXT,
    source TEXT,
    source_record_id TEXT,
    observation_id UUID,
    geometry JSONB,
    properties JSONB,
    confidence DOUBLE PRECISION,
    observed_at TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        mf.feature_id,
        mf.feature_type,
        mf.source,
        mf.source_record_id,
        mf.observation_id,
        ST_AsGeoJSON(mf.geometry)::jsonb,
        mf.properties,
        mf.confidence,
        mf.observed_at,
        mf.raw_payload_hash,
        mf.parser_version,
        mf.license_class,
        mf.valid_from,
        mf.valid_to
    FROM map_features mf
    WHERE mf.geometry && ST_MakeEnvelope(
        min_lon, min_lat, max_lon, max_lat, 4326
    )
    AND (
        at_time IS NULL
        OR (
            (mf.valid_from IS NULL OR mf.valid_from <= at_time)
            AND (mf.valid_to IS NULL OR at_time < mf.valid_to)
        )
    )
    ORDER BY mf.observed_at DESC
    LIMIT GREATEST(result_limit, 1);
$$;
