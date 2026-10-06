import argparse
import json
import os
import sys
from functools import wraps
from flask import Flask, jsonify, request

app = Flask(__name__)

# Répertoire absolu où se situe le script actuel
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_script_file_path(filename: str) -> str:
    """Retourne le chemin complet d'un fichier situé dans le même répertoire que ce script."""
    return os.path.join(SCRIPT_DIR, filename)


# Parsing des arguments CLI / variables d'environnement
parser = argparse.ArgumentParser(description="Simulateur d'API locale eedomus (Flask)")
parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=int(os.getenv("EEDOMUS_PORT", "8080")),
    help="Port HTTP d'écoute (défaut/env: 8080 / EEDOMUS_PORT)",
)
parser.add_argument(
    "-u",
    "--api-user",
    type=str,
    default=os.getenv("EEDOMUS_API_USER", "apiUser"),
    help="API User Eedomus (défaut/env: apiUser / EEDOMUS_API_USER)",
)
parser.add_argument(
    "-s",
    "--api-secret",
    type=str,
    default=os.getenv("EEDOMUS_API_SECRET", "apiPassword"),
    help="API Secret Eedomus (défaut/env: apiPassword / EEDOMUS_API_SECRET)",
)

args, _ = parser.parse_known_args()

API_USER = args.api_user
API_SECRET = args.api_secret
PORT = args.port

#  Chargement des données dans le répertoire du script

dump_file = get_script_file_path("eedomus_dump.json")
rules_file = get_script_file_path("thermostat_rules.json")

# 1. Chargement des données eedomus_dump.json
try:
    with open(dump_file, "r", encoding="utf-8") as f:
        dump = json.load(f)
        periph_list_data = dump.get("periph_list", [])
        value_list_data = dump.get("value_list", [])
        caract_list_data = dump.get("caract", [])
    print("Données chargées depuis 'eedomus_dump.json'.")
except FileNotFoundError:
    print("Fichier de données eedomus_dump.json doit etre présent.")
    sys.exit(1)

# Indexation par periph_id en conservant la structure exacte
caract_by_id = {
    str(dev["periph_id"]): dev
    for dev in caract_list_data
    if isinstance(dev, dict) and "periph_id" in dev
}

print(f"Simulateur prêt : {len(caract_by_id)} équipements indexés.")

# Chargement du fichier de règles thermostat
THERMOSTAT_RULES = []
if os.path.exists(rules_file):
    with open(rules_file, "r", encoding="utf-8") as f:
        THERMOSTAT_RULES = json.load(f)
    print(f"Règles thermostats chargées : {len(THERMOSTAT_RULES)} règle(s).")

def evaluate_thermostat_rules(changed_periph_id):
    """Évalue et bascule le chauffage si la consigne ou la température change."""
    for rule in THERMOSTAT_RULES:
        setpoint_id = str(rule["setpoint_id"])
        sensor_id = str(rule["sensor_id"])

        # Si le périphérique modifié impacte cette règle
        if str(changed_periph_id) in (setpoint_id, sensor_id):
            try:
                setpoint_val = float(
                    caract_by_id[setpoint_id].get("last_value", 0)
                )
                sensor_val = float(caract_by_id[sensor_id].get("last_value", 0))
                switch_id = str(rule["switch_id"])

                # Logique de déclenchement du chauffage
                if setpoint_val > sensor_val:
                    new_switch_val = str(rule.get("on_value", "100"))
                else:
                    new_switch_val = str(rule.get("off_value", "0"))

                # Application du nouvel état si changement
                current_switch_val = str(
                    caract_by_id[switch_id].get("last_value", "")
                )
                if current_switch_val != new_switch_val:
                    caract_by_id[switch_id]["last_value"] = new_switch_val
                    print(
                        f"[SIMU THERMOSTAT] '{rule['name']}' -> Consigne:"
                        f" {setpoint_val}°C | Mesuré: {sensor_val}°C => Commande"
                        f" {switch_id} passée à : {new_switch_val}"
                    )
            except (ValueError, KeyError) as e:
                print(
                    f"[SIMU THERMOSTAT ERROR] Échec évaluation règle"
                    f" {rule['name']}: {e}"
                )


