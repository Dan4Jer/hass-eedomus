---
title: 'Story 5.1: salvage the eedomus simulator from PR #119'
type: 'chore'
ticket: '1'
created: '2026-10-09'
status: built
route: 'oneshot'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'cf8b642'
---

## Intent

Salvage the local eedomus API simulator from the closed, unmerged PR #119
(head fmo01/hass-eedomus@ecaf505): a Flask server serving the API from a
JSON dump (auth.test, periph.list, periph.value_list, periph.caract,
periph.value + thermostat rules, /simulate/change), with the demo dataset
and the extraction/anonymization utilities.

## Implementation Notes

- Source: fmo01/hass-eedomus@ecaf505 scripts/simulateur/ — 7 files,
  fetched via `git fetch --depth 1 fmo01 ecaf505`.
- All user-facing text, comments and the README translated to English
  (repo policy); periph names inside the demo dump stay as data.
- flask>=3.1 added to requirements_dev.txt (requests was already there).
- Smoke test (local, port 8199): auth.test success + 401 on bad
  credentials; periph.list 69 demo periphs; periph.caract single ID
  returns the 7 base fields; /simulate/change updates a value.
- Remote fmo01 kept for provenance; removable later.

## Verification

- `python3 -m py_compile scripts/simulateur/*.py` — green
- Live smoke test — all endpoints answered as above
- Unit suite untouched — 354 green (scripts are dev tooling, not
  integration code)
