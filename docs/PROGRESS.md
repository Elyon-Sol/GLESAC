# GLESAC - progress & state (read this first on any new session)

> **Status (2026-07-20): SUPERSEDED — historical record.** GLESAC's development has been retired
> and the project is **open source under AGPL-3.0** (same license as the Elyon-Sol core), in a
> public repo. The notes below are a record of the build. Authoritative license/status:
> `LICENSE` and `README.md`.

Self-describing state so a fresh session (or a new collaborator) resumes from the REPO, not from
memory or a prior chat. Keep it short and current. Authoritative design: `docs/DESIGN.md`;
security law: `docs/SECURITY.md`.

## What GLESAC is (one paragraph)

Gargoyles Ledge (GLESAC) - the Elyon-Sol Administrative Console. An OPA-style, LOCAL-FIRST
operator toolkit for an Elyon-Sol admission-gate deployment: a `glesac` CLI plus a `glesac run`
localhost web console. It CONSUMES Elyon-Sol by INVOCATION (the installed CLIs) - never by
importing core internals. AGPL-3.0, public repo.

## Decisions on record (do not silently reverse)

- **Option B, local-first** (not a networked admin server). `glesac run` binds `127.0.0.1` only.
  The networked multi-operator API (Option A) is DEFERRED until multiple/remote operators or a
  product surface require it.
- **OPA-toolkit ergonomics** (`glesac <subcommand>` + `glesac run`), stricter security posture
  (localhost-only, local-custody HIL). OPA is the shape, not the network posture.
- **Consume Elyon-Sol by invocation** (`envelope_inspector`, `approver_cli` CLIs + read the JSONL
  logs), never by import. Keeps the repos decoupled and "no re-implementation" true.
- **AGPL-3.0, public** (was proprietary + private; reversed at retirement, 2026-07-20). LICENSE is AGPL-3.0, same as the Elyon-Sol core.
- **HIL preserves SoD:** GLESAC contains NO signing primitive; the approver key stays in local
  custody and grants are signed by `approver_cli`. Enforced by a package-wide revert-catcher test.
- **GLESAC is NEVER referenced in the public Elyon-Sol repo.** One-directional coupling.

## Phase status

- **P0 DONE** - design (`docs/DESIGN.md`).
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
- **LIVE-1 DONE (operational, not code).** The full HIL loop was exercised end-to-end on the
  PUBLIC gate (`gate.elyon-sol.io:8443`), 2026-07-04: mint -> 202 hold -> `glesac pending` shows
  it with context -> human `glesac pending --approve` (approver key `approver-2026-07-04` in
  laptop custody) -> present grant -> target `/received` 5->6 (exactly one action) -> re-present
  -> `REF_APPROVAL_REQUEST_UNKNOWN` (single-use holds). `glesac trace`/`audit` corroborate the
  same `grant_id` on both sides. This is the answer to "an approval queue that lets a human in
  fact approve": proven live, not asserted.
- **Live gate was upgraded this session** from a weeks-stale tree (bare `ELYON_APPROVER_PUBKEY_HEX`
  pin, NO approval log) to the full R1 chain: signed approver-role key record + pinned root, run
  via `deploy.governance.approver_trust_bootstrap:app`, durable issuance/approval logs under
  `EVIDENCE/runtime/`. The startup wiring-guard (G-01/G-04/G-06) forced this - it fail-closed
  until R1 + logs were wired. Gate on Elyon-Sol `bd1159b`; systemd unit `elyon-gate` with a
  drop-in override for the shim ExecStart.
- **POLISH DONE (freshness chip live-refresh).** `/api/status` now takes `probe` (default True);
  the dashboard polls `?probe=0` every 60s to live-refresh the signed-record freshness chip via a
  cheap local re-read (no repeated node probes) and shows an "as of" time. GET-only, localhost -
  security law unchanged; test `test_status_probe_false_skips_node_probes_but_keeps_freshness`
  added (39 passed, 2 skipped). This closes the last named backlog cosmetic.
- **WEBUI DONE (click-to-detail + cache-hardening).** The web console's `request` (approval_request_id),
  `decision` (decision_sha256), and `subject` (audit) cells - and every `action-trace` stage - open a
  read-only detail modal with the full record; decision cells also wire to the trace view. Cache-hardened:
  a `Cache-Control: no-store` middleware + content-hash `?v=` on the static asset URLs (fixes browser
  script-caching that made a rebuilt UI look stale). Verified with a headless jsdom click-through;
  localhost, GET-only, no signing primitive (SoD no-mutating-routes catcher green); 42 passed, 2 skipped.
  On GLESAC `origin/main` (fa67030..0742ead).
- **Typed-impact dependency (allowed direction).** Elyon-Sol shipped typed impact (per-interaction-type
  classification: VL-132 evaluator + VL-133 wiring) DEFAULT-OFF. GLESAC's HIL console surfaces holds
  correctly regardless; when Elyon-Sol turns typed impact ON (its coordinated deploy), the pending view
  can label the interaction type. GLESAC consumes this BY INVOCATION; Elyon-Sol never references GLESAC
  (one-directional - re-verified this session and a stray GLESAC reference scrubbed from the Elyon-Sol
  deploy runbook). Next-session opener: `docs/NEXT_SESSION.md`.
- **No scheduled phase after LIVE-1.** Backlog candidates (build only when needed): consume gate
  `/audit` for a remote-log view; local session token for shared boxes (DESIGN section 5).

## Carryover / operator housekeeping (from the LIVE-1 session)

- **Attack-suite re-run REQUIRED** against the live gate - refusal-path wiring changed with the
  R1 upgrade. `ELYON_LIVE_GATE_URL=https://gate.elyon-sol.io:8443` +
  `EVIDENCE/proofs/attack_suite_live_runner.py` (deploy Phase 1.4). NOT yet run.
- **Key record re-issue before 2026-08-03** - the approver key record has a 30-day TTL; rerun
  `deploy/governance/make_approver_key_record.py --serial 2` on the laptop, ship the record,
  restart the gate. An EXPIRED record fail-closes to an empty approver map (refuses all grants).
- **Gate host OS reboot pending** ("*** System restart required ***" at login).
- **CHALLENGE-DOC POLICY NOTE:** the LIVE manifest (`MANIFEST/manifest.json`) has NO `HIGH_IMPACT`
  key, so under [FIX H1] `requires_approval` fail-closes to True for EVERY eligible mint - the
  public gate is now in "everything-holds" mode. The challenge doc's "a mint immediately forwards
  one action" positive control no longer happens. To restore it, declare an explicit
  `HIGH_IMPACT` policy (even `[]`), which changes the manifest hash and requires republishing the
  pins on Host B (target + sidecar). Operator decision, deferred.
- **Deploy-host note:** the gate VPS runs a COPIED tree, not a git clone; updates need a full
  `IMPLEMENTAT