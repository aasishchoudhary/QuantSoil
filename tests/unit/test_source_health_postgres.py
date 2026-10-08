from datetime import datetime, timezone
from packages.evaluation.data_quality import SourceHealth
from packages.repositories.source_health_postgres import PostgresSourceHealthRepository

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

class Cursor:
    def __init__(self):
        self.row = None
        self.calls = []
    def execute(self, q, p): self.calls.append((q, p))
    def fetchone(self): return self.row
    def __enter__(self): return self
    def __exit__(self, *args): return None

class Connection:
    def __init__(self):
        self.c = Cursor(); self.commits = 0
    def cursor(self): return self.c
    def commit(self): self.commits += 1
    def rollback(self): pass

def test_source_health_round_trip():
    conn = Connection()
    health = SourceHealth("sensor", T, T, 2)
    conn.c.row = ("sensor", T, T, 2)
    repo = PostgresSourceHealthRepository(conn)
    assert repo.put(health) == health
    assert repo.get("sensor") == health
    assert conn.commits == 1
