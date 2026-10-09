---
title: 'Bug 1.8: pass unit_class to async_import_statistics (HA 2026.11)'
type: 'bugfix'
ticket: '8'
created: '2026-10-08'
status: built
route: 'oneshot'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'c48cfdd'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** HA logs at every import: "custom integration 'eedomus' doesn't specify unit_class when calling async_import_statistics... This will stop working in Home Assistant 2026.11."

**Approach:** Derive `unit_class` from the imported entity's unit via HA's own `unit_conversion.get_unit_converter()` (°C → temperature, kWh → energy...; no converter → None, key still present — only the missing key deprecates) and pass it in the statistics metadata.

## Boundaries & Constraints

**Always:** unit_class derived only from the live unit already read for the metadata; unknown units keep the import running (unit_class None), matching how HA treats units without a converter; conftest stub mirrors real HA semantics (get_unit_converter raises ValueError for unknown units, converters carry UNIT_CLASS).

**Never:** no entity registry changes, no import-path changes beyond the metadata, no unit coercion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | unit °C | metadata carries unit_class "temperature" | None |
| Energy unit | unit kWh | unit_class "energy" | None |
| No converter | unit "%" or custom | unit_class None, key present, import proceeds | ValueError swallowed |
| Missing live state | no state | import skipped as before (pre-existing behavior) | Existing warning |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/coordinator.py` — `_import_via_statistics` metadata dict (~2296): add the unit_class derivation beside the unit read.
- `tests/unit/conftest.py` — stub `homeassistant.util.unit_conversion` (module stub pattern at ~268 for util.dt).
- `tests/unit/test_history_import_statistics.py` — nominal metadata assertion (line ~134) + new cases (°C, kWh, no-converter unit).

## Tasks & Acceptance

**Execution:**
- [ ] `tests/unit/conftest.py` — stub unit_conversion with get_unit_converter mirroring HA semantics
- [ ] `custom_components/eedomus/coordinator.py` — derive + pass unit_class in the metadata
- [ ] `tests/unit/test_history_import_statistics.py` — update nominal assertion, add converter cases
- [ ] Run the unit suite — green

**Acceptance Criteria:**
- Given a chunk imported for a °C sensor, when async_import_statistics is called, then the metadata includes unit_class "temperature"
- Given a unit with no HA converter, when the import runs, then the metadata includes unit_class None and the import completes

## Implementation Notes

- 2026-10-09 hotfix: `unit_conversion.get_unit_converter()` does not exist
  in HA 2026.9 (the AttributeError — not caught by the ValueError/TypeError
  handler — aborted every live statistics import, 103 failures / 25 entities).
  Replaced with `recorder_statistics.STATISTIC_UNIT_TO_UNIT_CONVERTER`, the
  table the recorder itself resolves converters from. Chunks fetched during
  the failure window were already advanced past (progress moves on fetch,
  not import) — affected periphs need a progress reset to re-import them.

## Plan Change Log

- 2026-10-09: unit_class lookup switched from
  `homeassistant.util.unit_conversion.get_unit_converter` to
  `recorder.statistics.STATISTIC_UNIT_TO_UNIT_CONVERTER.get(unit)`
  (coordinator.py ~2395, conftest stub follows).

## Review Triage Log

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: all green
