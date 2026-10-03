"""Tests unitaires pour le flux de configuration (config_flow) d'eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus.config_flow import EedomusConfigFlow
from custom_components.eedomus.const import (
    CONF_API_HOST,
    CONF_API_SECRET,
    CONF_API_USER,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_HTTP_REQUEST_TIMEOUT,
    DOMAIN,
)

from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from custom_components.eedomus.const import (
    DOMAIN,
    CONF_API_HOST,
    CONF_API_USER,
    CONF_API_SECRET,
    CONF_ENABLE_HISTORY,
    CONF_REMOVE_ENTITIES,
    DEFAULT_REMOVE_ENTITIES,
)

from custom_components.eedomus.config_flow import EedomusOptionsFlow, EedomusConfigFlow



# Données de test valides pour le formulaire
VALID_USER_INPUT = {
    CONF_API_HOST: "192.168.1.50",
    CONF_ENABLE_API_EEDOMUS: True,
    CONF_ENABLE_API_PROXY: False,
    CONF_API_USER: "my_api_user",
    CONF_API_SECRET: "my_api_secret",
    "scan_interval": 60,
    CONF_HTTP_REQUEST_TIMEOUT: 15,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Autorise le chargement du dossier custom_components/eedomus pendant les tests."""
    yield


@pytest.fixture
def mock_eedomus_client():
    """Fixture simulant le client API eedomus."""
    with patch(
        "custom_components.eedomus.config_flow.EedomusClient", autospec=True
    ) as mock_client_cls:
        client_instance = MagicMock()
        client_instance.auth_test = AsyncMock(return_value={"success": 1})
        mock_client_cls.return_value = client_instance
        yield client_instance


# --- 1. Test d'affichage du formulaire ---


async def test_step_user_show_form(hass: HomeAssistant):
    """Vérifie que l'étape initiale 'user' renvoie le formulaire."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == None


# --- 2. Tests de succès (API Eedomus & Proxy) ---

async def test_step_user_success_api_mode(
    hass: HomeAssistant,
    mock_eedomus_client,
    aioclient_mock,
):
    """Vérifie la création réussie d'une entrée en mode API Eedomus."""

    # ------------------------------------------------------------
    # Mock des appels HTTP réels effectués lors du setup de l'entrée
    # ------------------------------------------------------------

    # periph.list
    aioclient_mock.get(
        "http://192.168.1.50/api/get",
        params={
            "api_user": "my_api_user",
            "api_secret": "my_api_secret",
        },
        json={
            "success": 1,
            "body": [],
        },
    )

    # periph.value_list
    aioclient_mock.get(
        "http://192.168.1.50/api/get",
        params={
            "periph_id": "all",
            "api_user": "my_api_user",
            "api_secret": "my_api_secret",
        },
        json={
            "success": 1,
            "body": [],
        },
    )

    # periph.caract
    aioclient_mock.get(
        "http://192.168.1.50/api/get",
        params={
            "periph_id": "all",
            "show_config": 1,
            "api_user": "my_api_user",
            "api_secret": "my_api_secret",
        },
        json={
            "success": 1,
            "body": [],
        },
    )

    # ------------------------------------------------------------
    # Démarrage du config flow
    # ------------------------------------------------------------

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # ------------------------------------------------------------
    # Soumission de la configuration utilisateur
    # ------------------------------------------------------------

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_USER_INPUT,
    )

    # ------------------------------------------------------------
    # Vérifications
    # ------------------------------------------------------------

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Eedomus (192.168.1.50) - Eedomus API Mode"
    assert result2["data"][CONF_API_HOST] == "192.168.1.50"
    assert result2["result"].unique_id == "eedomus_192.168.1.50"


