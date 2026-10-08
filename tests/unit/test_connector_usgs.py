from datetime import datetime, timezone
from packages.connectors.usgs import USGSEarthquakeConnector

def test_usgs_parses_feature_and_preserves_source_identity():
    observed_ms = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    document = {
        "type": "FeatureCollection",
        "metadata": {"generated": observed_ms + 1000},
        "features": [{
            "type": "Feature",
            "id": "us123",
            "properties": {"time": observed_ms, "mag": 4.2},
            "geometry": {"type": "Point", "coordinates": [86.9, 25.2, 10]},
        }],
    }
    records = list(USGSEarthquakeConnector(fetcher=lambda url: document).fetch())
    assert len(records) == 1
    assert records[0].source_record_id == "us123"
    assert records[0].observed_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert records[0].payload["feature"]["id"] == "us123"
