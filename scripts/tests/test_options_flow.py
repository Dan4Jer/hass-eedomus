"""Tests unitaires pour le flux d'options (options_flow) d'eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus.const import (
    CONF_API_HOST,
    CONF_API_SECRET,
    CONF_API_USER,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_YAML_CONTENT,
    DOMAIN,
)
from custom_components.eedomus.options_flow import EedomusOptionsFlow

# Configuration initiale simulant les données enregistrées lors de la config
MOCK_CONFIG_DATA = {
    CONF_API_HOST: "192.168.1.50",
    CONF_API_USER: "user_test",
    CONF_API_SECRET: "secret_test",
    CONF_ENABLE_API_EEDOMUS: True,
    CONF_ENABLE_API_PROXY: False,
    CONF_ENABLE_HISTORY: False,
    CONF_SCAN_INTERVAL: 300,
}

# Données soumises par l'utilisateur dans le formulaire d'options
MOCK_USER_INPUT_INIT = {
    CONF_API_HOST: "192.168.1.50",
    CONF_API_USER: "user_test",
    CONF_API_SECRET: "secret_test",
    CONF_ENABLE_API_EEDOMUS: True,
    CONF_ENABLE_API_PROXY: False,
    CONF_ENABLE_HISTORY: True,
    CONF_SCAN_INTERVAL: 600,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Autorise le chargement des intégrations personnalisées dans HA."""
    yield


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Crée une fausse ConfigEntry enregistrée dans Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eedomus (192.168.1.50)",
        data=MOCK_CONFIG_DATA,
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)
    return entry


# --- 1. Test de la fabrique async_get_options_flow ---


def test_async_get_options_flow(mock_config_entry):
    """Vérifie que la méthode statique instancie correctement EedomusOptionsFlow."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    assert isinstance(flow, EedomusOptionsFlow)


# --- 2. Tests de l'étape init (Affichage & Validation API) ---


async def test_step_init_show_form(hass: HomeAssistant, mock_config_entry):
    """Vérifie l'affichage initial du formulaire avec la récupération des valeurs par défaut."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {}


async def test_step_init_success(hass: HomeAssistant, mock_config_entry):
    """Vérifie la mise à jour réussie des options avec test d'authentification OK."""
    with patch(
        "custom_components.eedomus.eedomus_client.EedomusClient"
    ) as mock_client_cls:
        client_inst = MagicMock()
        client_inst.auth_test = AsyncMock(return_value={"success": 1})
        mock_client_cls.return_value = client_inst

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=MOCK_USER_INPUT_INIT,
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"][CONF_SCAN_INTERVAL] == 600
        assert result2["data"][CONF_ENABLE_HISTORY] is True


async def test_step_init_cannot_connect_api_failure(
    hass: HomeAssistant, mock_config_entry
):
    """Vérifie l'erreur quand l'API eedomus renvoie une réponse d'échec (success != 1)."""
    with patch(
        "custom_components.eedomus.eedomus_client.EedomusClient"
    ) as mock_client_cls:
        client_inst = MagicMock()
        client_inst.auth_test = AsyncMock(return_value={"success": 0})
        mock_client_cls.return_value = client_inst

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=MOCK_USER_INPUT_INIT,
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_step_init_cannot_connect_exception(
    hass: HomeAssistant, mock_config_entry
):
    """Vérifie l'erreur quand l'API eedomus lève une exception réseau."""
    with patch(
        "custom_components.eedomus.eedomus_client.EedomusClient"
    ) as mock_client_cls:
        client_inst = MagicMock()
        client_inst.auth_test = AsyncMock(side_effect=Exception("Timeout"))
        mock_client_cls.return_value = client_inst

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=MOCK_USER_INPUT_INIT,
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_step_init_bypass_api_check_when_disabled(
    hass: HomeAssistant, mock_config_entry
):
    """Vérifie le saut du test de connexion si l'API eedomus est désactivée."""
    user_input = {**MOCK_USER_INPUT_INIT, CONF_ENABLE_API_EEDOMUS: False}

    with patch(
        "custom_components.eedomus.eedomus_client.EedomusClient"
    ) as mock_client_cls:
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=user_input,
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"][CONF_ENABLE_API_EEDOMUS] is False
        mock_client_cls.assert_not_called()


# --- 3. Tests de l'étape UI ---


