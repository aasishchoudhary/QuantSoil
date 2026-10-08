from fastapi.testclient import TestClient

from services.analyst.api import create_unavailable_app


def test_degraded_analyst_contract_is_not_a_404():
    client = TestClient(create_unavailable_app())
    health = client.get("/health")
    spatial = client.get("/spatial?bbox=0,0,1,1&limit=10")

    assert health.status_code == 503
    assert health.json()["status"] == "degraded"
    assert spatial.status_code == 503
    assert spatial.json()["detail"] == "runtime dependencies are not ready"
