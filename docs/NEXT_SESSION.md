# Next session starter — GLESAC / Elyon-Sol

Paste this to open the next session. Resume from the REPOS, not memory.

## 0. Connect & resume
Connect both folders: `~/glesac` and `~/Elyon-Sol` (work natively; local-first).
Read in order:
- GLESAC: `docs/PROGRESS.md`, `docs/DESIGN.md`, `docs/SECURITY.md`, `docs/overview.svg`
- Elyon-Sol: `STATE.md`, `EVIDENCE/verification_ledger.md` (latest is **VL-133**), `deploy/TYPED_IMPACT_DEPLOY.md`
Run tests to confirm the baseline:
- GLESAC: `python -m pytest -q` → expect **42 passed, 2 skipped**
- Elyon-Sol: `python -m pytest -q` → expect **541 passed**

## 1. Current state (end of last session)
- **GLESAC @ `origin/main` 0742ead** — localhost operator console. Web UI has click-to-detail:
  the **request** (`approval_request_id`), **decision** (`decision_sha256`), and **subject**
  (audit) cells, plus every **action-trace stage**, open a read-only detail modal with the full
  record. Cache-hardened: `Cache-Control: no-store` middleware + content-hash `?v=` on the
  `app.js`/`style.css` URLs (fixes browser script-caching). Localhost-only, GET-only, no signing
  primitive; SoD no-mutating-routes catcher green.
- **Elyon-Sol @ `origin/main` 435ae37** — typed-impact **built, proven, DEFAULT-OFF**:
  - VL-132: evaluator per-interaction-type required sets (`resolve_required_sets`); `evaluator_sha256`
    moved `89a30ffe -> e307fab2`.
  - VL-133: wiring (optional `interaction_type` in the request schema, per-type `interaction_for`,
    per-type `governed_call` envelope). No pinned file touched by 8.2.
  - Live manifest is still **FLAT** (`HIGH_IMPACT: []`, `manifest_sha256 ac18ac78`). Candidate typed
    manifest at `deploy/manifest_typed_v1.1.candidate.json` (`manifest_sha256 b1b2128a`; validated:
    benign `read` forwards, sensitive `transfer` holds). Turn-on runbook: `deploy/TYPED_IMPACT_DEPLOY.md`.

## 2. Ground rules (do NOT silently reverse)
LOCAL-FIRST (GLESAC binds 127.0.0.1 only). Consume Elyon-Sol BY INVOCATION (CLIs + read JSONL logs),
never import core internals. HIL preserves SoD — GLESAC holds NO signing primitive (the revert-catcher
must stay GREEN). GLESAC is NEVER referenced in the public Elyon-Sol repo (one-directional). Elyon-Sol
core changes are default-off + build-then-wire; the startup wiring-guard is load-bearing. Canon is
corrected only by version increment (GR-1); the ledger is append-only (GR-4).

## 3. OBJECTIVES THIS SESSION

### Objective A — Confirm ALL public nodes are up to date
The four public nodes: **gate** `gate.elyon-sol.io:8443`, **target** `:9443`, **authz sidecar**
`:9243`, **publisher** `:9143`. (The Cowork sandbox CANNOT reach them — 403; run these from the
laptop / operator tunnel.)

