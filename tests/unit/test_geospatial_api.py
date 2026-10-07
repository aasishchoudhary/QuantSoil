from datetime import datetime, timezone

import pytest

from services.geospatial.api import InMemoryMapRepository, MapFeature, _parse_bbox, create_app


def _feature(**overrides):
    values = {
        "feature_id": "f-1",
        "feature_type": "aircraft",
        "source": "synthetic",
        "source_record_id": "record-1",
        "geometry": {"type": "Point", "coordinates": [87.0, 25.25]},
        "properties": {"platform": "test"},
        "observation_id": "obs-1",
        "confidence": 0.95,
        "observed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "raw_payload_hash": "a" * 64,
        "parser_version": "test-1",
        "license_class": "synthetic",
        **overrides,
    }
    return MapFeature(**values)


def test_bbox_returns_point_feature():
    app = create_app(InMemoryMapRepository([_feature()]))
    assert app.title.startswith("God's Eye World Intelligence")


def test_point_repository_respects_bbox_and_time():
    repo = InMemoryMapRepository([_feature()])
    result = repo.query_bbox(
        86.0, 24.0, 88.0, 26.0,
        datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    assert [item.feature_id for item in result] == ["f-1"]


def test_repository_filters_non_point_geometry_by_bbox():
    feature = _feature(
        feature_id="line-1",
        geometry={"type": "LineString", "coordinates": [[87.0, 25.0], [88.0, 25.0]]},
    )
    repo = InMemoryMapRepository([feature])
    assert repo.query_bbox(86.0, 24.0, 86.5, 24.5) == []


def test_geojson_preserves_provenance():
    feature = _feature()
    output = feature.to_geojson()
    assert output["properties"]["source"] == "synthetic"
    assert output["properties"]["source_record_id"] == "record-1"
    assert output["properties"]["observation_id"] == "obs-1"
    assert output["properties"]["raw_payload_hash"] == "a" * 64
    assert output["properties"]["parser_version"] == "test-1"
    assert output["properties"]["license_class"] == "synthetic"


@pytest.mark.parametrize(
    "value",
    ["1,2,3", "x,2,3,4", "181,2,3,4", "1,-91,3,4", "4,2,3,4"],
)
def test_parse_bbox_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _parse_bbox(value)
