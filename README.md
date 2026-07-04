# Gargoyles Ledge (GLESAC)

**G**argoyles **L**edge - the **E**lyon-**S**ol **A**dministrative **C**onsole.

An OPA-style operator toolkit for an [Elyon-Sol](https://elyon-sol.io) admission-gate
deployment: administration, envelope review, action tracing, and human-in-the-loop (HIL)
approval - as a `glesac` CLI plus a local web console (`glesac run`).

> **Local-first, by design.** GLESAC is an operator tool, not a networked admin server. The
> web console binds `127.0.0.1` only; every mutation (HIL approval, key/cert rotation) runs
> LOCALLY through the Elyon-Sol tools, and the approver's signing key never leaves the operator
> machine. GLESAC is never exposed on the public gate surface. See `docs/SECURITY.md`.

## Operating model (like OPA's toolkit)

A single `glesac` binary with subcommands - familiar to anyone who uses `opa` - most of which
REUSE the installed Elyon-Sol tools by invocation (no re-implementation of verification/crypto):

| Command | Does | Backed by |
|---------|------|-----------|
| `glesac inspect <envelope>` | decode + verify + reassert one envelope | `envelope_inspector inspect` |
| `glesac reevaluate <envelope>` | semantic re-evaluation | `envelope_inspector reevaluate` |
| `glesac reconcile --issued --executed` | issued-vs-executed audit | `envelope_inspector reconcile` |
| `glesac approve` | HIL: sign an approval grant (LOCAL key custody) | `approver_cli` |
| `glesac pending` | HIL queue: list pending 202 holds; `--approve` delegates to `approver_cli`, `--deny` records to the console audit | approval log + `approver_cli` |
| `glesac status` | node health + readiness predicates | node endpoints + `readiness` |
| `glesac logs` | tail/query the JSONL decision logs | issuance/approval logs |
| `glesac run` | start the localhost web console (OPA `run -s`, 127.0.0.1 only) | this repo |

Freshness/integrity reuses Elyon-Sol's signed published record + hash-pinned manifest (the
"bundle" analog). GLESAC adopts OPA's ergonomics, NOT its network posture: OPA's server can bind
`0.0.0.0` and signs nothing with a custody key; GLESAC binds localhost and HIL signs locally.

## Requires

Elyon-Sol installed on the operator machine (GLESAC shells out to its CLIs). Point GLESAC at it
with `ELYON_SOL_HOME=/path/to/Elyon-Sol` (or have `envelope_inspector`/`approver_cli` on PATH).

## Install (dev)

```
pip install -e .
glesac --help
```

## Status

P2 (HIL approval queue) done. Build order (see `docs/DESIGN.md`): P0 spec -> P1 read-only console + CLI shell ->
P2 HIL approval -> P3 administration. Operator capability; NOT external validation of the gate.

## License

Proprietary and confidential. Copyright (c) 2026 Justin LaPorte. All rights reserved.
Not licensed for use, copying, or distribution except under a separate written agreement.
See `LICENSE`. Licensing inquiries: admin@elyon-sol.io
