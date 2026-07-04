"""GLESAC CLI - OPA-style subcommands. Most REUSE the installed Elyon-Sol tools by invocation."""
from __future__ import annotations
import argparse, sys
from . import __version__
from . import invoke


def _passthrough(tool: str, subcmd: str, rest):
    cp = invoke.run(tool, [subcmd, *rest])
    sys.stdout.write(cp.stdout)
    sys.stderr.write(cp.stderr)
    return cp.returncode


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="glesac", description="Gargoyles Ledge - Elyon-Sol Administrative Console")
    p.add_argument("--version", action="version", version=f"glesac {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # envelope review (-> envelope_inspector) - READ-ONLY
    for name in ("inspect", "reevaluate", "reconcile"):
        sp = sub.add_parser(name, help=f"{name} (envelope_inspector)")
        sp.add_argument("rest", nargs=argparse.REMAINDER)

    # HIL approval (-> approver_cli) - LOCAL key custody; GLESAC never signs
    sp = sub.add_parser("approve", help="HIL: sign an approval grant locally (approver_cli)")
    sp.add_argument("rest", nargs=argparse.REMAINDER)

    # status / logs / run - GLESAC-native (P1)
    sub.add_parser("status", help="node health + readiness predicates (TODO P1)")
    lp = sub.add_parser("logs", help="tail/query the JSONL decision logs (TODO P1)")
    lp.add_argument("--issued"); lp.add_argument("--approvals")
    rp = sub.add_parser("run", help="start the localhost web console (127.0.0.1 only)")
    rp.add_argument("--port", type=int, default=8181)

    a = p.parse_args(argv)
    if a.cmd in ("inspect", "reevaluate", "reconcile"):
        return _passthrough("envelope_inspector", a.cmd, a.rest)
    if a.cmd == "approve":
        # Delegates to approver_cli, which holds the approver PRIVATE key in local custody.
        return _passthrough("approver_cli", "", a.rest) if False else _run_approve(a.rest)
    if a.cmd == "status":
        print("TODO P1: node status board (health, cert expiry, signed-record freshness, readiness).")
        return 0
    if a.cmd == "logs":
        print("TODO P1: decision-log tail/query. See glesac/decision_logs.py.")
        return 0
    if a.cmd == "run":
        from . import server
        server.serve(port=a.port)
        return 0
    return 1


def _run_approve(rest):
    # approver_cli takes flags (not a subcommand); pass through directly.
    cp = invoke.run("approver_cli", list(rest))
    sys.stdout.write(cp.stdout); sys.stderr.write(cp.stderr)
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
