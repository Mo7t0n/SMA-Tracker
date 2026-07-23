"""Data update coordinator for the SMA Tracker integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import YAHOO_CHART_URL, YAHOO_INTERVAL, YAHOO_RANGE

_LOGGER = logging.getLogger(__name__)

_HEADERS = {
    # Yahoo's chart endpoint occasionally rejects requests without a
    # browser-like User-Agent header.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


class SmaTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches Yahoo Finance data for one symbol and computes the SMA distance."""

    def __init__(
        self,
        hass: HomeAssistant,
        symbol: str,
        sma_period: int,
        scan_interval_minutes: int,
    ) -> None:
        self.symbol = symbol
        self.sma_period = sma_period
        super().__init__(
            hass,
            _LOGGER,
            name=f"sma_tracker_{symbol}",
            update_interval=timedelta(minutes=scan_interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        url = YAHOO_CHART_URL.format(symbol=self.symbol)
        params = {
            "range": YAHOO_RANGE,
            "interval": YAHOO_INTERVAL,
            "includePrePost": "false",
        }

        try:
            async with session.get(
                url,
                params=params,
                headers=_HEADERS,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"Yahoo Finance returned HTTP {resp.status} for '{self.symbol}'"
                    )
                payload = await resp.json(content_type=None)
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error contacting Yahoo Finance for '{self.symbol}': {err}") from err

        try:
            result = payload["chart"]["result"][0]
            meta = result["meta"]
            closes = result["indicators"]["quote"][0]["close"]
        except (KeyError, IndexError, TypeError) as err:
            raise UpdateFailed(
                f"Unexpected Yahoo Finance response format for '{self.symbol}': {err}"
            ) from err

        closes = [c for c in closes if c is not None]

        if len(closes) < self.sma_period:
            raise UpdateFailed(
                f"Not enough historical data for '{self.symbol}': got {len(closes)} "
                f"candles, need at least {self.sma_period} for the configured SMA period"
            )

        sma_window = closes[-self.sma_period :]
        sma_value = sum(sma_window) / len(sma_window)

        current_price = meta.get("regularMarketPrice")
        if current_price is None:
            current_price = closes[-1]

        if sma_value == 0:
            raise UpdateFailed(f"SMA value for '{self.symbol}' is 0, cannot calculate distance")

        distance_pct = ((current_price - sma_value) / sma_value) * 100

        return {
            "current_price": round(float(current_price), 4),
            "sma_value": round(float(sma_value), 4),
            "distance_pct": round(float(distance_pct), 2),
            "currency": meta.get("currency"),
            "symbol": self.symbol,
        }
