from datetime import datetime, timezone
from packages.contracts.world_state import EntityState
from packages.repositories.world_state_postgres import PostgresWorldStateRepository


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.row = None
        self.rows = []
    def execute(self, query, params):
        self.calls.append((query, params))
    def fetchone(self):
        return self.row
    def fetchall(self):
        return self.rows
    def __enter__(self): return self
    def __exit__(self, *args): return None


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0
        self.rollbacks = 0
    def cursor(self): return self.cursor_obj
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def make_state():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return EntityState(
        state_id="s-1", entity_id="e-1", entity_type="aircraft",
        valid_from=t, valid_to=None, observed_at=t, recorded_at=t,
        properties={"status":"active"}, evidence_refs=("ev-1",)
    )


def test_append_commits():
    conn = FakeConnection()
    state = make_state()
    assert PostgresWorldStateRepository(conn).append(state) == state
    assert conn.commits == 1


def test_as_of_reconstructs_domain_state():
    conn = FakeConnection()
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    conn.cursor_obj.row = (
        "s-1","e-1","aircraft",t,None,t,t,{"status":"active"},None,0.9,["ev-1"]
    )
    result = PostgresWorldStateRepository(conn).as_of("e-1", t)
    assert result is not None
    assert result.state_id == "s-1"
    assert result.properties["status"] == "active"


def test_history_is_ordered_by_database_contract():
    conn = FakeConnection()
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    conn.cursor_obj.rows = [
        ("s-1","e-1","aircraft",t,None,t,t,{},None,None,["ev-1"])
    ]
    result = PostgresWorldStateRepository(conn).history("e-1")
    assert [item.state_id for item in result] == ["s-1"]
