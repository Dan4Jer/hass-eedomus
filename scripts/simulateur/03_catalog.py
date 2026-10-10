#!/usr/bin/env python3
"""Generate CATALOG.md, the catalog of missing hardware types (ticket 114).

The catalog is computed statically from the shipped simulator dump
(`eedomus_dump.json`) and the integration's mapping
(`custom_components/eedomus/config/device_mapping.yaml`): no box
access, no network. It lists:

- usage_ids handled by the mapping but absent from the dump,
- usage_ids present in the dump but unmapped,
- structural gaps: parent/child shapes, value_type variants,
  dangling platform mappings and the thermostat rules finding,

each with a documented priority rubric. The "how to add a type"
section points at the 00/01/02 extraction flow, which stays a human
step (real box + credentials + CAP-5 privacy pass).

The generation is deterministic: the same inputs always render a
byte-identical CATALOG.md. Regenerate with `python3 03_catalog.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

DEFAULT_DUMP_FILE = SCRIPT_DIR / "eedomus_dump.json"
DEFAULT_MAPPING_FILE = (
    REPO_ROOT / "custom_components" / "eedomus" / "config" / "device_mapping.yaml"
)
DEFAULT_OUTPUT_FILE = SCRIPT_DIR / "CATALOG.md"
DEFAULT_RULES_FILE = SCRIPT_DIR / "thermostat_rules.json"
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "eedomus"


class CatalogError(Exception):
    """A catalog input is invalid — fail loud, write nothing."""


# ---------------------------------------------------------------------
# Static priority rubric
#
# No coverage tool exists in this repository: the tiers are reasoned
# from the platform code paths a dump entry would reach (climate.py,
# light.py, cover.py, binary_sensor.py, switch.py, sensor.py,
# coordinator.py), not from measured coverage. Platform code with no
# unit coverage and the most unreachable branches ranks first.
# ---------------------------------------------------------------------

TIER_1_CRITICAL = {"15", "19", "20", "38", "48", "82"}
TIER_2_HIGH = {"14", "28", "29", "36", "42"}
TIER_3_NORMAL = {"50", "127", "999"}

TIER_LABELS = {
    1: "1 - critical",
    2: "2 - high",
    3: "3 - normal",
    4: "4 - low",
}

TIER_MEANINGS = {
    1: (
        "A whole platform (climate, cover) or a core structure (the "
        "RGBW parent/child light) has zero representation in the "
        "dump: the platform code paths are unreachable in the "
        "e2e_sim strate."
    ),
    2: (
        "A structural variant of a partially covered platform is "
        "missing (flood child, int/integer value types, "
        "shutter-group and power/energy sensors)."
    ),
    3: (
        "A single missing branch with limited reach (camera privacy "
        "switch, dangling button mapping, virtual scene trigger)."
    ),
    4: (
        "Eedomus box internal/app-data text sensors: the sensor/text "
        "path is already covered by present usage ids."
    ),
}

EXTRACTION_HINTS = {
    "14": "a virtual shutter-group select (eedomus centralization)",
    "15": "a virtual thermostat setpoint (eedomus thermostat module)",
    "19": "a fil pilote heater (usage 19)",
    "20": "a fil pilote heater (usage 20)",
    "28": "a real-time power meter peripheral",
    "29": "a cumulative energy meter peripheral",
    "36": "a flood/water leak detector (usage 36 child)",
    "38": "a heating device (usage 38, fil pilote)",
    "42": "a shutter centralization virtual device",
    "48": "a shutter/blind, ideally with a usage-48 slats child",
    "50": "a camera privacy switch",
    "82": (
        "a standalone usage-82 color-preset select — not part of the "
        "RGBW parent/child structure (light.py maps no 82 child)"
    ),
    "127": (
        "a camera snapshot trigger — blocked on the missing button.py "
        "platform (see findings); do not extract until it exists"
    ),
    "999": "a virtual scene-trigger device",
}
DEFAULT_EXTRACTION_HINT = "an eedomus box internal/app-data peripheral"

# Curated finding: kept as a constant because the mismatch is a human
# judgment about hardware semantics, not something the dump and the
# YAML can decide. Only carried while usage 109 is present and mapped.
VOLETS_FINDING = {
    "finding": "usage 109 (Volets) maps to sensor/text",
    "priority": 3,
    "detail": (
        "The dump labels usage_id 109 peripherals 'Volets' (shutters), "
        "but usage_id_mappings maps 109 to sensor/text ('Eedomus app "
        "data'). Deciding whether 109 should map to a shutter "
        "select/cover instead is out of scope for the catalog — "
        "flagged for a later decision."
    ),
}


# Short English glosses for the French dump labels of usage ids the
# mapping does not handle (same treatment as the Volets finding).
USAGE_GLOSSES = {
    "16": "alarm arming",
    "32": "pressure",
    "41": "rainfall",
    "119": "fog",
}


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------


def load_dump(dump_file: Path) -> dict[str, Any]:
    """Load and validate the simulator dump. Fail loud on bad input."""
    dump_file = Path(dump_file)
    if not dump_file.exists():
        raise CatalogError(f"File not found: {dump_file}")
    try:
        dump = json.loads(dump_file.read_text(encoding="utf-8"))
    except UnicodeDecodeError as err:
        raise CatalogError(f"{dump_file} is not valid UTF-8: {err}") from err
    except json.JSONDecodeError as err:
        raise CatalogError(f"Invalid JSON in {dump_file}: {err}") from err
    if not isinstance(dump, dict) or not isinstance(dump.get("periph_list"), list):
        raise CatalogError(
            f"{dump_file} must contain a JSON object with a " f"'periph_list' list."
        )
    return dump


def load_mapping(mapping_file: Path) -> dict[str, Any]:
    """Load device_mapping.yaml and validate usage_id_mappings."""
    mapping_file = Path(mapping_file)
    if not mapping_file.exists():
        raise CatalogError(f"File not found: {mapping_file}")
    try:
        mapping = yaml.safe_load(mapping_file.read_text(encoding="utf-8"))
    except UnicodeDecodeError as err:
        raise CatalogError(f"{mapping_file} is not valid UTF-8: {err}") from err
    except yaml.YAMLError as err:
        raise CatalogError(f"Invalid YAML in {mapping_file}: {err}") from err
    if not isinstance(mapping, dict):
        raise CatalogError(f"{mapping_file} must contain a YAML object.")
    mappings = mapping.get("usage_id_mappings")
    if not isinstance(mappings, dict) or not mappings:
        raise CatalogError(
            f"{mapping_file} has no 'usage_id_mappings' table — the "
            f"catalog cannot be computed. Nothing was written."
        )
    for key, value in mappings.items():
        if not isinstance(value, dict):
            raise CatalogError(
                f"usage_id_mappings entry '{key}' in {mapping_file} "
                f"must be a mapping of ha_entity/ha_subtype fields."
            )
    mapping["usage_id_mappings"] = {
        str(key): value for key, value in mappings.items()
    }
    return mapping


# ---------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------


def _usage_sort_key(usage_id: str) -> tuple[int, int, str]:
    if usage_id.isdigit():
        return (0, int(usage_id), "")
    return (1, 0, usage_id)


def _text(value: Any) -> str:
    """Dump field as text: null reads as '' (never literal 'None')."""
    return "" if value is None else str(value)


def priority_for(usage_id: str, entry: Any) -> tuple[int, str]:
    """Return the (tier, label) pair from the static rubric."""
    if usage_id in TIER_1_CRITICAL:
        tier = 1
    elif usage_id in TIER_2_HIGH:
        tier = 2
    elif usage_id in TIER_3_NORMAL:
        tier = 3
    elif (
        isinstance(entry, dict)
        and entry.get("ha_entity") == "sensor"
        and entry.get("ha_subtype") == "text"
    ):
        # Tier 4 keys off the mapping entry (a text sensor), not off
        # a magic numeric usage_id range.
        tier = 4
    else:
        raise CatalogError(
            f"usage_id {usage_id} is handled but absent from the dump "
            f"and has no priority in the rubric — extend the rubric "
            f"before regenerating the catalog."
        )
    return tier, TIER_LABELS[tier]


def analyze(
    dump: dict[str, Any],
    mapping: dict[str, Any],
    integration_dir: Path = INTEGRATION_DIR,
    rules_file: Path = DEFAULT_RULES_FILE,
) -> dict[str, Any]:
    """Compute every catalog section from the dump and the mapping."""
    periphs = dump["periph_list"]
    for periph in periphs:
        if not isinstance(periph, dict):
            raise CatalogError(
                "periph_list entries must be JSON objects, found "
                f"{type(periph).__name__}"
            )

    usage_counts: Counter = Counter()
    usage_names: dict[str, str] = {}
    value_types: Counter = Counter()
    for periph in periphs:
        usage_id = _text(periph.get("usage_id"))
        usage_counts[usage_id] += 1
        usage_names.setdefault(usage_id, _text(periph.get("usage_name")))
        value_type = periph.get("value_type")
        # Only null or the empty string counts as empty; 0/False are
        # value types of their own.
        if value_type is None or value_type == "":
            key = "(empty)"
        else:
            key = str(value_type)
        value_types[key] += 1

    handled = mapping["usage_id_mappings"]

    missing = []
    for usage_id in sorted(set(handled) - set(usage_counts), key=_usage_sort_key):
        entry = handled[usage_id]
        tier, label = priority_for(usage_id, entry)
        missing.append(
            {
                "usage_id": usage_id,
                "platform": str(entry.get("ha_entity", "")) or "-",
                "subtype": str(entry.get("ha_subtype", "")) or "-",
                "priority": tier,
                "priority_label": label,
                "what_to_extract": EXTRACTION_HINTS.get(
                    usage_id, DEFAULT_EXTRACTION_HINT
                ),
            }
        )
    missing.sort(key=lambda row: (row["priority"], _usage_sort_key(row["usage_id"])))

    unmapped = [
        {
            "usage_id": usage_id,
            "usage_name": usage_names.get(usage_id, "-"),
            "count": usage_counts[usage_id],
        }
        for usage_id in sorted(set(usage_counts) - set(handled), key=_usage_sort_key)
    ]

    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for periph in periphs:
        parent = _text(periph.get("parent_periph_id")).strip()
        if parent:
            children[parent].append(periph)

    periphs_by_id: dict[str, dict[str, Any]] = {}
    for periph in periphs:
        periph_id = _text(periph.get("periph_id"))
        if periph_id in periphs_by_id:
            raise CatalogError(f"duplicate periph_id '{periph_id}' in the dump")
        periphs_by_id[periph_id] = periph

    # Phantom parents: a parent_periph_id with no matching peripheral.
    # Their children are excluded from every parent/child count below.
    phantom_parents = sorted(
        parent_id for parent_id in children if parent_id not in periphs_by_id
    )
    children = {
        parent_id: kids
        for parent_id, kids in children.items()
        if parent_id in periphs_by_id
    }

    # Children usage counts, scoped by the parent's usage_id.
    child_usage_by_parent: dict[str, Counter] = defaultdict(Counter)
    for parent_id, kids in children.items():
        parent_usage = _text(periphs_by_id[parent_id].get("usage_id"))
        for child in kids:
            child_usage = _text(child.get("usage_id"))
            child_usage_by_parent[parent_usage][child_usage] += 1

    # Mapped ha_entity of a usage_id ('' when unmapped).
    def mapped_entity(usage_id: str) -> str:
        entry = handled.get(usage_id)
        return _text(entry.get("ha_entity")) if isinstance(entry, dict) else ""

    # switch.py inspects children of switch-mapped parents only.
    control_children = {usage_id: 0 for usage_id in ("1", "2", "4", "52")}
    for parent_id, kids in children.items():
        parent_usage = _text(periphs_by_id[parent_id].get("usage_id"))
        if mapped_entity(parent_usage) != "switch":
            continue
        for child in kids:
            child_usage = _text(child.get("usage_id"))
            if child_usage in control_children:
                control_children[child_usage] += 1
    control_status = (
        "covered"
        if all(count > 0 for count in control_children.values())
        else "partially covered"
    )

    # RGBW aggregate: light.py counts ALL children of the parent
    # (len(children) >= 4), not usage-1 children only.
    rgbw_child_counts = [
        len(kids)
        for parent_id, kids in children.items()
        if _text(periphs_by_id[parent_id].get("usage_id")) == "1"
    ]
    rgbw_max_children = max(rgbw_child_counts, default=0)

    motion_children = child_usage_by_parent.get("37", Counter())

    structural_gaps = [
        {
            "id": "rgbw-light",
            "gap": "RGBW aggregate light (parent/child color structure)",
            "code_path": "light.py:88-102",
            "priority": 1,
            "status": "unreachable",
            "detail": (
                f"light.py builds an RGBW light from a usage-1 parent "
                f"with at least 4 children of any usage "
                f"(len(children) >= 4); the dump's usage-1 parents "
                f"have at most {rgbw_max_children}."
            ),
        },
        {
            "id": "cover-slats",
            "gap": "Cover platform and slats child",
            "code_path": "cover.py:47,61",
            "priority": 1,
            "status": "unreachable",
            "detail": (
                "No peripheral with usage_id 48 exists in the dump: "
                "the cover platform and its slats-child branch (a "
                "usage-48 child of a cover parent) cannot be exercised."
            ),
        },
        {
            "id": "bsensor-children",
            "gap": "Binary sensor child mappings",
            "code_path": "binary_sensor.py:69-81",
            "priority": 2,
            "status": "partially covered",
            "detail": (
                f"binary_sensor.py maps children of motion parents by "
                f"usage id: 7 (temperature, "
                f"{motion_children.get('7', 0)} in the dump), 24 "
                f"(illuminance, {motion_children.get('24', 0)}) and 36 "
                f"(flood, {motion_children.get('36', 0)}); the flood "
                f"child branch is unreachable."
            ),
        },
        {
            "id": "switch-control-children",
            "gap": "Switch control-capable children",
            "code_path": "switch.py:78-84",
            "priority": None if control_status == "covered" else 2,
            "status": control_status,
            "detail": (
                "switch.py counts control-capable children (usage "
                "1/2/4/52) of switch-mapped parents only: "
                + ", ".join(
                    f"usage {usage_id}: {count}"
                    for usage_id, count in control_children.items()
                )
                + (
                    " — some control usages never appear as children "
                    "of a switch-mapped parent, so the branch is only "
                    "partially exercisable."
                    if control_status == "partially covered"
                    else " — the control-children branch is reachable."
                )
            ),
        },
        {
            "id": "value-type-int",
            "gap": "int/integer value_type variants",
            "code_path": "sensor.py:397, coordinator.py:1155",
            "priority": 2,
            "status": "unreachable",
            "detail": (
                "coordinator.py treats value_type in (float, int, "
                "integer) as numeric; the dump only carries float "
                "(plus list/string/empty) — the int/integer branch is "
                "never exercised."
            ),
        },
    ]

    # Dangling platform mappings: a ha_entity with no platform file.
    integration_dir = Path(integration_dir)
    dangling = []
    for usage_id in sorted(handled, key=_usage_sort_key):
        entry = handled[usage_id]
        ha_entity = str(entry.get("ha_entity", ""))
        if not ha_entity:
            continue
        if not (integration_dir / f"{ha_entity}.py").exists():
            dangling.append(
                {
                    "usage_id": usage_id,
                    "mapping": f"{ha_entity}/{entry.get('ha_subtype') or '-'}",
                    "platform_file": f"custom_components/eedomus/{ha_entity}.py",
                    "in_dump": usage_counts.get(usage_id, 0),
                }
            )

    findings: list[dict[str, Any]] = []

    # Thermostat rules: climate.py only creates entities whose mapped
    # ha_entity is 'climate'; flag every rule whose setpoint maps
    # elsewhere, is absent from the dump, or cannot be checked at all.
    rules_path = Path(rules_file)
    if not rules_path.exists():
        findings.append(
            {
                "finding": "thermostat rules file is missing",
                "priority": 1,
                "detail": (
                    f"{rules_path} does not exist — the shipped "
                    f"thermostat rules cannot be checked for climate "
                    f"coverage."
                ),
            }
        )
    else:
        try:
            rules = json.loads(rules_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
            raise CatalogError(f"Cannot read {rules_path}: {err}") from err
        if not isinstance(rules, list):
            raise CatalogError(f"{rules_path} must contain a JSON list of rules.")
        for rule in rules:
            if not isinstance(rule, dict):
                raise CatalogError(
                    f"{rules_path} contains a rule that is not a "
                    f"JSON object."
                )
            setpoint_id = _text(rule.get("setpoint_id"))
            periph = periphs_by_id.get(setpoint_id)
            if periph is None:
                findings.append(
                    {
                        "finding": (
                            f"thermostat rule setpoint '{setpoint_id}' "
                            f"is absent from the dump"
                        ),
                        "priority": 1,
                        "detail": (
                            f"{rules_path} references setpoint "
                            f"'{setpoint_id}' but no peripheral carries "
                            f"that id; the rule can never produce a "
                            f"climate entity."
                        ),
                    }
                )
                continue
            usage_id = _text(periph.get("usage_id"))
            entry = handled.get(usage_id)
            ha_entity = _text(entry.get("ha_entity")) if entry else "(unmapped)"
            if ha_entity != "climate":
                findings.append(
                    {
                        "finding": (
                            f"thermostat rule setpoint '{setpoint_id}' "
                            f"never becomes a climate entity"
                        ),
                        "priority": 1,
                        "detail": (
                            f"climate.py only creates entities whose "
                            f"ha_entity is 'climate'; the rule's setpoint "
                            f"has usage {usage_id} "
                            f"('{_text(periph.get('usage_name'))}') mapped "
                            f"to {ha_entity}, so the shipped "
                            f"thermostat_rules.json produces no climate "
                            f"entity."
                        ),
                    }
                )

    for parent_id in phantom_parents:
        findings.append(
            {
                "finding": (
                    f"peripheral '{parent_id}' is referenced as a "
                    f"parent but absent from the dump"
                ),
                "priority": 2,
                "detail": (
                    "parent_periph_id references a peripheral that does "
                    "not exist; its children are excluded from the "
                    "parent/child counts and the child-usage analysis."
                ),
            }
        )

    for entry in dangling:
        findings.append(
            {
                "finding": (
                    f"usage {entry['usage_id']} maps to "
                    f"{entry['mapping']} but the platform file does "
                    f"not exist"
                ),
                "priority": 3,
                "detail": (
                    f"{entry['platform_file']} is missing from the "
                    f"integration; the mapping is dangling. Creating "
                    f"the platform is out of scope for the catalog — "
                    f"flagged for a later decision."
                ),
            }
        )

    if "109" in usage_counts and "109" in handled:
        findings.append(dict(VOLETS_FINDING))

    findings.sort(key=lambda row: (row["priority"], row["finding"]))

    return {
        "periph_count": len(periphs),
        "usage_count": len(usage_counts),
        "parents_with_children": len(children),
        "periphs_with_parent": sum(len(kids) for kids in children.values()),
        "value_types": value_types,
        "handled": handled,
        "missing": missing,
        "unmapped": unmapped,
        "structural_gaps": structural_gaps,
        "dangling": dangling,
        "findings": findings,
    }


# ---------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [_row(headers), _row(["---"] * len(headers))]
    lines.extend(_row(row) for row in rows)
    return lines


def _value_type_summary(value_types: Counter) -> str:
    return ", ".join(
        f"{value_type}: {count}" for value_type, count in sorted(value_types.items())
    )


def _glossed_label(usage_id: str, usage_name: str) -> str:
    """Dump label plus a short English gloss when one is curated."""
    gloss = USAGE_GLOSSES.get(usage_id)
    return f"{usage_name} ({gloss})" if gloss else usage_name


def render(analysis: dict[str, Any]) -> str:
    """Render the CATALOG.md content — deterministic, no timestamps."""
    lines: list[str] = []
    add = lines.append
    extend = lines.extend

    add("# Simulator dump catalog: missing hardware types (ticket 114)")
    add("")
    extend(
        [
            "> Generated by `03_catalog.py` from `eedomus_dump.json` and",
            "> `custom_components/eedomus/config/device_mapping.yaml`.",
            "> Deterministic output — do not edit by hand; regenerate",
            "> with `python3 03_catalog.py`.",
            "",
        ]
    )

    add("## Dataset summary")
    add("")
    extend(
        _table(
            ["Metric", "Value"],
            [
                ["Peripherals in the dump", str(analysis["periph_count"])],
                ["Distinct usage_ids", str(analysis["usage_count"])],
                [
                    "Parents with children",
                    str(analysis["parents_with_children"]),
                ],
                [
                    "Peripherals with a parent",
                    str(analysis["periphs_with_parent"]),
                ],
                [
                    "value_type distribution",
                    _value_type_summary(analysis["value_types"]),
                ],
            ],
        )
    )
    add("")

    add("## 1. Handled but absent from the dump")
    add("")
    extend(
        [
            "These usage_ids have a `usage_id_mappings` entry in",
            "`device_mapping.yaml` but no peripheral in the shipped dump",
            "carries them: the matching platform code paths are",
            "unreachable in the `e2e_sim` strate. Sorted by priority.",
            "",
        ]
    )
    extend(
        _table(
            ["usage_id", "Platform", "Subtype", "Priority", "What to extract"],
            [
                [
                    row["usage_id"],
                    row["platform"],
                    row["subtype"],
                    row["priority_label"],
                    row["what_to_extract"],
                ]
                for row in analysis["missing"]
            ],
        )
    )
    add("")

    add("## 2. Present but unmapped")
    add("")
    extend(
        [
            "These usage_ids exist in the dump but have no",
            "`usage_id_mappings` entry: the integration ignores these",
            "peripherals. Adding a mapping (or confirming they should",
            "stay unmapped) is a later decision — the catalog only",
            "reports them.",
            "",
        ]
    )
    extend(
        _table(
            ["usage_id", "Usage name (dump label)", "Peripherals"],
            [
                [
                    row["usage_id"],
                    _glossed_label(row["usage_id"], row["usage_name"]),
                    str(row["count"]),
                ]
                for row in analysis["unmapped"]
            ],
        )
    )
    add("")

    add("## 3. Structural gaps")
    add("")
    add("### 3.1 Parent/child shapes")
    add("")
    extend(
        _table(
            ["Gap", "Code path", "Priority", "Status", "Detail"],
            [
                [
                    gap["gap"],
                    gap["code_path"],
                    TIER_LABELS[gap["priority"]] if gap["priority"] else "-",
                    gap["status"],
                    gap["detail"],
                ]
                for gap in analysis["structural_gaps"]
            ],
        )
    )
    add("")
    add("### 3.2 Dangling platform mappings")
    add("")
    if analysis["dangling"]:
        extend(
            _table(
                ["usage_id", "Mapping", "Platform file", "In dump"],
                [
                    [
                        entry["usage_id"],
                        entry["mapping"],
                        entry["platform_file"] + " (missing)",
                        str(entry["in_dump"]),
                    ]
                    for entry in analysis["dangling"]
                ],
            )
        )
    else:
        add("None: every mapped ha_entity has a platform file.")
    add("")

    add("## 4. Priority rubric")
    add("")
    extend(
        [
            "No coverage tool exists in this repository: the tiers",
            "below are **static reasoning** over the platform code",
            "paths a dump entry would reach, not measured coverage.",
            "Platform code with no unit coverage and the most",
            "unreachable branches ranks first.",
            "",
        ]
    )
    tier_ids: dict[int, list[str]] = {}
    for row in analysis["missing"]:
        tier_ids.setdefault(row["priority"], []).append(row["usage_id"])
    for gap in analysis["structural_gaps"]:
        if gap["priority"] is not None:
            tier_ids.setdefault(gap["priority"], []).append(gap["id"])
    extend(
        _table(
            ["Tier", "Meaning", "Ids concerned"],
            [
                [
                    TIER_LABELS[tier],
                    TIER_MEANINGS[tier],
                    ", ".join(tier_ids.get(tier, ["-"])),
                ]
                for tier in sorted(TIER_LABELS)
            ],
        )
    )
    add("")

    add("## 5. How to add a missing type")
    add("")
    extend(
        [
            "Adding a missing type is a **human step**: it needs a real",
            "eedomus box, its credentials and a privacy review. The",
            "catalog only says what to extract. The flow is documented",
            "in this directory's README (sections 8 to 15):",
            "",
            "1. **Extract** from a real box with `00_extract.py` (env",
            "   `EEDOMUS_HOST`, `EEDOMUS_API_USER`,",
            "   `EEDOMUS_API_SECRET`) — produces",
            "   `eedomus_dump_box_<address>.json`.",
            "2. **Prepare renaming** with `01_create_renom.py` —",
            "   produces `renom.csv`.",
            "3. **Edit the CSV**: pick the peripherals that fill the",
            "   catalog gaps, assign neutral new ids and names.",
            "4. **Apply** with `02_apply_renom.py` — produces `new_*`",
            "   files, never merges into the shipped files.",
            "5. **Privacy pass (CAP-5, README section 13)**: strip GPS",
            "   coordinates, URLs, OAuth tokens, `VAR1`/`VAR2`/`VAR3`,",
            "   external identifiers, phone numbers, network addresses,",
            "   person names and revealing room names. Renaming alone",
            "   is not a complete anonymization.",
            "6. **Extend** `eedomus_dump.json` (and",
            "   `thermostat_rules.json` when relevant) manually; keep",
            "   `periph_list`, `caract` and `value_list` consistent",
            "   (README section 12).",
            "7. **Regenerate the catalog**: `python3 03_catalog.py` —",
            "   the rows for the newly added types disappear and this",
            "   file stays the single source of truth.",
            "",
        ]
    )

    add("## 6. Findings")
    add("")
    extend(
        [
            "Findings computed from the dump and the mapping, plus the",
            "curated Volets finding. Fixing them is out of scope: the",
            "catalog records them for later decisions.",
            "",
        ]
    )
    extend(
        _table(
            ["Finding", "Priority", "Detail"],
            [
                [
                    finding["finding"],
                    TIER_LABELS[finding["priority"]],
                    finding["detail"],
                ]
                for finding in analysis["findings"]
            ],
        )
    )
    add("")

    return "\n".join(lines)


def build(dump_file: Path, mapping_file: Path) -> str:
    """Load the inputs and return the rendered catalog content."""
    dump = load_dump(dump_file)
    mapping = load_mapping(mapping_file)
    return render(analyze(dump, mapping))


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "generate CATALOG.md, the catalog of missing hardware "
            "types in the simulator dump"
        )
    )
    parser.add_argument(
        "-d",
        "--dump-file",
        type=str,
        default=os.getenv("DUMP_JSON_FILE", str(DEFAULT_DUMP_FILE)),
        help="simulator dump file (default/env: eedomus_dump.json /" " DUMP_JSON_FILE)",
    )
    parser.add_argument(
        "-m",
        "--mapping-file",
        type=str,
        default=os.getenv("MAPPING_FILE", str(DEFAULT_MAPPING_FILE)),
        help="device_mapping.yaml file (default/env:"
        " custom_components/eedomus/config/device_mapping.yaml /"
        " MAPPING_FILE)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=os.getenv("CATALOG_FILE", str(DEFAULT_OUTPUT_FILE)),
        help="output file, or '-' for stdout (default/env:"
        " CATALOG.md / CATALOG_FILE)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the existing output instead of writing;" " exit 1 on drift",
    )
    args = parser.parse_args(argv)

    try:
        content = build(Path(args.dump_file), Path(args.mapping_file))
    except CatalogError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    if args.check:
        if args.output == "-":
            print("ERROR: --check needs an output file, not '-'", file=sys.stderr)
            return 1
        output_path = Path(args.output)
        try:
            existing = (
                output_path.read_text(encoding="utf-8")
                if output_path.exists()
                else None
            )
        except (OSError, UnicodeDecodeError) as err:
            print(f"ERROR: cannot read {args.output}: {err}", file=sys.stderr)
            return 1
        if existing is None:
            print(
                f"ERROR: {args.output} does not exist — not generated; "
                f"run 03_catalog.py without --check first",
                file=sys.stderr,
            )
            return 1
        if existing != content:
            print(
                f"ERROR: {args.output} is out of date — regenerate it "
                f"with 03_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} is up to date.")
        return 0

    if args.output == "-":
        sys.stdout.write(content)
    else:
        try:
            Path(args.output).write_text(content, encoding="utf-8")
        except OSError as err:
            print(f"ERROR: cannot write {args.output}: {err}", file=sys.stderr)
            return 1
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
