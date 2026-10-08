"""PostGIS repository adapter for evidence-aware map projections."""
from __future__ import annotations

from typing import Any

from services.geospatial.api import MapFeature
from packages.repositories.db import connection_scope


_QUERY = """SELECT feature_id, feature_type, source, source_record_id,
    observation_id, geometry, properties, confidence, observed_at,
    raw_payload_hash, parser_version, license_class, valid_from, valid_to
    FROM map_features_in_bbox(%s,%s,%s,%s,%s,%s)"""
_TILE = "SELECT map_features_mvt(%s,%s,%s,%s)"


class MapRepositoryError(RuntimeError):
    pass


class PostgresMapRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def query_bbox(self, min_lon, min_lat, max_lon, max_lat, at=None, limit=500):
        try:
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        _QUERY,
                        (min_lon, min_lat, max_lon, max_lat, at, limit),
                    )
                    rows = cursor.fetchall()
        except Exception as exc:
            raise MapRepositoryError("failed to query spatial projection") from exc
        return tuple(self._row(row) for row in rows)

    def tile(self, z: int, x: int, y: int, at=None) -> bytes:
        if not (0 <= z <= 24):
            raise ValueError("zoom outside supported range")
        max_tile = 2**z
        if not (0 <= x < max_tile and 0 <= y < max_tile):
            raise ValueError("tile coordinate outside zoom bounds")
        try:
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_TILE, (z, x, y, at))
                    row = cursor.fetchone()
        except Exception as exc:
            raise MapRepositoryError("failed to query vector tile") from exc
        return bytes(row[0] or b"") if row else b""

    @staticmethod
    def _row(row):
        return MapFeature(
            feature_id=str(row[0]), feature_type=str(row[1]), source=str(row[2]),
            source_record_id=str(row[3]), geometry=row[5] or {}, properties=row[6] or {},
            observation_id=str(row[4]) if row[4] else None, confidence=row[7],
            observed_at=row[8], raw_payload_hash=str(row[9]) if row[9] else None,
            parser_version=str(row[10]) if row[10] else None,
            license_class=str(row[11]) if row[11] else None,
            valid_from=row[12], valid_to=row[13],
        )
