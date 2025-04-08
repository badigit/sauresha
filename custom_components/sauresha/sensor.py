import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN, COORDINATOR, CONTROLLERS
from .entity.base_entity import SauresControllerSensor
from .entity.sensor_entity import SauresSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Saures sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Собираем все сенсоры (и счетчики, и статусы контроллеров)
    entities_to_add = []

    if coordinator.data:  # Убедимся, что данные загружены
        # 1. Создаем сенсоры состояния для каждого контроллера
        for flat_id, controllers_in_flat in coordinator.data.get(CONTROLLERS, {}).items():
            for controller_sn, controller_data in controllers_in_flat.items():
                if controller_data:  # Проверка на пустые данные
                    _LOGGER.debug("Setting up Controller Sensor for SN: %s in flat %s", controller_sn, flat_id)
                    entities_to_add.append(
                        SauresControllerSensor(
                            coordinator=coordinator,
                            flat_id=flat_id,
                            controller_sn=controller_sn,
                            controller_data=controller_data,  # Передаем начальные данные
                        )
                    )
                else:
                    _LOGGER.warning("No data found for controller %s in flat %s during setup.", controller_sn, flat_id)

        # 2. Создаем сенсоры для счетчиков (воды, газа, температуры и т.д.)
        for flat_id, sensors_in_flat in coordinator.data.get("sensors", {}).items():
            for meter_id, meter_data in sensors_in_flat.items():
                controller_sn = meter_data.get("controller_sn")
                if controller_sn and meter_data:  # Проверяем наличие controller_sn и данных
                    _LOGGER.debug(
                        "Setting up Sensor for Meter ID: %s (Controller: %s) in flat %s", meter_id, controller_sn, flat_id
                    )
                    entities_to_add.append(
                        SauresSensor(
                            coordinator=coordinator,
                            flat_id=flat_id,
                            meter_id=meter_id,
                            controller_sn=controller_sn,
                            meter_data=meter_data,  # Передаем начальные данные
                        )
                    )
                else:
                    _LOGGER.warning("Sensor %s in flat %s is missing controller_sn or data.", meter_id, flat_id)

    else:
        _LOGGER.warning("Coordinator data is empty, skipping sensor setup.")

    # Добавляем все собранные сущности
    if entities_to_add:
        _LOGGER.info("Adding %d Saures sensor entities.", len(entities_to_add))
        async_add_entities(entities_to_add)
    else:
        _LOGGER.info("No Saures sensor entities to add.")
