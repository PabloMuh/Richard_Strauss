"""Identificação da instância (local ou task ECS)."""
import json
import os
import socket
import urllib.request
from functools import lru_cache


@lru_cache(maxsize=1)
def ecs_task_metadata(metadata_uri: str | None) -> dict | None:
    """Lê o endpoint de metadados v4 do ECS (só existe dentro de uma task)."""
    if not metadata_uri:
        return None
    try:
        with urllib.request.urlopen(f"{metadata_uri}/task", timeout=1) as resp:
            data = json.loads(resp.read())
    except Exception:  # noqa: BLE001 - metadados são opcionais
        return None
    task_arn = data.get("TaskARN", "")
    return {
        "task_arn": task_arn,
        "task_id": task_arn.rsplit("/", 1)[-1] if task_arn else None,
        "cluster": data.get("Cluster"),
        "family": data.get("Family"),
        "revision": data.get("Revision"),
        "availability_zone": data.get("AvailabilityZone"),
    }


def instance_id(override: str | None, ecs: dict | None) -> str:
    if override:
        return override
    if ecs and ecs.get("task_id"):
        return ecs["task_id"]
    return socket.gethostname()


def base_info() -> dict:
    return {"hostname": socket.gethostname(), "pid": os.getpid()}
