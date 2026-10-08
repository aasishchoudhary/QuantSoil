from datetime import datetime, timezone, timedelta
from packages.repositories.prediction_postgres import PostgresPredictionRepository

class Cursor:
    def execute(self,q,p): self.query=q; self.params=p
    def __enter__(self): return self
    def __exit__(self,*a): pass
class DB:
    def __init__(self): self.commits=0
    def cursor(self): return Cursor()
    def commit(self): self.commits+=1
    def rollback(self): pass

def test_prediction_repository_rejects_invalid_score():
    repo=PostgresPredictionRepository(DB())
    try:
        repo.score("x",1.2,1,evaluated_at=datetime.now(timezone.utc))
    except Exception as exc:
        assert "invalid score" in str(exc)
    else:
        raise AssertionError("invalid probability accepted")