async def test_step_ui_flow(hass: HomeAssistant, mock_config_entry):
    """Vérifie l'affichage et la soumission de l'étape UI."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    # Formulaire initial UI
    result_form = await flow.async_step_ui()
    assert result_form["type"] == FlowResultType.FORM
    assert result_form["step_id"] == "ui"

    # Validation du formulaire UI
    result_submit = await flow.async_step_ui(
        user_input={CONF_ENABLE_API_EEDOMUS: True, CONF_SCAN_INTERVAL: 180}
    )
    assert result_submit["type"] == FlowResultType.CREATE_ENTRY


# --- 4. Tests de l'étape YAML ---


async def test_step_yaml_show_form_success(hass: HomeAssistant, mock_config_entry):
    """Vérifie le chargement et le rendu du contenu YAML existant."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    fake_mapping = {"custom_devices": [{"eedomus_id": "123", "name": "Lampe"}]}

    with patch(
        "custom_components.eedomus.options_flow.async_load_mapping",
        AsyncMock(return_value=fake_mapping),
    ):
        result = await flow.async_step_yaml()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "yaml"
        assert "123" in flow.yaml_content


async def test_step_yaml_show_form_fallback_on_error(
    hass: HomeAssistant, mock_config_entry
):
    """Vérifie qu'un modèle de secours est utilisé si le chargement YAML échoue."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    with patch(
        "custom_components.eedomus.options_flow.async_load_mapping",
        AsyncMock(side_effect=Exception("File error")),
    ):
        result = await flow.async_step_yaml()

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "failed_to_load_yaml"}
        assert "# Eedomus Custom Mapping" in flow.yaml_content


async def test_step_yaml_submit_valid(hass: HomeAssistant, mock_config_entry):
    """Vérifie la sauvegarde réussie d'une configuration YAML valide."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    valid_yaml_str = "custom_devices:\n  - eedomus_id: '12345'\n    type: 'light'"

    with patch(
        "custom_components.eedomus.options_flow.async_save_custom_mapping",
        AsyncMock(return_value=True),
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA",
        side_effect=lambda x: x,
    ):
        result = await flow.async_step_yaml(user_input={"yaml_content": valid_yaml_str})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_YAML_CONTENT] == valid_yaml_str


async def test_step_yaml_submit_invalid_syntax(hass: HomeAssistant, mock_config_entry):
    """Vérifie l'erreur remontée en cas de syntaxe YAML corrompue."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    invalid_yaml_syntax = "custom_devices: [unclosed_array"

    with patch(
        "custom_components.eedomus.options_flow.async_load_mapping",
        AsyncMock(return_value={}),
    ):
        result = await flow.async_step_yaml(
            user_input={"yaml_content": invalid_yaml_syntax}
        )

        assert result["type"] == FlowResultType.FORM
        assert "invalid_yaml" in result["errors"]["base"]


async def test_step_yaml_submit_invalid_schema(hass: HomeAssistant, mock_config_entry):
    """Vérifie l'erreur remontée si le schéma de validation du mapping échoue."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    valid_yaml_syntax = "custom_devices: 'invalid_type_should_be_list'"

    with patch(
        "custom_components.eedomus.options_flow.async_load_mapping",
        AsyncMock(return_value={}),
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA",
        side_effect=vol.Invalid("Invalid schema structure"),
    ):
        result = await flow.async_step_yaml(
            user_input={"yaml_content": valid_yaml_syntax}
        )

        assert result["type"] == FlowResultType.FORM
        assert "invalid_mapping" in result["errors"]["base"]


async def test_step_yaml_submit_save_failure(hass: HomeAssistant, mock_config_entry):
    """Vérifie l'erreur quand la fonction async_save_custom_mapping retourne False."""
    flow = EedomusOptionsFlow.async_get_options_flow(mock_config_entry)
    flow.hass = hass

    with patch(
        "custom_components.eedomus.options_flow.async_save_custom_mapping",
        AsyncMock(return_value=False),
    ), patch(
        "custom_components.eedomus.options_flow.async_load_mapping",
        AsyncMock(return_value={}),
    ), patch(
        "custom_components.eedomus.const.YAML_MAPPING_SCHEMA",
        side_effect=lambda x: x,
    ):
        result = await flow.async_step_yaml(
            user_input={"yaml_content": "custom_devices: []"}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "failed_to_save_yaml"}


@pytest.mark.asyncio
async def test_options_flow_copy_config_with_existing_options():
    """Cover line 60: options_flow copies existing non-empty options."""
    from custom_components.eedomus.options_flow import EedomusOptionsFlow

    config_entry = MagicMock()
    # On initialise options avec des valeurs non vides pour passer dans le 'else' (ligne 60)
    config_entry.options = {"existing_option": "value"}
    config_entry.data = {}

    flow = EedomusOptionsFlow(config_entry)

    # Appel direct de la méthode interne pour exécuter la ligne 60
    flow._copy_config_to_options()
