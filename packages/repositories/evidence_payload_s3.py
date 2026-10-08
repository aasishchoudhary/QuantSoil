"""Content-addressed raw-evidence payload storage in Amazon S3.

Authentication is delegated to the AWS SDK credential chain/IAM; no credentials
are accepted in source code. Objects are keyed by the evidence content hash.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
from packages.contracts.evidence import EvidenceRecord, canonical_json_bytes

class S3EvidencePayloadStore:
    def __init__(self, bucket: str, *, prefix: str = "evidence/") -> None:
        if not bucket.strip():
            raise ValueError("bucket is required")
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 evidence storage") from exc
        self._client = boto3.client("s3")

    def put(self, record: EvidenceRecord) -> tuple[str, int]:
        body = canonical_json_bytes(record.payload)
        key = f"{self.prefix}{record.raw_payload_hash[:2]}/{record.raw_payload_hash}.json"
        try:
            existing = self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            response = getattr(exc, "response", {})
            code = str(response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise RuntimeError("failed to verify existing evidence object") from exc
        else:
            existing_hash = str(existing.get("Metadata", {}).get("sha256", ""))
            if existing_hash != record.raw_payload_hash:
                raise RuntimeError("existing evidence object hash does not match content address")
            if int(existing.get("ContentLength", -1)) != len(body):
                raise RuntimeError("existing evidence object length does not match payload")
            return f"s3://{self.bucket}/{key}", len(body)
        self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                IfNoneMatch="*",
                Metadata={
                    "source": record.source,
                    "source-record-id": record.source_record_id,
                    "sha256": record.raw_payload_hash,
                },
            )
        return f"s3://{self.bucket}/{key}", len(body)


class LocalEvidencePayloadStore:
    """Content-addressed filesystem store for local/offline development only.

    Production defaults to S3; this backend exists so a real PostgreSQL-backed
    local runtime can be exercised on Termux without inventing evidence.
    """

    def __init__(self, root: str, *, prefix: str = "evidence/") -> None:
        if not root.strip():
            raise ValueError("root is required")
        self.root = Path(root).expanduser()
        self.prefix = prefix.strip("/")

    def put(self, record: EvidenceRecord) -> tuple[str, int]:
        body = canonical_json_bytes(record.payload)
        expected = record.raw_payload_hash
        actual = hashlib.sha256(body).hexdigest()
        if actual != expected:
            raise RuntimeError("payload hash does not match content address")
        key = Path(self.prefix) / expected[:2] / f"{expected}.json"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_bytes()
            if len(existing) != len(body) or hashlib.sha256(existing).hexdigest() != expected:
                raise RuntimeError("existing evidence object does not match content address")
            return path.as_uri(), len(existing)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with tmp.open("xb") as handle:
                handle.write(body)
            os.replace(tmp, path)
        except FileExistsError:
            if path.exists():
                existing = path.read_bytes()
                if len(existing) != len(body) or hashlib.sha256(existing).hexdigest() != expected:
                    raise RuntimeError("existing evidence object does not match content address")
            else:
                raise
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        return path.as_uri(), len(body)
