"""`glesac run` - the local web console. FastAPI app, bound to 127.0.0.1 ONLY.

Security (docs/SECURITY.md): READ-ONLY routes here; any mutation is orchestrated to the local
Elyon-Sol tools, never performed by a networked endpoint. Never bind 0.0.0.0.
"""
from __future__ import annotations
from typing import Optional

from .config import Config
from . import status as _status
from . import decision_logs as _logs

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
except Exception:  # pragma: no cover
    FastAPI = None

LOCALHOST = "127.0.0.1"
_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def build_app(config: Optional[Config] = None):
    if FastAPI is None:
        raise RuntimeError("install glesac[server] deps (fastapi, uvicorn) to use `glesac run`.")
    cfg = config or Config.from_env()
    app = FastAPI(title="GLESAC - Gargoyles Ledge", docs_url="/api/docs")

    @app.get("/api/health")
    def health():
        return {"ok": True, "app": "glesac", "bind": LOCALHOST}

    @app.get("/api/status")
    def api_status():
        return _status.gather(cfg)

    @app.get("/api/logs")
    def api_logs(which: str = "issued", tail: int = 50, decision: Optional[str] = None):
        path = cfg.approval_log if which == "approvals" else cfg.issuance_log
        return {"which": which, "records": _logs.tail(path, tail, decision)}

    @app.get("/api/trace/{decision_sha256}")
    def api_trace(decision_sha256: str):
        return {"decision_sha256": decision_sha256,
                "timeline": _logs.trace_by_decision(cfg.issuance_log, cfg.approval_log, decision_sha256)}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return _DASHBOARD_HTML
    return app


def serve(host: str = LOCALHOST, port: int = 8181, config: Optional[Config] = None) -> None:
    """Start the console. host is FORCED to localhost - GLESAC does not expose a network server."""
    if host not in _LOCAL_HOSTS:
        raise ValueError("GLESAC binds localhost only (Option B / docs/SECURITY.md).")
    import uvicorn
    uvicorn.run(build_app(config), host=host, port=port)


_DASHBOARD_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>GLESAC - Gargoyles Ledge</title>
<style>
 body{font-family:ui-monospace,Consolas,monospace;background:#0a0e14;color:#e8edf6;margin:0;padding:20px}
 h1{font-size:1.2rem;color:#57d0a3} h2{font-size:.95rem;color:#66b2ff;margin-top:22px}
 .card{background:#121926;border:1px solid #22304a;border-radius:10px;padding:14px 16px;margin:10px 0}
 pre{white-space:pre-wrap;font-size:.8rem;margin:0} input,select{background:#0e131c;color:#e8edf6;border:1px solid #2c3d5c;border-radius:6px;padding:6px}
 .muted{color:#9aa7bd}
</style></head><body>
<h1>GLESAC &middot; Gargoyles Ledge <span class="muted">(local operator console &mdash; 127.0.0.1)</span></h1>
<div class="card"><h2>Node status &amp; readiness</h2><pre id="status">loading...</pre></div>
<div class="card"><h2>Decision logs</h2>
 <div class="muted">which:
   <select id="which"><option value="issued">issued</option><option value="approvals">approvals</option></select>
   tail: <input id="tail" type="number" value="25" style="width:70px"> <button onclick="loadLogs()">refresh</button></div>
 <pre id="logs">loading...</pre></div>
<div class="card"><h2>Action trace</h2>
 <div class="muted">decision_sha256: <input id="sha" size="40"> <button onclick="loadTrace()">trace</button></div>
 <pre id="trace" class="muted">enter a decision_sha256</pre></div>
<script>
var NL=String.fromCharCode(10);
async function j(u){const r=await fetch(u);return r.json()}
async function loadStatus(){document.getElementById('status').textContent=JSON.stringify(await j('/api/status'),null,2)}
async function loadLogs(){const w=document.getElementById('which').value,t=document.getElementById('tail').value;
 const d=await j('/api/logs?which='+w+'&tail='+t);
 document.getElementById('logs').textContent=d.records.map(r=>JSON.stringify(r)).join(NL)||'(no records)'}
async function loadTrace(){const s=document.getElementById('sha').value.trim();if(!s)return;
 const d=await j('/api/trace/'+encodeURIComponent(s));
 document.getElementById('trace').textContent=d.timeline.map(e=>e.stage+': '+JSON.stringify(e)).join(NL)||'(no events)'}
loadStatus();loadLogs();
</script></body></html>"""
