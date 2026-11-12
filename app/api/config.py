"""Configuração da aplicação via variáveis de ambiente."""
import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Variável {name} deve ser inteira, recebido: {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    port: int
    app_version: str
    instance_id: str | None
    log_level: str
    work_default_iterations: int
    work_max_iterations: int
    ecs_metadata_uri: str | None


def load_settings() -> Settings:
    s = Settings(
        port=_int_env("PORT", 8000),
        app_version=os.getenv("APP_VERSION", "dev"),
        instance_id=os.getenv("INSTANCE_ID") or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        work_default_iterations=_int_env("WORK_DEFAULT_ITERATIONS", 200_000),
        work_max_iterations=_int_env("WORK_MAX_ITERATIONS", 5_000_000),
        ecs_metadata_uri=os.getenv("ECS_CONTAINER_METADATA_URI_V4") or None,
    )
    if s.work_default_iterations < 1 or s.work_max_iterations < s.work_default_iterations:
        raise ValueError("Requer 1 <= WORK_DEFAULT_ITERATIONS <= WORK_MAX_ITERATIONS")
    return s
