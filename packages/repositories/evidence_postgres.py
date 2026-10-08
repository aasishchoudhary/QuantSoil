"""PostgreSQL repository for the immutable evidence ledger.

The adapter depends only on the Python DB-API connection/cursor contract. A
PostgreSQL driver such as psycopg can be supplied by the deployment without
becoming part of the domain contract or the default test environment.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from packages.contracts.evidence import EvidenceRecord


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def __enter__(self) -> "Cursor": ...
    def __exit__(self, *args: Any) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...


class EvidenceRepositoryError(RuntimeError):
    """Raised when persistence fails before an evidence record is accepted."""


_INSERT = """
INSERT INTO evidence_records (
    evidence_id, source, source_record_id, observed_at, acquired_at,
    ingested_at, raw_payload_hash, parser_version, schema_version,
    license_class, payload_uri, payload_size_bytes
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (source, source_record_id, raw_payload_hash) DO NOTHING
"""

_SELECT = """
SELECT evidence_id, source, source_record_id, observed_at, acquired_at,
       ingested_at, raw_payload_hash, parser_version, schema_version,
       license_class
FROM evidence_records
WHERE source = %s AND source_record_id = %s AND raw_payload_hash = %s
"""


class PostgresEvidenceRepository:
    """Persist and replay immutable EvidenceRecord identities."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def put(
        self,
        record: EvidenceRecord,
        *,
        payload_uri: str | None = None,
        payload_size_bytes: int | None = None,
    ) -> EvidenceRecord:
        if payload_size_bytes is not None and payload_size_bytes < 0:
            raise EvidenceRepositoryError("payload_size_bytes must be non-negative")

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    _INSERT,
                    (
                        record.evidence_id,
                        record.source,
                        record.source_record_id,
                        record.observed_at,
                        record.acquired_at,
                        record.ingested_at,
                        record.raw_payload_hash,
                        record.parser_version,
                        record.schema_version,
                        record.license_class,
                        payload_uri,
                        payload_size_bytes,
                    ),
                )
                cursor.execute(
                    _SELECT,
                    (record.source, record.source_record_id, record.raw_payload_hash),
                )
                row = cursor.fetchone()
            self._connection.commit()
        except Exception as exc:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise EvidenceRepositoryError("failed to persist evidence record") from exc

        if row is None:
            raise EvidenceRepositoryError("evidence insert completed without a readable record")
        return self._row_to_record(row, record.payload)

    def get(
        self,
        source: str,
        source_record_id: str,
        raw_payload_hash: str,
        *,
        payload: dict[str, Any],
    ) -> EvidenceRecord | None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_SELECT, (source, source_record_id, raw_payload_hash))
                row = cursor.fetchone()
        except Exception as exc:
            raise EvidenceRepositoryError("failed to read evidence record") from exc
        if row is None:
            return None
        return self._row_to_record(row, payload)

    @staticmethod
    def _row_to_record(row: tuple[Any, ...], payload: dict[str, Any]) -> EvidenceRecord:
        (
            evidence_id,
            source,
            source_record_id,
            observed_at,
            acquired_at,
            ingested_at,
            raw_payload_hash,
            parser_version,
            schema_version,
            license_class,
        ) = row
        return EvidenceRecord(
            evidence_id=str(evidence_id),
            source=str(source),
            source_record_id=str(source_record_id),
            observed_at=_as_datetime(observed_at),
            acquired_at=_as_datetime(acquired_at) if acquired_at is not None else None,
            ingested_at=_as_datetime(ingested_at),
            payload=payload,
            raw_payload_hash=str(raw_payload_hash),
            parser_version=str(parser_version),
            schema_version=str(schema_version),
            license_class=str(license_class),
        )


def _as_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise EvidenceRepositoryError("database returned a non-datetime timestamp")
    return value
