"""Operação CPU-bound controlada e determinística."""
import hashlib
import time


def cpu_work(iterations: int) -> dict:
    """Encadeia `iterations` hashes SHA-256.

    Custo linear e previsível em `iterations`; o digest final é determinístico,
    o que permite validar que o trabalho foi realmente executado.
    """
    digest = b"ecs-load-test"
    start = time.perf_counter()
    for _ in range(iterations):
        digest = hashlib.sha256(digest).digest()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"iterations": iterations, "digest": digest.hex(), "duration_ms": round(elapsed_ms, 3)}
