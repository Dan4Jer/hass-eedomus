#!/usr/bin/env python3

import csv
import json
import sys
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="generation nouveau dump anonymiser")

parser.add_argument(
    "-d",
    "--dump-file",
    type=str,
    default=os.getenv("DUMP_JSON_FILE", "eedomus_dump_box_xx.json"),
    help="Nom fichier JSON (défaut/env: eedomus_dump_box_xx.json / DUMP_JSON_FILE)",
)
parser.add_argument(
    "-c",
    "--csv",
    type=str,
    default=os.getenv("CSV_FILE", "renom.csv"),
    help="Nom fichier CSV (défaut/env: renom.csv / JSON_FILE)",
)
parser.add_argument(
    "-t",
    "--thermostat",
    type=str,
    default=os.getenv("THERMOSTAT_FILE", "thermostat_rules.json"),
    help="Nom fichier Regles de Thermostat (défaut/env: thermostat_rules.json / THERMOSTAT_FILE)",
)

parser.add_argument(
    "-nd",
    "--news-dump-file",
    type=str,
    help="Nouveau Nom fichier JSON (défaut: new_<dump_file>)",
)
parser.add_argument(
    "-nt",
    "--new-thermostat",
    type=str,
    help="Nouveau Nom fichier Regles de Thermostat (défaut: new_<thermostat>)",
)

args = parser.parse_args()

if args.news_dump_file is None:
    directory, filename = os.path.split(args.dump_file)
    args.news_dump_file = os.path.join(directory, f"new_{filename}")

if args.new_thermostat is None:
    directory, filename = os.path.split(args.thermostat)
    args.new_thermostat = os.path.join(directory, f"new_{filename}")

DUMP_FILE = Path(args.dump_file)
RENOM_FILE = Path(args.csv)
THERMOSTAT_FILE = Path(args.thermostat)

NEW_DUMP_FILE = Path(args.news_dump_file)
NEW_THERMOSTAT_FILE = Path(args.new_thermostat)


CSV_COLUMNS = {
    "periph_id",
    "name",
    "parent_periph_id",
    "usage_id",
    "new_periph_id",
    "new_name",
}


# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------

def fail(message):
    print()
    print("ERREUR :")
    print(message)
    print()
    sys.exit(1)


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


# ----------------------------------------------------------------------
# Chargement du dump
# ----------------------------------------------------------------------

def load_dump():
    if not DUMP_FILE.exists():
        fail(f"Fichier introuvable : {DUMP_FILE}")

    with DUMP_FILE.open("r", encoding="utf-8") as f:
        dump = json.load(f)

    if not isinstance(dump, dict):
        fail("eedomus_dump.json doit contenir un objet JSON.")

    if "periph_list" not in dump:
        fail("eedomus_dump.json ne contient pas 'periph_list'.")

    return dump


# ----------------------------------------------------------------------
# Chargement du CSV
# ----------------------------------------------------------------------

def load_csv():
    if not RENOM_FILE.exists():
        fail(f"Fichier introuvable : {RENOM_FILE}")

    # On accepte UTF-8, UTF-8 BOM et CP1252.
    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]

    last_error = None

    for encoding in encodings:
        try:
            with RENOM_FILE.open(
                "r",
                encoding=encoding,
                newline=""
            ) as f:

                sample = f.read(4096)
                f.seek(0)

                # Le CSV est normalement séparé par des virgules.
                delimiter = ","

                if sample.count(";") > sample.count(","):
                    delimiter = ";"

                reader = csv.DictReader(
                    f,
                    delimiter=delimiter
                )

                if reader.fieldnames is None:
                    fail("renom.csv ne contient pas d'en-tête.")

                # Support d'un éventuel ancien nom "_new_name".
                fieldnames = set(reader.fieldnames)

                if "_new_name" in fieldnames and "new_name" not in fieldnames:
                    for row in reader:
                        row["new_name"] = row.pop("_new_name")
                        yield row

                    return

                missing = CSV_COLUMNS - fieldnames

                if missing:
                    fail(
                        "Colonnes manquantes dans renom.csv : "
                        + ", ".join(sorted(missing))
                    )

                for row in reader:
                    yield row

                return

        except UnicodeDecodeError as e:
            last_error = e

    fail(f"Impossible de lire {RENOM_FILE}: {last_error}")


# ----------------------------------------------------------------------
# Validation du CSV
# ----------------------------------------------------------------------

