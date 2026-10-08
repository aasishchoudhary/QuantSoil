"""PostgreSQL projection of accepted GeoJSON observations into analyst world state."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


class PostgresObservationProjectionRepository:
    """Project accepted GeoJSON Feature observations into temporal analyst state."""

    def __init__(self, connection) -> None:
        self._connection = connection

    def project(self, *, observation, evidence) -> bool:
        payload = observation.payload
        feature = payload.get("feature") if isinstance(payload, dict) else None
        if not isinstance(feature, dict):
            return False
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or not geometry.get("type"):
            return False
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        entity_id = f"{observation.source}:{observation.source_record_id}"
        entity_type = str(
            properties.get("eventtype")
            or properties.get("event")
            or properties.get("category")
            or observation.source
        )[:256]
        state_id = hashlib.sha256(
            f"{entity_id}:{observation.observed_at.isoformat()}:{observation.provenance.raw_payload_hash}".encode()
        ).hexdigest()
        evidence_ref = evidence.evidence_id
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """SELECT valid_from FROM entity_state
                       WHERE entity_id=%s AND valid_to IS NULL
                       ORDER BY valid_from DESC LIMIT 1""",
                    (entity_id,),
                )
                current = cursor.fetchone()
                if current is not None and observation.observed_at <= current[0]:
                    return False
                if current is not None:
                    cursor.execute(
                        """UPDATE entity_state SET valid_to=%s
                           WHERE entity_id=%s AND valid_to IS NULL AND valid_from < %s""",
                        (observation.observed_at, entity_id, observation.observed_at),
                    )
                cursor.execute(
                    """INSERT INTO entity_state (
                         state_id, entity_id, entity_type, valid_from, valid_to,
                         observed_at, recorded_at, properties, geometry, confidence, evidence_refs
                       ) VALUES (%s,%s,%s,%s,NULL,%s,%s,%s,%s,NULL,%s)
                       ON CONFLICT (state_id) DO NOTHING""",
                    (
                        state_id, entity_id, entity_type, observation.observed_at,
                        observation.observed_at, observation.ingested_at,
                        json.dumps(properties), json.dumps(geometry),
                        json.dumps([evidence_ref]),
                    ),
                )
                cursor.execute(
                    """INSERT INTO map_features (
                         feature_type, source, source_record_id, observation_id,
                         geometry, properties, confidence, observed_at,
                         raw_payload_hash, parser_version, license_class
                       ) VALUES (%s,%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),
                                 %s,NULL,%s,%s,%s,%s)
                       ON CONFLICT (source, source_record_id, raw_payload_hash) DO NOTHING""",
                    (
                        entity_type, observation.source, observation.source_record_id,
                        observation.observation_id, json.dumps(geometry),
                        json.dumps(properties), observation.observed_at,
                        observation.provenance.raw_payload_hash,
                        evidence.parser_version, evidence.license_class,
                    ),
                )
            self._connection.commit()
        except Exception:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise
        return True
