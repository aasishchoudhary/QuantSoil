CREATE OR REPLACE FUNCTION map_features_mvt(
    z INTEGER,
    x INTEGER,
    y INTEGER,
    at_time TIMESTAMPTZ DEFAULT NULL
)
RETURNS BYTEA
LANGUAGE SQL
STABLE
AS $$
WITH bounds AS (
    SELECT ST_TileEnvelope(z, x, y) AS geom
),
features AS (
    SELECT
        mf.feature_id::text AS id,
        mf.feature_type,
        mf.source,
        mf.source_record_id,
        mf.observation_id::text,
        mf.confidence,
        mf.observed_at,
        mf.raw_payload_hash,
        mf.parser_version,
        mf.license_class,
        ST_AsMVTGeom(
            ST_Transform(mf.geometry, 3857),
            bounds.geom,
            4096,
            64,
            true
        ) AS geom
    FROM map_features mf, bounds
    WHERE mf.geometry && ST_Transform(bounds.geom, 4326)
      AND (
        at_time IS NULL OR (
          (mf.valid_from IS NULL OR mf.valid_from <= at_time)
          AND (mf.valid_to IS NULL OR at_time < mf.valid_to)
        )
      )
)
SELECT ST_AsMVT(features, 'world', 4096, 'geom') FROM features;
$$;
