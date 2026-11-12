"""Read planning, snapshots and mode-aware decoding without HA dependencies."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from .catalog import Variable, build_catalog, decode
from .modbus import ModbusClient, ModbusException


@dataclass(frozen=True, slots=True)
class Reading:
    value: int | float | str | None
    unit: str | None
    error: str | None = None


def plan_reads(variables: list[Variable]) -> list[list[Variable]]:
    """Combine only touching/overlapping ranges, never read undocumented gaps."""
    batches: list[list[Variable]] = []
    for variable in sorted(variables, key=lambda v: (v.unit_id, v.address, v.count)):
        if batches:
            batch = batches[-1]
            start = batch[0].address
            end = max(v.address + v.count for v in batch)
            if (batch[0].unit_id == variable.unit_id and variable.address <= end
                    and max(end, variable.address + variable.count) - start <= 125):
                batch.append(variable)
                continue
        batches.append([variable])
    return batches


class Gateway:
    """One logger's client and snapshot lock; no shared mutable global state."""

    def __init__(self, settings: dict, client=None):
        self.settings = dict(settings)
        self.client = client or ModbusClient(
            settings["host"], settings.get("port", 502), settings.get("timeout", 5),
            settings.get("retries", 1), settings.get("request_delay", 0.05),
        )
        self._lock = asyncio.Lock()
        self.last_snapshot: datetime | None = None

    async def close(self):
        async with self._lock:
            await self.client.close()

    async def snapshot(self, variables: list[Variable]) -> dict[str, Reading]:
        async with self._lock:
            return await self._snapshot(variables)

    async def _snapshot(self, variables: list[Variable]) -> dict[str, Reading]:
        requested = [v for v in variables if v.selectable]
        raw = {}
        errors = {}
        # Target 40742 has a mode-dependent unit and gain.
        mode_needed = any(v.group == "logger" and v.address == 40742 for v in requested)
        if mode_needed:
            mode = next(v for v in build_catalog(self.settings.get("unit_id", 0)) if v.address == 40741)
            if mode.key not in {v.key for v in requested}:
                requested.append(mode)

        async def read_batch(batch):
            start = batch[0].address
            count = max(v.address + v.count for v in batch) - start
            try:
                words = await self.client.read(batch[0].unit_id, start, count)
                for variable in batch:
                    offset = variable.address - start
                    raw[variable.key] = words[offset:offset + variable.count]
            except ModbusException as err:
                if err.code in (2, 3) and len(batch) > 1:
                    middle = len(batch) // 2
                    await read_batch(batch[:middle])
                    await read_batch(batch[middle:])
                else:
                    for variable in batch:
                        errors[variable.key] = str(err)

        # A transport failure aborts this snapshot so stale values are not kept.
        # Unsupported registers are isolated and do not hide working neighbours.
        for batch in plan_reads(requested):
            await read_batch(batch)
        readings = {}
        for variable in requested:
            if variable.key not in raw:
                readings[variable.key] = Reading(None, variable.unit, errors.get(variable.key, "No data"))
                continue
            try:
                value = decode(variable, raw[variable.key])
                unit = variable.unit
                if variable.group == "logger" and variable.address == 40742:
                    mode_words = raw.get(mode.key)
                    if not mode_words or mode_words[0] not in (0, 1):
                        readings[variable.key] = Reading(None, None, "Scheduling mode unavailable")
                        continue
                    value /= 1000 if mode_words[0] == 0 else 10
                    unit = None if mode_words[0] == 0 else "kvar"
                readings[variable.key] = Reading(value, unit)
            except (ValueError, OverflowError) as err:
                readings[variable.key] = Reading(None, variable.unit, str(err))
        self.last_snapshot = datetime.now(timezone.utc)
        return {v.key: readings[v.key] for v in variables if v.selectable}


def selection_label(variable: Variable, reading: Reading | None) -> str:
    prefix = "SmartLogger" if variable.group == "logger" else f"{variable.group} {variable.target}"
    unit = reading.unit if reading and not reading.error else variable.unit
    current = str(reading.value) if reading and not reading.error else (reading.error if reading else "Not read")
    return (f"{prefix} / {variable.name} | {variable.address} | {variable.datatype} | "
            f"{unit or 'no unit'} | {current}")
