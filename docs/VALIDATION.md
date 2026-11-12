# Validation

Version: 0.1.0-beta.1. Date: 2026-11-12.

## Local verification

- 22 portable unit and asynchronous loopback TCP tests passed on Python 3.12.14 / Windows.
- Source tables extracted from the provided Huawei Issue 37 PDF: 83 logger, 12 EMI,
  44 meter, 5 public, 19 remapped inverter and 21 remapped EMI definitions.
- Tests verify direct addressing, unit ID 0, fragmented TCP responses, protocol/transaction/
  unit/length checks, retries, reconnect after timeout, cancellation, signed decoding,
  64-bit values, source scaling, dynamic mode dependency, sparse register support and
  independence between two simulated loggers.

## Home Assistant verification

- **7 Home Assistant tests passed** on Home Assistant **2026.10.4**, Python **3.14.10**, Linux.
- The actual integration was loaded. The suite verified complete setup including the
  background scan and selection form, independent entity identities and values,
  adding/removing entities through reload, per-logger unavailable states, saved
  selections, duplicate prevention, offline options and endpoint reconfiguration.
- Home Assistant's **hassfest validation passed** for manifest and translation metadata.
- **22 protocol tests, compilation, lint and ZIP creation passed** in Linux CI.
- [Successful verification run](https://github.com/pmfpedrosa/huawei-smartlogger/actions/runs/43239073812)
  tested implementation commit `bae6aaa9f4d0113493d17b6407febb5098161e4d`.

The declared 2025.3 API baseline was reviewed against upstream definitions. The full
runtime suite has been executed against 2026.10.4; earlier HA releases have not been
individually commissioned. CI follows the HA version selected by the test plugin.

## Hardware commissioning still required

1. Confirm firmware version, address mode, Modbus enablement and permitted client IP.
2. Add one logger, compare power, energy, ESN and status values against its WebUI.
3. Check unsupported-register handling and any firmware-specific invalid sentinels.
4. Add a second logger, including matching unit IDs, and verify independent values.
5. Add/remove entities, restart HA and confirm saved selections.
6. Disconnect one logger and verify only its entities become unavailable; reconnect.
7. Verify downstream profiles against actual physical/logical addressing, if used.
8. Verify daily energy rollover and energy statistics before using production dashboards.

No live SmartLogger connection has been tested and no existing HA installation has been modified.
