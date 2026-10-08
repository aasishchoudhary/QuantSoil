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


def test_existing_evidence_object_rejects_length_mismatch():
    class Client:
        def head_object(self, **kwargs):
            return {"ContentLength": 999, "Metadata": {"sha256": "def"}}
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
        assert "length does not match" in str(exc)
    else:
        raise AssertionError("expected length mismatch")


def test_s3_new_object_is_written_with_content_address():
    calls = []
    class Client:
        def head_object(self, **kwargs):
            class Missing(Exception):
                response = {"Error": {"Code": "404"}}
            raise Missing()
        def put_object(self, **kwargs):
            calls.append(kwargs)
    store = object.__new__(S3EvidencePayloadStore)
    store.bucket = "bucket"
    store.prefix = "evidence/"
    store._client = Client()

    class Record:
        raw_payload_hash = "a" * 64
        payload = {"x": 1}
        source = "test"
        source_record_id = "record-1"

    uri, size = store.put(Record())
    assert uri == f"s3://bucket/evidence/{'a' * 2}/{'a' * 64}.json"
    assert size > 0
    assert len(calls) == 1
    assert calls[0]["IfNoneMatch"] == "*"


def test_local_evidence_store_is_content_addressed(tmp_path):
    from packages.repositories.evidence_payload_s3 import LocalEvidencePayloadStore
    import hashlib
    import json

    payload = {"x": 1}
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(body).hexdigest()

    class Record:
        raw_payload_hash = digest

    Record.payload = payload
    store = LocalEvidencePayloadStore(str(tmp_path))
    uri, size = store.put(Record())
    assert uri.startswith("file://")
    assert size == len(body)
    assert len(list(tmp_path.rglob("*.json"))) == 1
