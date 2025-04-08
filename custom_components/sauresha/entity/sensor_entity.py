import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import SauresBaseEntity
from ..const import (
    ATTR_METER_APPROVE_DT,
    ATTR_METER_EIRC_NUM,
    ATTR_METER_ID,
    ATTR_METER_INPUT,
    ATTR_METER_LAST_READING_DT,
    ATTR_METER_SN,
    ATTR_METER_STATE_NAME,
    ATTR_METER_STATE_NUMBER,
    ATTR_METER_TYPE_NAME,
    ATTR_METER_TYPE_NUMBER,
    ATTR_METER_UNIT,
)

_LOGGER = logging.getLogger(__name__)

# Маппинг типов Saures API на характеристики сенсоров HA
SAURES_TYPE_TO_HA_SENSOR_MAP = {
    # type_number: (device_class, state_class, unit_of_measurement)
    1: (SensorDeviceClass.WATER, SensorStateClass.TOTAL_INCREASING, UnitOfVolume.CUBIC_METERS),  # Счетчик холодной воды (м³)
    2: (SensorDeviceClass.WATER, SensorStateClass.TOTAL_INCREASING, UnitOfVolume.CUBIC_METERS),  # Счетчик горячей воды (м³)
    3: (SensorDeviceClass.GAS, SensorStateClass.TOTAL_INCREASING, UnitOfVolume.CUBIC_METERS),  # Счетчик газа (м³)
    5: (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS),  # Датчик температуры (°C)
    7: (
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
    ),  # Счетчик тепла (кВт*ч) - предполагаем, что это энергия
    8: (
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
    ),  # Счетчик электричества (кВт*ч)
    10: (SensorDeviceClass.ENUM, None, None),  # Состояние крана (представим как enum - open/closed/unknown...)
    # Добавить другие типы по необходимости
    # 11 - сам контроллер, его статус обрабатывается в SauresControllerSensor
}


class SauresSensor(SauresBaseEntity, SensorEntity):
    """Representation of a Saures Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        flat_id: str,
        meter_id: str,
        controller_sn: str,
        meter_data: dict,  # Начальные данные
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, flat_id, meter_id, controller_sn, meter_data, "sensor")
        # Устанавливаем начальные характеристики сенсора на основе типа
        self._update_sensor_characteristics(meter_data)
        # Устанавливаем начальное состояние и атрибуты
        self._update_state_and_attrs(meter_data)  # Вызываем для инициализации

    def _get_meter_key(self) -> str:
        return "sensors"

    def _update_sensor_characteristics(self, meter_data: dict):
        """Set device_class, state_class, unit based on meter type."""
        meter_type_number = meter_data.get("type", {}).get("number")
        characteristics = SAURES_TYPE_TO_HA_SENSOR_MAP.get(meter_type_number)

        if characteristics:
            self._attr_device_class, self._attr_state_class, self._attr_native_unit_of_measurement = characteristics
        else:
            # Если тип неизвестен, сбрасываем характеристики
            self._attr_device_class = None
            self._attr_state_class = None
            # Пытаемся взять единицу измерения из API, если она там есть
            self._attr_native_unit_of_measurement = meter_data.get("unit")

        # Особый случай для состояния крана (type 10)
        if meter_type_number == 10:
            self._attr_device_class = SensorDeviceClass.ENUM
            # Определяем возможные состояния (опционально, но полезно)
            self._attr_options = ["not_connected", "unknown", "open", "closed"]
            self._attr_translation_key = "valve_state"  # Для перевода состояний в UI

    def _update_state_and_attrs(self, meter_data: dict):
        """Update state and attributes from new meter data."""
        self._meter_data = meter_data

        self._update_sensor_characteristics(meter_data)

        vals = meter_data.get("vals", [])
        primary_value = None
        if vals:
            if isinstance(vals[0], (int, float)):
                primary_value = vals[0]
            else:
                _LOGGER.warning("First element in 'vals' is not a number for %s: %s", self.unique_id, vals[0])
        else:
            _LOGGER.debug("Empty 'vals' for %s", self.unique_id)

        meter_type_info = meter_data.get("type", {})
        meter_state_info = meter_data.get("state", {})

        meter_type_number = meter_type_info.get("number")
        # --- Обработка состояния ---
        # (логика определения _attr_native_value остается прежней)
        if meter_type_number == 10:
            state_map = {0: "not_connected", 1: "unknown", 2: "open", 3: "closed"}
            self._attr_native_value = state_map.get(primary_value, "unknown")
        elif self._attr_state_class in [SensorStateClass.MEASUREMENT, SensorStateClass.TOTAL_INCREASING] or isinstance(
            primary_value, (int, float)
        ):
            try:
                self._attr_native_value = float(primary_value) if primary_value is not None else None
            except (ValueError, TypeError):
                self._attr_native_value = None
                _LOGGER.warning("Invalid numeric value for %s: %s", self.unique_id, primary_value)
        else:
            self._attr_native_value = primary_value

        # --- Обновляем атрибуты ---
        attributes = {
            ATTR_METER_ID: self.meter_id,
            ATTR_METER_SN: meter_data.get(ATTR_METER_SN),
            ATTR_METER_TYPE_NAME: meter_type_info.get(ATTR_METER_TYPE_NAME, {}),
            ATTR_METER_TYPE_NUMBER: meter_type_info.get(ATTR_METER_TYPE_NUMBER, {}),
            ATTR_METER_UNIT: self._attr_native_unit_of_measurement,
            ATTR_METER_INPUT: meter_data.get(ATTR_METER_INPUT),  # <-- Добавлено
            ATTR_METER_EIRC_NUM: meter_data.get(ATTR_METER_EIRC_NUM),  # <-- Добавлено
            ATTR_METER_STATE_NAME: meter_state_info.get(ATTR_METER_STATE_NAME),
            ATTR_METER_STATE_NUMBER: meter_state_info.get(ATTR_METER_STATE_NUMBER),
            ATTR_METER_APPROVE_DT: meter_data.get(ATTR_METER_APPROVE_DT),
            ATTR_METER_LAST_READING_DT: meter_data.get(ATTR_METER_LAST_READING_DT),
            "controller_sn": self.controller_sn,
            "flat_id": self.flat_id,
            "raw_value": primary_value,
        }

        # Убираем None значения
        self._attr_extra_state_attributes = {k: v for k, v in attributes.items() if v is not None}
