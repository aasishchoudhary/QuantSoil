"""Content-addressed raw-evidence payload storage in Amazon S3.

Authentication is delegated to the AWS SDK credential chain/IAM; no credentials
are accepted in source code. Objects are keyed by the evidence content hash.
"""
from __future__ import annotations
import json
from typing import Any
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
            self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                Metadata={
                    "source": record.source,
                    "source-record-id": record.source_record_id,
                    "sha256": record.raw_payload_hash,
                },
            )
        return f"s3://{self.bucket}/{key}", len(body)
