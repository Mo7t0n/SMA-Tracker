"""The SMA Tracker (Yahoo Finance) integration."""
from __future__ import annotations

from datetime import time as dt_time
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

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
    DOMAIN,
)
from .coordinator import SmaTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMA Tracker from a config entry."""
    symbol = entry.data[CONF_SYMBOL]
    sma_period = entry.data[CONF_SMA_PERIOD]
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    coordinator = SmaTrackerCoordinator(hass, symbol, sma_period, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    if (
        CONF_NOTIFICATION_ENABLED not in entry.options
        and CONF_NOTIFICATION_ENABLED not in entry.data
    ):
        new_options = {
            **entry.options,
            CONF_NOTIFICATION_ENABLED: False,
            CONF_NOTIFICATION_TIME: DEFAULT_NOTIFICATION_TIME,
            CONF_NOTIFICATION_SERVICE: DEFAULT_NOTIFICATION_SERVICE,
        }
        hass.config_entries.async_update_entry(entry, options=new_options)

    notification_enabled = entry.options.get(
        CONF_NOTIFICATION_ENABLED,
        entry.data.get(CONF_NOTIFICATION_ENABLED, False),
    )
    notification_time = entry.options.get(
        CONF_NOTIFICATION_TIME,
        entry.data.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME),
    )
    notification_service = entry.options.get(
        CONF_NOTIFICATION_SERVICE,
        entry.data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE),
    ).strip()

    if notification_enabled:
        try:
            if isinstance(notification_time, str):
                hour, minute = map(int, notification_time.split(":"))
            elif isinstance(notification_time, dt_time):
                hour = notification_time.hour
                minute = notification_time.minute
            else:
                raise ValueError("notification_time must be a time string or time object")

            notification_at = dt_time(hour=hour, minute=minute)
        except ValueError:
            _LOGGER.warning(
                "Invalid notification time for %s: %s",
                entry.entry_id,
                notification_time,
            )
        else:
            @callback
            async def _send_daily_notification(now):
                if dt_util.now().weekday() >= 5:
                    return

                trackers = [
                    value
                    for value in hass.data.get(DOMAIN, {}).values()
                    if isinstance(value, SmaTrackerCoordinator)
                ]
                if not trackers:
                    return

                lines: list[str] = []
                for tracker in trackers:
                    if not tracker.last_update_success or tracker.data is None:
                        continue
                    data = tracker.data
                    entry_title = entry.data.get(CONF_NAME) or data["symbol"]
                    lines.append(
                        f"{entry_title}: {data['distance_pct']} % | "
                        f"Kurs {data['current_price']} {data.get('currency','')} | "
                        f"SMA{tracker.sma_period} {data['sma_value']}"
                    )

                if not lines:
                    return

                if "." not in notification_service:
                    _LOGGER.warning(
                        "Invalid notification service for %s: %s",
                        entry.entry_id,
                        notification_service,
                    )
                    return

                domain, service_name = notification_service.split(".", 1)
                message = "\n".join(lines)
                title = "SMA Tracker Übersicht"

                try:
                    await hass.services.async_call(
                        domain,
                        service_name,
                        {"message": message, "title": title},
                        blocking=True,
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.exception(
                        "Failed to send daily notification for %s: %s",
                        entry.entry_id,
                        err,
                    )

            cancel = async_track_time_change(
                hass,
                _send_daily_notification,
                hour=notification_at.hour,
                minute=notification_at.minute,
            )
            entry.async_on_unload(cancel)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
