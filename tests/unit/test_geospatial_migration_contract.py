from pathlib import Path


SQL = Path("db/migrations/001_geospatial_map.sql").read_text()


def test_map_bbox_function_returns_all_repository_columns():
    start = SQL.index("RETURNS TABLE (")
    end = SQL.index(")\nLANGUAGE SQL", start)
    returned = SQL[start:end]

    for column in (
        "feature_id UUID",
        "feature_type TEXT",
        "source TEXT",
        "source_record_id TEXT",
        "observation_id UUID",
        "geometry JSONB",
        "properties JSONB",
        "confidence DOUBLE PRECISION",
        "observed_at TIMESTAMPTZ",
        "raw_payload_hash CHAR(64)",
        "parser_version TEXT",
        "license_class TEXT",
        "valid_from TIMESTAMPTZ",
        "valid_to TIMESTAMPTZ",
    ):
        assert column in returned
