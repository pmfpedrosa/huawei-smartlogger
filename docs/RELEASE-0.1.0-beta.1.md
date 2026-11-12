# Huawei SmartLogger 0.1.0-beta.1

Initial public beta for Home Assistant OS and other Home Assistant installations.

- Multiple independent SmartLogger3000 connections over local Modbus TCP.
- Editable host, port, unit ID, timeout, retries, request spacing and polling interval.
- Setup and options screens showing variable name, address, type, unit and current-value snapshot.
- Add/remove selected entities after setup; refresh values without losing the selection.
- Issue 37 logger register catalogue, with optional meter, EMI and remapped inverter profiles.
- Read-only polling, partial-register handling, reconnects and per-logger fault isolation.

Install with HACS by adding `https://github.com/pmfpedrosa/huawei-smartlogger` as an
Integration custom repository, or extract the attached ZIP into `/config` and restart HA.

This beta has automated protocol and Home Assistant lifecycle checks. It has not yet
been commissioned against actual SmartLogger hardware. Newer firmware can add
registers absent from Issue 37. Full SUN2000 maps and writable control entities are
outside this release. Configuration values are snapshots with an explicit refresh option.
