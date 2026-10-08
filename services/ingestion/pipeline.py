"""Ingestion pipeline that makes quality disposition explicit."""
from __future__ import annotations
from dataclasses import dataclass
from packages.contracts.evidence import EvidenceRecord, InMemoryEvidenceLedger
from services.ingestion.observation import IngestionResult, ObservationIngestor


@dataclass(frozen=True)
class PipelineOutcome:
    result: IngestionResult
    evidence_stored: bool
    may_enter_authoritative_state: bool


class IngestionPipeline:
    def __init__(self, *, ingestor: ObservationIngestor, evidence_ledger: InMemoryEvidenceLedger):
        self.ingestor = ingestor
        self.evidence_ledger = evidence_ledger

    def process(self, **kwargs) -> PipelineOutcome:
        result = self.ingestor.ingest(**kwargs)
        self.evidence_ledger.put(result.evidence)
        return PipelineOutcome(
            result=result,
            evidence_stored=True,
            may_enter_authoritative_state=result.accepted,
        )
