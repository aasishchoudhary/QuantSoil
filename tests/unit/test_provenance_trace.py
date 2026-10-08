from datetime import datetime, timezone
from packages.contracts.evidence import EvidenceRecord, payload_sha256
from services.provenance.trace import trace_evidence
class Repo:
    def __init__(self, record=None): self.record=record
    def get(self, source, source_record_id, raw_payload_hash, payload):
        return self.record
def record():
    payload={"x":1}; digest=payload_sha256(payload)
    return EvidenceRecord("00000000-0000-0000-0000-000000000001","src","r1",datetime.now(timezone.utc),datetime.now(timezone.utc),payload,digest,"p1","s1","synthetic")
def test_found_is_deterministic():
    r=record(); out=trace_evidence(Repo(r),source="src",source_record_id="r1",raw_payload_hash=r.raw_payload_hash,payload={"x":1})
    assert out.status=="found" and out.evidence==r
def test_missing_is_explicit():
    out=trace_evidence(Repo(),source="src",source_record_id="r1",raw_payload_hash="0"*64,payload={"x":1})
    assert out.status=="missing" and out.evidence is None
