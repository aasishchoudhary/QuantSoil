from datetime import datetime, timezone, timedelta
from services.runtime.postgres import PostgresJobQueue
from services.runtime.contracts import RuntimeJob, JobStatus

class C:
    def __init__(self,row=None): self.row=row; self.calls=[]; self.rowcount=1
    def execute(self,q,p): self.calls.append((q,p))
    def fetchone(self): return self.row
    def __enter__(self): return self
    def __exit__(self,*a): pass

class DB:
    def __init__(self,row=None): self.c=C(row); self.commits=0; self.rollbacks=0
    def cursor(self): return self.c
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1

def test_claim_uses_skip_locked_and_returns_lease():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    row=("j","s","k",t,1,"running",t+timedelta(minutes=5),None)
    db=DB(row)
    j=PostgresJobQueue(db).claim(now=t,lease=timedelta(minutes=5))
    assert j.job_id=="j"
    assert j.status is JobStatus.RUNNING
    assert "SKIP LOCKED" in db.c.calls[0][0]

def test_get_returns_none_when_absent():
    db=DB(None)
    assert PostgresJobQueue(db).get("missing") is None