1. **Reconcile the deployed-commit divergence FIRST.** The Elyon-Sol ledger (VL-122 / VL-128) records
   the four nodes at commit **`3343e32`** (pre-governance); GLESAC `PROGRESS.md` (LIVE-1, 2026-07-04)
   records the **gate** at **`bd1159b`** (full R1 chain). Determine the ACTUAL per-node commit (SSH to
   each; `git rev-parse HEAD` if it's a clone, else inspect the deployed tree / a version marker).
2. **Confirm version-match (siblings must match).** All record-consuming nodes must be consistent. They
   currently interoperate across `3343e32`/`bd1159b` only because `evaluator.py` was byte-identical
   across those commits (`evaluator_sha256 89a30ffe`, verified last session). Confirm this still holds
   and that `published_hashes.json` / `ELYON_PINNED_ROOT_SHA256` are consistent across target + sidecar.
3. **Confirm health + freshness** via the GLESAC console: `python -m glesac.cli status` probes all four;
   the publisher signed record should be FRESH (re-signs ~5-min); run the live attack suite
   version-matched (`EVIDENCE/proofs/attack_suite_live_runner.py`) for a GREEN referent.
4. **Confirm the R1 approver key-record is not expired** — it has a 30-day TTL; re-issue before
   **2026-08-03** or the gate fail-closes to refuse-all (`deploy/governance/make_approver_key_record.py
   --serial 2`; mind the root-pin caveat: the script regenerates root each run).
5. **Confirm the pending gate-host OS reboot** ("*** System restart required ***").
6. **Define "up to date" and record the verdict.** Two meanings: (a) internally consistent + current at
   the deployed commit (challenge-ready) — likely the target for this session; or (b) matching
   `origin/main` 435ae37 (i.e. deploying VL-132/133) — which is NOT a drop-in: it changes
   `evaluator_sha256` (and, if typed impact is turned on, `manifest_sha256`), so it requires the
   coordinated two-hash re-pin across all nodes per `deploy/TYPED_IMPACT_DEPLOY.md`, and is gated on the
   HIGH_IMPACT decision. Do NOT deploy VL-132 to the gate alone (its envelopes stamp `e307fab2` while
   the target still pins `89a30ffe` → refuse-all).

**Deliverable A:** a per-node table {node, deployed commit, `evaluator_sha256`, `manifest_sha256`, cert
expiry, record freshness, reachable?, up-to-date verdict}; reconcile the record divergence and write it
to the Elyon-Sol ledger (a VL entry) + a GLESAC `PROGRESS.md` note (the allowed direction).

### Objective B — Issue a public (reproducible) test case for WebUI detail verification
Context: last session the click-to-detail feature was correct but a browser script-cache made it LOOK
broken; we hardened caching and PROVED the feature with a headless jsdom click-through. Formalize that
into a committed, reproducible test case so it can never regress or be misdiagnosed again.

1. **Author a FUNCTIONAL UI test** (not just a presence check). Seed: the jsdom harnesses from last
   session (`/tmp/uitest.mjs`, `/tmp/tracetest.mjs`). It must: load the real `webui/index.html` +
   `app.js`, mock the `/api/*` responses, render the pending/logs/audit tables + a trace, dispatch a
   `click` on a request / decision / subject cell AND a trace stage, and assert the `#detail-overlay`
   opens with the correct title + full-record JSON in `#detail-body`. Commit it under `tests/` (e.g.
   `tests/webui/test_detail_clickthrough.mjs` + a pytest wrapper that skips if node/jsdom is absent).
2. **Make it "public"/reproducible:** document how to run it (node + jsdom, or a pure-python DOM
   alternative), and keep it GLESAC-private-safe (do NOT reference GLESAC in the public Elyon-Sol repo).
3. **Write the test case in a shareable QA form** (TC-WEBUI-DETAIL-001): preconditions, steps, expected
   result, so any collaborator can verify by hand (`glesac run` → open console → click a decision → detail
   panel + "trace this decision"; click a trace stage → detail panel).
4. **Close the regression loop:** the `no-store` + content-hash tests already exist
   (`test_static_assets_are_no_store`, `test_index_content_hashes_asset_urls`); the new functional test
   proves clicking actually opens the modal, catching a future wiring break.

**Deliverable B:** a committed functional click-through test (green in the glesac suite) + a short
`docs/` verification note (TC-WEBUI-DETAIL-001). Suite stays green; covers request/decision/subject +
trace-stage detail.

## 4. Carryover (track; not this session's primary objectives)
VL-134 (flip live manifest to typed + ~85-test migration + regenerate pins) — the opening move of the
typed-impact deploy. The HIGH_IMPACT / everything-holds policy decision. The coordinated two-hash re-pin.
These are all in `deploy/TYPED_IMPACT_DEPLOY.md`.

## 5. Environment notes
- Cowork sandbox CANNOT reach the public nodes (403) or push. The AUTHOR runs live checks + pushes
  natively.
- Mount hazard: host file-tool writes to the connected folders truncate intermittently; write via bash
  and verify byte counts + `ast.parse`/`node --check`. Git in the sandbox leaves phantom `index.lock`/
  `HEAD.lock`/`refs/heads/main.lock` and stray `tmp_obj_*` — commit via a relocated `GIT_INDEX_FILE` +
  `commit-tree` + direct ref write, and clean up natively (`rm -f .git/*.lock`; `git reset --mixed HEAD`;
  `git gc --prune=now`).
- The `glesac` command may not be on PATH — `python -m glesac.cli ...` always works.
- Division of labor: build/commit in-session, AUTHOR verifies blobs on a pristine `git archive HEAD`
  extraction and pushes natively.
