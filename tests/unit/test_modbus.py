import asyncio
from contextlib import suppress
import struct
import unittest

from load_core import load

modbus = load("modbus")


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.connections = 0
        self.handlers = set()
        self.writers = set()
        self.mode = "normal"
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.client = modbus.ModbusClient("127.0.0.1", self.server.sockets[0].getsockname()[1],
                                           timeout=0.1, retries=0, request_delay=0)

    async def asyncTearDown(self):
        await self.client.close()
        self.server.close()
        await self.server.wait_closed()
        for writer in list(self.writers):
            writer.close()
        for task in list(self.handlers):
            task.cancel()
        await asyncio.gather(*list(self.handlers), return_exceptions=True)

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.handlers.add(task)
        self.writers.add(writer)
        self.connections += 1
        try:
            while True:
                data = await reader.readexactly(12)
                tid, protocol, length, unit, function, address, count = struct.unpack(">HHHBBHH", data)
                self.requests.append((unit, function, address, count))
                if self.mode == "timeout":
                    await asyncio.sleep(10)
                if self.mode == "drop_once":
                    self.mode = "normal"
                    return
                body = bytes([3, count * 2]) + struct.pack(f">{count}H", *range(count))
                if self.mode == "exception":
                    body = bytes([0x83, 2])
                if self.mode == "bad_count":
                    body = bytes([3, 0])
                response = struct.pack(">HHHB", tid + (self.mode == "bad_tid"),
                                       1 if self.mode == "bad_protocol" else 0,
                                       len(body) + 1, unit + (self.mode == "bad_unit")) + body
                # Split headers and payload to exercise readexactly against TCP fragmentation.
                writer.write(response[:3])
                await writer.drain()
                await asyncio.sleep(0)
                writer.write(response[3:])
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            with suppress(ConnectionError):
                await writer.wait_closed()
            self.writers.discard(writer)
            self.handlers.discard(task)

    async def test_direct_address_and_unit_zero(self):
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])
        self.assertEqual(self.requests, [(0, 3, 40525, 2)])

    async def test_persistent_serialised_requests(self):
        result = await asyncio.gather(*(self.client.read(0, 40525, 2) for _ in range(5)))
        self.assertEqual(result, [[0, 1]] * 5)
        self.assertEqual(self.connections, 1)

    async def test_explicit_modbus_exception(self):
        self.mode = "exception"
        with self.assertRaises(modbus.ModbusException) as caught:
            await self.client.read(0, 40525, 2)
        self.assertEqual(caught.exception.code, 2)

    async def test_malformed_responses_close_connection(self):
        for mode in ("bad_tid", "bad_protocol", "bad_unit", "bad_count"):
            with self.subTest(mode=mode):
                self.mode = mode
                with self.assertRaises(modbus.ModbusError):
                    await self.client.read(0, 40525, 2)
                self.assertIsNone(self.client._writer)
        self.mode = "normal"
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])

    async def test_timeout_and_reconnect(self):
        self.mode = "timeout"
        with self.assertRaises(modbus.ModbusError):
            await self.client.read(0, 40525, 2)
        self.mode = "normal"
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])

    async def test_retry_after_peer_disconnect(self):
        self.client.retries = 1
        self.mode = "drop_once"
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])
        self.assertEqual(self.connections, 2)

    async def test_request_spacing_does_not_consume_response_timeout(self):
        self.client.request_delay = 0.15
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])
        self.assertEqual(await self.client.read(0, 40525, 2), [0, 1])

    async def test_cancellation_closes_stream(self):
        self.mode = "timeout"
        task = asyncio.create_task(self.client.read(0, 40525, 2))
        while not self.requests:
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIsNone(self.client._writer)

    async def test_bounds_rejected_without_network_io(self):
        for args in ((248, 0, 1), (0, 65535, 2), (0, 0, 126), (0, 0, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                await self.client.read(*args)
        self.assertEqual(self.requests, [])
