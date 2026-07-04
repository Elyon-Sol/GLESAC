"""`glesac run` - the local web console. FastAPI app, bound to 127.0.0.1 ONLY.

Security (docs/SECURITY.md): read-only routes here; any mutation is orchestrated to the local
Elyon-Sol tools, never performed by a networked endpoint. Never bind 0.0.0.0. P1 fills the read
routes (status, envelope review, action trace, reconcile, refusal analytics, audit viewer).
"""
from __future__ import annotations

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover - fastapi optional until `glesac run` is used
    FastAPI = None

LOCALHOST = "127.0.0.1"


def build_app():
    if FastAPI is None:
        raise RuntimeError("install glesac[server] deps (fastapi, uvicorn) to use `glesac run`.")
    app = FastAPI(title="GLESAC - Gargoyles Ledge", docs_url="/api/docs")

    @app.get("/api/health")
    def health():
        return {"ok": True, "app": "glesac", "bind": LOCALHOST}

    # TODO P1: /api/status, /api/envelope/{sha}, /api/trace/{sha}, /api/reconcile,
    # /api/refusals, /api/audit  (all READ-ONLY). TODO P2: /api/pending (read) + a LOCAL
    # approve action that shells to approver_cli. UI is served over these.
    return app


def serve(host: str = LOCALHOST, port: int = 8181) -> None:
    """Start the console. host is forced to localhost - GLESAC does not expose a network server."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("GLESAC binds localhost only (Option B / docs/SECURITY.md).")
    import uvicorn
    uvicorn.run(build_app(), host=host, port=port)
