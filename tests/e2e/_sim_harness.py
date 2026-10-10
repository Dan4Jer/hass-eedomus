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
        """Kill the simulator process (best effort — teardown never raises)."""
        if self.pid:
            _ssh(f"kill {self.pid} 2>/dev/null; true", check=False)
            self.pid = None
