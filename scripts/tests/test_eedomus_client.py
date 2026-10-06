"""Tests unitaires pour le client API eedomus."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.eedomus.const import (
    CONF_HTTP_REQUEST_TIMEOUT,
    DEFAULT_HTTP_REQUEST_TIMEOUT,
    DEFAULT_PHP_FALLBACK_ENABLED,
    DEFAULT_PHP_FALLBACK_SCRIPT_NAME,
    DEFAULT_PHP_FALLBACK_TIMEOUT,
)
from custom_components.eedomus.eedomus_client import EedomusClient


def create_mock_response(status=200, body=b'{"success": 1}', read_side_effect=None):
    """Génère un mock pour la réponse HTTP aiohttp."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    if read_side_effect:
        mock_resp.read.side_effect = read_side_effect
    else:
        mock_resp.read.return_value = body

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_ctx.__aexit__.return_value = None
    return mock_ctx


@pytest.fixture
def mock_config_entry():
    """Fixture simulant une ConfigEntry Home Assistant."""
    entry = MagicMock()
    entry.data = {
        "api_user": "test_user",
        "api_secret": "test_secret",
        "api_host": "192.168.1.100",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_session():
    """Fixture simulant la session ClientSession aiohttp."""
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def client(mock_session, mock_config_entry):
    """Fixture instanciant le client eedomus."""
    return EedomusClient(mock_session, mock_config_entry)


# --- 1. Tests d'initialisation ---


def test_init_default_values(mock_session, mock_config_entry):
    """Vérifie l'initialisation avec les valeurs par défaut."""
    client = EedomusClient(mock_session, mock_config_entry)

    assert client.api_user == "test_user"
    assert client.api_secret == "test_secret"
    assert client.base_url_get == "http://192.168.1.100/api/get"
    assert client.base_url_set == "http://192.168.1.100/api/set"
    assert client.php_fallback_enabled == DEFAULT_PHP_FALLBACK_ENABLED
    assert client.php_fallback_script_name == DEFAULT_PHP_FALLBACK_SCRIPT_NAME
    assert client.php_fallback_timeout == DEFAULT_PHP_FALLBACK_TIMEOUT
    assert client.http_request_timeout == DEFAULT_HTTP_REQUEST_TIMEOUT


def test_init_options_override(mock_session, mock_config_entry):
    """Vérifie que les options prévalent sur les données de configuration."""
    mock_config_entry.options = {
        "php_fallback_enabled": False,
        "php_fallback_script_name": "custom.php",
        "php_fallback_timeout": 15,
        CONF_HTTP_REQUEST_TIMEOUT: 5,
    }
    client = EedomusClient(mock_session, mock_config_entry)

    assert client.php_fallback_enabled is False
    assert client.php_fallback_script_name == "custom.php"
    assert client.php_fallback_timeout == 15
    assert client.http_request_timeout == 5


# --- 2. Tests de fetch_data et gestion réseau / encodages ---


@pytest.mark.asyncio
async def test_fetch_data_success_get(client, mock_session):
    """Vérifie une requête GET réussie."""
    mock_response = create_mock_response(
        body=json.dumps({"success": 1, "body": []}).encode("utf-8")
    )
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.list")

    assert result["success"] == 1
    assert "_raw_data_size_bytes" in result
    mock_session.get.assert_called_once()
    url_called = mock_session.get.call_args[0][0]
    assert url_called == "http://192.168.1.100/api/get?action=periph.list"


@pytest.mark.asyncio
async def test_fetch_data_success_set(client, mock_session):
    """Vérifie une requête SET réussie."""
    mock_response = create_mock_response(
        body=json.dumps({"success": 1, "body": {"result": "OK"}}).encode("utf-8")
    )
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.value", use_set=True)

    assert result["success"] == 1
    url_called = mock_session.get.call_args[0][0]
    assert url_called == "http://192.168.1.100/api/set?action=periph.value"


@pytest.mark.asyncio
async def test_fetch_data_history_mode(client, mock_session):
    """Vérifie le fonctionnement en mode historique (URL absolue)."""
    mock_response = create_mock_response(
        body=json.dumps({"success": 1, "body": {"history": []}}).encode("utf-8")
    )
    mock_session.get.return_value = mock_response
    custom_url = "https://api.eedomus.com/get?action=periph.history"

    result = await client.fetch_data(custom_url, history_mode=True)

    assert result["success"] == 1
    url_called = mock_session.get.call_args[0][0]
    assert url_called == custom_url


@pytest.mark.asyncio
async def test_fetch_data_http_error_utf8(client, mock_session):
    """Vérifie la gestion d'un statut HTTP !== 200 décodé en UTF-8."""
    mock_response = create_mock_response(
        status=500, body="Erreur serveur".encode("utf-8")
    )
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert result["http_status"] == 500
    assert result["raw_response"] == "Erreur serveur"


@pytest.mark.asyncio
async def test_fetch_data_http_error_iso_fallback(client, mock_session):
    """Vérifie le passage en ISO-8859-1 en cas d'erreur de décodage UTF-8."""
    # Le caractère 'è' en ISO-8859-1 produit un octet invalide en UTF-8 (\xe8),
    # ce qui déclenche naturellement UnicodeDecodeError sans mocker 'bytes'.
    raw_data = "Erreur accès".encode("iso-8859-1")
    mock_response = create_mock_response(status=403, body=raw_data)
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert result["http_status"] == 403
    assert result["raw_response"] == "Erreur accès"


def test_decode_response_encodings(client):
    """Vérifie le décodage sous plusieurs encodages (latin-1, iso, windows-1252)."""
    text = "Élément dynamique"
    encoded_latin = text.encode("latin-1")

    decoded = client._decode_response(encoded_latin)
    assert decoded == text


@pytest.mark.asyncio
async def test_fetch_data_eedomus_known_error(client, mock_session):
    """Vérifie l'interception d'un code d'erreur eedomus connu."""
    payload = {"success": "0", "body": {"error_code": "1", "error_msg": "Bad auth"}}
    mock_response = create_mock_response(body=json.dumps(payload).encode("utf-8"))
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("auth.test")

    assert result["success"] == 0
    assert result["error_code"] == "1"
    assert "Invalid API credentials" in result["error"]


@pytest.mark.asyncio
async def test_fetch_data_eedomus_unknown_error(client, mock_session):
    """Vérifie la gestion d'un code d'erreur eedomus inconnu."""
    payload = {"success": 0, "body": {"error_code": "999", "error_msg": "Custom err"}}
    mock_response = create_mock_response(body=json.dumps(payload).encode("utf-8"))
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("auth.test")

    assert result["success"] == 0
    assert result["error"] == "Custom err"


@pytest.mark.asyncio
async def test_fetch_data_invalid_json(client, mock_session):
    """Vérifie la réaction à une réponse qui n'est pas du JSON valide."""
    mock_response = create_mock_response(body=b"<html>Bad Gateway</html>")
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert result["error"] == "Invalid JSON response"


@pytest.mark.asyncio
async def test_fetch_data_non_dict_json(client, mock_session):
    """Vérifie la réaction lorsque le JSON retourné est une liste au lieu d'un dictionnaire."""
    mock_response = create_mock_response(body=b"[1, 2, 3]")
    mock_session.get.return_value = mock_response

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert result["error"] == "Invalid response format"


@pytest.mark.asyncio
async def test_fetch_data_timeout(client, mock_session):
    """Vérifie la capture du timeout (asyncio.TimeoutError)."""
    mock_session.get.side_effect = asyncio.TimeoutError()

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert result["http_status"] == 408
    assert result["error"] == "Request timed out"


@pytest.mark.asyncio
async def test_fetch_data_client_error(client, mock_session):
    """Vérifie la capture des exceptions aiohttp.ClientError."""
    mock_session.get.side_effect = aiohttp.ClientError("Connexion refusée")

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert "Connexion refusée" in result["error"]


@pytest.mark.asyncio
async def test_fetch_data_generic_exception(client, mock_session):
    """Vérifie la capture de toute exception inattendue."""
    mock_session.get.side_effect = RuntimeError("Crash imprévu")

    result = await client.fetch_data("periph.list")

    assert result["success"] == 0
    assert "Crash imprévu" in result["error"]


# --- 3. Tests des utilitaires de sécurité / logging ---


def test_get_safe_url_for_logging(client):
    """Vérifie que l'URL à logger est purgée de ses paramètres de requête."""
    client.url = "http://192.168.1.100/api/get?action=test&api_secret=12345"
    safe_url = client._get_safe_url_for_logging()

    assert safe_url == "http://192.168.1.100/api/get"


def test_get_safe_params_for_logging(client):
    """Vérifie le masquage des clés sensibles api_user et api_secret dans les dictionnaires de paramètres."""
    client.params = {
        "action": "get",
        "api_user": "user123",
        "api_secret": "secret123",
        "periph_id": "100",
    }
    safe_params = client._get_safe_params_for_logging()

    assert safe_params["api_user"] == "***redacted***"
    assert safe_params["api_secret"] == "***redacted***"
    assert safe_params["periph_id"] == "100"


# --- 4. Tests des méthodes API spécifiques ---


@pytest.mark.asyncio
async def test_set_periph_value_success(client):
    """Vérifie l'envoi de valeur et la normalisation du champ message."""
    mock_response = {"success": 1, "body": {"result": "Value set"}}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.set_periph_value("12345", "100")
        assert res["success"] == 1
        assert res["message"] == "Value set"


@pytest.mark.asyncio
async def test_set_periph_value_error(client):
    """Vérifie l'échec de la modification d'une valeur de périphérique."""
    mock_response = {"success": 0, "error": "Invalid peripheral"}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.set_periph_value("12345", "100")
        assert res["success"] == 0


@pytest.mark.asyncio
async def test_get_periph_value_normalization(client):
    """Vérifie l'extraction automatique de value depuis body."""
    mock_response = {"success": 1, "body": {"value": "21.5"}}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.get_periph_value("12345")
        assert res["value"] == "21.5"


@pytest.mark.asyncio
async def test_get_periph_list_normalization(client):
    """Vérifie que body est toujours une liste même s'il est absent du retour."""
    mock_response = {"success": 1}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.get_periph_list()
        assert res["body"] == []


@pytest.mark.asyncio
async def test_get_periph_caract(client):
    """Vérifie la transmission de l'option show_config."""
    mock_response = {"success": 1, "body": {"name": "Thermostat"}}
    with patch.object(
        client, "fetch_data", AsyncMock(return_value=mock_response)
    ) as mock_fetch:
        await client.get_periph_caract("12345", show_config=True)
        mock_fetch.assert_called_once_with(
            "periph.caract", {"periph_id": "12345", "show_config": 1}
        )


@pytest.mark.asyncio
async def test_get_periph_history(client):
    """Vérifie l'obtention de l'historique d'un périphérique."""
    mock_response = {"success": 1, "body": [{"value": "1", "date": "2026-01-01"}]}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.get_periph_history("12345")
        assert len(res["body"]) == 1


@pytest.mark.asyncio
async def test_get_periph_value_list(client):
    """Vérifie la récupération de la liste des valeurs autorisées."""
    mock_response = {"success": 1, "body": ["ON", "OFF"]}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.get_periph_value_list("12345")
        assert res["body"] == ["ON", "OFF"]


@pytest.mark.asyncio
async def test_auth_test(client):
    """Vérifie le test d'authentification."""
    mock_response = {"success": 1, "body": {"auth": "OK"}}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        res = await client.auth_test()
        assert res["success"] == 1


@pytest.mark.asyncio
async def test_get_periph_info_found(client):
    """Vérifie l'extraction d'un périphérique spécifique à partir de getPeriphList."""
    mock_response = {
        "success": 1,
        "body": [
            {"periph_id": "100", "name": "Lampe"},
            {"periph_id": "200", "name": "Prise"},
        ],
    }
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        info = await client.get_periph_info("200")
        assert info["name"] == "Prise"


@pytest.mark.asyncio
async def test_get_periph_info_not_found(client):
    """Vérifie le retour None lorsque le périphérique est absent de la liste."""
    mock_response = {"success": 1, "body": [{"periph_id": "100"}]}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        info = await client.get_periph_info("999")
        assert info is None


@pytest.mark.asyncio
async def test_get_device_history_count(client):
    """Vérifie le calcul par défaut de l'estimation du nombre de points d'historique."""
    count = await client.get_device_history_count("12345")
    assert count == 8760


@pytest.mark.asyncio
async def test_get_device_history_success(client):
    """Vérifie le traitement de l'historique récupéré depuis api.eedomus.com."""
    mock_response = {
        "success": 1,
        "body": {"history": [["21.5", "1700000000"], ["22.0", "1700003600"]]},
    }
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        history = await client.get_device_history("12345", start_timestamp=1000)
        assert len(history) == 2
        assert history[0] == {"value": "21.5", "timestamp": "1700000000"}


@pytest.mark.asyncio
async def test_get_device_history_failure(client):
    """Vérifie le retour None lors d'un échec d'extraction de l'historique."""
    mock_response = {"success": 0, "message": "History disabled"}
    with patch.object(client, "fetch_data", AsyncMock(return_value=mock_response)):
        history = await client.get_device_history("12345")
        assert history is None


# --- 5. Tests de la fonction PHP Fallback ---


@pytest.mark.asyncio
async def test_php_fallback_disabled(client):
    """Vérifie l'interruption directe si le fallback PHP n'est pas activé."""
    client.php_fallback_enabled = False
    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 0
    assert res["error"] == "PHP fallback not configured"


@pytest.mark.asyncio
async def test_php_fallback_success(client, mock_session):
    """Vérifie le succès de l'exécution du script de secours PHP."""
    client.php_fallback_enabled = True
    payload = {"success": 1, "duration": "0.12"}
    mock_response = create_mock_response(body=json.dumps(payload).encode("utf-8"))
    mock_session.get.return_value = mock_response

    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 1
    assert res["duration"] == "0.12"


@pytest.mark.asyncio
async def test_php_fallback_http_error(client, mock_session):
    """Vérifie la gestion d'une erreur HTTP sur le script PHP de secours."""
    client.php_fallback_enabled = True
    mock_response = create_mock_response(status=404, body=b"Script Not Found")
    mock_session.get.return_value = mock_response

    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 0
    assert "HTTP 404" in res["error"]


@pytest.mark.asyncio
async def test_php_fallback_json_error(client, mock_session):
    """Vérifie la réaction à un retour non-JSON du script PHP."""
    client.php_fallback_enabled = True
    mock_response = create_mock_response(body=b"Fatal PHP Error")
    mock_session.get.return_value = mock_response

    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 0
    assert res["error"] == "Invalid JSON response from PHP fallback script"


@pytest.mark.asyncio
async def test_php_fallback_timeout(client, mock_session):
    """Vérifie la gestion du timeout lors de l'appel PHP."""
    client.php_fallback_enabled = True
    mock_session.get.side_effect = asyncio.TimeoutError()

    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 0
    assert res["error"] == "PHP fallback script timeout"


@pytest.mark.asyncio
async def test_php_fallback_client_error(client, mock_session):
    """Vérifie la gestion d'une erreur client lors de l'appel PHP."""
    client.php_fallback_enabled = True
    mock_session.get.side_effect = aiohttp.ClientError("DNS fail")

    res = await client.php_fallback_set_value("123", "ON")

    assert res["success"] == 0
    assert "DNS fail" in res["error"]
