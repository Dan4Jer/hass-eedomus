"""Tests unitaires pour la vue proxy API de l'intégration Eedomus (api_proxy.py)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.api_proxy import EedomusApiProxyView


@pytest.mark.asyncio
async def test_api_proxy_unauthorized_ip():
    """Test que les requêtes d'une IP non autorisée sont rejetées par le proxy (403)[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=False
    )

    request = MagicMock()
    request.remote = "192.168.1.99"  # IP non autorisée[cite: 5]

    response = await view.post(request, path="services/light/turn_on")
    assert response.status == 403
    assert response.text == "Unauthorized"


@pytest.mark.asyncio
async def test_api_proxy_disabled_security_ip():
    """Test que la sécurité IP peut être contournée si disable_security est à True[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.99"
    request.json = AsyncMock(side_effect=json.JSONDecodeError("Erreur", "", 0))

    # Doit passer le filtre IP et échouer sur le JSON (400 au lieu de 403)[cite: 5]
    response = await view.post(request, path="services/light/turn_on")
    assert response.status == 400
    assert response.text == "Invalid JSON"


@pytest.mark.asyncio
async def test_api_proxy_invalid_json():
    """Test le rejet d'un payload JSON invalide envoyé au proxy (400)[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(side_effect=json.JSONDecodeError("Erreur", "", 0))

    response = await view.post(request, path="services/light/turn_on")
    assert response.status == 400
    assert response.text == "Invalid JSON"


@pytest.mark.asyncio
async def test_api_proxy_invalid_path():
    """Test le rejet d'un chemin d'URL non conforme ou hors services (400)[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={"entity_id": "light.salon"})

    # Chemin trop court ou ne commençant pas par 'services'[cite: 5]
    response = await view.post(request, path="invalid/path")
    assert response.status == 400
    assert response.text == "Invalid path"


@pytest.mark.asyncio
async def test_api_proxy_successful_service_call():
    """Test l'appel réussi d'un service Home Assistant via le proxy[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    hass = MagicMock()
    hass.services.async_call = AsyncMock()

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(
        return_value={"entity_id": "light.salon", "brightness": 255}
    )
    request.app = {"hass": hass}

    response = await view.post(request, path="services/light/turn_on")

    assert response.status == 200
    assert response.text == "OK"
    # Vérification que le service Home Assistant a bien été appelé avec les bons arguments[cite: 5]
    hass.services.async_call.assert_awaited_once_with(
        "light", "turn_on", {"entity_id": "light.salon", "brightness": 255}
    )


@pytest.mark.asyncio
async def test_api_proxy_internal_error():
    """Test la capture d'une exception interne lors de l'appel au service (500)[cite: 5]."""
    view = EedomusApiProxyView(
        entry_id="box_123", allowed_ips=["192.168.1.10"], disable_security=True
    )

    hass = MagicMock()
    # Simulation d'un crash lors de l'appel au service HASS
    hass.services.async_call = AsyncMock(side_effect=Exception("Service indisponible"))

    request = MagicMock()
    request.remote = "192.168.1.10"
    request.json = AsyncMock(return_value={})
    request.app = {"hass": hass}

    response = await view.post(request, path="services/switch/turn_off")
    assert response.status == 500
    assert response.text == "Internal error"
