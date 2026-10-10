"""Simulated-box harness for the E2E-sim strate (spec-eedomus-simulator).

Boots the local eedomus API simulator ON the Raspberry Pi itself
(decision 2026-10-06: validation happens on the target environment;
the HA core container runs on the host network, so 127.0.0.1 from HA
is the Pi's loopback) and drives its lifecycle over SSH.

The harness is test infrastructure only — the live-Pi strate never
touches it (AD-16: two strates, live-Pi stays the regression truth).
"""

import os
import subprocess
import time

import requests

SIM_PORT = int(os.environ.get("E2E_SIM_PORT", "8199"))
SIM_USER = os.environ.get("E2E_SIM_USER", "simUser")
SIM_SECRET = os.environ.get("E2E_SIM_SECRET", "simSecret")
SIM_API_HOST = f"127.0.0.1:{SIM_PORT}"

REMOTE_IP = os.environ.get("REMOTE_IP", "192.168.1.5")
REMOTE_USER = os.environ.get("REMOTE_USER", "danjer")
REMOTE_PATH = os.environ.get(
    "REMOTE_PATH", "/homeassistant/custom_components/hass-eedomus"
)

# PEP 668 blocks system pip on the Pi (externally-managed): the
# simulator runs from a dedicated venv, created once and reused.
VENV_PATH = "~/eedomus-sim-venv"


def _ssh(cmd, timeout=120, check=True):
    """Run a command on the Pi over SSH."""
    proc = subprocess.run(
        ["ssh", f"{REMOTE_USER}@{REMOTE_IP}", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"ssh command failed: {cmd}\n{proc.stderr}")
    return proc


class SimulatedBox:
    """The simulator process running on the Pi, its lifecycle owned here."""

    def __init__(self):
        self.pid = None

    def start(self):
        """Kill any stale instance, bootstrap the venv, start, wait healthy."""
        _ssh(
            f"pkill -f 'simulator.py -p {SIM_PORT}' 2>/dev/null; true",
            check=False,
        )
        # Idempotent venv bootstrap (flask install is a no-op once done)
        _ssh(
            f"python3 -m venv {VENV_PATH} 2>/dev/null; "
            f"{VENV_PATH}/bin/pip install -q flask"
        )
        start_cmd = (
            f"cd {REMOTE_PATH}/scripts/simulateur && "
            f"EEDOMUS_API_USER='{SIM_USER}' "
            f"EEDOMUS_API_SECRET='{SIM_SECRET}' "
            f"nohup {VENV_PATH}/bin/python simulator.py -p {SIM_PORT} "
            f"> /tmp/eedomus-sim.log 2>&1 & echo $!"
        )
        proc = _ssh(start_cmd)
        lines = [line for line in proc.stdout.strip().splitlines() if line]
        self.pid = lines[-1]

        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                res = requests.get(
                    f"http://{REMOTE_IP}:{SIM_PORT}/api/get",
                    params={
                        "action": "auth.test",
                        "api_user": SIM_USER,
                        "api_secret": SIM_SECRET,
                    },
                    timeout=3,
                )
                if res.ok and res.json().get("body", {}).get("auth") == 1:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise RuntimeError(
            "simulator did not become healthy within 30s "
            "(check /tmp/eedomus-sim.log on the Pi)"
        )

    def stop(self):
        """Kill the simulator process (best effort — teardown never raises).

        The PID kill is backed by a pattern pkill: over SSH the
        captured PID can miss (shell wrapping), and a stale simulator
        on the port breaks the next run's health check.
        """
        if self.pid:
            _ssh(f"kill {self.pid} 2>/dev/null; true", check=False)
        _ssh(
            f"pkill -f 'simulator.py -p {SIM_PORT}' 2>/dev/null; true",
            check=False,
        )
        self.pid = None


# ------------------------------------------------------------------
# Real config-flow drive helpers (HA 2026 REST flow API)
# ------------------------------------------------------------------

SIM_TITLE_MARK = SIM_API_HOST  # entry title contains the api_host


def build_user_input(**overrides):
    """A user-step payload accepted by the flow's field validators."""
    payload = {
        "api_host": SIM_API_HOST,
        "history_api_host": SIM_API_HOST,
        "api_eedomus": True,
        "enable_api_proxy": False,
        "api_user": SIM_USER,
        "api_secret": SIM_SECRET,
        "scan_interval": 30,
        "history": False,
        "http_request_timeout": 10,
        "max_concurrent_requests": 5,
        "min_request_delay": 0.5,
        "enable_set_value_retry": False,
        "max_retries": 3,
        "enable_webhook": False,
        "api_proxy_disable_security": False,
        "php_fallback_enabled": False,
        "php_fallback_script_name": "",
        "php_fallback_timeout": 5,
    }
    payload.update(overrides)
    return payload


def sim_entries(ha_api):
    """The simulated entries present on the instance (stale-run guard)."""
    r = ha_api.get("/api/config/config_entries/entry")
    r.raise_for_status()
    return [
        e for e in r.json()
        if e["domain"] == "eedomus" and SIM_TITLE_MARK in e["title"]
    ]


def remove_entry(ha_api, entry_id):
    """Best-effort entry removal (a teardown must never raise)."""
    r = ha_api.delete(f"/api/config/config_entries/entry/{entry_id}")
    return r.status_code == 200


def create_sim_entry(ha_api, **payload_overrides):
    """Create the simulated entry through the real flow (REST flow API).

    Returns (entry_id, result). Raises AssertionError when the flow
    does not end in a loaded create_entry.
    """
    r = ha_api.post("/api/config/config_entries/flow", {"handler": "eedomus"})
    r.raise_for_status()
    flow_id = r.json()["flow_id"]
    r = ha_api.post(
        f"/api/config/config_entries/flow/{flow_id}",
        build_user_input(**payload_overrides),
    )
    r.raise_for_status()
    result = r.json()
    assert result["type"] == "create_entry", result
    assert result["result"]["state"] == "loaded", result["result"]
    assert SIM_TITLE_MARK in result["result"]["title"], result["result"]
    return result["result"]["entry_id"], result


def discard_flow(ha_api, flow_id):
    """Never leave a pending flow behind."""
    ha_api.delete(f"/api/config/config_entries/flow/{flow_id}")
