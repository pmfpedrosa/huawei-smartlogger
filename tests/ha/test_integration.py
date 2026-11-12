"""Exercise real Home Assistant setup, flows, registry and entity lifecycles."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huawei_smartlogger.catalog import build_catalog
from custom_components.huawei_smartlogger.config_flow import SmartLoggerConfigFlow, SmartLoggerOptionsFlow
from custom_components.huawei_smartlogger.const import DOMAIN
from custom_components.huawei_smartlogger.gateway import Reading
from custom_components.huawei_smartlogger.modbus import ModbusError

POWER = "logger:0:40525"
ENERGY = "logger:0:40560"


def settings(host="logger-a"):
    return dict(name=host, host=host, port=502, unit_id=0, timeout=5, retries=1,
                request_delay=0, poll_interval=30, devices="")


def entry(hass, host, variables):
    result = MockConfigEntry(domain=DOMAIN, title=host, data=settings(host),
                            options={"variables": variables}, unique_id=f"{host}:502:0", version=1)
    result.add_to_hass(hass)
    return result


async def snapshot(self, variables):
    value = 1 if self.settings["host"] == "logger-a" else 2
    return {v.key: Reading(value, v.unit) for v in variables if v.selectable}


@pytest.fixture
def snapshots():
    with patch("custom_components.huawei_smartlogger.gateway.Gateway.snapshot", new=snapshot):
        yield


async def test_two_entries_and_selection_reload(hass, snapshots):
    first = entry(hass, "logger-a", [POWER, ENERGY])
    second = entry(hass, "logger-b", [POWER])
    assert await hass.config_entries.async_setup(first.entry_id)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    first_power = registry.async_get_entity_id("sensor", DOMAIN, f"{first.entry_id}:{POWER}")
    second_power = registry.async_get_entity_id("sensor", DOMAIN, f"{second.entry_id}:{POWER}")
    assert first_power != second_power
    assert hass.states.get(first_power).state == "1"
    assert hass.states.get(second_power).state == "2"
    hass.config_entries.async_update_entry(first, options={"variables": [ENERGY]})
    await hass.async_block_till_done()
    assert registry.async_get(first_power) is None
    assert hass.states.get(first_power) is None
    assert hass.states.get(second_power).state == "2"
    hass.config_entries.async_update_entry(first, options={"variables": [POWER, ENERGY]})
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{first.entry_id}:{POWER}") is not None
    assert await hass.config_entries.async_unload(first.entry_id)
    assert await hass.config_entries.async_unload(second.entry_id)


async def test_connection_failure_does_not_change_second_logger(hass, snapshots):
    first = entry(hass, "logger-a", [POWER])
    second = entry(hass, "logger-b", [POWER])
    assert await hass.config_entries.async_setup(first.entry_id)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    with patch.object(first.runtime_data.gateway, "snapshot", side_effect=ModbusError("offline")):
        await first.runtime_data.async_refresh()
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    a = registry.async_get_entity_id("sensor", DOMAIN, f"{first.entry_id}:{POWER}")
    b = registry.async_get_entity_id("sensor", DOMAIN, f"{second.entry_id}:{POWER}")
    assert hass.states.get(a).state == "unavailable"
    assert hass.states.get(b).state == "2"


async def test_flow_selection_and_empty_selection(hass):
    flow = SmartLoggerConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    flow._settings = settings()
    flow._catalog = build_catalog()
    flow._readings = {POWER: Reading(12.345, "kW")}
    result = await flow.async_step_variables()
    assert result["type"] == "form"
    result = await flow.async_step_variables({"variables": [POWER], "refresh": False})
    assert result["type"] == "create_entry"
    assert result["options"] == {"variables": [POWER]}
    empty = await flow.async_step_variables({"variables": [], "refresh": False})
    assert empty["options"] == {"variables": []}


async def test_duplicate_connection_rejected(hass):
    entry(hass, "logger-a", [POWER])
    flow = SmartLoggerConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    result = await flow.async_step_user(settings())
    assert result["type"] == "form"
    assert result["errors"]["base"] == "already_configured"


async def test_options_offline_preserves_selection(hass):
    existing = entry(hass, "logger-a", [POWER])
    flow = SmartLoggerOptionsFlow()
    flow.hass = hass
    flow.handler = existing.entry_id
    flow._settings = settings()
    flow._catalog = build_catalog()
    flow._selected = [POWER]
    with patch("custom_components.huawei_smartlogger.config_flow.Gateway.snapshot", new=AsyncMock(side_effect=ModbusError("offline"))):
        await flow._read_catalog()
    assert flow._selected == [POWER]
    assert flow._readings[POWER].error is not None
    result = await flow.async_step_variables({"variables": [POWER], "refresh": False})
    assert result["data"] == {"variables": [POWER]}


async def test_reconfigure_preserves_identity_and_changes_endpoint(hass, snapshots):
    existing = entry(hass, "logger-a", [POWER])
    assert await hass.config_entries.async_setup(existing.entry_id)
    await hass.async_block_till_done()
    original_id = existing.entry_id
    flow = SmartLoggerConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_RECONFIGURE, "entry_id": existing.entry_id}
    flow._settings = settings("logger-c")
    result = await flow._finish([POWER])
    await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert existing.entry_id == original_id
    assert existing.data["host"] == "logger-c"
    assert existing.unique_id == "logger-c:502:0"
