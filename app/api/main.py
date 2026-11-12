"""API para experimentos de escalabilidade no ECS.

Endpoints:
  GET /health    -> liveness/health check do ALB e do ECS
  GET /instance  -> identifica qual task/instância respondeu
  GET /work      -> operação CPU-bound controlada (?iterations=N)
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import anyio
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import load_settings
from api.instance import base_info, ecs_task_metadata, instance_id
from api.logging_setup import setup_logging
from api.work import cpu_work

settings = load_settings()
log = setup_logging(settings.log_level)
STARTED_AT = datetime.now(timezone.utc)
_START_MONO = time.monotonic()

@asynccontextmanager
async def lifespan(app_: FastAPI):
    # Criado dentro do event loop do servidor: limita quantas execuções de /work rodam ao mesmo tempo.
    app_.state.work_limiter = anyio.CapacityLimiter(settings.work_concurrency)
    log.info("startup", extra={"extra_fields": {
        "port": settings.port, "version": settings.app_version, "instance_id": _instance_id(),
        "work_default_iterations": settings.work_default_iterations,
        "work_max_iterations": settings.work_max_iterations,
        "work_concurrency": settings.work_concurrency,
    }})
    yield
    log.info("shutdown", extra={"extra_fields": {"instance_id": _instance_id()}})


app = FastAPI(title="ECS Load Test API", version=settings.app_version, lifespan=lifespan)


def _instance_id() -> str:
    return instance_id(settings.instance_id, ecs_task_metadata(settings.ecs_metadata_uri))


def _error(status: int, code: str, message: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message},
            "instance_id": _instance_id(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.middleware("http")
async def access_log(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled_error", extra={"extra_fields": {"path": request.url.path}})
        response = _error(500, "internal_error", "Erro interno", request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    response.headers["x-request-id"] = request.state.request_id
    response.headers["x-instance-id"] = _instance_id()
    if request.url.path != "/health":  # evita poluir logs com health checks
        log.info(
            "request",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": response.status_code,
                "duration_ms": elapsed_ms,
                "request_id": request.state.request_id,
                "instance_id": _instance_id(),
            }},
        )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "http_error"
    return _error(exc.status_code, code, str(exc.detail), request)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    msgs = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
    return _error(400, "invalid_parameter", msgs, request)


# `async`: responde direto no event loop, sem esperar thread livre nem competir com /work.
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/instance")
def instance():
    ecs = ecs_task_metadata(settings.ecs_metadata_uri)
    return {
        "instance_id": _instance_id(),
        **base_info(),
        "version": settings.app_version,
        "started_at": STARTED_AT.isoformat(),
        "uptime_s": round(time.monotonic() - _START_MONO, 3),
        "ecs": ecs,
    }


# O cálculo roda numa thread, fora do event loop, com no máximo WORK_CONCURRENCY execuções
# simultâneas (padrão 1); os pedidos excedentes esperam na fila sem consumir CPU. Com 0,25 vCPU,
# execuções em paralelo não aumentam a vazão: só disputam a GIL com o event loop e atrasavam
# /health além do timeout do health check (impedimento API-02 em docs/impedimentos.md).
@app.get("/work")
async def work(
    request: Request,
    iterations: int | None = Query(
        default=None, ge=1, le=settings.work_max_iterations,
        description="Número de hashes SHA-256 encadeados",
    ),
):
    n = iterations or settings.work_default_iterations
    result = await anyio.to_thread.run_sync(cpu_work, n, limiter=request.app.state.work_limiter)
    return {"instance_id": _instance_id(), **result}

