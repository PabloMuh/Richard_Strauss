import os
import threading
import time

os.environ.setdefault("INSTANCE_ID", "test-instance")
os.environ.setdefault("WORK_DEFAULT_ITERATIONS", "1000")
os.environ.setdefault("WORK_MAX_ITERATIONS", "100000")
os.environ.setdefault("WORK_CONCURRENCY", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api.main as main_module  # noqa: E402
from api.config import load_settings  # noqa: E402
from api.main import app  # noqa: E402
from api.work import cpu_work  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # `with` executa o lifespan (como o uvicorn) e mantém um único event loop para todas as requisições.
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["content-type"].startswith("application/json")


def test_instance(client):
    r = client.get("/instance")
    assert r.status_code == 200
    body = r.json()
    for key in ("instance_id", "hostname", "pid", "version", "started_at", "uptime_s", "ecs"):
        assert key in body
    assert body["instance_id"] == "test-instance"
    assert body["ecs"] is None  # fora do ECS
    assert r.headers["x-instance-id"] == "test-instance"


def test_work_default(client):
    r = client.get("/work")
    assert r.status_code == 200
    body = r.json()
    assert body["iterations"] == 1000
    assert body["instance_id"] == "test-instance"
    assert len(body["digest"]) == 64
    assert body["duration_ms"] >= 0


def test_work_is_deterministic(client):
    a = client.get("/work", params={"iterations": 500}).json()
    b = client.get("/work", params={"iterations": 500}).json()
    assert a["digest"] == b["digest"] == cpu_work(500)["digest"]
    assert a["digest"] != cpu_work(501)["digest"]


def test_work_cost_scales():
    small = cpu_work(1_000)["duration_ms"]
    big = cpu_work(100_000)["duration_ms"]
    assert big > small


def test_work_rejects_invalid(client):
    for params in ({"iterations": 0}, {"iterations": 100001}, {"iterations": "abc"}):
        r = client.get("/work", params=params)
        assert r.status_code == 400, params
        assert r.json()["error"]["code"] == "invalid_parameter"


def test_not_found_is_json(client):
    r = client.get("/nao-existe")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_request_id_propagated(client):
    r = client.get("/instance", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


def _fake_result(n):
    return {"iterations": n, "digest": "0" * 64, "duration_ms": 0.0}


def test_work_concurrency_is_limited(client, monkeypatch):
    """Pedidos simultâneos de /work executam no máximo WORK_CONCURRENCY cálculos ao mesmo tempo."""
    lock = threading.Lock()
    state = {"active": 0, "peak": 0}

    def tracked_cpu_work(n):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        time.sleep(0.1)
        with lock:
            state["active"] -= 1
        return _fake_result(n)

    monkeypatch.setattr(main_module, "cpu_work", tracked_cpu_work)
    statuses = []
    threads = [threading.Thread(target=lambda: statuses.append(client.get("/work").status_code)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert statuses == [200] * 5
    assert state["peak"] == main_module.settings.work_concurrency == 1


def test_health_responds_while_work_is_saturated(client, monkeypatch):
    """API-02: com /work ocupado e fila cheia, /health continua respondendo (health check do ECS/ALB)."""
    release = threading.Event()
    started = threading.Event()

    def blocking_cpu_work(n):
        started.set()
        release.wait(timeout=15)
        return _fake_result(n)

    monkeypatch.setattr(main_module, "cpu_work", blocking_cpu_work)
    # Mais pedidos que as 40 threads padrão do Starlette: no desenho antigo, /health ficava sem thread.
    threads = [threading.Thread(target=client.get, args=("/work",)) for _ in range(50)]
    for t in threads:
        t.start()
    try:
        assert started.wait(timeout=5)
        time.sleep(0.5)  # deixa os demais pedidos chegarem à fila
        t0 = time.perf_counter()
        r = client.get("/health")
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert elapsed < 2, f"/health levou {elapsed:.2f}s com /work saturado"
    finally:
        release.set()
        for t in threads:
            t.join(timeout=20)


def test_work_concurrency_must_be_positive(monkeypatch):
    monkeypatch.setenv("WORK_CONCURRENCY", "0")
    with pytest.raises(ValueError, match="WORK_CONCURRENCY"):
        load_settings()
