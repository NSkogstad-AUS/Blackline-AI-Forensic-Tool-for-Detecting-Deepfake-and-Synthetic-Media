from fastapi.testclient import TestClient
from backend.src import api_server


def test_root_and_health_endpoints():
    client = TestClient(api_server.app)
    r = client.get("/")
    assert r.status_code == 200
    j = r.json()
    assert j.get("service") == "blackline-api"

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json().get("status") == "ok"
