import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, COORDINATOR, CONF_ISDEBUG
from .entity.switch_entity import SauresSwitch

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Setup switch platform."""
    my_switches = []
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id].get(COORDINATOR)
    if not coordinator:
        _LOGGER.error("SauresHA coordinator not found")
        return

    is_debug = config_entry.data.get(CONF_ISDEBUG, False)
    # scan_interval не нужен, так как обновление управляется координатором
    # scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL, 15)

    for flat_id, switches in coordinator.data.get("switches", {}).items():
        for switch in switches:
            meter_id = switch.get("meter_id")
            sn = switch.get("sn")
            meter_name = switch.get("meter_name")
            if not all([meter_id, sn, meter_name]):
                _LOGGER.warning("Switch with missing meter_id, sn, or meter_name: %s", switch)
                continue

            my_switch = SauresSwitch(
                coordinator,
                flat_id,
                meter_id,
                sn,
                meter_name,
                is_debug,
                # scan_interval,  # Удалено
            )
            my_switches.append(my_switch)

    if my_switches:
        async_add_entities(my_switches, True)
