# Elyon-Sol + GLESAC — project assessment & recommendations

> **Status (2026-07-20): SUPERSEDED — historical record.** GLESAC's development has been retired
> and the project **open-sourced under AGPL-3.0** (the same license as the Elyon-Sol core). This
> document's analysis — including its recommendation to keep GLESAC proprietary — reflects the
> earlier plan and is preserved as a record of the thinking. It no longer describes the project's
> license, visibility, or direction. Authoritative now: `LICENSE` (AGPL-3.0) and `README.md`.

*An outside-but-informed read, prepared from the two repos (Elyon-Sol @ `435ae37`, GLESAC @
`0742ead`), `elyon-sol.io`, the licensing docs, and the verification ledger. Written candidly, in
the project's own house style of not overselling.*

---

## Executive summary

This is an unusually disciplined solo project with a clear, timely thesis — **pre-execution
authorization for actions** ("governance before intelligence") — and a genuine engineering spine:
a formal canon, a faithful implementation of its three invariants, spec-to-code traceability, an
append-only verification ledger that records its own corrections, revert-catcher tests, and a
fail-closed posture throughout. The honesty of the public positioning (it states plainly what has
**not** been validated and which layers are **not** deployed) is a real credibility asset, not a
weakness.

The offering is coherently structured as **open core + proprietary tooling**: the Elyon-Sol core
is AGPL-3.0, and GLESAC is precisely the "proprietary administration and tooling SDK" the licensing
model already describes — an independent work that consumes the core across its public API, one-
directional, holding no signing primitive. That separation is principled and correct; keep it.

The single biggest incoherence — and the highest-leverage fix — is that **the core is licensed
open-source (AGPL) and the entire strategy depends on it being inspected, adopted, and attacked, yet
the GitHub repo is private** ("source available on request"). The red-team challenge literally asks
people to read `IMPLEMENTATION/envelope_inspector.py` and `deploy/BREAK_IT_IN_60_SECONDS.md`, which
they cannot. Making the core public is the move that unlocks the whole credibility play. **But there
is a hard prerequisite: the git history contains a previously-exposed publisher signing key (VL-108,
rotated at VL-122) — that history must be scrubbed or the exposure formally accepted before the repo
goes public.**

The central maturity gap is **G5 — zero external validation** — and it is gated on one unfinished
item: the counsel-reviewed safe-harbor clause. Nothing else moves the project's credibility as much
as landing the first outside break attempt, and nothing can happen there until that clause is signed.

---

## 1. The convergence — GLESAC as part of the offering

**Verdict: coherent and correctly architected. Productize it, don't merge it.**

The licensing model (`LICENSING.md`) already names a "closed administration and tooling SDK...
sold separately, not in this repo... interoperates strictly across the core's public API." GLESAC
IS that SDK: an OPA-style operator console (CLI + localhost web UI) that consumes Elyon-Sol by
invocation, never imports internals, binds `127.0.0.1`, and contains no signing primitive
(separation of duties enforced by a package-wide revert-catcher). So the two pieces are not two
projects — they are the two tiers of a deliberate open-core business model:

- **Open core (AGPL, public-facing):** drives adoption, citation, and the red-team challenge. Meant
  to be attacked. This is the credibility and community engine.
- **GLESAC (proprietary, commercial):** the operator/management layer — administration, envelope
  review, action tracing, HIL approval, audit. This is a monetization surface.

This session's typed-impact work is a textbook example of the *healthy* dynamic between the tiers:
GLESAC's operational goal (real, selective human-in-the-loop oversight) surfaced a genuine
limitation in the **core** (impact was structurally all-or-nothing), and the fix landed in the
**open core** (VL-132/133) — benefiting every AGPL user — while GLESAC stayed proprietary and the
one-directional rule held (the core never references GLESAC). That is exactly how open-core should
work: the commercial tier's needs improve the commons.

