import os
import pytest
from glesac import server
from glesac.config import Config

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
CFG = Config(issuance_log=os.path.join(FIX, "issuance.jsonl"),
             approval_log=os.path.join(FIX, "approvals.jsonl"),
             readiness=os.path.join(FIX, "readiness.json"),
             signed_record=os.path.join(FIX, "signed_record_fresh.json"))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def _client():
    return TestClient(server.build_app(CFG))


def test_health_and_dashboard():
    c = _client()
    assert c.get("/api/health").json()["ok"] is True
    assert "GLESAC" in c.get("/").text


def test_status_and_logs_routes_read_fixtures():
    c = _client()
    st = c.get("/api/status").json()
    assert st["readiness"]["DEFAULT_SECURE"] is True and st["signed_record"]["fresh"] is True
    logs = c.get("/api/logs?which=issued&tail=1").json()
    assert logs["records"][0]["decision_sha256"] == "bbb222"


def test_trace_route():
    tl = _client().get("/api/trace/aaa111").json()["timeline"]
    assert [e["stage"] for e in tl] == ["issued", "approval_request", "grant_consumed"]


def test_serve_binds_localhost_only_REVERT_CATCHER():
    """GLESAC must never expose a network server. serve() must reject any non-localhost host.

    Revert-catcher: if the localhost guard in serve() is removed, this test goes RED. It asserts
    the guard fires BEFORE uvicorn is imported/started, so no socket is ever opened on 0.0.0.0.
    """
    for bad in ("0.0.0.0", "10.0.0.5", ""):
        with pytest.raises(ValueError):
            server.serve(host=bad)


def test_static_ui_assets_serve():
    """The web UI is static assets (glesac/webui/), not an inline string."""
    c = _client()
    assert c.get("/").status_code == 200 and "GLESAC" in c.get("/").text
    js = c.get("/static/app.js"); assert js.status_code == 200 and "loadStatus" in js.text
    assert c.get("/static/style.css").status_code == 200
