# GLESAC design

See the originating design of record in the Elyon-Sol repo:
`docs/design/admin_console_KICKOFF.md`. Summary here; keep in sync.

## Operating model
An OPA-style toolkit: one `glesac` binary with subcommands, plus `glesac run` for a localhost
web console. Consumes Elyon-Sol BY INVOCATION (the installed CLIs), never by importing core
internals. See README for the subcommand map and `docs/SECURITY.md` for the invariants.

## Interface contract (what GLESAC depends on from Elyon-Sol)
1. CLIs: `envelope_inspector` (inspect/reevaluate/reconcile), `approver_cli` (make_grant).
2. JSONL log schemas: `JsonlIssuanceLog` (envelope-per-line) and `JsonlApprovalLog`
   (`approval_request` / `grant_consumed`).
3. Optional minimal read-only node endpoints (gate `GET /pending`, `GET /audit`) - added in the
   Elyon-Sol repo, default-off, tunnel-only.

## Build order
- **P0** - this design + the node read-endpoint spec + the HIL custody boundary.
- **P1** - read-only console + CLI shell (status, envelope review, action trace, reconcile,
  refusal analytics, decision-log viewer). Localhost-bound, no mutation, tests incl.
  revert-catchers.
- **P2** - HIL approval queue; approve via local `approver_cli`; revert-catcher proves GLESAC
  cannot mint a grant.
- **P3** - administration (rotation triggers to the existing local runbooks; audited).

Honest scope: operator capability, not a G5 referent; canon stays locked.
