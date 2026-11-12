"""One update coordinator per SmartLogger config entry."""

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DOMAIN
from .gateway import Gateway
from .modbus import ModbusError

_LOGGER = logging.getLogger(__name__)


class SmartLoggerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, variables):
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN} {entry.title}", config_entry=entry,
            update_interval=timedelta(seconds=entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
        self.gateway = Gateway(dict(entry.data))
        self.variables = variables

    async def _async_update_data(self):
        try:
            return await self.gateway.snapshot(self.variables)
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err
