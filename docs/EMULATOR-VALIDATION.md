# Portable emulator verification

Date: 2026-11-12. Emulator: 0.1.0. Integration package: 0.1.0-beta.2.

Implementation commit: `e9ba63a27d14b39c82d1864ed835436bc4841d26`.

## Passed

- **33 protocol/catalogue/emulator tests** on Linux, including 11 emulator tests.
- **8 Home Assistant tests** against HA **2026.10.4**, Python **3.14.10**.
- The additional HA test loads the actual integration and exchanges actual Modbus TCP
  requests with two emulator servers. It verifies distinct values and entity identities,
  changing simulated power, per-logger unavailability and recovery. Only host-address
  inventory is replaced with loopback addresses; the transport and register replies
  are not mocked.
- **Windows build and frozen-executable smoke test** in GitHub Actions.
- Two frozen EXEs start from an empty working directory with no Python in PATH.
  Their bundled control pages work and the real integration client decodes **145
  variables per executable**, including separate serials and power values.
- Both executables shut down cooperatively through their local control API.
- **HACS, hassfest, compilation and lint** checks.
- Local Windows 11 build and the same two-EXE smoke test.
- Browser verification of power edits, timeout/recovery, per-variable overrides,
  filtering, clearing overrides and clean shutdown using the Stop button.

[Successful test/build run](https://github.com/pmfpedrosa/huawei-smartlogger/actions/runs/43269668091)
and [HACS validation](https://github.com/pmfpedrosa/huawei-smartlogger/actions/runs/43269668195).

## Local distributed executable

Filename: `SmartLoggerEmulator.exe`. Size: **10,300,006 bytes**.

SHA-256:

```text
2878c512c13446b1848d2de65dd7778c24d98d066995b0775c816eb227724836
```

The release asset is the locally tested build. Separate CI builds can have different
hashes because executable build metadata and environments differ.

## Limits

Testing used loopback TCP and simulated measurements. Inbound access from a separate
HAOS machine depends on the Windows computer's network and firewall configuration.
Windows 10 compatibility is targeted; the local execution check used Windows 11.
Physical Huawei firmware behaviour has not been validated. The emulator is a documented
read-interface test double and does not simulate write operations or function 2B discovery.

The existing Home Assistant installation was not modified. Temporary test emulator
instances were stopped after verification.
