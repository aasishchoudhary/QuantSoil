from services.runtime.service import build_components

def test_build_components_registers_all_public_connectors(monkeypatch):
    class DummyConn: pass
    monkeypatch.setenv("DATABASE_URL","postgresql://unused")
    monkeypatch.setattr("services.runtime.service._database_factory",lambda:DummyConn())
    class Queue:
        def __init__(self,connection): pass
    monkeypatch.setattr("services.runtime.service.PostgresJobQueue",Queue)
    class Health: 
        def __init__(self,*a,**k): pass
    monkeypatch.setattr("services.runtime.service.PostgresSourceHealthRepository",Health)
    class Audit:
        def __init__(self,*a,**k): pass
    monkeypatch.setattr("services.runtime.service.PostgresIngestionAuditRepository",Audit)
    class EMeta:
        def __init__(self,*a,**k): pass
    monkeypatch.setattr("services.runtime.service.PostgresEvidenceRepository",EMeta)
    class EPayload:
        def __init__(self,*a,**k): pass
    monkeypatch.setattr("services.runtime.service.S3EvidencePayloadStore",EPayload)
    _, registry, connectors, _, _, _ = build_components()
    assert len(connectors)==3
    assert set(connectors)=={spec.source for spec in registry.all()}
