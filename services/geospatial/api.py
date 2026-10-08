"""Evidence-aware map API contract.

The map is a spatial projection of source observations. Every returned feature
must retain enough provenance to trace it back to its source assertion.
The default repository is in-memory so contract tests do not require PostGIS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query, Response
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]


@dataclass(frozen=True)
class MapFeature:
    feature_id: str
    feature_type: str
    source: str
    source_record_id: str
    geometry: dict[str, Any]
    properties: dict[str, Any]
    observation_id: str | None = None
    confidence: float | None = None
    observed_at: datetime | None = None
    raw_payload_hash: str | None = None
    parser_version: str | None = None
    license_class: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def to_geojson(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.feature_id,
            "geometry": self.geometry,
            "properties": {
                "feature_type": self.feature_type,
                "source": self.source,
                "source_record_id": self.source_record_id,
                "observation_id": self.observation_id,
                "confidence": self.confidence,
                "observed_at": self.observed_at.isoformat() if self.observed_at else None,
                "raw_payload_hash": self.raw_payload_hash,
                "parser_version": self.parser_version,
                "license_class": self.license_class,
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

        def bbox_candidate(feature: MapFeature) -> bool:
            coords = _coordinates(feature.geometry)
            if not coords:
                return False
            lons = [point[0] for point in coords]
            lats = [point[1] for point in coords]
            return not (
                max(lons) < min_lon
                or min(lons) > max_lon
                or max(lats) < min_lat
                or min(lats) > max_lat
            )

        result: list[MapFeature] = []
        for feature in self._features:
            if visible(feature) and bbox_candidate(feature):
                result.append(feature)
            if len(result) >= limit:
                break
        return result


def _coordinates(geometry: dict[str, Any]) -> list[list[float]]:
    """Flatten GeoJSON coordinates into [lon, lat] points.

    This is a conservative in-memory bbox candidate test. PostGIS remains the
    production spatial execution path and should perform authoritative geometry
    operations.
    """
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        return []

    points: list[list[float]] = []

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                points.append([float(value[0]), float(value[1])])
                return
            for item in value:
                walk(item)

    walk(coordinates)
    return points


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise ValueError("bbox must contain four numeric coordinates") from exc
    if len(parts) != 4:
        raise ValueError("bbox must contain four coordinates")
    min_lon, min_lat, max_lon, max_lat = parts
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("longitude outside WGS84 bounds")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("latitude outside WGS84 bounds")
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError("bbox minimum must not exceed maximum")
    return min_lon, min_lat, max_lon, max_lat


def create_app(repository: InMemoryMapRepository | None = None):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the map API")
    repo = repository or InMemoryMapRepository()
    app = FastAPI(title="God's Eye World Intelligence — Map API", version="0.2.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/tiles/{z}/{x}/{y}.pbf")
    def tile(z: int, x: int, y: int, at: datetime | None = Query(default=None)):
        tile_fn = getattr(repo, "tile", None)
        if tile_fn is None:
            raise HTTPException(status_code=501, detail="vector tiles require the PostGIS repository")
        if at is not None and at.tzinfo is None:
            raise HTTPException(status_code=400, detail="at must include a timezone offset")
        try:
            payload = tile_fn(z, x, y, at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return Response(content=payload, media_type="application/vnd.mapbox-vector-tile")

    @app.get("/features")
    def features(
        bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
        at: datetime | None = Query(default=None),
        limit: int = Query(default=500, ge=1, le=5000),
    ) -> dict[str, Any]:
        try:
            min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if at is not None and at.tzinfo is None:
            raise HTTPException(status_code=400, detail="at must include a timezone offset")

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
