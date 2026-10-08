import pytest
from packages.repositories.map_postgres import PostgresMapRepository

class Cursor:
    def execute(self,q,p): self.params=p
    def fetchone(self): return (b"tile",)
    def __enter__(self): return self
    def __exit__(self,*a): pass
class DB:
    def cursor(self): return Cursor()

def test_vector_tile_bounds():
    repo=PostgresMapRepository(DB())
    assert repo.tile(2,1,1)==b"tile"
    with pytest.raises(ValueError): repo.tile(25,0,0)
    with pytest.raises(ValueError): repo.tile(2,4,0)
