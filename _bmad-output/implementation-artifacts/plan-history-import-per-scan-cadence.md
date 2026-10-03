---
title: 'History import per-scan cadence + E2E websocket timeout'
type: 'bugfix'
ticket: ''
created: '2026-10-03'
status: 'built'
baseline_revision: '404a659c52504dd87177dc4d01faf3e52cf094ed'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md
warnings: []
deferred:
  - summary: >-
      E2E panel suite and reload-latency check are unverified: they require
      deploying this change to the live Pi (push + deploy), which this
      unattended run forbids.
    evidence: >-
      Local E2E against the undeployed instance cannot exercise the fix;
      what settles it: deploy to the Pi, then run
      `python3 -m pytest tests/e2e/test_e2e_panel.py -v` (expect 7/7 in
      under ~2 min) and check the log for one PARTIAL REFRESH per cycle
      with `History: <N periphs>` and a save_mapping reload completing
      in seconds.
    location: tests/e2e/test_e2e_panel.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The E2E panel test `test_identical_save_applies_and_changes_nothing` (tests/e2e/test_e2e_panel.py) hangs indefinitely: `eedomus/save_mapping` awaits the entry reload, and every reload runs a full history import inside the first refresh (~90 peripherals, ~180 s measured), because the coordinator never reads `CONF_HISTORY_PERIPHERALS_PER_SCAN` (const.py:35, default 1) — the per-refresh loop processes every pending periph at once. The E2E ws helper (tests/e2e/conftest.py, `ws_call` fixture) has no timeout, so the test never fails, it just blocks. This also contradicts architecture AD-2 (history import must not block the real-time refresh cycle; it is cadenced by `history_peripherals_per_scan`).

**Approach:** Two small changes. (1) In `EedomusDataUpdateCoordinator._async_partial_refresh` (custom_components/eedomus/coordinator.py, history loop at ~line 967), honor the per-scan quota: read `CONF_HISTORY_PERIPHERALS_PER_SCAN` via `_get_config_value(self.client.config_entry, CONF_HISTORY_PERIPHERALS_PER_SCAN, DEFAULT_HISTORY_PERIPHERALS_PER_SCAN)` (helper imported at coordinator.py:25; constants already imported from .const at line 14 — verify and add to that import if missing), then process history for at most N pending peripherals per refresh cycle (a decrementing counter in the existing loop; periphs beyond the quota stay pending and drain on later scans). (2) In tests/e2e/conftest.py `ws_call`, wrap the final `await ws.recv()` (and the send/recv sequence) in `asyncio.wait_for(..., timeout=...)` with `E2E_WS_TIMEOUT` (env override, default 120 s) so a slow or stuck command raises instead of hanging.

