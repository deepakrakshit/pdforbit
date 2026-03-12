from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_endpoint_reports_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "PdfORBIT API"
    assert body["environment"] == "test"
def test_readiness_endpoint_sets_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready", headers={"X-Request-ID": "req-phase-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-phase-1"
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["checks"]) == 5
    assert {check["name"] for check in body["checks"]} == {
        "configuration",
        "router",
        "database",
        "queue",
        "storage",
    }
