"""Huawei SmartLogger 3000: independent Modbus TCP configuration entries."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .catalog import selected_variables
from .const import CONF_VARIABLES, DOMAIN
from .coordinator import SmartLoggerCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    variables = selected_variables(dict(entry.data), entry.options.get(CONF_VARIABLES, []))
    coordinator = SmartLoggerCoordinator(hass, entry, variables)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Huawei", model="SmartLogger3000", name=entry.title,
        )
        # Remove only this entry's deselected entities. Never touch another logger.
        registry = er.async_get(hass)
        desired = {f"{entry.entry_id}:{v.key}" for v in variables}
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity.platform == DOMAIN and entity.unique_id not in desired:
                registry.async_remove(entity.entity_id)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.gateway.close()
        raise
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.gateway.close()
        return True
    return False
