import asyncio
import unittest

from load_core import load

catalog = load("catalog")
gateway = load("gateway")
modbus = load("modbus")


class MemoryClient:
    def __init__(self, words=None):
        self.words = words or {}
        self.calls = []
        self.offline = False

    async def read(self, unit, address, count):
        self.calls.append((unit, address, count))
        if self.offline:
            raise modbus.ModbusError("Offline")
        if any((unit, address + i) not in self.words for i in range(count)):
            raise modbus.ModbusException(2)
        return [self.words[unit, address + i] for i in range(count)]

    async def close(self):
        pass


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_register_support_keeps_neighbours(self):
        variables = [v for v in catalog.build_catalog() if v.address in (40572, 40573, 40574)]
        client = MemoryClient({(0, 40572): 12, (0, 40574): 34})
        result = await gateway.Gateway({"host": "fake"}, client).snapshot(variables)
        self.assertEqual(result[variables[0].key].value, 12)
        self.assertIsNotNone(result[variables[1].key].error)
        self.assertEqual(result[variables[2].key].value, 34)
        self.assertEqual(client.calls[0], (0, 40572, 3))

    async def test_mode_dependent_unit_and_gain(self):
        variable = next(v for v in catalog.build_catalog() if v.address == 40742)
        client = MemoryClient({(0, 40741): 0, (0, 40742): 0, (0, 40743): 950})
        reader = gateway.Gateway({"host": "fake"}, client)
        result = (await reader.snapshot([variable]))[variable.key]
        self.assertEqual((result.value, result.unit), (0.95, None))
        client.words[0, 40741] = 1
        result = (await reader.snapshot([variable]))[variable.key]
        self.assertEqual((result.value, result.unit), (95, "kvar"))
        client.words[0, 40741] = 10
        self.assertIsNotNone((await reader.snapshot([variable]))[variable.key].error)

    async def test_two_loggers_same_address_remain_independent(self):
        v = next(v for v in catalog.build_catalog() if v.address == 40525)
        first = gateway.Gateway({"host": "first"}, MemoryClient({(0, 40525): 0, (0, 40526): 1000}))
        second = gateway.Gateway({"host": "second"}, MemoryClient({(0, 40525): 0, (0, 40526): 2000}))
        a, b = await asyncio.gather(first.snapshot([v]), second.snapshot([v]))
        self.assertEqual((a[v.key].value, b[v.key].value), (1, 2))
        first.client.offline = True
        with self.assertRaises(modbus.ModbusError):
            await first.snapshot([v])
        self.assertEqual((await second.snapshot([v]))[v.key].value, 2)

    async def test_only_selected_addresses_and_no_gap_reads(self):
        variables = [v for v in catalog.build_catalog() if v.address in (40525, 40560)]
        client = MemoryClient({(0, 40525): 0, (0, 40526): 1234, (0, 40560): 0, (0, 40561): 5678})
        reader = gateway.Gateway({"host": "fake"}, client)
        await reader.snapshot(variables)
        self.assertEqual(client.calls, [(0, 40525, 2), (0, 40560, 2)])
        client.calls.clear()
        self.assertEqual(await reader.snapshot([]), {})
        self.assertEqual(client.calls, [])

    async def test_failure_does_not_return_stale_values(self):
        v = next(v for v in catalog.build_catalog() if v.address == 40572)
        client = MemoryClient({(0, 40572): 10})
        reader = gateway.Gateway({"host": "fake"}, client)
        self.assertEqual((await reader.snapshot([v]))[v.key].value, 10)
        client.words.clear()
        result = (await reader.snapshot([v]))[v.key]
        self.assertIsNone(result.value)
        self.assertIsNotNone(result.error)

    async def test_labels_expose_type_unit_address_and_value(self):
        v = next(v for v in catalog.build_catalog() if v.address == 40525)
        label = gateway.selection_label(v, gateway.Reading(1.25, "kW"))
        for value in ("Active power", "I32", "kW", "40525", "1.25"):
            self.assertIn(value, label)

    def test_batches_stay_inside_protocol_limit(self):
        variables = catalog.build_catalog(0, "meter:1,emi:2,inverter_remap:3")
        for batch in gateway.plan_reads([v for v in variables if v.selectable]):
            self.assertLessEqual(max(v.address + v.count for v in batch) - batch[0].address, 125)
            self.assertEqual(len({v.unit_id for v in batch}), 1)
