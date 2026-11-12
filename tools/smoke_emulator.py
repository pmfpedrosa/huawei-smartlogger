"""Verify two frozen executables without Python in PATH or the source directory.

The test driver uses Python, but the child emulator processes receive a minimal
Windows PATH and run from an empty directory. Both are stopped in finally.
"""

import argparse
import asyncio
from contextlib import suppress
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/unit"))
from load_core import load  # noqa: E402


def start(executable, directory, serial):
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
    environment["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    process = subprocess.Popen(
        [str(executable), "--bind", "127.0.0.1", "--port", "0", "--ui-port", "0",
         "--serial", serial, "--no-browser"], cwd=directory, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    lines = queue.Queue()

    def capture():
        for line in process.stdout:
            lines.put(line.rstrip())
    threading.Thread(target=capture, daemon=True).start()
    deadline = time.monotonic() + 30
    output = []
    port = url = None
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=0.2)
            output.append(line)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue
        if line.startswith("Control page:"):
            url = line.split("Control page:", 1)[1].strip()
        if line.startswith("Modbus TCP port:"):
            port = int(re.search(r"port: (\d+)", line).group(1))
        if url and port:
            return process, port, url
    process.kill()
    process.wait(timeout=5)
    raise RuntimeError("Frozen emulator failed to start: " + "\n".join(output))


def update(url, data):
    with urlopen(url, timeout=3) as response:
        html = response.read().decode()
    token = re.search(r"const token='([^']+)'", html).group(1)
    with urlopen(Request(url + "api/control", data=json.dumps(data).encode(),
                         headers={"Content-Type": "application/json", "X-Emulator-Token": token}), timeout=3) as response:
        assert json.loads(response.read())["ok"]


async def verify(ports):
    catalog, gateway = load("catalog"), load("gateway")
    readers = [gateway.Gateway(dict(host="127.0.0.1", port=p, timeout=2, retries=0, request_delay=0)) for p in ports]
    variables = [v for v in catalog.build_catalog(0, "meter:1,emi:2,inverter_remap:3") if v.selectable]
    try:
        results = await asyncio.gather(*(r.snapshot(variables) for r in readers))
        assert all(not reading.error for result in results for reading in result.values())
        assert [result["logger:0:40525"].value for result in results] == [25, 75]
        assert [result["logger:0:40713"].value for result in results] == ["SIM3000-A", "SIM3000-B"]
        print(f"PASS: {len(variables)} real integration variables decoded from each frozen executable")
    finally:
        for reader in readers:
            await reader.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", nargs="?", default=str(ROOT / "dist/SmartLoggerEmulator.exe"))
    args = parser.parse_args()
    directory = ROOT / "tmp/portable-smoke"
    directory.mkdir(parents=True, exist_ok=True)
    instances = []
    try:
        for serial, power in (("SIM3000-A", 25), ("SIM3000-B", 75)):
            instance = start(Path(args.executable).resolve(), directory, serial)
            instances.append(instance)
            update(instance[2], {"power_kw": power})
        asyncio.run(verify([instance[1] for instance in instances]))
        for process, _port, url in instances:
            with urlopen(url + "api/state", timeout=3) as response:
                state = json.loads(response.read())
            assert state["requests"] > 0
            assert process.poll() is None
        print("PASS: portable EXEs, localhost control pages, overrides and independent TCP sessions")
    finally:
        for process, _port, _url in instances:
            # A one-file Windows bootloader owns a child process; close the whole
            # test process tree, rather than leaving the child server running.
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, check=False)
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=5)
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
