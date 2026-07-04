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
- **P3 DONE** - administration: `glesac admin <runbook>` triggers the existing Elyon-Sol
  runbooks by invocation from a CLOSED whitelist (`rotate-publisher-key` ->
  `deploy/rotate_publisher_key.py`, `renew-certs` -> `deploy/tls/gen_certs.py`; resolved under
  `ELYON_SOL_HOME`). Mutation gate: operator must type the runbook name (or `--yes`); every
  trigger/refusal/failure is appended to the console-audit log; `glesac audit` + a read-only
  dashboard card view it (`/api/audit` - still GET-only, the no-mutating-routes catcher holds).
  Key-material law: the `--print-private` flag is REFUSED before invocation (revert-catcher,
  proven RED) so secret material can never transit GLESAC. Verified live: real rotation runbook
  run through the trigger - public key on stdout, new key in a 0600 file, audit recorded.
- **P3.1 DONE** - live HIL queue detail. The core SHIPPED the gate read-endpoints (`GET
  /pending`, `GET /audit?tail=N`; DEFAULT OFF, `ELYON_GATE_READ_ENDPOINTS=1`; hold records now
  carry `requested_at` + `target_url`). GLESAC consumes them: `pending_view` prefers the live
  gate `/pending` (`GLESAC_GATE_PENDING_URL`, over the operator tunnel) and falls back to the
  log-derived join on 404/unreachable - same record shape either way; CLI and card report the
  source. Card ergonomics: source badge, requested-at age, per-row copy-ready approve command.
  Verified live both ways (flag on -> source: gate with context; flag off -> 404 -> logs).
- **No scheduled phase after P3.1.** Backlog candidates (build only when needed): consume gate
  `/audit` for a remote-log view; local session token for shared boxes (DESIGN section 5).

## Visual overview

`docs/overview.svg` - the P3 communication & configuration map (trust boundary, invocation vs
read vs network legs, env vars). Update it if the gate `/pending`,`/audit`
read-endpoints are ever consumed.

## Interface contract (all GLESAC depends on from Elyon-Sol)

1. CLIs by invocation: `envelope_inspector` (inspect/reevaluate/reconcile), `approver_cli`.
   Point at them with `ELYON_SOL_HOME` or PATH.
1b. Gate read-endpoints (OPTIONAL, default-off on the gate): `GET /pending` (held-not-consumed
   with public context), `GET /audit?tail=N`. Gate enables with `ELYON_GATE_READ_ENDPOINTS=1`;
   GLESAC points at them with `GLESAC_GATE_PENDING_URL` and degrades to pulled logs when absent.
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
  `GLESAC_SIGNED_RECORD`, `GLESAC_CONSOLE_AUDIT`, `GLESAC_{GATE,TARGET,AUTHZ,PUB}_URL`, `GLESAC_GATE_PENDING_URL`,
  `ELYON_SOL_HOME`.
- **Opt-in live-node check:** `GLESAC_LIVE_NODES=1 python -m pytest -q` additionally runs the
  live-node smoke tests (`tests/test_live_nodes.py`, the 2 default skips) against whatever node
  URLs are configured. Default suite stays hermetic - fixtures only, no network.
- **Mount hazard (Cowork sandbox only):** host file-tool writes to this folder truncate
  intermittently. When editing via the sandbox, write files through bash and verify byte counts
  + `ast.parse`. Native (laptop) editing is unaffected.
- **Tests:** `pip install -e . && python -m pytest -q` (or `python -m glesac.cli ...`).

## Resume in one line

Read this file + `docs/DESIGN.md` + `docs/SECURITY.md`, run the tests green (38 passed,
2 skipped). P0-P3 are DONE; there is no scheduled next phase - pick up from the backlog
candidates above only when a real need arrives.
