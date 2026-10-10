---
title: 'Story 5.5: E2E-sim multi-box + destructive suite'
type: 'feature'
ticket: '5'
created: '2026-10-10'
status: done
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The multi-box and destructive surfaces are untestable on
the live-Pi strate (one real box, destructive actions forbidden on
it) — the simulator strate built by 5.2–5.4 exists precisely to
cover them, and nothing exercises it yet.

**Approach:** Second e2e_sim suite: a simulated entry WITH history
enabled (the knob from 5.3 routes its backfill to the simulator —
CAP-2's success via the production path), covering multi-box
aggregation (get_backfill_state across both boxes, get_box_metrics
two sections, global-pause fan-out), the four destructive backfill
actions end-to-end on a simulated periph (retry_now through the
production import path, prioritize, per-periph pause/resume,
ignore + reactivation), plus the AD-16 two-strates rule into
AGENTS.md.

## Boundaries & Constraints

**Always:** Real websocket/REST APIs only; the real box's entry is
never steered (no pause, no action on its periphs — the global pause
is set and resumed immediately, and its engine state is restored);
determinism — no assertion on wall-clock, explicit timeouts;
English everywhere.

**Never:** No integration-code change expected (the multi-box
machinery exists: `_aggregate_backfill_state`, `_coordinator_for_periph`,
global fan-out loop); no full-drain requirement (the production path
is proven by the first fetched+imported chunk; the drain keeps
running in background); no panel JS change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sim entry queue | history=True entry created | get_backfill_state rows carry the sim entry_id | None |
| Production import | Worker drains a sim periph | retrieved_points > 0, oldest_timestamp set (fetch+import through the simulator) | None |
| Multi-box state | Two loaded entries | Aggregated queue holds rows of both entry_ids | None |
| Box metrics | Two loaded entries | get_box_metrics returns two sections | None |
| Global pause | backfill_set_paused global | Aggregated state global_paused True; resume restores | Restored in teardown |
| retry_now | Engine paused, lock free | Chunk fetched+imported via the simulator | None |
| prioritize | Sim periph | Row moves to head of its box's queue | None |
| pause/resume periph | Sim periph | Row status paused → pending | None |
| ignore + reactivate | Sim periph | Row leaves queue, listed ignored; ignored=False restores it | None |

</frozen-after-approval>

## Code Map

- `tests/e2e/_sim_harness.py` — extract the flow helpers (create/remove simulated entry, payload builder) from the 5.3 test module so both suites share them; keep the simulator lifecycle as is.
- `tests/e2e/test_e2e_sim_config_flow.py` — refactor to the shared helpers (no behavior change).
- `tests/e2e/test_e2e_sim_multi_box.py` — the new suite (markers e2e+e2e_sim).
- `custom_components/eedomus/ui_service.py:1154-1240` — aggregation and routing already multi-box: queues concatenated with entry_id on rows, `_coordinator_for_periph` first-match (dump periph_ids are strings — no collision with the real box's numeric ids).
- `custom_components/eedomus/coordinator.py:1302-1321` — get_box_metrics payload carries entry_id + name (panel sections per box).
- `AGENTS.md` — the two-strates rule goes OUTSIDE the managed `<!-- bmad:context -->` block (edits inside get replaced on refresh).
- Pi runtime: the sim entities are new, so their whole synthetic history is BEFORE the first native statistic — no AD-11 clip; the drain imports for real (~26k hourly stats per numeric periph at the default depth).

## Tasks & Acceptance

**Execution:**
- [ ] `tests/e2e/_sim_harness.py` — flow helpers extracted (create_entry, remove_entry, user_input builder) -- shared by both e2e_sim suites
- [ ] `tests/e2e/test_e2e_sim_config_flow.py` -- refactor onto the shared helpers, 4 tests stay green -- no regression
- [ ] `tests/e2e/test_e2e_sim_multi_box.py` -- the CAP-4 suite: aggregation, box metrics, global fan-out, 4 destructive actions, production-path import -- the intestable under test
- [ ] `AGENTS.md` -- two-strates rule (AD-16), outside the managed markers -- the rule the epic's Done-when 4 names

**Acceptance Criteria:**
- Given the simulated entry with history enabled, when the worker drains one of its periphs, then its queue row shows retrieved_points > 0 and an oldest_timestamp — the production path through the simulator (CAP-2 success).
- Given two loaded eedomus entries, when get_backfill_state and get_box_metrics are called, then both boxes' data is present (rows and sections distinguished by entry_id).
- Given the engine globally paused, when the four actions run on a simulated periph, then retry_now imports a chunk, prioritize jumps the queue, pause/resume moves the row, ignore removes it to the ignored list and reactivation restores it.
- Given the suite ends (however it ends), then the global pause is resumed, the simulated entry removed, the simulator stopped; the real box's queue is untouched.

## Implementation Notes

- Implemented directly (session subagent name limit — same as 5.2/5.3).
- Response-shape findings from the live run: the global pause
  response carries paused/global keys (not global_paused — that
  lives in the aggregated state); the priority marker overlays the
  paused status in the row derivation, so the per-periph pause
  assertion must run BEFORE prioritizing. Both were test-side
  misunderstandings, no integration change.
- stop() hardened with a pattern-pkill safety net (the captured SSH
  PID can miss); the post-suite "still running" check was a pgrep
  false positive on its own command line — the simulator was dead.
- Depth N measurement: first chunk fetch+import ran in seconds
  through the local simulator; the default 3 years / 1 point-hour
  (~26k points, 3 chunks per numeric periph) is kept — the full
  drain of a simulated box completes in background. Sim-statistics
  rows written during the suite stay in the recorder as orphans
  after entry removal (purge tooling from story 1.3 can clean them).
- Live validation: e2e_sim 9/9 green (4 config-flow + 5 multi-box),
  live-Pi strate 29/29 green and unchanged, unit 379 green, node
  strict green. AGENTS.md carries the two-strates rule (AD-16).

## Plan Change Log

## Review Triage Log

## Design Notes

- **Depth N measurement (spec open question, settled here):** default
  3 years / 1 point per hour stays — the first measured chunk
  (fetch ~1-2s local + import seconds) shows a full periph walk is
  ~3 chunks; the drain runs in background during the suite. The knob
  stays env-tunable for future retuning.
- **Determinism of the production-path proof:** wait for
  retrieved_points > 0 on a sim row with a bounded timeout (worker
  pass = 60s); assert oldest_timestamp is set (the simulator's
  3-year anchor makes it deep, not "recent" — distinct from the
  real API's fresh-window behavior).
- **Destructive ordering:** pause global (stops both drains,
  releases locks) → retry_now → prioritize → per-periph pause/resume
  → ignore → reactivate → resume global (teardown restores).
- **Real-box safety:** the global pause is the only action touching
  both boxes — resumed in teardown; the real box's periphs are
  never targeted (dump ids are strings, real ids numeric).

## Verification

**Commands:**
- `python3 -m pytest tests/e2e/ -m e2e_sim -q` -- expected: all green (both suites)
- `python3 -m pytest tests/e2e/ -m e2e -q` -- expected: 33+ green, live-Pi strate unchanged
- `python3 -m pytest tests/unit/ -q` -- expected: 379 green
- `node tests/js/test-coherence.js` -- expected: green
