---
title: 'Story 1.4: background task, .storage progress, CAP-5 indicators, bug 109 fusion, reset action'
type: 'feature'
ticket: '4'
created: '2026-10-08'
status: built
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'd3a57c2'
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The backfill drain runs inside the partial-refresh cycle (scheduled cycles are almost all FULL, so the queue barely drains without manual refreshes); progress and retry state live in state-machine helper states (amnesic to restarts in principle, and bug 109: the 165 History Progress sensors are never mounted); and the CAP-5 progress fields (retrieved/total estimated, oldest timestamp, retention start) exist nowhere, so the indicator cannot be validated.

**Approach:** Move the drain to a dedicated background task (AD-2) cadenced by history_peripherals_per_scan; migrate progress + retry to the existing .storage backfill store (schema v2, one-time migration from the helper states, progress keyed `<entry_id>_<periph_id>` per the spec constraint); write the CAP-5 fields at fetch time (retrieved_points cumulative, total_points estimated = (now − creation_date) / POLLING, oldest timestamp, retention start, value_list hash per AD-6bis with invalidation on change); serve them in get_backfill_state AND get_coherence; mount the History Progress sensors (bug 109 fusion: consume async_setup_history_sensors' return into coordinator._history_sensors); add the fifth CAP-5 action « Réinitialiser la progression » (websocket, per-periph, marker only — statistics never deleted).

## Boundaries & Constraints

**Always:** mono-importer lock guards fetch+import everywhere (worker + retry_now); unload = cancel + await worker + flush the store; a broken store never blocks the coordinator; the partial refresh keeps its ~1 s cadence with no history segment; estimation marked (total ESTIMÉ) in the payload via a boolean; all strings EN with FR translation where user-facing.
**Never:** no state-machine progress helpers after the migration (one-time read, then the states die); no change to the statistics import path (AD-1/AD-11 untouched); no panel rendering of the new fields (story 110); no deletion of imported statistics, ever.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Worker tick with eligible pending periphs | Up to history_peripherals_per_scan fetch+imports under the lock, progress persisted to .storage | None |
| Restart mid-backfill | HA restarts with stored progress | Worker resumes at the persisted last_timestamp; no re-fetch from zero | Existing warning paths |
| Old helper states present | No stored progress, states exist | One-time migration reads the states into .storage, then the states stop being written | Missing/unparseable state skipped |
| value_list changes | Frozen hash differs at fetch | Progress invalidated (re-enters the queue), warning logged | None |
| Reset action | Reset on an eligible non-completed periph | Persisted marker cleared, periph re-queued at zero, statistics untouched | Invalid periph → invalid_format |
| Reset on completed periph | Reset on a completed periph | Same — completed is part of the marker; it re-enters the queue | Ignored/paused refused |
| Global pause | Pause ON | Worker skips its tick, quota not consumed | None |
| Broken store | Store load/save raises | Coordinator starts with empty progress; the refresh flow never depends on it | Warning |
| Estimation impossible | Periph without creation_date/POLLING | total_points None, estimated False — the UI shows what it has | None |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/coordinator.py` — drain segment inside `_async_partial_refresh` (~1082-1150, to extract); `_load_history_progress`/`_save_history_progress` (1402-1455, state machine, to migrate); backfill store `_get_backfill_store`/`_load_backfill_persistence`/`_save_backfill_persistence` (1590-1660, schema + progress migration); `get_backfill_state` (~1395) row builder; `async_fetch_history_chunk` (~1749) progress init/update; BACKFILL_CONFIG_SCHEMA_VERSION + _BACKFILL_MIGRATIONS (const.py or coordinator head — check).
- `custom_components/eedomus/history_sensor.py` — `async_setup_history_sensors` returns sensors (209-258); EedomusHistoryProgressSensor already reads retrieved_points/total_points (87-91).
- `custom_components/eedomus/__init__.py` — call sites 423-425 and 453-456 discard the return (bug 109 fix); entry unload for the worker shutdown.
- `custom_components/eedomus/sensor.py` — 167-169: the `_history_sensors` branch already extends the platform (activates once assigned).
- `custom_components/eedomus/ui_service.py` — backfill command registration area (~296 retry_now) for the reset command; `_json_safe`.
- `tests/unit/test_backfill_commands.py` — store registry (_StubStore), queue derivation, command guards; extend.
- `tests/unit/conftest.py` — storage Store stub already present (registry pattern).

## Tasks & Acceptance

**Execution:**
- [ ] `coordinator.py` — store schema v2: progress + retry in the backfill store, one-time migration from helper states, keyed `<entry>_<periph>`
- [ ] `coordinator.py` — drain extraction: `_backfill_drain_pass(quota)`; background worker task (start, cancel+await+flush on shutdown); partial refresh keeps no history segment
- [ ] `coordinator.py` — fetch path: CAP-5 fields written (retrieved_points, total_points estimated + estimated flag, oldest_timestamp, retention_start, value_list hash + invalidation)
- [ ] `coordinator.py` — `get_backfill_state` rows carry the progress fields; `ui_service.py` get_coherence rows too
- [ ] `coordinator.py` + `ui_service.py` — fifth action `async_backfill_reset_progress` + websocket command `eedomus/backfill_reset_progress` (require_admin)
- [ ] `__init__.py` — capture `async_setup_history_sensors` return into `coordinator._history_sensors` (bug 109); worker shutdown at unload
- [ ] Tests: store-backed persistence across re-instantiation, reset action + guards, estimation + value_list invalidation, worker drain respects quota/pause, partial refresh has no drain segment, coherence rows carry the fields
- [ ] Full suite + JS harness green

**Acceptance Criteria:**
- Given a partial refresh during an active backfill, when it completes, then no history fetch ran inside the cycle and the worker drains from its own cadence
- Given a restart mid-backfill, when the coordinator loads, then progress resumes from .storage (no state-machine helper read after the first migration)
- Given the Sonoff temperature periph completed, when its History Progress sensor renders, then it shows a real percentage from the persisted retrieved/total fields
- Given « Réinitialiser la progression » on an eligible periph, when it runs, then the queue shows it pending at zero and its statistics rows are unchanged

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Design Notes

Worker cadence: one drain pass every 60 s, quota per pass = history_peripherals_per_scan (option, default from const). Store doc: {"ignored", "paused", "global_paused", "config_schema_version": 2, "progress": {"<entry>_<periph>": {...}}, "retry": {...}}. Migration v1→v2: stamp empty progress/retry; the one-time state migration fills progress from eedomus.history_progress_* states on the first load where stored progress is empty.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green
- `node tests/js/test-coherence.js` -- expected: all passed
- Post-deploy manual: queue drains without manual refreshes; a History Progress sensor mounted and live; reset action requeues a periph
