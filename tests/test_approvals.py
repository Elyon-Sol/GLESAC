"""P2 - HIL approval queue: pending detection, approve-by-delegation, deny-with-audit.

The load-bearing property: GLESAC surfaces and records but NEVER signs. Approve is a
delegation to approver_cli (local key custody); the console-cannot-mint-a-grant
revert-catchers live here and in test_cli.py.
"""
import json
import os
import subprocess
import sys

import pytest

from glesac import approvals, invoke

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
GOV_ISS = os.path.join(FIX, "gov_issuance.jsonl")
GOV_APP = os.path.join(FIX, "gov_approvals.jsonl")
PENDING_ID = "6c2496b29ecf45d59beeac0af2d64591"          # the un-granted hold in the fixture
PENDING_SHA = "cbc8dd56d1cda21c9cee1cabe7641a2650d396fccbddf017a534a97b06779551"


def test_pending_holds_are_requests_without_grant():
    holds = approvals.pending_holds(GOV_APP, GOV_ISS)
    assert [h["approval_request_id"] for h in holds] == [PENDING_ID]
    assert holds[0]["decision_sha256"] == PENDING_SHA
    # the granted request (fc9f92bf...) must NOT appear
    assert approvals.find_hold(holds, "fc9f92bf55a541eea9d6226b237ca88a") is None


def test_pending_enriched_with_issuance_context(tmp_path):
    iss = tmp_path / "iss.jsonl"
    app = tmp_path / "app.jsonl"
    iss.write_text(json.dumps({"decision_sha256": "d1", "target_url": "https://t.local/x",
                               "not_after": "2999-01-01T00:00:00Z", "decision": "ELIGIBLE"}) + "\n")
    app.write_text(json.dumps({"type": "approval_request", "decision_sha256": "d1",
                               "approval_request_id": "r1"}) + "\n")
    holds = approvals.pending_holds(str(app), str(iss))
    assert holds[0]["context"]["target_url"] == "https://t.local/x"
    assert holds[0]["context"]["decision"] == "ELIGIBLE"
    # tolerant of missing paths
    assert approvals.pending_holds(None) == []


def test_deny_records_reason_in_console_audit(tmp_path):
    audit = str(tmp_path / "audit" / "console_audit.jsonl")
    holds = approvals.pending_holds(GOV_APP, GOV_ISS)
    entry = approvals.deny(holds[0], "target not recognized", audit=audit)
    on_disk = [json.loads(l) for l in open(audit)]
    assert on_disk[-1]["action"] == "deny" and on_disk[-1]["reason"] == "target not recognized"
    assert on_disk[-1]["approval_request_id"] == PENDING_ID and entry["ts"]


def test_approve_delegates_to_approver_cli_and_audits(tmp_path, monkeypatch):
    """Approve = invoke approver_cli with the pending JSON on stdin. GLESAC passes the grant
    through and audits grant_id; the signing happened entirely in the (mocked) external tool."""
    audit = str(tmp_path / "console_audit.jsonl")
    seen = {}

    def fake_run(tool, args, *, input_text=None):
        seen["tool"], seen["args"], seen["stdin"] = tool, args, input_text
        grant = {"grant_id": "g-123", "approver_key_id": "approver-local-001",
                 "decision_sha256": PENDING_SHA, "approval_request_id": PENDING_ID}
        return subprocess.CompletedProcess([tool], 0, stdout=json.dumps(grant), stderr="")

    monkeypatch.setattr(approvals.invoke, "run", fake_run)
    holds = approvals.pending_holds(GOV_APP, GOV_ISS)
    grant = approvals.approve(holds[0], ttl=120, audit=audit)
    assert grant["grant_id"] == "g-123"
    assert seen["tool"] == "approver_cli" and "--yes" in seen["args"] and "120" in seen["args"]
    assert json.loads(seen["stdin"]) == {"decision_sha256": PENDING_SHA,
                                         "approval_request_id": PENDING_ID}
    rec = [json.loads(l) for l in open(audit)][-1]
    assert rec["action"] == "approve" and rec["grant_id"] == "g-123"


