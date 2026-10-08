from datetime import datetime, timezone

from packages.contracts.evidence import payload_sha256
from packages.evaluation.replay import replay


def item(value=1, evidence_id="00000000-0000-0000-0000-000000000001", source_record_id="r1"):
    payload = {"value": value}
    return {
        "evidence_id": evidence_id,
        "source": "synthetic",
        "source_record_id": source_record_id,
        "observed_at": datetime.now(timezone.utc),
        "ingested_at": datetime.now(timezone.utc),
        "payload": payload,
        "raw_payload_hash": payload_sha256(payload),
        "parser_version": "p1",
        "schema_version": "s1",
        "license_class": "synthetic",
    }


def test_replay_is_idempotent():
    result = replay([item(), item()])
    assert result.accepted == 2
    assert result.unique == 1
    assert result.rejected == 0


def test_replay_rejects_tampering():
    bad = item()
    bad["raw_payload_hash"] = "0" * 64
    result = replay([bad])
    assert result.rejected == 1 and result.unique == 0


def test_replay_accepts_distinct_content_identity():
    result = replay([item(), item(value=2, evidence_id="00000000-0000-0000-0000-000000000002", source_record_id="r2")])
    assert result.accepted == 2
    assert result.unique == 2
    assert result.rejected == 0
