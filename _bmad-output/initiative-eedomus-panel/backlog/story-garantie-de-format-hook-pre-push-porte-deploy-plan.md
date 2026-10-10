---
title: 'Format guarantee: pre-push hook + deploy-script gate (ticket 115)'
type: 'feature'
ticket: '115'
created: '2026-10-10'
status: done
baseline_revision: '132a719982243cd34a8ea8aad3a99546d2ab3041'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      AGENTS.md still tells agents to keep lines <= 88 chars manually and
      never claim formatting was run; black now enforces style beyond line
      length, so an agent following AGENTS.md literally can produce a tree
      the new hook refuses to push.
    evidence: >-
      Real conflict, but the fix edits an agent-context file (AGENTS.md),
      which review triage routes to defer, not patch. The line should
      become: run the pinned black/isort via uv before committing
      (commands in scripts/hooks/README.md).
    location: >-
      AGENTS.md, "Running and verifying" section
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Nothing in the delivery chain guarantees the ≤ 88-char/black/isort format: the rule is held by hand, GitHub jobs run after the local git-only deploy, and the tree is in fact not format-clean (black: 53 files would be reformatted).

**Approach:** Two local locks plus the one-time format pass that makes them viable: (1) format the tree once with black + isort (pyproject config already sets line-length 88, py39, profile black); (2) a `pre-push` git hook refusing any push — any remote, any branch — whose tree fails `black --check` / `isort --check-only`; (3) the same checks as a gate in the deploy script's pre-deployment section, catching code already pushed from another machine. No permanent tooling: black/isort run in ephemeral uv environments (`uv run --with black --with isort -- python -m ...`; `uvx` shims are broken on this machine — realpath missing — so the hook uses `uv run`).

## Acceptance Criteria

1. **Malformatted push refused**
   **Given** a tree that fails `black --check` or `isort --check-only`
   **When** a push to any remote of the repo is attempted (after the hook is installed)
   **Then** the pre-push hook exits non-zero, refusing the push, and names the failing tool
2. **Deploy gate blocks dirty format**
   **Given** committed code that fails the format checks
   **When** `deploy_hass_eedomus.sh` runs its pre-deployment checks
   **Then** the script exits 1 before any deployment, naming the failing tool
3. **Clean tree passes**
   **Given** the one-time format pass applied to `custom_components/`, `tests/unit/`, and the Python files under `scripts/`
   **When** the same checks the hook runs are executed
   **Then** they pass, and the unit suite (`pytest tests/unit/`) and `node tests/js/test-coherence.js` stay green
4. **No permanent install**
   **Given** any machine with `uv` only
   **When** the hook or the deploy gate runs
   **Then** black and isort resolve from ephemeral uv environments; nothing is installed into the system
5. **Human step (hitl)**
   **Given** the hook file committed at `scripts/hooks/pre-push`
   **When** the user installs it (per machine)
   **Then** `scripts/hooks/install.sh` sets `core.hooksPath` to `scripts/hooks` idempotently and prints what it did

## Boundaries

- No CI auto-fix job: GitHub jobs run after the local deploy (forge decision, 2026-10-10).
- No edits to `*.backup*` files (black never picks them up: not `.py`).
- The build does NOT install the hook (per-machine person step, `install.sh` is provided); the build does verify the hook script's behavior directly by invoking it.
- AGENTS.md's "black/isort are NOT installed locally" line stays true (uv ephemeral); the build does not rewrite AGENTS.md.

</intent-contract>

## Implementation Notes

Oneshot because the whole change is one mechanical formatter pass plus three small files (hook, installer, deploy gate edit); no subagent needed. The one-time format pass is mandatory scope: without it the hook would refuse every push from day one.

## Verification

**Commands:**
- `uv run --quiet --with black --with isort -- python -m black --check custom_components/ tests/unit/ scripts/` — expected: "All files already formatted" (the exact command set the hook runs; same for isort)
- `uv run --quiet --with isort --with black -- python -m isort --check-only custom_components/ tests/unit/ scripts/` — expected: no ERROR lines
- `python3 -m pytest tests/unit/ -q` — expected: suite green after the format pass (formatting is semantics-preserving; import order changes are covered by the conftest stubs)
- `node tests/js/test-coherence.js` — expected: green
- Direct hook invocation with a temporarily malformatted temp file (or a forced check failure) — expected: non-zero exit naming the tool; clean tree — expected: exit 0
- `bash -n` on the hook and installer — expected: syntax OK

