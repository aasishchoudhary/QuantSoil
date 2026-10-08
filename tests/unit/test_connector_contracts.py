from datetime import datetime, timezone
from packages.connectors.contracts import ConnectorError, SourceRecord, SourceSpec
from packages.connectors.registry import SourceRegistry

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def spec(name="synthetic"):
    return SourceSpec(name, "synthetic", "v1", "parser-v1", 300)

def test_registry_rejects_unknown_source():
    registry = SourceRegistry()
    try:
        registry.get("missing")
        assert False
    except ConnectorError:
        pass

def test_registry_is_idempotent_for_same_spec():
    registry = SourceRegistry()
    registry.register(spec())
    registry.register(spec())
    assert registry.get("synthetic") == spec()

def test_source_record_requires_valid_temporal_metadata():
    record = SourceRecord("r1", {"x": 1}, T, T)
    assert record.acquired_at == T

def test_source_record_rejects_bad_time_order():
    try:
        SourceRecord("r1", {"x": 1}, T, T.replace(year=2025))
        assert False
    except ConnectorError:
        pass

from packages.connectors.contracts import USGSEarthquakeConnector

def test_usgs_connector_normalizes_geojson_event():
    document = {
        "type": "FeatureCollection",
        "metadata": {"generated": 1770000000000},
        "features": [{
            "type": "Feature",
            "id": "us123",
            "properties": {"time": 1769999999000, "mag": 4.2},
            "geometry": {"type": "Point", "coordinates": [85.0, 25.0, 10.0]}
        }]
    }
    records = list(USGSEarthquakeConnector(fetcher=lambda _: document).fetch())
    assert len(records) == 1
    assert records[0].source_record_id == "us123"
    assert records[0].payload["feature"]["geometry"]["coordinates"][0] == 85.0
