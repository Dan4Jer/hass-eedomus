"""Helpers to read eedomus values: value type, unit and display text."""

from __future__ import annotations

from typing import Any

NUMERIC_TYPES = {"float", "int", "integer", "number", "numeric", "decimal"}
TEXT_TYPES = {"string", "text"}
LIST_TYPES = {"list"}

# eedomus reports -9999 as the "error / no data" entry of a value list
ERROR_RAW_VALUE = "-9999"


def normalize_value_type(value_type: Any) -> str:
    """Return a lower-case value type, "" when unknown."""
    if value_type is None:
        return ""
    return str(value_type).strip().lower()


def normalize_unit(unit: Any) -> str:
    """Return the unit stripped; a blank unit (" ") counts as empty."""
    if unit is None:
        return ""
    return str(unit).strip()


def value_type_matches(device_value_type: Any, expected: Any) -> bool:
    """Check a rule's value_type condition.

    ``expected`` may be a single label or a list of labels. The labels
    "numeric"/"number"/"decimal"/"float"/"int" all select numeric
    periphs, "text"/"string" select free text, "list" selects value lists.
    """
    actual = normalize_value_type(device_value_type)
    wanted = expected if isinstance(expected, (list, tuple, set)) else [expected]
    for item in wanted:
        label = normalize_value_type(item)
        if label in NUMERIC_TYPES and actual in NUMERIC_TYPES:
            return True
        if label in TEXT_TYPES and actual in TEXT_TYPES:
            return True
        if label in LIST_TYPES and actual in LIST_TYPES:
            return True
        if label and label == actual:
            return True
    return False


def unit_matches(device_unit: Any, expected: Any) -> bool:
    """Check a rule's unit condition (case-insensitive, blank == "")."""
    actual = normalize_unit(device_unit).lower()
    wanted = expected if isinstance(expected, (list, tuple, set)) else [expected]
    return any(normalize_unit(item).lower() == actual for item in wanted)


def resolve_display_value(periph_data: dict) -> str | None:
    """Return the human-readable value of a periph.

    Order: description of the matching entry of ``values``, then
    ``last_value_text``, then the raw ``last_value``. Empty strings are
    skipped (eedomus may leave ``last_value_text`` empty while
    ``last_value`` holds the text). The -9999 error entry yields None.
    """
    raw = periph_data.get("last_value")
    raw_str = "" if raw is None else str(raw)

    if raw_str == ERROR_RAW_VALUE:
        return None

    for item in periph_data.get("values") or []:
        if str(item.get("value")) == raw_str:
            description = item.get("description")
            if description not in (None, ""):
                return str(description)
            break

    text = periph_data.get("last_value_text")
    if text not in (None, ""):
        return str(text)
    if raw_str == "":
        return None
    return raw_str
