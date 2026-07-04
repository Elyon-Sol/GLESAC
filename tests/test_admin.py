"""P3 - administration: whitelisted, confirmed, AUDITED runbook triggers. Load-bearing
properties: only whitelisted runbooks run; the secret-printing flag is structurally refused;
every trigger/refusal/failure lands in the console-audit log; no admin web route exists
(covered by the all-GET catcher in test_server.py)."""
import json
import os
import subprocess
import sys

import pytest

from glesac import admin, invoke


def _audit_recs(path):
    return [json.loads(l) for l in open(path)]


def test_runbook_whitelist_is_closed():
    assert set(invoke.RUNBOOKS) == {"rotate-publisher-key", "renew-certs"}
    with pytest.raises(ValueError):
        invoke.run_runbook("../../evil", [])
    with pytest.raises(ValueError):
        invoke.run_runbook("rm-rf", [])


def test_trigger_unknown_runbook_is_audited_and_refused(tmp_path):
    audit = str(tmp_path / "audit.jsonl")
    with pytest.raises(ValueError):
        admin.trigger("not-a-runbook", [], audit=audit)
    rec = _audit_recs(audit)[-1]
    assert rec["action"] == "runbook_error" and "not-a-runbook" in rec["error"]


def test_secret_flag_is_blocked_REVERT_CATCHER(tmp_path, monkeypatch):
    """Key-material law: the flag that would print SECRET material to stdout must be refused
    BEFORE any invocation, so secrets can never transit GLESAC. If BLOCKED_FLAGS or the check
    is ever removed, this goes RED."""
    audit = str(tmp_path / "audit.jsonl")
    ran = []
    monkeypatch.setattr(admin.invoke, "run_runbook", lambda n, a: ran.append(n))
    with pytest.raises(ValueError):
        admin.trigger("rotate-publisher-key", ["--print-private"], audit=audit)
    assert ran == []                                   # refused before any invocation
    rec = _audit_recs(audit)[-1]
    assert rec["action"] == "runbook_refused" and "--print-private" in str(rec["args"])
    assert admin.BLOCKED_FLAGS                          # the blocklist itself must exist


def test_trigger_runs_whitelisted_runbook_and_audits(tmp_path, monkeypatch):
    audit = str(tmp_path / "audit.jsonl")
    seen = {}

    def fake_runbook(name, args):
        seen["name"], seen["args"] = name, args
        return subprocess.CompletedProcess(["python"], 0, stdout="=== ok ===", stderr="")

    monkeypatch.setattr(admin.invoke, "run_runbook", fake_runbook)
    cp = admin.trigger("renew-certs", ["extra.host"], audit=audit)
    assert cp.returncode == 0 and seen == {"name": "renew-certs", "args": ["extra.host"]}
    rec = _audit_recs(audit)[-1]
    assert rec["action"] == "runbook" and rec["runbook"] == "renew-certs" and rec["returncode"] == 0


def test_cli_admin_requires_exact_confirmation(tmp_path):
    """Mutation gate: without --yes, the operator must type the runbook name. Wrong input ->
    abort, rc 1, NOTHING run and nothing audited as a runbook action."""
    env = dict(os.environ)
    env["GLESAC_CONSOLE_AUDIT"] = str(tmp_path / "audit.jsonl")
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "admin", "rotate-publisher-key"],
                       capture_output=True, text=True, env=env, input="no\n")
    assert r.returncode == 1 and "aborted" in r.stderr
    assert not os.path.exists(env["GLESAC_CONSOLE_AUDIT"])


def test_cli_admin_unknown_runbook_rejected():
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "admin", "evil-script", "--yes"],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "unknown runbook" in r.stderr


def test_cli_admin_fails_cleanly_without_core_home(tmp_path):
    env = dict(os.environ)
    env["GLESAC_CONSOLE_AUDIT"] = str(tmp_path / "audit.jsonl")
    env.pop("ELYON_SOL_HOME", None)
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "admin", "renew-certs", "--yes"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 3 and "admin failed" in r.stderr
    rec = _audit_recs(env["GLESAC_CONSOLE_AUDIT"])[-1]
    assert rec["action"] == "runbook_error"


def test_cli_audit_lists_the_console_log(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(json.dumps({"ts": "2026-07-04T00:00:00+00:00", "action": "deny",
                                 "approval_request_id": "r1", "reason": "test"}) + "\n")
    env = dict(os.environ)
    env["GLESAC_CONSOLE_AUDIT"] = str(audit)
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "audit", "--tail", "10"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and '"deny"' in r.stdout and "r1" in r.stdout
