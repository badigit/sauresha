"""API for Saures"""

import asyncio
from datetime import datetime
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONF_BINARY_SENSORS_DEF,
    CONF_SWITCH_DEF,
    CONTROLLERS,
)
from .saures_api_client import SauresAPIClient

_LOGGER = logging.getLogger(__name__)


class SauresHA:
    _debug: bool
    _last_login_time: datetime
    _api_client: SauresAPIClient
    userflats: list

    CONTROLLER_NAME_MAP = {
        "1.3": "счетчик C1",
        "1.4": "счетчик C1",
        "1.5": "счетчик C1",
        "3.1": "контроллер R1(до 2017)",
        "3.2": "контроллер R1(до 2017)",
        "3.4": "контроллер R1 8 (2017-2018)",
        "3.5": "контроллер R1 4 (после 2018)",
        "4.0": "контроллер R2 (4.0)",
        "4.5": "контроллер R2 (4.5)",
        "4.1": "контроллер R4",
        "6.3": "контроллер R5",
        "7.2": "контроллер R6",
        "8.2": "контроллер R7(до 2020)",
        "8.3": "контроллер R7(после 2020)",
        "9.1": "контроллер R8(после 2022)",
    }

    def __init__(self, hass: HomeAssistant | None, email, password, is_debug, userflats) -> None:
        self._hass = hass
        self._debug = is_debug
        self._email = email
        self._password = password
        self.userflats = userflats  # Выбранные пользователем квартиры/объекты

        session = async_get_clientsession(hass)  # Используем HA клиент
        self._api_client = SauresAPIClient(email, password, session, debug=is_debug)

        self._last_login_time = datetime(2000, 1, 1, 1, 1, 1)
        self._last_update_time_dict = {}  # Кеш времени последнего обновления для каждого flat_id
        self._flats_cache = {}  # Кеш для информации о квартирах/объектах

    def get_controller_name(self, version_id):
        """Return the name of the controller based on version_id."""
        return self.CONTROLLER_NAME_MAP.get(str(version_id), f"неизвестный контроллер ({version_id})")

    async def async_get_flats(self) -> dict:
        """Get available flats/objects from API. Returns a dict {flat_id: name}."""
        if not await self._api_client.check_sid():
            _LOGGER.error("SID not available. Failed to get flats")
            return {}

        # Используем кеш, если есть
        if self._flats_cache:
            return self._flats_cache

        flats_info = {}
        try:
            response = await self._api_client.request(
                "GET", "/user/objects"
            )  # Тут мы получает объекты пользователя, например квартиры
            if response and response.get("status") == "ok":
                result_data = response["data"]["objects"]
                for val in result_data:
                    flat_id = val.get("id")
                    if flat_id:
                        label = val.get("label", "")
                        house = val.get("house", "")
                        number = val.get("number", "")
                        # Формируем читаемое имя
                        name_parts = [part for part in [label, house, f"({number})" if number else ""] if part]
                        flats_info[str(flat_id)] = " : ".join(name_parts) if name_parts else f"Объект {flat_id}"

                self._flats_cache = flats_info  # Сохраняем в кеш
                _LOGGER.debug("Flats fetched: %s", flats_info)
                return flats_info
            else:
                _LOGGER.error(
                    "Failed to get flats: Invalid response status=%s, errors=%s", response.get("status"), response.get("errors")
                )
                return {}
        except Exception as err:
            _LOGGER.error("Exception during getting flats: %s", err, exc_info=self._debug)
            return {}

    async def set_command(self, meter_id, command_text):
        """Send command to a meter (e.g., switch)."""
        if not await self._api_client.check_sid():
            _LOGGER.warning("Cannot send command, SID not available.")
            return False
        try:
            # Используем POST и передаем параметры в data (как требует API)
            response = await self._api_client.request("POST", "/meter/control", data={"id": meter_id, "command": command_text})

            if response and response.get("status") == "ok":
                _LOGGER.info("Command '%s' sent successfully to meter %s", command_text, meter_id)
                return True
            else:
                errors = response.get("errors", [{"msg": "Unknown error"}]) if response else [{"msg": "No response"}]
                error_msg = errors[0].get("msg", "Unknown error")
                _LOGGER.warning("Failed to send command '%s' to meter %s: %s", command_text, meter_id, error_msg)
                return False
        except Exception as err:
            _LOGGER.error("Exception sending command to meter %s: %s", meter_id, err, exc_info=self._debug)
            return False

    async def _async_get_meters_for_flat(self, flat_id: str) -> list | None:
        """Fetch meter data for a specific flat from API."""
        # Простая проверка кеширования по времени убрана, т.к. DataUpdateCoordinator управляет интервалом
        if await self._api_client.check_sid():
            try:
                response = await self._api_client.request("GET", "/object/meters", id=flat_id)
                if response and response.get("status") == "ok":
                    # Данные API это список контроллеров, каждый со списком счетчиков
                    # [{'sn': '123', ..., 'meters': [{'meter_id': 1, ...}, {'meter_id': 2, ...}]}, ...]
                    return response["data"].get(
                        "sensors", []
                    )  # API возвращает ключ 'sensors', который содержит список контроллеров
                else:
                    _LOGGER.warning(
                        "Failed to get meters for flat %s: status=%s, errors=%s",
                        flat_id,
                        response.get("status"),
                        response.get("errors"),
                    )
                    return None
            except Exception as err:
                _LOGGER.error("Exception getting meters for flat %s: %s", flat_id, err, exc_info=self._debug)
                return None
        else:
            _LOGGER.warning("Cannot get meters for flat %s, SID not available.", flat_id)
            return None

    async def async_fetch_data(self):
        """Fetch all data for selected flats and structure it for coordinator."""
        if not await self._api_client.check_sid():
            _LOGGER.error("Initial SID check failed, cannot fetch data.")
            raise UpdateFailed("Authentication failed (SID invalid).")

        all_flats_info = await self.async_get_flats()
        if not all_flats_info:
            _LOGGER.warning("No flats found for this user.")
            # Можно вернуть пустую структуру, чтобы не было ошибки дальше
            return {CONTROLLERS: {}, "sensors": {}, "binary_sensors": {}, "switches": {}}

        # Фильтруем квартиры, если пользователь выбрал конкретные
        target_flat_ids = self.userflats if self.userflats else list(all_flats_info.keys())

        _LOGGER.debug("Fetching data for flats: %s", target_flat_ids)

        # Структура данных для координатора
        data = {
            CONTROLLERS: {},  # {flat_id: {controller_sn: controller_data}}
            "sensors": {},  # {flat_id: {meter_id: meter_data}}
            "binary_sensors": {},  # {flat_id: {meter_id: meter_data}}
            "switches": {},  # {flat_id: {meter_id: meter_data}}
        }

        for i, flat_id in enumerate(target_flat_ids):
            if i > 0:  # Делаем паузу между запросами для разных квартир
                await asyncio.sleep(3)  # Пауза 3 секунды

            _LOGGER.debug("Fetching data for flat_id: %s", flat_id)
            flat_controllers_data = await self._async_get_meters_for_flat(flat_id)  # Получаем список контроллеров с их счетчиками

            if flat_controllers_data is None:  # Ошибка при получении данных для этой квартиры
                _LOGGER.warning("Skipping flat_id %s due to fetch error.", flat_id)
                continue  # Переходим к следующей квартире

            # Инициализируем словари для текущей квартиры
            data[CONTROLLERS][flat_id] = {}
            data["sensors"][flat_id] = {}
            data["binary_sensors"][flat_id] = {}
            data["switches"][flat_id] = {}

            # Обрабатываем каждый контроллер в квартире
            for controller_info in flat_controllers_data:
                controller_sn = controller_info.get("sn")
                if not controller_sn:
                    _LOGGER.warning("Controller in flat %s has no SN: %s", flat_id, controller_info)
                    continue

                # Сохраняем данные контроллера (добавим имя для удобства)
                controller_info["name"] = self.get_controller_name(controller_info.get("hardware"))
                data[CONTROLLERS][flat_id][controller_sn] = controller_info

                # Обрабатываем счетчики (meters), привязанные к этому контроллеру
                meters = controller_info.get("meters", [])
                for meter_data in meters:
                    meter_id = meter_data.get("meter_id")
                    if not meter_id:
                        _LOGGER.warning(
                            "Meter in controller %s (flat %s) has no meter_id: %s", controller_sn, flat_id, meter_data
                        )
                        continue

                    # Добавляем ссылку на SN контроллера к данным счетчика
                    meter_data["controller_sn"] = controller_sn
                    # Добавляем flat_id для удобства в сущностях
                    meter_data["flat_id"] = flat_id

                    meter_type = meter_data.get("type", {}).get("number")

                    # Распределяем счетчик по категориям
                    if meter_type in CONF_BINARY_SENSORS_DEF:
                        data["binary_sensors"][flat_id][meter_id] = meter_data
                    elif meter_type in CONF_SWITCH_DEF:
                        data["switches"][flat_id][meter_id] = meter_data
                    else:  # Все остальное считаем сенсорами (вода, газ, температура, ...)
                        data["sensors"][flat_id][meter_id] = meter_data

        _LOGGER.debug("Data fetched successfully.")
        # _LOGGER.info("Fetched data structure: %s", data) # Для отладки структуры данных
        return data

    async def test_connection(self) -> bool:
        """Test API connection by fetching user profile."""
        if not await self._api_client.check_sid():
            # Попытка обновить SID, если его нет
            if not await self._api_client.update_sid():
                _LOGGER.error("Test connection failed: Could not obtain SID.")
                return False
            # Если SID получен, проверяем еще раз
            if not await self._api_client.check_sid():
                _LOGGER.error("Test connection failed: SID obtained but check failed.")
                return False

        try:
            response = await self._api_client.request("GET", "/user/profile")
            if response and response.get("status") == "ok":
                _LOGGER.info("Test connection successful.")
                return True
            else:
                _LOGGER.warning(
                    "Test connection failed: API status=%s, errors=%s", response.get("status"), response.get("errors")
                )
                return False
        except Exception as ex:
            _LOGGER.error("Test connection exception: %s", ex, exc_info=self._debug)
            return False
