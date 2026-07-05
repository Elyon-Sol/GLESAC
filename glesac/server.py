"""`glesac run` - the local web console. FastAPI app, bound to 127.0.0.1 ONLY.

Security (docs/SECURITY.md): READ-ONLY routes here; any mutation is orchestrated to the local
Elyon-Sol tools, never performed by a networked endpoint. Never bind 0.0.0.0. The UI is static
assets under glesac/webui/ served over the read-only /api/* routes.
"""
from __future__ import annotations
import os
from typing import Optional

from .config import Config
from . import status as _status
from . import decision_logs as _logs

try:
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
except Exception:  # pragma: no cover
    FastAPI = None

LOCALHOST = "127.0.0.1"
_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
_WEBUI_DIR = os.path.join(os.path.dirname(__file__), "webui")


def build_app(config: Optional[Config] = None):
    if FastAPI is None:
        raise RuntimeError("install glesac[server] deps (fastapi, uvicorn) to use `glesac run`.")
    cfg = config or Config.from_env()
    app = FastAPI(title="GLESAC - Gargoyles Ledge", docs_url="/api/docs")

    @app.get("/api/health")
    def health():
        return {"ok": True, "app": "glesac", "bind": LOCALHOST}

    @app.get("/api/status")
    def api_status(probe: bool = True):
        # probe=false: cheap local re-read (signed-record freshness + readiness), no node
        # network probes. The dashboard polls this on an interval to live-refresh the
        # freshness chip without repeatedly hitting the public nodes. Still GET-only.
        return _status.gather(cfg, probe=probe)

    @app.get("/api/logs")
    def api_logs(which: str = "issued", tail: int = 50, decision: Optional[str] = None):
        path = cfg.approval_log if which == "approvals" else cfg.issuance_log
        return {"which": which, "records": _logs.tail(path, tail, decision)}

    @app.get("/api/trace/{decision_sha256}")
    def api_trace(decision_sha256: str):
        return {"decision_sha256": decision_sha256,
                "timeline": _logs.trace_by_decision(cfg.issuance_log, cfg.approval_log, decision_sha256)}

    @app.get("/api/pending")
    def api_pending():
        # READ-ONLY view of the HIL queue. Approve/deny are NOT web routes (docs/SECURITY.md):
        # mutations run locally via `glesac pending --approve/--deny` -> approver_cli custody.
        from . import approvals as _appr
        view = _appr.pending_view(cfg)
        view["how_to_act"] = ("run locally: glesac pending --approve <approval_request_id> "
                              "(delegates to approver_cli) or --deny <id> --reason '...'")
        return view

    @app.get("/api/audit")
    def api_audit(tail: int = 50):
        # READ-ONLY view of the local console-audit log (operator approve/deny/runbook records).
        from . import approvals as _appr
        return {"records": _logs.tail(_appr.audit_path(), tail)}

    # static UI (glesac/webui/): /static/* assets + index.html at /
    if os.path.isdir(_WEBUI_DIR):
        app.mount("/static", StaticFiles(directory=_WEBUI_DIR), name="static")

    @app.get("/")
    def index():
        idx = os.path.join(_WEBUI_DIR, "index.html")
        if os.path.exists(idx):
            return FileResponse(idx)
        return {"app": "glesac", "note": "webui assets not found; API is at /api/*"}
    return app


def serve(host: str = LOCALHOST, port: int = 8181, config: Optional[Config] = None) -> None:
    """Start the console. host is FORCED to localhost - GLESAC does not expose a network server."""
    if host not in _LOCAL_HOSTS:
        raise ValueError("GLESAC binds localhost only (Option B / docs/SECURITY.md).")
    import uvicorn
    uvicorn.run(build_app(config), host=host, port=port)
