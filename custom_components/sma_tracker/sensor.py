"""Sensor platform for the SMA Tracker integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CURRENCY,
    ATTR_CURRENT_PRICE,
    ATTR_SMA_PERIOD,
    ATTR_SMA_VALUE,
    ATTR_SYMBOL,
    CONF_NAME,
    CONF_SMA_PERIOD,
    CONF_SYMBOL,
    DOMAIN,
)
from .coordinator import SmaTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SMA Tracker sensor from a config entry."""
    coordinator: SmaTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmaTrackerSensor(coordinator, entry)])


class SmaTrackerSensor(CoordinatorEntity[SmaTrackerCoordinator], SensorEntity):
    """Represents the percentage distance between price and SMA for one symbol."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = False

    def __init__(self, coordinator: SmaTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        symbol = entry.data[CONF_SYMBOL]
        sma_period = entry.data[CONF_SMA_PERIOD]
        display_name = entry.data.get(CONF_NAME) or symbol

        self._attr_name = f"{display_name} SMA{sma_period} Abstand"
        self._attr_unique_id = f"{DOMAIN}_{symbol}_{sma_period}"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data["distance_pct"]

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data
        return {
            ATTR_CURRENT_PRICE: data["current_price"],
            ATTR_SMA_VALUE: data["sma_value"],
            ATTR_SYMBOL: data["symbol"],
            ATTR_SMA_PERIOD: self._entry.data[CONF_SMA_PERIOD],
            ATTR_CURRENCY: data.get("currency"),
        }

    @property
    def icon(self) -> str:
        value = self.native_value
        if value is None:
            return "mdi:chart-line"
        if value <= 0:
            return "mdi:arrow-down-bold-circle"
        if value < 2:
            return "mdi:arrow-right-bold-circle"
        return "mdi:arrow-up-bold-circle"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB color based on distance percentage.
        
        Green: > 2%
        Yellow: >= 0% and < 2%
        Red: < 0%
        """
        value = self.native_value
        if value is None:
            return None

        if value <= 0:
            # Red: unter oder gleich 0%
            return (255, 0, 0)
        elif value < 2:
            # Yellow: 0% bis 2%
            return (255, 255, 0)
        else:
            # Green: über 2%
            return (0, 255, 0)
