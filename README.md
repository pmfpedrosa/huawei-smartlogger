# Huawei SmartLogger for Home Assistant

Custom Home Assistant integration for Huawei SmartLogger3000 over local Modbus TCP.
Install on Home Assistant OS through **HACS → Custom repositories → Integration**.

**Initial beta:** protocol tests use simulated devices. Actual SmartLogger hardware and
firmware compatibility still need commissioning tests before relying on the readings.
Independent project; not affiliated with Huawei or Home Assistant.

## Install through HACS

1. Install [HACS](https://www.hacs.xyz/docs/use/) if it is not already installed.
2. In HACS, open the three-dot menu → **Custom repositories**.
3. Add `https://github.com/pmfpedrosa/huawei-smartlogger`, category **Integration**.
4. Download **Huawei SmartLogger** and restart Home Assistant.
5. Open **Settings → Devices & services → Add integration → Huawei SmartLogger**.

This is a prerelease. If it is hidden by HACS, enable **Show beta versions**
in the repository menu and select **0.1.0-beta.2**, or use the manual-install ZIP below.

## Test without a physical SmartLogger

A **portable Windows x64 emulator** is included in the release downloads. Run
`SmartLoggerEmulator.exe`; its local control page displays the computer IP and TCP
port to enter in Home Assistant. No installer or Python installation is needed.
It provides simulated measurements, editable values, failure modes and independent
instances. See [the emulator guide](emulator/README.md).

This is an integration installed into Home Assistant Core, including on HAOS.
It does not install as a Supervisor app/add-on. It is available through HACS's
custom-repository option; default HACS catalogue inclusion is a separate process.
Home Assistant **2025.3 or later** is required.

## Manual install

Extract the supplied ZIP into the Home Assistant configuration directory, so that
`/config/custom_components/huawei_smartlogger/manifest.json` exists. The ZIP contains
the `custom_components` directory already. Restart and add the integration as above.

## Enable Modbus TCP on the SmartLogger

In the SmartLogger WebUI, open **Settings → Comm. Param. → Modbus TCP**:

- Enable the connection. With **Enable (Limited)**, add Home Assistant's IP to the permitted clients.
- Check the address mode and SmartLogger address configured on the device.
- Make sure Home Assistant can reach the logger's TCP port (normally **502**).

Issue 37 specifies **unit ID 0** for logger-level registers. The integration starts with
0 and lets you change it to match the deployed logger's address configuration.
Addresses such as **40525 are sent directly**, without subtracting 40001.
Byte and word order follow Huawei's documented big-endian representation.
Serial parameters such as baud rate and parity do not apply to Modbus TCP.

## Add a connection

Give each connection a meaningful name. Editable parameters are:

| Setting | Default | Meaning |
|---|---:|---|
| Host | required | IP address or hostname of this SmartLogger |
| Port | 502 | TCP listening port |
| SmartLogger unit ID | 0 | Logical Modbus address for logger-level and remapped registers |
| Timeout | 5 s | Maximum time for one request, including connecting |
| Retries | 1 | Additional attempts after transport failure |
| Request delay | 0.05 s | Minimum spacing between request starts |
| Polling interval | 30 s | Requested interval between updates; updates never overlap |
| Downstream devices | empty | Optional explicit device profiles; see below |

The integration reads a snapshot of the documented, readable registers. Each selection
label includes **device, variable name, register address, data type, unit and current
value or read error**. Values are snapshots, rather than continuously updating while
the dialog is open. Choose **Refresh values** and submit to rescan while preserving
your choices. Submit with refresh unchecked to save your entity selection.

No entities are preselected. Selecting none is supported. Write-only commands and
reserved registers are listed separately in the dialog and cannot be selected as
measurement entities. Read/write registers can be exposed as read-only sensors.
Unsupported readable registers remain visible with their read error and can be
selected in anticipation of a firmware or hardware change.

## Add or remove entities later

Open **Settings → Devices & services → Huawei SmartLogger → Configure** for the
relevant connection. A fresh variable snapshot is read. Change the selections and save.
New selections create entities; deselected entities are removed from that connection's
entity registry. Historical Recorder data is not deliberately deleted. Removing and
re-adding an entity can lose its manually assigned name or other registry customisations.

Use the connection's three-dot menu → **Reconfigure** to edit communication settings
or downstream profiles. This also offers a fresh variable selection before saving.
Changing the host preserves the connection's entity unique IDs. When a logger is
replaced, historical data therefore continues under those existing entity identities.

## Multiple SmartLoggers

Add the integration again for each SmartLogger. Each configuration entry has its own
TCP client, request lock, polling coordinator, settings, selections, snapshots and
device/entity identifiers. Identical register addresses and Modbus unit IDs on different
loggers cannot merge their entities. A logger's communication failure only makes its
own entities unavailable. Identical host/port/unit combinations are rejected as duplicates.
Hostname aliases for the same physical device are not automatically detected.

## Optional downstream variables

The initial catalogue contains every SmartLogger register in **Huawei ModBus Interface
Definitions Issue 37 (2020-06-24)**. It also includes the meter and environmental
instrument maps, public device registers, and documented remapped inverter/EMI values.
Full SUN2000 inverter coverage requires its separate model-specific register document.

To include downstream devices, enter comma-separated or newline-separated profiles:

```text
meter:1
emi:2
inverter_remap:3
emi_remap:4
```

- `meter:N` and `emi:N` read directly using downstream unit ID N.
- `inverter_remap:N` and `emi_remap:N` read through the configured SmartLogger unit ID.
  N is the **physical device address** in Huawei's remap formula:
  `51000 + 25 × (N − 1) + offset`.
- Read the actual device addresses from the logger WebUI. Do not assume logical and
  physical device addresses are the same when address translation is configured.
- Each downstream address can appear once, with a maximum of 32 devices per entry.
  Devices are configured explicitly; this beta does not automatically enumerate devices.

See [the complete register catalogue](docs/REGISTERS.md) for coverage and printed source pages.
Newer firmware can expose variables absent from Issue 37; these cannot be discovered
with names/types/units from plain Modbus reads and require updated register definitions.
The catalogue is bundled as Python data; the PDF is not distributed.

## Readings and statistics

Only selected readable variables are polled, plus mode register 40741 when required to
decode scheduling target 40742. Requests combine adjacent documented ranges, stay
within 125 registers, and split rejected batches to isolate unsupported registers.
Network failures cause unavailable states and reconnect attempts on later updates.
No previous value is returned as a successful fresh reading after a read failure.

Numeric values are scaled by Huawei's documented gain. Sensor attributes expose source
register, source unit, data type, gain and read errors. Reactive and apparent power are
converted from kvar/kVA to **var/VA** for Home Assistant compatibility. The selection
screen retains the source units. Lifetime and daily production energy sensors support
Home Assistant energy statistics. Signed meter energy totals use `total`, allowing
bidirectional changes. Status and alarm words are exposed numerically in this beta.

Register 40742 changes meaning according to 40741: power factor (divide by 1000) or
reactive power (divide by 10). It is unavailable when its mode cannot be read. Because
its unit can change, it has no fixed statistics or device class.

The read-only transport implements **function 03 only**. This version does not provide
power control, reset commands, register writes or the encrypted management-system
connection. Firmware-specific invalid-value sentinels are not inferred where Issue 37
does not define them; unusual extremes must be checked during commissioning.

## Development and verification

Run the portable tests (Python 3.12+, no third-party dependencies):

```sh
python -m unittest discover -s tests/unit -v
python -m compileall -q custom_components tools
python tools/package.py
```

Real Home Assistant lifecycle tests run in Linux CI:

```sh
pip install pytest-homeassistant-custom-component
pytest -q
```

The suite covers independent loggers, add/remove entity reloads, offline behaviour,
configuration persistence, reconfiguration, Modbus framing, reconnects, partial register
support, signed values, scaling and conditional units. See [validation notes](docs/VALIDATION.md).

To regenerate the catalogue locally, install `pdfplumber` and run:

```sh
python tools/extract_catalog.py /path/to/SmartLogger-ModBus-Interface-Definitions.pdf
```

The extractor checks all six table row counts and rejects duplicate group/address pairs.
Review table changes against the applicable Huawei firmware documentation before release.
