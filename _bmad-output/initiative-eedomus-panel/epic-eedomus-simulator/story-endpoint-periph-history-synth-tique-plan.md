---
title: 'Story 5.2: synthetic periph.history endpoint in the simulator'
type: 'feature'
ticket: '2'
created: '2026-10-09'
status: done
route: 'full'
route_source: 'auto'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'f3df73a'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The simulator salvaged from PR #119 does not serve
`periph.history` — the endpoint the integration's backfill consumes
(`eedomus_client.py`, `get_device_history`) — so the E2E-sim strate
(epic 5) cannot exercise a simulated box's history import.

**Approach:** Add a `periph.history` action to the simulator's
`/api/get` route: a synthetic, deterministic history generated purely
from the dump (fixed per-periph anchor, seeded value function), served
with the chunking/pagination contract the production client expects
(≤ 10 000 points per call, epoch `start`/`end` params, resume by
`start`).

## Boundaries & Constraints

**Always:** Deterministic — same dump + same anchor = same history, no
wall-clock time in generation; points strictly ascending, resume
serves `start < ts <= end`; chunk capped at 10 000; response shape
`{"success": 1, "body": {"history": [[value, iso_timestamp], ...]}}`
with naive-local ISO timestamps (`datetime.fromisoformat`-parseable);
English everywhere; Flask stays test-only tooling.

**Never:** No integration-code change in this ticket (the client's
history routing knob is decided separately — see Open Questions); no
real-time push simulation; no thermostat/rule coupling; no dump-format
change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Numeric periph, `start=0`, wide `end` | First chunk of ≤ 10 000 ascending points from the series start | None |
| Pagination resume | `start` = last chunk's max ts | Next chunk, no overlap, no gap, still ≤ 10 000 | None |
| Tail | `start` at/after series end | Empty `history` list, `success: 1` | None (client completes: chunk < 10 000) |
| Non-numeric periph | Base value not float-parseable | Empty `history`, `success: 1` | None |
| Unknown periph_id | Not in the dump | 404 `{"success": 0, "error": ...}` | Mirrors `periph.caract` |
| Bad params | Non-integer `start`/`end` | Treated as 0 / now respectively | Never 500 |

**Decisions (user, 2026-10-09):** (1) Simulated-box history routing goes
through an optional advanced `history_api_host` config-flow field
(default empty → `https://api.eedomus.com`), delivered with ticket 5.3
— the real box is untouched, the E2E harness supplies the value via
the real config flow; this ticket (5.2) stays simulator-side only.
(2) Provisional synthetic-history defaults: 3 years, 1 point/hour,
anchor `last_value_change`, env knobs — measured and adjusted at 5.5.

</frozen-after-approval>

## Code Map

- `scripts/simulateur/simulator.py` — single Flask file salvaged by 5.1; add the `periph.history` action beside `periph.caract` in `/api/get` (`api_get`); reuse `require_eedomus_auth` and `caract_by_id`.
- `custom_components/eedomus/eedomus_client.py:545-590` — `get_device_history` contract: params `action=periph.history`, `periph_id`, `start`/`end` epoch ints, auth as query params; reads `data["body"]["history"]` as `[value, timestamp]` pairs.
- `custom_components/eedomus/coordinator.py:2041-2180` — `async_fetch_history_chunk` resume semantics: `start` = last chunk max ts; chunk < 10 000 marks the periph completed. The simulator must NOT reproduce the real API's stale-window loop (never return a chunk whose max ts ≤ `start`).
- `tests/unit/conftest.py` — stub environment; the new test file imports only the simulator module + stdlib (no HA stubs needed).
- `requirements-test.txt` — add `flask>=3.1` (present in requirements_dev.txt, missing here so CI runs the simulator tests).
- `scripts/simulateur/README.md` — document the endpoint, params, env knobs.

## Tasks & Acceptance

**Execution:**
- [ ] `scripts/simulateur/simulator.py` -- add `periph.history` action + synthetic generator (pure function of periph_id, anchor, ts) -- CAP-2 endpoint
- [ ] `requirements-test.txt` -- add `flask>=3.1` -- CI coverage for the new tests
- [ ] `tests/unit/test_simulator_history.py` -- determinism, chunk bounds, pagination resume, empty-history cases (I/O matrix) -- regression net
- [ ] `scripts/simulateur/README.md` -- document endpoint + env knobs -- discoverability

**Acceptance Criteria:**
- Given the same dump and the same anchor, when history is generated twice, then the point series is byte-identical.
- Given a numeric periph with > 10 000 synthetic points, when the client paginates with `start` = previous max ts, then the union of chunks is the full series, ordered, gapless and overlap-free.
- Given a periph whose base value is not float-parseable, when history is requested, then `success: 1` with an empty `history` list.

## Implementation Notes

- Implemented directly (no subagent): the session's subagent lifetime
  name limit was reached (~140 reserved names, all stopped) — the
  step-03 fallback sanctions direct implementation from the plan.
- Series iteration stays naive-local; `.timestamp()` maps two distinct
  naive times to the same epoch across DST spring-forward transitions
  (3 collisions over 3 years). Harmless for the production client (it
  only takes min/max per chunk); tests assert uniqueness on ISO
  stamps, monotonicity in epoch space.
- `simulator.py` parses CLI args at import; the test module imports it
  with a neutral `sys.argv` (`unittest.mock.patch`) so pytest flags
  like a future `-p` can never leak into argparse.
- requirements-test.txt: flask>=3.1 added with a comment (the unit
  tests import the simulator module directly).
- Verification: `test_simulator_history.py` 10/10 green; full unit
  suite 373 green (363 + 10).

## Plan Change Log

## Review Triage Log

- 2026-10-10: thorough review could not run in-session — the session's
  subagent lifetime name limit blocks lens spawns (~140 names
  reserved). The four standalone lens prompts were written to
  implementation-artifacts (review-5-2-*.md); the user declined the
  manual-session path and pinned review to none. In lieu of lenses:
  the staged diff was read and judged in step-03, and the I/O matrix
  test audit ran inline — every matrix row covered by a passing test
  (10/10), full unit suite 373 green.

## Design Notes

Generation is a pure function — no RNG state, no wall clock:

- Anchor: the periph's `last_value_change` from the dump (stable per
  dump). Series = hourly (density knob) points from anchor − N years
  to anchor.
- Value at ts: base (float of `last_value`, else empty history) +
  seasonal sinusoid (day-of-year phase) + stable hash noise
  (`md5(f"{periph_id}:{ts}").digest()[0]` scaled). Determinism falls
  out of the pure function.
- Knobs (env/CLI): `EEDOMUS_HISTORY_YEARS` (default 3),
  `EEDOMUS_HISTORY_DENSITY` (points per hour, default 1 → 26 280
  points per numeric periph → 3 chunks). Defaults are provisional —
  fixed at ticket 5.5's first measured backfill (spec open question).
- Serving: filter `start < ts <= end`, sort ascending, cap 10 000.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/test_simulator_history.py -q` -- expected: all green
- `python3 -m pytest tests/unit/ -q` -- expected: 363+ green, no regression
- `python3 -m py_compile scripts/simulateur/*.py` -- expected: green

**Manual checks (if no CLI):**
- Start the simulator locally, curl `periph.history` twice with the same window: identical bodies; paginate a > 10 000 series with the client's resume semantics: gapless union.
