# GLESAC - progress & state (read this first on any new session)

Self-describing state so a fresh session (or a new collaborator) resumes from the REPO, not from
memory or a prior chat. Keep it short and current. Authoritative design: `docs/DESIGN.md`;
security law: `docs/SECURITY.md`.

## What GLESAC is (one paragraph)

Gargoyles Ledge (GLESAC) - the Elyon-Sol Administrative Console. An OPA-style, LOCAL-FIRST
operator toolkit for an Elyon-Sol admission-gate deployment: a `glesac` CLI plus a `glesac run`
localhost web console. It CONSUMES Elyon-Sol by INVOCATION (the installed CLIs) - never by
importing core internals. Proprietary, private repo.

## Decisions on record (do not silently reverse)

- **Option B, local-first** (not a networked admin server). `glesac run` binds `127.0.0.1` only.
  The networked multi-operator API (Option A) is DEFERRED until multiple/remote operators or a
  product surface require it.
- **OPA-toolkit ergonomics** (`glesac <subcommand>` + `glesac run`), stricter security posture
  (localhost-only, local-custody HIL). OPA is the shape, not the network posture.
- **Consume Elyon-Sol by invocation** (`envelope_inspector`, `approver_cli` CLIs + read the JSONL
  logs), never by import. Keeps the repos decoupled and "no re-implementation" true.
- **Proprietary + private.** LICENSE is all-rights-reserved.
- **HIL preserves SoD:** GLESAC contains NO signing primitive; the approver key stays in local
  custody and grants are signed by `approver_cli`. Enforced by a package-wide revert-catcher test.
- **GLESAC is NEVER referenced in the public Elyon-Sol repo.** One-directional coupling.

## Phase status

- **P0 DONE** - design (`docs/DESIGN.md`), proprietary license.
- **P1 DONE** - read-only console + CLI: `status`, `logs`, `trace`, `run` (localhost web
  dashboard); config via env; fixtures + tests. Reads the real Elyon-Sol `readiness.json`
  (`deployment_predicates` + `capabilities`) and the JSONL decision logs.
- **P2 DONE** - HIL approval queue: `glesac pending` + dashboard card surface `approval_request`
  records with no matching `grant_consumed`; approve DELEGATES to the local `approver_cli`
  (pending JSON on stdin, `--yes --ttl`; key custody stays in the approver's env -
  `ELYON_APPROVER_KEY_HEX`/`_ID` - GLESAC never signs); deny records a reason to the local
  console-audit log (`GLESAC_CONSOLE_AUDIT`, default `~/.glesac/console_audit.jsonl`).
  Revert-catchers extended and proven RED-on-revert: signing-primitive scan now covers
  `build_grant`/`hazmat`/etc. + the webui and bans crypto imports package-wide; a functional
  catcher proves `pending --approve` cannot mint a grant without `approver_cli`; a server
  catcher fails on any non-GET web route (mutations are CLI-only, never a web route).
  Verified live end-to-end against `run_local_governance.py` logs with the real `approver_cli`.
- **P3 NEXT** - administration (rotation triggers to the existing local runbooks; audited).

## Visual overview

`docs/overview.svg` - the P2 communication & configuration map (trust boundary, invocation vs
read vs network legs, env vars). Update it when P3 adds legs (rotation runbooks; gate
`/pending`,`/audit` read-endpoints if/when the core ships them).

## Interface contract (all GLESAC depends on from Elyon-Sol)

1. CLIs by invocation: `envelope_inspector` (inspect/reevaluate/reconcile), `approver_cli`.
   Point at them with `ELYON_SOL_HOME` or PATH.
2. JSONL schemas: issuance log (one envelope/line; `decision_sha256` top-level) and approval log
   (`approval_request` / `grant_consumed`, keyed by `decision_sha256` + `approval_request_id`).
3. Readiness JSON: `deployment_predicates` (DEFAULT_SECURE/END_TO_END_NO_SHORTCUT/ROOT_RECOVERY/
   REAL_TRANSPORT with a `green` flag) + `capabilities`.
Real-shape fixtures live in `tests/fixtures/` (`gov_issuance.jsonl`, `gov_approvals.jsonl`,
`readiness_real.json`) so GLESAC builds and tests WITHOUT Elyon-Sol present.

## Dev workflow notes

- **Getting live data:** Elyon-Sol ships `deploy/governance/local_demo/run_local_governance.py`
  - a single-box driver that runs the real 202->approve->consume flow and writes real
  issuance/approval logs. Point GLESAC at those (`GLESAC_ISSUANCE_LOG` / `GLESAC_APPROVAL_LOG`).
- **Config env vars:** `GLESAC_ISSUANCE_LOG`, `GLESAC_APPROVAL_LOG`, `GLESAC_READINESS`,
  `GLESAC_SIGNED_RECORD`, `GLESAC_CONSOLE_AUDIT`, `GLESAC_{GATE,TARGET,AUTHZ,PUB}_URL`,
  `ELYON_SOL_HOME`.
- **Opt-in live-node check:** `GLESAC_LIVE_NODES=1 python -m pytest -q` additionally runs the
  live-node smoke tests (`tests/test_live_nodes.py`, the 2 default skips) against whatever node
  URLs are configured. Default suite stays hermetic - fixtures only, no network.
- **Mount hazard (Cowork sandbox only):** host file-tool writes to this folder truncate
  intermittently. When editing via the sandbox, write files through bash and verify byte counts
  + `ast.parse`. Native (laptop) editing is unaffected.
- **Tests:** `pip install -e . && python -m pytest -q` (or `python -m glesac.cli ...`).

## Resume in one line

Read this file + `docs/DESIGN.md` + `docs/SECURITY.md`, run the tests green (28 passed,
2 skipped), then continue at the "P3 NEXT" item above.
