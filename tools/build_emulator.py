"""Build and package the portable Windows emulator using PyInstaller."""

from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows executable on Windows")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", "SmartLoggerEmulator", "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "tmp/emulator-build"), "--specpath", str(ROOT / "tmp"),
        "--paths", str(ROOT / "custom_components/huawei_smartlogger"),
        "--add-data", f"{ROOT / 'emulator/dashboard.html'}:.",
        str(ROOT / "emulator/server.py"),
    ], check=True, cwd=ROOT)
    executable = ROOT / "dist/SmartLoggerEmulator.exe"
    target = ROOT / "dist/SmartLoggerEmulator-0.1.0-Windows-x64.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.write(executable, executable.name)
        archive.write(ROOT / "emulator/README.md", "README.md")
        archive.write(ROOT / "LICENSE", "LICENSE")
    print(target)


if __name__ == "__main__":
    main()
