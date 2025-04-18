"""Create ABB-free@home event entities."""

from typing import Any

from abbfreeathome.devices.blind_sensor import BlindSensor, BlindSensorState
from abbfreeathome.devices.des_door_ringing_sensor import DesDoorRingingSensor
from abbfreeathome.devices.force_on_off_sensor import (
    ForceOnOffSensor,
    ForceOnOffSensorState,
)
from abbfreeathome.devices.switch_sensor import (
    DimmingSensor,
    DimmingSensorState,
    SwitchSensor,
    SwitchSensorState,
)
from abbfreeathome.devices.virtual.virtual_switch_actuator import VirtualSwitchActuator
from abbfreeathome.freeathome import FreeAtHome

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERIAL, DOMAIN

EVENT_DESCRIPTIONS = {
    "EventBlindSensorState": {
        "device_class": BlindSensor,
        "event_type_callback": lambda state: state,
        "state_attribute": "state",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": [state.name for state in BlindSensorState],
            "translation_key": "blind_sensor",
        },
    },
    "EventDesDoorRingingSensorActivated": {
        "device_class": DesDoorRingingSensor,
        "event_type_callback": lambda: "activated",
        "state_attribute": "",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": ["activated"],
            "translation_key": "des_door_ringing_sensor",
        },
    },
    "EventDimmingSensorState": {
        "device_class": DimmingSensor,
        "event_type_callback": lambda state: state,
        "state_attribute": "state",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": list(
                set(
                    [state.name for state in SwitchSensorState]
                    + [state.name for state in DimmingSensorState]
                )
            ),
            "translation_key": "dimming_sensor",
        },
    },
    "EventForceOnOffSensorOnOff": {
        "device_class": ForceOnOffSensor,
        "event_type_callback": lambda state: state,
        "state_attribute": "state",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": [state.name for state in ForceOnOffSensorState],
            "translation_key": "force_on_off_sensor",
        },
    },
    "EventSwitchSensorOnOff": {
        "device_class": SwitchSensor,
        "event_type_callback": lambda state: state,
        "state_attribute": "state",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": [state.name for state in SwitchSensorState],
            "translation_key": "switch_sensor",
        },
    },
    "EventVirtualSwitchActuatorOnOff": {
        "device_class": VirtualSwitchActuator,
        "event_type_callback": lambda requested_state: "On"
        if requested_state
        else "Off",
        "state_attribute": "requested_state",
        "entity_description_kwargs": {
            "device_class": EventDeviceClass.BUTTON,
            "event_types": ["On", "Off"],
            "translation_key": "virtual_switch_actuator_onoff",
        },
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    free_at_home: FreeAtHome = hass.data[DOMAIN][entry.entry_id]

    for key, description in EVENT_DESCRIPTIONS.items():
        async_add_entities(
            FreeAtHomeEventEntity(
                device,
                state_attribute=description.get("state_attribute"),
                entity_description_kwargs={"key": key}
                | description.get("entity_description_kwargs"),
                sysap_serial_number=entry.data[CONF_SERIAL],
                event_type_callback=description.get("event_type_callback"),
            )
            for device in free_at_home.get_devices_by_class(
                device_class=description.get("device_class")
            )
        )


class FreeAtHomeEventEntity(EventEntity):
    """free@home Event Entity."""

    def __init__(
        self,
        device: BlindSensor
        | DesDoorRingingSensor
        | DimmingSensor
        | ForceOnOffSensor
        | SwitchSensor
        | VirtualSwitchActuator,
        state_attribute: str,
        entity_description_kwargs: dict[str:Any],
        sysap_serial_number: str,
        event_type_callback: callback,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._device = device
        self._state_attribute = state_attribute
        self._sysap_serial_number = sysap_serial_number
        self._event_type_callback = event_type_callback

        self.entity_description = EventEntityDescription(
            has_entity_name=True,
            name=device.channel_name,
            translation_placeholders={"channel_id": device.channel_id},
            **entity_description_kwargs,
        )

    @callback
    def _async_handle_event(self) -> None:
        """Handle the demo button event."""

        if hasattr(self._device, self._state_attribute):
            event_type = self._event_type_callback(
                getattr(self._device, self._state_attribute)
            )
        else:
            event_type = self._event_type_callback()

        self._trigger_event(event_type)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Entity being added to hass."""
        if len(self._state_attribute) > 0:
            self._device.register_callback(
                callback_attribute=self._state_attribute,
                callback=self._async_handle_event,
            )
        else:
            self._device.register_callback(
                callback_attribute="state", callback=self._async_handle_event
            )

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        if len(self._state_attribute) > 0:
            self._device.remove_callback(
                callback_attribute=self._state_attribute,
                callback=self._async_handle_event,
            )
        else:
            self._device.remove_callback(
                callback_attribute="state", callback=self._async_handle_event
            )

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
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self._device.device_id}_{self._device.channel_id}_{self.entity_description.key}"
