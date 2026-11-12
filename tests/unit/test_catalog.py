from dataclasses import replace
import unittest

from load_core import load

catalog = load("catalog")


class CatalogTests(unittest.TestCase):
    def test_document_counts_and_types(self):
        expected = {"logger": 83, "emi": 12, "meter": 44, "public": 5,
                    "inverter_remap": 19, "emi_remap": 21}
        rows = load("catalog_data").REGISTERS
        self.assertEqual({g: sum(r["group"] == g for r in rows) for g in expected}, expected)
        for row in rows:
            if not row["reserved"] and row["datatype"] not in ("STR", "MLD"):
                self.assertEqual(int(row["datatype"][1:]) // 16, row["count"])
        self.assertEqual(len({(r['group'], r['address']) for r in rows}), len(rows))

    def test_selected_excludes_commands_and_reserved(self):
        variables = catalog.build_catalog()
        self.assertEqual(len(variables), 83)
        result = catalog.selected_variables({}, [v.key for v in variables])
        self.assertTrue(all(v.access != "WO" and not v.reserved for v in result))
        self.assertEqual(catalog.selected_variables({}, []), [])

    def test_remap_formula_and_downstream_unit(self):
        variables = catalog.build_catalog(0, "meter:1, emi:2, inverter_remap:3, emi_remap:4")
        inverter = next(v for v in variables if v.key == "inverter_remap:3:0")
        meter = next(v for v in variables if v.key == "meter:1:32278")
        self.assertEqual((inverter.unit_id, inverter.address), (0, 51050))
        self.assertEqual((meter.unit_id, meter.address), (1, 32278))
        self.assertEqual(len(variables), 83 + 49 + 17 + 19 + 21)

    def test_invalid_device_inputs(self):
        for text in ("meter:0", "meter:248", "foo:1", "meter:1,emi:1", "meter:a", "meter:1:2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                catalog.parse_devices(text)
        with self.assertRaises(ValueError):
            catalog.build_catalog(1, "meter:1")

    def test_signed_unsigned_and_scaling(self):
        power = next(v for v in catalog.build_catalog() if v.address == 40525)
        self.assertEqual(catalog.decode(power, [0xFFFF, 0xFC18]), -1)
        self.assertEqual(catalog.decode(power, [0, 12345]), 12.345)
        for bits in (16, 32, 64):
            v = replace(power, datatype=f"I{bits}", count=bits // 16, gain=1)
            self.assertEqual(catalog.decode(v, [0xFFFF] * v.count), -1)
            self.assertEqual(catalog.decode(replace(v, datatype=f"U{bits}"), [0xFFFF] * v.count), 2**bits - 1)

    def test_string_and_64bit_energy(self):
        variables = catalog.build_catalog()
        esn = next(v for v in variables if v.address == 40713)
        self.assertEqual(catalog.decode(esn, [0x4142, 0x4344] + [0] * 8), "ABCD")
        co2 = next(v for v in variables if v.address == 40550)
        self.assertEqual(catalog.decode(co2, [0, 1, 0, 100]), 42949673.96)
        with self.assertRaises(ValueError):
            catalog.decode(esn, [0])
