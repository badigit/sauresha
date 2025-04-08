# saures_api_client.py

import asyncio
import logging
from aiohttp import ClientOSError, ContentTypeError, FormData, ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)


class SauresAPIClient:
    API_URL = "https://api.saures.ru/1.0"
    REQUEST_ATTEMPTS = 5
    REQUEST_TIMEOUT = 6  # Таймаут запроса в секундах

    def __init__(self, email: str, password: str, session: ClientSession, debug: bool = False) -> None:
        self._email = email
        self._password = password
        self._debug = debug
        self._session = session
        self._sid_renewal = False
        self._sid = None
        self._sid_update_event = asyncio.Event()

    async def request(self, method: str, url: str, params: dict = None, data: any = None, **kwargs):
        if params is None:
            params = {}
        params.update(kwargs)

        for attempt in range(1, self.REQUEST_ATTEMPTS + 1):
            if self._sid:
                params["sid"] = self._sid  # Добавляем sid в параметры

            try:
                async with self._session.request(
                    method,
                    self.API_URL + url,
                    params=params if method == "GET" else None,
                    data=data if method == "POST" else None,
                    headers={"user-agent": "chrome"},
                    timeout=ClientTimeout(total=self.REQUEST_TIMEOUT),
                ) as resp:
                    response = await resp.json()
            except (ClientOSError, ContentTypeError, asyncio.TimeoutError) as ex:
                if isinstance(ex, asyncio.TimeoutError):
                    _LOGGER.warning(f"Request timed out after {self.REQUEST_TIMEOUT} seconds")
                if attempt == self.REQUEST_ATTEMPTS:
                    _LOGGER.error("Request error: %s, attempts exhausted", ex)
                    return False
                await asyncio.sleep(30)
            else:
                status = response.get("status")
                errors = response.get("errors", [])
                if status == "ok":
                    return response
                if errors:
                    err_names = [e.get("name") for e in errors]
                    if "WrongSIDException" in err_names:
                        if not self._sid_renewal:
                            self._sid = None
                        if attempt == self.REQUEST_ATTEMPTS:
                            _LOGGER.error("WrongSIDException - attempts exhausted")
                            return False
                        await self.check_sid()
                        continue
                    if "DuplicateRequestException" in err_names:
                        if attempt == self.REQUEST_ATTEMPTS:
                            _LOGGER.error("DuplicateRequestException - attempts exhausted")
                            return False
                        _LOGGER.warning("DuplicateRequestException - waiting 10 sec")
                        await asyncio.sleep(10)
                        continue
                return response
        return False

    async def update_sid(self):
        if self._sid_renewal:
            return False
        self._sid_renewal = True
        self._sid_update_event.clear()
        try:
            # Подготовка данных для отправки в формате x-www-form-urlencoded
            form_data = FormData()
            form_data.add_field("email", self._email)
            form_data.add_field("password", self._password)

            response = await self.request("POST", "/login", data=form_data)  # Исправлено

            if response and response.get("status") == "ok":
                self._sid = response["data"].get("sid")
                _LOGGER.debug(f"SID updated: {self._sid}")
                self._sid_update_event.set()
                return True
            else:
                _LOGGER.error(f"Failed to update SID. Response: {response}")
                self._sid_update_event.set()
                return False
        except Exception as ex:
            _LOGGER.error(f"update_sid error: {ex}")
            self._sid_renewal = False
            self._sid_update_event.set()
            return False
        finally:
            self._sid_renewal = False

    async def check_sid(self):
        if self._sid_renewal:
            await self._sid_update_event.wait()
        elif not self._sid:
            await self.update_sid()
        return bool(self._sid)
