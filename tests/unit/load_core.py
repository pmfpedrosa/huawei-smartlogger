"""Load the actual HA-independent modules without executing HA's entry point."""

import importlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "smartlogger_core_under_test"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components/huawei_smartlogger")]
    sys.modules[PACKAGE] = package


def load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")
