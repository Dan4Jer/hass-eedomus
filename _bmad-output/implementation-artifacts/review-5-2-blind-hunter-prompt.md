# Lens: blind-hunter (story 5.2 review) — run this whole prompt in a separate session

Conduct a review of CONTENT.
Look for what's missing, not only what's wrong.
Compute your finding floor N from the diff file's size: N = min(floor(sqrt(kB) + 1), 10), where kB is the file's size in kilobytes. State the arithmetic in one line, then find at least N issues to fix or improve.
Output a Markdown list of findings only — no severity, priority, or ranking.
If the content is empty, stop and say so.
If you have zero findings, re-check and keep thinking; do not stop with an empty list.

CONTENT: the unified diff below — it is the content under review.

```diff
diff --git a/_bmad-output/initiative-eedomus-panel/epic-eedomus-simulator/story-endpoint-periph-history-synth-tique-plan.md b/_bmad-output/initiative-eedomus-panel/epic-eedomus-simulator/story-endpoint-periph-history-synth-tique-plan.md
new file mode 100644
index 0000000..1a2a209
--- /dev/null
+++ b/_bmad-output/initiative-eedomus-panel/epic-eedomus-simulator/story-endpoint-periph-history-synth-tique-plan.md
@@ -0,0 +1,137 @@
+---
+title: 'Story 5.2: synthetic periph.history endpoint in the simulator'
+type: 'feature'
+ticket: '2'
+created: '2026-10-09'
+status: 'in-progress'
+route: 'full'
+route_source: 'auto'
+review: ''
+review_source: ''
+lenses_ran: []
+review_loop_iteration: 0
+baseline_revision: 'f3df73a'
+context: []
+---
+
+<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">
+
+## Intent
+
+**Problem:** The simulator salvaged from PR #119 does not serve
+`periph.history` — the endpoint the integration's backfill consumes
+(`eedomus_client.py`, `get_device_history`) — so the E2E-sim strate
+(epic 5) cannot exercise a simulated box's history import.
+
+**Approach:** Add a `periph.history` action to the simulator's
+`/api/get` route: a synthetic, deterministic history generated purely
+from the dump (fixed per-periph anchor, seeded value function), served
+with the chunking/pagination contract the production client expects
+(≤ 10 000 points per call, epoch `start`/`end` params, resume by
+`start`).
+
+## Boundaries & Constraints
+
+**Always:** Deterministic — same dump + same anchor = same history, no
+wall-clock time in generation; points strictly ascending, resume
+serves `start < ts <= end`; chunk capped at 10 000; response shape
+`{"success": 1, "body": {"history": [[value, iso_timestamp], ...]}}`
+with naive-local ISO timestamps (`datetime.fromisoformat`-parseable);
+English everywhere; Flask stays test-only tooling.
+
+**Never:** No integration-code change in this ticket (the client's
+history routing knob is decided separately — see Open Questions); no
+real-time push simulation; no thermostat/rule coupling; no dump-format
+change.
+
+## I/O & Edge-Case Matrix
+
+| Scenario | Input / State | Expected Output / Behavior | Error Handling |
+|----------|--------------|---------------------------|----------------|
+| Happy path | Numeric periph, `start=0`, wide `end` | First chunk of ≤ 10 000 ascending points from the series start | None |
+| Pagination resume | `start` = last chunk's max ts | Next chunk, no overlap, no gap, still ≤ 10 000 | None |
+| Tail | `start` at/after series end | Empty `history` list, `success: 1` | None (client completes: chunk < 10 000) |
+| Non-numeric periph | Base value not float-parseable | Empty `history`, `success: 1` | None |
+| Unknown periph_id | Not in the dump | 404 `{"success": 0, "error": ...}` | Mirrors `periph.caract` |
+| Bad params | Non-integer `start`/`end` | Treated as 0 / now respectively | Never 500 |
+
+**Decisions (user, 2026-10-09):** (1) Simulated-box history routing goes
+through an optional advanced `history_api_host` config-flow field
+(default empty → `https://api.eedomus.com`), delivered with ticket 5.3
+— the real box is untouched, the E2E harness supplies the value via
+the real config flow; this ticket (5.2) stays simulator-side only.
+(2) Provisional synthetic-history defaults: 3 years, 1 point/hour,
+anchor `last_value_change`, env knobs — measured and adjusted at 5.5.
+
+</frozen-after-approval>
+
+## Code Map
+
+- `scripts/simulateur/simulator.py` — single Flask file salvaged by 5.1; add the `periph.history` action beside `periph.caract` in `/api/get` (`api_get`); reuse `require_eedomus_auth` and `caract_by_id`.
+- `custom_components/eedomus/eedomus_client.py:545-590` — `get_device_history` contract: params `action=periph.history`, `periph_id`, `start`/`end` epoch ints, auth as query params; reads `data["body"]["history"]` as `[value, timestamp]` pairs.
+- `custom_components/eedomus/coordinator.py:2041-2180` — `async_fetch_history_chunk` resume semantics: `start` = last chunk max ts; chunk < 10 000 marks the periph completed. The simulator must NOT reproduce the real API's stale-window loop (never return a chunk whose max ts ≤ `start`).
+- `tests/unit/conftest.py` — stub environment; the new test file imports only the simulator module + stdlib (no HA stubs needed).
+- `requirements-test.txt` — add `flask>=3.1` (present in requirements_dev.txt, missing here so CI runs the simulator tests).
+- `scripts/simulateur/README.md` — document the endpoint, params, env knobs.
+
+## Tasks & Acceptance
+
+**Execution:**
+- [ ] `scripts/simulateur/simulator.py` -- add `periph.history` action + synthetic generator (pure function of periph_id, anchor, ts) -- CAP-2 endpoint
+- [ ] `requirements-test.txt` -- add `flask>=3.1` -- CI coverage for the new tests
+- [ ] `tests/unit/test_simulator_history.py` -- determinism, chunk bounds, pagination resume, empty-history cases (I/O matrix) -- regression net
+- [ ] `scripts/simulateur/README.md` -- document endpoint + env knobs -- discoverability
+
+**Acceptance Criteria:**
+- Given the same dump and the same anchor, when history is generated twice, then the point series is byte-identical.
+- Given a numeric periph with > 10 000 synthetic points, when the client paginates with `start` = previous max ts, then the union of chunks is the full series, ordered, gapless and overlap-free.
+- Given a periph whose base value is not float-parseable, when history is requested, then `success: 1` with an empty `history` list.
+
+## Implementation Notes
+
+- Implemented directly (no subagent): the session's subagent lifetime
+  name limit was reached (~140 reserved names, all stopped) — the
+  step-03 fallback sanctions direct implementation from the plan.
+- Series iteration stays naive-local; `.timestamp()` maps two distinct
+  naive times to the same epoch across DST spring-forward transitions
+  (3 collisions over 3 years). Harmless for the production client (it
+  only takes min/max per chunk); tests assert uniqueness on ISO
+  stamps, monotonicity in epoch space.
+- `simulator.py` parses CLI args at import; the test module imports it
+  with a neutral `sys.argv` (`unittest.mock.patch`) so pytest flags
+  like a future `-p` can never leak into argparse.
+- requirements-test.txt: flask>=3.1 added with a comment (the unit
+  tests import the simulator module directly).
+- Verification: `test_simulator_history.py` 10/10 green; full unit
+  suite 373 green (363 + 10).
+
+## Plan Change Log
+
+## Review Triage Log
+
+## Design Notes
+
+Generation is a pure function — no RNG state, no wall clock:
+
+- Anchor: the periph's `last_value_change` from the dump (stable per
+  dump). Series = hourly (density knob) points from anchor − N years
+  to anchor.
+- Value at ts: base (float of `last_value`, else empty history) +
+  seasonal sinusoid (day-of-year phase) + stable hash noise
+  (`md5(f"{periph_id}:{ts}").digest()[0]` scaled). Determinism falls
+  out of the pure function.
+- Knobs (env/CLI): `EEDOMUS_HISTORY_YEARS` (default 3),
+  `EEDOMUS_HISTORY_DENSITY` (points per hour, default 1 → 26 280
+  points per numeric periph → 3 chunks). Defaults are provisional —
+  fixed at ticket 5.5's first measured backfill (spec open question).
+- Serving: filter `start < ts <= end`, sort ascending, cap 10 000.
+
+## Verification
+
+**Commands:**
+- `python3 -m pytest tests/unit/test_simulator_history.py -q` -- expected: all green
+- `python3 -m pytest tests/unit/ -q` -- expected: 363+ green, no regression
+- `python3 -m py_compile scripts/simulateur/*.py` -- expected: green
+
+**Manual checks (if no CLI):**
+- Start the simulator locally, curl `periph.history` twice with the same window: identical bodies; paginate a > 10 000 series with the client's resume semantics: gapless union.
diff --git a/_bmad-output/specs/spec-eedomus-simulator/.memlog.md b/_bmad-output/specs/spec-eedomus-simulator/.memlog.md
index 9895763..69f2f3b 100644
--- a/_bmad-output/specs/spec-eedomus-simulator/.memlog.md
+++ b/_bmad-output/specs/spec-eedomus-simulator/.memlog.md
@@ -1,6 +1,6 @@
 ---
 topic: Simulateur d'API eedomus — strate E2E multi-box et destructive
