from packages.contracts.fusion import Assertion
from packages.repositories.fusion_postgres import PostgresAssertionRepository


class Cursor:
    def __init__(self):
        self.row = None
        self.rows = []
        self.calls = []
    def execute(self, query, params): self.calls.append((query, params))
    def fetchone(self): return self.row
    def fetchall(self): return self.rows
    def __enter__(self): return self
    def __exit__(self, *args): return None


class Connection:
    def __init__(self):
        self.c = Cursor()
        self.commits = 0
        self.rollbacks = 0
    def cursor(self): return self.c
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def assertion():
    return Assertion("a-1", "e-1", "status", "active", 0.9, 0.8, ("ev-1",))


def test_put_is_idempotent_and_immutable():
    conn = Connection()
    a = assertion()
    conn.c.row = ("a-1", "e-1", "status", '"active"', 0.9, 0.8, ["ev-1"])
    assert PostgresAssertionRepository(conn).put(a) == a
    assert conn.commits == 1


def test_list_reconstructs_assertions():
    conn = Connection()
    conn.c.rows = [("a-1", "e-1", "status", '"active"', 0.9, 0.8, ["ev-1"])]
    result = PostgresAssertionRepository(conn).list_for_property("e-1", "status")
    assert result == (assertion(),)
