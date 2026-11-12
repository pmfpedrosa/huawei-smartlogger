"""Small asynchronous, read-only Modbus TCP transport using Python's standard library.

Only function 03 exists here. Responses are validated before use. Each connection
owns its stream and lock, including when multiple SmartLoggers share a unit ID.
"""

import asyncio
from contextlib import suppress
import struct


class ModbusError(Exception):
    """A communication or protocol error."""


class ModbusException(ModbusError):
    """An explicit exception response from the server."""

    def __init__(self, code: int):
        self.code = code
        super().__init__(f"Modbus exception 0x{code:02X}")


class ModbusClient:
    """One serialised persistent TCP session, with bounded reconnect attempts."""

    def __init__(self, host: str, port: int = 502, timeout: float = 5,
                 retries: int = 1, request_delay: float = 0.05):
        self.host, self.port, self.timeout = host, port, timeout
        self.retries, self.request_delay = retries, request_delay
        self._reader = None
        self._writer = None
        self._transaction = 0
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _close(self):
        writer, self._writer = self._writer, None
        self._reader = None
        if writer is not None:
            writer.close()
            with suppress(OSError, TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), timeout=1)

    async def close(self):
        async with self._lock:
            await self._close()

    async def read(self, unit_id: int, address: int, count: int) -> list[int]:
        if not 0 <= unit_id <= 247 or not 1 <= count <= 125 or not 0 <= address <= 65536 - count:
            raise ValueError("Invalid Modbus request bounds")
        async with self._lock:
            for attempt in range(self.retries + 1):
                try:
                    loop = asyncio.get_running_loop()
                    delay = self.request_delay - (loop.time() - self._last_request)
                    if delay > 0:
                        await asyncio.sleep(delay)
                    async with asyncio.timeout(self.timeout):
                        if self._writer is None or self._writer.is_closing():
                            self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
                        self._transaction = (self._transaction + 1) % 65536
                        transaction = self._transaction
                        packet = struct.pack(">HHHBBHH", transaction, 0, 6, unit_id, 3, address, count)
                        self._last_request = loop.time()
                        self._writer.write(packet)
                        await self._writer.drain()
                        header = await self._reader.readexactly(7)
                        tid, protocol, length, unit = struct.unpack(">HHHB", header)
                        if tid != transaction or protocol != 0 or unit != unit_id or not 2 <= length <= 254:
                            raise ModbusError("Invalid Modbus TCP response header")
                        body = await self._reader.readexactly(length - 1)
                        if body[0] == 0x83 and len(body) == 2:
                            raise ModbusException(body[1])
                        if body[0] != 3 or len(body) != 2 + count * 2 or body[1] != count * 2:
                            raise ModbusError("Invalid Modbus register response")
                        return list(struct.unpack(f">{count}H", body[2:]))
                except ModbusException:
                    raise
                except asyncio.CancelledError:
                    await self._close()
                    raise
                except (OSError, TimeoutError, asyncio.IncompleteReadError, ModbusError) as err:
                    await self._close()
                    if attempt == self.retries:
                        raise ModbusError(f"Modbus TCP communication failed: {type(err).__name__}") from err
        raise ModbusError("No response")  # Defensive; the retry loop always exits above.
