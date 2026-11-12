# Huawei SmartLogger 0.1.0-beta.2

Adds a portable Windows x64 SmartLogger emulator for testing without physical hardware.
The Home Assistant integration's runtime behaviour is unchanged from beta.1.

## Windows emulator 0.1.0

- Download **SmartLoggerEmulator.exe**, or the portable ZIP containing the same executable and guide.
- Double-click to start. No installer or Python installation is required.
- A local control page displays the computer IP, TCP port and unit ID for Home Assistant.
- Simulates 145 readable variables with the default logger, meter, EMI and remapped inverter profiles.
- Change power/load/temperature, override individual registers, and test timeout/disconnect/exception recovery.
- Launch multiple copies to test separate SmartLogger connections on different ports.

The EXE bundles its runtime and uses a temporary extraction folder while running.
If Windows Firewall asks, permit access on the private network used by Home Assistant.
The control page is local to the Windows computer. Modbus replies use its network interfaces.

The emulator reproduces the documented read interface, not Huawei firmware or plant control.
Physical hardware testing remains a separate commissioning step.

Install the integration through HACS as before; download the integration ZIP only for
manual HA installation. The Windows EXE is run on the Windows computer, not on HAOS.
