"""Real Home Assistant → integration → TCP → emulator, without a physical logger."""

import asyncio
from contextlib import suppress

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from emulator.server import Simulation, serve_client

DOMAIN = "huawei_smartlogger"
POWER = "logger:0:40525"
ENERGY = "logger:0:40560"


async def test_two_emulators_with_actual_home_assistant(hass, socket_enabled):
    simulations = [Simulation(serial="SIM3000-A"), Simulation(serial="SIM3000-B")]
    simulations[1].update({"power_kw": 75})
    servers = []
    entries = []
    writers = set()
    handlers = set()

    async def handle(reader, writer, simulation):
        task = asyncio.current_task()
        handlers.add(task)
        writers.add(writer)
        try:
            await serve_client(reader, writer, simulation)
        finally:
            handlers.discard(task)
            writers.discard(writer)

    try:
        for index, simulation in enumerate(simulations):
            server = await asyncio.start_server(
                lambda r, w, s=simulation: handle(r, w, s), "127.0.0.1", 0)
            servers.append(server)
            port = server.sockets[0].getsockname()[1]
            entry = MockConfigEntry(
                domain=DOMAIN, title=f"Emulator {index + 1}", version=1,
                data=dict(host="127.0.0.1", name=f"Emulator {index + 1}", port=port,
                          unit_id=0, timeout=1, retries=0, request_delay=0, poll_interval=30, devices=""),
                options={"variables": [POWER, ENERGY]}, unique_id=f"127.0.0.1:{port}:0",
            )
            entry.add_to_hass(hass)
            entries.append(entry)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_ids = [registry.async_get_entity_id("sensor", DOMAIN, f"{e.entry_id}:{POWER}") for e in entries]
        assert entity_ids[0] != entity_ids[1]
        assert [float(hass.states.get(key).state) for key in entity_ids] == [50, 75]
        assert all(s.requests > 0 for s in simulations)

        simulations[0].update({"power_kw": 25})
        await entries[0].runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert [float(hass.states.get(key).state) for key in entity_ids] == [25, 75]

        simulations[0].update({"fault": "exception"})
        await entries[0].runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get(entity_ids[0]).state == "unavailable"
        assert float(hass.states.get(entity_ids[1]).state) == 75

        simulations[0].update({"fault": "online"})
        await entries[0].runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert float(hass.states.get(entity_ids[0]).state) == 25
    finally:
        for entry in entries:
            with suppress(Exception):
                await hass.config_entries.async_unload(entry.entry_id)
        for server in servers:
            server.close()
            await server.wait_closed()
        for writer in list(writers):
            writer.close()
        for task in list(handlers):
            task.cancel()
        await asyncio.gather(*list(handlers), return_exceptions=True)