Invariants: the periph history-processing condition (`periph_id in peripherals_for_history` and not completed in `self._history_progress`) is otherwise unchanged; quota applies only to how many are processed per cycle, not to which API call is made. `_history_progress` remains in-memory (no persistence — that is AD-2's full background-task epic, out of scope). The save_mapping contract (await reload, then respond with `reloaded_entries`) is unchanged.

## Implementation Notes

Oneshot because the change is two localized edits under 100 lines with all anchors already identified. A unit test for the quota belongs in tests/unit/test_coordinator_partial_refresh.py style (mock a config entry with `history_peripherals_per_scan` set and a `_dynamic_peripherals` list larger than the quota; assert only N periphs fetch history per cycle, and that the next cycle drains the next N).

Run log:
- Read `CONF_HISTORY_PERIPHERALS_PER_SCAN` once per refresh cycle (not per periph) and decremented it per pending periph processed, including no-data fetches (a consumed slot is consumed). Files: custom_components/eedomus/coordinator.py (import block + `_async_partial_refresh`), tests/e2e/conftest.py (`E2E_WS_TIMEOUT`, default 120 s, env override), tests/unit/test_coordinator_partial_refresh.py (new `test_partial_refresh_history_quota_limits_per_scan`).
- Surprise: the >88-char lines flagged in coordinator.py and conftest.py are pre-existing; no added line exceeds 88 chars.
- Unit verification: 168 passed (`python3 -m pytest tests/unit/ -q`), including the new cadence test.
- Not yet verified: the E2E panel suite (7/7 under ~2 min) requires deploying this change to the live Pi; local E2E would still time out against the undeployed instance.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 5 findings — high 0, medium 2, low 2, false 1, maybe-false 0
- findings:
  - `[medium]` `[defer]` E2E panel suite and reload-latency acceptance criteria unmet — real verification gap: the criterion requires deploy to the live Pi, which this run forbids ("Do not push"); deferred with the deploy+E2E procedure that settles it.
  - `[false]` `[reject]` "History work is not on the awaited reload path, so the quota may not fix the hang" — refuted by live evidence from this session: the 22:04:52 CancelledError trace shows entry setup blocked in `_async_add_and_update_entities` for the whole ~3-min history cycle, and the panel test's ws hang coincided exactly with that cycle; the static reading of `async_config_entry_first_refresh` (no history loop) misses that the awaited entity addition waits on the coordinator's in-flight partial refresh. Residual confirmation is the deferred E2E item above.
  - `[low]` `[patch]` Empty-chunk slot consumption untested — real gap: the quota decrement sits outside `if chunk:` by design but the mock always returned a truthy chunk; patched by making periph 111 return an empty chunk in `test_partial_refresh_history_quota_limits_per_scan` and asserting it consumes a slot and is retried next cycle.
  - `[low]` `[patch]` Vacuous assertion `set(fetched_first) <= set(periph_ids)` cannot fail — patched: removed and replaced with meaningful assertions (`"333" not in fetched_first`, retried-set equality in cycle 2).
  - `[medium]` `[patch]` Duplicate `review`/`review_source` YAML keys corrupted the plan frontmatter (last-wins would blank the review metadata) — patched: exactly one pair kept, in template order.

## Auto Run Result

Status: built

- Summary: the coordinator now honors `history_peripherals_per_scan` (AD-2 cadence): at most N pending history imports per refresh cycle, so a reload's awaited partial refresh costs ~N×2 s instead of ~180 s; the E2E ws helper now bounds every recv by `E2E_WS_TIMEOUT` (default 120 s) so a stuck command fails instead of hanging.
- Files changed: `custom_components/eedomus/coordinator.py` (quota read + gate in `_async_partial_refresh`, const imports), `tests/e2e/conftest.py` (ws timeouts), `tests/unit/test_coordinator_partial_refresh.py` (new quota test covering cap, drain, empty-chunk slot).
- Review findings: 5 reported — 3 patched (empty-chunk coverage + vacuous assertion, both low; duplicate frontmatter YAML keys, medium), 1 deferred (E2E + reload-latency verification requires deploy), 1 rejected as false (reload-path claim refuted by live logs).
- Follow-up review: not recommended (0 high patched, 1 medium patched; converged).
- Verification: `python3 -m pytest tests/unit/ -q` — 168 passed including the new cadence test; no added line over 88 chars. E2E panel suite NOT run: requires deploy to the live Pi (see deferred).
- Residual risks: reload-latency improvement is evidenced by live logs (entry setup blocked through the history cycle) but not yet confirmed end-to-end on the deployed instance; the backfill of ~90 pending periphs now drains at N per scan interval (default 1 → slow initial drain after each reload until AD-2's full background-task + persistence epic lands).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all pass, including the new cadence test
- `python3 -m pytest tests/e2e/test_e2e_panel.py -v` -- expected: 7/7 pass in under ~2 min total (after deploy; requires the live Pi)
- `git status --short` -- expected: only the intended files modified

**Manual checks (if no CLI):**
- After deploy, logs show one PARTIAL REFRESH with `History: <N periphs>` per cycle instead of 90, and the reload after `eedomus/save_mapping` completes in seconds.
</intent-contract>