**Manual checks (if no CLI):**
- The actual `git push` refusal and the deploy-script gate fire only after the user installs the hook / runs a deploy — both are the user's steps (hitl), verified here by direct script invocation instead.

## Review Triage Log

### 2026-10-10 — Review pass (quick)
- verdicts: 6 findings — high 0, medium 4, low 2, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` deploy gate checked the local tree while what deploys is origin/unstable (the Pi pulls it) — added a local HEAD == origin/$BRANCH assertion before the format checks, refusing deploy with a clear message on mismatch
  - `[medium]` `[patch]` untracked files (never deployed, "warning only" per the script's own policy) could block the gate — hook and gate now check tracked files only (`git ls-files`)
  - `[medium]` `[patch]` black/isort unpinned: an upstream formatter release or a two-machine version split could block every push — pinned to the versions that formatted the tree (`black==26.10.1`, `isort==9.0.2`) in hook, gate, and README
  - `[low]` `[patch]` uv missing/offline was misreported as a format failure naming the wrong tool — hook and gate now fail OPEN with a warning when uv is absent; the deploy gate remains the backstop
  - `[medium]` `[defer]` AGENTS.md's "keep lines ≤ 88 manually" line now contradicts the guarantee (black enforces more than line length) — fix edits an agent-context file, deferred to the frontmatter list
  - `[low]` `[reject]` plan's Verification section documents a combined `--with black --with isort` command while the hook runs `--no-project` separate envs — the fix edits the plan's own text, and the verification that actually ran used the hook's exact form (recorded below); rejected per triage rules

## Auto Run Result

**Summary.** Ticket 115 built: a one-time black+isort format pass (114 files reformatted, byte-identical to formatter output — verified by the reviewer), a version-pinned pre-push git hook (`scripts/hooks/pre-push`) refusing any push whose tracked Python files fail the checks, an idempotent per-machine installer (`scripts/hooks/install.sh`, sets `core.hooksPath`), a README, and a deploy-script gate that asserts local HEAD == origin/unstable before running the same checks.

**Files changed.** 120 files: the format pass over `custom_components/`, `tests/unit/`, `scripts/`; NEW `scripts/hooks/{pre-push,install.sh,README.md}`; format gate added to `.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh`; this plan.

**Review findings breakdown.** Quick review (1 lens), 6 findings: 4 patches applied by the orchestrator (oneshot route): origin/HEAD assertion (medium), tracked-files-only (medium), version pinning (medium), uv fail-open (low). 1 deferred: AGENTS.md "≤ 88 manually" line (medium, agent-context file). 1 rejected: plan verification-command text (fix edits the plan; the executed verification used the hook's exact commands).

**Follow-up review recommendation.** `true` — three medium entries were patched on this first pass. Named unverified risk: the deploy gate's HEAD==origin assertion and the full deploy flow are verified only by `bash -n` and the hook's identical command paths; an actual deploy run (which contacts the Pi) is the user's step and has not been exercised.

**Verification performed.** Hook direct invocation: clean tree exit 0; untracked bad file exit 0 (not blocking); tracked bad file exit 1 naming black (file reverted from the index afterwards); uv absent exit 0 with warning. `uv run --no-project --with black==26.10.1 -- python -m black --check` on tracked files — all unchanged; isort --check-only — no errors. `python3 -m pytest tests/unit/ -q` — 418 passed, 2 warnings (pre-existing). `node tests/js/test-coherence.js` — green. `bash -n` on hook, installer, deploy script — OK. Installer ran idempotently (reviewer-verified).

**Residual risks.** The human step remains: `bash scripts/hooks/install.sh` per machine (hitl) — the hook is committed but NOT installed on this machine by the build; the deploy gate (fail-open on missing uv) is the backstop until then. The AGENTS.md contradiction is deferred. uv's ephemeral env occasionally prints interpreter-teardown noise to stderr (machine-local cache quirk); exit codes observed stable and the hook keys on exit codes only.
