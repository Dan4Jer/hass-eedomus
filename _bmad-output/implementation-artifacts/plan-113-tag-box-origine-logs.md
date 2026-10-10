---
title: 'Box-origin tag on every log line of the integration (ticket 113)'
type: 'feature'
ticket: '113'
created: '2026-10-10'
status: 'in-progress'
baseline_revision: '4e74dba316ee0214371b4bd0d1ab02d7a74242a6'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** On a multi-box install no log line says which box emitted it; the 29 integration modules each roll their own `logging.getLogger(__name__)` (746 call sites), so multi-box bugs (#102, #103) had to be diagnosed blind.

**Approach:** A shared logging module (`log.py`) with a `ContextVar`-driven tag filter: a `get_logger(name)` factory, a `box_log_context(box_name)` context manager set around every per-box operation (coordinator refresh, backfill, service handling, webhook), and a filter that appends ` [box: <name>]` to each record emitted inside a box context. A mechanical sweep switches all real modules to the factory; no call site is rewritten.

## Boundaries & Constraints

**Always:**
- Logger names stay exactly `custom_components.eedomus.<module>` (unit tests pin them via `caplog.set_level(logger="custom_components.eedomus.coordinator")`).
- The filter never drops or rewrites records; it only appends the tag when a box context is set.
- Box tag resolution order: config entry title → `api_host` → `entry_id` (mirror of `coordinator._box_display_name`, coordinator.py:1421).
- All new log text in English; lines ≤ 88 chars; messages in the HA log show the tag without formatter changes (append to the record message).

**Never:**
- No per-entry child logger names (breaks pinned caplog tests).
- No rewriting of the 746 `_LOGGER.` call sites; no edits to `*.backup*` files.
- No tag on lines emitted outside any box context (module import in `entity.py:64-110`, config flow before a connection, domain-level mapping helpers). This is a documented boundary, not a failure.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Box-scoped refresh | Coordinator refresh for box "Salon" runs inside box context | Every line logged during that refresh ends with ` [box: Salon]` | No error expected |
| Domain service, 2 boxes | `eedomus.set_value` reaches each coordinator in turn | Lines emitted for each box carry that box's tag, alternating | No error expected |
| Outside box context | Startup, import-time logging, config flow pre-entry | Lines emitted untagged; no crash, filter passes records through | No error expected |
| Re-entrant context | A second `box_log_context("Box2")` opens inside box A's context | Inner context wins until it exits, then A's tag resumes | No error expected |
| Unresolvable title | Entry with empty title, no api_host | Tag falls back to `entry_id`; never an empty ` [box: ]` | Fallback, not error |

</intent-contract>

## Code Map

- `custom_components/eedomus/log.py` -- NEW: `get_logger(name)` (idempotent filter attach), `_BoxTagFilter` (reads ContextVar, appends tag to `record.msg`), `box_log_context(name)` (ContextVar set/reset), `resolve_box_tag(entry, client=None)` (title → api_host → entry_id).
- `custom_components/eedomus/coordinator.py:34` -- `_LOGGER` switches to `get_logger`; constructor `(hass, client, scan_interval)` at :90-99 passes `_LOGGER` to `DataUpdateCoordinator` (keep passing the same-name logger). `_box_display_name` (:1421) is the tag resolution precedent; wrap `_async_refresh_data` and the backfill worker pipelines in `box_log_context`.
- `custom_components/eedomus/services.py:18-35` -- `_get_all_coordinators`: wrap each coordinator's handling in `box_log_context` in every domain-service handler.
- `custom_components/eedomus/webhook.py:31` -- holds `entry_id`; tag with the resolved entry title.
- `custom_components/eedomus/__init__.py:308,320` -- per-entry client + coordinator creation; no signature change needed (tag resolves through `client.config_entry`).
- All real modules with `_LOGGER = logging.getLogger(__name__)` (29, list in explore notes): `__init__.py:51`, `api_proxy.py:15`, `binary_sensor.py:18`, `climate.py:20`, `config_flow.py:67`, `config_manager.py:16`, `cover.py:14`, `device_mapping.py:21`, `eedomus_client.py:29`, `endpoint_volume_sensor.py:20`, `entity.py:28`, `history_sensor.py:18`, `light.py:26`, `mapping_registry.py:6`, `mapping_rules.py:7`, `options_flow.py:58`, `panel.py:26`, `refresh_timing_sensor.py:20`, `scene.py:14`, `schema_service.py:12`, `select.py:14`, `sensor.py:16`, `switch.py:14`, `text_sensor.py:20`, `ui_service.py:17` -- switch to `_LOGGER = get_logger(__name__)`.
- `tests/unit/conftest.py:1-10` -- HA stubbed in sys.modules; tests import integration modules directly. New tests follow `tests/unit/test_coordinator_partial_refresh.py:87-128` caplog pattern.
- DO NOT TOUCH: `options_flow.py.backup*`, `services.py.backup` (stale, but never swept).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/log.py` -- create the factory, filter, context manager, and tag resolver -- the single tagging engine; no other module duplicates it
- [ ] `custom_components/eedomus/coordinator.py` -- adopt `get_logger`; wrap the refresh pipeline and backfill worker in `box_log_context` (tag from `resolve_box_tag`) -- the highest-volume per-box emitters (122 sites)
- [ ] `custom_components/eedomus/services.py` -- adopt `get_logger`; tag each coordinator turn in domain-service handlers -- services fan out across boxes (#103 context)
- [ ] `custom_components/eedomus/webhook.py` -- adopt `get_logger`; tag via its `entry_id` -- per-box webhook path
- [ ] remaining 25 modules -- mechanical sweep to `_LOGGER = get_logger(__name__)` -- uniformity: the sweep guard test requires it everywhere
- [ ] `tests/unit/test_box_log_tag.py` -- unit tests: tag injected inside context, absent outside, inner context wins, fallback to entry_id, plus a sweep guard walking `custom_components/eedomus/*.py` (excluding `*.backup*`) asserting every `_LOGGER` assignment uses `get_logger` -- makes the AC machine-checkable

**Acceptance Criteria:**
- Given a coordinator refresh on a multi-box install, when the refresh logs, then every line from any platform module carries that box's tag
- Given a domain service handled across two boxes, when each coordinator processes it, then the log trail distinguishes the boxes by tag alone
- Given a line emitted outside any box context, when it is logged, then it passes through untagged and the unit suite stays green
- Given the full module sweep, when the sweep guard test runs, then no real module logs through a logger that bypasses the factory

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Design Notes

Why ContextVar + filter instead of a per-entry child logger or `LoggerAdapter`: HA's caplog-based tests pin logger names (`custom_components.eedomus.coordinator`), and 746 call sites make adapter threading prohibitive. A `ContextVar` propagates across `await` inside one task, so wrapping only the handful of per-box operation entry points tags all downstream logging from every module with zero call-site edits. `contextvars.copy_context()` semantics guarantee the inner-context-wins behavior.

Tag format: append ` [box: <title>]` to the record message (example: `Refresh complete (165 peripherals) [box: Salon]`) — visible in HA's stock log format with no formatter change, and assertable via `caplog.text`.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: full suite green, including the new `test_box_log_tag.py`
- `node tests/js/test-coherence.js` -- expected: green (JS panel untouched; sanity that nothing regressed)
- `grep -rn "logging.getLogger(__name__)" custom_components/eedomus/ --include="*.py"` -- expected: zero hits outside `log.py` itself

**Manual checks (if no CLI):**
- E2E (`tests/e2e/`, live Pi) is not run by the build; the deploy+live check that logs show `[box: ...]` on the real install happens after, at the user's deploy step.
