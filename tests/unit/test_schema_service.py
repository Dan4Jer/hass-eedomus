"""Unit tests for the Eedomus SchemaService schema documentation.

Covers the P.1.1 fix: generate_schema_documentation must return a
JSON-serializable payload (the get_schema websocket command serializes it
with json.dumps, which rejects vol.Optional/vol.Required marker keys).
"""

import json
from unittest.mock import MagicMock

import pytest

from custom_components.eedomus.schema_service import SchemaService

pytestmark = pytest.mark.unit


def make_service():
    """Build a SchemaService around the real YAML_MAPPING_SCHEMA."""
    return SchemaService(MagicMock())


class TestGenerateSchemaDocumentation:
    def test_documentation_is_json_serializable(self):
        """The payload must survive json.dumps (websocket transport)."""
        documentation = make_service().generate_schema_documentation()

        json.dumps(documentation)

    def test_section_keys_are_strings(self):
        """vol.Optional markers must be replaced by their string names."""
        documentation = make_service().generate_schema_documentation()

        assert all(isinstance(key, str) for key in documentation["sections"])
        assert "custom_devices" in documentation["sections"]
        assert "metadata" in documentation["sections"]

    def test_field_keys_are_strings(self):
        """vol.Required markers in item schemas must not leak as keys."""
        documentation = make_service().generate_schema_documentation()

        for section in documentation["sections"].values():
            assert all(isinstance(key, str) for key in section["fields"])

    def test_array_section_documents_item_fields(self):
        """A list section documents the fields of its item schema."""
        documentation = make_service().generate_schema_documentation()
        devices = documentation["sections"]["custom_devices"]

        assert devices["type"] == "array"
        assert devices["fields"]["eedomus_id"]["type"] == "string"
        assert devices["fields"]["eedomus_id"]["required"] is True
        assert devices["fields"]["type"]["type"] == "enum"

    def test_plain_dict_section_documents_fields(self):
        """A dict section keyed by vol markers documents its fields."""
        documentation = make_service().generate_schema_documentation()
        metadata = documentation["sections"]["metadata"]

        assert metadata["type"] == "object"
        assert metadata["fields"]["version"]["type"] == "string"
        assert metadata["fields"]["version"]["required"] is False

    def test_free_form_map_section_typed_as_map(self):
        """A {str: ...} section exposes no field names, only a type."""
        documentation = make_service().generate_schema_documentation()
        mappings = documentation["sections"]["custom_usage_id_mappings"]

        assert mappings["type"] == "map"
        assert mappings["fields"] == {}

    def test_field_documentation_types_composite_validators(self):
        """vol.In/vol.Any/nested dicts get readable types, not unknown."""
        documentation = make_service().generate_schema_documentation()
        devices = documentation["sections"]["custom_devices"]
        rules = documentation["sections"]["custom_rules"]

        assert devices["fields"]["attributes"]["type"] == "object"
        assert rules["fields"]["condition"]["type"] == "object"
        assert rules["fields"]["actions"]["type"] == "array"
