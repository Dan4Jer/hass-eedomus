---
title: 'Story 5.3: simulated box harness + history_api_host knob'
type: 'feature'
ticket: '3'
created: '2026-10-10'
status: 'built'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 'a32bb8e'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The E2E-sim strate cannot exist: nothing starts the
simulator on the Pi, nothing creates a second config entry through the
real flow, and the production client hardcodes
`https://api.eedomus.com` for `periph.history` (verified live:
the real box serves `success: 0` locally) — a simulated box's
backfill would hit the real cloud.

**Approach:** Add the optional advanced `history_api_host` config
field (default empty → cloud; decision 2026-10-09, story 5.2) and
build the e2e_sim harness: a session fixture that starts the simulator
on the Pi over SSH (venv — PEP 668 blocks system pip; dedicated port),
then the first `e2e_sim` marker test suite driving the real config
flow over websocket — creation ok, bad-auth ko, entity coexistence,
clean removal.

## Boundaries & Constraints

**Always:** Real config flow and real config-entries API only — no
direct .storage writes, no injection of entry data outside the flow;
the live-Pi strate stays untouched (`-m e2e` suite unchanged); the
real box entry is never reloaded, removed, or modified by the harness;
English everywhere; i18n: strings.json = en.json source of truth,
fr.json structurally identical.

**Never:** No backfill exercise in this ticket (5.5's scope — the
simulated entry is created with history disabled); no multi-box UI
assertions beyond entity existence (5.4/5.5); no simulator change
(5.2 delivered the endpoint); no HA container exec (docker is
confirmation-locked on the Pi — the simulator runs on the Pi host).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Knob empty | `history_api_host` unset/"" | History URL stays `https://api.eedomus.com` | None |
| Knob set | `history_api_host=127.0.0.1:8199` | History URL `http://127.0.0.1:8199/api/get` | None |
| Flow ok | Valid simulator creds | Entry created, `type: create_entry` | None |
| Flow ko | Wrong api_secret | Form re-shown, `errors: base cannot_connect`/auth error | Flow aborted, no entry |
| Entry data | Flow with knob filled | Entry data carries `history_api_host` | None |
| Teardown | Any test failure | Simulator killed, simulated entry removed (try/finally) | Real box untouched |

</frozen-after-approval>

## Code Map

- `custom_components/eedomus/const.py:32` — add `CONF_HISTORY_API_HOST = "history_api_host"` beside CONF_API_HOST.
- `custom_components/eedomus/config_flow.py` — `STEP_USER_DATA_SCHEMA` (~85-136): add `vol.Optional(CONF_HISTORY_API_HOST, default=""): str`; `async_create_entry` data dict (~295-330): add the knob pass-through (the entry data is rebuilt field-by-field, NOT copied from user_input).
- `custom_components/eedomus/eedomus_client.py:55,75-78` — `__init__` reads the knob via `_get_config_value`; `get_device_history` (~562): `base_url = f"http://{self.history_api_host}/api/get"` when set, else the `HISTORY_API_URL` cloud default.
- `custom_components/eedomus/strings.json` + `translations/en.json` + `translations/fr.json` — `config.step.user.data.history_api_host` label in all three trees (key sets currently identical — keep it so).
- `tests/e2e/conftest.py` — existing `ha_api`/`ws_call` session fixtures to reuse; `.env` loading pattern for REMOTE_IP/REMOTE_USER/REMOTE_PATH.
- `tests/e2e/test_e2e_*.py` — existing live-Pi suite (marker `e2e`); the new file carries a distinct `e2e_sim` marker.
- `pyproject.toml:46-50` — markers list: add `e2e_sim`.
- Pi environment (verified): repo clone at `/homeassistant/custom_components/hass-eedomus` (scripts/simulateur present), host python 3.14.8, no flask, PEP 668 (externally-managed), `python3 -m venv` works; HA OS 18.3 (core container on host network → 127.0.0.1 reachable from HA).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/` (const, config_flow, client) + i18n trees — the `history_api_host` knob end to end — CAP-3 prerequisite (decision 2026-10-09)
- [ ] `tests/unit/` — knob URL resolution test + flow pass-through test — regression net
- [ ] `tests/e2e/conftest.py` (or a new `_sim_harness.py` module) — session fixture: SSH venv bootstrap + simulator lifecycle on the Pi (start, health-wait, teardown kill) — CAP-3 harness
- [ ] `tests/e2e/test_e2e_sim_config_flow.py` — flow ok, bad-auth ko, entities from dump coexist, entry data carries the knob, clean removal in teardown — CAP-3 + first e2e_sim strate test
- [ ] `pyproject.toml` — `e2e_sim` marker — selection distinct from live-Pi

**Acceptance Criteria:**
- Given the simulator running on the Pi, when the flow is submitted with its address and valid creds, then a second entry is created via `config_entries/flow` and dump entities appear on the instance beside the real box's.
- Given the same flow submitted with a wrong secret, then the form re-shows with an error and no entry is created.
- Given the entry exists, when the suite tears down, then `config_entries/remove` removes it and its entities disappear; the real box's entities and states are unchanged.
- Given an entry with `history_api_host` set, when `get_device_history` builds its URL, then it targets that host; empty → cloud (unit-verified).

## Implementation Notes

- Implemented directly (session subagent name limit — same as 5.2).
- async_step_user creates the entry with data=user_input verbatim,
  so the knob lands in entry data naturally; the explicit add went
  into validate_input's synthetic ConfigEntry (the client the flow
  builds for its connection test) for coherence.
- Spec open question settled: entry removal via the standard
  `config_entries/remove` websocket command; stale-run guard removes
  leftover entries before the flow (unique_id eedomus_<api_host>
  would abort with already_configured otherwise).
- Unit: 6 new tests (4 client URL resolution + 2 flow pass-through),
  suite 379 green. e2e_sim: 4 tests collected; runtime validation
  needs the deploy (the flow must serve the new field).

## Plan Change Log

## Review Triage Log

## Design Notes

- **Removal mechanism (spec open question, settled here):** the
  websocket `config_entries/remove` command — standard HA 2026.9 API,
  already used by the UI; no .storage surgery, no manual cleanup doc.
  Teardown is try/finally: remove the entry, then kill the simulator.
- **Simulator bootstrap on the Pi:** PEP 668 blocks `pip install` on
  the host python; the harness creates/reuses a venv at a fixed path
  (`~/eedomus-sim-venv`, `pip install flask` once, idempotent), then
  starts `simulator.py -p <port> --api-user/--api-secret` from the
  git-deployed clone. Port: dedicated (8199, the 5.1 smoke port) —
  HA reaches it via host-network 127.0.0.1.
- **Simulated entry knobs:** `history=False` (no backfill drain —
  5.5's scope), `api_eedomus=True`, sane scan interval; the
  harness fills `history_api_host` through the real flow to prove the
  knob end to end.
- **Entity verification:** poll REST states for a distinctive dump
  periph name (setup is async after create_entry) with a bounded
  timeout; coexistence = real-box state snapshot taken before/after.
- **Markers:** `e2e_sim` marks the strate; live-Pi stays `e2e`.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 373+ green (knob tests added)
- `python3 -m pytest tests/e2e/ -m e2e_sim -q` -- expected: green (requires .env + live Pi; harness boots the simulator itself)
- `python3 -m pytest tests/e2e/ -m e2e -q` -- expected: 29 live-Pi tests still green, unchanged
- `node tests/js/test-coherence.js` -- expected: green (no JS change, guard against collateral)
