"""Options flow for eedomus integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_REMOVE_ENTITIES,
    CONF_SCAN_INTERVAL,
    DEFAULT_API_PROXY_DISABLE_SECURITY,
    DEFAULT_ENABLE_SET_VALUE_RETRY,
    DEFAULT_ENABLE_WEBHOOK,
    DEFAULT_REMOVE_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EedomusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle eedomus options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # OptionsFlow handles config_entry automatically, no need to set it
        pass
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlowHandler(config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_SET_VALUE_RETRY,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_SET_VALUE_RETRY,
                            self.config_entry.data.get(
                                CONF_ENABLE_SET_VALUE_RETRY,
                                DEFAULT_ENABLE_SET_VALUE_RETRY,
                            ),
                        ),
                    ): bool,

                    vol.Optional(
                        CONF_ENABLE_WEBHOOK,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_WEBHOOK,
                            self.config_entry.data.get(
                                CONF_ENABLE_WEBHOOK,
                                DEFAULT_ENABLE_WEBHOOK,
                            ),
                        ),
                    ): bool,

                    vol.Optional(
                        CONF_API_PROXY_DISABLE_SECURITY,
                        default=self.config_entry.options.get(
                            CONF_API_PROXY_DISABLE_SECURITY,
                            self.config_entry.data.get(
                                CONF_API_PROXY_DISABLE_SECURITY,
                                DEFAULT_API_PROXY_DISABLE_SECURITY,
                            ),
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL,
                                DEFAULT_SCAN_INTERVAL,
                            ),
                        ),
                    ): int,
                    vol.Optional(
                        CONF_REMOVE_ENTITIES,
                        default=self.config_entry.options.get(
                            CONF_REMOVE_ENTITIES,
                            self.config_entry.data.get(
                                CONF_REMOVE_ENTITIES,
                                DEFAULT_REMOVE_ENTITIES,
                            ),
                        ),
                    ): bool,
                }
            ),
            description_placeholders={
                "explanation": "📋 Configure advanced options for your eedomus integration. "
                "These options allow you to customize the behavior of the integration. "
                "Changes take effect immediately after saving.",
                "scan_interval_note": "Scan interval in seconds (minimum 30 seconds recommended)",
                "remove_entities_note": "⚠️ WARNING: This option will remove all entities associated with this integration when the integration is removed. "
                "This action cannot be undone. Make sure you have a backup of your configuration."
            },
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage advanced options (future expansion)."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional("max_retries", default=3): int,
                }
            ),
        )
