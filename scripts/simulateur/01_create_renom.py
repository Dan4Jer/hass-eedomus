#!/usr/bin/env python3

import csv
import json
import requests
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Extraction json Eedomus construction csv")
parser.add_argument(
    "-j",
    "--json",
    type=str,
    default=os.getenv("JSON_FILE", "eedomus_dump_box_xx.json"),
    help="JSON file name (default/env: eedomus_dump_box_xx.json / JSON_FILE)",
)
parser.add_argument(
    "-c",
    "--csv",
    type=str,
    default=os.getenv("CSV_FILE", "renom.csv"),
    help="CSV file name (default/env: renom.csv / JSON_FILE)",
)

args, _ = parser.parse_known_args()

INPUT = Path("eedomus_dump.json")
OUTPUT = Path("renom.csv")

INPUT = Path(args.json)
OUTPUT = Path(args.csv)

def main():
    if not INPUT.exists():
        raise SystemExit(f"ERROR: fichier introuvable : {INPUT}")

    if OUTPUT.exists():
        raise SystemExit(
            f"ERROR: {OUTPUT} already exists.\n"
            "Delete or rename it before generating a new CSV."
        )

    with INPUT.open("r", encoding="utf-8") as f:
        dump = json.load(f)

    peripherals = dump.get("periph_list", [])

    if not isinstance(peripherals, list):
        raise SystemExit("ERROR: periph_list n'est pas une liste.")

    rows = []

    for p in peripherals:
        rows.append({
            "periph_id": str(p.get("periph_id", "")),
            "name": p.get("name", ""),
            "parent_periph_id": str(p.get("parent_periph_id", "") or ""),
            "usage_id": str(p.get("usage_id", "") or ""),
            "new_periph_id": "",
            "new_name": "",
        })

    rows.sort(key=lambda x: int(x["periph_id"])
              if x["periph_id"].isdigit()
              else x["periph_id"])

    with OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "periph_id",
                "name",
                "parent_periph_id",
                "usage_id",
                "new_periph_id",
                "new_name",
            ],
            delimiter=",",
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} peripherals exported to {OUTPUT}")


if __name__ == "__main__":
    main()
