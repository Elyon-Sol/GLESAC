# GLESAC security model (non-negotiable)

GLESAC is a console for a security gate, and Elyon-Sol actively recruits red-teamers. These
rules are design law; a feature that cannot meet them is descoped, not compromised.

1. **Local client, not a networked server.** GLESAC runs on the operator's machine. `glesac run`
   binds `127.0.0.1` only (enforced in `server.serve`). No network-reachable admin service, no
   new remote auth surface, no remotely-reachable mutation path.
2. **Mutations stay local.** Every admin change and HIL approval is performed by the installed
   Elyon-Sol tools (`approver_cli`, rotation/cert runbooks) invoked locally. GLESAC orchestrates
   and records; it never exposes a networked endpoint that performs them.
3. **HIL preserves separation of duties ([FIX H5]).** The approver signs the grant with
   `approver_cli` using their OWN private key, in local custody - it never touches GLESAC's
   server or the gate. GLESAC contains NO signing primitive; it cannot mint a grant. (Enforced
   by a revert-catcher test.)
4. **Reads are read-only and minimal.** Live node state comes from minimal, read-only,
   authenticated node endpoints over an SSH tunnel / VPN, or from pulled logs. No secrets, no
   mutation, fail-closed.
5. **Never on the public gate surface.** Neither GLESAC nor its read endpoints are exposed on the
   four in-scope public nodes.
6. **No new admissibility / crypto.** Reuse `envelope_inspector` / `approver_cli` / `readiness`
   by invocation. Never re-implement verification or signing.
7. **Honest scope.** Operator capability; NOT external validation of the gate; moves no readiness
   predicate.

OPA parallel: GLESAC borrows OPA's toolkit ergonomics, NOT its network posture. OPA's server may
bind `0.0.0.0` and signs nothing with a custody key; GLESAC binds localhost and signs HIL grants
locally.
