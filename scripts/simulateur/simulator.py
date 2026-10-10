import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)

# Absolute directory of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_script_file_path(filename: str) -> str:
    """Return the full path of a file next to this script."""
    return os.path.join(SCRIPT_DIR, filename)


# CLI arguments / environment variables parsing
parser = argparse.ArgumentParser(description="Local eedomus API simulator (Flask)")
parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=int(os.getenv("EEDOMUS_PORT", "8080")),
    help="HTTP listen port (default/env: 8080 / EEDOMUS_PORT)",
)
parser.add_argument(
    "-u",
    "--api-user",
    type=str,
    default=os.getenv("EEDOMUS_API_USER", "apiUser"),
    help="Eedomus API user (default/env: apiUser / EEDOMUS_API_USER)",
)
parser.add_argument(
    "-s",
    "--api-secret",
    type=str,
    default=os.getenv("EEDOMUS_API_SECRET", "apiPassword"),
    help="Eedomus API secret (default/env: apiPassword / EEDOMUS_API_SECRET)",
)

args, _ = parser.parse_known_args()

API_USER = args.api_user
API_SECRET = args.api_secret
PORT = args.port

# Data loading from the script directory

dump_file = get_script_file_path("eedomus_dump.json")
rules_file = get_script_file_path("thermostat_rules.json")

# 1. Load eedomus_dump.json
try:
    with open(dump_file, "r", encoding="utf-8") as f:
        dump = json.load(f)
        periph_list_data = dump.get("periph_list", [])
        value_list_data = dump.get("value_list", [])
        caract_list_data = dump.get("caract", [])
    print("Data loaded from 'eedomus_dump.json'.")
except FileNotFoundError:
    print("The eedomus_dump.json data file must be present.")
    sys.exit(1)

# Index by periph_id, keeping the exact structure
caract_by_id = {
    str(dev["periph_id"]): dev
    for dev in caract_list_data
    if isinstance(dev, dict) and "periph_id" in dev
}

print(f"Simulator ready: {len(caract_by_id)} devices indexed.")

# Load the thermostat rules file
THERMOSTAT_RULES = []
if os.path.exists(rules_file):
    with open(rules_file, "r", encoding="utf-8") as f:
        THERMOSTAT_RULES = json.load(f)
    print(f"Thermostat rules loaded: {len(THERMOSTAT_RULES)} rule(s).")

# Synthetic history knobs (CAP-2, spec-eedomus-simulator): depth in
# years and density in points per hour, both env-overridable so the
# first measured E2E backfill (epic entry 5) can retune them without
# a code change. The per-chunk cap matches the real API's 10 000.
HISTORY_YEARS = int(os.getenv("EEDOMUS_HISTORY_YEARS", "3"))
HISTORY_DENSITY = max(int(os.getenv("EEDOMUS_HISTORY_DENSITY", "1")), 1)
HISTORY_CHUNK_CAP = 10000