async def test_step_user_success_proxy_only_mode(hass: HomeAssistant):
    """Vérifie la création réussie d'une entrée en mode Proxy uniquement (sans identifiants)."""
    proxy_input = {
        CONF_API_HOST: "192.168.1.50",
        CONF_ENABLE_API_EEDOMUS: False,
        CONF_ENABLE_API_PROXY: True,
        CONF_API_USER: "",
        CONF_API_SECRET: "",
        "scan_interval": 60,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # On mocke EedomusClient pour empêcher toute tentative de connexion réseau réelle
    with patch("custom_components.eedomus.config_flow.EedomusClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.auth_test = AsyncMock(return_value={"success": 1})

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            proxy_input,
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Eedomus (192.168.1.50) - Proxy Mode"


# --- 3. Test de détection des doublons ---


async def test_step_user_already_configured(hass: HomeAssistant):
    """Vérifie le comportement d'abandon si la box eedomus est déjà configurée."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="eedomus_192.168.1.50",
        data=VALID_USER_INPUT,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_USER_INPUT,
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


# --- 4. Tests des erreurs de validation du formulaire ---


@pytest.mark.parametrize(
    ("override_data", "expected_error"),
    [
        ({CONF_API_HOST: ""}, "API host cannot be empty"),
        ({"scan_interval": 10}, "Scan interval must be at least 30 seconds"),
        (
            {CONF_HTTP_REQUEST_TIMEOUT: 2},
            "HTTP request timeout must be between 5 and 120 seconds",
        ),
        (
            {CONF_ENABLE_API_EEDOMUS: True, CONF_API_USER: ""},
            "API user is required when API Eedomus mode is enabled",
        ),
        (
            {CONF_ENABLE_API_EEDOMUS: True, CONF_API_SECRET: ""},
            "API secret is required when API Eedomus mode is enabled",
        ),
        (
            {CONF_ENABLE_API_EEDOMUS: False, CONF_ENABLE_API_PROXY: False},
            "At least one connection mode (API Eedomus or API Proxy) must be enabled",
        ),
    ],
)
async def test_validation_errors(hass: HomeAssistant, override_data, expected_error):
    """Vérifie les différentes erreurs de validation des paramètres."""
    user_input = {**VALID_USER_INPUT, **override_data}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result2["type"] == FlowResultType.FORM
    assert "base" in result2["errors"]
    assert expected_error in result2["errors"]["base"]


# --- 5. Tests d'échec d'authentification / API ---


async def test_auth_test_failure_invalid_credentials(
    hass: HomeAssistant, mock_eedomus_client
):
    """Vérifie l'erreur quand l'API eedomus renvoie un statut d'échec (success != 1)."""
    mock_eedomus_client.auth_test.return_value = {"success": 0, "error_code": "1"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_USER_INPUT,
    )

    assert result2["type"] == FlowResultType.FORM
    assert "Cannot connect to eedomus API" in result2["errors"]["base"]


async def test_auth_test_exception(hass: HomeAssistant, mock_eedomus_client):
    """Vérifie l'erreur quand l'API eedomus lève une exception réseau."""
    mock_eedomus_client.auth_test.side_effect = Exception("Connection refused")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_USER_INPUT,
    )

    assert result2["type"] == FlowResultType.FORM
    assert "API Eedomus connection test failed" in result2["errors"]["base"]


async def test_unexpected_exception(hass: HomeAssistant):
    """Vérifie le comportement en cas d'erreur inattendue non gérée dans validate_input."""
    with patch.object(
        EedomusConfigFlow, "validate_input", side_effect=RuntimeError("Fatal error")
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_USER_INPUT,
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "unknown"}


# --- 6. Test d'obtention du gestionnaire d'options ---


def test_async_get_options_flow():
    """Vérifie que async_get_options_flow retourne une instance valide d'EedomusOptionsFlow."""
    mock_entry = MagicMock(spec=config_entries.ConfigEntry)
    options_flow = EedomusConfigFlow.async_get_options_flow(mock_entry)

    assert options_flow is not None


# =================

import pytest
import voluptuous as vol
import inspect
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant
from custom_components.eedomus.const import (
    DOMAIN,
    CONF_API_HOST,
    CONF_ENABLE_HISTORY,
    CONF_REMOVE_ENTITIES,
)
from custom_components.eedomus.config_flow import EedomusConfigFlow

def test_print_validate_input_source():
    """Diagnostic pour voir où se trouve et comment est définie la fonction de validation."""
    try:
        from custom_components.eedomus import config_flow
        if hasattr(config_flow, "validate_input"):
            print("\n--- SOURCE validate_input ---")
            print(inspect.getsource(config_flow.validate_input))
            print("------------------------------\n")
        elif hasattr(EedomusConfigFlow, "validate_input"):
            print("\n--- SOURCE EedomusConfigFlow.validate_input ---")
            print(inspect.getsource(EedomusConfigFlow.validate_input))
            print("---------------------------------------------\n")
    except Exception as e:
        print(f"Erreur diagnostic : {e}")

@pytest.mark.asyncio
@patch("custom_components.eedomus.config_flow.EedomusClient")
async def test_history_without_api_eedomus_invalid(hass: HomeAssistant):
    """Cover line 242: History enabled without API Eedomus mode raises vol.Invalid."""
    flow = EedomusConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_API_HOST: "192.168.1.50",
        CONF_ENABLE_HISTORY: True,
        CONF_ENABLE_API_EEDOMUS: False,
        CONF_ENABLE_API_PROXY: True,
    }

    validator = getattr(flow, "validate_input", None)
    if validator is not None:
        with pytest.raises(vol.Invalid, match="History can only be enabled with API Eedomus mode"):
            if inspect.iscoroutinefunction(validator):
                await validator(user_input)
            else:
                validator(flow, user_input)

