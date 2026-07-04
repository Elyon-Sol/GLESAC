"""P2 - the HIL approval queue (pending 202 holds), read + orchestrate, NEVER sign.

A "pending hold" is an `approval_request` record in the approval log with no matching
`grant_consumed` (keyed by decision_sha256 + approval_request_id). GLESAC surfaces them
(`glesac pending`, dashboard card) and orchestrates the human decision:

- APPROVE: delegate to the installed `approver_cli` (by invocation, stdin = the pending JSON).
  The approver key stays in LOCAL CUSTODY with approver_cli; GLESAC contains no signing
  primitive and cannot mint a grant (SoD, [FIX H5] - enforced by the revert-catcher tests).
- DENY: no core-side action exists to perform (the hold simply expires unconsumed); GLESAC
  records the operator's decision + reason in the local console-audit log.

Every operator decision is appended to the console-audit log (JSONL, local file).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import decision_logs as _logs
from . import invoke

DEFAULT_AUDIT = os.path.join(os.path.expanduser("~"), ".glesac", "console_audit.jsonl")


def pending_holds(approval_path: Optional[str], issuance_path: Optional[str] = None) -> List[Dict]:
    """approval_request records with no matching grant_consumed, enriched (when the decision
    appears in the issuance log) with public decision context: target_url, not_after, decision."""
    recs = _logs.records(approval_path)
    granted = {(r.get("decision_sha256"), r.get("approval_request_id"))
               for r in recs if r.get("type") == "grant_consumed"}
    envelopes: Dict[str, Dict] = {}
    for env in _logs.records(issuance_path):
        d = env.get("decision_sha256") or (env.get("decision") or {}).get("decision_sha256")
        if isinstance(d, str):
            envelopes[d] = env
    out: List[Dict] = []
    for r in recs:
        if r.get("type") != "approval_request":
            continue
        if (r.get("decision_sha256"), r.get("approval_request_id")) in granted:
            continue
        item = dict(r)
        env = envelopes.get(r.get("decision_sha256") or "")
        if env:
            item["context"] = {k: env.get(k) for k in ("target_url", "not_after", "decision")
                               if env.get(k) is not None}
        out.append(item)
    return out


def find_hold(holds: List[Dict], approval_request_id: str) -> Optional[Dict]:
    for h in holds:
        if h.get("approval_request_id") == approval_request_id:
            return h
    return None


def audit_path(configured: Optional[str] = None) -> str:
    return configured or os.environ.get("GLESAC_CONSOLE_AUDIT") or DEFAULT_AUDIT


def record_audit(path: str, action: str, **fields) -> Dict:
    """Append one operator decision to the local console-audit log (JSONL). Local file only -
    this is GLESAC's own record of what the human decided; it never touches the core logs."""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "action": action, **fields}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def approve(hold: Dict, *, ttl: int = 300, audit: Optional[str] = None) -> Dict:
    """Delegate the approval to `approver_cli` (LOCAL custody; GLESAC never signs).

    Feeds the pending JSON ({decision_sha256, approval_request_id}) to approver_cli on stdin
    with --yes (the human already confirmed to GLESAC). approver_cli reads the approver key
    from ITS environment/custody and emits the signed grant on stdout; GLESAC passes that
    grant through to the operator and records grant_id (public) in the console audit."""
    pending_json = json.dumps({"decision_sha256": hold.get("decision_sha256"),
                               "approval_request_id": hold.get("approval_request_id")})
    ap = audit_path(audit)
    try:
        cp = invoke.run("approver_cli", ["--yes", "--ttl", str(int(ttl))], input_text=pending_json)
    except FileNotFoundError as e:
        record_audit(ap, "approve_error", approval_request_id=hold.get("approval_request_id"),
                     decision_sha256=hold.get("decision_sha256"), error=str(e))
        raise
    if cp.returncode != 0:
        record_audit(ap, "approve_error", approval_request_id=hold.get("approval_request_id"),
                     decision_sha256=hold.get("decision_sha256"),
                     error=(cp.stderr or "").strip()[-500:])
        raise RuntimeError(f"approver_cli failed (rc={cp.returncode}): {(cp.stderr or '').strip()}")
    grant = json.loads(cp.stdout)
    record_audit(ap, "approve", approval_request_id=hold.get("approval_request_id"),
                 decision_sha256=hold.get("decision_sha256"),
                 grant_id=grant.get("grant_id"), approver_key_id=grant.get("approver_key_id"))
    return grant


def deny(hold: Dict, reason: str, *, audit: Optional[str] = None) -> Dict:
    """Record the operator's DENY + reason locally. There is no core mutation to perform:
    an unconsumed hold simply expires at the gate. The console audit is the record."""
    return record_audit(audit_path(audit), "deny",
                        approval_request_id=hold.get("approval_request_id"),
                        decision_sha256=hold.get("decision_sha256"), reason=reason)