def _float_or_none(value):
    """Float of the value, or None when it is not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _history_anchor(dev):
    """Series anchor: the periph's last_value_change from the dump.

    Naive local time, like every eedomus timestamp — deterministic
    per dump, never the wall clock.
    """
    try:
        return datetime.strptime(str(dev.get("last_value_change")), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _synthetic_value(periph_id, ts, base):
    """Deterministic synthetic value at ts — pure function.

    Seasonal sinusoid on the day of year plus a stable hash-derived
    noise: same dump + same anchor = same history, whatever the
    request time (CAP-2 determinism, no wall clock).
    """
    day = ts.timetuple().tm_yday
    seasonal = 3.0 * math.sin(2 * math.pi * day / 365.25)
    digest = hashlib.md5(f"{periph_id}:{ts.isoformat()}".encode("utf-8")).digest()
    noise = (digest[0] / 255.0) * 2.0 - 1.0
    return base + seasonal + noise


def serve_periph_history(periph_id, start, end):
    """Build the synthetic history chunk for one peripheral.

    Contract of the production client (eedomus_client.get_device_history
    + coordinator.async_fetch_history_chunk): epoch `start`/`end` window,
    points strictly after `start` (a chunk whose max timestamp equals
    `start` would loop the drain forever — the real API does this, the
    simulator must not), ascending order, capped at 10 000 points, a
    chunk smaller than the cap tells the client the series is complete.
    Timestamps are naive-local ISO strings; values are strings.
    """
    dev = caract_by_id[periph_id]
    base = _float_or_none(dev.get("last_value"))
    anchor = _history_anchor(dev)
    if base is None or anchor is None:
        # Non-numeric or undated peripheral: no synthetic history
        return []

    step = timedelta(seconds=3600 // HISTORY_DENSITY)
    first = anchor - timedelta(days=365 * HISTORY_YEARS)
    history = []
    ts = first
    while ts <= anchor:
        epoch = int(ts.timestamp())
        if start < epoch <= end:
            value = _synthetic_value(periph_id, ts, base)
            history.append([f"{value:.2f}", ts.isoformat()])
            if len(history) >= HISTORY_CHUNK_CAP:
                break
        ts = ts + step
    return history


def evaluate_thermostat_rules(changed_periph_id):
    """Evaluate the rules and toggle the heater if setpoint or temperature changes."""
    for rule in THERMOSTAT_RULES:
        setpoint_id = str(rule["setpoint_id"])
        sensor_id = str(rule["sensor_id"])

        # If the changed peripheral impacts this rule
        if str(changed_periph_id) in (setpoint_id, sensor_id):
            try:
                setpoint_val = float(caract_by_id[setpoint_id].get("last_value", 0))
                sensor_val = float(caract_by_id[sensor_id].get("last_value", 0))
                switch_id = str(rule["switch_id"])

                # Heater trigger logic
                if setpoint_val > sensor_val:
                    new_switch_val = str(rule.get("on_value", "100"))
                else:
                    new_switch_val = str(rule.get("off_value", "0"))

                # Apply the new state when it changes
                current_switch_val = str(caract_by_id[switch_id].get("last_value", ""))
                if current_switch_val != new_switch_val:
                    caract_by_id[switch_id]["last_value"] = new_switch_val
                    print(
                        f"[SIMU THERMOSTAT] '{rule['name']}' -> setpoint:"
                        f" {setpoint_val}°C | measured: {sensor_val}°C => switch"
                        f" {switch_id} set to: {new_switch_val}"
                    )
            except (ValueError, KeyError) as e:
                print(
                    f"[SIMU THERMOSTAT ERROR] rule evaluation failed"
                    f" {rule['name']}: {e}"
                )


def require_eedomus_auth(f):
    """Eedomus API access-control decorator."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.args.get("api_user")
        secret = request.args.get("api_secret")
        if user != API_USER or secret != API_SECRET:
            return jsonify({"success": 0, "error": "Authentication failed"}), 401
        return f(*args, **kwargs)

    return decorated_function


def format_caract(dev, show_config):
    """
    Format the caract response per show_config:
    - '1': the full object with the hardware configuration
    - '0' (or absent): the 7 base eedomus fields
    """
    if str(show_config) == "1":
        return dev

    keys = [
        "periph_id",
        "name",
        "last_value",
        "last_value_text",
        "unit",
        "battery",
        "last_value_change",
    ]
    return {k: dev.get(k, "") for k in keys}