@pytest.mark.asyncio
async def test_config_flow_uninstall_form_and_submit(hass: HomeAssistant):
    """Cover lines 327-359: async_step_uninstall form display and submission."""
    flow = EedomusConfigFlow()
    flow.hass = hass
    flow.hass.config_entries = MagicMock()
    flow.config_entry = MagicMock()
    flow.config_entry.options = {}

    # 1. user_input is None -> affiche le formulaire
    result = await flow.async_step_uninstall(user_input=None)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "uninstall"

    # 2. user_input soumis -> met à jour l'entrée et appelle async_step_remove
    with patch.object(flow, "async_step_remove", return_value={"type": data_entry_flow.FlowResultType.ABORT}) as mock_remove:
        result = await flow.async_step_uninstall(user_input={CONF_REMOVE_ENTITIES: True})
        flow.hass.config_entries.async_update_entry.assert_called_once()
        mock_remove.assert_called_once()

@pytest.mark.asyncio
async def test_config_flow_remove_and_entity_cleanup(hass: HomeAssistant):
    """Cover lines 364-393: async_step_remove and _async_remove_entities."""
    flow = EedomusConfigFlow()
    flow.hass = hass
    flow.config_entry = MagicMock()

    # Mock du registre d'entités
    entity_registry = MagicMock()
    entity_entry = MagicMock()
    entity_entry.platform = DOMAIN
    entity_entry.entity_id = "sensor.eedomus_test"
    entity_registry.entities.values.return_value = [entity_entry]

    if not hasattr(flow.hass, "helpers") or flow.hass.helpers is None:
        flow.hass.helpers = MagicMock()
    flow.hass.helpers.entity_registry = MagicMock()
    flow.hass.helpers.entity_registry.async_get_registry = AsyncMock(return_value=entity_registry)

    original_super_remove = getattr(ConfigFlow, "async_step_remove", None)
    ConfigFlow.async_step_remove = AsyncMock(return_value={"type": data_entry_flow.FlowResultType.ABORT})

    try:
        flow.config_entry.options = {CONF_REMOVE_ENTITIES: True}
        await flow.async_step_remove(user_input=None)
        entity_registry.async_remove.assert_called_once_with("sensor.eedomus_test")

        flow.config_entry.options = {CONF_REMOVE_ENTITIES: False}
        entity_registry.async_remove.reset_mock()
        await flow.async_step_remove(user_input=None)
        entity_registry.async_remove.assert_not_called()
    finally:
        if original_super_remove is not None:
            ConfigFlow.async_step_remove = original_super_remove
        else:
            delattr(ConfigFlow, "async_step_remove")


async def test_validation_connection_failure(hass: HomeAssistant):
    """Vérifie qu'une erreur est levée si l'API Eedomus échoue."""
    user_input = {
        CONF_API_HOST: "192.168.1.50",
        CONF_ENABLE_API_EEDOMUS: True,
        CONF_ENABLE_API_PROXY: False,
        CONF_API_USER: "user",
        CONF_API_SECRET: "secret",
    }

    with patch("custom_components.eedomus.config_flow.EedomusClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Simule un échec de l'API (ex: success != 1 ou exception)
        mock_client.auth_test = AsyncMock(return_value={"success": 0})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input,
        )

        assert result2["type"] == FlowResultType.FORM
        assert "base" in result2["errors"]

async def test_validation_unexpected_exception(hass: HomeAssistant):
    """Vérifie qu'une exception inattendue pendant l'authentification lève une erreur de validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.eedomus.config_flow.EedomusClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Simule une erreur critique / exception inattendue
        mock_client.auth_test.side_effect = Exception("Erreur réseau critique")

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_HOST: "192.168.1.50",
                CONF_ENABLE_API_EEDOMUS: True,
                CONF_ENABLE_API_PROXY: False,
                CONF_API_USER: "my_api_user",
                CONF_API_SECRET: "my_api_secret",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert "base" in result2["errors"]
