---
title: 'Box-origin tag on every log line of the integration (ticket 113)'
type: 'feature'
ticket: '113'
created: '2026-10-10'
status: done
baseline_revision: '4e74dba316ee0214371b4bd0d1ab02d7a74242a6'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      Backfill worker-loop wrapper is untested: drain-pass tests call the
      method directly, outside the loop, so deleting the box context at
      the loop level would keep the suite green.
    evidence: >-
      The tagging mechanism is the same one verified by
      test_coordinator_refresh_tags_log_lines at _async_update_data; closing
      the loop-level gap needs a loop-body seam the repo's direct-call test
      style does not have. Fold into any future backfill-worker test work.
    location: >-
      custom_components/eedomus/coordinator.py:1510
    severity: low
  - summary: >-
      entity.py manifest-read except logs via _LOGGER before the assignment
      executes, so a manifest-read failure raises NameError on the warning
      path instead of logging it.
    evidence: >-
      Pre-existing latent NameError, present before this change (the old
      code had the same order); not caused by this build. Fix is reordering
      the assignment above the try block.
    location: >-
      custom_components/eedomus/entity.py:24
    severity: low
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

- Implemented by subagent impl-113-2 (first dispatch impl-113 died on a model stream failure before writing anything; tree was clean, fresh dispatch made; the patch round re-engaged the same agent, commit `820a7bc`). During patching the agent briefly corrupted the git index with `git stash` and recovered it with a mixed `git reset` — verified by the orchestrator afterwards: history intact, tree clean, `git fsck` clean.
- Plan naming error adapted: the refresh entry point is `_async_update_data` (not `_async_refresh_data`); wrapped as a thin `box_log_context` wrapper around `_async_update_data_untagged`, preserving every existing call site including HA's framework calls.
- Committed by the implementer as `47f4da7` on `unstable` (31 files, +647/−168; tree clean per repo policy). Not pushed — push+deploy stays the user's step.
- `resolve_box_tag` also reads `entry.data["api_host"]` beyond the plan's three sources, plus a final `"unknown"` guarantee; mirrors `coordinator._box_display_name` order (title → host → entry_id).
- Cross-box cleanup services (`cleanup_unused_entities/devices`) stay untagged by design: they act on the whole instance, not one box (plan boundary, noted here for the reviewer).
- Matrix row "Domain service, 2 boxes" is covered by mechanism tests (`test_inner_context_wins` alternation + `test_tag_reaches_every_module_logger` + coordinator refresh test) rather than a service-fan-out test; the service handlers use the same context manager. Residual risk: the service fan-out path itself has no direct unit test — the live deploy log will show it.
- Verification re-run by the orchestrator, not trusted from the report: `pytest tests/unit/ -q` 413 passed; `node tests/js/test-coherence.js` green; grep `logging.getLogger(__name__)` zero hits outside backups.
- entity.py pre-existing latent issue (manifest-read `except` logs before `_LOGGER` assignment) left untouched, per minimal-diff.

