"""Create ABB-free@home number entities."""

from typing import Any

from abbfreeathome.devices.temperature_sensor import VirtualTemperatureSensor
from abbfreeathome.freeathome import FreeAtHome

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERIAL, DOMAIN

NUMBER_DESCRIPTIONS = {
    "VirtualTemperatureSensorTemperature": {
        "device_class": VirtualTemperatureSensor,
        "value_attribute": "state",
        "entity_description_kwargs": {
            "device_class": NumberDeviceClass.TEMPERATURE,
            "mode": NumberMode.AUTO,
            "native_max_value": 100,
            "native_min_value": -100,
            "native_step": 0.01,
            "native_unit_of_measurement": "°C",
        },
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up numbers."""
    free_at_home: FreeAtHome = hass.data[DOMAIN][entry.entry_id]

    for key, description in NUMBER_DESCRIPTIONS.items():
        async_add_entities(
            FreeAtHomeNumberEntity(
                device,
                value_attribute=description.get("value_attribute"),
                entity_description_kwargs={"key": key}
                | description.get("entity_description_kwargs"),
                sysap_serial_number=entry.data[CONF_SERIAL],
            )
            for device in free_at_home.get_devices_by_class(
                device_class=description.get("device_class")
            )
            if getattr(device, description.get("value_attribute")) is not None
        )


class FreeAtHomeNumberEntity(NumberEntity):
    """Defines a free@home number entity."""

    _attr_should_poll: bool = False

    def __init__(
        self,
        device: VirtualTemperatureSensor,
        value_attribute: str,
        entity_description_kwargs: dict[str:Any],
        sysap_serial_number: str,
    ) -> None:
        """Initialize the number."""
        super().__init__()
        self._device = device
        self._value_attribute = value_attribute
        self._sysap_serial_number = sysap_serial_number

        self.entity_description = NumberEntityDescription(
            has_entity_name=True,
            name=device.channel_name,
            translation_placeholders={
                "channel_id": device.channel_id,
                "channel_name": device.channel_name,
            },
            native_value=getattr**entity_description_kwargs,
        )

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._device.remove_callback(self.async_write_ha_state)

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._device.device_id)},
            "name": self._device.device_name,
            "manufacturer": "ABB busch-jaeger",
            "serial_number": self._device.device_id,
            "suggested_area": self._device.room_name,
            "via_device": (DOMAIN, self._sysap_serial_number),
        }

    @property
    def native_value(self) -> float | None:
        """Return state of the sensor."""
        return getattr(self._device, self._value_attribute)

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self._device.device_id}_{self._device.channel_id}_{self.entity_description.key}"

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value."""
        await self._device.set_value(value)