@app.route("/api/get", methods=["GET"])
@require_eedomus_auth
def api_get():
    action = request.args.get("action")
    periph_id = request.args.get("periph_id", "")
    show_config = request.args.get("show_config", "0")

    # 1. Connection validation
    if action == "auth.test":
        return jsonify({"success": 1, "body": {"auth": 1}})

    # 2. Peripheral summary list
    if action == "periph.list":
        return jsonify({"success": 1, "body": periph_list_data})

    # 3. Possible values list
    if action == "periph.value_list":
        if periph_id == "all":
            return jsonify({"success": 1, "body": value_list_data})

        # Single ID or comma-separated list
        requested_ids = set(pid.strip() for pid in periph_id.split(",") if pid.strip())
        filtered = [
            v for v in value_list_data if str(v.get("periph_id")) in requested_ids
        ]
        return jsonify({"success": 1, "body": filtered})

    # 4. Detailed characteristics (with/without show_config)
    if action == "periph.caract":
        if not periph_id:
            return jsonify({"success": 0, "error": "Missing periph_id parameter"}), 400

        # Case 1: the "all" request
        if periph_id == "all":
            data = [format_caract(d, show_config) for d in caract_list_data]
            return jsonify({"success": 1, "body": data})

        # Case 2: comma-separated ID list (e.g. periph_id=123,456)
        if "," in periph_id:
            requested_ids = [pid.strip() for pid in periph_id.split(",") if pid.strip()]
            data = [
                format_caract(caract_by_id[pid], show_config)
                for pid in requested_ids
                if pid in caract_by_id
            ]
            return jsonify({"success": 1, "body": data})

        # Case 3: single ID (e.g. periph_id=123)
        if periph_id in caract_by_id:
            data = format_caract(caract_by_id[periph_id], show_config)
            return jsonify({"success": 1, "body": data})

        return (
            jsonify({"success": 0, "error": f"Peripheral {periph_id} not found"}),
            404,
        )

    # 5. Synthetic history (CAP-2) — deterministic from the dump
    if action == "periph.history":
        if not periph_id:
            return jsonify({"success": 0, "error": "Missing periph_id parameter"}), 400
        if periph_id not in caract_by_id:
            return (
                jsonify({"success": 0, "error": f"Peripheral {periph_id} not found"}),
                404,
            )

        def _int_param(name, default):
            try:
                return int(float(request.args.get(name, default)))
            except (TypeError, ValueError):
                return default

        # Bad params degrade to the documented defaults, never a 500
        start = _int_param("start", 0)
        end = _int_param("end", int(time.time()))
        history = serve_periph_history(periph_id, start, end)
        return jsonify({"success": 1, "body": {"history": history}})

    return jsonify({"success": 0, "error": f"Action '{action}' not recognized"}), 404


@app.route("/api/set", methods=["GET"])
@require_eedomus_auth
def api_set():
    action = request.args.get("action")
    periph_id = request.args.get("periph_id")
    value = request.args.get("value")

    if action == "periph.value" and periph_id in caract_by_id:
        caract_by_id[periph_id]["last_value"] = str(value)
        print(
            f"[HA ACTION] -> Device {periph_id}"
            f" ({caract_by_id[periph_id].get('name')}) changed to: {value}"
        )

        # Evaluate the thermostats impacted by the HA command
        evaluate_thermostat_rules(periph_id)

        return jsonify({"success": 1, "body": {"result": "OK"}})

    return jsonify({"success": 0, "error": "Update failed"}), 400


@app.route("/simulate/change", methods=["POST"])
def simulate_change():
    """Local endpoint to change a sensor value manually."""
    data = request.get_json()
    periph_id = str(data.get("periph_id"))
    new_value = str(data.get("value"))

    if periph_id in caract_by_id:
        caract_by_id[periph_id]["last_value"] = new_value
        print(
            f"[SIMULATION] -> sensor {periph_id} ({caract_by_id[periph_id].get('name')}) changed to: {new_value}"
        )

        # Evaluate the thermostats when an ambient temperature changes
        evaluate_thermostat_rules(periph_id)

        return jsonify(
            {"status": "updated", "periph_id": periph_id, "new_value": new_value}
        )

    return jsonify({"error": "Device not found"}), 404


if __name__ == "__main__":
    print(f"Simulator listening on http://0.0.0.0:{PORT}")
    print(f"API user: {API_USER} | API secret: {API_SECRET}")

    app.run(host="0.0.0.0", port=PORT)
