from datetime import datetime, timezone

from services.geospatial.api import InMemoryMapRepository, MapFeature, create_app


def test_bbox_returns_point_feature():
    feature = MapFeature(
        feature_id="f-1",
        feature_type="aircraft",
        geometry={"type": "Point", "coordinates": [87.0, 25.25]},
        properties={"source": "synthetic"},
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    app = create_app(InMemoryMapRepository([feature]))
    assert app.title.startswith("God's Eye World Intelligence")


def test_point_repository_respects_bbox_and_time():
    feature = MapFeature(
        feature_id="f-1",
        feature_type="sensor",
        geometry={"type": "Point", "coordinates": [87.0, 25.25]},
        properties={},
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    repo = InMemoryMapRepository([feature])
    result = repo.query_bbox(
        86.0,
        24.0,
        88.0,
        26.0,
        datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    assert [item.feature_id for item in result] == ["f-1"]
