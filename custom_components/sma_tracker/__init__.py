"""The SMA Tracker (Yahoo Finance) integration."""
from __future__ import annotations

from datetime import time as dt_time
import functools
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NAME,
    CONF_NOTIFICATION_ENABLED,
    CONF_NOTIFICATION_MINIMAL,
    CONF_NOTIFICATION_SERVICE,
    CONF_NOTIFICATION_TIME,
    CONF_SCAN_INTERVAL,
    CONF_SMA_PERIOD,
    CONF_SYMBOL,
    DEFAULT_NOTIFICATION_MINIMAL,
    DEFAULT_NOTIFICATION_SERVICE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import SmaTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

# Debug switch: set to True locally to bypass the weekend skip below and
# test the notification flow immediately. Never commit this as True.
_DEBUG_IGNORE_WEEKEND = False

# Emoji/color thresholds mirror SmaTrackerSensor.icon in sensor.py.
_STATUS_EMOJI_RED = "\U0001F7E5"
_STATUS_EMOJI_YELLOW = "\U0001F7E8"
_STATUS_EMOJI_GREEN = "\U0001F7E9"
_STATUS_COLOR_RED = "#FF0000"
_STATUS_COLOR_YELLOW = "#FFFF00"
_STATUS_COLOR_GREEN = "#00FF00"

_TREND_ARROW_UP = "↑"
_TREND_ARROW_DOWN = "↓"
_TREND_ARROW_SIDEWAYS = "→"
# Day-over-day moves smaller than this are noise, not a trend.
_TREND_SIDEWAYS_THRESHOLD_PCT = 0.05

_SMA_SIDE_STORE_VERSION = 1


def _sma_side_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, bool]]:
    """Return the store remembering which side of the SMA an entry was last on.

    Persisting it lets a crossing that happened while Home Assistant was down
    still trigger a signal after the restart.
    """
    return Store(hass, _SMA_SIDE_STORE_VERSION, f"{DOMAIN}.{entry_id}.sma_side")


def _status_style(distance_pct: float) -> tuple[str, str]:
    """Return (emoji, color) for the distance-to-SMA thresholds."""
    if distance_pct <= 0:
        return _STATUS_EMOJI_RED, _STATUS_COLOR_RED
    if distance_pct < 2:
        return _STATUS_EMOJI_YELLOW, _STATUS_COLOR_YELLOW
    return _STATUS_EMOJI_GREEN, _STATUS_COLOR_GREEN


def _trend_arrow(current_price: float, reference_price: float) -> str:
    """Return an arrow comparing current_price to a reference price.

    The reference is normally the price from the last notification actually
    sent for this tracker, so the arrow reflects the move since then rather
    than a fixed calendar period.
    """
    if reference_price == 0:
        return _TREND_ARROW_SIDEWAYS
    change_pct = ((current_price - reference_price) / reference_price) * 100
    if abs(change_pct) < _TREND_SIDEWAYS_THRESHOLD_PCT:
        return _TREND_ARROW_SIDEWAYS
    return _TREND_ARROW_UP if change_pct > 0 else _TREND_ARROW_DOWN


def _price_lines(data: dict, sma_period: int) -> str:
    """Return the indented price and SMA lines shown below a notification header."""
    currency = data.get("currency", "")
    indent = "       "
    return (
        f"{indent}Kurs: {data['current_price']:.2f} {currency}\n"
        f"{indent}SMA{sma_period}: {data['sma_value']:.2f} {currency}"
    )


