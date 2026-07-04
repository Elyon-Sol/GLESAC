"""P3 - administration: AUDITED triggers for the existing Elyon-Sol runbooks. GLESAC adds
orchestration and the audit record, never the capability: every trigger is a whitelisted repo
script run locally by invocation (docs/SECURITY.md #2), confirmed by the local operator, and
appended to the console-audit log. There is no web route for any of this.

Key-material law: the rotation runbook writes the new key to a 0600 file and prints only
PUBLIC material. GLESAC REFUSES the runbook flag that would print secret material to stdout
(BLOCKED_FLAGS) so nothing secret can ever transit or be logged by this package - enforced by
a revert-catcher test.
"""
from __future__ import annotations
import subprocess
from typing import Dict, List, Optional

from . import invoke
from .approvals import audit_path, record_audit

BLOCKED_FLAGS = ("--print-private",)


def trigger(name: str, args: Optional[List[str]] = None, *,
            audit: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run one whitelisted runbook, audited. Raises on unknown name / blocked flag / missing
    runbook; the refusal or failure itself is audited too."""
    args = list(args or [])
    ap = audit_path(audit)
    for flag in args:
        if flag in BLOCKED_FLAGS:
            record_audit(ap, "runbook_refused", runbook=name, args=args,
                         reason=f"blocked flag {flag}: secret material must never transit GLESAC")
            raise ValueError(f"{flag} is blocked: secret material must never transit GLESAC.")
    try:
        cp = invoke.run_runbook(name, args)
    except (ValueError, FileNotFoundError) as e:
        record_audit(ap, "runbook_error", runbook=name, args=args, error=str(e))
        raise
    record_audit(ap, "runbook", runbook=name, args=args, returncode=cp.returncode)
    return cp
