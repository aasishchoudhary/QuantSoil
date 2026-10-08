# Evidence Ledger

The Evidence Ledger is the trust boundary between source ingestion and downstream intelligence.

## Invariants

1. A raw payload receives a deterministic SHA-256 content identity.
2. Evidence is immutable after acceptance.
3. Replaying the same `(source, source_record_id, raw_payload_hash)` is idempotent.
4. A changed payload creates a distinct content identity; it must not overwrite the prior record.
5. Parser and schema versions are retained with the evidence.
6. License classification is retained with the evidence.
7. Raw bytes are not treated as mutable application state.
8. Derived observations and world-state projections must retain an evidence reference.

## Persistence

The PostgreSQL migration defines the provenance index. Raw payload bytes should live in immutable/versioned object storage, referenced by `payload_uri`; the database record remains the queryable integrity and provenance index.

The current Python `InMemoryEvidenceLedger` is intentionally infrastructure-free for deterministic tests and replay evaluation. A DB-API-compatible PostgreSQL repository adapter is implemented in `packages/repositories/evidence_postgres.py`; it preserves the ledger identity, commits atomically, rolls back on failure, and redacts driver errors at the application boundary.

## Replay semantics

A connector replay should execute: raw payload -> canonical hash -> validate contract -> idempotent ledger put -> observation/projection.

If the same payload is replayed, the ledger count does not increase. If the content changes, the new hash produces a new immutable evidence identity.

## Failure behavior

- malformed/unserializable payload: reject
- hash mismatch: reject
- invalid hash format: reject
- immutable identity collision with different content: reject
- duplicate identical evidence: return existing record
