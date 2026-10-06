"""Tests unitaires pour la vue webhook de l'intégration Eedomus (webhook.py)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.const import COORDINATOR, DOMAIN
from custom_components.eedomus.webhook import EedomusWebhookView


@pytest.mark.asyncio
async def test_webhook_unauthorized_ip():
    """Test que les requêtes provenant d'une IP non autorisée sont rejetées (403)."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=False
    )

    request = MagicMock()
    request.remote = "192.168.1.50"  # IP non présente dans allowed_ips

    response = await view.post(request)
    assert response.status == 403
    assert response.text == "Unauthorized"


@pytest.mark.asyncio
async def test_webhook_disabled_security_ip():
    """Test que la sécurité IP peut être contournée si disable_security est à True."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.50"  # IP non autorisée mais sécurité désactivée
    request.json = AsyncMock(side_effect=json.JSONDecodeError("Erreur", "", 0))

    # Doit passer le filtre IP et échouer plus loin sur le JSON invalide (400 au lieu de 403)
    response = await view.post(request)
    assert response.status == 400
    assert response.text == "Invalid JSON"


@pytest.mark.asyncio
async def test_webhook_invalid_json():
    """Test le rejet d'un payload JSON malformé (400)[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(side_effect=json.JSONDecodeError("Erreur", "", 0))

    response = await view.post(request)
    assert response.status == 400
    assert response.text == "Invalid JSON"


@pytest.mark.asyncio
async def test_webhook_unrecognized_action():
    """Test le rejet d'une action non reconnue dans le JSON (400)[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "action_inconnue"})

    response = await view.post(request)
    assert response.status == 400
    assert response.text == "Unrecognized action"


@pytest.mark.asyncio
async def test_webhook_coordinator_not_available():
    """Test le comportement si le coordinateur est introuvable dans hass.data (500)[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    hass = MagicMock()
    hass.data = {DOMAIN: {}}  # Pas de données pour cette box[cite: 4]

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "refresh"})
    request.app = {"hass": hass}

    response = await view.post(request)
    assert response.status == 500
    assert response.text == "Coordinator not available"


@pytest.mark.asyncio
async def test_webhook_action_refresh():
    """Test l'exécution réussie de l'action de rafraîchissement complet ('refresh')[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    coordinator = AsyncMock()
    hass = MagicMock()
    hass.data = {DOMAIN: {"box_123": {COORDINATOR: coordinator}}}

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "refresh"})
    request.app = {"hass": hass}

    response = await view.post(request)
    assert response.status == 200
    assert response.text == "OK"
    coordinator._async_full_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_action_partial_refresh():
    """Test l'exécution réussie de l'action de rafraîchissement partiel ('partial_refresh')[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    coordinator = AsyncMock()
    hass = MagicMock()
    hass.data = {DOMAIN: {"box_123": {COORDINATOR: coordinator}}}

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "partial_refresh"})
    request.app = {"hass": hass}

    response = await view.post(request)
    assert response.status == 200
    assert response.text == "OK"
    coordinator._async_partial_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_action_reload():
    """Test l'exécution réussie du rechargement de l'intégration ('reload')[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    coordinator = AsyncMock()
    config_entry = MagicMock()
    config_entry.entry_id = "box_123"

    hass = MagicMock()
    hass.data = {DOMAIN: {"box_123": {COORDINATOR: coordinator}}}
    hass.config_entries.async_entries.return_value = [config_entry]
    hass.config_entries.async_reload = AsyncMock()

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "reload"})
    request.app = {"hass": hass}

    response = await view.post(request)
    assert response.status == 200
    assert response.text == "OK"
    hass.config_entries.async_reload.assert_awaited_once_with("box_123")


@pytest.mark.asyncio
async def test_webhook_action_reload_config_not_found():
    """Test l'échec du rechargement si l'entrée de configuration est introuvable (500)[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    coordinator = AsyncMock()
    hass = MagicMock()
    hass.data = {DOMAIN: {"box_123": {COORDINATOR: coordinator}}}
    hass.config_entries.async_entries.return_value = (
        []
    )  # Aucune entrée correspondante[cite: 4]

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"action": "reload"})
    request.app = {"hass": hass}

    response = await view.post(request)
    assert response.status == 500
    assert response.text == "Config entry not found"


@pytest.mark.asyncio
async def test_webhook_internal_error():
    """Test la capture d'une exception imprévue générant une erreur interne (500)[cite: 4]."""
    view = EedomusWebhookView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(side_effect=Exception("Crash inattendu"))

    response = await view.post(request)
    assert response.status == 500
    assert response.text == "Internal error"
