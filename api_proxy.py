import logging
import json
from aiohttp import web
from .const import DOMAIN, PLATFORMS, COORDINATOR, CONF_API_HOST, CONF_API_PROXY_DISABLE_SECURITY
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)

class EedomusApiProxyView(HomeAssistantView):
    requires_auth = False
    url = "/api/eedomus/apiproxy/{path:.+}"
    name = "api:eedomus:apiproxy"

    def __init__(self, entry_id: str, allowed_ips: list = None, disable_security: bool = False):
        self.entry_id = entry_id
        self.allowed_ips = allowed_ips or []
        self.disable_security = disable_security

    async def post(self, request, path: str):  # Ajoutez le paramètre path ici
        client_ip = request.remote
        _LOGGER.debug(f"Request from {client_ip}")

        # Vérification de l'IP (unless security is disabled for debugging)
        if not self.disable_security and client_ip not in self.allowed_ips:
            _LOGGER.warning(f"Unauthorized IP: {client_ip}")
            return web.Response(text="Unauthorized", status=403)
        
        # Log warning if security is disabled
        if self.disable_security:
            _LOGGER.warning(f"SECURITY WARNING: IP validation disabled for debugging. Request from {client_ip}")

        hass = request.app["hass"]
        try:
            # 1. Parse JSON
            data = await request.json()

            # 2. Extract domain and service from path (e.g., "services/light/turn_on")
            parts = path.split("/")
            if len(parts) < 3 or parts[0] != "services":
                return web.Response(text="Invalid path", status=400)

            domain = parts[1]
            service = parts[2]

            # 3. Call the Home Assistant service
            await hass.services.async_call(domain, service, data)

            _LOGGER.info(f"Service {domain}.{service} called with data: {data}")

            return web.Response(text="OK")

        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON", status=400)
        except Exception as e:
            _LOGGER.error("Webhook error: %s", str(e), exc_info=True)
            return web.Response(text="Internal error", status=500)
