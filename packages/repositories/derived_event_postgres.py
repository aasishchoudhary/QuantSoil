"""PostgreSQL persistence for evidence-backed derived events."""
from __future__ import annotations
import json
from typing import Any
from packages.contracts.event import Event

class DerivedEventRepositoryError(RuntimeError): pass

class PostgresDerivedEventRepository:
    def __init__(self, connection): self.connection=connection

    def put(self,event: Event)->Event:
        if event.state!="derived":
            raise DerivedEventRepositoryError("only derived events may be persisted here")
        q="""INSERT INTO derived_events
        (event_id,event_type,occurred_at,evidence_refs,payload,confidence)
        VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s)
        ON CONFLICT (event_id) DO NOTHING"""
        try:
            with self.connection.cursor() as c:
                c.execute(q,(event.event_id,event.event_type,event.occurred_at,
                    json.dumps(list(event.evidence_refs)),json.dumps(dict(event.payload)),
                    event.confidence))
            self.connection.commit()
        except Exception as exc:
            try:self.connection.rollback()
            except Exception:pass
            raise DerivedEventRepositoryError("failed to persist derived event") from exc
        return event
