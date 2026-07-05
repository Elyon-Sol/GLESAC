# Full path — typed high-impact policy + honest live attack-suite re-attestation

Target posture: **typed impact** (benign calls forward; genuinely high-impact calls hold for a
human grant). This supersedes the framing in `LIVE-1.4_attack_suite_rerun_prep.md` §3, which
predated the finding that the impact model is structurally all-or-nothing today.

Everything below is grounded in files read directly this session (Elyon-Sol `19af1c6`), not the
carryover notes. Ground rules preserved throughout: core changes are **default-off / build-then-
wire**; the startup wiring-guard stays load-bearing; **GLESAC is never referenced in Elyon-Sol**;
GLESAC holds no signing primitive.

---

## 1. Diagnosis — why impact is all-or-nothing today (verified)

- `IMPLEMENTATION/evaluator.py::evaluate()` reads a **single flat** `manifest["AR"]` and
  `manifest["R"]`. `interaction_type` (present in `MANIFEST/manifest.json` as `"default"`) is a
  label — nothing branches on it. Eligibility = `AP ⊇ AR` (`ac3_valid`) and `OP ⊇ R` (`t26_valid`).
- `IMPLEMENTATION/mcp_server.py::interaction_for(tool, args)` returns a **fixed** context for every
  call: `AP = ["identity","role"]`, `OP = ["session","request"]` — identical to `AR`/`R`,
  independent of `tool` and `args`.
- `IMPLEMENTATION/impact.py`: `safe_high_impact` requires `HIGH_IMPACT ⊆ AR∪R` ([FIX H2]);
  `requires_approval` holds iff `(AP∪OP) ∩ HIGH_IMPACT ≠ ∅`. A **missing** key → `None` → fail-
  closed True; an explicit `[]` → forwards.

**Consequence:** every eligible mint declares exactly `AR∪R = {identity, role, session, request}`.
So any non-empty `HIGH_IMPACT ⊆ AR∪R` intersects **every** eligible mint → all hold; `[]` → none
hold. Impact is a property of the interaction **type** (the manifest), never of the specific call —
exactly as `impact.py`'s own docstring states. There is **no** single-manifest value that makes
some calls forward and others hold. That capability is a core build, not a config edit.

Corollary about the live gate: its manifest is *missing* the key, and
`governance_wiring.high_impact_declared()` treats missing (`None`) as **declared** (fail-closed).
So the gate is already in high-impact-governed mode with R1 + approval log wired (that's what the
startup guard forced). "Everything-holds" today is a **malformation that fail-closes**, not a
declared policy. The task is to replace the malformation with a real, typed policy.

## 2. Target model — typed impact (the designed end-state)

The manifest already carries `interaction_type` and `HIGH_IMPACT` as selectors; the evaluator just
never implemented per-type policy. Realize it:

- A manifest defines **named interaction types**, each with its own required sets and an impact
  class. A benign type (e.g. `read`) requires low authority and is **not** high-impact; a
  sensitive type (e.g. `transfer`) requires elevated authority tokens and **is** high-impact.
- The caller's interaction declares its type + the authority/operation tokens it actually carries.
  `requires_approval` then holds **only** the sensitive types. Benign traffic forwards; sensitive
  actions get the human. The LIVE-1 HIL loop fires for a *declared* reason.

This keeps every existing invariant: eligibility is still `AP⊇AR_type` / `OP⊇R_type`, impact is
still manifest-derived (never caller-set), [FIX H1] (missing/malformed → fail-closed) and [FIX H2]
(`HIGH_IMPACT ⊆ ⋃ types' AR∪R`) still hold, and the SHA pin still anchors the whole manifest.

## 3. Core build — component by component (default-off, build-then-wire)

Each item is additive and behind the typed-manifest opt-in; the current flat manifest keeps
byte-identical behavior until the new manifest is pinned.

1. **Manifest schema** (`MANIFEST/manifest.json` + a schema validator). Introduce a
   `interaction_types` map: `{ type_name: { "AR": [...], "R": [...], "high_impact": bool } }`,
   keeping top-level `AR`/`R` as the default type for backward compatibility. `HIGH_IMPACT` becomes
   derived (the union of tokens for types flagged `high_impact`) OR stays an explicit token list
   constrained to `⋃ AR∪R` — pick one and enforce it in `safe_high_impact`. Bump `version`.
