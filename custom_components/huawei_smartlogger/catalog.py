"""Typed, address-aware register catalogue; independent of Home Assistant."""

from dataclasses import dataclass
import re

from .catalog_data import REGISTERS


@dataclass(frozen=True, slots=True)
class Variable:
    key: str
    name: str
    group: str
    target: int
    unit_id: int
    address: int
    datatype: str
    count: int
    unit: str | None
    gain: int
    access: str
    source_page: int
    reserved: bool = False

    @property
    def selectable(self) -> bool:
        return self.access != "WO" and not self.reserved


DEVICE_TYPES = ("meter", "emi", "inverter_remap", "emi_remap")


def parse_devices(text: str) -> list[tuple[str, int]]:
    """Parse explicit downstream devices, without probing unknown addresses."""
    devices = []
    seen = set()
    for token in re.split(r"[,\n]+", text.strip()):
        if not token.strip():
            continue
        parts = token.strip().split(":")
        if len(parts) != 2 or parts[0] not in DEVICE_TYPES or not parts[1].isdigit():
            raise ValueError("Use meter:1, emi:2, inverter_remap:3 or emi_remap:4")
        group, number = parts[0], int(parts[1])
        if not 1 <= number <= 247:
            raise ValueError("Device addresses must be between 1 and 247")
        # A physical device must have a single profile.
        if number in seen:
            raise ValueError("A downstream address can only be listed once")
        seen.add(number)
        devices.append((group, number))
    if len(devices) > 32:
        raise ValueError("Configure at most 32 downstream devices per connection")
    return devices


def build_catalog(unit_id: int = 0, devices: str = "") -> list[Variable]:
    """Expand register facts into separate targets and stable variable keys."""
    result = []
    targets = [("logger", 0), *parse_devices(devices)]
    for group, target in targets:
        if group in ("meter", "emi") and target == unit_id:
            raise ValueError("A downstream unit ID conflicts with the SmartLogger unit ID")
        rows = [r for r in REGISTERS if r["group"] == group]
        if group in ("meter", "emi"):
            rows += [r for r in REGISTERS if r["group"] == "public"]
        for row in rows:
            address = row["address"]
            if group.endswith("_remap"):
                address = 51000 + 25 * (target - 1) + address
            result.append(Variable(
                key=f"{group}:{target}:{row['address']}", name=row["name"], group=group,
                target=target, unit_id=unit_id if group == "logger" or group.endswith("_remap") else target,
                address=address, datatype=row["datatype"], count=row["count"], unit=row["unit"],
                gain=row["gain"], access=row["access"], source_page=row["page"], reserved=row["reserved"],
            ))
    return result


def selected_variables(settings: dict, selection: list[str]) -> list[Variable]:
    keys = set(selection)
    return [v for v in build_catalog(settings.get("unit_id", 0), settings.get("devices", ""))
            if v.selectable and v.key in keys]


def decode(variable: Variable, registers: list[int]) -> int | float | str:
    """Huawei sends direct register addresses and big-endian multiword values."""
    if len(registers) != variable.count:
        raise ValueError("Incorrect register count")
    raw = b"".join(word.to_bytes(2, "big") for word in registers)
    if variable.datatype == "STR":
        return raw.split(b"\0", 1)[0].decode("ascii", errors="replace").strip()
    if variable.datatype == "MLD":
        return raw.hex()
    value = int.from_bytes(raw, "big", signed=variable.datatype.startswith("I"))
    return value if variable.gain in (0, 1) else value / variable.gain
