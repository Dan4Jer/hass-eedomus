---
title: 'Story 1.9: the seam probe — periodic cloud re-compare for completed peripherals'
type: 'feature'
ticket: '9'
created: '2026-10-10'
status: done
route: 'full'
route_source: 'auto'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'f2136ae'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The backfill walk is one-shot: a completed peripheral is
never re-fetched. Post-native hours belong to the recorder (AD-11),
but the seam — hours between the walk's last imported point and the
entity's first native statistic (entity registered late, entity
disabled for a while, cloud lag at walk time) — and newly arrived
cloud points after the walk have no mechanism.

**Approach:** The seam probe: when the drain queue is empty, a worker
pass probes ONE completed eligible peripheral (round-robin): fetch
[start = last_timestamp, now], keep ONLY points strictly newer than
last, import them (the AD-11 clip keeps native-owned hours untouched,
the upsert is idempotent — CAP-3), advance last_timestamp to the new
max. Full re-walks of completed history are a documented non-goal:
the cloud does not demonstrably correct old hours, and re-paginating
whole histories hourly would recreate the drain the dead-window fix
(bug 1.10) closed.

## Boundaries & Constraints

**Always:** The probe never flips a completed periph back to pending
(its progress stays completed, it never re-enters the drain queue);
the probe keeps only points strictly newer than last_timestamp —
never an import storm of the newest 10k window; the drain keeps
absolute priority (probe only when the queue is empty); idempotent
upsert (CAP-3) + AD-11 clip preserved.

**Never:** No deep-history re-compare (non-goal, documented); no new
config option (the probe rides the existing worker); no panel change
(112/110 already render the aggregates).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New points | chunk has points > last | Seam import, last_timestamp advances, completed stays | None |
| Nothing new | chunk max <= last | No import, no state change | None |
| Probe error | client raises | Log + skip (probe never poisons the periph's progress) | Warning, no retry queue |
| Queue busy | drain queue non-empty | No probe this pass (drain priority) | None |
| Not completed | periph pending or no progress | Skipped | None |
| History off | option disabled | No probe (worker early return, unchanged) | None |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/coordinator.py:1395-1450` — `_backfill_drain_pass`: after the drain loop, probe one completed periph when the queue was empty; round-robin cursor in memory.
- `custom_components/eedomus/coordinator.py:545-590` (client) — `get_device_history` reused as-is (the probe filters client-side).
- `custom_components/eedomus/coordinator.py:2183-2240` — `async_import_history_chunk` reused as-is (AD-11 clip + idempotent upsert).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` — `async_seam_probe(periph_id)` + worker integration + cursor -- the run's mechanism
- [ ] `tests/unit/test_history_seam_probe.py` — matrix rows as regression tests -- the net

**Acceptance Criteria:**
- Given a completed periph and a cloud chunk containing points newer than last_timestamp, when the probe runs, then those points are imported, last_timestamp advances, and the periph stays completed (never re-queued).
- Given a completed periph whose newest chunk has nothing newer, when the probe runs, then nothing is imported and no state changes.
- Given a non-empty drain queue, when the worker pass runs, then no probe happens (drain priority).

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Design Notes

- Why filter client-side: the real cloud API returns the newest
  10,000 points whatever the window (the bug 1.10 finding) — an
  unfiltered probe would re-import the newest window every pass.
  Filtering to ts > last keeps the delta bounded (typically a
  handful of points).
- Why the probe advances last_timestamp: the next probe resumes from
  the new frontier; the completed flag is never touched, so the
  queue derivation (completed -> out) keeps the periph out of the
  drain.
- Cadence: one probe per worker pass (60 s) round-robin over the
  completed eligible periphs — a full round hourly on this box; the
  cursor resets at restart (a missed round is harmless).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green with the seam-probe regression tests
- `node tests/js/test-coherence.js` -- expected: green (no JS change, guard)
