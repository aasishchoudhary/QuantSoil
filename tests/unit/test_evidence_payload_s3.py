from packages.repositories.evidence_payload_s3 import S3EvidencePayloadStore


def test_existing_evidence_object_is_hash_and_length_checked(monkeypatch):
    class Client:
        def head_object(self, **kwargs):
            return {"ContentLength": 3, "Metadata": {"sha256": "abc"}}
    store = object.__new__(S3EvidencePayloadStore)
    store.bucket = "bucket"
    store.prefix = "evidence/"
    store._client = Client()

    class Record:
        raw_payload_hash = "def"
        payload = {"x": 1}

    try:
        store.put(Record())
    except RuntimeError as exc:
        assert "hash does not match" in str(exc)
    else:
        raise AssertionError("expected hash mismatch")
