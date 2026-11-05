"""Sensor platform for the SMA Tracker integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CURRENCY,
    ATTR_CURRENT_PRICE,
    ATTR_SMA_PERIOD,
    ATTR_SMA_VALUE,
    ATTR_SYMBOL,
    CONF_NAME,
    CONF_SYMBOL,
    DOMAIN,
)
from .coordinator import SmaTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SMA Tracker sensor from a config entry."""
    coordinator: SmaTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensor = SmaTrackerSensor(coordinator, entry)

    # Changing the SMA period creates a new sensor; drop the one for the old period.
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.unique_id != sensor.unique_id:
            entity_registry.async_remove(entity_entry.entity_id)

    async_add_entities([sensor])


class SmaTrackerSensor(CoordinatorEntity[SmaTrackerCoordinator], SensorEntity):
    """Represents the percentage distance between price and SMA for one symbol."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = False

    def __init__(self, coordinator: SmaTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        symbol = entry.data[CONF_SYMBOL]
        sma_period = coordinator.sma_period
        display_name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME)) or symbol

        self._attr_name = f"{display_name} SMA{sma_period} Distance"
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
            ATTR_SMA_PERIOD: self.coordinator.sma_period,
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