2. **Evaluator** (`evaluator.py`). `safe_manifest` validates the typed shape; `evaluate` selects
   the type's `AR`/`R` by the caller's declared `interaction_type` (fail-closed on unknown type),
   then applies `ac3_valid`/`t26_valid` against the **type's** sets. `manifest_integrity_valid`
   and `manifest_sha256` unchanged (still hash the whole on-disk file).
3. **Interaction construction** (`mcp_server.py::interaction_for`). Derive real `AP`/`OP` (and the
   `interaction_type`) from the tool→authority mapping, so a `transfer` carries the elevated
   tokens and a `read` does not. This is what makes impact a *real* property instead of a constant.
4. **`impact.py`.** `safe_high_impact` extended to the typed manifest (still `⊆ ⋃ AR∪R`, still
   `None` on any malformation). `requires_approval` unchanged in spirit — now it actually
   discriminates because callers carry different token sets.
5. **Wiring-guard** (`governance_wiring.py`). No code change needed — it already fires whenever
   high-impact is declared and enforces G-01 (R1 injected approver trust), G-06 (non-empty approver
   map), G-04 (approval log), G-03 (pending/replay redis coherence). With a real typed policy it
   stays active, which is correct.
6. **Backward-compat + pin.** Default manifest (single `default` type, `HIGH_IMPACT: []`) stays
   behavior-identical. The typed manifest is a conscious pin change (new `manifest_sha256`).

## 4. Deployment path (Host A gate · Host B target+sidecar · publisher)

Changing the manifest changes `manifest_sha256`, which changes the byte-anchor the enforcing side
pins. Sequence, fail-closed at each step:

1. **Regenerate the published record.** `PYTHONPATH=. python3 EVIDENCE/published_hashes_gen.py`
   rebuilds `EVIDENCE/published_hashes.json` (canon + evaluator + **new manifest** sha). The new
   out-of-band anchor is `sha256(published_hashes.json bytes)`.
2. **Republish to Host B.** Publisher serves the new bytes at `/published_hashes.json`
   (`IMPLEMENTATION/publisher.py`); the **reference target** and the **authz sidecar** must both be
   updated: the target re-pins `ELYON_PINNED_ROOT_SHA256` (it fetches the record), the sidecar gets
   the new `ELYON_RECORD_PATH` file **and** `ELYON_PINNED_ROOT_SHA256` (it reads a local copy). In
   signed-freshness mode the publisher re-signs per request (5-min TTL), so currency is automatic;
   only the anchor changes. Full-tree sync per the copied-tree caveat, never a one-file swap.
3. **Gate restart with R1 chain.** Start via the shim
   `uvicorn deploy.governance.approver_trust_bootstrap:app` so approver trust is **injected** from
   the publisher-signed key record (`ELYON_APPROVER_KEY_RECORD_PATH`) validated against the pinned
   **R1 root** (`ELYON_PINNED_ROOT_KEY_ID` / `ELYON_PINNED_ROOT_PUBKEY_B64`). Note these are the
   **approver-trust** root pins — distinct from the **published-record** anchor
   `ELYON_PINNED_ROOT_SHA256` in step 2. Do not conflate them.
4. **Fail-closed boot verification.** The wiring-guard must pass (R1 injected, approver map
   non-empty, approval log configured, redis coherence). If any is missing the gate refuses to
   start — that is the intended proof the oversight is wired, not asserted. Confirm a benign mint
   forwards and a sensitive mint returns 202.

### 4a. R1 key-record re-issue (independently due before 2026-08-03)

The approver record has a 30-day TTL; expired → empty approver map → refuse-all. Re-issue on the
**approver/laptop** host: `python deploy/governance/make_approver_key_record.py --serial 2
--out-dir <clean>`; ship only `approver_key_record.json`; restart the gate. **Caveat (verified in
the script):** it `Ed25519PrivateKey.generate()`s a fresh **root** every run (line 82) while
keeping `--root-key-id root-1`, so a serial-2 re-issue as-written also rotates the pinned R1 root →
you'd re-pin `ELYON_PINNED_ROOT_PUBKEY_B64` on the gate, not just ship the record. The line-129
hint ("root key file must be moved back in place") implies re-use of `root-1`, but the code has no
flag to load an existing root. Decide reuse-vs-rotate before shipping.

