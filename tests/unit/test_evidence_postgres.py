from datetime import datetime, timezone

import pytest

from packages.contracts.evidence import EvidenceRecord, payload_sha256
from packages.repositories.evidence_postgres import EvidenceRepositoryError, PostgresEvidenceRepository


class FakeCursor:
    def __init__(self, row=None, error=None):
        self.row = row
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query, params):
        self.calls.append((query, params))
        if self.error:
            raise self.error

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None, error=None):
        self.cursor_instance = FakeCursor(row, error)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def make_record(payload=None):
    payload = payload or {"sensor": "synthetic", "value": 7}
    return EvidenceRecord(
        evidence_id="ev-original",
        source="synthetic",
        source_record_id="r-7",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        payload=payload,
        raw_payload_hash=payload_sha256(payload),
        parser_version="synthetic-v1",
        schema_version="evidence-v1",
        license_class="synthetic",
    )


def row_for(record, evidence_id="ev-original"):
    return (
        evidence_id, record.source, record.source_record_id, record.observed_at,
        record.acquired_at, record.ingested_at, record.raw_payload_hash,
        record.parser_version, record.schema_version, record.license_class,
    )


def test_put_is_idempotent_and_returns_database_identity():
    record = make_record()
    connection = FakeConnection(row_for(record, evidence_id="ev-database"))
    result = PostgresEvidenceRepository(connection).put(record, payload_size_bytes=12)

    assert result.evidence_id == "ev-database"
    assert result.raw_payload_hash == record.raw_payload_hash
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert len(connection.cursor_instance.calls) == 2
    assert connection.cursor_instance.calls[0][1][-1] == 12


def test_put_rolls_back_and_hides_driver_error():
    connection = FakeConnection(error=RuntimeError("database details"))
    with pytest.raises(EvidenceRepositoryError, match="failed to persist") as exc:
        PostgresEvidenceRepository(connection).put(make_record())
    assert "database details" not in str(exc.value)
    assert connection.rollbacks == 1


def test_negative_payload_size_is_rejected_before_database_access():
    connection = FakeConnection()
    with pytest.raises(EvidenceRepositoryError, match="non-negative"):
        PostgresEvidenceRepository(connection).put(make_record(), payload_size_bytes=-1)
    assert connection.cursor_instance.calls == []
