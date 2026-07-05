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


def test_status_probe_false_skips_node_probes_but_keeps_freshness():
    """The dashboard polls /api/status?probe=0 on an interval to live-refresh the signed-record
    freshness chip cheaply. probe=false must NOT run node network probes (empty nodes map) while
    still returning the recomputed signed-record freshness + readiness. Still GET-only."""
    c = _client()
    st = c.get("/api/status?probe=0").json()
    assert st["nodes"] == {}
    assert st["signed_record"]["fresh"] is True
    assert st["readiness"]["DEFAULT_SECURE"] is True


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


def test_index_content_hashes_asset_urls():
    """The dashboard HTML must reference app.js/style.css with a content-hash
    ?v= query so a rebuilt UI is never served stale from browser cache."""
    c = _client()
    html = c.get("/").text
    assert "/static/app.js?v=" in html and "/static/style.css?v=" in html


def test_static_assets_are_no_store():
    """Local console must not serve a stale cached UI: every response carries
    Cache-Control: no-store so a rebuilt app.js/style.css is always fetched."""
    c = _client()
    assert c.get("/static/app.js").headers.get("cache-control") == "no-store"
    assert c.get("/").headers.get("cache-control") == "no-store"


def test_ui_click_to_detail_present():
    """request / decision / subject cells are clickable to a READ-ONLY detail
    panel (GET-only; no new web route - the no-mutating-routes catcher holds)."""
    c = _client()
    js = c.get("/static/app.js").text
    assert "openDetail" in js and "maybeLinkTd" in js
    assert "trace this decision" in js  # decision cells wire to the trace view
    assert '"stage link"' in js          # trace timeline entries are clickable too
    assert 'id="detail-overlay"' in c.get("/").text

def test_pending_route_lists_ungranted_holds():
    """/api/pending is the READ-ONLY dashboard feed for the P2 HIL queue card."""
    gov = Config(issuance_log=os.path.join(FIX, "gov_issuance.jsonl"),
                 approval_log=os.path.join(FIX, "gov_approvals.jsonl"))
    d = TestClient(server.build_app(gov)).get("/api/pending").json()
    ids = [h["approval_request_id"] for h in d["pending"]]
    assert ids == ["6c2496b29ecf45d59beeac0af2d64591"] and "glesac pending" in d["how_to_act"]
    # the simple fixture set has no un-granted hold -> empty queue, no error
    assert _client().get("/api/pending").json()["pending"] == []


def test_no_mutating_web_routes_REVERT_CATCHER():
    """SoD/local-mutation law (docs/SECURITY.md #2): the web console NEVER exposes a route
    that mutates - approve/deny/rotation run locally via the CLIs. If anyone adds a POST/PUT/
    DELETE/PATCH route (e.g. a web 'approve' button that acts), this goes RED."""
    app = server.build_app(CFG)
    for r in app.routes:
        methods = getattr(r, "methods", None) or set()
        assert not (set(methods) - {"GET", "HEAD"}), f"mutating route: {r.path} {methods}"
