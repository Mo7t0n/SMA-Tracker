"""The SMA Tracker (Yahoo Finance) integration."""
from __future__ import annotations

from datetime import time as dt_time
import functools
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

# Emoji thresholds mirror SmaTrackerSensor.rgb_color in sensor.py.
_STATUS_EMOJI_RED = "\U0001F534"
_STATUS_EMOJI_YELLOW = "\U0001F7E1"
_STATUS_EMOJI_GREEN = "\U0001F7E2"

_TREND_ARROW_UP = "↑"
_TREND_ARROW_DOWN = "↓"
_TREND_ARROW_SIDEWAYS = "→"
# Day-over-day moves smaller than this are noise, not a trend.
_TREND_SIDEWAYS_THRESHOLD_PCT = 0.05


def _status_emoji(distance_pct: float) -> str:
    if distance_pct <= 0:
        return _STATUS_EMOJI_RED
    if distance_pct < 2:
        return _STATUS_EMOJI_YELLOW
    return _STATUS_EMOJI_GREEN


def _trend_arrow(current_price: float, previous_close: float) -> str:
    if previous_close == 0:
        return _TREND_ARROW_SIDEWAYS
    change_pct = ((current_price - previous_close) / previous_close) * 100
    if abs(change_pct) < _TREND_SIDEWAYS_THRESHOLD_PCT:
        return _TREND_ARROW_SIDEWAYS
    return _TREND_ARROW_UP if change_pct > 0 else _TREND_ARROW_DOWN


def _parse_notification_time(notification_time: str | dt_time) -> dt_time:
    if isinstance(notification_time, dt_time):
        return notification_time
    hour_str, minute_str, *_ = str(notification_time).split(":")
    return dt_time(hour=int(hour_str), minute=int(minute_str))


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

    if notification_enabled:
        try:
            notification_at = _parse_notification_time(notification_time)
        except ValueError:
            _LOGGER.warning(
                "Invalid notification time for %s: %s",
                entry.entry_id,
                notification_time,
            )
        else:
            cancel = async_track_time_change(
                hass,
                functools.partial(_async_send_due_notifications, hass, notification_at),
                hour=notification_at.hour,
                minute=notification_at.minute,
            )
            entry.async_on_unload(cancel)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


@callback
async def _async_send_due_notifications(
    hass: HomeAssistant, notification_at: dt_time, now
) -> None:
    """Send one combined notification for all entries due at notification_at.

    Multiple config entries can share the same notification time, and each
    of them registers its own time trigger. A per-tick dedup guard ensures
    the combined message is only assembled and sent once per time slot,
    instead of once per entry.
    """
    if dt_util.now().weekday() >= 5:
        return

    sent_key = (dt_util.now().date().isoformat(), notification_at.hour, notification_at.minute)
    sent_today: set[tuple[str, int, int]] = hass.data.setdefault(
        f"{DOMAIN}_notified", set()
    )
    if sent_key in sent_today:
        return
    sent_today.add(sent_key)

    blocks_by_service: dict[str, list[str]] = {}
    for config_entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
        if not isinstance(coordinator, SmaTrackerCoordinator):
            continue
        if not coordinator.last_update_success or coordinator.data is None:
            continue

        enabled = config_entry.options.get(
            CONF_NOTIFICATION_ENABLED,
            config_entry.data.get(CONF_NOTIFICATION_ENABLED, False),
        )
        if not enabled:
            continue

        entry_time = config_entry.options.get(
            CONF_NOTIFICATION_TIME,
            config_entry.data.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME),
        )
        try:
            if _parse_notification_time(entry_time) != notification_at:
                continue
        except ValueError:
            continue

        service = config_entry.options.get(
            CONF_NOTIFICATION_SERVICE,
            config_entry.data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE),
        ).strip()
        if "." not in service:
            _LOGGER.warning(
                "Invalid notification service for %s: %s", config_entry.entry_id, service
            )
            continue

        data = coordinator.data
        display_name = config_entry.data.get(CONF_NAME) or data["symbol"]
        trend = _trend_arrow(data["current_price"], data["previous_close"])
        currency = data.get("currency", "")
        emoji = _status_emoji(data["distance_pct"])
        indent = "       "
        block = (
            f"{emoji} {display_name}: "
            f"{data['distance_pct']:+.2f} % {trend}\n"
            f"{indent}Kurs {data['current_price']:.2f} {currency}\n"
            f"{indent}SMA{coordinator.sma_period} {data['sma_value']:.2f} {currency}"
        )
        blocks_by_service.setdefault(service, []).append(block)

    title = "SMA Tracker Übersicht"
    for service, blocks in blocks_by_service.items():
        domain, service_name = service.split(".", 1)
        try:
            await hass.services.async_call(
                domain,
                service_name,
                {"message": "\n\n".join(blocks), "title": title},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to send daily notification via %s: %s", service, err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