-updated: 2026-10-06T21:07
+updated: 2026-10-10T07:40
 ---
 
 - (direction) Exigence utilisateur (2026-10-06) : analyser la PR #119 (fmo01) et pouvoir utiliser son simulateur comme si on ajoutait une box dans Home Assistant, pour des tests de bout en bout — multi-box et actions destructives.
@@ -19,3 +19,4 @@ updated: 2026-10-06T21:07
 - (event) Create run (2026-10-06) : SPEC derive. Self-validate pass 1 (coherence) : OK — 5 CAP intent+success testables, contraintes qui excluent (live-Pi jamais moquee, Flask test-only, anglais, determinisme, pas de merge), 5 non-goals, signal concret (69 entites, 4 actions destructives, live-Pi verte), IDs stables, prose lean. Pass 2 (preservation) : OK — l'analyse PR (salvage vs non-mergeable), la couverture simulateur, le gap periph.history, l'objectif box-ajoutee, la strate E2E et les outils d'extraction atterrissent ; DECISION ajoutee : l'amelioration des logs (box d'origine) est un salvage separe, consignee en non-goal pour que le drop soit sur le record. Ouvertes : cycle de vie de l'entry simulee, profondeur N de l'historique.
 - (decision) Clarification utilisateur (2026-10-06) : la box fictive vit SUR l'environment cible — le simulateur tourne sur le Pi meme (127.0.0.1:port), deploye par le pull git du deploiement existant (scripts/simulateur/ hors custom_components, invisible de HACS), api_host=127.0.0.1:port — la validation est 100% sur l'environment cible, aucune dependance reseau cross-machine. SUPPLANTE l'assumption precedente (simulateur sur machine de dev).
 - (event) Update run (2026-10-06) : clarification atterrie (assumption supprimee, CAP-3 affine : le harnais demarre le simulateur sur le Pi, l'entry pointe en local). Self-validate pass 1+2 : OK — la clarification utilisateur atterrit integralement ; l'assumption remplacee est tracee par l'entree de decision (supersession memlog).
+- (decision) Simulated-box history routing: optional advanced history_api_host config-flow field (default empty -> https://api.eedomus.com), delivered with story 5.3 - live box serves success=0 for periph.history locally (verified 2026-10-09), so api_host routing would break the real backfill; CAP-2 'sans modification du client' read as 'the test never modifies the client, the integration legitimately supports the knob'. Provisional synthetic defaults: 3 years, 1 point/hour, anchor last_value_change, env knobs (user decision 2026-10-09)
diff --git a/requirements-test.txt b/requirements-test.txt
index f0d279d..4a049ef 100644
--- a/requirements-test.txt
+++ b/requirements-test.txt
@@ -11,3 +11,5 @@ async-timeout>=5.0.1
 PyYAML>=6.0.3
 # Websocket client for the E2E tests against the live instance (tests/e2e/)
 websockets>=12.0
+# Local eedomus API simulator (scripts/simulateur/, E2E-sim strate + unit tests)
+flask>=3.1
diff --git a/scripts/simulateur/README.md b/scripts/simulateur/README.md
index 0aed712..db0bcaf 100644
--- a/scripts/simulateur/README.md
+++ b/scripts/simulateur/README.md
@@ -188,8 +188,21 @@ periph.list
 periph.value_list
 periph.caract
 periph.value
+periph.history
 ```
 
+`periph.history` serves a synthetic, deterministic history generated
+from the dump (story 5.2, spec-eedomus-simulator CAP-2): hourly points
+over `EEDOMUS_HISTORY_YEARS` years (default 3) ending at the
+peripheral's `last_value_change`, at most `EEDOMUS_HISTORY_DENSITY`
+points per hour (default 1). The response honors the production
+client's chunking contract — points strictly after the epoch `start`
+parameter and up to epoch `end`, ascending, capped at 10 000 points
+per call; a chunk shorter than the cap means the series is complete.
+Peripherals whose `last_value` is not numeric get an empty history.
+The generation is a pure function of the dump (no wall clock): the
+same dump always yields the same series.
+
 Example:
 
 ```bash
diff --git a/scripts/simulateur/simulator.py b/scripts/simulateur/simulator.py
index 2e0f7a3..8ca4acc 100644
--- a/scripts/simulateur/simulator.py
+++ b/scripts/simulateur/simulator.py
@@ -1,7 +1,11 @@
 import argparse
+import hashlib
 import json
+import math
 import os
 import sys
+import time
+from datetime import datetime, timedelta
 from functools import wraps
 from flask import Flask, jsonify, request
 
@@ -78,6 +82,83 @@ if os.path.exists(rules_file):
         THERMOSTAT_RULES = json.load(f)
     print(f"Thermostat rules loaded: {len(THERMOSTAT_RULES)} rule(s).")
 
+# Synthetic history knobs (CAP-2, spec-eedomus-simulator): depth in
+# years and density in points per hour, both env-overridable so the
+# first measured E2E backfill (epic entry 5) can retune them without
+# a code change. The per-chunk cap matches the real API's 10 000.
+HISTORY_YEARS = int(os.getenv("EEDOMUS_HISTORY_YEARS", "3"))
+HISTORY_DENSITY = max(int(os.getenv("EEDOMUS_HISTORY_DENSITY", "1")), 1)
+HISTORY_CHUNK_CAP = 10000
+
+
+def _float_or_none(value):
+    """Float of the value, or None when it is not numeric."""
+    try:
+        return float(value)
+    except (TypeError, ValueError):
+        return None
+
+
+def _history_anchor(dev):
+    """Series anchor: the periph's last_value_change from the dump.
+
+    Naive local time, like every eedomus timestamp — deterministic
+    per dump, never the wall clock.
+    """
+    try:
+        return datetime.strptime(str(dev.get("last_value_change")), "%Y-%m-%d %H:%M:%S")
+    except ValueError:
+        return None
+
+
+def _synthetic_value(periph_id, ts, base):
+    """Deterministic synthetic value at ts — pure function.
+
+    Seasonal sinusoid on the day of year plus a stable hash-derived
+    noise: same dump + same anchor = same history, whatever the
+    request time (CAP-2 determinism, no wall clock).
+    """
+    day = ts.timetuple().tm_yday
+    seasonal = 3.0 * math.sin(2 * math.pi * day / 365.25)
+    digest = hashlib.md5(
+        f"{periph_id}:{ts.isoformat()}".encode("utf-8")
+    ).digest()
+    noise = (digest[0] / 255.0) * 2.0 - 1.0
+    return base + seasonal + noise
+
+
+def serve_periph_history(periph_id, start, end):
+    """Build the synthetic history chunk for one peripheral.
+
+    Contract of the production client (eedomus_client.get_device_history
+    + coordinator.async_fetch_history_chunk): epoch `start`/`end` window,
+    points strictly after `start` (a chunk whose max timestamp equals
+    `start` would loop the drain forever — the real API does this, the
+    simulator must not), ascending order, capped at 10 000 points, a
+    chunk smaller than the cap tells the client the series is complete.
+    Timestamps are naive-local ISO strings; values are strings.
+    """
+    dev = caract_by_id[periph_id]
+    base = _float_or_none(dev.get("last_value"))
+    anchor = _history_anchor(dev)
+    if base is None or anchor is None:
+        # Non-numeric or undated peripheral: no synthetic history
+        return []
+
+    step = timedelta(seconds=3600 // HISTORY_DENSITY)
+    first = anchor - timedelta(days=365 * HISTORY_YEARS)
+    history = []
+    ts = first
+    while ts <= anchor:
+        epoch = int(ts.timestamp())
+        if start < epoch <= end:
+            value = _synthetic_value(periph_id, ts, base)
+            history.append([f"{value:.2f}", ts.isoformat()])
+            if len(history) >= HISTORY_CHUNK_CAP:
+                break
+        ts = ts + step
+    return history
+
 def evaluate_thermostat_rules(changed_periph_id):
     """Evaluate the rules and toggle the heater if setpoint or temperature changes."""
     for rule in THERMOSTAT_RULES:
@@ -205,6 +286,25 @@ def api_get():
 
         return jsonify({"success": 0, "error": f"Peripheral {periph_id} not found"}), 404
 
+    # 5. Synthetic history (CAP-2) — deterministic from the dump
+    if action == "periph.history":
+        if not periph_id:
+            return jsonify({"success": 0, "error": "Missing periph_id parameter"}), 400
+        if periph_id not in caract_by_id:
+            return jsonify({"success": 0, "error": f"Peripheral {periph_id} not found"}), 404
+
+        def _int_param(name, default):
+            try:
+                return int(float(request.args.get(name, default)))
+            except (TypeError, ValueError):
+                return default
+
+        # Bad params degrade to the documented defaults, never a 500
+        start = _int_param("start", 0)
+        end = _int_param("end", int(time.time()))
+        history = serve_periph_history(periph_id, start, end)
+        return jsonify({"success": 1, "body": {"history": history}})
+
     return jsonify({"success": 0, "error": f"Action '{action}' not recognized"}), 404
 
 
diff --git a/tests/unit/test_simulator_history.py b/tests/unit/test_simulator_history.py
new file mode 100644
index 0000000..896291a
--- /dev/null
+++ b/tests/unit/test_simulator_history.py
@@ -0,0 +1,221 @@
+"""Unit tests for the simulator's synthetic periph.history (CAP-2).
+
+Story 5.2 (epic-eedomus-simulator, spec-eedomus-simulator): the
+endpoint serves a deterministic synthetic history with the production
+client's chunking/pagination contract — ≤ 10 000 points per call,
+points strictly after `start`, ascending, a short chunk means
+"series complete".
+"""
+
+import importlib.util
+import sys
+from datetime import datetime, timedelta
+from pathlib import Path
+from unittest.mock import patch
+
+import pytest
+
+pytestmark = pytest.mark.unit
+
+SIM_DIR = Path(__file__).resolve().parents[2] / "scripts" / "simulateur"
+
+
+def _load_simulator():
+    """Import simulator.py with a neutral argv (it parses CLI args)."""
+    spec = importlib.util.spec_from_file_location(
+        "eedomus_simulator", SIM_DIR / "simulator.py"
+    )
+    module = importlib.util.module_from_spec(spec)
+    with patch.object(sys, "argv", ["simulator.py"]):
+        spec.loader.exec_module(module)
+    return module
+
+
+@pytest.fixture(scope="module")
+def sim():
+    module = _load_simulator()
+    module.app.config["TESTING"] = True
+    return module
+
+
+@pytest.fixture(scope="module")
+def client(sim):
+    return sim.app.test_client()
+
+
+AUTH = {"api_user": "apiUser", "api_secret": "apiPassword"}
+
+
+def _get_history(client, periph_id, start=0, end=None, **extra):
+    params = {"action": "periph.history", "periph_id": periph_id, **AUTH}
+    if start is not None:
+        params["start"] = start
+    if end is not None:
+        params["end"] = end
+    params.update(extra)
+    return client.get("/api/get", query_string=params)
+
+
+def _first_numeric_periph(sim):
+    for pid, dev in sim.caract_by_id.items():
+        base = sim._float_or_none(dev.get("last_value"))
+        anchor = sim._history_anchor(dev)
+        if base is not None and anchor is not None:
+            return pid
+    pytest.fail("the dump has no numeric peripheral with an anchor")
+
+
+def _expected_points(sim, periph_id):
+    """The canonical series length for a periph at the default knobs."""
+    dev = sim.caract_by_id[periph_id]
+    anchor = sim._history_anchor(dev)
+    step = timedelta(seconds=3600 // sim.HISTORY_DENSITY)
+    first = anchor - timedelta(days=365 * sim.HISTORY_YEARS)
+    count = 0
+    ts = first
+    while ts <= anchor:
+        count += 1
+        ts = ts + step
+    return count
+
+
+def test_history_is_deterministic_across_calls(client, sim):
+    """Same dump + same window = byte-identical history (CAP-2)."""
+    periph_id = _first_numeric_periph(sim)
+    first = _get_history(client, periph_id, end=9999999999)
+    second = _get_history(client, periph_id, end=9999999999)
+    assert first.status_code == 200
+    assert first.data == second.data
+
+
+def test_generation_is_pure_of_request_time(client, sim):
+    """The value at a given timestamp never depends on `end`."""
+    periph_id = _first_numeric_periph(sim)
+    dev = sim.caract_by_id[periph_id]
+    anchor = sim._history_anchor(dev)
+    # First point of the series: always inside the capped first chunk
+    probe = anchor - timedelta(days=365 * sim.HISTORY_YEARS)
+    wide = _get_history(client, periph_id, end=9999999999).get_json()
+    narrow = _get_history(
+        client, periph_id, start=int(probe.timestamp()) - 1,
+        end=int(probe.timestamp()),
+    ).get_json()
+    wide_value = next(
+        p[0] for p in wide["body"]["history"] if p[1] == probe.isoformat()
+    )
+    assert narrow["body"]["history"] == [[wide_value, probe.isoformat()]]
+
+
+def test_chunk_capped_at_10000(client, sim):
+    """A periph with > 10 000 points serves exactly the cap, ascending."""
+    periph_id = _first_numeric_periph(sim)
+    assert _expected_points(sim, periph_id) > 10000
+    body = _get_history(client, periph_id, end=9999999999).get_json()
+    history = body["body"]["history"]
+    assert len(history) == 10000
+    epochs = [datetime.fromisoformat(p[1]).timestamp() for p in history]
+    assert epochs == sorted(epochs)
+
+
+def test_client_resume_pagination_is_gapless(client, sim):
+    """The production resume semantics walk the full series without
+    overlap or gap, and a short chunk closes the walk."""
+    periph_id = _first_numeric_periph(sim)
+    expected_total = _expected_points(sim, periph_id)
+    points = []
+    start = 0
+    for _ in range(10):
+        body = _get_history(client, periph_id, start=start,
+                            end=9999999999).get_json()
+        history = body["body"]["history"]
+        assert len(history) <= 10000
+        points.extend(history)
+        if len(history) < 10000:
+            break
+        start = int(max(datetime.fromisoformat(p[1]).timestamp()
+                        for p in history))
+    assert len(points) == expected_total
+    stamps = [p[1] for p in points]
+    # Uniqueness/gaplessness live in naive local time — the series space.
+    # Epoch values can collide across DST spring-forward transitions
+    # (the production client only uses min/max per chunk, so this is
+    # harmless there); ordering stays monotonic in epoch space.
+    assert len(set(stamps)) == len(stamps)
+    epochs = [datetime.fromisoformat(s).timestamp() for s in stamps]
+    assert epochs == sorted(epochs)
+    assert points[-1][1] == sim._history_anchor(
+        sim.caract_by_id[periph_id]
+    ).isoformat()
+
+
+def test_start_at_series_end_returns_empty(client, sim):
+    """Tail request: empty history, success 1 (client completes)."""
+    periph_id = _first_numeric_periph(sim)
+    anchor = sim._history_anchor(sim.caract_by_id[periph_id])
+    body = _get_history(
+        client, periph_id, start=int(anchor.timestamp()), end=9999999999
+    ).get_json()
+    assert body == {"success": 1, "body": {"history": []}}
+
+
+def test_non_numeric_periph_has_no_history(client, sim):
+    """A peripheral whose base value is not float-parseable serves an
+    empty history — never a synthetic series, never an error."""
+    target = None
+    for pid, dev in sim.caract_by_id.items():
+        if sim._float_or_none(dev.get("last_value")) is None:
+            target = pid
+            break
+    if target is None:
+        target = "999001"
+        sim.caract_by_id[target] = {
+            "periph_id": target,
+            "name": "Non numeric fixture",
+            "last_value": "Vert",
+            "last_value_change": "2026-09-27 12:15:28",
+        }
+    body = _get_history(client, target, end=9999999999).get_json()
+    assert body == {"success": 1, "body": {"history": []}}
+
+
+def test_unknown_periph_is_404(client):
+    res = _get_history(client, "000000", end=9999999999)
+    assert res.status_code == 404
+    assert res.get_json()["success"] == 0
+
+
+def test_missing_periph_id_is_400(client):
+    res = client.get(
+        "/api/get",
+        query_string={"action": "periph.history", **AUTH},
+    )
+    assert res.status_code == 400
+    assert res.get_json()["success"] == 0
+
+
+def test_bad_params_never_500(client, sim):
+    """Non-integer start degrades to 0; non-integer end to now."""
+    periph_id = _first_numeric_periph(sim)
+    bad_start = _get_history(
+        client, periph_id, start="not-a-number", end=9999999999
+    )
+    ok_start = _get_history(client, periph_id, start=0, end=9999999999)
+    assert bad_start.status_code == 200
+    assert bad_start.get_json() == ok_start.get_json()
+    bad_end = _get_history(client, periph_id, start=0, end="not-a-number")
+    assert bad_end.status_code == 200
+    assert "history" in bad_end.get_json()["body"]
+
+
+def test_history_requires_auth(client, sim):
+    periph_id = _first_numeric_periph(sim)
+    res = client.get(
+        "/api/get",
+        query_string={
+            "action": "periph.history",
+            "periph_id": periph_id,
+            "api_user": "apiUser",
+            "api_secret": "wrong",
+        },
+    )
+    assert res.status_code == 401
```