**Recommendation:** name GLESAC explicitly as the commercial tier of the offering (e.g. "Elyon-Sol
core, AGPL — Gargoyles Ledge operator console, commercial"). Right now GLESAC is a private repo, not
a *product*; the open-core story is stronger when the commercial tier is a named, described thing
(even without opening its source). Consider a public **screenshots/short demo** of the console (the
click-to-detail UI, the HIL queue, the trace view) so prospects see the operator experience without
the source leaving custody.

---

## 2. The public site (elyon-sol.io)

**Verdict: strong and honest; a few staleness and coherence fixes.**

What works, and should be preserved:
- The **honest-scope framing** is the site's best feature — "has not yet been validated by any
  external party," the governance/mTLS layers "not deployed on these public nodes," a run that finds
  nothing is "recorded as exactly that, never as 'unbreakable.'" In a field full of overclaiming,
  this is genuinely differentiating and builds trust.
- The **falsifiable, tool-adjudicated challenge** ("the tool decides, not us") and the one-line
  claim-to-disprove are well-constructed and intellectually honest.
- The **recognition-not-bounty** model (ledger credit, Zenodo co-authorship, CVE, founding red-team
  seat) is a thoughtful fit for recruiting serious researchers rather than bug-bounty volume.
- Clear technical exposition (AC³ / T²⁶ / CCS, envelope, binding, single-use), a runnable "break it
  in 60s," a citable Zenodo DOI + ORCID, canon versioning.

What to fix:
- **The open-core-but-private contradiction (top priority).** The badge says "AGPL-3.0 open-core"
  and the pitch is radical inspectability, but "source available on request" means the repo isn't
  actually public. This undercuts the whole premise and was already flagged internally (VL-129).
  Resolve it by making the core public (see §3).
- **Stale test count.** The site says "512 tests"; the repo is now at 541. Derive the number, don't
  hand-type it (the project already values un-fakeable counts — apply that here).
- **Deployed-vs-repo gap.** The live four nodes run a pre-governance build (`3343e32` per
  VL-122/128); the governance/human-oversight, mTLS non-bypass, and now typed-impact features shown
  on the site are codebase-only. The site *discloses* this honestly, which is good — but the gap is
  widening as the repo advances, and internally the deployed commit is even ambiguous (ledger says
  `3343e32`, GLESAC's LIVE-1 says the gate is at `bd1159b`). Reconcile it (see §4).
- **Safe-harbor not finalized.** The challenge cannot actually launch — no invitations, no
  authorized traffic — until the safe-harbor clause is signed. The site says so honestly, but it
  means the site is currently marketing a challenge that isn't open. Prioritize closing it.

---

## 3. Should the GitHub repo be public? — the open-source decision

**Elyon-Sol core: yes, open it — with one hard security gate first.**
**GLESAC: no, keep it proprietary.**

### Why open the core
- It is **already AGPL-3.0.** AGPL's entire value is public, copyleft distribution; an AGPL license
  on a private repo is close to a contradiction in terms.
- The **strategy requires it.** "Meant to be inspected, adopted, and attacked"; the red-team
  challenge points researchers at repo paths; "it's all on the public record." None of that is true
  while the repo is private. Opening it converts the positioning from aspiration to fact.
- **Credibility.** For a project whose entire pitch is transparency and falsifiability, a private
  repo is the one visible place where the walk doesn't match the talk. Opening it is the single
  cheapest, highest-trust move available.
- **Open-core is protected.** AGPL + the dual-license (commercial exemption) + the proprietary
  GLESAC tier means opening the core does **not** give away the business — it is the standard, proven
  open-core structure (the copyleft pushes commercial users toward the paid license; the tooling tier
  stays closed).

### The hard prerequisite (do NOT skip)
Before flipping visibility, **audit and, if needed, rewrite the git history for secrets.** The
ledger itself records that a publisher **signing private key was exposed** (VL-108) and later rotated
(VL-122). If that key — or any `.hex`/`.env`/key material — is reachable anywhere in history, making
the repo public discloses it permanently. Concretely: run a secret scanner over full history
(`gitleaks`/`trufflehog`), review what the repo's own `check_history.sh`/`disable_history.sh` were
for, confirm every historically-exposed key is fully revoked and trusted by no node, and if any live-
sensitive material remains, rewrite history (BFG/`git filter-repo`) before opening. Treat this as a
release gate, not a nice-to-have.

### Why keep GLESAC closed
GLESAC is the commercial tier by design, and the one-directional coupling (core never references
GLESAC; GLESAC never on the public gate surface) is a deliberate security and business boundary.
Opening it would both surrender the monetization surface and blur a separation that currently keeps
the core's public story clean. Keep it proprietary; market it, don't publish it.

---

## 4. Risks & gaps (the candid part)

1. **No external validation (G5).** Every test and review to date is the author's or author-run
   cross-model convergence (Cursor/OpenAI/Grok) — which the project correctly labels as *not*
   external validation. This is the defining maturity gap, and it is blocked on the safe-harbor
   clause. Until an independent party attacks the live surface, "unbroken" means "un-attacked."
2. **Deployed reality trails the repo.** The impressive layers (governance/HIL, mTLS non-bypass,
   typed impact) are not on the live nodes, and the deployed commit is internally ambiguous
   (`3343e32` vs `bd1159b`). The live surface is a genuine but *partial* demonstration of the claimed
   system. Resolve the divergence and decide, deliberately, whether to deploy the newer layers (the
   coordinated re-pin we scoped in `deploy/TYPED_IMPACT_DEPLOY.md`) or keep the honest "core-only"
   scope.
3. **Bus factor / single custody.** One author holds all copyright, all keys, all operations, and
   all custody. For a product whose entire value proposition is *trustworthy governance*, single-
   person key custody and no documented recovery/succession is itself a governance risk an adopter
   will ask about. Document key custody + recovery, and consider a second maintainer or key escrow.
4. **Complexity / onboarding cost.** The rigor produces a large surface — canon, ledger volumes,
   dozens of deploy docs, session protocols. Onboarding the external contributors the challenge is
   trying to recruit is hard. A concise "contributor start-here" + architecture map would lower the
   barrier (the CONTRIBUTING.md exists; make it the front door).
5. **Demand validation.** The thesis is compelling and the MCP/executor-SDK integration surface is
   the right hook, but there is no non-author user or design partner yet. One real agent deployment
   would validate demand and produce the first independent reference.

---

## 5. Prioritized recommendations

1. **Scrub history, then make the Elyon-Sol core repo public.** (Highest leverage; resolves the
   open-core incoherence and unlocks the challenge premise. Gate on the secret-history audit — the
   VL-108 key exposure makes this non-negotiable.)
2. **Finalize the safe-harbor clause and open the red-team challenge.** This is the only path to G5;
   nothing else raises credibility as much.
3. **Keep GLESAC proprietary; productize and name it** as the commercial operator tier; publish a
   console demo (not source).
4. **Reconcile the deployed-commit divergence and decide the live-surface scope** — either deploy the
   governance/typed-impact layers via the coordinated re-pin, or keep the disclosed core-only scope,
   but end the internal ambiguity.
5. **Fix site staleness** (derive the test count; re-verify every claim against deployed reality;
   keep the honest-scope notes).
6. **Address bus-factor**: document key custody/recovery; plan a second maintainer or escrow.
7. **Land one design partner / real agent integration** to validate demand and generate a non-author
   reference.
8. **Re-issue the R1 approver key-record before 2026-08-03** and reboot the gate host — operational
   hygiene that, left undone, fail-closes the live gate to refuse-all.

---

## Bottom line

The engineering and intellectual honesty here are well above what a solo project usually shows, and
the open-core + proprietary-console structure is sound. The project is being held back not by its
technology but by two self-imposed blocks: **a private repo that contradicts its own open-core, made-
to-be-attacked thesis**, and **an unsigned safe-harbor clause that keeps the external validation it
needs from ever starting.** Clear those two — after a careful history scrub — and Elyon-Sol converts
from "impressive internal artifact" to "credible, inspectable, externally-tested governance
substrate," with GLESAC as its commercial operator tier. That is the whole game.
