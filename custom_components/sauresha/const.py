# config/custom_components/sauresha/const.py

"""
The Saures component.

For more details about this platform, please refer to the documentation at
https://github.com/volshebniks/sauresha/
"""

# Base component constants

NAME = "Saures"
DOMAIN = "sauresha"
VERSION = "1.0.5"  # <-- Обновим версию
ATTRIBUTION = "Home assistant component for Saures"
ISSUE_URL = "https://github.com/volshebniks/sauresha/issues"

PLATFORMS = [
    "binary_sensor",  # <-- Раскомментировано
    "sensor",
    "switch",  # <-- Раскомментировано
]

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have ANY issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Configuration and options
CONF_ISDEBUG = "is_debug"
CONF_DEBUG = "debug"
CONF_FLATS = "flats"
CONF_SENSORS = "sensors"
CONF_BINARY_SENSORS_DEF = [
    4,
    9,
    10,
]  # On Saures API [9 = Датчик протечки] [10 = Состояние крана] [4 = Датчик протечки] (добавим 4)
CONF_BINARY_SENSOR_DEV_CLASS_MOISTURE_DEF = [4, 9]  # <-- Добавим 4
CONF_BINARY_SENSOR_DEV_CLASS_OPENING_DEF = [10]
CONF_SWITCH_DEF = [6]  # Электро-шаровой кран управление

COORDINATOR = "coordinator"
CONTROLLERS = "controllers"  # <-- Добавим ключ для контроллеров

# Command
CONF_COMMAND_ACTIVATE = "activate"
CONF_COMMAND_DEACTIVATE = "deactivate"

# Атрибуты контроллера (для удобства)
ATTR_CONTROLLER_NAME = "name"
ATTR_CONTROLLER_MODEL = "model"
ATTR_CONTROLLER_HARDWARE = "hardware"
ATTR_CONTROLLER_FIRMWARE = "firmware"
ATTR_CONTROLLER_NEW_FIRMWARE = "new_firmware"
ATTR_CONTROLLER_SN = "sn"
ATTR_CONTROLLER_SSID = "ssid"
ATTR_CONTROLLER_LOCAL_IP = "local_ip"
ATTR_CONTROLLER_BATTERY = "bat"
ATTR_CONTROLLER_LAST_CONNECTION = "last_connection"
ATTR_CONTROLLER_ACTIVE = "active"
ATTR_CONTROLLER_CHECK_HOURS = "check_hours"
ATTR_CONTROLLER_CHECK_PERIOD_DISPLAY = "check_period_display"
ATTR_CONTROLLER_LAST_CONNECTION_WARNING = "last_connection_warning"
ATTR_CONTROLLER_LIC_CHANNELS = "lic_channels"
ATTR_CONTROLLER_REQUESTS = "requests"
ATTR_CONTROLLER_RSSI = "rssi"
ATTR_CONTROLLER_SCAN_PERIOD = "scan"
ATTR_CONTROLLER_LOG_PERIOD = "log"
ATTR_CONTROLLER_VOL_THRESHOLD = "vol"
ATTR_CONTROLLER_SEND_PERIOD = "send"
ATTR_CONTROLLER_READOUT_DT = "readout_dt"  # Lата и время последних переданных показаний c сервера ISO 8601
ATTR_CONTROLLER_REQUEST_DT = "request_dt"  # дата и время последней передачи показаний от Контроллера на сервер
ATTR_CONTROLLER_CAP_STATE = "cap_state"  # Состояние крышки
ATTR_CONTROLLER_POWER_SUPPLY = "power_supply"  # Внешнее питание
ATTR_CONTROLLER_EMPTY_INPUTS = "empty_inputs"  # Не настроенные входы

# Атрибуты счетчиков
ATTR_METER_ID = "meter_id"
ATTR_METER_NAME = "meter_name"
ATTR_METER_EIRC_NUM = "eirc_num"
ATTR_METER_VALUE = "value"
ATTR_METER_VALS = "vals"  # Список значений от счетчика
ATTR_METER_SN = "sn"
ATTR_METER_DESCR = "description"
ATTR_METER_TYPE_NAME = "name"
ATTR_METER_TYPE_NUMBER = "number"
ATTR_METER_STATE_NAME = "state_name"
ATTR_METER_STATE_NUMBER = "state_number"
ATTR_METER_UNIT = "unit"
ATTR_METER_APPROVE_DT = "approve_dt"
ATTR_METER_LAST_READING_DT = "last_reading_dt"  # Время последнего показания от счетчика
ATTR_METER_INPUT = "input"

ATTR_METER_LAST_COMMAND_INFO = "last_command_info"  # Для кранов, из 'command' в API
ATTR_METER_ACTIVE_TEXT = "active_text"  # Для бинарных датчиков
ATTR_METER_PASSIVE_TEXT = "passive_text"  # Для бинарных датчиков
