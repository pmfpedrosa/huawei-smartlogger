"""Read-only SmartLogger Modbus TCP emulator with a localhost control page."""

import argparse
import asyncio
from collections import deque
from contextlib import suppress
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import math
from pathlib import Path
import secrets
import socket
import struct
import sys
import threading
import time
import webbrowser

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components/huawei_smartlogger"))
from catalog_data import REGISTERS  # noqa: E402

VERSION = "0.1.0"
DEFAULT_DEVICES = "meter:1,emi:2,inverter_remap:3"


def definitions(unit_id=0, devices=DEFAULT_DEVICES):
    """Expand the same factual catalogue shipped with the integration."""
    targets = [("logger", 0)]
    seen = set()
    for part in devices.replace("\n", ",").split(","):
        if not part.strip():
            continue
        group, text = part.strip().split(":")
        target = int(text)
        if group not in ("meter", "emi", "inverter_remap", "emi_remap") or not 1 <= target <= 247:
            raise ValueError("Invalid downstream profile")
        if target in seen or (group in ("meter", "emi") and target == unit_id):
            raise ValueError("Conflicting downstream device address")
        seen.add(target)
        targets.append((group, target))
    result = []
    for group, target in targets:
        groups = (group, "public") if group in ("meter", "emi") else (group,)
        for source in REGISTERS:
            if source["group"] not in groups or source["reserved"] or source["access"] == "WO":
                continue
            row = dict(source, group=group, target=target,
                       key=f"{group}:{target}:{source['address']}", source_address=source["address"])
            row["unit_id"] = target if group in ("meter", "emi") else unit_id
            if group.endswith("_remap"):
                row["address"] = 51000 + 25 * (target - 1) + source["address"]
            result.append(row)
    return result


def encode(row, value, mode=1):
    """Encode engineering units into Huawei big-endian register words."""
    count = row["count"]
    if row["datatype"] == "STR":
        data = str(value).encode("ascii")
        if len(data) > count * 2:
            raise ValueError(f"String exceeds {count * 2} ASCII characters")
        data = data.ljust(count * 2, b"\0")
    else:
        divisor = (1000 if mode == 0 else 10) if row["gain"] == 0 else row["gain"]
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Value must be finite")
        integer = round(number * divisor)
        try:
            data = integer.to_bytes(count * 2, "big", signed=row["datatype"].startswith("I"))
        except OverflowError as err:
            raise ValueError(f"Value is outside {row['datatype']} range") from err
    return list(struct.unpack(f">{count}H", data))