## 5. Attack-suite re-attestation — honest positive controls

Under typed impact the suite needs **two** positive controls (the current harness has only the
first, which is why it can't pass against an everything-holds gate):

1. **Benign forward control** — mint a **benign-type** interaction; the gate signs + push-forwards;
   the target's `/received` increments once. This is the honest version of the existing
   `positive_control` (`EVIDENCE/proofs/attack_harness.py` push branch), repointed to a benign type.
2. **High-impact HIL control** — mint a **sensitive-type** interaction → 202 hold → human approves
   via `approver_cli` (R1 custody) → present the grant → target acts **exactly once** → re-present →
   refused (`REF_APPROVAL_REQUEST_UNKNOWN`). This is LIVE-1, promoted from a one-off demo to a
   standing control. It proves oversight *functions*, not just that it *blocks*.
3. **Six adversarial attacks, defeated over real transport** — un-attested, forged signature,
   replay, rebind-tool, rebind-args, target_url-swap (the existing suite; reasons are verifier-level
   `REF_VERIFY_*`, upstream of approval, so unaffected by the policy change).

On green, re-attest `REAL_TRANSPORT` in `EVIDENCE/readiness.json` naming the **new** run log, and
keep the honest residual explicit: this is an author-run proof; the external-stranger bound (G5)
stays open and unclaimed.

## 6. GLESAC console alignment (read-only, no core coupling)

- `pending_view` and the dashboard already surface held decisions; add the **interaction type** to
  the pending row so an operator sees *why* something held (sensitive-type), not just that it did.
- `glesac trace` timeline already renders the issued→approval_request→grant_consumed→executed legs;
  no change needed beyond the type label.
- Still GET-only, localhost, no signing primitive. GLESAC remains unreferenced in Elyon-Sol.

## 7. Test / verification plan (each phase ships proven-RED-on-revert catchers)

- **Evaluator per-type unit tests:** benign type forwards, sensitive type holds, unknown type
  fail-closes; `AP⊇AR_type` boundary cases.
- **Impact catchers:** [FIX H1] missing/malformed still fail-closed; [FIX H2] `HIGH_IMPACT ⊆ ⋃
  AR∪R` still enforced per-type; a token outside the union rejected.
- **Wiring-guard catcher:** a typed high-impact manifest with R1/log/redis missing must refuse to
  boot (extend existing G-01/04/06/03 coverage).
- **SHA-pin catcher:** changing the manifest changes `manifest_sha256`; a stale
  `published_hashes.json` must fail the target's anchor check.
- **GLESAC SoD revert-catcher** stays green (no signing primitive appears).
- **E2E:** the two positive controls + six adversarial, in-process first (CI), then author-run over
  real transport (excluded from CI, same as today).

## 8. Sequenced execution (each step shippable + default-off)

1. Schema + evaluator + impact typed support, behind the default manifest (no behavior change). CI
   green. **← proposed first build; I can start here on your go-ahead.**
2. `interaction_for` real AP/OP derivation + a typed `MANIFEST/manifest.json` (benign + sensitive).
   New `manifest_sha256`; regenerate `published_hashes.json`.
3. Attack-suite: add the HIL positive control; repoint the benign control.
4. Deploy: republish pins to Host B, restart gate via R1 shim, fail-closed boot check.
5. Live re-attestation run; update `readiness.json` REAL_TRANSPORT with the new log.
6. GLESAC: interaction-type label in the pending view.

## 9. What I need from you (custody / host actions I can't do from here)

- Approver-key custody actions (`approver_cli`, `make_approver_key_record.py`) — laptop only.
- Host B / gate VPS access for the pin republish + restart (sandbox can't reach the live surface).
- The reuse-vs-rotate decision on the R1 root (§4a).
- Confirmation of the concrete type taxonomy (what operations are "sensitive") — I'll propose a
  starter set (`read`/`list` benign; `transfer`/`delete`/`rotate` sensitive) unless you have one.

---

*I can begin at step 8.1 immediately — it's pure Elyon-Sol core, default-off, CI-verifiable, no
live surface or custody needed. Say the word and I'll build it against a worktree and hand you the
diff to commit.*
