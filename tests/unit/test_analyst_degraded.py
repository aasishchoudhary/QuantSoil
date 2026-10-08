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

from fastapi.testclient import TestClient

from services.runtime import service as runtime_service


def test_runtime_keeps_analyst_contract_mounted_when_dependencies_fail(monkeypatch):
    def fail_build_components():
        raise RuntimeError("DATABASE_URL is required")

    monkeypatch.setattr(runtime_service, "build_components", fail_build_components)
    client = TestClient(runtime_service.create_app())

    with client:
        response = client.get("/v1/analyst/health")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"
        assert response.json()["ready"] is False
