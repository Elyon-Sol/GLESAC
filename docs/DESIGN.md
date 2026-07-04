# GLESAC - design (P0)

Design of record for Gargoyles Ledge (the Elyon-Sol Administrative Console). This document is
self-contained and lives ONLY in this repo; the open Elyon-Sol core repo intentionally contains
no reference to GLESAC. GLESAC is proprietary operator tooling and consumes Elyon-Sol as an
external dependency, by invocation, never by importing core internals.

## 1. Purpose & operating model

An OPA-style operator toolkit for an Elyon-Sol admission-gate deployment: administration,
envelope review, action tracing, and human-in-the-loop (HIL) approval. One `glesac` binary with
subcommands, plus `glesac run` for a localhost web console. Ergonomics borrowed from `opa`;
security posture is stricter (localhost-only, local-custody HIL). See `README.md` for the
subcommand map and `docs/SECURITY.md` for the non-negotiable invariants.

## 2. Security model (summary; authority is docs/SECURITY.md)

Load-bearing invariants: (a) local client, not a networked server - `glesac run` binds
`127.0.0.1` only; (b) mutations run locally through the installed Elyon-Sol tools, never a
networked endpoint; (c) HIL preserves separation of duties - the approver signs with their own
key in local custody, and GLESAC contains NO signing primitive (enforced by a revert-catcher
test); (d) reads are read-only and minimal; (e) never exposed on the public gate surface; (f) no
re-implementation of admissibility/crypto. A feature that cannot meet these is descoped.

## 3. Data model

The **decision** is the spine. Every ELIGIBLE gate decision has a `decision_sha256` that binds
tool + args digest + target + manifest pins + condition results + timestamp. GLESAC joins every
other record to it.

| Entity | Key fields | Source |
|--------|-----------|--------|
| Envelope / decision | `decision_sha256`, tool, `args_sha256`, `target_url`, `not_after`, issuer sig | issuance log; or pasted by the operator |
| Issuance record | one envelope per line | `JsonlIssuanceLog` (JSONL) |
| Approval request (202 hold) | `{type:"approval_request", decision_sha256, approval_request_id}` | `JsonlApprovalLog` / gate pending store |
| Grant consumed | `{type:"grant_consumed", decision_sha256, approval_request_id, grant_id}` | `JsonlApprovalLog` |
| Executed action | the interaction the target acted on | target `GET /received` |
| Signed published record | `publisher_key_id`, `serial`, `issued_at`, `not_after` | publisher `/published_hashes_signed.json` |
| Readiness predicates | DEFAULT_SECURE / END_TO_END_NO_SHORTCUT / ROOT_RECOVERY / REAL_TRANSPORT | `readiness` (readiness.json) |
| Node | host, port, role, cert expiry, deployed commit | TLS probe + config |

**The action timeline** (the trace view) is the left-to-right join on `decision_sha256` (and
`approval_request_id` for the HIL leg):

```
issued (envelope minted)
  -> [approval_request]        (only if high-impact: a 202 hold)
  -> [grant_consumed]          (a human grant was recorded)
  -> forwarded                 (gate forwarded to the target)
  -> executed (/received++)    (the target acted)
```

A gap in that chain is the signal: forwarded-but-no-grant_consumed on a high-impact decision is
`FORWARDED_WITHOUT_GRANT` - a caught invariant violation surfaced by `envelope_inspector
reconcile`.

## 4. Data sources & access

P1 requires ZERO changes to the Elyon-Sol core: GLESAC reads the JSONL logs (pulled to the
operator over SSH, or mounted read-only) and shells out to `envelope_inspector`, and supports
pasting a single envelope for review. Live cross-node state (pending 202s on the gate, the
`/received` count on the target) is read from the nodes' read-only endpoints over an SSH tunnel /
VPN, or derived from pulled logs. No secrets are ever read; no mutation is ever performed over a
network.

### Node read-endpoint contract (optional; used when live reads are wanted)

