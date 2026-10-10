"""Unit tests for the simulator's synthetic periph.history (CAP-2).

Story 5.2 (epic-eedomus-simulator, spec-eedomus-simulator): the
endpoint serves a deterministic synthetic history with the production
client's chunking/pagination contract — ≤ 10 000 points per call,
points strictly after `start`, ascending, a short chunk means
"series complete".
"""

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

SIM_DIR = Path(__file__).resolve().parents[2] / "scripts" / "simulateur"


def _load_simulator():
    """Import simulator.py with a neutral argv (it parses CLI args)."""
    spec = importlib.util.spec_from_file_location(
        "eedomus_simulator", SIM_DIR / "simulator.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "argv", ["simulator.py"]):
        spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sim():
    module = _load_simulator()
    module.app.config["TESTING"] = True
    return module


@pytest.fixture(scope="module")
def client(sim):
    return sim.app.test_client()


AUTH = {"api_user": "apiUser", "api_secret": "apiPassword"}


def _get_history(client, periph_id, start=0, end=None, **extra):
    params = {"action": "periph.history", "periph_id": periph_id, **AUTH}
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    params.update(extra)
    return client.get("/api/get", query_string=params)


def _first_numeric_periph(sim):
    for pid, dev in sim.caract_by_id.items():
        base = sim._float_or_none(dev.get("last_value"))
        anchor = sim._history_anchor(dev)
        if base is not None and anchor is not None:
            return pid
    pytest.fail("the dump has no numeric peripheral with an anchor")


def _expected_points(sim, periph_id):
    """The canonical series length for a periph at the default knobs."""
    dev = sim.caract_by_id[periph_id]
    anchor = sim._history_anchor(dev)
    step = timedelta(seconds=3600 // sim.HISTORY_DENSITY)
    first = anchor - timedelta(days=365 * sim.HISTORY_YEARS)
    count = 0
    ts = first
    while ts <= anchor:
        count += 1
        ts = ts + step
    return count


def test_history_is_deterministic_across_calls(client, sim):
    """Same dump + same window = byte-identical history (CAP-2)."""
    periph_id = _first_numeric_periph(sim)
    first = _get_history(client, periph_id, end=9999999999)
    second = _get_history(client, periph_id, end=9999999999)
    assert first.status_code == 200
    assert first.data == second.data


def test_generation_is_pure_of_request_time(client, sim):
    """The value at a given timestamp never depends on `end`."""
    periph_id = _first_numeric_periph(sim)
    dev = sim.caract_by_id[periph_id]
    anchor = sim._history_anchor(dev)
    # First point of the series: always inside the capped first chunk
    probe = anchor - timedelta(days=365 * sim.HISTORY_YEARS)
    wide = _get_history(client, periph_id, end=9999999999).get_json()
    narrow = _get_history(
        client,
        periph_id,
        start=int(probe.timestamp()) - 1,
        end=int(probe.timestamp()),
    ).get_json()
    wide_value = next(
        p[0] for p in wide["body"]["history"] if p[1] == probe.isoformat()
    )
    assert narrow["body"]["history"] == [[wide_value, probe.isoformat()]]


def test_chunk_capped_at_10000(client, sim):
    """A periph with > 10 000 points serves exactly the cap, ascending."""
    periph_id = _first_numeric_periph(sim)
    assert _expected_points(sim, periph_id) > 10000
    body = _get_history(client, periph_id, end=9999999999).get_json()
    history = body["body"]["history"]
    assert len(history) == 10000
    epochs = [datetime.fromisoformat(p[1]).timestamp() for p in history]
    assert epochs == sorted(epochs)


def test_client_resume_pagination_is_gapless(client, sim):
    """The production resume semantics walk the full series without
    overlap or gap, and a short chunk closes the walk."""
    periph_id = _first_numeric_periph(sim)
    expected_total = _expected_points(sim, periph_id)
    points = []
    start = 0
    for _ in range(10):
        body = _get_history(client, periph_id, start=start, end=9999999999).get_json()
        history = body["body"]["history"]
        assert len(history) <= 10000
        points.extend(history)
        if len(history) < 10000:
            break
        start = int(max(datetime.fromisoformat(p[1]).timestamp() for p in history))
    assert len(points) == expected_total
    stamps = [p[1] for p in points]
    # Uniqueness/gaplessness live in naive local time — the series space.
    # Epoch values can collide across DST spring-forward transitions
    # (the production client only uses min/max per chunk, so this is
    # harmless there); ordering stays monotonic in epoch space.
    assert len(set(stamps)) == len(stamps)
    epochs = [datetime.fromisoformat(s).timestamp() for s in stamps]
    assert epochs == sorted(epochs)
    assert points[-1][1] == sim._history_anchor(sim.caract_by_id[periph_id]).isoformat()


def test_start_at_series_end_returns_empty(client, sim):
    """Tail request: empty history, success 1 (client completes)."""
    periph_id = _first_numeric_periph(sim)
    anchor = sim._history_anchor(sim.caract_by_id[periph_id])
    body = _get_history(
        client, periph_id, start=int(anchor.timestamp()), end=9999999999
    ).get_json()
    assert body == {"success": 1, "body": {"history": []}}


def test_non_numeric_periph_has_no_history(client, sim):
    """A peripheral whose base value is not float-parseable serves an
    empty history — never a synthetic series, never an error."""
    target = None
    for pid, dev in sim.caract_by_id.items():
        if sim._float_or_none(dev.get("last_value")) is None:
            target = pid
            break
    if target is None:
        target = "999001"
        sim.caract_by_id[target] = {
            "periph_id": target,
            "name": "Non numeric fixture",
            "last_value": "Vert",
            "last_value_change": "2026-09-27 12:15:28",
        }
    body = _get_history(client, target, end=9999999999).get_json()
    assert body == {"success": 1, "body": {"history": []}}


def test_unknown_periph_is_404(client):
    res = _get_history(client, "000000", end=9999999999)
    assert res.status_code == 404
    assert res.get_json()["success"] == 0


def test_missing_periph_id_is_400(client):
    res = client.get(
        "/api/get",
        query_string={"action": "periph.history", **AUTH},
    )
    assert res.status_code == 400
    assert res.get_json()["success"] == 0


def test_bad_params_never_500(client, sim):
    """Non-integer start degrades to 0; non-integer end to now."""
    periph_id = _first_numeric_periph(sim)
    bad_start = _get_history(client, periph_id, start="not-a-number", end=9999999999)
    ok_start = _get_history(client, periph_id, start=0, end=9999999999)
    assert bad_start.status_code == 200
    assert bad_start.get_json() == ok_start.get_json()
    bad_end = _get_history(client, periph_id, start=0, end="not-a-number")
    assert bad_end.status_code == 200
    assert "history" in bad_end.get_json()["body"]


def test_history_requires_auth(client, sim):
    periph_id = _first_numeric_periph(sim)
    res = client.get(
        "/api/get",
        query_string={
            "action": "periph.history",
            "periph_id": periph_id,
            "api_user": "apiUser",
            "api_secret": "wrong",
        },
    )
    assert res.status_code == 401
