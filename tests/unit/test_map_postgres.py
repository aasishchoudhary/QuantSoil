from datetime import datetime, timezone
from packages.repositories.map_postgres import PostgresMapRepository

class Cursor:
    def execute(self,q,p): self.params=p
    def fetchall(self):
        return [("f1","earthquake","usgs","r1",None,{"type":"Point","coordinates":[1,2]},{"mag":4.0},.9,datetime(2026,1,1,tzinfo=timezone.utc),"a"*64,"p1","public/open",None,None)]
    def __enter__(self): return self
    def __exit__(self,*a): pass
class DB:
    def cursor(self): return Cursor()

def test_map_repository_preserves_provenance():
    item=PostgresMapRepository(DB()).query_bbox(0,0,3,3)[0]
    assert item.source=="usgs"
    assert item.raw_payload_hash=="a"*64
    assert item.geometry["coordinates"]==[1,2]

class SearchCursor:
    def __init__(self, parent): self.parent=parent
    def execute(self, query, params):
        self.parent.query=query
        self.parent.params=params
    def fetchall(self):
        return [("f1","aircraft","adsb","ABC123",None,{"type":"Point","coordinates":[87,25]},{"callsign":"ABC123"},.8,datetime(2026,1,1,tzinfo=timezone.utc),"b"*64,"p1","public/open",None,None)]
    def __enter__(self): return self
    def __exit__(self,*a): pass

class SearchDB:
    def cursor(self): return SearchCursor(self)

def test_map_repository_global_search_uses_bound_parameters():
    db=SearchDB()
    results=PostgresMapRepository(db).search("ABC123", limit=10)
    assert len(results)==1
    assert results[0].source_record_id=="ABC123"
    assert "LIKE lower(%s)" in db.query
    assert db.params==("%ABC123%",10)
