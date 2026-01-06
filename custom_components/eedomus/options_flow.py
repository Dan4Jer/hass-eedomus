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
    CONF_ENABLE_EXTENDED_ATTRIBUTES,
    CONF_ENABLE_SET_VALUE_RETRY,
    DEFAULT_API_PROXY_DISABLE_SECURITY,
    DEFAULT_ENABLE_EXTENDED_ATTRIBUTES,
    DEFAULT_ENABLE_SET_VALUE_RETRY,
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
                        CONF_ENABLE_EXTENDED_ATTRIBUTES,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_EXTENDED_ATTRIBUTES,
                            self.config_entry.data.get(
                                CONF_ENABLE_EXTENDED_ATTRIBUTES,
                                DEFAULT_ENABLE_EXTENDED_ATTRIBUTES,
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
                }
            ),
            description_placeholders={
                "explanation": "📋 Configure advanced options for your eedomus integration. "
                "These options allow you to customize the behavior of the integration. "
                "Changes take effect immediately after saving."
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
