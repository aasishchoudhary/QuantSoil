from fastapi.testclient import TestClient
from datetime import datetime, timezone
from packages.contracts.world_state import InMemoryWorldStateRepository
from services.analyst.api import create_app
from services.analyst.query import AnalystService
import os

def service():
    class Map:
        def query_bbox(self,*args): return ()
    return AnalystService(InMemoryWorldStateRepository(), Map())

def test_optional_auth_and_security_headers(monkeypatch):
    monkeypatch.setenv("ANALYST_AUTH_MODE","optional")
    client=TestClient(create_app(service()))
    response=client.get("/health")
    assert response.status_code==200
    assert response.headers["x-content-type-options"]=="nosniff"
    assert response.headers["cache-control"]=="no-store"

def test_required_auth_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("ANALYST_AUTH_MODE","required")
    monkeypatch.setenv("ANALYST_BEARER_TOKEN","test-token")
    client=TestClient(create_app(service()))
    response=client.get("/snapshot", params={"entity_ids":"missing","at":"2026-01-01T00:00:00Z"})
    assert response.status_code==401
    assert response.headers["www-authenticate"]=="Bearer"
