import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN, COORDINATOR
from .entity.binary_sensor_entity import SauresBinarySensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Saures binary sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    entities_to_add = []

    if coordinator.data:
        for flat_id, sensors_in_flat in coordinator.data.get("binary_sensors", {}).items():
            for meter_id, meter_data in sensors_in_flat.items():
                controller_sn = meter_data.get("controller_sn")
                if controller_sn and meter_data:
                    _LOGGER.debug(
                        "Setting up Binary Sensor for Meter ID: %s (Controller: %s) in flat %s", meter_id, controller_sn, flat_id
                    )
                    entities_to_add.append(
                        SauresBinarySensor(
                            coordinator=coordinator,
                            flat_id=flat_id,
                            meter_id=meter_id,
                            controller_sn=controller_sn,
                            meter_data=meter_data,
                        )
                    )
                else:
                    _LOGGER.warning("Binary Sensor %s in flat %s is missing controller_sn or data.", meter_id, flat_id)
    else:
        _LOGGER.warning("Coordinator data is empty, skipping binary_sensor setup.")

    if entities_to_add:
        _LOGGER.info("Adding %d Saures binary sensor entities.", len(entities_to_add))
        async_add_entities(entities_to_add)
    else:
        _LOGGER.info("No Saures binary sensor entities to add.")
