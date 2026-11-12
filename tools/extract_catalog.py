"""Rebuild the factual register catalogue from Huawei Issue 37 (not redistributed).

Usage: python tools/extract_catalog.py path/to/SmartLogger.pdf
Requires pdfplumber only for catalogue maintenance, never at runtime.
"""

import json
from pathlib import Path
import pprint
import sys

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
UNITS = {"N/A": None, "mins": "min", "kVar": "kvar", "kVAR": "kvar",
         "ºC": "°C", "℃": "°C", "W/㎡": "W/m²", "W/m2": "W/m²",
         "MJ/㎡": "MJ/m²", "MJ/m2": "MJ/m²", "kWh/㎡": "kWh/m²"}


def extract(path):
    result = []
    groups = {"logger": range(11, 22), "emi": (27, 28), "meter": (28, 29, 30),
              "public": (30,), "inverter_remap": (31, 32), "emi_remap": (33,)}
    with pdfplumber.open(path) as pdf:
        for group, pages in groups.items():
            for page in pages:
                for table in pdf.pages[page].extract_tables():
                    for row in table:
                        if len(row) < 8 or not (row[0] or "").strip().isdigit():
                            continue
                        if row[2] not in ("RO", "RW", "WO"):
                            continue
                        # Page 29 holds both the last EMI rows and the meter table.
                        address = (row[6] or "").strip()
                        if not address.isdigit():
                            continue
                        address = int(address)
                        if group == "emi" and not 40031 <= address <= 40045:
                            continue
                        if group == "meter" and not 32260 <= address <= 32361:
                            continue
                        if group == "public" and address < 65521:
                            continue
                        if group == "meter" and address >= 65521:
                            continue
                        name = " ".join(row[1].split())
                        name = name.replace("Communica tion", "Communication").replace("communicat ion", "communication")
                        name = name.replace("anbormal", "abnormal").replace("activeadjust ment", "active adjustment")
                        name = name.replace("grid- connected", "grid-connected")
                        unit = "".join((row[4] or "N/A").split())
                        unit = UNITS.get(unit, unit)
                        gain_text = "".join((row[5] or "1").split())
                        gain = int(gain_text) if gain_text.isdigit() else 1
                        if group == "logger" and address == 40742:
                            gain, unit = 0, None  # Determined by register 40741.
                        result.append(dict(group=group, name=name, access=row[2],
                                           datatype=row[3], unit=unit, gain=gain,
                                           address=address, count=int(row[7]), page=page - 8,
                                           reserved="reserv" in name.lower() or "spare" in name.lower()))
    seen = set()
    for row in result:
        key = row["group"], row["address"]
        if key in seen:
            raise ValueError(f"Duplicate register: {key}")
        seen.add(key)
    counts = {g: sum(r["group"] == g for r in result) for g in groups}
    assert counts == {"logger": 83, "emi": 12, "meter": 44, "public": 5,
                      "inverter_remap": 19, "emi_remap": 21}, counts
    return result


def main():
    rows = extract(sys.argv[1])
    target = ROOT / "custom_components/huawei_smartlogger/catalog_data.py"
    target.write_text('"""Register facts transcribed from Huawei Issue 37, 2020-06-24.\n\n'
                      'Generated with tools/extract_catalog.py. Page numbers are printed pages.\n"""\n\n'
                      + "REGISTERS = " + pprint.pformat(rows, width=100, sort_dicts=False) + "\n", encoding="utf-8")
    lines = ["# Register catalogue", "", "Source: Huawei SmartLogger ModBus Interface Definitions, Issue 37 (2020-06-24).",
             "", "Reserved and write-only registers are documented but are not selectable measurement entities.",
             "Register 40742 uses mode 40741 to choose its scaling and unit. Remapped addresses are offsets.", "",
             "| Group | Variable | Address / offset | Type | Unit | Gain | Registers | Access | Source page |",
             "|---|---|---:|---|---|---:|---:|---|---:|"]
    for r in rows:
        lines.append(f"| {r['group']} | {r['name']} | {r['address']} | {r['datatype']} | {r['unit'] or '—'} | {r['gain'] or 'mode-dependent'} | {r['count']} | {r['access']} | {r['page']} |")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/REGISTERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({g: sum(r['group'] == g for r in rows) for g in sorted({r['group'] for r in rows})}))


if __name__ == "__main__":
    main()
