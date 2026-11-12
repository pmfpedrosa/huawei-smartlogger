"""Exercise the actual integration client against the actual emulator TCP server."""

import asyncio
import json
import re
import struct
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from emulator.server import Simulation, control_server, serve_client
from load_core import load

catalog = load("catalog")
gateway = load("gateway")
modbus = load("modbus")


class EmulatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.simulation = Simulation()
        self.servers = []
        self.clients = []
        self.handlers = set()
        self.writers = set()
        self.port = await self.start(self.simulation)

    async def start(self, simulation):
        async def handle(reader, writer):
            task = asyncio.current_task()
            self.handlers.add(task)
            self.writers.add(writer)
            try:
                await serve_client(reader, writer, simulation)
            finally:
                self.handlers.discard(task)
                self.writers.discard(writer)
        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        self.servers.append(server)
        return server.sockets[0].getsockname()[1]

    def reader(self, port=None):
        client = modbus.ModbusClient("127.0.0.1", port or self.port, timeout=0.2, retries=0, request_delay=0)
        self.clients.append(client)
        return gateway.Gateway({"host": "127.0.0.1"}, client)

    async def asyncTearDown(self):
        for client in self.clients:
            await client.close()
        for server in self.servers:
            server.close()
            await server.wait_closed()
        for writer in list(self.writers):
            writer.close()
        for task in list(self.handlers):
            task.cancel()
        await asyncio.gather(*list(self.handlers), return_exceptions=True)

    async def test_complete_integration_catalogue_over_real_tcp(self):
        variables = [v for v in catalog.build_catalog(0, "meter:1,emi:2,inverter_remap:3") if v.selectable]
        result = await self.reader().snapshot(variables)
        self.assertEqual(len(result), len(variables))
        self.assertTrue(all(r.error is None for r in result.values()), result)
        self.assertEqual(result["logger:0:40525"].value, 50)
        self.assertAlmostEqual(result["meter:1:32278"].value, 10)
        self.assertEqual(result["emi:2:40034"].value, 28)
        self.assertEqual(result["inverter_remap:3:0"].value, 50)
        self.assertEqual(result["logger:0:40713"].value, "SIM3000-00000001")

    async def test_override_signed_unsigned_64bit_and_string(self):
        changes = {"logger:0:40525": -12.345, "meter:1:32341": 9876543210.12,
                   "logger:0:40713": "SIM-CUSTOM"}
        for key, value in changes.items():
            self.simulation.update(dict(override_key=key, override_value=value))
        variables = [v for v in catalog.build_catalog(0, "meter:1") if v.key in changes]
        result = await self.reader().snapshot(variables)
        for key, expected in changes.items():
            self.assertEqual(result[key].value, expected)

    async def test_partial_map_isolated_by_actual_client(self):
        self.simulation.update({"unsupported": "0:40573"})
        variables = [v for v in catalog.build_catalog() if v.address in (40572, 40573, 40574)]
        result = await self.reader().snapshot(variables)
        self.assertIsNone(result["logger:0:40572"].error)
        self.assertIsNotNone(result["logger:0:40573"].error)
        self.assertIsNone(result["logger:0:40574"].error)

    async def test_timeout_disconnect_and_recovery(self):
        variable = next(v for v in catalog.build_catalog() if v.address == 40525)
        reader = self.reader()
        for mode in ("timeout", "disconnect"):
            self.simulation.update({"fault": mode})
            with self.assertRaises(modbus.ModbusError):
                await reader.snapshot([variable])
            self.simulation.update({"fault": "online"})
            self.assertEqual((await reader.snapshot([variable]))[variable.key].value, 50)

    async def test_gateway_exception_can_recover_on_same_session(self):
        variable = next(v for v in catalog.build_catalog() if v.address == 40525)
        reader = self.reader()
        self.simulation.update({"fault": "exception"})
        self.assertIsNotNone((await reader.snapshot([variable]))[variable.key].error)
        self.simulation.update({"fault": "online"})
        self.assertEqual((await reader.snapshot([variable]))[variable.key].value, 50)

    async def test_two_real_servers_with_same_unit_remain_independent(self):
        second = Simulation(serial="SIM3000-B")
        second.update({"power_kw": 75})
        port = await self.start(second)
        a, b = self.reader(), self.reader(port)
        variable = next(v for v in catalog.build_catalog() if v.address == 40525)
        first, last = await asyncio.gather(a.snapshot([variable]), b.snapshot([variable]))
        self.assertEqual((first[variable.key].value, last[variable.key].value), (50, 75))
        self.simulation.update({"fault": "timeout"})
        with self.assertRaises(modbus.ModbusError):
            await a.snapshot([variable])
        self.assertEqual((await b.snapshot([variable]))[variable.key].value, 75)

    async def test_mode_dependent_target(self):
        variable = next(v for v in catalog.build_catalog() if v.address == 40742)
        reader = self.reader()
        self.simulation.update({"override_key": "logger:0:40741", "override_value": 0})
        result = (await reader.snapshot([variable]))[variable.key]
        self.assertEqual((result.value, result.unit), (0.985, None))
        self.simulation.update({"override_key": "logger:0:40741", "remove_override": True})
        result = (await reader.snapshot([variable]))[variable.key]
        self.assertEqual(result.unit, "kvar")

    async def test_fragmented_requests_and_read_only_exception(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            packet = struct.pack(">HHHBBHH", 17, 0, 6, 0, 3, 40525, 2)
            for chunk in (packet[:2], packet[2:7], packet[7:]):
                writer.write(chunk)
                await writer.drain()
                await asyncio.sleep(0)
            header = await reader.readexactly(7)
            self.assertEqual(struct.unpack(">HHHB", header), (17, 0, 7, 0))
            self.assertEqual(await reader.readexactly(6), bytes([3, 4, 0, 0, 0xC3, 0x50]))
            writer.write(struct.pack(">HHHBBHH", 18, 0, 6, 0, 6, 40525, 0))
            await writer.drain()
            await reader.readexactly(7)
            self.assertEqual(await reader.readexactly(2), bytes([0x86, 1]))
        finally:
            writer.close()
            await writer.wait_closed()

    async def test_bad_bounds_and_invalid_header(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            writer.write(struct.pack(">HHHBBHH", 1, 0, 6, 0, 3, 65535, 2))
            await writer.drain()
            await reader.readexactly(7)
            self.assertEqual(await reader.readexactly(2), bytes([0x83, 3]))
            writer.write(struct.pack(">HHHB", 2, 0, 65535, 0))
            await writer.drain()
            self.assertEqual(await reader.read(), b"")
        finally:
            writer.close()
            await writer.wait_closed()

    def test_controls_validate_without_changing_existing_values(self):
        for change in ({"power_kw": 101}, {"temperature": float("nan")}, {"fault": "unknown"},
                       {"override_key": "logger:0:40572", "override_value": 999999},
                       {"override_key": "logger:0:40713", "override_value": "X" * 21}):
            with self.subTest(change=change), self.assertRaises((ValueError, UnicodeError)):
                self.simulation.update(change)
        self.assertEqual(self.simulation.controls["power_kw"], 50)
        self.assertEqual(self.simulation.overrides, {})
        self.simulation.update({"power_kw": 100, "vary": True})
        self.simulation.state()

    async def test_control_page_and_token_protected_updates(self):
        control = control_server(self.simulation, 0)
        base = f"http://127.0.0.1:{control.server_port}"

        def exercise():
            html = urlopen(base + "/", timeout=3).read().decode()
            self.assertIn("SmartLogger Emulator", html)
            token = re.search(r"const token='([^']+)'", html).group(1)
            data = json.loads(urlopen(base + "/api/state", timeout=3).read())
            self.assertEqual(data["unit_id"], 0)
            body = json.dumps({"power_kw": 25}).encode()
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + "/api/control", data=body), timeout=3)
            self.assertEqual(caught.exception.code, 403)
            result = urlopen(Request(base + "/api/control", data=body,
                                    headers={"X-Emulator-Token": token, "Content-Type": "application/json"}), timeout=3)
            self.assertTrue(json.loads(result.read())["ok"])

        try:
            await asyncio.to_thread(exercise)
            self.assertEqual(self.simulation.controls["power_kw"], 25)
        finally:
            await asyncio.to_thread(control.shutdown)
            control.server_close()
