from datetime import datetime, timezone

import pytest

from packages.contracts.evidence import (
    EvidenceIntegrityError,
    EvidenceRecord,
    InMemoryEvidenceLedger,
    payload_sha256,
)


def record(payload=None, **overrides):
    payload = payload if payload is not None else {"b": 2, "a": 1}
    values = {
        "evidence_id": "ev-1",
        "source": "synthetic",
        "source_record_id": "record-1",
        "observed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "payload": payload,
        "raw_payload_hash": payload_sha256(payload),
        "parser_version": "synthetic-v1",
        "schema_version": "evidence-v1",
        "license_class": "synthetic",
    }
    values.update(overrides)
    return EvidenceRecord(**values)


def test_hash_is_deterministic_across_mapping_order():
    assert payload_sha256({"a": 1, "b": 2}) == payload_sha256({"b": 2, "a": 1})


def test_record_rejects_tampered_payload():
    with pytest.raises(EvidenceIntegrityError):
        record(raw_payload_hash="0" * 64)


def test_ledger_is_idempotent_for_same_content():
    ledger = InMemoryEvidenceLedger()
    first = record()
    assert ledger.put(first) == first
    assert ledger.put(first) == first
    assert ledger.count() == 1


def test_ledger_preserves_distinct_content():
    ledger = InMemoryEvidenceLedger()
    ledger.put(record())
    ledger.put(record(payload={"a": 99}))
    assert ledger.count() == 2


def test_ledger_retrieves_by_immutable_identity():
    ledger = InMemoryEvidenceLedger()
    item = record()
    ledger.put(item)
    assert ledger.get(item.source, item.source_record_id, item.raw_payload_hash) == item