def computer_addresses():
    addresses = set()
    with suppress(OSError):
        addresses.update(item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    return sorted(a for a in addresses if not a.startswith("127.")) or ["127.0.0.1"]


class Simulation:
    def __init__(self, unit_id=0, devices=DEFAULT_DEVICES, serial="SIM3000-00000001"):
        if not 0 <= unit_id <= 247:
            raise ValueError("Unit ID must be 0–247")
        serial.encode("ascii")
        if not serial or len(serial) > 20:
            raise ValueError("Serial must contain 1–20 ASCII characters")
        self.rows = definitions(unit_id, devices)
        self.by_key = {row["key"]: row for row in self.rows}
        self.unit_id, self.devices, self.serial = unit_id, devices, serial
        self.lock = threading.RLock()
        self.shutdown = threading.Event()
        self.controls = dict(power_kw=50.0, load_kw=60.0, temperature=28.0, vary=False, fault="online")
        self.overrides = {}
        self.unsupported = set()
        self.total_kwh, self.daily_kwh = 123456.7, 123.4
        self.started = self.previous = time.monotonic()
        self.day = datetime.now().date()
        self.requests = 0
        self.recent = deque(maxlen=12)
        self.port = None
        self.addresses = computer_addresses()

    def _values(self):
        now = datetime.now().astimezone()
        tick = time.monotonic()
        factor = 1 + 0.05 * math.sin((tick - self.started) / 20) if self.controls["vary"] else 1
        power = self.controls["power_kw"] * factor
        if self.day != now.date():
            self.day, self.daily_kwh = now.date(), 0.0
        produced = power * max(0, tick - self.previous) / 3600
        self.total_kwh += produced
        self.daily_kwh += produced
        self.previous = tick
        pf = 0.985
        reactive = power * math.tan(math.acos(pf))
        grid = self.controls["load_kw"] - power
        current = power * 1000 / (math.sqrt(3) * 400 * pf)
        temperature = self.controls["temperature"]
        logger = {
            40000: int(now.timestamp()), 40002: 0, 40004: 1, 40005: int(now.utcoffset().total_seconds()),
            40007: int(bool(now.dst())), 40008: int(now.dst().total_seconds() / 60) if now.dst() else 0,
            40009: int(now.timestamp() + now.utcoffset().total_seconds()),
            40204: 0, 40420: power, 40422: reactive, 40424: power, 40426: reactive,
            40428: 100, 40429: pf, 40500: power * 1000 / 600, 40521: power / 0.98,
            40523: self.total_kwh * 0.5, 40525: power, 40532: pf,
            40541: 1, 40542: 1, 40543: 1, 40544: reactive, 40550: self.total_kwh * 0.5,
            40554: power * 1000 / 600, 40560: self.total_kwh, 40562: self.daily_kwh,
            40564: 6.5, 40566: 1, 40567: 1, 40568: 0, 40570: 0,
            40572: current, 40573: current, 40574: current, 40575: 400, 40576: 400, 40577: 400,
            40685: 98, 40693: 60, 40695: -60, 40697: 100, 40699: 1, 40700: 0,
            40713: self.serial, 40736: 0, 40737: 0, 40738: power, 40740: 0, 40741: 1,
            40742: reactive, 40802: 100, 41124: 0.5, 41934: 110, 41936: 100,
            41938: 100, 41940: 1, 41942: 0, 41947: 0, 41948: 300, 41949: 0,
            42017: now.year, 42018: now.month, 42019: now.day, 42020: now.hour,
            42021: now.minute, 42022: now.second, 42150: 0, 50000: 0, 50001: 0,
            50002: 0, 50003: 0,
        }
        emi = {40031: 2.5, 40032: 180, 40033: temperature + 8, 40034: temperature,
               40035: 800, 40036: 12, 40038: 780, 40039: 11.8, 40041: 0,
               40042: 0, 40043: 3.33, 40045: 3.28}
        meter = {a: 0 for a in range(32260, 32362)}
        for address in (32260, 32262, 32264):
            meter[address] = 230
        for address in (32266, 32268, 32270):
            meter[address] = 400
        for address in (32272, 32274, 32276):
            meter[address] = grid * 1000 / (math.sqrt(3) * 400 * pf)
        meter.update({32278: grid, 32280: grid * math.tan(math.acos(pf)), 32284: pf,
                      32287: abs(grid) / pf, 32335: grid / 3, 32337: grid / 3, 32339: grid / 3,
                      32341: 54321.0, 32345: 1234.0, 32349: 100.0, 32353: 20.0,
                      32357: 54421.0, 32361: 1254.0})
        inverter = {0: power, 2: reactive, 4: power * 1000 / 600, 5: power / 0.98,
                    7: 10, 8: pf, 9: 0x0200, 11: temperature + 10, 12: 0, 14: 0, 16: 0}
        remapped_emi = dict(zip((0, 1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 14), emi.values(), strict=True))
        mode_key = "logger:0:40741"
        mode = int(self.overrides.get(mode_key, 1))
        if mode == 0:
            logger[40742] = pf
        maps = dict(logger=logger, meter=meter, emi=emi, inverter_remap=inverter, emi_remap=remapped_emi)
        values = {}
        words = {}
        for row in self.rows:
            address = row["source_address"]
            public = {65521: 1, 65522: 1, 65523: row["target"],
                      65524: f"SIM {row['group']} {row['target']}", 65534: 0xB001}
            value = self.overrides.get(row["key"], public.get(address, maps[row["group"]].get(address, 0)))
            values[row["key"]] = value
            for offset, word in enumerate(encode(row, value, mode)):
                words[row["unit_id"], row["address"] + offset] = word
        for key in self.unsupported:
            words.pop(key, None)
        return values, words

    def read(self, unit, address, count):
        with self.lock:
            _, words = self._values()
            try:
                return [words[unit, address + index] for index in range(count)]
            except KeyError:
                return None

    def record(self, client, unit, function, address, count, result):
        with self.lock:
            self.requests += 1
            self.recent.appendleft(dict(time=datetime.now().strftime("%H:%M:%S"), client=client,
                                       unit=unit, function=function, address=address, count=count, result=result))

    def update(self, data):
        with self.lock:
            controls = dict(self.controls)
            for key, lower, upper in (("power_kw", 0, 100), ("load_kw", 0, 500), ("temperature", -40, 100)):
                if key in data:
                    value = float(data[key])
                    if not math.isfinite(value) or not lower <= value <= upper:
                        raise ValueError(f"{key} must be between {lower} and {upper}")
                    controls[key] = value
            if "vary" in data:
                if not isinstance(data["vary"], bool):
                    raise ValueError("vary must be a boolean")
                controls["vary"] = data["vary"]
            if "fault" in data:
                if data["fault"] not in ("online", "timeout", "disconnect", "exception"):
                    raise ValueError("Unknown fault mode")
                controls["fault"] = data["fault"]
            unsupported = set(self.unsupported)
            if "unsupported" in data:
                unsupported = set()
                for item in data["unsupported"].replace("\n", ",").split(","):
                    if item.strip():
                        unit, address = map(int, item.strip().split(":"))
                        if not 0 <= unit <= 247 or not 0 <= address <= 65535:
                            raise ValueError("Invalid unsupported unit:register")
                        unsupported.add((unit, address))
            overrides = dict(self.overrides)
            if data.get("clear_overrides"):
                overrides.clear()
            if "override_key" in data:
                key = data["override_key"]
                if key not in self.by_key:
                    raise ValueError("Unknown variable")
                if data.get("remove_override"):
                    overrides.pop(key, None)
                else:
                    row = self.by_key[key]
                    value = data["override_value"]
                    value = str(value) if row["datatype"] == "STR" else float(value)
                    mode = int(overrides.get("logger:0:40741", 1))
                    if key == "logger:0:40741" and value not in (0, 1):
                        raise ValueError("Scheduling mode must be 0 or 1")
                    encode(row, value, mode)
                    overrides[key] = value
            old = self.controls, self.overrides, self.unsupported
            self.controls, self.overrides, self.unsupported = controls, overrides, unsupported
            try:
                self._values()  # Validate interdependent mode/target overrides atomically.
            except (ValueError, OverflowError):
                self.controls, self.overrides, self.unsupported = old
                raise
            if data.get("shutdown") is True:
                self.shutdown.set()

    def state(self):
        with self.lock:
            values, _ = self._values()
            mode = int(self.overrides.get("logger:0:40741", 1))
            variables = [dict(key=r["key"], name=r["name"], group=r["group"], target=r["target"],
                              address=r["address"], unit_id=r["unit_id"], datatype=r["datatype"],
                              unit=(None if mode == 0 else "kvar") if r["gain"] == 0 else r["unit"],
                              value=values[r["key"]], overridden=r["key"] in self.overrides)
                         for r in self.rows]
            return dict(version=VERSION, port=self.port, unit_id=self.unit_id, devices=self.devices,
                        serial=self.serial, addresses=self.addresses, controls=self.controls.copy(),
                        variables=variables, requests=self.requests, recent=list(self.recent),
                        unsupported=",".join(f"{u}:{a}" for u, a in sorted(self.unsupported)))


async def serve_client(reader, writer, simulation):
    """Handle fragmented/pipelined MBAP frames, with a bounded frame size."""
    peer = writer.get_extra_info("peername")
    client = peer[0] if peer else "unknown"
    try:
        while True:
            header = await asyncio.wait_for(reader.readexactly(7), 120)
            transaction, protocol, length, unit = struct.unpack(">HHHB", header)
            if protocol != 0 or not 2 <= length <= 254:
                break
            body = await asyncio.wait_for(reader.readexactly(length - 1), 10)
            function = body[0]
            address, count = struct.unpack(">HH", body[1:]) if len(body) == 5 else (None, None)
            with simulation.lock:
                fault = simulation.controls["fault"]
            if fault == "disconnect":
                simulation.record(client, unit, function, address, count, "disconnected")
                break
            if fault == "timeout":
                simulation.record(client, unit, function, address, count, "no response")
                continue
            code = 0
            words = None
            if fault == "exception":
                code = 0x0B
            elif function != 3:
                code = 1
            elif len(body) != 5 or not 1 <= count <= 125 or address + count > 65536:
                code = 3
            else:
                words = simulation.read(unit, address, count)
                if words is None:
                    code = 2
            if code:
                response = bytes([function | 0x80, code])
            else:
                response = bytes([3, count * 2]) + struct.pack(f">{count}H", *words)
            writer.write(struct.pack(">HHHB", transaction, 0, len(response) + 1, unit) + response)
            await writer.drain()
            simulation.record(client, unit, function, address, count, f"exception {code:02X}" if code else "OK")
    except (asyncio.IncompleteReadError, ConnectionError, TimeoutError):
        pass
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()


def control_server(simulation, port=8765):
    token = secrets.token_urlsafe(24)
    html = (Path(__file__).resolve().parent / "dashboard.html").read_text(encoding="utf-8")
    html = html.replace("__TOKEN__", token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, data, content_type="application/json"):
            payload = data.encode("utf-8") if isinstance(data, str) else json.dumps(data, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, html, "text/html")
            elif self.path == "/api/state":
                self.respond(200, simulation.state())
            else:
                self.respond(404, {"error": "Not found"})

        def do_POST(self):
            if self.path != "/api/control":
                self.respond(404, {"error": "Not found"})
                return
            if not hmac.compare_digest(self.headers.get("X-Emulator-Token", ""), token):
                self.respond(403, {"error": "Open the emulator's local control page"})
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 1 <= size <= 16384:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object")
                simulation.update(data)
                self.respond(200, {"ok": True})
            except (ValueError, KeyError, TypeError, UnicodeError) as err:
                self.respond(400, {"error": str(err)})

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def run(args):
    simulation = Simulation(args.unit_id, args.devices, args.serial)
    if args.bind != "0.0.0.0":
        simulation.addresses = [args.bind]
    server = None
    for port in ([args.port] if args.port is not None else range(502, 513)):
        try:
            server = await asyncio.start_server(lambda r, w: serve_client(r, w, simulation), args.bind, port)
            break
        except OSError:
            if args.port is not None:
                raise
    if server is None:
        raise OSError("No free Modbus port in 502–512; specify --port")
    simulation.port = server.sockets[0].getsockname()[1]
    control = control_server(simulation, args.ui_port)
    url = f"http://127.0.0.1:{control.server_port}/"
    print(f"SmartLogger Emulator {VERSION} — simulated data only", flush=True)
    print(f"Control page: {url}", flush=True)
    print(f"Home Assistant host: {', '.join(simulation.addresses)}", flush=True)
    print(f"Modbus TCP port: {simulation.port}; unit ID: {simulation.unit_id}", flush=True)
    print(f"Optional downstream devices: {simulation.devices}", flush=True)
    print("Keep this window open. Press Ctrl+C or close it to stop.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        async with server:
            # A cooperative stop also lets the frozen single-file launcher clean
            # up its child process and temporary runtime directory normally.
            while not simulation.shutdown.is_set():
                await asyncio.sleep(0.2)
    finally:
        control.shutdown()
        control.server_close()


def main():
    parser = argparse.ArgumentParser(description="Portable, read-only Huawei SmartLogger Modbus TCP emulator")
    parser.add_argument("--bind", default="0.0.0.0", help="Listening interface (default: all IPv4 interfaces)")
    parser.add_argument("--port", type=int, help="Modbus TCP port; default chooses first free port in 502–512")
    parser.add_argument("--unit-id", type=int, default=0)
    parser.add_argument("--devices", default=DEFAULT_DEVICES)
    parser.add_argument("--serial", default="SIM3000-00000001")
    parser.add_argument("--ui-port", type=int, default=8765, help="Local control-page port; falls back to a free port")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error("Port must be 0–65535")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, UnicodeError) as err:
        print(f"Cannot start emulator: {err}", file=sys.stderr, flush=True)
        if getattr(sys, "frozen", False) and not args.no_browser:
            input("Press Enter to close...")
        raise SystemExit(1) from err


if __name__ == "__main__":
    main()
