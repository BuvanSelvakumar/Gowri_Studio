"""Passport size presets, loaded from presets.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    width_mm: float
    height_mm: float
    dpi: int
    output_px: tuple[int, int]
    head_fraction: float
    top_margin: float

    @property
    def aspect(self) -> float:
        """Output width / height."""
        return self.output_px[0] / self.output_px[1]


from .resources import writable

DEFAULT_PRESETS_PATH = writable("presets.json")


def load_presets(path: str | Path = DEFAULT_PRESETS_PATH) -> dict[str, Preset]:
    data = json.loads(Path(path).read_text())
    presets: dict[str, Preset] = {}
    for key, p in data.items():
        presets[key] = Preset(
            key=key,
            label=p["label"],
            width_mm=p["width_mm"],
            height_mm=p["height_mm"],
            dpi=p["dpi"],
            output_px=(int(p["output_px"][0]), int(p["output_px"][1])),
            head_fraction=p["head_fraction"],
            top_margin=p["top_margin"],
        )
    return presets


def get_preset(key: str, path: str | Path = DEFAULT_PRESETS_PATH) -> Preset:
    presets = load_presets(path)
    if key not in presets:
        raise KeyError(f"Unknown preset '{key}'. Available: {', '.join(presets)}")
    return presets[key]


def sync_bundled_presets() -> None:
    """Add any newly-bundled presets to the user's presets file, preserving
    their own edits. Needed because the writable presets.json is only seeded
    once; new app versions ship new presets that must still appear."""
    from .resources import bundle_root

    user_path = Path(DEFAULT_PRESETS_PATH)
    bundle_path = bundle_root() / "presets.json"
    if not bundle_path.exists() or bundle_path.resolve() == user_path.resolve():
        return  # running from source: user file IS the bundle file
    try:
        bundled = json.loads(bundle_path.read_text())
        user = json.loads(user_path.read_text()) if user_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return
    added = {k: v for k, v in bundled.items() if k not in user}
    if added:
        user.update(added)
        user_path.write_text(json.dumps(user, indent=2))


def load_raw(path: str | Path = DEFAULT_PRESETS_PATH) -> dict:
    """Raw JSON dict (for the Configuration page editor)."""
    return json.loads(Path(path).read_text())


def save_raw(data: dict, path: str | Path = DEFAULT_PRESETS_PATH) -> None:
    Path(path).write_text(json.dumps(data, indent=2))
