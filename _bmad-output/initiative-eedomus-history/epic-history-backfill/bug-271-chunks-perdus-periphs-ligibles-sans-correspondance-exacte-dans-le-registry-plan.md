---
title: 'Bug 1.11: chunks silently lost on peripherals without an exact registry match'
type: 'bugfix'
ticket: '11'
created: '2026-10-10'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
baseline_revision: '999942f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `async_import_history_chunk` resolves its statistics
target with an exact registry match (AD-8bis); a peripheral without
one is skipped with a warning while the fetch already advanced its
progress — the chunk is lost silently. 271 chunks were observed
(2026-10-03..07).

**Approach:** Root cause verified on the live box: every affected
peripheral (usage 14/15/19/38/42/43/82) maps to climate/select —
their eligibility predated the AD-3 fix (story 1.7), and the queue
now derives strictly from `_backfill_eligible_peripherals` (numeric
sensors), so the loop can no longer recur. The hardening that
remains: an eligible sensor that still fails resolution repeatedly
has no importable target — after 3 consecutive misses it leaves the
queue (progress popped, persisted) instead of burning every chunk.

## Given/When/Then

- Given an eligible periph whose entity never resolves, when 3
  consecutive imports miss the registry match, then the periph is
  removed from the queue and the removal is persisted.
- Given a periph whose resolution succeeds, when an import runs,
  then the miss counter resets (a later transient miss starts over).
- Given a periph with 1-2 misses, when the next import resolves,
  then it stays in the queue (transient failures tolerated).
- Given a removed periph, when the user fixes the mapping and resets
  the progress, then it re-enters the queue (reset path unchanged).

</frozen-after-approval>

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green, with regression tests for the miss counter
