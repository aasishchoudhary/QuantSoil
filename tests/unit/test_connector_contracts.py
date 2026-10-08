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