def require_eedomus_auth(f):
    """Décorateur de contrôle d'accès API Eedomus."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.args.get("api_user")
        secret = request.args.get("api_secret")
        if user != API_USER or secret != API_SECRET:
            return jsonify({"success": 0, "error": "Authentification échouée"}), 401
        return f(*args, **kwargs)
    return decorated_function


def format_caract(dev, show_config):
    """
    Formate la réponse caract selon show_config :
    - '1' : renvoie l'objet complet avec configuration matérielle
    - '0' (ou absent) : renvoie les 7 champs de base Eedomus
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

    # 1. Validation de la connexion
    if action == "auth.test":
        return jsonify({"success": 1, "body": {"auth": 1}})

    # 2. Liste sommaire des périphériques
    if action == "periph.list":
        return jsonify({"success": 1, "body": periph_list_data})

    # 3. Liste des valeurs possibles
    if action == "periph.value_list":
        if periph_id == "all":
            return jsonify({"success": 1, "body": value_list_data})
        
        # Support d'un ID unique ou d'une liste séparée par des virgules
        requested_ids = set(pid.strip() for pid in periph_id.split(",") if pid.strip())
        filtered = [
            v for v in value_list_data
            if str(v.get("periph_id")) in requested_ids
        ]
        return jsonify({"success": 1, "body": filtered})

    # 4. Caractéristiques détaillées (avec/sans show_config)
    if action == "periph.caract":
        if not periph_id:
            return jsonify({"success": 0, "error": "Paramètre periph_id manquant"}), 400

        # Cas 1 : Demande globale "all"
        if periph_id == "all":
            data = [format_caract(d, show_config) for d in caract_list_data]
            return jsonify({"success": 1, "body": data})

        # Cas 2 : Liste d'IDs séparés par des virgules (ex: periph_id=123,456)
        if "," in periph_id:
            requested_ids = [pid.strip() for pid in periph_id.split(",") if pid.strip()]
            data = [
                format_caract(caract_by_id[pid], show_config)
                for pid in requested_ids
                if pid in caract_by_id
            ]
            return jsonify({"success": 1, "body": data})

        # Cas 3 : ID unique (ex: periph_id=123)
        if periph_id in caract_by_id:
            data = format_caract(caract_by_id[periph_id], show_config)
            return jsonify({"success": 1, "body": data})

        return jsonify({"success": 0, "error": f"Périphérique {periph_id} non trouvé"}), 404

    return jsonify({"success": 0, "error": f"Action '{action}' non reconnue"}), 404


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
            f" ({caract_by_id[periph_id].get('name')}) changé à : {value}"
        )

        # Évaluation des thermostats impactés par la commande HA
        evaluate_thermostat_rules(periph_id)

        return jsonify({"success": 1, "body": {"result": "OK"}})

    return jsonify({"success": 0, "error": "Échec de mise à jour"}), 400


@app.route("/simulate/change", methods=["POST"])
def simulate_change():
    """Endpoint local pour faire varier manuellement un capteur."""
    data = request.get_json()
    periph_id = str(data.get("periph_id"))
    new_value = str(data.get("value"))

    if periph_id in caract_by_id:
        caract_by_id[periph_id]["last_value"] = new_value
        print(f"[SIMULATION] -> Capteur {periph_id} ({caract_by_id[periph_id].get('name')}) varié à : {new_value}")

        # Évaluation des thermostats si on simule une variation de température ambiante
        evaluate_thermostat_rules(periph_id)

        return jsonify({"status": "updated", "periph_id": periph_id, "new_value": new_value})

    return jsonify({"error": "Device non trouvé"}), 404


if __name__ == "__main__":
    print(f"Démarrage du simulateur sur http://0.0.0.0:{PORT}")
    print(f"API User : {API_USER} | API Secret : {API_SECRET}")

    app.run(host="0.0.0.0", port=PORT)
