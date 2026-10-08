---
title: 'Story 111: Supervision cards rework — activity gauge, category chips, system chart'
type: 'feature'
ticket: '111'
created: '2026-10-08'
status: built
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
baseline_revision: 'e1edeba'
review_loop_iteration: 0
followup_review_recommended: false
deferred:
  - summary: >-
      Activity gauge timezone assumption — eedomus naive-local timestamps
      compared against host-local now.
    evidence: >-
      A box/HA-host timezone mismatch would skew active_periphs_last_hour by
      the offset. Not shown reachable (box and host share the site). Settle by
      comparing the box clock against the host timezone on the live instance.
    location: custom_components/eedomus/coordinator.py (_count_active_periphs_last_hour)
    severity: medium (unverified)
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

- Inline run (user-authorized 2026-10-08): implemented in-session, the
  subagent harness being down (see Auto Run Result).
- Decimal formatting added for the system card (supervisionFormatDecimal):
  counts round (29), CPU/kB carry one decimal (29.2 / 2282.4).
- "Espace libre" added to the French-lexicon exemptions (data matcher —
  the eedomus box names its free-storage periph in French, same
  precedent as sensor.py).
- Both catalog fixtures regenerated (sorted keys, matching the previous
  convention): panel-keys.json 197 keys, panel-catalog.json minimal diff.
- Two pre-existing payload key-set tests updated (the contract grew by
  active_periphs_last_hour + periphs_by_category, by design).

## Plan Change Log

## Review Triage Log

### 2026-10-08 — Review pass (thorough, run inline: subagent harness down, user-authorized)
- verdicts: 7 findings — high 0, medium 0, low 1, false 5, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` Activity count compares the eedomus naive-local last_value_change against host-local datetime.now() — a box/host timezone mismatch would skew the gauge. Not shown reachable (same-LAN deployment); comparing the box clock against the host TZ would settle it. Deferred below.
  - `[low]` `[reject]` Bar-chart helpers (supervisionBarRects/BarChartHtml) lost their only card consumer with the api_calls card. Generic, harness-tested chart capability; removal is churn with no user gain — rejected.
  - `[false]` `[reject]` usage_id arriving as int would hide the system card — refuted: 24 string-comparison sites on usage_id across the codebase; the string invariant is repo-wide, the matcher follows the convention.
  - `[false]` `[reject]` Handler-chain verification gap — refuted: the updated handler test asserts the full payload key set (cycles + snapshot fields) and runs green.
  - `[false]` `[reject]` cycle api_calls field retained without a card — refuted as a defect: data/presentation split by design, the metrics tests consume the field.
  - `[false]` `[reject]` "espace libre en valeur associée" claim falsified — refuted: the companion rides the card's textual sentence (the equivalent-carrier discipline of the spine), and the cpu-only branch exists when free space is absent.
  - `[false]` `[reject]` Activity gauge counts the box's own system periphs — refuted as a defect: the CPU periph is a periph; the sentence stays honest.

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


## Auto Run Result

Status: blocked — blocking condition: no subagents.

Run 2026-10-08 (bmad-build-auto, full route). The plan routed correctly
(ticket 111, plan ready-for-dev -> in-progress, baseline e1edeba) and
the working tree was clean. The implementing subagent could not be
launched: three spawn attempts (impl-111-supervision, impl-111-b, and
a trivial diagnostic agent) all returned success but never registered
in the subagent list — the harness's subagent capability is down in
this environment (same silent failure earlier tonight with the UX
rubric-walker agent). Per the workflow's Subagents rule, the full route
mandates an implementing subagent; without it the run halts blocked.
No code was changed. Resume paths: (a) rerun bmad-build-auto in a fresh
session once subagents work, or (b) authorize inline implementation
(the interactive bmad-build path allows direct implementation).

---

## Auto Run Result — final (2026-10-08, same day)

**Status: built.** Continuation of the blocked run above: the user
authorized inline implementation (the subagent harness stayed down), and
the plan was implemented, verified and reviewed in-session under the
bmad-build discipline.

**Implemented change.** The Supervision metric cards now render the
spine's set: refresh-time chart (unchanged), activity gauge (periphs
that reported a value in the last hour, semicircular SVG arc with
textual equivalent), static periph count with category chips (coherence
chip discipline), and the box system chart (CPU sampled per refresh
cycle from the usage-23 periphs, free space as companion sentence,
card hidden without CPU samples). The API calls card and its i18n keys
are gone. The get_box_metrics payload gained active_periphs_last_hour
and periphs_by_category; cycle records gained cpu and free_space_kb.

**Files changed.**
- custom_components/eedomus/coordinator.py — box-system sampling,
  activity/category counters, cycle + payload extensions
- custom_components/eedomus/panel_translations.py — 2 keys removed,
  6 added, EN + FR
- custom_components/eedomus/www/panel/supervision.js — gauge, chips,
  value-card renderer, decimal formatting, cards rework
- tests/fixtures/panel-keys.json, panel-catalog.json — regenerated
  (197 keys, sorted convention kept)
- tests/js/test-coherence.js — card-set expectations updated; new
  cases: no-api-calls card, system card hidden, cpu-only sentence
- tests/unit/test_box_metrics.py — I/O matrix coverage (6 new tests)
  + 2 payload key-set updates
- tests/unit/test_no_french_source.py — "Espace libre" exemption
  (data matcher, sensor.py precedent)

**Review findings breakdown.** Thorough lenses run inline (subagent
harness down; deviation noted in the triage log). 7 findings: 0 high,
0 medium, 1 low (rejected — bar-chart helpers keep their tested
generic role), 5 false (refutations in the triage log), 1 maybe-false
deferred (timezone assumption, medium-unverified). Patches applied:
none — no finding survived triage as this change's problem to fix.

**Follow-up review: false** (nothing patched; counts by verdict: high 0,
medium 0, low 0 patched).

**Verification performed.** python3 -m pytest tests/unit/ -q — 343
passed. node tests/js/test-coherence.js — all passed. Line-length
guard on changed files — no new lines over 88. Frontmatter deferred
list YAML-validated (1 entry). Full unified diff re-read from
baseline e1edeba.

**Residual risks.** (1) The deferred timezone assumption (unverified,
medium if true) — settle by comparing the box clock with the host TZ.
(2) Manual deploy check pending (per the plan): after the git-only
deploy, the Supervision tab shows 4 cards, CPU chart fills after 2+
cycles, FR labels correct. (3) The activity count includes the box's
own system periphs (honest, noted in triage).
