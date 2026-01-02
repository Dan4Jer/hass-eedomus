import json
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import (
    CONF_API_HOST,
    CONF_API_PROXY_DISABLE_SECURITY,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


## webhook
class EedomusWebhookView(HomeAssistantView):
    requires_auth = False
    url = "/api/eedomus/webhook"
    name = "api:eedomus:webhook"

    def __init__(
        self, entry_id: str, allowed_ips: list = None, disable_security: bool = False
    ):
        self.entry_id = entry_id
        self.allowed_ips = allowed_ips
        self.disable_security = disable_security

    async def post(self, request):
        client_ip = request.remote
        _LOGGER.debug(f"Request from {client_ip}")

        # Vérification de l'IP (unless security is disabled for debugging)
        if not self.disable_security and client_ip not in self.allowed_ips:
            _LOGGER.warning(f"Unauthorized IP: {client_ip}")
            return web.Response(text="Unauthorized", status=403)

        # Log warning if security is disabled
        if self.disable_security:
            _LOGGER.warning(
                f"SECURITY WARNING: IP validation disabled for debugging. Request from {client_ip}"
            )

        hass = request.app["hass"]
        try:
            # 1. Parse JSON first (fail fast if invalid)
            data = await request.json()
            if (
                data.get("action") != "refresh"
                and data.get("action") != "partial_refresh"
            ):
                return web.Response(text="Unrecognized action", status=400)

            # 2. Get coordinator safely
            domain_data = hass.data.get(DOMAIN, {})
            entry_data = domain_data.get(self.entry_id, {})
            coordinator = entry_data.get(COORDINATOR)

            if coordinator is None:
                _LOGGER.error("Coordinator not found for entry_id: %s", self.entry_id)
                return web.Response(text="Coordinator not available", status=500)

            # 3. Execute refresh
            _LOGGER.info("Triggering eedomus %s", data.get("action"))
            if data.get("action") == "refresh":
                await coordinator._async_full_refresh()
            if data.get("action") == "partial_refresh":
                await coordinator._async_partial_refresh()
            return web.Response(text="OK")

        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON", status=400)
        except Exception as e:
            _LOGGER.error("Webhook error: %s", str(e), exc_info=True)
            return web.Response(text="Internal error", status=500)
