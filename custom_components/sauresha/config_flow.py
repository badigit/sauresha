import voluptuous as vol
import logging
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigEntry,
    OptionsFlow,
    CONN_CLASS_LOCAL_POLL,
)
from typing import Any
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import CONF_ISDEBUG, DOMAIN, CONF_FLATS, COORDINATOR
from .api import SauresHA

_LOGGER = logging.getLogger(__name__)


class SaureshaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Init config flow."""
        self._errors = {}

    async def async_step_import(self, platform_config):
        """Handle configuration import from YAML."""
        if platform_config is None:
            return self.async_abort(reason="unknown_error")

        email = platform_config[CONF_EMAIL]
        await self.async_set_unique_id(email)
        self._abort_if_unique_id_configured()

        password = platform_config[CONF_PASSWORD]
        flat_ids = platform_config.get(CONF_FLATS, "")

        user_input = {
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
            CONF_SCAN_INTERVAL: 30,  # при импорте ставим дефолт
        }
        user_options = {
            # Если flat_ids строка - превращаем в список
            CONF_FLATS: str(flat_ids).split(",") if flat_ids else [],
        }

        return self.async_create_entry(title=email, data=user_input, options=user_options)

    async def async_step_user(self, user_input=None):
        """Handle user initiated config flow."""
        self._errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            is_debug = user_input.get(CONF_ISDEBUG, False)

            # Проверка уникальности email
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            # Тестируем соединение с новым конфигурационным вводом
            # Создаём временный экземпляр SauresHA для тестирования
            temp_client = SauresHA(
                self.hass,
                email,
                password,
                is_debug,
                [],
            )

            # Тестируем соединение
            try:
                res_ok = await temp_client.test_connection()
                if not res_ok:
                    self._errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Error checking Saures connection: %s", ex)
                self._errors["base"] = "cannot_connect"

            if not self._errors:
                # Успех - создаём ConfigEntry
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_SCAN_INTERVAL: scan_interval,
                    },
                )

            # Если есть ошибки - показать форму с этими ошибками
            return self._show_config_form(user_input, self._errors)

        # Если user_input=None - показываем форму первый раз
        return self._show_config_form(
            user_input={
                CONF_EMAIL: "email@example.com",
                CONF_PASSWORD: "pass",
                CONF_SCAN_INTERVAL: 30,
            },
            current_errors=self._errors,
        )

    def _show_config_form(self, user_input, current_errors=None):
        """Show the configuration form to edit data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input[CONF_EMAIL]): cv.string,
                    vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): cv.string,
                    vol.Required(CONF_SCAN_INTERVAL, default=user_input[CONF_SCAN_INTERVAL]): cv.positive_int,
                }
            ),
            errors=current_errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get component options flow."""
        return SaureshaOptionsFlowHandler()


class SaureshaOptionsFlowHandler(OptionsFlow):
    """Handle SauresHA options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        self._errors = {}  # ПЕРЕНЕСТИ СЮДА

        if user_input is not None:
            return self.async_create_entry(title=self.config_entry.title, data=user_input)

        # Получаем существующий координатор для текущей config_entry
        coordinator_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if not coordinator_data or COORDINATOR not in coordinator_data:
            _LOGGER.error("SauresHA coordinator not found in hass.data for entry_id: %s", self.config_entry.entry_id)
            self._errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                errors=self._errors,
            )

        coordinator = coordinator_data[COORDINATOR]
        client: SauresHA = coordinator.my_api

        flats = {}
        try:
            flats = await client.async_get_flats()
        except Exception as e:
            _LOGGER.error(f"Error fetching flats: {e}")
            self._errors["base"] = "cannot_connect"

        if not flats:
            try:
                test_ok = await client.test_connection()
                if not test_ok:
                    self._errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Error checking Saures connection: %s", ex)
                self._errors["base"] = "cannot_connect"

        if self._errors:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                errors=self._errors,
            )

        all_flats = {str(flat_id): f"{label} ({flat_id})" for flat_id, label in flats.items()}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FLATS,
                        default=self.config_entry.options.get(CONF_FLATS, []),
                    ): cv.multi_select(all_flats)
                }
            ),
            errors=self._errors,
        )
