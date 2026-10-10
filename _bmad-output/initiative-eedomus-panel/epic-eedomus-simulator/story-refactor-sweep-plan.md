---
title: 'Story 5.4: refactor sweep (end of epic)'
type: 'chore'
ticket: '4'
created: '2026-10-10'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
baseline_revision: '4a8e8fa'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** End-of-epic cleanup pass (entry scope: build records +
deferred findings). There are no deferred findings (no
deferred-work.md exists); the build records of 5.1–5.3 carry no open
cleanup. The only stale artifacts are the four standalone review
prompts written when the session's subagent limit blocked the 5.2
lenses — the user declined the manual-review path, the review was
pinned to none, and the decision is recorded in 5.2's triage log.

**Approach:** Delete the four unused review-5-2-*.md prompt files;
verify no dead artifacts remain in the tree; keep the fmo01 git
remote (documented provenance, 5.1's record).

## Boundaries & Constraints

**Always:** Cleanup only — no behavior change; all suites stay green.

**Never:** No code refactor beyond deletion (nothing was flagged);
no marker/selection change (e2e_sim intentionally carries both
markers so `-m "not e2e"` deselects both strates).

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 379 green
- `node tests/js/test-coherence.js` -- expected: green
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 33 collected (29 live-Pi + 4 e2e_sim)
