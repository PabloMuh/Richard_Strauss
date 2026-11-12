import os

os.environ.setdefault("INSTANCE_ID", "test-instance")
os.environ.setdefault("WORK_DEFAULT_ITERATIONS", "1000")
os.environ.setdefault("WORK_MAX_ITERATIONS", "100000")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.work import cpu_work  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["content-type"].startswith("application/json")


def test_instance():
    r = client.get("/instance")
    assert r.status_code == 200
    body = r.json()
    for key in ("instance_id", "hostname", "pid", "version", "started_at", "uptime_s", "ecs"):
        assert key in body
    assert body["instance_id"] == "test-instance"
    assert body["ecs"] is None  # fora do ECS
    assert r.headers["x-instance-id"] == "test-instance"


def test_work_default():
    r = client.get("/work")
    assert r.status_code == 200
    body = r.json()
    assert body["iterations"] == 1000
    assert body["instance_id"] == "test-instance"
    assert len(body["digest"]) == 64
    assert body["duration_ms"] >= 0


def test_work_is_deterministic():
    a = client.get("/work", params={"iterations": 500}).json()
    b = client.get("/work", params={"iterations": 500}).json()
    assert a["digest"] == b["digest"] == cpu_work(500)["digest"]
    assert a["digest"] != cpu_work(501)["digest"]


def test_work_cost_scales():
    small = cpu_work(1_000)["duration_ms"]
    big = cpu_work(100_000)["duration_ms"]
    assert big > small


def test_work_rejects_invalid():
    for params in ({"iterations": 0}, {"iterations": 100001}, {"iterations": "abc"}):
        r = client.get("/work", params=params)
        assert r.status_code == 400, params
        assert r.json()["error"]["code"] == "invalid_parameter"


def test_not_found_is_json():
    r = client.get("/nao-existe")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_request_id_propagated():
    r = client.get("/instance", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
