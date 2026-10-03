"""Fixtures for E2E tests against a live Home Assistant instance.

These tests run against the Raspberry Pi production instance.
Credentials and target are read from the project .env file:
  HA_URL     - Home Assistant base URL (default http://192.168.1.5:8123)
  HA_TOKEN   - long-lived access token

The peripheral used for write tests (set_value) is the "RubanLed Salon"
(eedomus periph_id 3485837, entity light.rubanled_salon_2).
"""

import os
import time
from pathlib import Path

import pytest
import requests

# Load .env from the project root
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

HA_URL = os.environ.get("HA_URL", "http://192.168.1.5:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

# Test peripheral: RubanLed Salon
TEST_PERIPH_ID = "3485837"
TEST_ENTITY_ID = "light.rubanled_salon_2"


@pytest.fixture(scope="session")
def ha_headers():
    """Authorization headers for the HA REST API."""
    assert HA_TOKEN, "HA_TOKEN missing from .env"
    return {"Authorization": f"Bearer {HA_TOKEN}"}


@pytest.fixture(scope="session")
def ha_api(ha_headers):
    """Small helper client around the HA REST API."""

    class HaApi:
        def get(self, path, **kwargs):
            return requests.get(f"{HA_URL}{path}", headers=ha_headers, timeout=30, **kwargs)

        def post(self, path, json=None, **kwargs):
            return requests.post(
                f"{HA_URL}{path}", headers=ha_headers, json=json, timeout=60, **kwargs
            )

        def get_state(self, entity_id):
            r = self.get(f"/api/states/{entity_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

        def call_service(self, domain, service, data=None):
            r = self.post(f"/api/services/{domain}/{service}", json=data or {})
            r.raise_for_status()
            return r.json()

        def wait_for_state(self, entity_id, expected, timeout=30):
            """Poll until entity state matches expected (or is not None)."""
            deadline = time.time() + timeout
            while time.time() < deadline:
                state = self.get_state(entity_id)
                if state is not None:
                    if expected is None or state["state"] == expected:
                        return state
                time.sleep(1)
            raise TimeoutError(
                f"{entity_id} did not reach state {expected!r} within {timeout}s"
            )

    return HaApi()


@pytest.fixture(scope="session")
def config_entry_id(ha_api):
    """The eedomus config entry id from the live instance."""
    r = ha_api.get("/api/config/config_entries/entry")
    r.raise_for_status()
    for entry in r.json():
        if entry["domain"] == "eedomus":
            return entry["entry_id"]
    pytest.fail("No eedomus config entry found on the instance")


@pytest.fixture(scope="session")
def ws_call(ha_headers):
    """Callable executing websocket commands on the live instance.

    Returns an async function result synchronously: call("type", {...})
    resolves the command response (raises on a websocket error).

    Every send/recv is bounded by E2E_WS_TIMEOUT seconds (default 120):
    a stuck command raises asyncio.TimeoutError instead of hanging the
    suite forever (e.g. a reload blocked by a long-running import).
    """
    import asyncio
    import json as jsonlib
    import os

    import websockets

    ws_url = HA_URL.replace("http", "ws") + "/api/websocket"
    ws_timeout = float(os.environ.get("E2E_WS_TIMEOUT", "120"))

    async def _run(msg):
        async with websockets.connect(ws_url) as ws:
            await asyncio.wait_for(ws.recv(), timeout=ws_timeout)
            await ws.send(
                jsonlib.dumps({"type": "auth", "access_token": HA_TOKEN})
            )
            auth = jsonlib.loads(
                await asyncio.wait_for(ws.recv(), timeout=ws_timeout)
            )
            assert auth["type"] == "auth_ok", auth
            await ws.send(jsonlib.dumps(dict(msg, id=1)))
            res = jsonlib.loads(
                await asyncio.wait_for(ws.recv(), timeout=ws_timeout)
            )
            if not res.get("success"):
                raise AssertionError(f"websocket command failed: {res}")
            return res["result"]

    def call(msg_type, payload=None):
        msg = dict(payload or {})
        msg["type"] = msg_type
        return asyncio.run(_run(msg))

    return call
