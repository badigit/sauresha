import logging

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import slugify

from ..const import (
    ATTR_CONTROLLER_BATTERY,
    ATTR_CONTROLLER_NAME,
    ATTR_CONTROLLER_MODEL,
    ATTR_CONTROLLER_HARDWARE,
    ATTR_CONTROLLER_FIRMWARE,
    ATTR_CONTROLLER_NEW_FIRMWARE,
    ATTR_CONTROLLER_SSID,
    ATTR_CONTROLLER_LOCAL_IP,
    ATTR_CONTROLLER_ACTIVE,
    ATTR_CONTROLLER_CHECK_HOURS,
    ATTR_CONTROLLER_LIC_CHANNELS,
    ATTR_CONTROLLER_CHECK_PERIOD_DISPLAY,
    ATTR_CONTROLLER_CAP_STATE,
    ATTR_CONTROLLER_EMPTY_INPUTS,
    ATTR_CONTROLLER_LAST_CONNECTION_WARNING,
    ATTR_CONTROLLER_LAST_CONNECTION,
    ATTR_CONTROLLER_LOG_PERIOD,
    ATTR_CONTROLLER_POWER_SUPPLY,
    ATTR_CONTROLLER_READOUT_DT,
    ATTR_CONTROLLER_REQUEST_DT,
    ATTR_CONTROLLER_REQUESTS,
    ATTR_CONTROLLER_RSSI,
    ATTR_CONTROLLER_SCAN_PERIOD,
    ATTR_CONTROLLER_SEND_PERIOD,
    ATTR_CONTROLLER_SN,
    ATTR_CONTROLLER_VOL_THRESHOLD,
    CONTROLLERS,
    DOMAIN,
    NAME as BRAND_NAME,  # Используем имя интеграции как бренд
)

_LOGGER = logging.getLogger(__name__)


class SauresBaseEntity(CoordinatorEntity):
    """Base class for Saures entities (Sensors, BinarySensors, Switches)."""

    # Делаем _attr_has_entity_name = True, чтобы HA сам генерировал имя на основе device name + entity name key
    # Либо оставляем False и генерируем полное имя в @property name(self)
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        flat_id: str,
        meter_id: str,  # Уникальный ID счетчика
        controller_sn: str,  # SN контроллера, к которому подключен счетчик
        meter_data: dict,  # Начальные данные для счетчика
        entity_key_prefix: str,  # Префикс для unique_id (напр. "sensor", "switch")
    ) -> None:
        """Initialize the base Saures entity."""
        super().__init__(coordinator)
        self.flat_id = flat_id
        self.meter_id = meter_id
        self.controller_sn = controller_sn
        self._meter_data = meter_data  # Сохраняем начальные данные

        # Уникальный ID сущности
        self._attr_unique_id = slugify(f"sauresha_{entity_key_prefix}_{flat_id}_{meter_id}")

        # Информация об устройстве (контроллере), к которому привязана сущность
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.controller_sn)},  # Уникальный идентификатор контроллера
            # Остальные поля device_info будут заполнены в SauresControllerSensor
        )
        # Мы не устанавливаем state и attributes здесь, это делает _handle_coordinator_update

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        # Берем имя из данных счетчика, если нет - генерируем
        meter_name = self._meter_data.get("meter_name", f"Meter {self.meter_id}")
        # Можно добавить префикс/постфикс если нужно
        return meter_name  # Используем meter_name напрямую как имя сущности

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Доступность зависит от доступности координатора и наличия данных для этого счетчика
        meter_key = self._get_meter_key()  # Получаем ключ для поиска в coordinator.data
        return (
            super().available  # Проверка доступности координатора
            and self.coordinator.data is not None
            and self.flat_id in self.coordinator.data.get(meter_key, {})
            and self.meter_id in self.coordinator.data[meter_key][self.flat_id]
        )

    def _get_meter_key(self) -> str:
        """Returns the key ('sensors', 'binary_sensors', 'switches') for this entity type."""
        # Должен быть переопределен в дочерних классах
        raise NotImplementedError

    def _update_state_and_attrs(self, meter_data: dict):
        """Updates entity state and attributes from new meter data. Must be implemented by subclasses."""
        # Обновляем кеш данных
        self._meter_data = meter_data
        # Логика обновления _attr_native_value, _attr_is_on, _attr_extra_state_attributes
        raise NotImplementedError

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        meter_key = self._get_meter_key()
        try:
            if (
                self.coordinator.data is not None
                and self.flat_id in self.coordinator.data.get(meter_key, {})
                and self.meter_id in self.coordinator.data[meter_key][self.flat_id]
            ):
                new_meter_data = self.coordinator.data[meter_key][self.flat_id][self.meter_id]
                self._update_state_and_attrs(new_meter_data)
                self.async_write_ha_state()  # Сообщаем HA об обновлении
            else:
                # Если данных нет, можно пометить как недоступный, но available() уже это делает
                _LOGGER.debug("No data for %s %s in flat %s in coordinator update", meter_key, self.meter_id, self.flat_id)

        except Exception as e:
            _LOGGER.error("Error handling coordinator update for %s: %s", self.unique_id, e, exc_info=True)


