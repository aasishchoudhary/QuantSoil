from datetime import datetime, timezone

from services.geospatial.postgis import PostGISMapRepository


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query, params):
        self.executed = (query, params)

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def cursor(self):
        return self.cursor_instance


def test_postgis_repository_maps_rows_and_preserves_provenance():
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    connection = FakeConnection([
        (
            "f-1", "aircraft", "synthetic", "record-1", "obs-1",
            '{"type":"Point","coordinates":[87,25]}', '{"platform":"test"}',
            0.9, observed, "a" * 64, "parser-1", "synthetic", observed, None,
        )
    ])
    repository = PostGISMapRepository(connection)
    result = repository.query_bbox(86, 24, 88, 26, observed, 50)

    assert len(result) == 1
    assert result[0].source == "synthetic"
    assert result[0].observation_id == "obs-1"
    assert result[0].raw_payload_hash == "a" * 64
    assert result[0].parser_version == "parser-1"
    assert result[0].license_class == "synthetic"
    assert result[0].geometry["coordinates"] == [87, 25]
    assert connection.cursor_instance.executed[1][-1] == 50
