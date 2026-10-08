from services.runtime.health import check_database

class Cursor:
    def execute(self, query, params): self.query = query
    def fetchone(self): return (1,)
    def __enter__(self): return self
    def __exit__(self, *args): pass

class DB:
    def cursor(self): return Cursor()
    def close(self): pass

def test_database_health():
    assert check_database(DB) is True
