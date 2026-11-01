"""Unit tests: eedomus value type / unit in rules, description resolver.

Samples mirror real eedomus periphs: a decimal counter in Wh, a value list
with a -9999 error entry and a blank unit, and string periphs whose
last_value_text is empty while last_value holds the text.
"""

from types import SimpleNamespace

import pytest

from custom_components.eedomus.mapping_rules import (
    evaluate_advanced_rules,
    evaluate_conditions,
)
from custom_components.eedomus.sensor import EedomusSensor
from custom_components.eedomus.text_sensor import EedomusTextSensor
from custom_components.eedomus.value_resolver import (
    normalize_unit,
    resolve_display_value,
    unit_matches,
    value_type_matches,
)

pytestmark = pytest.mark.unit

FLOAT_WH = {
    "periph_id": "1",
    "name": "Conso",
    "usage_id": "35",
    "value_type": "float",
    "unit": "Wh",
    "last_value": "1234.5",
    "last_value_text": "1234.5",
}
LIST_PERIPH = {
    "periph_id": "2",
    "name": "Loi d eau",
    "usage_id": "115",
    "value_type": "list",
    "unit": " ",
    "last_value": "1",
    "last_value_text": "",
    "values": [
        {"value": "0", "description": "Arret"},
        {"value": "1", "description": "Courbe 1"},
        {"value": "-9999", "description": "Erreur"},
    ],
}
STRING_PERIPH = {
    "periph_id": "3",
    "name": "Ville station",
    "usage_id": "35",
    "value_type": "string",
    "unit": "",
    "last_value": "Lyon",
    "last_value_text": "",
}


def cond(periph, *conditions):
    return evaluate_conditions(list(conditions), periph, {}, periph["periph_id"], "r")


def test_value_type_labels():
    assert value_type_matches("float", "numeric")
    assert value_type_matches("float", ["int", "float"])
    assert value_type_matches("LIST", "list")
    assert value_type_matches("string", "text")
    assert not value_type_matches("string", "float")
    assert not value_type_matches(None, "float")


def test_blank_unit_is_empty():
    assert normalize_unit(" ") == ""
    assert unit_matches(" ", "")
    assert unit_matches("wh", "Wh")
    assert not unit_matches("Wh", "kWh")


def test_value_type_condition_in_rule():
    assert cond(FLOAT_WH, {"usage_id": "35"}, {"value_type": "float"})
    assert not cond(STRING_PERIPH, {"usage_id": "35"}, {"value_type": "float"})
    assert cond(STRING_PERIPH, {"usage_id": "35"}, {"value_type": "string"})


def test_unit_condition_in_rule():
    assert cond(FLOAT_WH, {"unit": "Wh"})
    assert not cond(FLOAT_WH, {"unit": "W"})


def test_same_usage_id_split_by_value_type():
    rules = {
        "numeric_35": {
            "conditions": [{"usage_id": "35"}, {"value_type": "float"}],
            "mapping": {"ha_entity": "sensor", "ha_subtype": "energy"},
        },
        "text_35": {
            "conditions": [{"usage_id": "35"}, {"value_type": "string"}],
            "mapping": {"ha_entity": "sensor", "ha_subtype": "text"},
        },
    }
    assert evaluate_advanced_rules(FLOAT_WH, {}, rules)["ha_subtype"] == "energy"
    assert evaluate_advanced_rules(STRING_PERIPH, {}, rules)["ha_subtype"] == "text"


def test_resolver_uses_description():
    assert resolve_display_value(LIST_PERIPH) == "Courbe 1"


def test_resolver_error_entry_is_none():
    assert resolve_display_value({**LIST_PERIPH, "last_value": "-9999"}) is None


def test_resolver_skips_empty_text_and_falls_back_to_raw():
    assert resolve_display_value(STRING_PERIPH) == "Lyon"
    assert resolve_display_value({**STRING_PERIPH, "last_value_text": "Paris"}) == (
        "Paris"
    )


def test_resolver_unmatched_raw_value_is_kept():
    periph = {**LIST_PERIPH, "last_value": "7"}
    assert resolve_display_value(periph) == "7"


def test_resolver_empty():
    assert resolve_display_value({"last_value": ""}) is None
    assert resolve_display_value({}) is None


def make(cls, periph, **attrs):
    entity = cls.__new__(cls)
    entity._periph_id = periph["periph_id"]
    entity.coordinator = SimpleNamespace(data={periph["periph_id"]: periph})
    for key, value in attrs.items():
        setattr(entity, key, value)
    return entity


def test_text_subtype_sensor_publishes_string():
    """Regression: a string periph mapped sensor/text used to be unknown."""
    sensor = make(EedomusSensor, STRING_PERIPH, _is_text=True)
    assert sensor.native_value == "Lyon"


def test_numeric_sensor_unchanged():
    sensor = make(EedomusSensor, FLOAT_WH, _is_text=False)
    assert sensor.native_value == 1234.5


def test_text_sensor_with_empty_last_value_text():
    sensor = make(EedomusTextSensor, STRING_PERIPH, _dynamic_value_mapping=False)
    assert sensor.native_value == "Lyon"


def test_text_sensor_dynamic_description():
    sensor = make(EedomusTextSensor, LIST_PERIPH, _dynamic_value_mapping=True)
    assert sensor.native_value == "Courbe 1"
