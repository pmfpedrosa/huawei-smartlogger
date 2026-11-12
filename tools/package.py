"""Build a manual-install archive containing only the integration and guide."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
component = ROOT / "custom_components/huawei_smartlogger"
manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
target = ROOT / "dist" / f"huawei-smartlogger-{manifest['version']}.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for path in sorted(component.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in (".py", ".json"):
            archive.write(path, path.relative_to(ROOT).as_posix())
    for name in ("README.md", "LICENSE", "docs/REGISTERS.md"):
        archive.write(ROOT / name, name)
print(target)
