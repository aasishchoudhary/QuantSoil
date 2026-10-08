from datetime import datetime, timezone
import uuid

from packages.contracts.evidence import EvidenceRecord, payload_sha256
from packages.contracts.observation import Observation, Provenance
from packages.repositories.observation_projection_postgres import (
    PostgresObservationProjectionRepository,
)


class Cursor:
    def __init__(self):
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class Connection:
    def __init__(self):
        self.cursor_instance = Cursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None


def make_records():
    payload = {
        "feature": {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [87.0, 25.0]},
            "properties": {"eventtype": "Earthquake"},
        }
    }
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    digest = payload_sha256(payload)
    observation = Observation(
        observation_id="usgs-earthquake-geojson:abc123:" + digest,
        source="usgs-earthquake-geojson",
        source_record_id="abc123",
        observed_at=observed,
        ingested_at=observed,
        payload=payload,
        provenance=Provenance(digest, "usgs-parser-v1"),
        acquired_at=observed,
    )
    evidence = EvidenceRecord(
        evidence_id="evidence-1",
        source=observation.source,
        source_record_id=observation.source_record_id,
        observed_at=observed,
        ingested_at=observed,
        acquired_at=observed,
        payload=payload,
        raw_payload_hash=digest,
        parser_version="usgs-parser-v1",
        schema_version="usgs-geojson-v1",
        license_class="public/open",
    )
    return observation, evidence


def test_projection_normalizes_domain_observation_id_to_postgres_uuid():
    observation, evidence = make_records()
    connection = Connection()

    projected = PostgresObservationProjectionRepository(connection).project(
        observation=observation,
        evidence=evidence,
    )

    assert projected is True
    map_insert = next(
        params
        for query, params in connection.cursor_instance.calls
        if "INSERT INTO map_features" in query
    )
    assert isinstance(map_insert[3], uuid.UUID)
    assert map_insert[3] == uuid.uuid5(uuid.NAMESPACE_URL, observation.observation_id)
    assert connection.commits == 1


def test_projection_uuid_normalization_is_deterministic():
    observation, evidence = make_records()
    first = uuid.uuid5(uuid.NAMESPACE_URL, observation.observation_id)
    second = uuid.uuid5(uuid.NAMESPACE_URL, observation.observation_id)
    assert first == second


def test_projection_sql_normalizes_3d_geojson_to_2d_postgis():
    observation, evidence = make_records()
    connection = Connection()
    PostgresObservationProjectionRepository(connection).project(
        observation=observation,
        evidence=evidence,
    )
    map_query = next(
        query
        for query, _params in connection.cursor_instance.calls
        if "INSERT INTO map_features" in query
    )
    assert "ST_Force2D(ST_GeomFromGeoJSON(%s))" in map_query
