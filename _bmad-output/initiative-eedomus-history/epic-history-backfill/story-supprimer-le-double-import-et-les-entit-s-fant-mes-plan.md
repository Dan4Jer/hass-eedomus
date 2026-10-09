---
title: 'Story 1.3: remove the double-import and the ghost sensor.eedomus_* artifacts'
type: 'chore'
ticket: '3'
created: '2026-10-08'
status: built
route: 'oneshot'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
baseline_revision: '8f71efc'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The backfill cycle still writes `sensor.eedomus_*` helper states through the state machine (`_create_error_sensors`: errors_total, completed, per-periph error states), and the live database carries 28 orphan `sensor.eedomus_*` statistics_meta rows (21 old history_error_*, the timing helpers, and the test statistic id 573 named in the ticket) — long-term statistics polluted by helper states.

**Approach:** Remove `_create_error_sensors` and its two call sites (its information is served by CAP-5 `get_backfill_state` and the panel), drop the dead test mocks, add a regression test asserting a backfill cycle never writes a `sensor.eedomus_*` state; after deploy, purge the orphan statistics_meta + statistics rows and let the restart drop the helper states (the four timing-helper states have no current setter — they vanish at restart).

## Boundaries & Constraints

**Always:** the registered timing entities (`sensor.box_eedomus_*`) and the CAP-5 websocket view stay untouched; the purge targets only `sensor.eedomus_*` statistics_meta ids (verified live list, 28 ids incl. 573); counts recorded before and after the DELETE.

**Never:** no DELETE on any other statistic_id pattern; no change to the recorder import path; no touch to the backfill queue logic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | A partial refresh cycle with history enabled | No `sensor.eedomus_*` state written | None |
| Error queue | A periph in error during a cycle | No `sensor.eedomus_history_error_*` state; the error lives in the CAP-5 view | None |
| Live purge | 28 orphan meta rows | Rows + their statistics deleted, counts logged | Transaction; backup-safe (no other pattern touched) |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/coordinator.py` — `_create_error_sensors` (1972-2035) + call sites 1146 (partial refresh) and 1962 (fetch path). Nothing else writes sensor.eedomus_* (grepped: the four timing helpers have no current setter).
- `tests/unit/test_backfill_commands.py:92`, `test_coordinator_partial_refresh.py` (5 sites), `test_history_value_resolution.py:237` — dead `_create_error_sensors` mocks to drop.
- Live DB: `statistics_meta` ids LIKE 'sensor.eedomus_%' (28, incl. 573) + their `statistics` rows.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` — remove the method + its two call sites
- [ ] 4 test files — drop the dead mocks
- [ ] `tests/unit/test_coordinator_partial_refresh.py` — new regression test: a full cycle writes no sensor.eedomus_* state
- [ ] Run the suite; then at the deploy checkpoint: purge the 28 meta rows + statistics rows, verify post-restart no sensor.eedomus_* state exists

**Acceptance Criteria:**
- Given a full backfill cycle with a periph in error, when it completes, then no `sensor.eedomus_*` state exists in the state machine
- Given the live instance post-deploy, when the purge ran, then zero `sensor.eedomus_*` rows remain in statistics_meta and the test statistic 573 is gone

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green
- Post-deploy: `sudo sqlite3 /homeassistant/home-assistant_v2.db "SELECT COUNT(*) FROM statistics_meta WHERE statistic_id LIKE 'sensor.eedomus_%';"` -- expected: 0
