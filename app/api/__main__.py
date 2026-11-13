"""Permite `python -m api` lendo a porta de PORT."""
import uvicorn

from api.config import load_settings

if __name__ == "__main__":
    s = load_settings()
    uvicorn.run("api.main:app", host="0.0.0.0", port=s.port, log_config=None,
                access_log=False, proxy_headers=True, forwarded_allow_ips="*")
