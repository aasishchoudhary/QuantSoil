"""PostGIS-backed map repository.

The repository depends only on the Python DB-API connection contract; the
application can inject psycopg or another compatible PostgreSQL driver without
coupling the domain contract to a specific driver.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from .api import MapFeature


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...
    def __enter__(self) -> "Cursor": ...
    def __exit__(self, *args: Any) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...


class PostGISMapRepository:
    """Production repository using the map_features_in_bbox SQL function."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def query_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        at: datetime | None = None,
        limit: int = 500,
    ) -> list[MapFeature]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT feature_id, feature_type, source, source_record_id,
                       observation_id, geometry, properties, confidence,
                       observed_at, raw_payload_hash, parser_version,
                       license_class, valid_from, valid_to
                FROM map_features_in_bbox(%s, %s, %s, %s, %s, %s)
                """,
                (min_lon, min_lat, max_lon, max_lat, at, limit),
            )
            rows = cursor.fetchall()

        return [self._row_to_feature(row) for row in rows]

    @staticmethod
    def _row_to_feature(row: tuple[Any, ...]) -> MapFeature:
        (
            feature_id,
            feature_type,
            source,
            source_record_id,
            observation_id,
            geometry,
            properties,
            confidence,
            observed_at,
            raw_payload_hash,
            parser_version,
            license_class,
            valid_from,
            valid_to,
        ) = row
        if isinstance(geometry, str):
            geometry = json.loads(geometry)
        if isinstance(properties, str):
            properties = json.loads(properties)
        return MapFeature(
            feature_id=str(feature_id),
            feature_type=feature_type,
            source=source,
            source_record_id=source_record_id,
            geometry=geometry,
            properties=properties,
            observation_id=str(observation_id) if observation_id is not None else None,
            confidence=confidence,
            observed_at=observed_at,
            raw_payload_hash=raw_payload_hash,
            parser_version=parser_version,
            license_class=license_class,
            valid_from=valid_from,
            valid_to=valid_to,
        )
