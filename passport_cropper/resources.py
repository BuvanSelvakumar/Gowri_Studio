"""Resource paths that work both from source and from a PyInstaller bundle.

- Read-only assets (ML models, default presets) live next to the code / in the
  bundle (``bundle_root``).
- User-writable files (settings.json, an editable presets.json) live in a data
  directory: the project root when running from source, or ~/.passport_cropper
  when frozen. Writable files are seeded from the bundle on first use.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)


def bundle_root() -> Path:
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    d = (Path.home() / ".passport_cropper") if FROZEN else bundle_root()
    d.mkdir(parents=True, exist_ok=True)
    return d


def bundled(*parts: str) -> Path:
    return bundle_root().joinpath(*parts)


def writable(name: str) -> Path:
    """A writable path in the data dir, seeded from the bundle if missing."""
    target = data_dir() / name
    if not target.exists():
        src = bundle_root() / name
        if src.exists() and src != target:
            shutil.copy2(src, target)
    return target
