# Portable SmartLogger Emulator for Windows

Run **SmartLoggerEmulator.exe**. No installer, Python installation, Home Assistant
installation or administrator account is required to run it. The executable contains
its Python runtime and extracts temporary runtime files while running. It needs no
internet connection. Target: Windows 10/11, 64-bit x86 (x64).

A local control page opens in your browser. Keep the console window open; closing
the browser tab does not stop the server. Use **Stop emulator** on the control page,
press **Ctrl+C** in the console or close the console window to stop it.
Simulation settings reset when you launch it again.

## Connect Home Assistant

1. Run the executable on a computer reachable from Home Assistant's network.
2. The control page displays the computer's IP address(es), chosen TCP port and unit ID.
3. Add **Huawei SmartLogger** in Home Assistant and enter those values. Use the
   computer's network IP, rather than `127.0.0.1` or Home Assistant's own IP.
4. Leave **unit ID 0**, timeout **5 seconds** and polling interval **30 seconds** for
   the defaults. The first free TCP port from **502 to 512** is chosen automatically.
   The displayed port is authoritative.
5. Optionally enter these downstream profiles in the integration:

   ```text
   meter:1,emi:2,inverter_remap:3
   ```

The server listens on the computer's existing IPv4 interfaces (`0.0.0.0`); it does not
assign an IP or change Windows network settings. If Windows Firewall asks, allow
the emulator on the private network used by Home Assistant. Network routing and
firewall rules must permit inbound access to the displayed Modbus port. The local
control page listens only on `127.0.0.1` and cannot be opened from Home Assistant.

## What it simulates

- Every nonreserved readable logger register in the supplied Huawei Issue 37 map.
- Realistic power, voltage, current, energy, temperature, timestamps, serial and
  status values; daily and total production energy accumulate while it runs.
- Meter and environmental-instrument profiles plus remapped inverter/EMI values.
- Big-endian data, signed and unsigned integers, strings, scaling and unit ID 0.
- Function 03 holding-register reads, including contiguous reads and concurrent clients.
- Modbus exceptions for unsupported addresses/functions and malformed request bounds.
- Read-only simulation. Modbus write requests return exception 01.

Solar power and site load are separate. Default solar output is **50 kW**, site load
**60 kW**, so the simulated grid meter reports approximately **10 kW import**.
Enable gentle variation or set power, load and ambient temperature directly.
Specific variables can be overridden in engineering units, including alarm words
and energy totals. When overriding the scheduling target, set mode register 40741
first: `0` means power factor, `1` means reactive power in kvar.

## Test failures and recovery

The control page lets you simulate no replies, closed connections or device-unavailable
exceptions. Use **Restore communication** to resume responses. Home Assistant's
entities should become unavailable and recover on subsequent polls. Restarting the
emulator restores normal communication and clears all custom overrides.

To emulate a partially supported register map, enter `unit:register` words under
Unsupported words, for example `0:40525`. This rejects any read spanning that word
and lets you test the integration's handling of individual unsupported variables.

The request counter and recent-request list show whether HA is actually communicating.
The page's own refreshes do not increment the Modbus request counter.

## Multiple independent SmartLoggers on one computer

Launch the executable a second time. Each process chooses a different free Modbus
port and local control-page port. Add a separate HA connection for each process using
the same computer IP and each displayed TCP port. Values, controls, overrides and
client connections are independent. For distinct serials or specific ports:

```powershell
.\SmartLoggerEmulator.exe --port 1502 --serial SIM3000-A
.\SmartLoggerEmulator.exe --port 1503 --serial SIM3000-B
```

Other options: `--unit-id 0`, `--devices "meter:1,emi:2,inverter_remap:3"`,
`--bind 0.0.0.0`, `--ui-port 8765`, `--no-browser` and `--version`.
An explicitly requested Modbus port is never silently changed if it is occupied.
For loopback-only testing, use `--bind 127.0.0.1`.

## Scope

This is a test double for the documented measurement interface. It does not certify
Huawei firmware compatibility or reproduce firmware-specific invalid values,
encrypted management connections, device discovery function 2B, write commands,
plant controls, historical data or actual electrical equipment. Nothing is sent to
Huawei. Only simulated Modbus replies are sent to connected clients.

The executable is unsigned. Windows may display its usual downloaded-application
checks. A source build is available in this repository; no Windows security settings
are changed by the program.

## Source and reproducible build

Run from the repository with Python 3.12 or later:

```sh
python -m emulator.server
```

To build the Windows single-file executable with Python and PyInstaller available:

```powershell
python -m pip install pyinstaller
python tools/build_emulator.py
```

The output is `dist/SmartLoggerEmulator.exe` and a portable ZIP containing that
executable and this guide. Build the executable on Windows; Linux CI runs source
protocol tests rather than trying to cross-compile a Windows program.
