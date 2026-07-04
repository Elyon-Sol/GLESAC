"""GLESAC CLI - OPA-style subcommands. Most REUSE the installed Elyon-Sol tools by invocation."""
from __future__ import annotations
import argparse, json, sys
from . import __version__
from . import invoke
from .config import Config


def _passthrough(tool: str, subcmd: str, rest):
    cp = invoke.run(tool, ([subcmd] if subcmd else []) + list(rest))
    sys.stdout.write(cp.stdout)
    sys.stderr.write(cp.stderr)
    return cp.returncode


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="glesac", description="Gargoyles Ledge - Elyon-Sol Administrative Console")
    p.add_argument("--version", action="version", version=f"glesac {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name in ("inspect", "reevaluate", "reconcile"):
        sp = sub.add_parser(name, help=f"{name} (envelope_inspector)")
        sp.add_argument("rest", nargs=argparse.REMAINDER)

    sp = sub.add_parser("approve", help="HIL: sign an approval grant locally (approver_cli)")
    sp.add_argument("rest", nargs=argparse.REMAINDER)

    st = sub.add_parser("status", help="node health + record freshness + readiness")
    st.add_argument("--no-probe", action="store_true", help="skip live node probes")
    lp = sub.add_parser("logs", help="tail/query the JSONL decision logs")
    lp.add_argument("--which", choices=("issued", "approvals"), default="issued")
    lp.add_argument("--tail", type=int, default=50)
    lp.add_argument("--decision", help="filter to one decision_sha256")
    lp.add_argument("--issued"); lp.add_argument("--approvals")
    tr = sub.add_parser("trace", help="one action's timeline joined on decision_sha256")
    tr.add_argument("decision_sha256")
    pd = sub.add_parser("pending", help="HIL queue: list pending 202 holds; approve/deny locally")
    pd.add_argument("--approve", metavar="APPROVAL_REQUEST_ID",
                    help="delegate approval to approver_cli (approver key stays in local custody)")
    pd.add_argument("--deny", metavar="APPROVAL_REQUEST_ID",
                    help="record a deny (with --reason) in the local console-audit log")
    pd.add_argument("--reason", help="reason for the deny (required with --deny)")
    pd.add_argument("--ttl", type=int, default=300, help="grant lifetime in seconds (approve)")
    pd.add_argument("--yes", action="store_true", help="skip the confirm prompt (approve)")
    rp = sub.add_parser("run", help="start the localhost web console (127.0.0.1 only)")
    rp.add_argument("--port", type=int, default=8181)

    a = p.parse_args(argv)
    if a.cmd in ("inspect", "reevaluate", "reconcile"):
        return _passthrough("envelope_inspector", a.cmd, a.rest)
    if a.cmd == "approve":
        # Delegates to approver_cli, which holds the approver key in local custody. GLESAC never signs.
        return _passthrough("approver_cli", "", a.rest)
    if a.cmd == "status":
        from . import status as _status
        print(json.dumps(_status.gather(Config.from_env(), probe=not a.no_probe), indent=2))
        return 0
    if a.cmd == "logs":
        from . import decision_logs as _logs
        cfg = Config.from_env(issuance_log=a.issued, approval_log=a.approvals)
        path = cfg.approval_log if a.which == "approvals" else cfg.issuance_log
        if not path:
            sys.stderr.write("no log path (set GLESAC_ISSUANCE_LOG/GLESAC_APPROVAL_LOG or --issued/--approvals)\n")
            return 2
        for rec in _logs.tail(path, a.tail, a.decision):
            print(json.dumps(rec))
        return 0
    if a.cmd == "trace":
        from . import decision_logs as _logs
        cfg = Config.from_env()
        for e in _logs.trace_by_decision(cfg.issuance_log, cfg.approval_log, a.decision_sha256):
            rest = {k: v for k, v in e.items() if k != "stage"}
            print(f"{e.get('stage'):16} {json.dumps(rest)}")
        return 0
    if a.cmd == "pending":
        # HIL queue (P2). The human decides here; the GRANT is signed by approver_cli with the
        # approver key in LOCAL custody - GLESAC delegates and records, it never signs (SoD).
        from . import approvals as _appr
        cfg = Config.from_env()
        holds = _appr.pending_holds(cfg.approval_log, cfg.issuance_log)
        if not a.approve and not a.deny:
            for h in holds:
                print(json.dumps(h))
            sys.stderr.write(f"{len(holds)} pending hold(s)\n")
            return 0
        rid = a.approve or a.deny
        hold = _appr.find_hold(holds, rid)
        if hold is None:
            sys.stderr.write(f"no pending hold with approval_request_id={rid}\n")
            return 2
        if a.deny:
            if not a.reason:
                sys.stderr.write("--deny requires --reason\n")
                return 2
            print(json.dumps(_appr.deny(hold, a.reason)))
            return 0
        sys.stderr.write("About to APPROVE a held high-impact decision (delegated to approver_cli):\n"
                         f"  decision_sha256     : {hold.get('decision_sha256')}\n"
                         f"  approval_request_id : {hold.get('approval_request_id')}\n"
                         f"  context             : {json.dumps(hold.get('context', {}))}\n")
        if not a.yes:
            sys.stderr.write("Type 'approve' to delegate: ")
            sys.stderr.flush()
            if sys.stdin.readline().strip() != "approve":
                sys.stderr.write("aborted (nothing delegated)\n")
                return 1
        try:
            grant = _appr.approve(hold, ttl=a.ttl)
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            sys.stderr.write(f"approve failed: {e}\n")
            return 3
        print(json.dumps(grant))
        sys.stderr.write("grant emitted by approver_cli; present it to the gate "
                         "(X-Elyon-Sol-Approval-Grant).\n")
        return 0
    if a.cmd == "run":
        from . import server
        server.serve(port=a.port, config=Config.from_env())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
