from datetime import datetime, timezone
from packages.repositories.analyst_audit_postgres import PostgresAnalystAuditRepository

class Cursor:
    def execute(self,q,p): self.query=q; self.params=p
    def __enter__(self): return self
    def __exit__(self,*a): pass
class DB:
    def __init__(self): self.commits=0
    def cursor(self): return Cursor()
    def commit(self): self.commits+=1
    def rollback(self): pass

def test_audit_repository_persists_low_cardinality_event():
    db=DB()
    PostgresAnalystAuditRepository(db).put(
        occurred_at=datetime.now(timezone.utc),method="GET",
        path="/v1/analyst/snapshot",status_code=200,correlation_id="abc")
    assert db.commits==1