## Plan Change Log

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 23 findings — high 0, medium 6, low 11, false 3, maybe-false 3
- findings:
  - `[medium]` `[patch]` services.py: box contexts span only the awaited call — the handlers' own failure/success lines (the ones multi-box diagnosis most needs) emit untagged; the refresh-wrapper also duplicates the coordinator's own tagging — re-span each handler's context over the full per-box handling (blind-hunter #2, #3, grouped)
  - `[medium]` `[patch]` coordinator.py: `async_set_periph_value` (and the climate set path) emit untagged when called from entity commands (light.py, climate.py direct calls) while the same call via `eedomus.set_value` is tagged — self-tag at the coordinator method level, mirroring `_async_update_data` (blind-hunter #4 + verification-gap #3, grouped)
  - `[medium]` `[patch]` no test executes a domain-service handler nor any concurrent two-box scenario — add a caplog test over two stub coordinators run concurrently, asserting each box's lines carry only its tag (blind-hunter #9 + verification-gap #1, grouped; closes the matrix row "Domain service, 2 boxes")
  - `[medium]` `[patch]` webhook post() rewrite has zero test coverage and accepts a non-dict JSON body (AttributeError → 500 instead of 400) — add isinstance(data, dict) → 400 and a stub-request unit test covering 403/400/OK with tag assertions (blind-hunter #8 + verification-gap #2, grouped)
  - `[low]` `[patch]` sweep guards match only the `_LOGGER` name and the exact `logging.getLogger(__name__)` literal — widen to flag any `logging.getLogger(` outside `log.py` (blind-hunter #10 + verification-gap #4, grouped)
  - `[low]` `[patch]` `test_get_logger_filter_attached_once` asserts the getLogger singleton, not idempotence — assert exactly one `_BoxTagFilter` in `logger.filters` after repeated calls (blind-hunter #1)
  - `[low]` `[defer]` backfill worker-loop wrapper untested — the mechanism is verified at `_async_update_data`; closing this needs a loop-body seam the direct-call test style lacks (verification-gap #5, filed disposition defer)
  - `[low]` `[defer]` entity.py manifest-read `except` logs `_LOGGER` before its assignment — pre-existing latent NameError on an error path, not caused by this change (blind-hunter #12)
  - `[false]` `[reject]` HA base-class coordinator failure lines untagged — refuted: the coordinator passes its own factory-built `_LOGGER` to `DataUpdateCoordinator` (coordinator.py:94-99), so "Timeout fetching"/"Error fetching" flow through the tagged logger (blind-hunter #5)
  - `[low]` `[reject]` tag as structured attribute instead of `record.msg` — design settled in the plan's Design Notes (HA stock format visibility, caplog assertability); named harm is hypothetical future shippers (blind-hunter #6)
  - `[low]` `[reject]` webhook entry resolution before IP check — the scan cost is negligible and the current order is what tags the unauthorized-IP warning; the proposed fix would untag it (blind-hunter #7)
  - `[low]` `[reject]` duplicated tag resolution — the fallback order lives in one place (`resolve_box_tag`); only the accessor pattern repeats, no named divergence (blind-hunter #11)
  - `[maybe-false]` `[reject]` executor-thread logging untagged — no demonstrated box-contexted logging from a thread; if true, harm is low (rare setup-time mapping warnings) (blind-hunter #13 + edge-case #1, same mechanism)
  - `[maybe-false]` `[reject]` task spawned inside a context outlives it → stale tag — no long-lived task spawn inside a box context shown; if true, low (short-lived children) (edge-case #4)
  - `[low]` `[reject]` config entry removed between webhook capture and reload — millisecond window inside one request; consequence is an HA-side warning (edge-case #2)
  - `[false]` `[reject]` `[box: unknown]` tag misleading when entry is gone — the tag states exactly what is known; no misattribution to a wrong box occurs (edge-case #3)
  - `[false]` `[reject]` non-string `record.msg` coerced by the f-string — no crash, behavior identical to standard %-formatting; no non-string call site exists in the package (edge-case #5)

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

## Auto Run Result

**Summary.** Ticket 113 built: every log line the integration emits during box-scoped work now ends with ` [box: <config entry title>]` (fallback api_host → entry_id → unknown), via a single ContextVar-driven tagging engine (`log.py`), a factory sweep over all 29 real modules (no call-site rewrite), and box contexts at every per-box operation boundary: coordinator refresh (`_async_update_data`), backfill worker, `async_set_periph_value` (all callers), the four domain-service handlers, and the whole webhook handler.

**Files changed.**
- `custom_components/eedomus/log.py` — NEW: get_logger / _BoxTagFilter / box_log_context / resolve_box_tag
- `custom_components/eedomus/coordinator.py` — factory + refresh, backfill and set-value self-tagging wrappers
- `custom_components/eedomus/services.py` — factory + full-span per-box contexts in all four handlers
- `custom_components/eedomus/webhook.py` — factory + whole-handler context + non-dict body 400
- 25 other modules — mechanical factory sweep
- `tests/unit/test_box_log_tag.py` — NEW: 22 tests (engine, coordinator, concurrent two-box service fan-out, webhook 403/400/OK, single widened sweep guard, idempotence pin)

**Review findings breakdown.** Thorough review (4 lenses), 23 findings: 0 high, 6 medium, 11 low, 3 false, 3 maybe-false. 6 patch entries applied by the implementer (commit `820a7bc`): services context re-span (2 findings), coordinator set-value self-tag (2), concurrent two-box service test (2), webhook validation + tests (2), widened sweep guard (2), idempotence pin (1). 2 deferred (backfill loop test seam; entity.py pre-existing NameError). 15 rejected with reasons in the Review Triage Log — notably the "HA failure lines untagged" claim refuted (the coordinator passes its own tagged logger to `DataUpdateCoordinator`) and executor-thread concerns left maybe-false at if-true low.

**Follow-up review recommendation.** `true` — three medium entries were patched on this first pass. Named unverified risk: the multi-box observable on a real install (live log lines carrying `[box: ...]` on the Pi) is untested — E2E live-Pi was not run by this build, and the patched surfaces (entity command paths, webhook) are exercised by unit stubs only.

**Verification performed.** `python3 -m pytest tests/unit/ -q` — 418 passed, 2 warnings (pre-existing RuntimeWarnings). `node tests/js/test-coherence.js` — all coherence tests passed. Sweep grep — zero `logging.getLogger(` in the package outside `log.py`, enforced permanently by the widened guard test. Repository: clean tree, commits `47f4da7` + `820a7bc` on `unstable`, not pushed.

**Residual risks.** E2E live-Pi check pending at the user's deploy step; untagged-by-design boundary (import-time, config flow pre-entry, cross-box domain operations) documented in the intent-contract; executor-thread and stale-task-tag scenarios remain maybe-false at if-true low.
