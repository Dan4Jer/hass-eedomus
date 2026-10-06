from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
import yaml

from custom_components.eedomus.storage_mapping import (
    async_load_mapping,
    async_save_custom_mapping,
)


@pytest.mark.asyncio
async def test_async_load_mapping_nominal(hass, tmp_path):
    """Test le chargement nominal avec de vrais fichiers YAML temporaires pour le custom."""
    custom_file = tmp_path / "custom_mapping.yaml"
    custom_file.write_text("devices:\n  switch:\n    name: 'Custom Switch'\n")

    with patch(
        "custom_components.eedomus.device_mapping.merge_yaml_mappings",
        return_value={"devices": {"light": {}, "switch": {}}},
    ) as mock_merge, patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA", side_effect=lambda x: x
    ) as mock_schema:
        result = await async_load_mapping(hass, str(tmp_path))

        assert result is not None
        assert mock_merge.called
        assert mock_schema.called


@pytest.mark.asyncio
async def test_async_load_mapping_missing_custom(hass, tmp_path):
    """Vérifie le comportement lorsque le fichier custom_mapping.yaml est absent (FileNotFoundError géré)."""
    with patch(
        "custom_components.eedomus.device_mapping.merge_yaml_mappings",
        return_value={"devices": {"light": {}}},
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA", side_effect=lambda x: x
    ):
        result = await async_load_mapping(hass, str(tmp_path))
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_load_mapping_default_yaml_error(hass, tmp_path):
    """Vérifie qu'une erreur YAML sur le fichier par défaut lève bien l'exception."""
    with patch(
        "yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML syntax")
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA", side_effect=lambda x: x
    ):
        with pytest.raises(yaml.YAMLError):
            await async_load_mapping(hass, str(tmp_path))


@pytest.mark.asyncio
async def test_async_load_mapping_sophisticated_merge_fallback(hass, tmp_path):
    """Vérifie le repli (fallback) vers un merge simple si la fusion sophistiquée échoue."""
    custom_file = tmp_path / "custom_mapping.yaml"
    custom_file.write_text("custom_key: custom_value\n")

    with patch(
        "custom_components.eedomus.device_mapping.merge_yaml_mappings",
        side_effect=Exception("Merge crashed"),
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA", side_effect=lambda x: x
    ) as mock_schema:
        result = await async_load_mapping(hass, str(tmp_path))
        assert result is not None
        assert isinstance(result, dict)
        assert "advanced_rules" in result
        assert mock_schema.called


@pytest.mark.asyncio
async def test_async_load_mapping_validation_failure(hass, tmp_path):
    """Vérifie qu'une exception vol.Invalid lève une erreur si le schéma de validation rejette les données."""

    def failing_schema(_):
        raise vol.Invalid("Schema validation error")

    with patch(
        "custom_components.eedomus.device_mapping.merge_yaml_mappings",
        return_value={"invalid_key": "data"},
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA",
        side_effect=failing_schema,
    ):
        with pytest.raises(vol.Invalid):
            await async_load_mapping(hass, str(tmp_path))


@pytest.mark.asyncio
async def test_async_save_custom_mapping_success(hass, tmp_path):
    """Vérifie la sauvegarde correcte d'un mapping personnalisé dans un vrai fichier temporaire."""
    mapping_data = {"custom_device": {"name": "Test Device"}}

    success = await async_save_custom_mapping(hass, str(tmp_path), mapping_data)

    assert success is True
    custom_file = tmp_path / "custom_mapping.yaml"
    assert custom_file.exists()

    content = yaml.safe_load(custom_file.read_text())
    assert content == mapping_data


@pytest.mark.asyncio
async def test_async_save_custom_mapping_failure(hass):
    """Vérifie que la fonction gère proprement les exceptions lors de la sauvegarde et renvoie False."""
    mapping_data = {"custom_device": {"name": "Test Device"}}

    with patch("os.makedirs", side_effect=PermissionError("Access denied")):
        success = await async_save_custom_mapping(
            hass, "/root/forbidden/path", mapping_data
        )

        assert success is False


@pytest.mark.asyncio
async def test_storage_mapping_default_file_not_found(hass):
    """Cover line 40: default mapping file not found triggers warning and raises validation/exception."""
    from custom_components.eedomus.storage_mapping import async_load_mapping

    with patch("builtins.open", side_effect=FileNotFoundError):
        # Le fichier par défaut est introuvable (ligne 40 couverte),
        # ce qui entraîne un échec de validation en aval.
        with pytest.raises(Exception):
            await async_load_mapping(hass, config_dir="/tmp")


@pytest.mark.asyncio
async def test_storage_mapping_default_yaml_error(hass):
    """Cover lines 44-46: yaml.YAMLError on default mapping."""
    from custom_components.eedomus.storage_mapping import async_load_mapping

    with patch("yaml.safe_load", side_effect=yaml.YAMLError("Bad default YAML")):
        with pytest.raises(yaml.YAMLError):
            await async_load_mapping(hass, config_dir="/tmp")


@pytest.mark.asyncio
async def test_storage_mapping_default_generic_exception(hass):
    """Cover unexpected exception on default mapping."""
    from custom_components.eedomus.storage_mapping import async_load_mapping

    with patch("yaml.safe_load", side_effect=Exception("Unexpected default error")):
        with pytest.raises(Exception):
            await async_load_mapping(hass, config_dir="/tmp")


@pytest.mark.asyncio
async def test_storage_mapping_custom_yaml_error(hass):
    """Cover lines 58-61: yaml.YAMLError on custom mapping."""
    from custom_components.eedomus.storage_mapping import async_load_mapping

    call_count = 0

    def mock_safe_load(stream):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "version": "1.3.4",
                "advanced_rules": [],
                "dynamic_entity_properties": {},
                "device_types": {},
                "usages": {},
            }
        else:
            raise yaml.YAMLError("Bad custom YAML")

    with patch("yaml.safe_load", side_effect=mock_safe_load):
        with pytest.raises(yaml.YAMLError):
            await async_load_mapping(hass, config_dir="/tmp")


@pytest.mark.asyncio
async def test_storage_mapping_custom_generic_exception(hass):
    """Cover lines 62-65: generic exception on custom mapping."""
    from custom_components.eedomus.storage_mapping import async_load_mapping

    call_count = 0

    def mock_safe_load(stream):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "version": "1.3.4",
                "advanced_rules": [],
                "dynamic_entity_properties": {},
                "device_types": {},
                "usages": {},
            }
        else:
            raise Exception("Unexpected custom error")

    with patch("yaml.safe_load", side_effect=mock_safe_load):
        with pytest.raises(Exception):
            await async_load_mapping(hass, config_dir="/tmp")
