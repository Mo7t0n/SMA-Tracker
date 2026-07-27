"""Config flow for the SMA Tracker (Yahoo Finance) integration."""
from __future__ import annotations

from datetime import time as dt_time
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_NAME,
    CONF_NOTIFICATION_ENABLED,
    CONF_NOTIFICATION_SERVICE,
    CONF_NOTIFICATION_TIME,
    CONF_SCAN_INTERVAL,
    CONF_SMA_PERIOD,
    CONF_SYMBOL,
    DEFAULT_NOTIFICATION_SERVICE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SMA_PERIOD,
    DOMAIN,
)


class SmaTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of one SMA tracker (one symbol)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            symbol = user_input[CONF_SYMBOL].strip().upper()
            sma_period = user_input[CONF_SMA_PERIOD]

            await self.async_set_unique_id(f"{symbol}_{sma_period}")
            self._abort_if_unique_id_configured()

            notification_time = user_input.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME)
            if isinstance(notification_time, dt_time):
                notification_time = notification_time.strftime("%H:%M")

            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or symbol,
                data={
                    CONF_SYMBOL: symbol,
                    CONF_NAME: user_input.get(CONF_NAME, ""),
                    CONF_SMA_PERIOD: sma_period,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_NOTIFICATION_ENABLED: user_input.get(CONF_NOTIFICATION_ENABLED, False),
                    CONF_NOTIFICATION_TIME: notification_time,
                    CONF_NOTIFICATION_SERVICE: user_input.get(
                        CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE
                    ).strip(),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SYMBOL): str,
                vol.Optional(CONF_NAME, default=""): str,
                vol.Required(CONF_SMA_PERIOD, default=DEFAULT_SMA_PERIOD): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=500)
                ),
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=1440)
                ),
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
                vol.Optional(CONF_NOTIFICATION_TIME, default=DEFAULT_NOTIFICATION_TIME): cv.time,
                vol.Optional(
                    CONF_NOTIFICATION_SERVICE,
                    default=DEFAULT_NOTIFICATION_SERVICE,
                ): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmaTrackerOptionsFlow:
        """Return the options flow."""
        return SmaTrackerOptionsFlow()


class SmaTrackerOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the polling interval after setup."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the options flow."""
        if user_input is not None:
            notification_time = user_input.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME)
            if isinstance(notification_time, dt_time):
                notification_time = notification_time.strftime("%H:%M")
            user_input[CONF_NOTIFICATION_TIME] = notification_time
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_notification_enabled = self.config_entry.options.get(
            CONF_NOTIFICATION_ENABLED,
            self.config_entry.data.get(CONF_NOTIFICATION_ENABLED, False),
        )
        current_notification_time = self.config_entry.options.get(
            CONF_NOTIFICATION_TIME,
            self.config_entry.data.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME),
        )
        current_notification_service = self.config_entry.options.get(
            CONF_NOTIFICATION_SERVICE,
            self.config_entry.data.get(
                CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE
            ),
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_NOTIFICATION_ENABLED,
                    default=current_notification_enabled,
                ): bool,
                vol.Optional(
                    CONF_NOTIFICATION_TIME,
                    default=current_notification_time,
                ): cv.time,
                vol.Optional(
                    CONF_NOTIFICATION_SERVICE,
                    default=current_notification_service,
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