def _parse_notification_time(notification_time: str | dt_time) -> dt_time:
    if isinstance(notification_time, dt_time):
        return notification_time
    hour_str, minute_str, *_ = str(notification_time).split(":")
    return dt_time(hour=int(hour_str), minute=int(minute_str))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMA Tracker from a config entry."""
    symbol = entry.data[CONF_SYMBOL]
    sma_period = entry.options.get(CONF_SMA_PERIOD, entry.data[CONF_SMA_PERIOD])
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
            CONF_NOTIFICATION_MINIMAL: DEFAULT_NOTIFICATION_MINIMAL,
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

    # entry_id -> (sma_period, above). Kept in memory across reloads, so an
    # options change right after a cross can't read a store write that hasn't
    # been flushed yet.
    sma_side: dict[str, tuple[int, bool]] = hass.data.setdefault(f"{DOMAIN}_sma_side", {})
    side_store = _sma_side_store(hass, entry.entry_id)
    if entry.entry_id not in sma_side:
        stored_side = await side_store.async_load()
        if stored_side and "above" in stored_side:
            # Stores from before the period could be changed don't record it.
            sma_side[entry.entry_id] = (
                stored_side.get("sma_period", sma_period),
                stored_side["above"],
            )

    @callback
    def _async_check_sma_cross() -> None:
        """Send a buy/sell signal when the price crossed the SMA since the last update.

        The side is tracked even while notifications are off, so turning them
        on later doesn't fire a stale signal for an old crossing.
        """
        if not coordinator.last_update_success or coordinator.data is None:
            return
        # Same threshold as the red status: reaching 0 % counts as below.
        above = coordinator.data["distance_pct"] > 0
        previous = sma_side.get(entry.entry_id)
        if previous == (sma_period, above):
            return
        sma_side[entry.entry_id] = (sma_period, above)
        side_store.async_delay_save(lambda: {"above": above, "sma_period": sma_period})
        if previous is None or previous[0] != sma_period:
            # First reading for this entry or its new SMA period: the side
            # relative to another SMA is no crossing.
            return
        hass.async_create_task(
            _async_send_sma_cross_notification(hass, entry, coordinator, above)
        )

    @callback
    def _async_start_sma_cross_watch(_hass: HomeAssistant) -> None:
        # Wait for startup to finish so the notify service is registered
        # before a crossing that happened during downtime is reported.
        entry.async_on_unload(coordinator.async_add_listener(_async_check_sma_cross))
        _async_check_sma_cross()

    entry.async_on_unload(async_at_started(hass, _async_start_sma_cross_watch))

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
    sent_key = (dt_util.now().date().isoformat(), notification_at.hour, notification_at.minute)
    sent_today: set[tuple[str, int, int]] = hass.data.setdefault(
        f"{DOMAIN}_notified", set()
    )
    if sent_key in sent_today:
        return
    sent_today.add(sent_key)

    if dt_util.now().weekday() >= 5 and not _DEBUG_IGNORE_WEEKEND:
        return

    last_sent_price: dict[str, float] = hass.data.setdefault(f"{DOMAIN}_last_sent_price", {})

    blocks_by_service: dict[str, list[tuple[int, str, str, float]]] = {}
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
        display_name = (
            config_entry.options.get(CONF_NAME, config_entry.data.get(CONF_NAME)) or data["symbol"]
        )
        reference_price = last_sent_price.get(config_entry.entry_id, data["previous_close"])
        trend = _trend_arrow(data["current_price"], reference_price)
        emoji, color = _status_style(data["distance_pct"])
        minimal = config_entry.options.get(
            CONF_NOTIFICATION_MINIMAL,
            config_entry.data.get(CONF_NOTIFICATION_MINIMAL, DEFAULT_NOTIFICATION_MINIMAL),
        )

        header = (
            f"{emoji} <b>{display_name}</b>: "
            f'<b><font color="{color}">{trend} {data["distance_pct"]:+.2f} %</font></b>'
        )
        if minimal:
            block = header
        else:
            block = f"{header}\n{_price_lines(data, coordinator.sma_period)}"
        blocks_by_service.setdefault(service, []).append(
            (coordinator.sma_period, block, config_entry.entry_id, data["current_price"])
        )

    title = "SMA Tracker Übersicht"
    for service, items in blocks_by_service.items():
        domain, service_name = service.split(".", 1)
        sorted_items = sorted(items, key=lambda item: item[0])
        message = "\n\n".join(block for _, block, _, _ in sorted_items)
        try:
            await hass.services.async_call(
                domain,
                service_name,
                {
                    "message": message,
                    "title": title,
                    "data": {"html": True},
                },
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to send daily notification via %s: %s", service, err)
        else:
            for _, _, entry_id, current_price in sorted_items:
                last_sent_price[entry_id] = current_price


async def _async_send_sma_cross_notification(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: SmaTrackerCoordinator,
    above: bool,
) -> None:
    """Send a buy signal (crossed above the SMA) or sell signal (fell to/below it)."""
    enabled = entry.options.get(
        CONF_NOTIFICATION_ENABLED,
        entry.data.get(CONF_NOTIFICATION_ENABLED, False),
    )
    if not enabled:
        return

    service = entry.options.get(
        CONF_NOTIFICATION_SERVICE,
        entry.data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE),
    ).strip()
    if "." not in service:
        _LOGGER.warning("Invalid notification service for %s: %s", entry.entry_id, service)
        return

    data = coordinator.data
    display_name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME)) or data["symbol"]
    minimal = entry.options.get(
        CONF_NOTIFICATION_MINIMAL,
        entry.data.get(CONF_NOTIFICATION_MINIMAL, DEFAULT_NOTIFICATION_MINIMAL),
    )

    if above:
        title = "SMA Tracker Kaufsignal"
        emoji, color = _STATUS_EMOJI_GREEN, _STATUS_COLOR_GREEN
        crossing = f"über SMA{coordinator.sma_period} gestiegen"
    else:
        title = "SMA Tracker Verkaufssignal"
        emoji, color = _STATUS_EMOJI_RED, _STATUS_COLOR_RED
        crossing = f"auf/unter SMA{coordinator.sma_period} gefallen"

    message = (
        f"{emoji} <b>{display_name}</b> {crossing}: "
        f'<b><font color="{color}">{data["distance_pct"]:+.2f} %</font></b>'
    )
    if not minimal:
        message = f"{message}\n{_price_lines(data, coordinator.sma_period)}"

    domain, service_name = service.split(".", 1)
    try:
        await hass.services.async_call(
            domain,
            service_name,
            {
                "message": message,
                "title": title,
                "data": {"html": True},
            },
            blocking=True,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Failed to send SMA cross notification via %s: %s", service, err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored SMA side when the entry is removed."""
    hass.data.get(f"{DOMAIN}_sma_side", {}).pop(entry.entry_id, None)
    await _sma_side_store(hass, entry.entry_id).async_remove()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