def test_approve_failure_is_audited_and_raises(tmp_path, monkeypatch):
    audit = str(tmp_path / "console_audit.jsonl")

    def failing_run(tool, args, *, input_text=None):
        return subprocess.CompletedProcess([tool], 2, stdout="", stderr="key env not set")

    monkeypatch.setattr(approvals.invoke, "run", failing_run)
    holds = approvals.pending_holds(GOV_APP, GOV_ISS)
    with pytest.raises(RuntimeError):
        approvals.approve(holds[0], audit=audit)
    rec = [json.loads(l) for l in open(audit)][-1]
    assert rec["action"] == "approve_error" and "key env" in rec["error"]


def test_cli_pending_lists_and_denies(tmp_path):
    env = dict(os.environ)
    env.update({"GLESAC_APPROVAL_LOG": GOV_APP, "GLESAC_ISSUANCE_LOG": GOV_ISS,
                "GLESAC_CONSOLE_AUDIT": str(tmp_path / "audit.jsonl")})
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "pending"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and PENDING_ID in r.stdout and "1 pending" in r.stderr
    r2 = subprocess.run([sys.executable, "-m", "glesac.cli", "pending",
                         "--deny", PENDING_ID, "--reason", "not ours"],
                        capture_output=True, text=True, env=env)
    assert r2.returncode == 0
    rec = [json.loads(l) for l in open(env["GLESAC_CONSOLE_AUDIT"])][-1]
    assert rec["action"] == "deny" and rec["reason"] == "not ours"


def test_cli_approve_cannot_mint_without_approver_cli_REVERT_CATCHER(tmp_path):
    """SoD, functional half: with NO approver_cli reachable (PATH stripped to the interpreter
    dir, ELYON_SOL_HOME unset), `glesac pending --approve --yes` must FAIL and emit no grant.
    If this ever starts succeeding, the console has grown a way to mint a grant - RED."""
    env = dict(os.environ)
    env.update({"GLESAC_APPROVAL_LOG": GOV_APP, "GLESAC_ISSUANCE_LOG": GOV_ISS,
                "GLESAC_CONSOLE_AUDIT": str(tmp_path / "audit.jsonl"),
                "PATH": os.path.dirname(sys.executable)})
    env.pop("ELYON_SOL_HOME", None)
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "pending",
                        "--approve", PENDING_ID, "--yes"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 3 and "approve failed" in r.stderr
    assert "grant_id" not in r.stdout                      # nothing grant-like was produced
    rec = [json.loads(l) for l in open(env["GLESAC_CONSOLE_AUDIT"])][-1]
    assert rec["action"] == "approve_error"                # the failure itself is audited


# ---- live gate /pending source (core read-endpoints, default-off on the gate) ----

GATE_PENDING = [{"type": "approval_request", "approval_request_id": PENDING_ID,
                 "decision_sha256": PENDING_SHA, "requested_at": "2026-07-04T22:00:00+00:00",
                 "target_url": "https://upstream.local/highimpact"}]


def test_pending_from_gate_normalizes_context(monkeypatch):
    monkeypatch.setattr(approvals, "_fetch_json", lambda url, timeout=3.0: list(GATE_PENDING))
    holds = approvals.pending_from_gate("http://gate.tunnel/pending")
    assert holds[0]["approval_request_id"] == PENDING_ID
    assert holds[0]["context"]["target_url"] == "https://upstream.local/highimpact"
    assert holds[0]["requested_at"].startswith("2026-07-04")
    assert approvals.pending_from_gate(None) is None       # unconfigured -> None


def test_pending_view_prefers_gate_and_falls_back_to_logs(monkeypatch):
    from glesac.config import Config
    cfg = Config(approval_log=GOV_APP, issuance_log=GOV_ISS,
                 gate_pending_url="http://gate.tunnel/pending")
    monkeypatch.setattr(approvals, "_fetch_json", lambda url, timeout=3.0: list(GATE_PENDING))
    v = approvals.pending_view(cfg)
    assert v["source"] == "gate" and len(v["pending"]) == 1
    # gate disabled/unreachable (404 -> None) -> log-derived fallback, same shape
    monkeypatch.setattr(approvals, "_fetch_json", lambda url, timeout=3.0: None)
    v2 = approvals.pending_view(cfg)
    assert v2["source"] == "logs"
    assert [h["approval_request_id"] for h in v2["pending"]] == [PENDING_ID]
    # no gate URL at all -> logs, no fetch attempted
    v3 = approvals.pending_view(Config(approval_log=GOV_APP, issuance_log=GOV_ISS))
    assert v3["source"] == "logs"
