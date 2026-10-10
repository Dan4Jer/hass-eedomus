---
title: 'Bug 1.10: dead-window fetch loop on periphs that reached the present'
type: 'bugfix'
ticket: '10'
created: '2026-10-10'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'e36bbab'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The eedomus cloud returns the newest 10,000 points of a
periph whatever the requested window. Once the walk reaches the
present, every pass returns the SAME window (max timestamp frozen at
the cloud's latest point) — `len(chunk) < 10000` never fires, the
periph loops forever on a full chunk, and its quota share of the
drain is wasted every pass (observed live: 1248341, 1091579, 1077374,
1123009, 1090997 looping for hours, retrieved_points inflating by
10k per pass).

**Approach:** Dead-window completion: a chunk whose max timestamp no
longer advances past the previous `last_timestamp` means the walk
holds the newest window the cloud has — mark the periph completed.

## Given/When/Then

- Given a periph whose previous pass set `last_timestamp` to T, when
  a pass returns a full chunk whose max timestamp is <= T, then the
  periph is marked completed and leaves the queue.
- Given a periph mid-walk, when a pass returns a chunk whose max
  timestamp is > T, then the walk continues (not completed).
- Given a periph whose total history is shorter than the chunk cap,
  when the tail pass returns < 10,000 points, then completion behaves
  as before (unchanged path).
- Given a first-ever pass (`last_timestamp` = 0), when any chunk
  returns, then the stale-window check is skipped (nothing to
  compare against).

</frozen-after-approval>

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green, with new regression tests for the stale-window completion