class SauresControllerSensor(CoordinatorEntity):
    """Representation of a Controller as a Sensor entity for monitoring its status."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        flat_id: str,
        controller_sn: str,
        controller_data: dict,
    ) -> None:
        """Initialize the controller sensor."""
        super().__init__(coordinator)
        self.flat_id = flat_id
        self.controller_sn = controller_sn
        self._controller_data = controller_data

        self._attr_name = f"Controller {controller_sn} Status"
        self._attr_unique_id = slugify(f"sauresha_controller_status_{flat_id}_{controller_sn}")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.controller_sn)},
            name=f"Saures Controller {self.controller_sn}",
            manufacturer=BRAND_NAME,
            # Используем 'model' из API для поля модели
            model=controller_data.get(ATTR_CONTROLLER_MODEL),
            sw_version=controller_data.get(ATTR_CONTROLLER_FIRMWARE),
            # Можно добавить hw_version если нужно, используя ATTR_CONTROLLER_HARDWARE
            # hw_version=controller_data.get(ATTR_CONTROLLER_HARDWARE),
        )

        # Устанавливаем начальное состояние и атрибуты
        self._update_state_and_attrs(controller_data)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.flat_id in self.coordinator.data.get(CONTROLLERS, {})
            and self.controller_sn in self.coordinator.data[CONTROLLERS][self.flat_id]
        )

    @property
    def icon(self) -> str:
        """Return the icon of the controller sensor."""
        return "mdi:lan-connect" if self._attr_native_value == "online" else "mdi:lan-disconnect"

    def _update_state_and_attrs(self, controller_data: dict):
        """Update state and attributes from new controller data."""
        self._controller_data = controller_data  # Обновляем кеш
        _LOGGER.debug("[%s Status] Updating state. Raw controller data: %s", self.controller_sn, controller_data)  # <-- Лог 1

        # --- Логика определения состояния online/offline ---
        last_warning = controller_data.get(ATTR_CONTROLLER_LAST_CONNECTION_WARNING)
        _LOGGER.debug(
            "[%s Status] last_connection_warning value: %s (type: %s)", self.controller_sn, last_warning, type(last_warning)
        )

        if last_warning is None:
            self._attr_native_value = "online"
        else:
            self._attr_native_value = "offline"
            # Можно было бы присвоить сам текст ошибки в state, но стандартно использовать online/offline
            # self._attr_native_value = last_warning

        # --- Обновляем атрибуты ---
        attributes = {
            ATTR_CONTROLLER_MODEL: controller_data.get(ATTR_CONTROLLER_MODEL),
            "controller_name": controller_data.get(ATTR_CONTROLLER_NAME),
            ATTR_CONTROLLER_SN: self.controller_sn,
            ATTR_CONTROLLER_HARDWARE: controller_data.get(ATTR_CONTROLLER_HARDWARE),
            ATTR_CONTROLLER_FIRMWARE: controller_data.get(ATTR_CONTROLLER_FIRMWARE),
            ATTR_CONTROLLER_NEW_FIRMWARE: controller_data.get(ATTR_CONTROLLER_NEW_FIRMWARE),
            ATTR_CONTROLLER_SSID: controller_data.get(ATTR_CONTROLLER_SSID),  # Используем константу
            ATTR_CONTROLLER_LOCAL_IP: controller_data.get(ATTR_CONTROLLER_LOCAL_IP),
            ATTR_BATTERY_LEVEL: controller_data.get(ATTR_CONTROLLER_BATTERY),
            ATTR_CONTROLLER_RSSI: controller_data.get(ATTR_CONTROLLER_RSSI),
            ATTR_CONTROLLER_LAST_CONNECTION: controller_data.get(ATTR_CONTROLLER_LAST_CONNECTION),
            ATTR_CONTROLLER_LAST_CONNECTION_WARNING: last_warning,
            ATTR_CONTROLLER_REQUEST_DT: controller_data.get(ATTR_CONTROLLER_REQUEST_DT),
            ATTR_CONTROLLER_READOUT_DT: controller_data.get(ATTR_CONTROLLER_READOUT_DT),
            ATTR_CONTROLLER_ACTIVE: controller_data.get(ATTR_CONTROLLER_ACTIVE),
            ATTR_CONTROLLER_CHECK_HOURS: controller_data.get(ATTR_CONTROLLER_CHECK_HOURS),
            ATTR_CONTROLLER_CHECK_PERIOD_DISPLAY: controller_data.get(ATTR_CONTROLLER_CHECK_PERIOD_DISPLAY),
            ATTR_CONTROLLER_LIC_CHANNELS: controller_data.get(ATTR_CONTROLLER_LIC_CHANNELS),
            ATTR_CONTROLLER_REQUESTS: controller_data.get(ATTR_CONTROLLER_REQUESTS),
            ATTR_CONTROLLER_LOG_PERIOD: controller_data.get(ATTR_CONTROLLER_LOG_PERIOD),
            ATTR_CONTROLLER_SCAN_PERIOD: controller_data.get(ATTR_CONTROLLER_SCAN_PERIOD),
            ATTR_CONTROLLER_VOL_THRESHOLD: controller_data.get(ATTR_CONTROLLER_VOL_THRESHOLD),
            ATTR_CONTROLLER_SEND_PERIOD: controller_data.get(ATTR_CONTROLLER_SEND_PERIOD),
            ATTR_CONTROLLER_CAP_STATE: controller_data.get(ATTR_CONTROLLER_CAP_STATE),
            ATTR_CONTROLLER_POWER_SUPPLY: controller_data.get(ATTR_CONTROLLER_POWER_SUPPLY),
            ATTR_CONTROLLER_EMPTY_INPUTS: controller_data.get(ATTR_CONTROLLER_EMPTY_INPUTS),
            "nbiot_info": str(controller_data.get("nbiot")) if controller_data.get("nbiot") else None,
            # Добавим обратно 'name' из API как отдельный атрибут, если он отличается от модели
        }
        # Убираем None значения из атрибутов для чистоты
        self._attr_extra_state_attributes = {k: v for k, v in attributes.items() if v is not None}

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            if (
                self.coordinator.data is not None
                and self.flat_id in self.coordinator.data.get(CONTROLLERS, {})
                and self.controller_sn in self.coordinator.data[CONTROLLERS][self.flat_id]
            ):
                new_controller_data = self.coordinator.data[CONTROLLERS][self.flat_id][self.controller_sn]
                self._update_state_and_attrs(new_controller_data)
                self.async_write_ha_state()  # Сообщаем HA об обновлении
            else:
                _LOGGER.debug("No data for controller %s in flat %s in coordinator update", self.controller_sn, self.flat_id)
        except Exception as e:
            _LOGGER.error("Error handling coordinator update for controller %s: %s", self.unique_id, e, exc_info=True)
