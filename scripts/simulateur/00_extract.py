import argparse
import json
import os

import requests

# CLI arguments / environment variables parsing
parser = argparse.ArgumentParser(description="Query the eedomus box")
parser.add_argument(
    "-i",
    "--ip",
    type=str,
    default=os.getenv("EEDOMUS_HOST", "192.128.0.10"),
    help="Eedomus box address (default/env: 192.128.0.10 / EEDOMUS_HOST)",
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
EEDOMUS_IP = args.ip

base_url = f"http://{EEDOMUS_IP}/api/get"
auth = f"api_user={API_USER}&api_secret={API_SECRET}"

print("0   Test connexion...")

res_test = requests.get(f"{base_url}?auth.test&{auth}").json()
if res_test.get("success") == "0":
    # Read the 'body' dict when present
    body = res_test.get("body", {})

    # Read 'error_code' inside 'body'
    error_code = body.get("error_code")

    # Exemple de test
    if error_code == "1":
        print("Authentication error detected!")
        exit(1)
    else:
        print("connexion OK")
else:
    print("Erreur connexion")
    exit(1)

print("1/3 Fetching periph.list...")
res_list = requests.get(f"{base_url}?action=periph.list&{auth}").json()

print("2/3 Fetching periph.value_list (all)...")
res_values = requests.get(
    f"{base_url}?action=periph.value_list&periph_id=all&{auth}"
).json()

print("3/3 Fetching periph.caract (with show_config=1)...")
res_caract = requests.get(
    f"{base_url}?action=periph.caract&periph_id=all&show_config=1&{auth}"
).json()

# Assemble the complete structure
full_dump = {
    "periph_list": res_list.get("body", []),
    "value_list": res_values.get("body", []),
    "caract": res_caract.get("body", []),
}


eedomus = EEDOMUS_IP.replace(".", "_")
fichier = f"eedomus_dump_box_{eedomus}.json"

with open(fichier, "w", encoding="utf-8") as f:
    json.dump(full_dump, f, indent=4, ensure_ascii=False)

print(f" Extraction succeeded! File '{fichier}' generated.")
