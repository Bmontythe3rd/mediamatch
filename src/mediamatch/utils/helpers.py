"""Miscellaneous utility functions."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Resolve path to a bundled asset whether running as script or PyInstaller exe."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent.parent / relative


def config_dir() -> Path:
    """Return platform-appropriate config directory for MediaMatch."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "MediaMatch"
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_file() -> Path:
    return config_dir() / "settings.json"
