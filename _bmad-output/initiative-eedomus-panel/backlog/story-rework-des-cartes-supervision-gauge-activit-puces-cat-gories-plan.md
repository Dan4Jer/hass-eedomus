---
title: 'Story 111: Supervision cards rework — activity gauge, category chips, system chart'
type: 'feature'
ticket: '111'
created: '2026-10-08'
status: 'ready-for-dev'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Supervision tab's "API calls" card is a developer diagnostic (per-cycle delta of 5 cumulative endpoint counters, nominal 1-3) that users cannot read, and the periph-count time chart tracks a number that barely moves. Nothing shows box health or device activity.

**Approach:** Rework the four metric cards from the UX spine run 2026-10-08: keep the refresh-time chart; replace the API calls card with a system card fed by the box's own periphs (usage 23: CPU Box sampled per refresh cycle, free space companion); make the periph count a static value card with category chips; add an activity gauge (periphs whose last_value_change falls within the last hour, computed backend from the coordinator cache).

## Boundaries & Constraints

**Always:** All user-facing strings via the `panel_translations.py` catalog (EN source of truth, FR full translation, key parity pinned by tests); every metric value carries its textual equivalent (chart never the sole carrier, svg aria-hidden); no subscription/polling — one load per tab visit; panel displays, never reimplements engine logic (CAP-9); lines ≤ 88 chars; multi-box: one section per box, a broken box is skipped without costing the others.

**Never:** No HA chart component dependency (none is exposed to the panel context — inline SVG themed via HA CSS variables only, per supervision.js header); no vendored chart library; no scraping of the box's local diagnostics page (CPU comes from the periphs the box itself exposes); no new websocket commands (the existing `eedomus/get_box_metrics` payload grows); no changes to the backfill queue section.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Box with CPU Box + Espace libre Box periphs (usage 23), cycles buffered | 4 cards: refresh chart, system chart (cpu series + free space companion), activity gauge, count + category chips | None |
| No CPU periph | Box without usage-23 CPU periph, or state unparseable | System card absent from the grid; others render | Field `cpu` null in cycle records, never a half-empty card |
| Fresh boot | Metrics buffer empty (no cycle yet) | Existing empty state (no cards section) — unchanged | Existing message |
| Unparseable last_value_change | A periph without the raw field | It does not count as active; no exception | Skipped silently |
| Free space missing | CPU present, Espace libre absent | System card renders without the companion value | Companion omitted, no placeholder |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/coordinator.py` — `_capture_cycle_metrics` (~1197): the per-cycle record append — extend with `cpu`/`free_space_kb` sampled from usage-23 periphs. `_is_dynamic_peripheral`/data cache: periph rows carry `usage_id`, raw `last_value_change` ("YYYY-MM-DD HH:MM:SS" naive local) and `last_value`. `get_box_metrics` (1281): payload assembly — add `active_periphs_last_hour` + `periphs_by_category`. Do not touch `_backfill_*`.
- `custom_components/eedomus/ui_service.py` — `_handle_get_box_metrics` (1172): multi-box walk, passes `coordinator.get_box_metrics()` through `_json_safe` — no change expected; extend only if a new field needs shaping.
- `custom_components/eedomus/panel_translations.py` — panel catalog; supervision keys at 207-230 (`card.*`, `value.*`). Remove `card.api_calls`/`value.api_calls`; add activity/count/system keys in BOTH `en` and `fr` sections (parity pinned by unit tests).
- `custom_components/eedomus/www/panel/supervision.js` — card assembly at ~493-540 (`supervisionCycleSeries`, `supervisionMetricCardHtml`); `SUPERVISION_STYLES` at 20+. Charts are inline SVG; the gauge is a new value-card variant (SVG arc, HA CSS variables); chips reuse the coherence chip discipline (12% `color-mix` tint, text ≥ 4.5:1, icon+text never color alone).
- `tests/unit/test_box_metrics.py` — existing coordinator metrics tests (`_scan_interval` guard, stubs at 40-60) — extend for sampling + payload fields.
- `tests/unit/test_translations_structure.py` — en/fr structural parity guards — will catch key removal/addition; keep green.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` -- add `_sample_box_system_periphs()` (resolve usage-23 CPU/free-space states from the cache, tolerant parse), call it in `_capture_cycle_metrics` to add `cpu`/`free_space_kb` to each cycle record; compute `active_periphs_last_hour` + `periphs_by_category` in `get_box_metrics` from the same cache -- the data source the cards read
- [ ] `custom_components/eedomus/panel_translations.py` -- remove the api_calls keys, add the activity/count/system card keys (titles, value sentences, chip labels) in en + fr -- i18n discipline
- [ ] `custom_components/eedomus/www/panel/supervision.js` -- rework `_renderMetrics`: refresh chart unchanged; system chart card (cpu series from cycles, free-space companion, hidden when no cpu samples); activity gauge value-card (SVG arc + textual equivalent); count value-card with category chips; drop the api_calls card and its series -- the spine's card set
- [ ] `tests/unit/test_box_metrics.py` -- cover the I/O matrix: sampling happy path, missing CPU periph (null fields), unparseable last_value_change, payload fields present -- prove the matrix
- [ ] Run the full unit suite + JS harness; fix anything red -- regression guard

**Acceptance Criteria:**
- Given a box with the CPU Box periph, when refresh cycles run, then `get_box_metrics` cycles carry `cpu` values and the panel renders the system chart with its textual equivalent and the free-space companion
- Given the panel in a non-EN locale, when the cards render, then every label comes from the websocket catalog and the en/fr parity tests pass
- Given the Supervision tab, when it renders, then no "API calls" card exists and no orphan api_calls keys remain in the catalog

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Design Notes

CPU periph resolution: scan `self.data` for `usage_id == "23"` with a name containing "CPU" (CPU Box) / "Espace libre" — matches live IDs 1061603/1061604 without hardcoding periph ids (other boxes carry their owner name in the periph name). State parse via `float()`; failure → None → card hidden, per the spine fallback.

Gauge: SVG arc, radius from the card, stroke via `var(--primary-color)`, track via `var(--divider-color)`; the numeric equivalent renders beside it (accessibility floor: never color alone). Chips: `color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color))` background, `var(--primary-text-color)` text.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green (extended box-metrics tests included)
- `node tests/js/test-coherence.js` -- expected: "All coherence tests passed."
- `awk 'length > 88 {print FILENAME":"FNR}' custom_components/eedomus/coordinator.py custom_components/eedomus/panel_translations.py custom_components/eedomus/www/panel/supervision.js` -- expected: no new long lines from this change

**Manual checks (if no CLI):**
- After deploy: Supervision tab shows 4 cards; CPU chart populated after 2+ refresh cycles; no API calls card; FR locale labels correct