def validate_mapping(dump, csv_rows):

    dump_devices = {
        clean(p.get("periph_id")): p
        for p in dump["periph_list"]
    }

    if "" in dump_devices:
        fail("Un périphérique du dump possède un periph_id vide.")

    csv_map = {}

    errors = []

    for line_number, row in enumerate(csv_rows, start=2):

        old_id = clean(row.get("periph_id"))
        old_name = clean(row.get("name"))
        old_parent = clean(row.get("parent_periph_id"))
        new_id = clean(row.get("new_periph_id"))
        new_name = clean(row.get("new_name"))

        if not old_id:
            errors.append(
                f"Ligne {line_number}: periph_id vide"
            )
            continue

        if old_id in csv_map:
            errors.append(
                f"Ligne {line_number}: periph_id {old_id} en doublon"
            )
            continue

        if old_id not in dump_devices:
            errors.append(
                f"Ligne {line_number}: periph_id {old_id} "
                f"absent de eedomus_dump.json"
            )
            continue

        # --------------------------------------------------------------
        # Règles new_periph_id / new_name
        # --------------------------------------------------------------

        if not new_id:
            errors.append(
                f"Ligne {line_number}: "
                f"new_periph_id est vide pour {old_id}"
            )
            continue

        if new_id.lower() == "non":

            if new_name:
                errors.append(
                    f"Ligne {line_number}: {old_id}: "
                    f"new_periph_id=non mais new_name est renseigné"
                )

        else:

            if not new_name:
                errors.append(
                    f"Ligne {line_number}: {old_id}: "
                    f"new_periph_id est renseigné mais new_name est vide"
                )

        csv_map[old_id] = {
            "new_periph_id": new_id,
            "new_name": new_name,
            "parent_periph_id": old_parent,
            "name": old_name,
        }

    # ------------------------------------------------------------------
    # Le CSV doit contenir TOUS les périphériques du dump
    # ------------------------------------------------------------------

    dump_ids = set(dump_devices)
    csv_ids = set(csv_map)

    missing = dump_ids - csv_ids
    extra = csv_ids - dump_ids

    if missing:
        errors.append(
            "Périphériques présents dans le dump mais absents du CSV : "
            + ", ".join(sorted(missing))
        )

    if extra:
        errors.append(
            "Périphériques présents dans le CSV mais absents du dump : "
            + ", ".join(sorted(extra))
        )

    # ------------------------------------------------------------------
    # Vérification des nouveaux IDs
    # ------------------------------------------------------------------

    new_ids = {}

    for old_id, mapping in csv_map.items():

        new_id = mapping["new_periph_id"]

        if new_id.lower() == "non":
            continue

        if new_id in new_ids:
            errors.append(
                f"Nouvel periph_id {new_id} utilisé par "
                f"{new_ids[new_id]} et {old_id}"
            )
        else:
            new_ids[new_id] = old_id

    # ------------------------------------------------------------------
    # Vérification des parents
    # ------------------------------------------------------------------

    for old_id, mapping in csv_map.items():

        new_id = mapping["new_periph_id"]

        # Le périphérique lui-même est supprimé.
        if new_id.lower() == "non":
            continue

        parent_id = mapping["parent_periph_id"]

        if not parent_id:
            continue

        if parent_id not in csv_map:
            errors.append(
                f"{old_id}: parent {parent_id} absent du CSV"
            )
            continue

        parent_new_id = csv_map[parent_id]["new_periph_id"]

        if parent_new_id.lower() == "non":
            errors.append(
                f"{old_id}: le parent {parent_id} "
                f"est supprimé (new_periph_id=non)"
            )

    if errors:
        print()
        print("=" * 70)
        print("VALIDATION DU CSV : ECHEC")
        print("=" * 70)

        for error in errors:
            print(f"- {error}")

        print()
        print(
            "Aucun fichier new_* n'a été généré."
        )

        sys.exit(1)

    return csv_map


# ----------------------------------------------------------------------
# Remapping d'un ID
# ----------------------------------------------------------------------

def remap_id(old_id, mapping, context):

    old_id = clean(old_id)

    if not old_id:
        return old_id

    if old_id not in mapping:
        fail(
            f"{context}: periph_id {old_id} "
            f"absent de la table de migration."
        )

    new_id = mapping[old_id]["new_periph_id"]

    if new_id.lower() == "non":
        fail(
            f"{context}: référence vers {old_id}, "
            f"mais ce périphérique est supprimé."
        )

    return new_id


# ----------------------------------------------------------------------
# Transformation d'un périphérique
# ----------------------------------------------------------------------

def transform_device(device, mapping):

    old_id = clean(device.get("periph_id"))
    m = mapping[old_id]

    new_id = m["new_periph_id"]

    # Périphérique supprimé
    if new_id.lower() == "non":
        return None

    result = dict(device)

    # Nouveau ID
    result["periph_id"] = new_id

    # Nouveau nom
    result["name"] = m["new_name"]

    # Parent
    old_parent = clean(device.get("parent_periph_id"))

    if old_parent:

        parent_new_id = remap_id(
            old_parent,
            mapping,
            f"Périphérique {old_id}"
        )

        result["parent_periph_id"] = parent_new_id

    else:
        result["parent_periph_id"] = ""

    return result


# ----------------------------------------------------------------------
# Transformation du dump complet
# ----------------------------------------------------------------------

