from fastapi.testclient import TestClient
from packages.contracts.world_state import InMemoryWorldStateRepository
from services.analyst.api import create_app
from services.analyst.query import AnalystService

class Map:
    def query_bbox(self,*args): return ()

def test_analyst_rate_limit(monkeypatch):
    monkeypatch.setenv("ANALYST_RATE_LIMIT_PER_MINUTE","1")
    client=TestClient(create_app(AnalystService(InMemoryWorldStateRepository(),Map())))
    assert client.get("/snapshot",params={"entity_ids":"missing","at":"2026-01-01T00:00:00Z"}).status_code==200
    assert client.get("/snapshot",params={"entity_ids":"missing","at":"2026-01-01T00:00:00Z"}).status_code==429