These are the ONLY node-side additions GLESAC would benefit from. They are generic read-only
observability endpoints (they do not name or imply GLESAC), added to the core build-then-wire,
default-off, and reachable only over the operator tunnel:

| Endpoint | Returns (no secrets) | Notes |
|----------|----------------------|-------|
| gate `GET /pending` | `[{approval_request_id, decision_sha256, tool, target_url, requested_at}]` | held 202s; public decision context only |
| gate `GET /audit?tail=N` | last N issuance/approval log records | read-only tail |
| target `GET /received` | `{count}` (already exists) | executed-action count |
| publisher `/published_hashes_signed.json` | the signed record (already exists) | freshness |
| readiness.json | predicate summary | already produced by `readiness` |

Until those exist, P1 operates entirely from pulled logs + the CLIs. The endpoints are a
convenience, not a prerequisite.

## 5. Auth & the HIL custody boundary

**Operator auth.** GLESAC is a local tool: the trust boundary is the operator's own machine and
OS user. `glesac run` binds localhost; the web console MAY require a locally-generated session
token (stored 0600) to prevent other local users on a shared box from driving it. No networked
auth, no remote sessions.

**HIL custody (the crux).** The approver's Ed25519 PRIVATE key lives in local custody on the
approver's machine (a `0600` file or a hardware token) - never in GLESAC, never on the gate,
never on a server. The flow:

1. GLESAC shows the pending decision (from `/pending` or the approval log) with full context.
2. The human decides. On approve, `glesac approve` invokes `approver_cli`, which reads the
   private key from local custody and emits a grant.
3. The operator presents that grant to the gate (the existing governed path). GLESAC records the
   decision in its local console-audit log.

GLESAC has NO signing code and NO access to the private key. `tests/test_cli.py` includes the
SoD revert-catcher: it fails if any signing primitive (`make_grant`, `sign_grant`,
`Ed25519PrivateKey`, `private_key`, ...) ever appears in the GLESAC package. A self-approval
backdoor is therefore structurally impossible, and the guard is enforced in CI.

## 6. CLI surface

`glesac inspect|reevaluate|reconcile` (-> `envelope_inspector`, read-only) · `glesac approve`
(-> `approver_cli`, local key custody) · `glesac status` (node health + readiness) · `glesac
logs` (tail/query the JSONL decision logs) · `glesac run` (localhost web console). All non-native
commands are pass-throughs to the installed core tools; GLESAC adds orchestration, joins, and the
UI, not verification or signing.

## 7. Web console (`glesac run`, 127.0.0.1)

Read-only panels over the local server: node status board; envelope review (inspect + verify +
reassert; search by `decision_sha256`); action trace (the section-3 timeline); reconciliation
dashboard; refusal analytics (counts by `REF_*`); key/record/cert freshness; replay/pending
inspection; self-test trigger + history; console audit-log viewer. Mutations (HIL approve, admin
rotation) are orchestrated to the LOCAL tools, never performed by a networked route.

## 8. Build order

- **P0** - this design (data model, node read-endpoint contract, HIL custody boundary). DONE.
- **P1** - localhost read-only console + CLI shell, from pulled logs + `envelope_inspector`;
  zero core change; localhost-bound; tests incl. revert-catchers.
- **P2** - HIL approval queue; approve via local `approver_cli`; the SoD revert-catcher stays
  green.
- **P3** - administration: rotation TRIGGERS that invoke the existing local runbooks
  (`rotate_publisher_key`, cert renewal); every mutation authenticated to the local operator and
  written to the console audit log.

## 9. Testing discipline

Every phase ships tests including revert-catchers proven RED-on-revert. The load-bearing one is
the no-signing SoD guard (section 5). Read paths are tested against sample JSONL fixtures so the
console renders without a live deployment.

## 10. Honest scope

GLESAC is operator capability. It is NOT external validation of the gate and moves no readiness
predicate. It never re-implements admissibility or cryptography. The Elyon-Sol canon is unchanged
and unreferenced here.