def transform_dump(dump, mapping):

    result = {}

    # On commence par recopier les autres sections.
    for key, value in dump.items():
        if key not in ("periph_list", "caract", "value_list"):
            result[key] = value

    # ------------------------------------------------------------------
    # periph_list
    # ------------------------------------------------------------------

    result["periph_list"] = []

    for device in dump.get("periph_list", []):

        new_device = transform_device(
            device,
            mapping
        )

        if new_device is not None:
            result["periph_list"].append(new_device)

    # ------------------------------------------------------------------
    # caract
    # ------------------------------------------------------------------

    result["caract"] = []

    for device in dump.get("caract", []):

        old_id = clean(device.get("periph_id"))

        if old_id not in mapping:
            fail(
                f"caract: periph_id {old_id} absent du CSV."
            )

        m = mapping[old_id]

        if m["new_periph_id"].lower() == "non":
            continue

        new_device = dict(device)

        new_device["periph_id"] = m["new_periph_id"]
        new_device["name"] = m["new_name"]

        old_parent = clean(
            device.get("parent_periph_id")
        )

        if old_parent:

            new_device["parent_periph_id"] = remap_id(
                old_parent,
                mapping,
                f"caract {old_id}"
            )

        result["caract"].append(new_device)

    # ------------------------------------------------------------------
    # value_list
    # ------------------------------------------------------------------
    #
    # On ne remappe QUE les champs connus comme contenant
    # un periph_id.
    #
    # Cela évite de remplacer par erreur une valeur numérique
    # qui serait simplement égale à un ancien periph_id.
    # ------------------------------------------------------------------

    result["value_list"] = []

    for value in dump.get("value_list", []):

        item = dict(value)

        if "periph_id" in item:

            old_id = clean(item["periph_id"])

            if old_id not in mapping:
                fail(
                    f"value_list: periph_id {old_id} absent du CSV."
                )

            new_id = mapping[old_id]["new_periph_id"]

            if new_id.lower() == "non":
                continue

            item["periph_id"] = new_id

        result["value_list"].append(item)

    return result


# ----------------------------------------------------------------------
# Création de simple_device_data
# ----------------------------------------------------------------------

def create_simple_device_data(dump):

    result = []

    # On utilise periph_list, qui contient les informations générales.
    for p in dump["periph_list"]:

        item = {
            "periph_id": p.get("periph_id", ""),
            "name": p.get("name", ""),
            "last_value": p.get("last_value", ""),
            "last_value_text": p.get("last_value_text", ""),
            "unit": p.get("unit", ""),
            "battery": p.get("battery", ""),
            "last_value_change": p.get(
                "last_value_change",
                ""
            ),
        }

        result.append(item)

    return result


# ----------------------------------------------------------------------
# Transformation thermostat_rules.json
# ----------------------------------------------------------------------

def transform_thermostat_rules(mapping):

    if not THERMOSTAT_FILE.exists():
        fail(
            f"Fichier introuvable : {THERMOSTAT_FILE}"
        )

    with THERMOSTAT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        rules = json.load(f)

    if not isinstance(rules, list):
        fail(
            "thermostat_rules.json doit contenir une liste."
        )

    result = []

    fields = [
        "setpoint_id",
        "sensor_id",
        "switch_id",
    ]

    for index, rule in enumerate(rules, start=1):

        new_rule = dict(rule)

        for field in fields:

            if field not in rule:
                continue

            old_id = clean(rule[field])

            if not old_id:
                continue

            new_rule[field] = remap_id(
                old_id,
                mapping,
                f"thermostat_rules.json règle {index}, {field}"
            )

        result.append(new_rule)

    return result


# ----------------------------------------------------------------------
# Ecriture JSON
# ----------------------------------------------------------------------

def write_json(path, data):

    with path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

        f.write("\n")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():

    print("=" * 70)
    print("MIGRATION EEDOMUS")
    print("=" * 70)

    dump = load_dump()

    csv_rows = list(load_csv())

    print(
        f"Périphériques dans le dump : "
        f"{len(dump['periph_list'])}"
    )

    print(
        f"Lignes dans renom.csv      : "
        f"{len(csv_rows)}"
    )

    # ------------------------------------------------------------------
    # VALIDATION COMPLETE
    # ------------------------------------------------------------------

    mapping = validate_mapping(
        dump,
        csv_rows
    )

    print()
    print("Validation du CSV : OK")

    # ------------------------------------------------------------------
    # TRANSFORMATION
    # ------------------------------------------------------------------

    new_dump = transform_dump(
        dump,
        mapping
    )

    new_thermostat = transform_thermostat_rules(
        mapping
    )

    # ------------------------------------------------------------------
    # ECRITURE
    # ------------------------------------------------------------------

    write_json(
        NEW_DUMP_FILE,
        new_dump
    )

    write_json(
        NEW_THERMOSTAT_FILE,
        new_thermostat
    )

    # ------------------------------------------------------------------
    # Résumé
    # ------------------------------------------------------------------

    kept = sum(
        1
        for m in mapping.values()
        if m["new_periph_id"].lower() != "non"
    )

    removed = len(mapping) - kept

    print()
    print("=" * 70)
    print("MIGRATION TERMINEE")
    print("=" * 70)
    print()
    print(f"Périphériques conservés : {kept}")
    print(f"Périphériques supprimés : {removed}")
    print()
    print(f"  {NEW_DUMP_FILE}")
    print(f"  {NEW_THERMOSTAT_FILE}")
    print()


if __name__ == "__main__":
    main()
