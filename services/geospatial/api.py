"""Minimal map API contract.

The production deployment should inject a PostGIS-backed repository implementation.
The default repository is deliberately in-memory so contract tests can run without
external infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from fastapi import FastAPI, Query
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]


@dataclass(frozen=True)
class MapFeature:
    feature_id: str
    feature_type: str
    geometry: dict[str, Any]
    properties: dict[str, Any]
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def to_geojson(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.feature_id,
            "geometry": self.geometry,
            "properties": {
                "feature_type": self.feature_type,
                **self.properties,
                "valid_from": self.valid_from.isoformat() if self.valid_from else None,
                "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            },
        }


class InMemoryMapRepository:
    def __init__(self, features: list[MapFeature] | None = None) -> None:
        self._features = features or []

    def query_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        at: datetime | None = None,
        limit: int = 500,
    ) -> list[MapFeature]:
        def visible(feature: MapFeature) -> bool:
            if at is None:
                return True
            return (
                (feature.valid_from is None or feature.valid_from <= at)
                and (feature.valid_to is None or at < feature.valid_to)
            )

        result: list[MapFeature] = []
        for feature in self._features:
            if not visible(feature):
                continue
            geometry = feature.geometry
            if geometry.get("type") != "Point":
                result.append(feature)
                continue
            lon, lat = geometry["coordinates"]
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                result.append(feature)
            if len(result) >= limit:
                break
        return result


def create_app(repository: InMemoryMapRepository | None = None):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the map API")
    repo = repository or InMemoryMapRepository()
    app = FastAPI(title="God's Eye World Intelligence — Map API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/map/features")
    def features(
        bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
        at: datetime | None = Query(default=None),
        limit: int = Query(default=500, ge=1, le=5000),
    ) -> dict[str, Any]:
        parts = [float(value.strip()) for value in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must contain four coordinates")
        min_lon, min_lat, max_lon, max_lat = parts
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("longitude outside WGS84 bounds")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("latitude outside WGS84 bounds")
        if min_lon > max_lon or min_lat > max_lat:
            raise ValueError("bbox minimum must not exceed maximum")

        result = repo.query_bbox(min_lon, min_lat, max_lon, max_lat, at, limit)
        return {
            "type": "FeatureCollection",
            "features": [feature.to_geojson() for feature in result],
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(result),
                "limit": limit,
            },
        }

    return app


app = create_app() if FastAPI is not None else None
