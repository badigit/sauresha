import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import SauresBaseEntity
from ..const import (
    ATTR_METER_APPROVE_DT,
    ATTR_METER_ID,
    ATTR_METER_LAST_READING_DT,
    ATTR_METER_SN,
    ATTR_METER_TYPE_NAME,
    ATTR_METER_TYPE_NUMBER,
    ATTR_METER_UNIT,
    ATTR_METER_VALUE,
)

_LOGGER = logging.getLogger(__name__)

# Маппинг типов Saures API на характеристики бинарных сенсоров HA
SAURES_TYPE_TO_HA_BINARY_SENSOR_MAP = {
    # type_number: (device_class, is_on_state)
    # is_on_state: Значение из API, которое соответствует состоянию ON
    4: (BinarySensorDeviceClass.MOISTURE, 1),  # Датчик протечки (старый тип?)
    9: (BinarySensorDeviceClass.MOISTURE, 1),  # Датчик протечки (0 – нет протечки, 1 - протечка)
    # 10: Состояние крана - сейчас сделано как Sensor. Если нужно как Binary Sensor:
    # 10: (BinarySensorDeviceClass.OPENING, 2), # Состояние крана (2 = открыт -> ON?)
    # Нужно решить, как представлять состояние крана: Sensor (open/closed/...) или Binary Sensor (open/closed)
}


class SauresBinarySensor(SauresBaseEntity, BinarySensorEntity):
    """Representation of a Saures Binary Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        flat_id: str,
        meter_id: str,
        controller_sn: str,
        meter_data: dict,  # Начальные данные
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, flat_id, meter_id, controller_sn, meter_data, "binary_sensor")
        # Устанавливаем начальные характеристики сенсора на основе типа
        self._update_sensor_characteristics(meter_data)
        # Устанавливаем начальное состояние и атрибуты
        self._update_state_and_attrs(meter_data)  # Вызываем для инициализации

    def _get_meter_key(self) -> str:
        return "binary_sensors"

    def _update_sensor_characteristics(self, meter_data: dict):
        """Set device_class based on meter type."""
        meter_type_number = meter_data.get("type", {}).get("number")
        characteristics = SAURES_TYPE_TO_HA_BINARY_SENSOR_MAP.get(meter_type_number)

        if characteristics:
            self._attr_device_class, self._on_state_value = characteristics
        else:
            # Если тип неизвестен, сбрасываем характеристики
            self._attr_device_class = None
            # По умолчанию считаем, что 1 - это ON (для неизвестных датчиков типа "сухой контакт")
            self._on_state_value = 1

    def _update_state_and_attrs(self, meter_data: dict):
        """Update state and attributes from new meter data."""
        self._meter_data = meter_data  # Обновляем кеш данных сущности

        # Обновляем характеристики
        self._update_sensor_characteristics(meter_data)

        # Извлекаем значение из 'vals'
        vals = meter_data.get("vals", [])
        primary_value = vals[0] if vals else None  # Просто берем первый элемент
        meter_type_number = meter_data.get("type", {}).get("number")

        # Определяем состояние ON/OFF
        try:
            # Сравниваем приведенное к int значение с тем, что считаем ON
            # Добавляем проверку на None перед конвертацией
            current_value_int = int(float(primary_value)) if primary_value is not None else None
            self._attr_is_on = current_value_int == self._on_state_value if current_value_int is not None else None
        except (ValueError, TypeError):
            self._attr_is_on = None  # Неопределенное состояние при ошибке
            _LOGGER.warning("Invalid binary sensor value for %s: %s", self.unique_id, primary_value)

        # Обновляем атрибуты
        attributes = {
            ATTR_METER_ID: self.meter_id,
            ATTR_METER_SN: meter_data.get(ATTR_METER_SN),
            ATTR_METER_VALUE: primary_value,  # Сохраняем "сырое" значение в атрибутах
            ATTR_METER_TYPE_NAME: meter_data.get("type", {}).get("name"),
            ATTR_METER_TYPE_NUMBER: meter_type_number,
            ATTR_METER_UNIT: meter_data.get("unit"),  # Единица измерения (если есть)
            ATTR_METER_APPROVE_DT: meter_data.get(ATTR_METER_APPROVE_DT),
            ATTR_METER_LAST_READING_DT: meter_data.get("last_ts"),
            "controller_sn": self.controller_sn,
            "flat_id": self.flat_id,
        }
        self._attr_extra_state_attributes = attributes
