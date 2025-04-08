from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import SauresBaseEntity, _LOGGER  # Добавим _LOGGER
from ..const import (
    ATTR_METER_APPROVE_DT,
    ATTR_METER_ID,
    ATTR_METER_LAST_READING_DT,
    ATTR_METER_SN,
    ATTR_METER_TYPE_NAME,
    ATTR_METER_TYPE_NUMBER,
    ATTR_METER_UNIT,
    ATTR_METER_VALUE,
    CONF_COMMAND_ACTIVATE,
    CONF_COMMAND_DEACTIVATE,
)


class SauresSwitch(SauresBaseEntity, SwitchEntity):
    """Representation of a Saures Switch (e.g., Valve Control)."""

    # Устанавливаем класс устройства, если это кран (можно сделать более общим)
    _attr_device_class = SwitchDeviceClass.SWITCH  # Или .OUTLET, .VALVE если применимо

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        flat_id: str,
        meter_id: str,
        controller_sn: str,
        meter_data: dict,  # Начальные данные
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, flat_id, meter_id, controller_sn, meter_data, "switch")
        # Устанавливаем начальное состояние и атрибуты
        self._update_state_and_attrs(meter_data)  # Вызываем для инициализации

    def _get_meter_key(self) -> str:
        return "switches"

    def _update_state_and_attrs(self, meter_data: dict):
        """Update state and attributes from new meter data."""
        self._meter_data = meter_data  # Обновляем кеш данных сущности

        # Извлекаем значение из 'vals'
        vals = meter_data.get("vals", [])
        primary_value = vals[0] if vals else None  # Просто берем первый элемент
        meter_type_number = meter_data.get("type", {}).get("number")

        # Определяем состояние ON/OFF (1 = ON (Закрыто?), 0 = OFF (Открыто?))
        try:
            # Добавляем проверку на None перед конвертацией
            current_value_int = int(float(primary_value)) if primary_value is not None else None
            self._attr_is_on = current_value_int == 1 if current_value_int is not None else None
        except (ValueError, TypeError):
            self._attr_is_on = None  # Неопределенное состояние при ошибке
            _LOGGER.warning("Invalid switch value for %s: %s", self.unique_id, primary_value)

        # Обновляем атрибуты
        attributes = {
            ATTR_METER_ID: self.meter_id,
            ATTR_METER_SN: meter_data.get(ATTR_METER_SN),
            ATTR_METER_VALUE: primary_value,  # Сохраняем "сырое" значение
            ATTR_METER_TYPE_NAME: meter_data.get("type", {}).get("name"),
            ATTR_METER_TYPE_NUMBER: meter_type_number,
            ATTR_METER_UNIT: meter_data.get("unit"),
            ATTR_METER_APPROVE_DT: meter_data.get(ATTR_METER_APPROVE_DT),
            ATTR_METER_LAST_READING_DT: meter_data.get("last_ts"),
            "controller_sn": self.controller_sn,
            "flat_id": self.flat_id,
        }
        self._attr_extra_state_attributes = attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (send 'deactivate' - close valve?)."""
        _LOGGER.debug("Turning ON switch %s (sending %s)", self.meter_id, CONF_COMMAND_DEACTIVATE)
        # ВНИМАНИЕ: Проверь, какая команда соответствует ВКЛ (закрытию крана)
        # Если 'activate' = ON, а 'deactivate' = OFF, поменяй команды местами
        if await self.coordinator.my_api.set_command(self.meter_id, CONF_COMMAND_DEACTIVATE):  # Или CONF_COMMAND_ACTIVATE
            # Оптимистичное обновление состояния (можно убрать, если обновление координатора быстрое)
            # self._attr_is_on = True
            # self.async_write_ha_state()
            # Запросить обновление у координатора
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn ON switch %s", self.meter_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (send 'activate' - open valve?)."""
        _LOGGER.debug("Turning OFF switch %s (sending %s)", self.meter_id, CONF_COMMAND_ACTIVATE)
        # ВНИМАНИЕ: См. комментарий в async_turn_on
        if await self.coordinator.my_api.set_command(self.meter_id, CONF_COMMAND_ACTIVATE):  # Или CONF_COMMAND_DEACTIVATE
            # Оптимистичное обновление
            # self._attr_is_on = False
            # self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn OFF switch %s", self.meter_id)
