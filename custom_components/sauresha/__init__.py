"""Support for Saures Connect appliances."""

from datetime import timedelta
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SauresHA
from .const import (
    CONF_FLATS,
    CONF_ISDEBUG,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up component."""
    domain_config = config.get(DOMAIN, {})
    if not domain_config:
        return True

    # Инициализируем структуру в hass.data
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    for user_cfg in domain_config.get("sensor", []):
        if not user_cfg:
            continue
        if not user_cfg.get(CONF_EMAIL):
            continue
        if not user_cfg.get(CONF_PASSWORD):
            continue

        yaml_email: str = user_cfg[CONF_EMAIL]
        yaml_password: str = user_cfg[CONF_PASSWORD]

        user_input = {
            CONF_EMAIL: yaml_email,
            CONF_PASSWORD: yaml_password,
            CONF_SCAN_INTERVAL: 30,  # при импорте ставим дефолт
        }

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_IMPORT,
                    "title": user_input[CONF_EMAIL],
                },
                data=user_input,
            )
        )

    # Print startup messages
    _LOGGER.info(STARTUP_MESSAGE)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up SauresHA from a config entry."""
    cur_config = config_entry.data
    cur_options = config_entry.options
    curFlats = cur_options.get(CONF_FLATS, [])

    # Создаём экземпляр SauresHA один раз
    client = SauresHA(
        hass,
        cur_config.get(CONF_EMAIL),
        cur_config.get(CONF_PASSWORD),
        cur_config.get(CONF_ISDEBUG, False),
        curFlats,
    )

    # Создаём DataUpdateCoordinator для централизованного обновления данных
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sauresha_coordinator",
        update_method=client.async_fetch_data,
        update_interval=timedelta(
            minutes=config_entry.options.get(CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, 15))
        ),
    )

    # Инициализируем первый раз (чтобы сразу получить данные)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.error("Failed to fetch initial data: %s", err)
        return False

    # Сохраняем coordinator в hass.data с использованием entry_id для поддержки нескольких учетных записей
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][config_entry.entry_id] = {COORDINATOR: coordinator}
    coordinator.my_api = client  # добавляем ссылку на SauresHA для удобства в сущностях

    # Перенаправляем на платформы (sensor, switch и т.д.)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


# async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
#     """Handle migration of config entry."""
#     # Здесь мы выполняем очистку импортированных конфигураций только один раз
#     if config_entry.source == SOURCE_IMPORT:
#         await hass.config_entries.async_remove(config_entry.entry_id)
#         _LOGGER.info("Imported configuration has been migrated and removed from configuration.yaml")

#     return True
